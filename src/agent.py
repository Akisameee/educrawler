"""LangGraph Agent - 基于 SPEC 架构的爬虫智能体"""
import operator
from typing import Annotated, Dict, List, TypedDict, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

from src.state import CrawlerState, ExplorerInput, ExplorerOutput, ExplorerState, LinksUpdate
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
    explorer_graph = StateGraph(ExplorerState, input_schema=ExplorerInput, output_schema=ExplorerOutput)
    explorer_graph.add_node("discoverer", DiscovererNode())
    explorer_graph.add_node("judge", JudgeNode())
    explorer_graph.add_node("healer", healer_node)

    explorer_graph.add_edge(START, "discoverer")
    explorer_graph = explorer_graph.compile()

    graph = StateGraph(CrawlerState)
    graph.add_node("planner", PlannerNode(2))
    graph.add_node("explorer", explorer_graph)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", PlannerNode.route_after, ["explorer", END])
    
    return graph.compile()


# ============ 运行入口 ============
async def run_crawler(domain_url: str, max_steps: int = 50):
    graph = build_crawler_graph()
    initial_state: CrawlerState = {
        "target_domain": domain_url,
        "working_links": [],
        "pending_links": LinksUpdate(reduce="replace", data=[
            Link(url=domain_url),
            Link(url="https://leetcode.cn/studyplan/top-100-liked")
        ]),
        "visited_links": {},
        "extracted_datas": [],
    }
    config = RunnableConfig(
        max_concurrency=10
    )

    print(f"\n{'=' * 60}")
    print(f"开始爬取: {domain_url}...")
    print("=" * 60)

    try:
        result = await graph.ainvoke(initial_state, config)
        # async for chunk in graph.astream(initial_state, stream_mode="debug", subgraphs=True):
        #     print(f"更新内容: {chunk}, payload_keys: {chunk[1]['payload'].keys()}")

        # # 打印结果
        print("\n" + "=" * 60)
        print("爬取完成!")
        print(f"已访问 URL 数量: {len(result.get('visited_links', []))}")
        print(f"提取数据数量: {len(result.get('extracted_datas', []))}")

        # if result.get("extracted_datas"):
        #     print("\n提取的数据:")
        #     for i, data in enumerate(result["extracted_datas"], 1):
        #         print(f"\n--- 数据 {i} ---")
        #         for field_name, value in data.model_dump().items():
        #             print(f"{field_name}: {value}")

    except Exception as e:
        print(f"\n执行出错: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理资源
        await close_browser()
        print("\n资源已清理")


__all__ = ["build_crawler_graph", "run_crawler"]