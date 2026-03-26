"""Judge 节点 - 评估页面是否包含目标数据"""
import time
from playwright.async_api import Page
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from typing import TYPE_CHECKING, List, Tuple, Dict, Literal

from configs.config import get_llm
from src.state import CrawlerState, ExplorerState, ExplorerOutput, LinksUpdate
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

    async def __call__(
        self,
        state: ExplorerState,
        config: RunnableConfig
    ) -> ExplorerOutput:
        """Judge节点 - 评估页面是否包含目标数据，解析并保存"""
        current_link: Link = state.current_link
        visited_links = state.visited_links.copy()
        current_page_content = state.current_page_content

        print(f"[Judge] 评估页面: {current_link}")

        system_prompt = load_prompt("judge") + self.parser.get_format_instructions()
        query = QUERY.format(url=current_link.url, content=current_page_content)

        start = time.time()
        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        print(f"[Judge] 分析完成: {current_link.url}, 开始: {start}, 耗时: {time.time() - start}s")

        response = self.parser.parse(response.content)
        extracted_datas = []
        if response.has_value:
            datas = response.datas
            storage = get_storage(state.target_domain)
            for data in datas:
                data.url = current_link.url if not current_link.redirected_url else current_link.redirected_url
                extracted_datas.append(data)
                # print(f"[Judge] 提取到数据: {data.category} {data.appeal or 'N/A'}")
                storage.save_extracted_data(current_link.url, data.model_dump())
            print(f"[Judge] 提取数据数量: {len(extracted_datas)}")
            current_link.judge_result = response.judge_result or "有价值页面"
        else:
            current_link.judge_result = response.judge_result or "无价值页面"
            print(f"[Judge] 页面无价值: {current_link.judge_result}")
        visited_links[current_link.url] = current_link

        return Command(
            update={
                "pending_links": LinksUpdate(reduce="merge", data=state.pending_links),
                "extracted_datas": extracted_datas,
            },
            goto="planner",
            graph=Command.PARENT
        )

    