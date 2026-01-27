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

        # 添加条件边：plan 节点可以根据情况跳转到 execute_step 或 request_user_input
        graph.add_conditional_edges(
            "plan",
            self._should_execute_plan,
            {
                "execute_step": "execute_step",
                "request_input": "request_user_input",
            },
        )
        
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

        # 首次生成计划时，检查是否需要用户输入
        if not state["plan_steps"] or current_step == 0:
            # 尝试解析决策（可能包含 request_input action）
            decision_result = self._parse_decision(response.content)
            action = decision_result.get("action", "continue")
            
            if action == "request_input":
                # LLM 决定请求用户输入，将其作为第一个步骤添加到 plan_steps
                question = decision_result.get("question", "请提供更多信息以继续分析。")
                context = decision_result.get("context", "")
                logger.info(f"Plan node: LLM decided to request user input before generating plan. Question: {question[:200]}")
                
                # 将用户交互作为第一个步骤添加到 plan_steps
                user_input_step = {
                    "step": 1,
                    "action": "请求用户输入",
                    "tool_name": "user_input",  # 特殊工具名称，表示用户交互
                    "tool_params": {
                        "question": question,
                        "context": context,
                    }
                }
                
                return {
                    "should_continue": True,
                    "decision": "request_input",
                    "user_input_question": question,
                    "user_input_context": context,
                    "messages": messages,
                    "plan_steps": [user_input_step],  # 将用户交互作为第一个步骤
                    "current_step": 0,
                }
        
        # 解析生成的计划
        new_plan = self._parse_plan(response.content)

        # 更新状态
        if not state["plan_steps"] or current_step == 0:
            plan_steps = new_plan
        else:
            # 保留已完成步骤，更新剩余步骤
            plan_steps = state["plan_steps"][:current_step] + new_plan

        logger.info(f"Plan node: Generated {len(plan_steps)} steps")

        # 检查计划是否为空（首次生成计划时）
        if not state["plan_steps"] and not plan_steps:
            logger.error(
                "Plan node: Failed to generate initial plan. LLM response may be missing tool_name or tool_params. "
                f"Response: {response.content[:500]}"
            )
            # 如果首次生成计划失败，请求用户输入，让用户知道问题
            return {
                "should_continue": True,
                "decision": "request_input",
                "user_input_question": (
                    "无法生成分析计划。请提供更详细的信息以继续分析。"
                ),
                "user_input_context": f"原始输入: {state['original_input'][:200]}",
                "messages": messages,
                "plan_steps": [],  # 保持空计划
                "current_step": 0,
            }

        # 立即通过消息队列发送 plan 消息（使用线程安全的 queue.Queue）
        if self.message_queue and plan_steps:
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

        # 使用大模型直接提供的工具名称和参数（必须由 LLM 提供，不再支持代码推断）
        if "tool_name" not in step or "tool_params" not in step:
            error_msg = (
                f"计划步骤缺少 tool_name 或 tool_params 字段。步骤内容: {step}。\n"
                f"请确保计划中的每个步骤都包含 tool_name 和 tool_params 字段。\n"
                f"示例格式：\n"
                f'{{"step": 1, "action": "...", "tool_name": "read", "tool_params": {{"file_path": "..."}}}}'
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        tool_name = step["tool_name"]
        tool_input = step["tool_params"]
        logger.info(f"Using tool_name and tool_params from plan: {tool_name}, params: {tool_input}")

        # 检查是否是用户交互步骤
        if tool_name == "user_input":
            # 用户交互步骤：跳转到 request_user_input 节点
            logger.info(f"Execute step node: Step {current_step + 1} is user input step, skipping tool execution")
            # 返回状态，让图执行跳转到 request_user_input 节点
            return {
                "step_results": state["step_results"],
                "current_step": current_step,  # 不增加 current_step，因为用户交互步骤还未完成
                "decision": "request_input",
                "user_input_question": tool_input.get("question", ""),
                "user_input_context": tool_input.get("context", ""),
            }

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
            
            # 检查：如果 action 是 synthesize，但 reasoning 中明确提到需要用户输入，则改为 request_input
            if action == "synthesize" and reasoning:
                reasoning_lower = reasoning.lower()
                # 通用的关键词检测：检查 reasoning 中是否提到需要更多信息
                if ('信息不足' in reasoning or '缺少信息' in reasoning or '未提供' in reasoning or 
                    '无法' in reasoning or '需要' in reasoning or '请求' in reasoning):
                    logger.warning(
                        f"Decision node: LLM returned 'synthesize' but reasoning indicates need for user input. "
                        f"Converting to 'request_input'. Reasoning: {reasoning[:200]}"
                    )
                    action = "request_input"
                    # 从 reasoning 中提取问题，如果没有提供 question
                    if not question:
                        # 尝试提取问题描述
                        import re
                        question_match = re.search(r'(?:需要|请提供|缺少|未提供)(.+?)(?:[。\n]|$)', reasoning)
                        if question_match:
                            question = f"请提供以下信息：{question_match.group(1).strip()}"
                        else:
                            question = "请提供更多信息以继续分析。"
                    if not context:
                        context = reasoning[:500]
            
            if action == "request_input":
                # LLM 决定请求用户输入，将其作为下一个步骤添加到 plan_steps
                logger.info(f"Decision node: Requesting user input. Question: {question[:200]}")
                
                # 获取当前步骤号和计划步骤
                current_step = state.get("current_step", 0)
                plan_steps = state.get("plan_steps", [])
                
                # 将用户交互作为下一个步骤添加到 plan_steps
                user_input_step = {
                    "step": len(plan_steps) + 1,
                    "action": "请求用户输入",
                    "tool_name": "user_input",  # 特殊工具名称，表示用户交互
                    "tool_params": {
                        "question": question,
                        "context": context,
                    }
                }
                
                # 保存请求信息到状态中
                result_state = {
                    "should_continue": True,
                    "decision": "request_input",
                    "user_input_question": question,
                    "user_input_context": context,
                    "messages": messages,
                    "plan_steps": plan_steps + [user_input_step],  # 添加用户交互步骤
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
                    
                    # 验证步骤数据是否包含必需字段
                    if "tool_name" not in new_step_data or "tool_params" not in new_step_data:
                        missing_fields = []
                        if "tool_name" not in new_step_data:
                            missing_fields.append("tool_name")
                        if "tool_params" not in new_step_data:
                            missing_fields.append("tool_params")
                        
                        logger.error(
                            f"Decision node: Step data missing required fields: {missing_fields}. "
                            f"Step data: {new_step_data}. This step will be skipped."
                        )
                        continue  # 跳过这个步骤
                    
                    # 验证 tool_params 是字典类型
                    tool_params = new_step_data.get("tool_params", {})
                    if not isinstance(tool_params, dict):
                        logger.error(
                            f"Decision node: Step has invalid tool_params type. Step data: {new_step_data}. "
                            f"tool_params must be a dict, but got {type(tool_params)}: {tool_params}"
                        )
                        continue  # 跳过这个步骤
                    
                    # 验证 tool_name 是否在可用工具列表中
                    tool_name = new_step_data.get("tool_name", "")
                    available_tools = [t.name for t in self.tools]
                    if tool_name not in available_tools:
                        logger.error(
                            f"Decision node: Step has invalid tool_name. Step data: {new_step_data}. "
                            f"tool_name '{tool_name}' is not in available tools: {available_tools}"
                        )
                        continue  # 跳过这个步骤
                    
                    updated_plan_steps.append({
                        "step": step_number,
                        "action": new_step_data.get("action", "未知操作"),
                        "tool_name": tool_name,
                        "tool_params": tool_params,
                    })
                
                # 检查是否有有效的步骤被添加
                if len(updated_plan_steps) == len(plan_steps):
                    logger.error(
                        f"Decision node: No valid steps were added. All steps from LLM were invalid. "
                        f"Original plan_steps: {len(plan_steps)}, Updated plan_steps: {len(updated_plan_steps)}, "
                        f"LLM next_steps: {next_steps}"
                    )
                    return {"should_continue": False, "messages": messages}
                
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

    def _should_execute_plan(self, state: AgentState) -> str:
        """判断 plan 节点后应该执行什么：execute_step 还是 request_user_input"""
        decision = state.get("decision")
        logger.debug(f"_should_execute_plan: decision={decision}, state keys: {list(state.keys())}")
        
        if decision == "request_input":
            logger.info(f"_should_execute_plan: decision=request_input, returning request_input")
            return "request_input"
        
        logger.debug(f"_should_execute_plan: returning execute_step")
        return "execute_step"
    
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

    def _get_tools_schema_info(self) -> str:
        """获取所有工具的参数 schema 信息"""
        schema_info = []
        for tool in self.tools:
            tool_info = f"\n**{tool.name}**:"
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    schema = tool.args_schema.model_json_schema()
                    properties = schema.get('properties', {})
                    required = schema.get('required', [])
                    params = []
                    for param_name, param_info in properties.items():
                        param_type = param_info.get('type', 'unknown')
                        param_desc = param_info.get('description', '')
                        is_required = param_name in required
                        req_mark = "（必需）" if is_required else "（可选）"
                        params.append(f"  - {param_name} ({param_type}){req_mark}: {param_desc}")
                    if params:
                        tool_info += "\n" + "\n".join(params)
                except Exception as e:
                    logger.warning(f"Failed to get schema for {tool.name}: {e}")
                    tool_info += f"\n  参数: 请参考工具描述"
            schema_info.append(tool_info)
        return "\n".join(schema_info)

    def _build_initial_plan_prompt(
        self, input_text: str, context_files: Optional[List[Dict]]
    ) -> str:
        """构建初始计划生成的 prompt - 只生成第一步"""
        tools_description = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        tools_schema = self._get_tools_schema_info()

        prompt = f"""请分析以下问题，判断是否需要用户提供更多信息，或者可以开始分析。

**重要决策：**
- **如果信息不足，无法进行分析** → 回复 "action": "request_input"，并提供 "question" 字段
- **如果信息足够，可以开始分析** → 回复 "action": "continue"，并提供 "next_steps" 数组（只包含第一步）

用户问题：
{input_text}

可用工具：
{tools_description}

工具参数说明：
{tools_schema}

请按照以下 JSON 格式输出：
```json
{{
  "action": "continue" 或 "request_input",
  "reasoning": "决策理由",
  "question": "如果需要用户输入，说明需要什么信息（仅在 action 为 request_input 时需要）",
  "context": "可选的上下文信息（仅在 action 为 request_input 时可选）",
  "next_steps": [
    {{
      "step": 1,
      "action": "具体操作描述（中文）",
      "tool_name": "工具名称（如 code_search、read、grep 等）",
      "tool_params": {{
        "参数名1": "参数值1",
        "参数名2": "参数值2"
      }}
    }}
  ]
}}
```

**格式要求（必须严格遵守）：**
- 如果 action 是 "request_input"，必须提供 question 字段，next_steps 可以为空
- 如果 action 是 "continue"，next_steps 必须包含至少一个步骤，且每个步骤必须包含：step、action、tool_name、tool_params
- tool_name 必须是工具列表中的准确名称
- tool_params 必须是 JSON 对象，包含所有必需参数
- 不要使用 target 字段（已废弃）
- 格式不正确将导致执行失败！

**重要：搜索字符串时的智能提取策略**
当用户提供错误信息或日志内容时，如果完整字符串搜索可能没有结果，请智能提取关键部分进行搜索：
- **提取原则**：优先提取错误消息的核心部分（去除时间戳、进程ID、日志级别等元数据）
- **示例**：
  - 完整错误：`'[55] [atb] [error] Message process fail. Result=-12'`
  - 提取关键字符串：`'Message process fail'` 或 `'Result=-12'` 或 `'process fail'`
  - 完整错误：`'FileNotFoundError: [Errno 2] No such file or directory: /path/to/file.txt'`
  - 提取关键字符串：`'FileNotFoundError'` 或 `'No such file or directory'`
- **搜索策略（优先级顺序，必须严格遵守）**：
  1. 先尝试搜索完整字符串（如果字符串较短且明确）
  2. **如果完整字符串搜索无结果（如 grep 或 code_search 返回无结果）** → **必须**先尝试提取关键词在代码中重试，而不是直接跳到日志搜索
  3. 提取核心关键词进行搜索（去除元数据，保留核心错误消息）
  4. 对于错误码（如 `Result=-12`），可以分别搜索错误码和错误消息
  5. 对于包含特殊字符的字符串，提取纯文本部分进行搜索
  6. **只有在代码搜索（grep、code_search）多次尝试都失败后，才考虑日志搜索**
  7. **不要因为一次代码搜索失败就立即跳到日志搜索，应该先尝试提取关键词重试**

**重要：文件类型选择**
- **不要假设项目语言**：如果用户没有明确说明项目语言，不要默认搜索特定语言的文件（如 `*.py`）
- **优先搜索所有文件类型**：除非用户明确指定文件类型，否则使用 `grep` 或 `code_search` 时不要限制文件类型（不要使用 `include` 参数）
- **如果用户提到特定语言**：根据用户输入选择对应的文件类型（如 C++ 项目使用 `*.cpp`、`*.h`、`*.hpp`、`*.cc`、`*.cxx` 等）

**🚨 格式要求（必须严格遵守，否则计划将无法执行并报错）：**

**每个步骤必须包含以下字段：**
1. `step`（必需）：步骤编号，从 1 开始
2. `action`（必需）：操作描述（中文）
3. `tool_name`（必需）：工具名称，必须是以下之一：code_search、read、grep、glob、bash、log_search、database_query、websearch、webfetch
4. `tool_params`（必需）：工具参数对象，必须包含该工具的所有必需参数

**严格禁止：**
- 不要使用 target 字段（旧格式，已废弃）
- 不要省略 tool_name 或 tool_params
- 不要使用工具名称的变体或别名，必须完全匹配工具列表中的名称
- 不要使用错误的参数名称，必须与工具参数说明完全一致（区分大小写）

**参数要求：**
- tool_params 必须是一个 JSON 对象（字典），不能是字符串、数组或其他类型
- 参数名称必须与工具参数说明中的名称完全一致（区分大小写）
- 参数值必须符合工具参数的类型要求：
  - 字符串类型：使用双引号包裹，例如 "value"
  - 数字类型：直接使用数字，例如 123
  - 布尔类型：使用 true 或 false
- 必须包含该工具的所有必需参数（在工具参数说明中标记为"必需"的参数）

**如果格式不正确，系统将拒绝执行并报错！**

示例：
- 使用 code_search 工具搜索代码元素：
  ```json
  {{
    "next_steps": [{{"step": 1, "action": "搜索代码元素", "tool_name": "code_search", "tool_params": {{"query": "elementName", "search_type": "auto"}}}}]
  }}
  ```

- 使用 read 工具读取文件：
  ```json
  {{
    "next_steps": [{{"step": 1, "action": "读取文件内容", "tool_name": "read", "tool_params": {{"file_path": "path/to/file.py"}}}}]
  }}
  ```

- 使用 grep 工具搜索文本：
  ```json
  {{
    "next_steps": [{{"step": 1, "action": "搜索文本模式", "tool_name": "grep", "tool_params": {{"pattern": "searchPattern"}}}}]
  }}
  ```"""

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

        tools_schema = self._get_tools_schema_info()
        
        prompt = f"""你是一个智能分析 Agent。请根据已执行步骤的结果，动态决定下一步。

**格式要求（必须严格遵守）：**
- 如果 action 是 "continue"，next_steps 中的每个步骤必须包含：step、action、tool_name、tool_params
- tool_name 必须是工具列表中的准确名称
- tool_params 必须是 JSON 对象，包含所有必需参数
- 不要使用 target 字段（已废弃）
- 格式不正确将导致执行失败！

原始问题：
{input_text}

已执行的步骤和结果：
{''.join(executed_info)}
{failed_info}
可用工具：
{tools_description}

工具参数说明：
{tools_schema}

**重要要求：**
1. **如果信息不足，无法进行分析** → **必须**回复 "action": "request_input"，并提供 "question" 字段说明需要什么信息以及为什么需要。**不要**在这种情况下返回 "synthesize"！
2. 如果已有足够信息得出结论（包括基于失败信息可以推断的情况） → 回复 "action": "synthesize"，此时不需要 next_steps
3. 如果需要继续收集信息（包括工具调用失败后需要尝试其他方法） → **必须**回复 "action": "continue"，并且 **必须**提供 next_steps 数组，至少包含一个步骤
4. **如果选择 continue，next_steps 不能为空！** 必须明确指定下一步要执行的操作
5. **如果步骤失败，请分析失败原因，决定是重试、换方法，还是基于已有信息得出结论**
6. **必须明确指定工具名称和参数**，使用 JSON 格式

**重要：搜索字符串时的智能提取策略（必须严格遵守）**
当搜索错误信息或日志内容时，如果完整字符串搜索可能没有结果，请智能提取关键部分：
- **提取原则**：优先提取错误消息的核心部分（去除时间戳、进程ID、日志级别等元数据）
- **示例**：
  - 完整错误：`'[55] [atb] [error] Message process fail. Result=-12'`
  - 提取关键字符串：`'Message process fail'` 或 `'process fail'` 或 `'Result=-12'`
  - 完整错误：`'FileNotFoundError: [Errno 2] No such file or directory: /path/to/file.txt'`
  - 提取关键字符串：`'FileNotFoundError'` 或 `'No such file or directory'`
- **搜索策略（优先级顺序）**：
  1. **如果完整字符串搜索失败（如 grep 或 code_search 返回无结果）** → **必须**先尝试提取关键词在代码中重试，而不是直接跳到日志搜索
  2. 提取核心关键词进行搜索（去除元数据，保留核心错误消息）
  3. 对于错误码（如 `Result=-12`），可以分别搜索错误码和错误消息
  4. 对于包含特殊字符的字符串，提取纯文本部分进行搜索
  5. **只有在代码搜索（grep、code_search）多次尝试都失败后，才考虑日志搜索**
  6. **不要因为一次代码搜索失败就立即跳到日志搜索，应该先尝试提取关键词重试**

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
      "action": "具体操作描述（中文）",
      "tool_name": "工具名称（如 code_search、read、grep、glob 等）",
      "tool_params": {{
        "参数名1": "参数值1",
        "参数名2": "参数值2"
      }}
    }}
  ]
}}
```

**🚨 格式要求（必须严格遵守，否则计划将无法执行并报错）：**

**如果 action 是 "continue"：**
- `next_steps` 必须是一个非空数组 `[]`，至少包含一个步骤
- **每个步骤必须包含以下字段：**
  1. `step`（必需）：步骤编号
  2. `action`（必需）：操作描述（中文）
  3. `tool_name`（必需）：工具名称，必须是以下之一：code_search、read、grep、glob、bash、log_search、database_query、websearch、webfetch
  4. `tool_params`（必需）：工具参数对象，必须包含该工具的所有必需参数

**如果 action 是 "synthesize"：**
- `next_steps` 可以为空数组 `[]` 或省略

**如果 action 是 "request_input"：**
- 必须提供 `question` 字段
- `context` 字段可选
- `next_steps` 可以为空（用户回复后再决定下一步）

**严格禁止：**
- 不要使用 target 字段（旧格式，已废弃）
- 不要省略 tool_name 或 tool_params
- 不要使用工具名称的变体或别名，必须完全匹配工具列表中的名称
- 不要使用错误的参数名称，必须与工具参数说明完全一致（区分大小写）

**参数要求：**
- tool_params 必须是一个 JSON 对象（字典），不能是字符串、数组或其他类型
- 参数名称必须与工具参数说明中的名称完全一致（区分大小写）
- 参数值必须符合工具参数的类型要求（字符串用双引号、数字直接写、布尔用 true/false）
- 必须包含该工具的所有必需参数

**如果格式不正确，系统将拒绝执行并报错！请仔细检查每个步骤的格式！**

示例：
- action 为 "continue"：
  ```json
  {{
    "action": "continue",
    "reasoning": "需要继续收集信息",
    "next_steps": [
      {{
        "step": {current_step + 1},
        "action": "执行操作描述",
        "tool_name": "grep",
        "tool_params": {{"pattern": "searchPattern"}}
      }}
    ]
  }}
  ```

- action 为 "synthesize"：
  ```json
  {{
    "action": "synthesize",
    "reasoning": "已有足够信息得出结论",
    "next_steps": []
  }}
  ```

- action 为 "request_input"：
  ```json
  {{
    "action": "request_input",
    "reasoning": "需要用户提供额外信息",
    "question": "请提供所需的信息",
    "context": "可选的上下文说明"
  }}
  ```"""

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


    def _call_tool_directly(self, tool_name: str, tool_input: Dict) -> str:
        """直接调用工具（不通过 ToolNode）"""
        for tool in self.tools:
            if tool.name == tool_name:
                logger.info(f"Calling tool: {tool_name} with input: {tool_input}")

                try:
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

                    logger.info(f"Tool {tool_name} executed successfully")
                    return str(result)
                except TypeError as e:
                    # 参数错误，记录详细信息
                    error_msg = f"Tool {tool_name} execution failed with TypeError: {str(e)}. Input: {tool_input}"
                    logger.error(error_msg, exc_info=True)
                    raise ValueError(error_msg) from e
                except Exception as e:
                    # 其他错误
                    error_msg = f"Tool {tool_name} execution failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    raise

        error_msg = f"Tool not found: {tool_name}. Available tools: {[t.name for t in self.tools]}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    def _parse_plan(self, plan_text: str) -> List[Dict[str, Any]]:
        """解析 LLM 生成的计划文本，提取工具名称和参数"""
        import re
        steps = []
        
        # 首先尝试从 JSON 中提取 next_steps
        try:
            # 尝试提取完整的 JSON 对象（包含 next_steps）
            json_match = re.search(r'\{[\s\S]*"next_steps"[\s\S]*?\}', plan_text)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if "next_steps" in parsed and isinstance(parsed["next_steps"], list):
                    for step_data in parsed["next_steps"]:
                        if isinstance(step_data, dict):
                            step_dict = {
                                "step": step_data.get("step", len(steps) + 1),
                                "action": step_data.get("action", ""),
                                "status": "pending"
                            }
                            # 必须包含工具名称和参数，否则记录错误
                            if "tool_name" in step_data and "tool_params" in step_data:
                                tool_name = step_data["tool_name"]
                                tool_params = step_data.get("tool_params", {})
                                
                                # 验证 tool_params 是字典类型
                                if not isinstance(tool_params, dict):
                                    logger.error(
                                        f"Plan step has invalid tool_params type. Step data: {step_data}. "
                                        f"tool_params must be a JSON object (dict), but got {type(tool_params)}: {tool_params}"
                                    )
                                    continue
                                
                                # 验证 tool_name 是否在可用工具列表中
                                available_tools = [t.name for t in self.tools]
                                if tool_name not in available_tools:
                                    logger.error(
                                        f"Plan step has invalid tool_name. Step data: {step_data}. "
                                        f"tool_name '{tool_name}' is not in available tools: {available_tools}"
                                    )
                                    continue
                                
                                step_dict["tool_name"] = tool_name
                                step_dict["tool_params"] = tool_params
                                steps.append(step_dict)
                            else:
                                # 如果缺少 tool_name 或 tool_params，记录详细错误并跳过该步骤
                                missing_fields = []
                                if "tool_name" not in step_data:
                                    missing_fields.append("tool_name")
                                if "tool_params" not in step_data:
                                    missing_fields.append("tool_params")
                                
                                logger.error(
                                    f"Plan step missing required fields: {missing_fields}. Step data: {step_data}. "
                                    f"Each step MUST include 'tool_name' and 'tool_params' fields. "
                                    f"Example format: {{'step': 1, 'action': '...', 'tool_name': 'read', 'tool_params': {{'file_path': '...'}}}}"
                                )
                                # 不添加该步骤，让执行流程处理错误
                    if steps:
                        return steps
        except Exception as e:
            logger.error(f"Failed to parse plan JSON: {e}. Plan text: {plan_text[:500]}")
        
        # 如果 JSON 解析失败，返回空列表（不再支持文本格式，因为无法提供 tool_name 和 tool_params）
        if not steps:
            logger.error(
                f"Failed to parse plan. Plan must be in JSON format with tool_name and tool_params. "
                f"Plan text: {plan_text[:500]}"
            )
        
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
                        question = f"根据您的描述，我需要更多信息来继续分析。{reasoning[:200]}"
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
                    # 验证 next_steps 中的每个步骤是否包含必需字段
                    validated_steps = []
                    for step in next_steps:
                        if not isinstance(step, dict):
                            logger.warning(f"[_parse_decision] Step is not a dict: {step}")
                            continue
                        
                        if "tool_name" not in step or "tool_params" not in step:
                            missing_fields = []
                            if "tool_name" not in step:
                                missing_fields.append("tool_name")
                            if "tool_params" not in step:
                                missing_fields.append("tool_params")
                            
                            logger.warning(
                                f"[_parse_decision] Step missing required fields: {missing_fields}. "
                                f"Step data: {step}. This step will be skipped."
                            )
                            continue
                        
                        # 验证 tool_params 是字典类型
                        tool_params = step.get("tool_params", {})
                        if not isinstance(tool_params, dict):
                            logger.warning(
                                f"[_parse_decision] Step has invalid tool_params type. Step data: {step}. "
                                f"tool_params must be a dict, but got {type(tool_params)}: {tool_params}"
                            )
                            continue
                        
                        validated_steps.append(step)
                    
                    if not validated_steps:
                        logger.error(
                            f"[_parse_decision] All steps in next_steps are invalid. "
                            f"Original next_steps: {next_steps}"
                        )
                        return {
                            'action': 'synthesize',
                            'reasoning': reasoning or llm_response[:200] + " (所有步骤格式无效)",
                            'next_steps': []
                        }
                    
                    return {
                        'action': 'continue',
                        'reasoning': reasoning or llm_response[:200],
                        'next_steps': validated_steps
                    }
        
        # 如果无法解析 JSON，使用文本分析作为后备
        logger.warning(f"[_parse_decision] Failed to parse JSON, falling back to text analysis. Response: {llm_response[:300]}")
        llm_lower = llm_response.lower()
        
        # 优先检查是否需要用户输入（通用的关键词检测）
        if ('request_input' in llm_lower or '请求' in llm_response or '需要' in llm_response or 
            '信息不足' in llm_response or '缺少' in llm_response or '无法' in llm_response):
            # 尝试从文本中提取问题
            question_match = re.search(r'问题[：:]\s*(.+?)(?:\n|$)', llm_response)
            question = question_match.group(1).strip() if question_match else "请提供更多信息以继续分析。"
            return {
                'action': 'request_input',
                'reasoning': llm_response[:200],
                'question': question,
                'context': llm_response[:500],
                'next_steps': []
            }
        
        if 'synthesize' in llm_lower or '足够' in llm_response or '结束' in llm_response or '完成' in llm_response:
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
            logger.info(f"GraphExecutor state update: keys={list(state.keys())}, has_plan_steps={bool(state.get('plan_steps'))}, decision={state.get('decision')}")
            
            # 检查是否需要请求用户输入（优先处理，确保及时发送）
            if state.get("decision") == "request_input":
                user_input_question = state.get("user_input_question", "")
                user_input_context = state.get("user_input_context", "")
                logger.info(f"GraphExecutor: Detected request_input decision, yielding user_input_request event")
                yield {
                    "event": "user_input_request",
                    "data": {
                        "request_id": state.get("request_id", ""),
                        "question": user_input_question,
                        "context": user_input_context,
                    }
                }
                # 更新 initial_state 以避免重复发送
                initial_state["decision"] = "request_input"
            
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
                # 更新 initial_state 以避免重复发送
                initial_state["step_results"] = state["step_results"]

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
