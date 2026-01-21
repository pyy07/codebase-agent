"""基于 LangGraph 的 Agent 执行器"""

import asyncio
import json
import queue
from typing import TypedDict, Annotated, Sequence, Dict, Any, Optional, List, AsyncGenerator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from codebase_driven_agent.agent.utils import create_llm, get_tools
from codebase_driven_agent.agent.prompt import generate_system_prompt
from codebase_driven_agent.agent.session_manager import get_session_manager
from codebase_driven_agent.utils.logger import setup_logger
from codebase_driven_agent.utils.database import get_schema_info, format_schema_info
from codebase_driven_agent.config import settings

logger = setup_logger("codebase_driven_agent.agent.graph_executor")


class AgentState(TypedDict, total=False):
    """Agent 状态定义"""

    messages: Annotated[Sequence[operator.add], operator.add]
    plan_steps: List[Dict[str, Any]]
    current_step: int
    step_results: List[Dict[str, Any]]
    should_continue: bool
    original_input: str
    context_files: Optional[List[Dict[str, Any]]]
    decision: Optional[str]  # 决策结果：continue, synthesize, adjust_plan, request_input
    user_input_question: Optional[str]  # 用户输入请求的问题
    user_input_context: Optional[str]  # 用户输入请求的上下文
    request_id: Optional[str]  # 用户输入请求的 ID


class GraphExecutor:
    """基于 LangGraph 的 Agent 执行器

    实现特点：
    1. 使用 LangGraph 构建结构化的工作流
    2. 支持动态计划生成和调整
    3. 根据执行结果动态决定下一步
    4. 完整的步骤追踪和状态管理
    """

    def __init__(self, callbacks=None, message_queue: Optional[queue.Queue] = None, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.llm = create_llm()
        self.tools = get_tools()
        self.callbacks = callbacks or []
        self.tool_node = ToolNode(self.tools)
        self.message_queue = message_queue  # 使用线程安全的 queue.Queue
        self.event_loop = event_loop  # 保存事件循环引用
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 Agent 图结构

        图结构：
        plan -> execute_step -> decide -> (execute_step | synthesize | adjust_plan) -> end
        """
        graph = StateGraph(AgentState)

        # 添加节点
        graph.add_node("plan", self._plan_node)
        graph.add_node("execute_step", self._execute_step_node)
        graph.add_node("decide", self._decision_node)
        graph.add_node("synthesize", self._synthesize_node)
        graph.add_node("request_user_input", self._request_user_input_node)

        # 设置入口点
        graph.set_entry_point("plan")

        # 添加边
        graph.add_edge("plan", "execute_step")
        graph.add_edge("execute_step", "decide")

        # 条件边
        graph.add_conditional_edges(
            "decide",
            self._should_continue,
            {
                "continue": "execute_step",
                "adjust_plan": "plan",
                "synthesize": "synthesize",
                "request_input": "request_user_input",
                "end": END,
            },
        )

        graph.add_edge("synthesize", END)
        graph.add_edge("request_user_input", END)  # 请求用户输入后暂停，等待用户回复

        return graph.compile()

    def _plan_node(self, state: AgentState) -> Dict[str, Any]:
        """计划节点：生成或调整分析计划

        首次执行时生成初始计划，后续执行时根据结果调整计划
        """
        logger.info("Plan node: Generating or adjusting analysis plan")

        messages = state["messages"]
        step_results = state["step_results"]
        current_step = state["current_step"]

        # 构建计划生成的 prompt
        if not state["plan_steps"] or current_step == 0:
            # 首次生成计划
            plan_prompt = self._build_initial_plan_prompt(
                state["original_input"], state["context_files"]
            )
        else:
            # 根据已有结果调整计划
            plan_prompt = self._build_adjustment_plan_prompt(
                state["original_input"], step_results, state["plan_steps"], current_step
            )

        # 调用 LLM 生成计划
        from langchain_core.messages import HumanMessage, AIMessage

        messages.append(HumanMessage(content=plan_prompt))
        
        # 检查消息长度，如果超长则直接结束分析
        is_too_long, total_length = self._check_messages_length(messages, max_total_length=120000)
        if is_too_long:
            logger.warning(f"Plan node: Messages too long ({total_length} chars), forcing synthesize")
            return {"should_continue": False}

        response = self.llm.invoke(messages)
        messages.append(AIMessage(content=response.content))

        # 解析生成的计划
        new_plan = self._parse_plan(response.content)

        # 更新状态
        if not state["plan_steps"] or current_step == 0:
            plan_steps = new_plan
        else:
            # 保留已完成步骤，更新剩余步骤
            plan_steps = state["plan_steps"][:current_step] + new_plan

        logger.info(f"Plan node: Generated {len(plan_steps)} steps")

        # 立即通过消息队列发送 plan 消息（使用线程安全的 queue.Queue）
        if self.message_queue:
            try:
                # queue.Queue 是线程安全的，可以直接从任何线程 put
                self.message_queue.put_nowait({"event": "plan", "data": {"steps": plan_steps}})
                logger.info(f"Plan message queued: {len(plan_steps)} steps")
            except Exception as e:
                logger.error(f"Failed to queue plan message: {e}", exc_info=True)

        return {
            "plan_steps": plan_steps,
            "messages": messages,
            "current_step": 0 if not state["plan_steps"] else current_step,
        }

    def _execute_step_node(self, state: AgentState) -> Dict[str, Any]:
        """执行步骤节点：根据当前步骤选择工具并执行

        根据 plan_steps[current_step] 的 action 和 target 选择合适的工具
        """
        plan_steps = state["plan_steps"]
        current_step = state["current_step"]

        if current_step >= len(plan_steps):
            logger.warning(
                f"Execute step node: No step to execute (current_step={current_step}, total={len(plan_steps)})"
            )
            return {"should_continue": False}

        step = plan_steps[current_step]
        logger.info(
            f"Execute step node: Step {current_step + 1}/{len(plan_steps)} - {step.get('action')}"
        )

        # 根据步骤的 action 决定使用哪个工具
        tool_name = self._map_action_to_tool(step.get("action", ""))
        tool_input = self._build_tool_input(step, state)

        # 执行工具调用
        try:
            tool_result = self._call_tool_directly(tool_name, tool_input)

            # 保存结果
            step_result = {
                "step": current_step,
                "action": step.get("action"),
                "target": step.get("target"),
                "status": "completed",
                "result": tool_result,
            }

            logger.info(f"Execute step node: Step {current_step + 1} completed")

            # 立即通过消息队列发送进度更新和步骤执行结果
            if self.message_queue:
                try:
                    total_steps = len(plan_steps)
                    progress_msg = {
                        "event": "progress",
                        "data": {
                            "message": f"执行步骤 {current_step + 1}/{total_steps}",
                            "progress": (current_step + 1) / total_steps if total_steps > 0 else 0.5,
                            "step": "graph_execution",
                        }
                    }
                    # queue.Queue 是线程安全的
                    self.message_queue.put_nowait(progress_msg)
                    logger.info(f"Progress message queued: step {current_step + 1}/{total_steps}")
                    
                    # 发送步骤执行结果
                    step_execution_msg = {
                        "event": "step_execution",
                        "data": {
                            "step": current_step + 1,
                            "action": step.get("action"),
                            "target": step.get("target"),
                            "status": "completed",
                            "result": tool_result[:5000] if len(tool_result) > 5000 else tool_result,  # 限制结果长度
                            "result_truncated": len(tool_result) > 5000,
                        }
                    }
                    self.message_queue.put_nowait(step_execution_msg)
                    logger.info(f"Step execution result queued: step {current_step + 1}")
                except Exception as e:
                    logger.error(f"Failed to queue progress/step_execution message: {e}", exc_info=True)

            return {
                "step_results": state["step_results"] + [step_result],
                "current_step": current_step + 1,
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Execute step node: Step {current_step + 1} failed: {error_msg}", exc_info=True)

            # 保存失败结果（包含详细的错误信息，让 AI 能够分析失败原因）
            step_result = {
                "step": current_step,
                "action": step.get("action"),
                "target": step.get("target"),
                "status": "failed",
                "error": error_msg,
                "tool_name": tool_name,  # 记录使用的工具名称
                "tool_input": str(tool_input)[:200] if tool_input else None,  # 记录工具输入（截断）
            }

            # 即使工具调用失败，也继续执行流程，让 AI 决策下一步
            logger.info(f"Execute step node: Step {current_step + 1} failed, but continuing to decision node")
            
            # 发送失败步骤的执行结果
            if self.message_queue:
                try:
                    step_execution_msg = {
                        "event": "step_execution",
                        "data": {
                            "step": current_step + 1,
                            "action": step.get("action"),
                            "target": step.get("target"),
                            "status": "failed",
                            "error": error_msg[:1000] if len(error_msg) > 1000 else error_msg,  # 限制错误信息长度
                        }
                    }
                    self.message_queue.put_nowait(step_execution_msg)
                    logger.info(f"Failed step execution result queued: step {current_step + 1}")
                except Exception as e:
                    logger.error(f"Failed to queue failed step_execution message: {e}", exc_info=True)

            return {
                "step_results": state["step_results"] + [step_result],
                "current_step": current_step + 1,
            }

    def _decision_node(self, state: AgentState) -> Dict[str, Any]:
        """决策节点：基于 LLM 判断是否继续、添加新步骤或结束分析
        
        核心自适应逻辑：
        1. 评估已有的步骤结果
        2. 询问 LLM：信息是否足够？还是需要继续？
        3. 如果需要继续，LLM 决定下一步
        4. 动态扩展 plan，返回新步骤
        """
        step_results = state["step_results"]
        plan_steps = state["plan_steps"]
        current_step = state["current_step"]
        original_input = state["original_input"]

        logger.info(
            f"Decision node: current_step={current_step}/{len(plan_steps)}, results={len(step_results)}"
        )

        # 检查是否达到最大迭代次数
        if current_step >= settings.agent_max_iterations:
            logger.warning(
                f"Decision node: Max iterations ({settings.agent_max_iterations}) reached, forcing synthesize"
            )
            return {"should_continue": False}

        # 构建决策 prompt，让 LLM 判断下一步
        decision_prompt = self._build_adjustment_plan_prompt(
            original_input, step_results, plan_steps, current_step
        )

        # 调用 LLM 做决策
        from langchain_core.messages import HumanMessage, AIMessage

        messages = state["messages"] + [HumanMessage(content=decision_prompt)]
        
        # 检查消息长度，如果超长则直接结束分析
        is_too_long, total_length = self._check_messages_length(messages, max_total_length=120000)
        if is_too_long:
            logger.warning(f"Decision node: Messages too long ({total_length} chars), forcing synthesize")
            return {"should_continue": False, "messages": messages}
        
        try:
            response = self.llm.invoke(messages)
            messages.append(AIMessage(content=response.content))
            
            # 解析 LLM 的决策
            decision = self._parse_decision(response.content)
            
            action = decision.get("action", "synthesize")
            reasoning = decision.get("reasoning", "")
            next_steps = decision.get("next_steps", [])
            question = decision.get("question", "")
            context = decision.get("context", "")
            
            logger.info(f"Decision node: LLM decided to '{action}'. Reasoning: {reasoning[:200]}")
            logger.info(f"Decision node: Extracted {len(next_steps)} next steps")
            logger.info(f"Decision node: Parsed decision - action={action}, has_question={bool(question)}, question={question[:100] if question else 'N/A'}")
            logger.debug(f"Decision node: Full parsed decision: {decision}")
            
            if action == "request_input":
                # LLM 决定请求用户输入
                logger.info(f"Decision node: Requesting user input. Question: {question[:200]}")
                
                # 保存请求信息到状态中
                result_state = {
                    "should_continue": True,
                    "decision": "request_input",
                    "user_input_question": question,
                    "user_input_context": context,
                    "messages": messages,
                }
                logger.info(f"Decision node: Returning state with decision=request_input, keys: {list(result_state.keys())}")
                return result_state
            
            elif action == "continue":
                # LLM 决定继续，获取新步骤
                if not next_steps:
                    logger.warning("Decision node: LLM said continue but provided no steps")
                    logger.warning(f"Decision node: Full LLM response: {response.content[:500]}")
                    logger.warning("Decision node: Forcing synthesize due to missing next_steps")
                    return {"should_continue": False, "messages": messages}
                
                # 扩展 plan_steps
                updated_plan_steps = list(plan_steps)
                for new_step_data in next_steps:
                    step_number = len(updated_plan_steps) + 1
                    updated_plan_steps.append({
                        "step": step_number,
                        "action": new_step_data.get("action", "未知操作"),
                        "target": new_step_data.get("target", ""),
                    })
                
                logger.info(f"Decision node: Plan expanded from {len(plan_steps)} to {len(updated_plan_steps)} steps")
                
                # 发送更新后的 plan 和推理原因给前端
                if self.message_queue:
                    try:
                        # 发送推理原因（关联到当前步骤之后，新步骤之前）
                        # 推理原因应该显示在当前步骤（current_step）之后，新步骤（从 len(plan_steps)+1 开始）之前
                        self.message_queue.put_nowait({
                            "event": "decision_reasoning",
                            "data": {
                                "reasoning": reasoning,
                                "action": action,
                                "after_step": current_step,  # 在哪个步骤之后
                                "before_steps": [len(plan_steps) + i + 1 for i in range(len(next_steps))],  # 在哪些新步骤之前
                            }
                        })
                        logger.info(f"Decision node: Reasoning sent to frontend: after_step={current_step}, before_steps={[len(plan_steps) + i + 1 for i in range(len(next_steps))]}")
                        
                        # 发送更新后的 plan
                        self.message_queue.put_nowait({
                            "event": "plan",
                            "data": {"steps": updated_plan_steps}
                        })
                        logger.info(f"Decision node: Updated plan sent to frontend")
                    except Exception as e:
                        logger.error(f"Failed to queue updated plan/reasoning: {e}")
                
                return {
                    "should_continue": True,
                    "plan_steps": updated_plan_steps,
                    "messages": messages,
                }
            
            else:  # action == "synthesize"
                logger.info("Decision node: LLM decided to synthesize final result")
                return {"should_continue": False, "messages": messages}
                
        except Exception as e:
            logger.error(f"Decision node: Error during LLM decision: {e}", exc_info=True)
            logger.warning("Decision node: Falling back to synthesize due to error")
            return {"should_continue": False}

    def _request_user_input_node(self, state: AgentState) -> Dict[str, Any]:
        """请求用户输入节点：暂停执行，等待用户回复"""
        import uuid
        
        question = state.get("user_input_question", "")
        context = state.get("user_input_context", "")
        
        logger.info(f"Request user input node: Question: {question[:200]}")
        
        # 生成请求 ID
        request_id = str(uuid.uuid4())
        
        # 保存会话状态
        session_manager = get_session_manager()
        session_manager.create_session(
            state=state,
            executor=self,
            message_queue=self.message_queue,
            request_id=request_id
        )
        
        # 发送 user_input_request 事件到前端
        if self.message_queue:
            try:
                self.message_queue.put_nowait({
                    "event": "user_input_request",
                    "data": {
                        "request_id": request_id,
                        "question": question,
                        "context": context,
                    }
                })
                logger.info(f"Request user input node: Sent user_input_request event with request_id={request_id}")
            except Exception as e:
                logger.error(f"Failed to queue user_input_request message: {e}", exc_info=True)
        
        # 暂停执行（不返回 should_continue=False，因为用户回复后会继续）
        # 状态保持不变，等待用户回复
        return {
            "request_id": request_id,
        }
    
    def _synthesize_node(self, state: AgentState) -> Dict[str, Any]:
        """综合节点：整合所有步骤结果，生成最终分析结论

        1. 收集所有步骤的结果
        2. 提取关键信息（代码、日志、数据）
        3. 生成根本原因分析
        4. 提供处理建议
        """
        logger.info("Synthesize node: Generating final analysis")

        step_results = state["step_results"]
        original_input = state["original_input"]

        # 构建 prompt 用于生成最终结论
        synthesize_prompt = self._build_synthesize_prompt(
            original_input, step_results, state["context_files"]
        )

        # 调用 LLM 生成结论
        from langchain_core.messages import HumanMessage, AIMessage

        messages = state["messages"] + [HumanMessage(content=synthesize_prompt)]
        
        # 检查消息长度，如果超长则基于已有信息生成简化结果
        is_too_long, total_length = self._check_messages_length(messages, max_total_length=120000)
        if is_too_long:
            logger.warning(f"Synthesize node: Messages too long ({total_length} chars), generating simplified result based on available information")
            
            # 基于已有步骤结果生成简化结论
            final_result = self._generate_simplified_result(original_input, step_results)
            # 添加一条系统消息说明情况
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content="由于对话上下文过长，已基于已执行的步骤生成简化分析结果。"))
        else:
            # 发送进度消息，告知用户正在生成结果
            if self.message_queue:
                try:
                    self.message_queue.put_nowait({
                        "event": "progress",
                        "data": {
                            "message": "正在生成最终分析结果...",
                            "progress": 0.95,
                            "step": "synthesizing"
                        }
                    })
                    logger.info("Progress message queued: synthesizing")
                except Exception as e:
                    logger.warning(f"Failed to queue progress message: {e}")
            
            # 直接调用 LLM（调用方已经在线程池中执行此方法，所以这里不需要再次包装）
            # 这样可以避免双重线程池包装，提高性能
            response = self.llm.invoke(messages)
            
            messages.append(AIMessage(content=response.content))

            # 提取结构化结果
            final_result = self._parse_synthesis_result(response.content)

        logger.info("Synthesize node: Final analysis generated")

        # 立即通过消息队列发送 result 消息
        if self.message_queue:
            try:
                self.message_queue.put_nowait({"event": "result", "data": final_result})
                self.message_queue.put_nowait({"event": "done", "data": {"message": "Analysis completed"}})
                logger.info("Result and done messages queued")
            except Exception as e:
                logger.error(f"Failed to queue result message: {e}", exc_info=True)

        return {"messages": messages, "final_result": final_result}

    def _should_continue(self, state: AgentState) -> str:
        """判断下一步执行路径"""
        if not state["should_continue"]:
            logger.debug(f"_should_continue: should_continue=False, returning synthesize")
            return "synthesize"

        # 检查是否需要调整计划
        decision = state.get("decision")
        logger.debug(f"_should_continue: decision={decision}, state keys: {list(state.keys())}")
        
        if decision == "adjust_plan":
            logger.debug(f"_should_continue: returning adjust_plan")
            return "adjust_plan"
        
        # 检查是否需要请求用户输入
        if decision == "request_input":
            logger.info(f"_should_continue: decision=request_input, returning request_input")
            return "request_input"

        logger.debug(f"_should_continue: returning continue")
        return "continue"

    def _build_initial_plan_prompt(
        self, input_text: str, context_files: Optional[List[Dict]]
    ) -> str:
        """构建初始计划生成的 prompt - 只生成第一步"""
        tools_description = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

        prompt = f"""请分析以下问题，并制定**第一步**的分析计划（不要一次性规划所有步骤）。

用户问题：
{input_text}

可用工具：
{tools_description}

要求：
1. **只规划第一步**，不要试图一次性规划完整流程
2. 第一步应该是最关键的信息收集步骤（通常是代码搜索）
3. 步骤必须具体、可执行，明确指定搜索目标

**重要：**
- 如果使用 code_search 工具，target 字段必须是**实际的搜索字符串**（例如：错误信息、函数名、变量名等），而不是中文描述
- 如果用户输入包含错误信息，直接提取并使用该错误信息作为搜索字符串
- target 应该是可以直接在代码中搜索的字符串，而不是"定位错误信息"这样的描述
- 如果用户输入包含文件路径和行号（如 "file.py:42" 或 "file.py line 10-20"），可以在 target 中包含行号信息，系统会自动提取并只返回指定行的内容

示例：
- ✅ 正确：如果用户输入包含 "FileNotFoundError: config.json"，则步骤1: 使用 code_search 工具搜索代码仓库中包含 "FileNotFoundError" 或 "config.json" 的代码片段 - 定位错误信息对应的代码位置
- ✅ 正确：如果用户输入包含函数名 "processPayment"，则步骤1: 使用 code_search 工具搜索代码仓库中包含 "processPayment" 的函数定义 - 定位该函数的实现
- ✅ 正确：如果用户输入包含 "src/utils.py:10-50"，则步骤1: 使用 code_search 工具查看文件 src/utils.py:10-50 - 查看第10-50行的代码
- ❌ 错误：步骤1: 使用 code_search 工具搜索代码仓库 - [定位错误信息在代码中的具体位置，找到触发该错误的函数或逻辑分支]

请按照以下格式输出计划：
步骤1: [具体操作] - [预期目标]

其中，如果使用 code_search，操作中应包含实际的搜索字符串，target 字段也应该是该搜索字符串（可以包含行号范围）。"""

        if context_files:
            context_info = "\n".join(
                [
                    f"- {ctx.get('path', 'unknown')}: {ctx.get('content', '')[:200]}..."
                    for ctx in context_files
                ]
            )
            prompt += f"\n\n上下文文件：\n{context_info}"

        return prompt

    def _build_adjustment_plan_prompt(
        self,
        input_text: str,
        step_results: List[Dict],
        plan_steps: List[Dict],
        current_step: int,
    ) -> str:
        """根据已有结果，动态生成下一步计划"""
        tools_description = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

        # 格式化已执行步骤的结果（包含成功和失败的情况）
        executed_info = []
        for i, result in enumerate(step_results):
            step_info = plan_steps[i] if i < len(plan_steps) else {}
            action = step_info.get('action', 'unknown')
            status = result.get("status", "unknown")
            
            if status == "failed":
                # 工具调用失败：明确告诉 AI 失败的原因和上下文
                error = result.get("error", "未知错误")
                tool_name = result.get("tool_name", "未知工具")
                tool_input = result.get("tool_input", "N/A")
                executed_info.append(
                    f"步骤 {i + 1}: {action}\n"
                    f"状态: ❌ 失败\n"
                    f"使用的工具: {tool_name}\n"
                    f"工具输入: {tool_input}\n"
                    f"错误信息: {error[:500]}\n"
                    f"目标: {result.get('target', 'N/A')}\n"
                )
            else:
                # 成功的结果
                result_str = str(result.get('result', 'N/A'))
                if len(result_str) > 500:
                    executed_info.append(
                        f"步骤 {i + 1}: {action}\n"
                        f"状态: ✅ 成功\n"
                        f"结果摘要: {result_str[:500]}... (已截断)\n"
                    )
                else:
                    executed_info.append(
                        f"步骤 {i + 1}: {action}\n"
                        f"状态: ✅ 成功\n"
                        f"结果: {result_str}\n"
                    )

        # 检查是否有失败的步骤
        has_failed_steps = any(r.get("status") == "failed" for r in step_results)
        failed_info = ""
        if has_failed_steps:
            failed_info = "\n**注意：部分步骤执行失败。请分析失败原因，考虑是否需要：\n" \
                         "- 使用其他工具或方法重试\n" \
                         "- 调整搜索策略\n" \
                         "- 或者基于已有信息（包括失败信息）得出结论\n"

        prompt = f"""你是一个智能分析 Agent。请根据已执行步骤的结果，动态决定下一步。

原始问题：
{input_text}

已执行的步骤和结果：
{''.join(executed_info)}
{failed_info}
可用工具：
{tools_description}

**重要要求：**
1. 如果已有足够信息得出结论（包括基于失败信息可以推断的情况） → 回复 "action": "synthesize"，此时不需要 next_steps
2. 如果需要继续收集信息（包括工具调用失败后需要尝试其他方法） → **必须**回复 "action": "continue"，并且 **必须**提供 next_steps 数组，至少包含一个步骤
3. **如果选择 continue，next_steps 不能为空！** 必须明确指定下一步要执行的操作
4. **如果步骤失败，请分析失败原因，决定是重试、换方法，还是基于已有信息得出结论**
5. **如果发现信息不足，需要用户提供额外信息** → 回复 "action": "request_input"，并提供 "question" 字段说明需要什么信息以及为什么需要

**关键：使用 code_search 时的 target 字段规则：**
- target 必须是**实际的搜索字符串**（例如：错误信息、函数名、变量名等），而不是中文描述
- 如果原始问题包含错误信息，直接提取并使用该错误信息作为 target
- target 应该是可以直接在代码中搜索的字符串
- 如果用户输入包含文件路径和行号（如 "file.py:42" 或 "file.py line 10-20"），可以在 target 中包含行号信息，系统会自动提取并只返回指定行的内容，减少上下文

示例：
- ✅ 正确（continue）：如果用户输入包含 "FileNotFoundError"，则 {{"action": "continue", "reasoning": "...", "next_steps": [{{"step": 2, "action": "使用 code_search 工具搜索代码仓库中包含 'FileNotFoundError' 的代码片段", "target": "FileNotFoundError"}}]}}
- ✅ 正确（continue）：如果用户输入包含函数名 "processPayment"，则 {{"action": "continue", "reasoning": "...", "next_steps": [{{"step": 2, "action": "使用 code_search 工具搜索代码仓库中包含 'processPayment' 的函数定义", "target": "processPayment"}}]}}
- ✅ 正确（request_input）：如果用户输入非常模糊（如"我的代码出错了"），缺少关键信息，则 {{"action": "request_input", "reasoning": "用户问题缺少具体的错误信息，无法进行有效分析", "question": "请提供具体的错误信息，包括：1) 错误类型（如 FileNotFoundError、ValueError 等）2) 错误消息 3) 相关的文件路径和行号（如果有）", "context": "当前只有模糊的问题描述，需要更多信息才能定位问题"}}
- ❌ 错误：{{"action": "使用 code_search 工具搜索代码仓库", "target": "[定位错误信息在代码中的具体位置]"}}

请严格按照以下JSON格式回复（不要添加任何其他文本）：
```json
{{
  "action": "continue" 或 "synthesize" 或 "request_input",
  "reasoning": "决策理由（说明为什么选择继续、结束或请求用户输入）",
  "question": "如果需要用户输入，说明需要什么信息以及为什么需要（仅在 action 为 request_input 时需要）",
  "context": "可选的上下文信息，帮助用户理解为什么需要这个信息（仅在 action 为 request_input 时可选）",
  "next_steps": [
    {{
      "step": {current_step + 1},
      "action": "具体操作描述（如果使用 code_search，应包含实际的搜索字符串，例如：使用 code_search 工具搜索代码仓库中包含 'FileNotFoundError' 的代码片段）",
      "target": "实际的搜索字符串（如果使用 code_search，必须是可以在代码中直接搜索的字符串，例如：'FileNotFoundError'、'processPayment' 或 'src/utils.py:10-50'，而不是中文描述）"
    }}
  ]
}}
```

**注意：**
- 如果 action 是 "continue"，next_steps 必须是一个非空数组
- 如果 action 是 "synthesize"，next_steps 可以为空数组或省略
- 如果 action 是 "request_input"，必须提供 question 字段，context 字段可选，next_steps 可以为空（用户回复后再决定下一步）
- **如果使用 code_search，target 必须是实际的搜索字符串，不是中文描述！**
- **如果查看文件，可以在文件路径后添加行号范围（如 'file.py:10-50'），减少返回的上下文**
- 请确保 JSON 格式正确，可以直接被解析"""

        return prompt

    def _build_synthesize_prompt(
        self, input_text: str, step_results: List[Dict], context_files: Optional[List[Dict]]
    ) -> str:
        """构建最终综合分析的 prompt"""
        prompt = f"""基于以下步骤的执行结果，生成最终的分析结论。

用户问题：
{input_text}

执行步骤及结果：
{self._format_all_step_results(step_results)}

"""

        if context_files:
            context_info = "\n".join(
                [
                    f"- {ctx.get('path', 'unknown')}: {ctx.get('content', '')[:200]}..."
                    for ctx in context_files
                ]
            )
            prompt += f"\n上下文文件：\n{context_info}"

        prompt += """

请以以下 JSON 格式输出分析结果：
```json
{
  "root_cause": "问题的根本原因分析（必须包含：错误发生的具体位置、为什么会出现这个错误、根本原因是什么）",
  "suggestions": [
    "建议1：...",
    "建议2：...",
    "建议3：..."
  ],
  "confidence": 0.85,
  "related_code": [
    {
      "file": "path/to/file.py",
      "lines": [10, 20],
      "description": "相关代码说明（必须包含：这段代码与错误的关系、为什么会导致错误）"
    }
  ],
  "related_logs": [
    {
      "timestamp": "2024-01-01 10:00:00",
      "content": "日志内容",
      "description": "日志说明（必须包含：这条日志说明了什么问题、与代码的关联）"
    }
  ]
}
```"""

        return prompt

    def _map_action_to_tool(self, action: str) -> str:
        """将计划步骤的 action 映射到工具名称"""
        action_lower = action.lower()

        if "代码" in action_lower or "code" in action_lower or "文件" in action_lower:
            return "code_search"
        elif "日志" in action_lower or "log" in action_lower:
            return "log_search"
        elif "数据库" in action_lower or "database" in action_lower or "db" in action_lower:
            return "database_query"
        else:
            # 默认使用代码搜索
            return "code_search"

    def _build_tool_input(self, step: Dict, state: AgentState) -> Dict[str, Any]:
        """根据步骤和当前状态构建工具输入"""
        action = step.get("action", "")
        target = step.get("target", "")
        step_results = state["step_results"]
        original_input = state.get("original_input", "")

        # 如果是代码搜索，尝试从之前的步骤结果中提取相关信息
        if self._map_action_to_tool(action) == "code_search":
            if target:
                query = target
                # 如果 target 是中文描述，尝试从原始输入中提取实际的错误字符串
                if self._is_chinese_description(query):
                    extracted_query = self._extract_error_string_from_input(original_input)
                    if extracted_query:
                        logger.info(f"Extracted error string from input: {extracted_query}, using it instead of Chinese description")
                        query = extracted_query
            else:
                # 如果没有明确的目标，从之前的结果中提取
                query = self._extract_query_from_results(step_results)
                if not query:
                    # 如果还是找不到，尝试从原始输入中提取
                    query = self._extract_error_string_from_input(original_input) or "error"
            
            # 从查询中提取行号范围（如果包含）
            line_start, line_end = self._extract_line_range_from_query(query)
            
            # 如果提取到行号，清理 query（移除行号部分），保留文件路径
            clean_query = query
            search_type = "auto"  # 初始化搜索类型
            if line_start:
                import re
                # 移除行号部分，保留文件路径
                clean_query = re.sub(r':\d+(?:[-:]?\d+)?', '', query)
                clean_query = re.sub(r'\s+line[s]?\s+\d+(?:\s*[-–]\s*\d+)?', '', clean_query, flags=re.IGNORECASE)
                clean_query = clean_query.strip()
                # 如果清理后的 query 看起来像文件路径，设置 search_type 为 "file"
                if clean_query.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.h', '.c', '.hpp', '.go', '.rs')) or '/' in clean_query or '\\' in clean_query:
                    search_type = "file"
            
            # 从 action 中推断搜索类型（如果还没有设置）
            if search_type == "auto":
                action_lower = action.lower()
                if "函数" in action or "function" in action_lower:
                    search_type = "function"
                elif "类" in action or "class" in action_lower:
                    search_type = "class"
                elif "变量" in action or "variable" in action_lower:
                    search_type = "variable"
                elif "字符串" in action or "string" in action_lower:
                    search_type = "string"
                elif "文件" in action or "file" in action_lower or clean_query.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.h')):
                    search_type = "file"

            return {
                "query": clean_query, 
                "search_type": search_type,
                "line_start": line_start,
                "line_end": line_end,
                "max_results": 10, 
                "include_context": True
            }

        # 日志搜索
        if self._map_action_to_tool(action) == "log_search":
            return {"query": target or "error OR exception", "time_range": "1h"}

        # 数据库查询
        if self._map_action_to_tool(action) == "database_query":
            return {"query": target or "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100"}

        return {"query": target}

    def _call_tool_directly(self, tool_name: str, tool_input: Dict) -> str:
        """直接调用工具（不通过 ToolNode）"""
        for tool in self.tools:
            if tool.name == tool_name:
                logger.info(f"Calling tool: {tool_name} with input: {tool_input}")

                # 根据工具类型调用不同的方法
                if hasattr(tool, "_run"):
                    result = tool._run(**tool_input)
                else:
                    # 兼容旧版本
                    from langchain_core.tools import BaseTool

                    if isinstance(tool, BaseTool):
                        result = tool.run(tool_input)
                    else:
                        result = str(tool.invoke(tool_input))

                return str(result)

        raise ValueError(f"Tool not found: {tool_name}")

    def _parse_plan(self, plan_text: str) -> List[Dict[str, Any]]:
        """解析 LLM 生成的计划文本"""
        import re
        steps = []
        
        # 首先尝试从 JSON 中提取 next_steps
        try:
            json_match = re.search(r'"next_steps"\s*:\s*\[([\s\S]*?)\]', plan_text)
            if json_match:
                # 尝试解析 next_steps 数组
                next_steps_str = json_match.group(0)
                # 提取完整的 JSON 对象
                full_json_match = re.search(r'\{[\s\S]*"next_steps"[\s\S]*?\}', plan_text)
                if full_json_match:
                    parsed = json.loads(full_json_match.group(0))
                    if "next_steps" in parsed and isinstance(parsed["next_steps"], list):
                        for step_data in parsed["next_steps"]:
                            if isinstance(step_data, dict):
                                steps.append({
                                    "step": step_data.get("step", len(steps) + 1),
                                    "action": step_data.get("action", ""),
                                    "target": step_data.get("target", ""),
                                    "status": "pending"
                                })
                        if steps:
                            return steps
        except:
            pass
        
        # 如果 JSON 解析失败，尝试从文本中提取
        lines = plan_text.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配 "步骤N: 操作 - 目标" 格式
            step_pattern = r"步骤\s*(\d+)\s*[:：]\s*(.+?)(?:\s*-\s*(.+))?$"
            match = re.match(step_pattern, line)

            if match:
                step_num = int(match.group(1))
                action = match.group(2).strip()
                target = match.group(3).strip() if match.group(3) else ""

                steps.append(
                    {"step": step_num, "action": action, "target": target, "status": "pending"}
                )
            else:
                # 尝试匹配 "action": "xxx", "target": "xxx" 格式（从 JSON 片段中提取）
                action_match = re.search(r'"action"\s*:\s*"([^"]+)"', line)
                target_match = re.search(r'"target"\s*:\s*"([^"]+)"', line)
                if action_match:
                    action = action_match.group(1)
                    target = target_match.group(1) if target_match else ""
                    steps.append({
                        "step": len(steps) + 1,
                        "action": action,
                        "target": target,
                        "status": "pending"
                    })

        return steps

    def _parse_decision(self, llm_response: str) -> Dict[str, Any]:
        """解析 LLM 的决策响应"""
        import re
        
        def extract_json_from_text(text: str) -> Dict[str, Any] | None:
            """从文本中提取 JSON 对象（支持嵌套结构）"""
            # 方式1：从 ```json ``` 代码块中提取
            json_match = re.search(r"```json\s*(\{[\s\S]*\})\s*```", text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 方式2：从 ``` ``` 代码块中提取（不带 json 标签）
            json_match = re.search(r"```\s*(\{[\s\S]*\})\s*```", text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 方式3：找到第一个 { 和最后一个 } 之间的内容（平衡括号）
            first_brace = text.find('{')
            if first_brace == -1:
                return None
            
            # 从第一个 { 开始，找到匹配的最后一个 }
            brace_count = 0
            last_brace = first_brace
            for i in range(first_brace, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_brace = i
                        break
            
            if brace_count == 0 and last_brace > first_brace:
                json_str = text[first_brace:last_brace + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            return None
        
        # 尝试提取 JSON
        parsed_json = extract_json_from_text(llm_response)
        if parsed_json:
            action = parsed_json.get("action", "").lower()
            reasoning = parsed_json.get("reasoning", "")
            next_steps = parsed_json.get("next_steps", [])
            
            # 验证 action
            if action == "synthesize":
                return {
                    'action': 'synthesize',
                    'reasoning': reasoning or llm_response[:200],
                    'next_steps': []
                }
            elif action == "request_input":
                # 如果 action 是 request_input，必须提供 question
                question = parsed_json.get('question', '')
                context = parsed_json.get('context', '')
                logger.info(f"[_parse_decision] Parsed request_input - question length: {len(question)}, question: {question[:200] if question else 'EMPTY'}")
                logger.debug(f"[_parse_decision] Full parsed_json keys: {list(parsed_json.keys())}")
                if not question:
                    logger.warning(f"[_parse_decision] LLM returned 'request_input' but question is empty. Full response: {llm_response[:1000]}")
                    logger.warning(f"[_parse_decision] Parsed JSON: {parsed_json}")
                    # 如果没有 question，尝试从 reasoning 中提取，或者生成一个默认问题
                    # 如果 reasoning 包含有用的信息，可以基于它生成问题
                    if reasoning:
                        # 尝试从 reasoning 中提取问题
                        question = f"根据您的描述，我需要更多信息来帮助分析问题。{reasoning[:200]}"
                        logger.info(f"[_parse_decision] Generated question from reasoning: {question[:200]}")
                    else:
                        # 回退到 synthesize
                        return {
                            'action': 'synthesize',
                            'reasoning': llm_response[:200],
                            'next_steps': []
                        }
                return {
                    'action': 'request_input',
                    'reasoning': reasoning or llm_response[:200],
                    'question': question,
                    'context': context,
                    'next_steps': next_steps if next_steps else []
                }
            elif action == "continue":
                # 如果 action 是 continue，必须提供 next_steps
                if not next_steps or len(next_steps) == 0:
                    logger.warning(f"[_parse_decision] LLM returned 'continue' but next_steps is empty. Full response: {llm_response[:500]}")
                    # 尝试从文本中解析步骤
                    steps = self._parse_plan(llm_response)
                    if steps:
                        logger.info(f"[_parse_decision] Extracted {len(steps)} steps from text fallback")
                        return {
                            'action': 'continue',
                            'reasoning': reasoning or llm_response[:200],
                            'next_steps': steps
                        }
                    else:
                        # 如果还是无法提取，返回空数组（会被上层处理）
                        return {
                            'action': 'continue',
                            'reasoning': reasoning or llm_response[:200],
                            'next_steps': []
                        }
                else:
                    return {
                        'action': 'continue',
                        'reasoning': reasoning or llm_response[:200],
                        'next_steps': next_steps
                    }
        
        # 如果无法解析 JSON，使用文本分析作为后备
        logger.warning(f"[_parse_decision] Failed to parse JSON, falling back to text analysis. Response: {llm_response[:300]}")
        llm_lower = llm_response.lower()
        if 'synthesize' in llm_lower or '足够' in llm_response or '结束' in llm_response:
            return {'action': 'synthesize', 'reasoning': llm_response[:200], 'next_steps': []}
        else:
            # 默认继续，尝试从文本中提取步骤
            steps = self._parse_plan(llm_response)
            return {
                'action': 'continue',
                'reasoning': llm_response[:200],
                'next_steps': steps if steps else []
            }

    def _parse_synthesis_result(self, result_text: str) -> Dict[str, Any]:
        """解析综合分析的结果"""
        import re
        
        logger.info(f"[_parse_synthesis_result] Input text (first 200 chars): {result_text[:200]}")
        
        def clean_json_string(s: str) -> str:
            """清理 JSON 字符串中的控制字符"""
            # 替换未转义的控制字符（保留已转义的 \n, \t 等）
            # 这里我们将实际的换行符替换为 \\n，制表符替换为 \\t
            result = []
            i = 0
            in_string = False
            while i < len(s):
                c = s[i]
                if c == '"' and (i == 0 or s[i-1] != '\\'):
                    in_string = not in_string
                    result.append(c)
                elif in_string and c == '\n':
                    result.append('\\n')
                elif in_string and c == '\r':
                    result.append('\\r')
                elif in_string and c == '\t':
                    result.append('\\t')
                elif in_string and ord(c) < 32 and c not in '\n\r\t':
                    # 其他控制字符用空格替换
                    result.append(' ')
                else:
                    result.append(c)
                i += 1
            return ''.join(result)
        
        def try_parse_json(json_str: str) -> Dict[str, Any] | None:
            """尝试解析 JSON，包括清理控制字符"""
            # 首先尝试直接解析
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            # 尝试清理后解析
            try:
                cleaned = clean_json_string(json_str)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # 尝试使用 strict=False（允许某些控制字符）
            try:
                return json.loads(json_str, strict=False)
            except json.JSONDecodeError:
                pass
            
            return None
        
        # 尝试多种方式提取 JSON
        
        # 方式1：从 ```json ``` 代码块中提取
        json_match = re.search(r"```json\s*(\{[\s\S]*\})\s*```", result_text)
        if json_match:
            logger.info("[_parse_synthesis_result] Found ```json code block")
            parsed = try_parse_json(json_match.group(1))
            if parsed:
                logger.info(f"[_parse_synthesis_result] Successfully parsed JSON, root_cause: {str(parsed.get('root_cause', ''))[:100]}")
                return parsed
            else:
                logger.warning("[_parse_synthesis_result] Failed to parse ```json code block")
        
        # 方式2：从 ``` ``` 代码块中提取（不带 json 标签）
        json_match = re.search(r"```\s*(\{[\s\S]*\})\s*```", result_text)
        if json_match:
            parsed = try_parse_json(json_match.group(1))
            if parsed:
                logger.info("[_parse_synthesis_result] Successfully parsed from ``` code block")
                return parsed
        
        # 方式3：直接查找 JSON 对象（以 { 开头，以 } 结尾）
        first_brace = result_text.find('{')
        last_brace = result_text.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            json_str = result_text[first_brace:last_brace + 1]
            parsed = try_parse_json(json_str)
            if parsed:
                logger.info("[_parse_synthesis_result] Successfully parsed from brace extraction")
                return parsed

        # 如果无法解析 JSON，返回原始文本
        logger.warning("[_parse_synthesis_result] Could not parse JSON, returning raw text as root_cause")
        return {
            "root_cause": result_text,
            "suggestions": [],
            "confidence": 0.5,
            "related_code": [],
            "related_logs": [],
        }
    
    def _generate_simplified_result(self, input_text: str, step_results: List[Dict]) -> Dict[str, Any]:
        """当 prompt 超长时，基于已有步骤结果生成简化结论
        
        即使上下文过长，也尝试调用 LLM 进行总结，而不是直接拼接工具输出。
        
        Args:
            input_text: 原始输入
            step_results: 已执行的步骤结果列表
        
        Returns:
            简化的分析结果
        """
        logger.info("Generating simplified result due to prompt length limit")
        
        # 统计成功和失败的步骤
        successful_steps = [r for r in step_results if r.get("status") == "completed"]
        failed_steps = [r for r in step_results if r.get("status") == "failed"]
        
        # 提取关键信息摘要（限制长度，用于构建简短的 prompt）
        key_findings = []
        for step in successful_steps[:5]:  # 最多取前5个步骤
            action = step.get('action', '')
            result_str = str(step.get("result", ""))
            # 提取关键信息：文件路径、行号、错误信息等
            import re
            # 提取文件路径和行号
            file_match = re.search(r'([\w/\\]+\.(?:py|js|ts|java|cpp|h|c|hpp|go|rs))[:\s]+Line\s+(\d+)', result_str)
            if file_match:
                file_path = file_match.group(1)
                line_num = file_match.group(2)
                key_findings.append(f"- {action}: 在 {file_path} 第 {line_num} 行")
            else:
                # 如果没有文件路径，提取前100个字符
                summary = result_str[:100].replace('\n', ' ').strip()
                if summary:
                    key_findings.append(f"- {action}: {summary}...")
        
        # 构建简短的 prompt，只包含关键信息
        simplified_prompt = f"""基于以下执行步骤的结果，分析问题的根本原因并提供修复建议。

原始问题：
{input_text[:500]}

执行步骤摘要：
{chr(10).join(key_findings[:10])}  # 最多10条

请以以下 JSON 格式输出分析结果（即使信息不完整，也要基于已有信息进行分析）：
```json
{{
  "root_cause": "问题的根本原因分析（基于已执行的步骤，说明：1) 错误发生的具体位置 2) 为什么会出现这个错误 3) 根本原因是什么。即使信息不完整，也要给出合理的分析）",
  "suggestions": [
    "建议1：...",
    "建议2：..."
  ],
  "confidence": 0.4
}}
```

注意：
- 即使信息不完整，也要基于已有步骤结果进行分析
- 根因分析应该是结构化的、易于理解的叙述，而不是工具输出的简单拼接
- 使用 Markdown 格式（如列表、代码块）来组织信息
- 如果某些关键信息缺失，在分析中明确说明"""
        
        try:
            # 尝试调用 LLM 进行总结（使用简短的 prompt）
            from langchain_core.messages import HumanMessage
            messages = [HumanMessage(content=simplified_prompt)]
            response = self.llm.invoke(messages)
            
            # 解析 LLM 响应
            final_result = self._parse_synthesis_result(response.content)
            
            # 如果解析失败，使用默认格式
            if not final_result.get("root_cause"):
                raise ValueError("Failed to parse LLM response")
            
            # 添加说明，降低置信度
            final_result["confidence"] = min(final_result.get("confidence", 0.4), 0.4)
            if "由于对话上下文过长" not in final_result.get("root_cause", ""):
                final_result["root_cause"] = "⚠️ **注意**：由于对话上下文过长，以下分析基于已执行步骤的摘要信息。\n\n" + final_result.get("root_cause", "")
            
            logger.info("Successfully generated simplified result using LLM")
            return final_result
            
        except Exception as e:
            logger.warning(f"Failed to generate simplified result using LLM: {str(e)}, falling back to basic summary")
            
            # Fallback: 如果 LLM 调用失败，生成基本的摘要
            root_cause_parts = []
            suggestions = []
            
            if failed_steps:
                root_cause_parts.append(f"⚠️ 部分步骤执行失败（{len(failed_steps)}/{len(step_results)}），可能影响分析的完整性。")
                suggestions.append("建议：重新运行分析，或尝试更具体的搜索条件。")
            
            if successful_steps:
                root_cause_parts.append("## 已执行的步骤摘要\n\n")
                for i, step in enumerate(successful_steps[:5], 1):
                    action = step.get('action', '')
                    result_str = str(step.get("result", ""))
                    # 提取关键信息
                    import re
                    file_match = re.search(r'([\w/\\]+\.(?:py|js|ts|java|cpp|h|c|hpp|go|rs))[:\s]+Line\s+(\d+)', result_str)
                    if file_match:
                        file_path = file_match.group(1)
                        line_num = file_match.group(2)
                        root_cause_parts.append(f"{i}. **{action}**: 在 `{file_path}` 第 {line_num} 行")
                    else:
                        summary = result_str[:150].replace('\n', ' ').strip()
                        if summary:
                            root_cause_parts.append(f"{i}. **{action}**: {summary}...")
            
            # 构建根因分析
            if root_cause_parts:
                root_cause = "⚠️ **注意**：由于对话上下文过长，以下分析基于已执行步骤的摘要信息。\n\n" + "\n\n".join(root_cause_parts)
            else:
                root_cause = "由于对话上下文过长，无法生成完整分析。建议重新运行分析或使用更具体的查询条件。"
            
            # 如果没有建议，添加默认建议
            if not suggestions:
                suggestions = [
                    "建议：重新运行分析，使用更具体的查询条件以减少上下文长度。",
                    "建议：分步骤分析，先解决部分问题，再逐步深入。",
                ]
            
            return {
                "root_cause": root_cause,
                "suggestions": suggestions,
                "confidence": 0.3,  # 降低置信度，因为这是简化结果
                "related_code": [],
                "related_logs": [],
            }

    def _has_enough_information(self, state: AgentState) -> bool:
        """判断是否已经有足够的信息来解决问题"""
        step_results = state["step_results"]

        # 如果有代码搜索结果，且有成功的结果
        has_code_result = any(
            "code" in r.get("action", "").lower() and r.get("status") == "completed"
            for r in step_results
        )

        # 如果有日志结果
        has_log_result = any(
            "log" in r.get("action", "").lower() and r.get("status") == "completed"
            for r in step_results
        )

        # 如果同时有代码和日志结果，可以认为有足够的信息
        if has_code_result and has_log_result:
            return True

        # 如果只有代码结果，但问题看起来很简单
        if has_code_result and len(step_results) >= 2:
            return True

        return False

    def _extract_query_from_results(self, step_results: List[Dict]) -> str:
        """从已有结果中提取查询关键词"""
        for result in step_results:
            if result.get("status") == "completed":
                content = result.get("result", "")
                # 提取文件名、错误信息等关键词
                import re

                if match := re.search(r'File\s+"([^"]+)"', content):
                    return match.group(1)
                if match := re.search(r"error:\s*(.+)", content, re.IGNORECASE):
                    return match.group(1)

        return "error"
    
    def _is_chinese_description(self, text: str) -> bool:
        """判断文本是否是中文描述（而不是实际的错误字符串）"""
        if not text:
            return False
        
        # 如果包含中文字符，且长度较长，可能是中文描述
        import re
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        is_long = len(text) > 30
        
        # 如果包含常见的描述性词汇，更可能是描述
        description_keywords = ['定位', '找到', '搜索', '查询', '分析', '获取', '提取', '确认']
        has_keywords = any(keyword in text for keyword in description_keywords)
        
        return has_chinese and (is_long or has_keywords)
    
    def _extract_error_string_from_input(self, input_text: str) -> str:
        """从原始输入中提取实际的错误字符串"""
        if not input_text:
            return ""
        
        import re
        
        # 尝试提取引号中的字符串（可能是错误信息）
        # 匹配单引号或双引号中的内容
        quoted_strings = re.findall(r'["\']([^"\']+)["\']', input_text)
        for quoted in quoted_strings:
            # 如果包含英文和常见错误关键词，可能是错误信息
            if re.search(r'[a-zA-Z]', quoted) and len(quoted) > 10:
                # 检查是否包含常见的错误关键词
                error_keywords = ['error', 'fail', 'exception', 'no', 'not found', 'missing', 'tag', 'when']
                if any(keyword.lower() in quoted.lower() for keyword in error_keywords):
                    return quoted
        
        # 尝试提取日志格式的错误信息（例如：no targetStrategy tag when determinePerf）
        # 匹配类似 "no ... when ..." 的模式
        error_patterns = [
            r'no\s+\w+\s+\w+.*when\s+\w+',  # no targetStrategy tag when determinePerf
            r'error:\s*([^\n]+)',  # error: ...
            r'Error:\s*([^\n]+)',  # Error: ...
            r'failed\s+to\s+([^\n]+)',  # failed to ...
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                error_str = match.group(1) if match.lastindex else match.group(0)
                if len(error_str.strip()) > 5:
                    return error_str.strip()
        
        return ""
    
    def _extract_line_range_from_query(self, query: str) -> tuple[Optional[int], Optional[int]]:
        """从查询中提取行号范围
        
        支持的格式：
        - "file.py:10" -> (10, None)
        - "file.py:10-20" -> (10, 20)
        - "file.py:10:20" -> (10, 20)
        - "file.py line 10" -> (10, None)
        - "file.py lines 10-20" -> (10, 20)
        """
        import re
        
        # 匹配 file.py:10 或 file.py:10-20 格式
        match = re.search(r':(\d+)(?:[-:](\d+))?', query)
        if match:
            line_start = int(match.group(1))
            line_end = int(match.group(2)) if match.group(2) else None
            return line_start, line_end
        
        # 匹配 "line 10" 或 "lines 10-20" 格式
        match = re.search(r'line[s]?\s+(\d+)(?:\s*[-–]\s*(\d+))?', query, re.IGNORECASE)
        if match:
            line_start = int(match.group(1))
            line_end = int(match.group(2)) if match.group(2) else None
            return line_start, line_end
        
        return None, None

    def _format_step_results(self, steps: List[Dict], results: List[Dict]) -> str:
        """格式化步骤结果"""
        formatted = []
        for step, result in zip(steps, results):
            status_icon = "✓" if result.get("status") == "completed" else "✗"
            formatted.append(f"{status_icon} {step.get('action')} - {step.get('target', '')}")
            if result.get("status") == "failed":
                formatted.append(f"  错误: {result.get('error', '')}")

        return "\n".join(formatted)

    def _format_all_step_results(self, results: List[Dict], max_length_per_result: int = 1000) -> str:
        """格式化所有步骤结果，包含成功和失败的情况"""
        formatted = []
        for i, result in enumerate(results, 1):
            status = result.get("status", "unknown")
            status_icon = "✓" if status == "completed" else "✗"
            action = result.get('action', '未知操作')
            formatted.append(f"{status_icon} 步骤 {i}: {action}")
            
            # 显示失败信息（重要：让 AI 知道工具调用失败的原因）
            if status == "failed":
                error = result.get("error", "未知错误")
                formatted.append(f"  状态: 失败")
                formatted.append(f"  错误信息: {error[:500]}")  # 限制错误信息长度
                formatted.append(f"  目标: {result.get('target', 'N/A')}")
            elif result.get("result"):
                # 成功的结果，截断过长的内容
                result_str = str(result.get('result'))
                if len(result_str) > max_length_per_result:
                    formatted.append(f"  结果: {result_str[:max_length_per_result]}... (已截断，原始长度: {len(result_str)} 字符)")
                else:
                    formatted.append(f"  结果: {result_str}")

        return "\n".join(formatted)

    def _format_plan_steps(self, steps: List[Dict]) -> str:
        """格式化计划步骤"""
        return "\n".join(
            [f"步骤 {s.get('step')}: {s.get('action')} - {s.get('target', '')}" for s in steps]
        )
    
    def _truncate_prompt_if_needed(self, prompt: str, max_length: int = 120000) -> str:
        """如果 prompt 超过最大长度，进行截断
        
        Args:
            prompt: 原始 prompt
            max_length: 最大长度（默认 120000，留一些余量）
        
        Returns:
            截断后的 prompt
        """
        if len(prompt) <= max_length:
            return prompt
        
        logger.warning(f"Prompt too long ({len(prompt)} chars), truncating to {max_length} chars")
        
        # 尝试智能截断：保留开头和结尾的重要部分
        # 开头保留 60%，结尾保留 40%
        header_length = int(max_length * 0.6)
        footer_length = max_length - header_length
        
        truncated = prompt[:header_length] + "\n\n[... 中间内容已截断 ...]\n\n" + prompt[-footer_length:]
        
        logger.info(f"Prompt truncated: {len(truncated)} chars")
        return truncated
    
    def _check_messages_length(self, messages: List, max_total_length: int = 120000) -> tuple[bool, int]:
        """检查消息列表的总长度是否超过限制
        
        Args:
            messages: LangChain 消息列表
            max_total_length: 最大总长度
        
        Returns:
            (是否超长, 总长度)
        """
        total_length = sum(len(str(msg.content)) for msg in messages if hasattr(msg, 'content'))
        is_too_long = total_length > max_total_length
        return is_too_long, total_length
    
    def _truncate_messages_if_needed(self, messages: List, max_total_length: int = 120000) -> List:
        """如果消息列表的总长度超过限制，截断最长的消息
        
        注意：当前策略是如果超长则直接结束分析，此函数暂时保留但不会被调用
        后续优化时可以用于压缩对话 context
        
        Args:
            messages: LangChain 消息列表
            max_total_length: 最大总长度
        
        Returns:
            截断后的消息列表
        """
        # 计算总长度
        total_length = sum(len(str(msg.content)) for msg in messages if hasattr(msg, 'content'))
        
        if total_length <= max_total_length:
            return messages
        
        logger.warning(f"Messages total length ({total_length} chars) exceeds limit ({max_total_length}), truncating")
        
        # 找到最长的消息并截断
        truncated_messages = []
        remaining_length = max_total_length
        
        for msg in messages:
            if not hasattr(msg, 'content'):
                truncated_messages.append(msg)
                continue
            
            content = str(msg.content)
            msg_length = len(content)
            
            if remaining_length > msg_length:
                # 消息可以完整保留
                truncated_messages.append(msg)
                remaining_length -= msg_length
            else:
                # 需要截断这条消息
                if remaining_length > 1000:  # 至少保留一些内容
                    truncated_content = content[:remaining_length] + "\n[... 内容已截断 ...]"
                    # 创建新消息对象（保持类型）
                    from langchain_core.messages import HumanMessage, AIMessage
                    if isinstance(msg, HumanMessage):
                        truncated_messages.append(HumanMessage(content=truncated_content))
                    elif isinstance(msg, AIMessage):
                        truncated_messages.append(AIMessage(content=truncated_content))
                    else:
                        truncated_messages.append(msg)
                    remaining_length = 0
                else:
                    logger.warning(f"Skipping message due to length limit")
                    break
        
        return truncated_messages

    async def run(
        self,
        input_text: str,
        context_files: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行图式 Agent

        Args:
            input_text: 用户输入
            context_files: 上下文文件列表

        Yields:
            包含进度、计划、结果的字典
        """
        logger.info(f"GraphExecutor: Starting execution for input: {input_text[:100]}...")

        # 初始状态
        initial_state: AgentState = {
            "messages": [],
            "plan_steps": [],
            "current_step": 0,
            "step_results": [],
            "should_continue": True,
            "original_input": input_text,
            "context_files": context_files,
        }

        # 流式执行图
        async for state in self.graph.astream(initial_state):
            logger.info(f"GraphExecutor state update: keys={list(state.keys())}, has_plan_steps={bool(state.get('plan_steps'))}")
            
            # 检查状态变化，发送进度更新
            if state.get("plan_steps"):
                plan_steps = state["plan_steps"]
                # 检查是否是新的 plan 或更新的 plan
                if plan_steps != initial_state.get("plan_steps", []):
                    logger.info(f"Yielding plan with {len(plan_steps)} steps: {plan_steps}")
                    yield {"event": "plan", "data": {"steps": plan_steps}}
                    # 更新 initial_state 以避免重复发送
                    initial_state["plan_steps"] = plan_steps
                else:
                    logger.debug(f"Plan unchanged, skipping: {len(plan_steps)} steps")

            if state.get("step_results") and state["step_results"] != initial_state["step_results"]:
                current_step = state.get("current_step", 0)
                total_steps = len(state.get("plan_steps", []))

                yield {
                    "event": "progress",
                    "data": {
                        "message": f"执行步骤 {current_step}/{total_steps}",
                        "progress": current_step / total_steps if total_steps > 0 else 0.5,
                        "step": "graph_execution",
                    },
                }

            if state.get("final_result"):
                yield {"event": "result", "data": state["final_result"]}

                yield {"event": "done", "data": {"message": "Analysis completed"}}

                break

        logger.info("GraphExecutor: Execution completed")


class GraphExecutorWrapper:
    """GraphExecutor 包装类，保持与原有 API 兼容"""

    def __init__(self, callbacks=None, message_queue: Optional[queue.Queue] = None, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.executor = GraphExecutor(callbacks=callbacks, message_queue=message_queue, event_loop=event_loop)

    async def run(
        self,
        input_text: str,
        context_files: Optional[List[Dict[str, Any]]] = None,
        plan_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        执行分析（兼容原有 API）

        Args:
            input_text: 用户输入
            context_files: 上下文文件列表
            plan_steps: 分析计划（可选，GraphExecutor 会自动生成）

        Returns:
            执行结果字典
        """
        import time

        start_time = time.time()

        try:
            logger.info(f"GraphExecutorWrapper: Starting execution")

            final_result = None
            output = ""

            async for event in self.executor.run(input_text, context_files):
                if event["event"] == "result":
                    final_result = event["data"]
                elif event["event"] == "progress":
                    logger.info(f"Progress: {event['data']}")

            execution_time = time.time() - start_time
            logger.info(f"GraphExecutorWrapper: Execution completed in {execution_time:.2f}s")

            # 构建输出格式（与原 API 兼容）
            if final_result:
                output = json.dumps(final_result, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "output": output,
                "intermediate_steps": [],
                "final_result": final_result,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"GraphExecutorWrapper: Execution failed: {str(e)}", exc_info=True)

            return {
                "success": False,
                "error": str(e),
                "output": None,
                "intermediate_steps": [],
            }
