"""Planner 节点 - 识别目标域名，生成初始URL种子列表"""

import heapq
from typing import List, Tuple

from langgraph.types import Send
from langgraph.graph import END

from configs.config import get_llm
from src.state import CrawlerState, LinksUpdate
from src.base import Link


class PlannerNode:
    """Planner 节点模型"""
    def __init__(self, max_parallel: int = 5):
        self.llm = get_llm()
        self.max_parallel = max_parallel

    async def __call__(self, state: CrawlerState) -> CrawlerState:
        """Planner节点 - 识别目标域名，生成初始URL种子列表"""
        pending_links = state.get("pending_links", [])
        print(f"[Planner] 待处理链接数量: {len(pending_links)}")

        working_links = []
        for _ in range(min(len(pending_links), self.max_parallel)):
            working_link = heapq.heappop(pending_links)
            working_links.append(working_link)
        
        return {
            "pending_links": LinksUpdate(reduce="replace", data=pending_links),
            "working_links": working_links,
        }

    @staticmethod
    def route_after(state: CrawlerState) -> str:
        """Planner后的路由"""
        working_links = state.get("working_links", [])
        if not working_links: return END
        return [
            Send("discoverer", {
                "target_domain": state["target_domain"],
                "current_link": working_link,
                "current_page_links": [],
                "current_page_content": "",
            }) for working_link in working_links
        ]