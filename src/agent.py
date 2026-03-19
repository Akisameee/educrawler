"""LangGraph Agent - 基于 SPEC 架构的爬虫智能体"""
import operator
from typing import Annotated, Dict, List, TypedDict, Optional

from langchain_core.messages import HumanMessage
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

from src.state import CrawlerState, LinksUpdate
from src.base import Link, ExtractedData
from src.browser import close_browser
from src.nodes import DiscovererNode, healer_node, JudgeNode, PlannerNode

MAX_PAGES = 30
# ============ 路由函数 ============
def route_after_healer(state: CrawlerState) -> str:
    """Healer后的路由"""
    pending_urls = state.get("pending_links", [])

    if not pending_urls:
        return END

    return "discoverer"


# ============ 构建图 ============
def build_crawler_graph():
    """构建爬虫状态机图"""
    graph = StateGraph(CrawlerState)

    # 添加节点
    graph.add_node("planner", PlannerNode())
    graph.add_node("discoverer", DiscovererNode())
    graph.add_node("judge", JudgeNode())
    graph.add_node("healer", healer_node)

    # 设置入口点
    graph.add_edge(START, "planner")

    # 添加条件边
    graph.add_conditional_edges("planner", PlannerNode.route_after, ["discoverer", END])
    graph.add_conditional_edges("discoverer", DiscovererNode.route_after, ["judge", "healer"])
    graph.add_conditional_edges("judge", JudgeNode.route_after, ["planner", "healer"])
    graph.add_conditional_edges("healer", route_after_healer, ["discoverer", "judge"])
    
    return graph.compile()


# ============ 运行入口 ============
async def run_crawler(domain_url: str, max_steps: int = 50):
    graph = build_crawler_graph()
    initial_state: CrawlerState = {
        "target_domain": domain_url,
        "current_link": None,
        "current_page_links": {},
        "current_page_content": "",

        "working_links": [],
        "pending_links": LinksUpdate(reduce="replace", data=[Link(url=domain_url)]),
        "visited_links": {},

        "extracted_datas": [],
        "error": None,
        "retry_count": 0,
    }

    print(f"\n{'=' * 60}")
    print(f"开始爬取: {domain_url}...")
    print("=" * 60)

    try:
        result = await graph.ainvoke(initial_state)

        # 打印结果
        print("\n" + "=" * 60)
        print("爬取完成!")
        print(f"已访问 URL 数量: {len(result.get('visited_urls', []))}")
        print(f"提取数据数量: {len(result.get('extracted_datas', []))}")

        if result.get("extracted_datas"):
            print("\n提取的数据:")
            for i, data in enumerate(result["extracted_datas"], 1):
                print(f"\n--- 数据 {i} ---")
                for field_name, value in data.model_dump().items():
                    print(f"{field_name}: {value}")

    except Exception as e:
        print(f"\n执行出错: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理资源
        await close_browser()
        print("\n资源已清理")


__all__ = ["build_crawler_graph", "run_crawler"]