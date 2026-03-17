"""Judge 节点 - 评估页面是否包含目标数据"""
from playwright.async_api import Page
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

from src.base import Link, ExtractedData, JudgeResult
from src.nodes.planner import get_llm
from src.browser import get_page
from src.storage import get_storage
from src.utils import load_prompt, parse_json_response

parser = PydanticOutputParser(pydantic_object=JudgeResult)

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


async def judge_node(state: dict) -> dict:
    """Judge节点 - 评估页面是否包含目标数据，解析并保存"""
    current_link: Link = state.get("current_url", None)
    extracted_data = list(state.get("extracted_data", []))
    visited_urls = state.get("visited_urls", {})

    if not current_link:
        print("[Judge] 没有待访问的URL，爬取完成")
        return {}

    # 获取当前页面内容
    try:
        page = await get_page()
        page_content = await get_text(page)
        if current_link.url != page.url:
            await page.goto(current_link.url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"[Judge] 获取页面内容失败: {e}")
        return {"error": str(e)}

    print(f"[Judge] 评估页面: {current_link}")

    system_prompt = load_prompt("judge") + parser.get_format_instructions()
    query = f"""
## 当前页面
URL: {current_link.url}

## 页面内容
{page_content}

请评估此页面并输出JSON格式的结果。"""

    llm = get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=query)
    ])

    response = parser.parse(response.content)
    if response.has_value:
        datas = response.datas
        storage = get_storage()
        for data in datas:
            data.url = current_link.url
            extracted_data.append(data)
            print(f"[Judge] 提取到数据: {data.topic_title or 'N/A'}, {data.appeal or 'N/A'}")
            storage.save_extracted_data(current_link.url, data.model_dump_json())
        current_link.judge_result = response.judge_result or "有价值页面"
    else:
        current_link.judge_result = response.judge_result or "无价值页面"
        print(f"[Judge] 页面无价值: {current_link.judge_result}")
    visited_urls[current_link.url] = current_link

    return {
        "extracted_data": extracted_data,
        "current_url": None,
        "visited_urls": visited_urls,
    }