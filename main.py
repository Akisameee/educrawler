"""
Educrawler - AI Agent 爬虫

使用 LangGraph + Playwright MCP 构建的智能爬虫
"""

import asyncio

from src.agent import run_crawler
from configs.config import settings


async def main():
    # 列出可用模型
    print("可用模型:", settings.list_models())

    # 设置使用的模型（可选，默认使用配置文件中的第一个）
    # settings.active_model = "gpt-4-turbo"

    # 示例任务
    task = """
    请帮我完成以下任务：
    1. 访问 https://example.com
    2. 获取页面的标题和主要内容
    3. 总结页面信息
    """

    await run_crawler(task, max_steps=15)


if __name__ == "__main__":
    asyncio.run(main())