"""Planner 节点 - 识别目标域名，生成初始URL种子列表"""

import re
from urllib.parse import urlparse
from typing import List, Tuple

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from configs.config import settings
from src.base import Link
from src.utils import load_prompt, parse_json_response


def get_llm() -> ChatOpenAI:
    """获取LLM实例"""
    return ChatOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model_name,
        temperature=settings.temperature,
    )


async def planner_node(state: dict) -> dict:
    """Planner节点 - 识别目标域名，生成初始URL种子列表"""
    llm = get_llm()

    # 从消息中提取任务描述
    task = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "content") and msg.content:
            task = msg.content
            break

    print(f"\n[Planner] 分析任务: {task[:100]}...")

    # 加载技能说明书
    skill_doc = load_prompt("planner")

    # 构建prompt
    prompt = f"""{skill_doc}

## 当前任务
{task}

请根据上述任务，输出JSON格式的规划结果。"""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    result = parse_json_response(response.content)

    domain = result.get("domain", "")
    seed_urls = result.get("seed_urls", [])

    # 如果解析失败，尝试从任务中提取URL
    if not seed_urls:
        urls = re.findall(r"https?://[^\s]+", task)
        domain = urlparse(urls[0]).netloc if urls else ""
        seed_urls = urls

    pending_urls: List[Link] = []
    for url in seed_urls:
        pending_urls.append(Link(url=url))
    
    print(f"[Planner] 目标域名: {domain}")
    print(f"[Planner] 种子 URL: {pending_urls}")

    return {
        "target_domain": domain,
        "pending_urls": pending_urls,
        "current_url": None,
    }