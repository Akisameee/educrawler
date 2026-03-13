"""Playwright 工具 - 直接使用 Python Playwright 库"""

from typing import Optional

from langchain_core.tools import tool
from playwright.async_api import async_playwright


# 全局浏览器实例
_browser_context = None
_page = None


async def get_page():
    """获取或创建浏览器页面"""
    global _browser_context, _page

    if _page is None:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        _browser_context = await browser.new_context()
        _page = await _browser_context.new_page()

    return _page


async def close_browser():
    """关闭浏览器"""
    global _browser_context, _page

    if _browser_context:
        await _browser_context.close()
        _browser_context = None
        _page = None


@tool
async def browser_navigate(url: str) -> str:
    """导航到指定的 URL。

    Args:
        url: 要访问的网址
    """
    page = await get_page()
    await page.goto(url)
    return f"已导航到: {url}"


@tool
async def browser_snapshot() -> str:
    """获取当前页面的可访问性快照，用于了解页面内容结构。"""
    page = await get_page()

    # 获取页面标题
    title = await page.title()

    # 获取页面主要内容
    content = await page.content()

    # 简化输出，提取关键信息
    text_content = await page.evaluate("""
        () => {
            const body = document.body;
            return body.innerText.substring(0, 5000);
        }
    """)

    return f"页面标题: {title}\n\n页面内容:\n{text_content}"


@tool
async def browser_click(element_description: str, selector: Optional[str] = None) -> str:
    """点击页面上的元素。

    Args:
        element_description: 元素的描述（如"登录按钮"、"提交按钮"）
        selector: 可选的 CSS 选择器，如果不提供则通过描述查找
    """
    page = await get_page()

    if selector:
        await page.click(selector)
        return f"已点击元素: {element_description}"
    else:
        # 尝试通过文本内容查找并点击
        try:
            await page.get_by_text(element_description, exact=False).click()
            return f"已点击元素: {element_description}"
        except Exception as e:
            return f"点击失败: {str(e)}。请提供更精确的 CSS 选择器。"


@tool
async def browser_type(text: str, selector: Optional[str] = None, submit: bool = False) -> str:
    """在输入框中输入文本。

    Args:
        text: 要输入的文本
        selector: 输入框的 CSS 选择器
        submit: 是否在输入后按回车提交
    """
    page = await get_page()

    if selector:
        await page.fill(selector, text)
    else:
        # 尝试聚焦当前活动元素
        await page.keyboard.type(text)

    if submit:
        await page.keyboard.press("Enter")
        return f"已输入文本 '{text}' 并提交"
    return f"已输入文本: {text}"


@tool
async def browser_take_screenshot(filename: str = "screenshot.png") -> str:
    """截取当前页面的截图。

    Args:
        filename: 截图保存的文件名
    """
    page = await get_page()
    await page.screenshot(path=filename)
    return f"截图已保存到: {filename}"


@tool
async def browser_wait_for(text: str, timeout: int = 10000) -> str:
    """等待指定文本出现在页面上。

    Args:
        text: 要等待的文本
        timeout: 超时时间（毫秒）
    """
    page = await get_page()
    try:
        await page.wait_for_selector(f"text={text}", timeout=timeout)
        return f"文本 '{text}' 已出现"
    except Exception:
        return f"等待超时: 文本 '{text}' 未在 {timeout}ms 内出现"


@tool
async def browser_evaluate(code: str) -> str:
    """在页面中执行 JavaScript 代码。

    Args:
        code: 要执行的 JavaScript 代码
    """
    page = await get_page()
    result = await page.evaluate(code)
    return f"执行结果: {result}"


@tool
async def browser_go_back() -> str:
    """返回上一页。"""
    page = await get_page()
    await page.go_back()
    return "已返回上一页"


@tool
async def browser_scroll(direction: str = "down", amount: int = 500) -> str:
    """滚动页面。

    Args:
        direction: 滚动方向 ("up" 或 "down")
        amount: 滚动像素数
    """
    page = await get_page()
    delta = amount if direction == "down" else -amount
    await page.mouse.wheel(0, delta)
    return f"已向{direction}滚动 {amount} 像素"


def get_playwright_tools():
    """获取所有 Playwright 工具列表"""
    return [
        browser_navigate,
        browser_snapshot,
        browser_click,
        browser_type,
        browser_take_screenshot,
        browser_wait_for,
        browser_evaluate,
        browser_go_back,
        browser_scroll,
    ]