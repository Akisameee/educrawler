"""Judge 节点 - 评估页面是否包含目标数据"""
from playwright.async_api import Page
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import END

from configs.config import get_llm
from src.state import CrawlerState, LinksUpdate
from src.base import Link, ExtractedData, JudgeResult
from src.storage import get_storage
from src.utils import load_prompt

QUERY = \
"""
## 当前页面
URL: {url}

## 页面内容
{content}

请评估此页面并输出JSON格式的结果。
"""

class JudgeNode:
    """Judge节点模型"""
    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=JudgeResult)
        self.llm = get_llm()

    async def __call__(self, state: dict) -> dict:
        """Judge节点 - 评估页面是否包含目标数据，解析并保存"""
        current_link: Link = state.get("current_link", None)
        visited_links = state.get("visited_links", {})
        current_page_content = state.get("current_page_content", "")

        print(f"[Judge] 评估页面: {current_link}")

        system_prompt = load_prompt("judge") + self.parser.get_format_instructions()
        query = QUERY.format(url=current_link.url, content=current_page_content)

        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])

        response = self.parser.parse(response.content)
        extracted_datas = []
        if response.has_value:
            datas = response.datas
            storage = get_storage()
            for data in datas:
                data.url = current_link.url if not current_link.redirected_url else current_link.redirected_url
                extracted_datas.append(data)
                print(f"[Judge] 提取到数据: {data.category} {data.appeal or 'N/A'}")
                storage.save_extracted_data(current_link.url, data.model_dump_json())
            current_link.judge_result = response.judge_result or "有价值页面"
        else:
            current_link.judge_result = response.judge_result or "无价值页面"
            print(f"[Judge] 页面无价值: {current_link.judge_result}")
        visited_links[current_link.url] = current_link

        return {
            "current_link": None,
            "current_page_links": [],
            "current_page_content": "",

            "pending_links": LinksUpdate(reduce="merge", data=state["current_page_links"]),
            "visited_links": LinksUpdate(reduce="merge", data=visited_links),
            "extracted_datas": extracted_datas,
        }
    
    @staticmethod
    def route_after(state: "CrawlerState") -> str:
        """Judge后的路由"""
        error = state.get("error")
        if error:
            return "healer"
        return "planner"