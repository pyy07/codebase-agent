"""基于 LangGraph 的 Agent 执行器"""

import asyncio
import json
from typing import TypedDict, Annotated, Sequence, Dict, Any, Optional, List, AsyncGenerator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from codebase_driven_agent.agent.executor import create_llm, get_tools
from codebase_driven_agent.agent.prompt import generate_system_prompt
from codebase_driven_agent.utils.logger import setup_logger
from codebase_driven_agent.utils.database import get_schema_info, format_schema_info
from codebase_driven_agent.config import settings

logger = setup_logger("codebase_driven_agent.agent.graph_executor")


class AgentState(TypedDict):
    """Agent 状态定义"""

    messages: Annotated[Sequence[operator.add], operator.add]
    plan_steps: List[Dict[str, Any]]
    current_step: int
    step_results: List[Dict[str, Any]]
    should_continue: bool
    original_input: str
    context_files: Optional[List[Dict[str, Any]]]


class GraphExecutor:
    """基于 LangGraph 的 Agent 执行器

    实现特点：
    1. 使用 LangGraph 构建结构化的工作流
    2. 支持动态计划生成和调整
    3. 根据执行结果动态决定下一步
    4. 完整的步骤追踪和状态管理
    """

    def __init__(self, callbacks=None):
        self.llm = create_llm()
        self.tools = get_tools()
        self.callbacks = callbacks or []
        self.tool_node = ToolNode(self.tools)
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
                "end": END,
            },
        )

        graph.add_edge("synthesize", END)

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

            return {
                "step_results": state["step_results"] + [step_result],
                "current_step": current_step + 1,
            }
        except Exception as e:
            logger.error(f"Execute step node: Step {current_step + 1} failed: {str(e)}")

            # 保存失败结果
            step_result = {
                "step": current_step,
                "action": step.get("action"),
                "target": step.get("target"),
                "status": "failed",
                "error": str(e),
            }

            return {
                "step_results": state["step_results"] + [step_result],
                "current_step": current_step + 1,
            }

    def _decision_node(self, state: AgentState) -> Dict[str, Any]:
        """决策节点：判断是否继续执行、调整计划或结束

        基于以下因素做决策：
        1. 最后一步的执行结果
        2. 已有的所有步骤结果
        3. 是否已经有足够的信息解决问题
        4. 是否达到了最大迭代次数
        """
        step_results = state["step_results"]
        plan_steps = state["plan_steps"]
        current_step = state["current_step"]

        logger.info(
            f"Decision node: current_step={current_step}/{len(plan_steps)}, results={len(step_results)}"
        )

        # 如果所有计划步骤都已完成
        if current_step >= len(plan_steps):
            logger.info("Decision node: All planned steps completed, moving to synthesize")
            return {"should_continue": False}

        # 检查最后一步的结果
        if step_results:
            last_result = step_results[-1]

            # 如果最后一步失败，需要调整计划
            if last_result.get("status") == "failed":
                logger.warning(f"Decision node: Last step failed, adjusting plan")
                # 使用 LLM 判断如何调整
                return {"should_continue": True, "decision": "adjust_plan"}

        # 检查是否已经有足够的信息
        if self._has_enough_information(state):
            logger.info("Decision node: Enough information gathered, moving to synthesize")
            return {"should_continue": False}

        # 检查是否达到最大迭代次数
        if current_step >= settings.agent_max_iterations:
            logger.warning(
                f"Decision node: Max iterations ({settings.agent_max_iterations}) reached, forcing synthesize"
            )
            return {"should_continue": False}

        # 继续执行下一步
        logger.info("Decision node: Continuing to next step")
        return {"should_continue": True}

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

        response = self.llm.invoke(messages)
        messages.append(AIMessage(content=response.content))

        # 提取结构化结果
        final_result = self._parse_synthesis_result(response.content)

        logger.info("Synthesize node: Final analysis generated")

        return {"messages": messages, "final_result": final_result}

    def _should_continue(self, state: AgentState) -> str:
        """判断下一步执行路径"""
        if not state["should_continue"]:
            return "synthesize"

        # 检查是否需要调整计划
        if state.get("decision") == "adjust_plan":
            return "adjust_plan"

        return "continue"

    def _build_initial_plan_prompt(
        self, input_text: str, context_files: Optional[List[Dict]]
    ) -> str:
        """构建初始计划生成的 prompt"""
        tools_description = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

        prompt = f"""请分析以下问题，并制定详细的分析计划。

用户问题：
{input_text}

可用工具：
{tools_description}

要求：
1. 计划要具体、可执行，每个步骤对应一个工具调用或分析操作
2. 步骤要按逻辑顺序排列，建议顺序：代码分析 → 日志查询（如需要）→ 代码定位 → 综合分析
3. 如果问题涉及错误或异常，必须包含使用代码工具（code_search）定位错误代码位置的步骤
4. 优先使用代码库分析，因为代码是问题的根源
5. 计划步骤不超过 5-7 个

请按照以下格式输出计划：
步骤1: [具体操作] - [预期目标]
步骤2: [具体操作] - [预期目标]
步骤3: [具体操作] - [预期目标]
..."""

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
        self, input_text: str, step_results: List[Dict], current_plan: List[Dict], current_step: int
    ) -> str:
        """构建计划调整的 prompt"""
        completed_steps = current_plan[:current_step]
        remaining_steps = current_plan[current_step:]

        prompt = f"""根据已执行的步骤结果，调整分析计划。

用户问题：
{input_text}

已完成的步骤：
{self._format_step_results(completed_steps, step_results)}

剩余的计划步骤：
{self._format_plan_steps(remaining_steps)}

请分析当前执行情况，并决定：
1. 是否需要修改剩余步骤？
2. 是否需要添加新的步骤？
3. 是否可以直接结束并生成结论？

如果需要调整计划，请按照以下格式输出调整后的步骤：
步骤{current_step + 1}: [具体操作] - [预期目标]
步骤{current_step + 2}: [具体操作] - [预期目标]
..."""

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

        # 如果是代码搜索，尝试从之前的步骤结果中提取相关信息
        if self._map_action_to_tool(action) == "code_search":
            if target:
                query = target
            else:
                # 如果没有明确的目标，从之前的结果中提取
                query = self._extract_query_from_results(step_results)

            return {"query": query, "max_lines": 100, "include_context": True}

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
        steps = []
        lines = plan_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            import re

            step_pattern = r"步骤\s*(\d+)\s*[:：]\s*(.+?)(?:\s*-\s*(.+))?$"
            match = re.match(step_pattern, line)

            if match:
                step_num = int(match.group(1))
                action = match.group(2).strip()
                target = match.group(3).strip() if match.group(3) else ""

                steps.append(
                    {"step": step_num, "action": action, "target": target, "status": "pending"}
                )

        return steps

    def _parse_synthesis_result(self, result_text: str) -> Dict[str, Any]:
        """解析综合分析的结果"""
        # 尝试提取 JSON
        import re

        json_match = re.search(r"```json\s*(\{.*?\})\s*```", result_text, re.DOTALL)

        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 如果无法解析 JSON，返回原始文本
        return {
            "root_cause": result_text,
            "suggestions": [],
            "confidence": 0.5,
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

    def _format_step_results(self, steps: List[Dict], results: List[Dict]) -> str:
        """格式化步骤结果"""
        formatted = []
        for step, result in zip(steps, results):
            status_icon = "✓" if result.get("status") == "completed" else "✗"
            formatted.append(f"{status_icon} {step.get('action')} - {step.get('target', '')}")
            if result.get("status") == "failed":
                formatted.append(f"  错误: {result.get('error', '')}")

        return "\n".join(formatted)

    def _format_all_step_results(self, results: List[Dict]) -> str:
        """格式化所有步骤结果"""
        formatted = []
        for i, result in enumerate(results, 1):
            status_icon = "✓" if result.get("status") == "completed" else "✗"
            formatted.append(f"{status_icon} 步骤 {i}: {result.get('action')}")
            if result.get("result"):
                formatted.append(f"  结果: {result.get('result')[:200]}...")
            if result.get("error"):
                formatted.append(f"  错误: {result.get('error')}")

        return "\n".join(formatted)

    def _format_plan_steps(self, steps: List[Dict]) -> str:
        """格式化计划步骤"""
        return "\n".join(
            [f"步骤 {s.get('step')}: {s.get('action')} - {s.get('target', '')}" for s in steps]
        )

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
            # 检查状态变化，发送进度更新
            if state.get("plan_steps") and state["plan_steps"] != initial_state["plan_steps"]:
                yield {"event": "plan", "data": {"steps": state["plan_steps"]}}

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

    def __init__(self, callbacks=None):
        self.executor = GraphExecutor(callbacks=callbacks)

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
