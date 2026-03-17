"""Discoverer 节点 - 导航到页面，使用 LLM 智能发现新链接"""
from urllib.parse import urlparse, ParseResult
from pydantic import BaseModel, Field
import heapq
from playwright.async_api import Page
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from typing import TYPE_CHECKING, List, Tuple, Dict, Literal
if TYPE_CHECKING:
    from src.agent import CrawlerState

from src.base import Link, RecommandedLink, DiscoveryResult
from src.browser import get_page
from src.nodes.planner import get_llm
from src.utils import load_prompt, parse_json_response, check_domain

parser = PydanticOutputParser(pydantic_object=DiscoveryResult)

IGNORE_TEXTS = [
    "登录", "login",
    "注册", "register",
    "退出", "exit",
    "下载", "download",
    "帮助", "help",
    "反馈", "feedback"
]
async def get_links(page: Page, domain: str, visited: Dict[str, Link]) -> Dict[str, Link]:
    """从页面提取链接信息，并仅保留属于指定 domain 的链接"""
    raw_links: List[Dict[str, str]] = await page.evaluate(
        """
        () => {
            return Array.from(document.querySelectorAll('a[href]')).map(a => {
                // 优先取 innerText，如果太乱或没有，可以取 title 属性
                let text = a.innerText || a.title || "";
                
                // 清洗文本：去除换行、多余空格
                const cleanText = text.replace(/\\s+/g, ' ').trim();
                
                return {
                    url: a.href,
                    anchor_text: cleanText || "[无文本]"
                };
            });
        }
        """
    )
    
    filtered_links: Dict[str, Link] = {}
    target_domain = urlparse(domain).netloc if "://" in domain else domain
    for link_data in raw_links:
        url = link_data['url'].rstrip('/')
        if not check_domain(url, target_domain):
            continue
        if url in visited:
            continue
        if len(link_data['anchor_text']) < 8 and any(text in link_data['anchor_text'] for text in IGNORE_TEXTS):
            continue
        if url not in filtered_links:
            filtered_links[url] = Link(**link_data)
    return filtered_links


async def discoverer_node(state: "CrawlerState") -> "CrawlerState":
    """Discoverer节点 - 导航到页面，使用 LLM 智能发现新链接"""
    target_domain = state.get("target_domain", "")
    current_link = state.get("current_url", None)
    pending_links: List[Link] = state.get("pending_urls", [])
    pending_url_dict: Dict[str, Link] = {link.url: link for link in pending_links}
    visited_links: Dict[str, Link] = state.get("visited_urls", dict())

    if not pending_links: return {}

    page = await get_page()
    while not current_link:
        current_link = heapq.heappop(pending_links)
        print(f"[Discoverer] 弹出待访问队列: {current_link}")
        await page.goto(current_link.url, wait_until="networkidle", timeout=30000)
        print(f"[Discoverer] 页面加载完成")
        if page.url in visited_links:
            print(f"[Discoverer] 已被重定向至访问过的页面: {page.url}")
            current_link = None

    print(f"[Discoverer] 导航到: {current_link}")

    # 从页面提取链接信息（URL + 锚点文本）
    links = await get_links(page, target_domain, visited_links)
    print(f"[Discoverer] 从页面提取到 {len(links)} 个链接")
    for link in links.values():
        if link.url in visited_links:
            link.judge_result = visited_links[link.url].judge_result

    system_prompt = load_prompt("discoverer") + parser.get_format_instructions()

    links_json = [link.model_dump_json(exclude_none=True) for link in list(links.values())[:100]]

    query = f"""
## 当前页面
URL: {current_link.url}

## 页面链接列表
{links_json}

请分析以上链接并输出JSON格式的结果。"""

    try:
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        response = parser.parse(response.content)
        print(f"[Discoverer] 页面类型: {response.current_page_type}")
        print(f"[Discoverer] 策略建议: {response.strategic_advice}")

        # 添加推荐的链接到大根堆
        for link in response.recommended_links:
            if link.url and link.url not in visited_links and link.url not in pending_url_dict:
                anchor_text = links[link.url].anchor_text if link.url in links else ""
                pending_link = Link(
                    url = link.url,
                    anchor_text = anchor_text,
                    score = link.score
                )
                heapq.heappush(pending_links, pending_link)
                print(f"[Discoverer] 加入推荐链接: {pending_link}")

        print(f"[Discoverer] 待访问队列: {len(pending_links)} 个")

    except Exception as e:
        print(f"[Discoverer] LLM 调用失败: {e}")

    return {
        "current_url": current_link,
        "pending_urls": pending_links,
        "visited_urls": visited_links,
        "error": None,
        "retry_count": 0,
    }