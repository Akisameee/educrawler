"""
Educrawler - AI Agent 爬虫

使用 LangGraph + Playwright 构建的智能爬虫
"""

import asyncio

from src.agent import run_crawler
from configs.config import settings


async def main():
    # 列出可用模型
    print("可用模型:", settings.list_models())

    # 示例任务：爬取教育领域相关信息
    task = "帮我爬取https://leetcode.cn/上的用户诉求"

    await run_crawler(task, max_steps=30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断，退出程序")