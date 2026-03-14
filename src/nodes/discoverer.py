"""Discoverer 节点 - 导航到页面，使用 LLM 智能发现新链接"""
from urllib.parse import urlparse, ParseResult
import json
import heapq
from playwright.async_api import Page
from langchain_core.messages import SystemMessage, HumanMessage
from typing import TYPE_CHECKING, List, Tuple, Dict
if TYPE_CHECKING:
    from src.agent import CrawlerState

from src.base import Link
from src.browser import get_page
from src.nodes.planner import get_llm
from src.utils import load_prompt, parse_json_response


async def get_links(page: Page, domain: str, visited: Dict[str, Link]) -> List[Link]:
    """从页面提取链接信息，并仅保留属于指定 domain 的链接"""
    
    # 1. 提取原始数据
    raw_links = await page.evaluate(
        """
        () => {
            const results = [];
            document.querySelectorAll('a[href]').forEach(a => {
                try {
                    // a.href 获取的是绝对路径
                    results.push({
                        url: a.href,
                        anchor_text: a.innerText.trim().substring(0, 100) || '[无文本]'
                    });
                } catch (e) {}
            });
            return results;
        }
        """
    )
    
    # 2. 在 Python 端进行域名清洗与筛选
    filtered_links: List[Link] = []
    # 确保 domain 格式统一（去除协议前缀和结尾斜杠）
    target_domain = urlparse(domain).netloc if "://" in domain else domain
    
    for link_data in raw_links:
        parsed_url: ParseResult = urlparse(link_data['url'])
        # 提取当前链接的域名 (netloc)
        current_netloc = parsed_url.netloc
        
        # 逻辑：判断当前域名是否与目标域名相同，或是其子域名
        if current_netloc == target_domain or current_netloc.endswith(f".{target_domain}"):
            filtered_links.append(Link(**link_data))
            
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
        await page.goto(current_link.url, wait_until="domcontentloaded", timeout=30000)
        print(f"[Discoverer] 页面加载完成")
        if page.url in visited_links:
            print(f"[Discoverer] 已被重定向至访问过的页面: {page.url}")
            current_link = None

    print(f"\n[Discoverer] 导航到: {current_link}")

    # 从页面提取链接信息（URL + 锚点文本）
    links = await get_links(page, target_domain, visited_links)
    print(f"[Discoverer] 从页面提取到 {len(links)} 个链接")
    for link in links:
        if link.url in visited_links:
            link.judge_result = visited_links[link.url].judge_result

    system_prompt = load_prompt("discoverer")

    links_json = [link.model_dump_json(exclude_none=True) for link in links[:100]]

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

        # Debug: 打印原始响应
        print(f"[Discoverer] LLM响应: {response.content[:300]}...")

        result = parse_json_response(response.content)

        if result:
            page_type = result.get("current_page_type", "OTHER")
            recommended = result.get("recommended_links", [])
            advice = result.get("strategic_advice", "")

            print(f"[Discoverer] 页面类型: {page_type}")
            print(f"[Discoverer] 策略建议: {advice}")

            # 添加推荐的链接到大根堆
            for item in recommended:
                url = item.get("url", "")
                if url and url not in visited_links and url not in pending_url_dict:
                    pending_link = Link(**item)
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