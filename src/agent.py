"""LangGraph Agent - 基于 SPEC 架构的爬虫智能体"""

from typing import Annotated, Dict, List, TypedDict, Optional

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from src.base import Link
from src.browser import close_browser
from src.nodes import discoverer_node, healer_node, judge_node, planner_node


# ============ 状态定义 ============


class CrawlerState(TypedDict):
    """爬虫状态"""

    messages: Annotated[List, add_messages]
    target_domain: str
    current_url: Optional[Link]
    pending_urls: List[Link]
    visited_urls: Dict[str, Link]
    extracted_data: List[dict]
    error: str | None
    retry_count: int


# ============ 路由函数 ============


def route_after_planner(state: CrawlerState) -> str:
    """Planner后的路由"""
    pending_urls = state.get("pending_urls", [])
    if not pending_urls:
        return END
    return "discoverer"


def route_after_discoverer(state: CrawlerState) -> str:
    """Discoverer后的路由"""
    error = state.get("error")
    current_url = state.get("current_url", "")
    pending_urls = state.get("pending_urls", [])

    if error:
        return "healer"

    if not current_url and not pending_urls:
        return END

    return "judge"


def route_after_judge(state: CrawlerState) -> str:
    """Judge后的路由"""
    error = state.get("error")
    pending_urls = state.get("pending_urls", [])
    visited_urls = state.get("visited_urls", [])

    if error:
        return "healer"

    # 限制最大访问页面数
    MAX_PAGES = 10
    if len(visited_urls) >= MAX_PAGES:
        print(f"\n[路由] 已达到最大页面限制 ({MAX_PAGES} 页)，结束爬取")
        return END

    if not pending_urls:
        return END

    return "discoverer"


def route_after_healer(state: CrawlerState) -> str:
    """Healer后的路由"""
    pending_urls = state.get("pending_urls", [])

    if not pending_urls:
        return END

    return "discoverer"


# ============ 构建图 ============


def build_crawler_graph():
    """构建爬虫状态机图"""
    graph = StateGraph(CrawlerState)

    # 添加节点
    graph.add_node("planner", planner_node)
    graph.add_node("discoverer", discoverer_node)
    graph.add_node("judge", judge_node)
    graph.add_node("healer", healer_node)

    # 设置入口点
    graph.set_entry_point("planner")

    # 添加条件边
    graph.add_conditional_edges("planner", route_after_planner)
    graph.add_conditional_edges("discoverer", route_after_discoverer)
    graph.add_conditional_edges("judge", route_after_judge)
    graph.add_conditional_edges("healer", route_after_healer)

    return graph.compile()


# ============ 运行入口 ============


async def run_crawler(task: str, max_steps: int = 50):
    """
    运行爬虫

    Args:
        task: 任务描述
        max_steps: 最大执行步数
    """
    # 构建图
    graph = build_crawler_graph()

    # 初始状态
    initial_state: CrawlerState = {
        "messages": [HumanMessage(content=task)],
        "target_domain": "",
        "current_url": None,
        "pending_urls": [],
        "visited_urls": {},
        "extracted_data": [],
        "error": None,
        "retry_count": 0,
    }

    print(f"\n{'=' * 60}")
    print(f"开始任务: {task[:100]}...")
    print("=" * 60)

    # 运行图
    try:
        result = await graph.ainvoke(
            initial_state,
            {"recursion_limit": max_steps},
        )

        # 打印结果
        print("\n" + "=" * 60)
        print("爬取完成!")
        print(f"已访问 URL 数量: {len(result.get('visited_urls', []))}")
        print(f"提取数据数量: {len(result.get('extracted_data', []))}")

        if result.get("extracted_data"):
            print("\n提取的数据:")
            for i, data in enumerate(result["extracted_data"], 1):
                print(f"\n--- 数据 {i} ---")
                for key, value in data.items():
                    if isinstance(value, list):
                        print(f"{key}: {', '.join(value)}")
                    else:
                        print(f"{key}: {value}")

    except Exception as e:
        print(f"\n执行出错: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理资源
        await close_browser()
        print("\n资源已清理")


# 导出
__all__ = ["build_crawler_graph", "run_crawler", "CrawlerState"]