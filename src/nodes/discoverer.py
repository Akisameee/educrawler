"""Discoverer 节点 - 导航到页面，使用 LLM 智能发现新链接"""
import asyncio
from playwright.async_api import Page
from playwright.async_api import Error as PlaywrightError
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.types import Send
from typing import TYPE_CHECKING, List, Tuple, Dict, Literal

from configs.config import get_llm
from src.state import CrawlerState
from src.base import Link, RecommandedLink, DiscoveryResult
from src.browser import get_new_page, get_links, get_text
from src.utils import load_prompt

QUERY = \
"""
## 当前页面
URL: {url}

## 页面链接列表
{links}

请分析以上链接并输出JSON格式的结果。
"""

class DiscovererNode:
    """Discoverer 节点模型"""
    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=DiscoveryResult)
        self.llm = get_llm()

    async def __call__(self, state: "CrawlerState") -> "CrawlerState":
        """Discoverer节点 - 导航到页面，使用 LLM 智能发现新链接"""
        target_domain = state.get("target_domain", "")
        current_link = state.get("current_link", None)
        visited_links: Dict[str, Link] = state.get("visited_links", dict())

        max_retries = 3
        async with get_new_page() as page:
            for attempt in range(3):
                try:
                    await page.goto(current_link.url, wait_until="networkidle", timeout=30000)
                    break
                except PlaywrightError as e:
                    if "ERR_NETWORK_CHANGED" in str(e) and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"网络抖动，{wait_time}s 后进行第 {attempt + 2} 次重试...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        print(f"加载失败: {current_link.url}, 错误: {e}")
                        return {"error": str(e)}
            
            page_url = page.url.rstrip('/')
            if page_url == current_link.url:
                print(f"[Discoverer] 导航到: {current_link}")
            else:
                print(f"[Discoverer] 页面被重定向: {current_link.url} -> {page_url}")
                current_link.redirected_url = page_url
                if page_url in visited_links:
                    print(f"[Discoverer] 页面已访问: {page_url}")
                    current_link.judge_result = visited_links[page_url].judge_result
                    visited_links[current_link.url] = current_link
                    return {
                        "current_link": None,
                        "current_page_links": {},
                        "current_page_content": "",
                    }
                
            # 从页面提取链接信息（URL + 锚点文本）
            current_page_links = await get_links(page, target_domain, visited_links)
            print(f"[Discoverer] 从页面提取到 {len(current_page_links)} 个链接")
            for link in current_page_links.values():
                if link.url in visited_links:
                    link.judge_result = visited_links[link.url].judge_result
            current_page_content = await get_text(page)

        system_prompt = load_prompt("discoverer") + self.parser.get_format_instructions()
        links_json = [link.model_dump_json(exclude_none=True) for link in list(current_page_links.values())[:100]]
        query = QUERY.format(url=current_link.url, links="\n".join(links_json))

        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        response = self.parser.parse(response.content)
        print(f"[Discoverer] 页面类型: {response.current_page_type}")
        print(f"[Discoverer] 策略建议: {response.strategic_advice}")

        recommended_links = []
        for link in response.recommended_links:
            if link.url and link.url not in visited_links:
                anchor_text = current_page_links[link.url].anchor_text if link.url in current_page_links else ""
                pending_link = Link(
                    url = link.url,
                    anchor_text = anchor_text,
                    score = link.score
                )
                recommended_links.append(pending_link)
                print(f"[Discoverer] 加入推荐链接: {pending_link}")

        return {
            "current_link": current_link,
            "current_page_links": recommended_links,
            "current_page_content": current_page_content,
        }
    
    @staticmethod
    def route_after(state: "CrawlerState") -> Send:
        """Discoverer后的路由"""
        error = state.get("error")
        if error:
            return "healer"
        return "judge"
