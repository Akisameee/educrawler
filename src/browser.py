from playwright.async_api import async_playwright
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from playwright.async_api import Page
from typing import Dict, List

from src.base import Link
from src.utils import check_domain


# 只保留底层的全局实例
_playwright = None
_browser = None

async def init_browser():
    """初始化全局浏览器（在整个程序入口处调用一次）"""
    global _playwright, _browser
    if _browser is None:
        _playwright = await async_playwright().start()
        # 开启无头模式对并发更友好，如果为了调试可以设为 False
        _browser = await _playwright.chromium.launch(headless=False)

@asynccontextmanager
async def get_new_page():
    """为每个并发任务提供一个独立的页面"""
    global _browser
    if _browser is None:
        await init_browser()
        
    # 为当前并发任务创建一个全新的上下文（互相隔离 Cookie 和缓存）
    context = await _browser.new_context()
    
    # 拦截图片加载，加快速度
    await context.route(
        "**/*.{png,jpg,jpeg,webp,gif,svg,ico}*", 
        lambda route: route.abort()
    )
    
    page = await context.new_page()
    
    try:
        # 将 page 交给调用方使用
        yield page
    finally:
        # 任务结束后，务必关闭当前上下文，释放内存！
        await context.close()

async def close_browser():
    """关闭全局浏览器（在程序完全结束时调用）"""
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


IGNORE_TEXTS = [
    "登录", "login",
    "注册", "register",
    "退出", "exit",
    "下载", "download",
    "帮助", "help",
    "反馈", "feedback",
    "关于", "about",
    "隐私政策", "privacy policy"
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
        if len(link_data['anchor_text']) < 6 and any(text in link_data['anchor_text'] for text in IGNORE_TEXTS):
            continue
        if url not in filtered_links:
            filtered_links[url] = Link(**link_data)
    return filtered_links


async def get_text(page: Page) -> str:
    """获取页面文本"""
    page_content = await page.evaluate(
        """
        () => {
            const body = document.body;
            return body.innerText.substring(0, 10000);
        }
    """
    )
    return page_content
