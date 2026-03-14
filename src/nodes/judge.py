"""Judge 节点 - 评估页面是否包含目标数据"""
from playwright.async_api import Page
from langchain_core.messages import SystemMessage, HumanMessage

from src.base import Link
from src.nodes.planner import get_llm
from src.browser import get_page
from src.storage import get_storage
from src.utils import load_prompt, parse_json_response


async def get_text(page: Page) -> str:
    """获取页面文本"""
    # await page.add_script_tag(path="./plugins/Readability.js")
    # # 2. 在浏览器环境中执行解析逻辑
    # article_data = await page.evaluate("""
    #     () => {
    #         // 检查库是否加载成功
    #         if (typeof Readability === 'undefined') return null;
            
    #         // 使用 cloneNode 保持原始页面不被破坏
    #         const documentClone = document.cloneNode(true);
    #         const reader = new Readability(documentClone);
    #         const article = reader.parse();
            
    #         return article; 
    #         // article 包含: title, content (HTML), textContent (纯文本), excerpt (摘要), siteName
    #     }
    # """)
    
    # if article_data:
    #     print(f"标题: {article_data['title']}")
    #     # 返回清洗后的纯文本，并限制长度防止 Token 溢出
    #     return article_data['textContent'].strip()[:10000]
    # return ""
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
            await page.goto(current_link.url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"[Judge] 获取页面内容失败: {e}")
        return {"error": str(e)}

    print(f"\n[Judge] 评估页面: {current_link}")

    system_prompt = load_prompt("judge")
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

    result = parse_json_response(response.content)

    if result.get("has_value"):
        datas = result.get("datas", [])
        storage = get_storage()
        for data in datas:
            data["source_url"] = current_link.url
            extracted_data.append(data)
            print(f"[Judge] 提取到数据: {data.get('topic_title', 'N/A')}, {data.get('appeal', 'N/A')}")
            storage.save_extracted_data(current_link.url, data)
        current_link.judge_result = result.get("judge_result", "有价值页面")
    else:
        current_link.judge_result = result.get("judge_result", "无价值页面")
        print(f"[Judge] 页面无价值: {current_link.judge_result}")
    visited_urls[current_link.url] = current_link

    return {
        "extracted_data": extracted_data,
        "current_url": None,
        "visited_urls": visited_urls,
    }