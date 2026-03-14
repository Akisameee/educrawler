"""浏览器操作模块"""

from playwright.async_api import async_playwright

# 全局浏览器实例
_playwright = None
_browser = None
_browser_context = None
_page = None


async def get_page():
    """获取或创建浏览器页面"""
    global _playwright, _browser, _browser_context, _page

    if _page is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=False)
        _browser_context = await _browser.new_context()
        await _browser_context.route(
            "**/*.{png,jpg,jpeg,webp,gif,svg,ico}*", 
            lambda route: route.abort()
        )
        _page = await _browser_context.new_page()

    return _page


async def close_browser():
    """关闭浏览器"""
    global _playwright, _browser, _browser_context, _page

    if _browser_context:
        await _browser_context.close()
        _browser_context = None
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
    _page = None