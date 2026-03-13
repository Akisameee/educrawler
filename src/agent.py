"""LangGraph Agent - 使用 Playwright 工具的 AI 爬虫 Agent"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from configs.config import settings
from src.tools.playwright_tools import get_playwright_tools


async def create_crawler_agent():
    """
    创建爬虫 Agent

    返回一个可执行的 LangGraph Agent
    """
    # 初始化 LLM
    llm = ChatOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model_name,
        temperature=settings.temperature,
    )

    # 获取 Playwright 工具
    tools = get_playwright_tools()

    # 使用 react agent 模式，自动处理工具调用
    agent = create_agent(llm, tools)
    return agent, tools


async def run_crawler(task: str, max_steps: int = 10):
    """
    运行爬虫 Agent

    Args:
        task: 任务描述，例如 "访问 https://example.com 并提取标题"
        max_steps: 最大执行步数
    """
    agent, tools = await create_crawler_agent()

    # 可用的工具名称
    tool_names = [t.name for t in tools]
    print(f"可用工具: {tool_names}")

    # 运行 Agent
    print(f"\n开始任务: {task}\n")
    print("=" * 50)

    config = {"recursion_limit": max_steps * 2}

    result = await agent.ainvoke(
        {"messages": [("user", task)]},
        config=config,
    )

    # 打印最终结果
    last_message = result["messages"][-1]
    print(f"\n最终回复:\n{last_message.content}")

    print("\n" + "=" * 50)
    print("任务完成")


# 导出
__all__ = ["create_crawler_agent", "run_crawler"]