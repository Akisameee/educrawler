"""
Educrawler - AI Agent 爬虫

使用 LangGraph + Playwright 构建的智能爬虫
"""

import asyncio
from langchain_core.globals import set_debug
# set_debug(True)

from src.agent import run_crawler
from configs.config import settings


async def main():
    # 列出可用模型
    print("可用模型:", settings.list_models())

    # 示例任务：爬取教育领域相关信息
    domain_url = "https://leetcode.cn/"

    await run_crawler(domain_url, max_steps=30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("用户中断，退出程序")