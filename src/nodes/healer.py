"""Healer 节点 - 错误处理和重试"""


async def healer_node(state: dict) -> dict:
    """Healer节点 - 错误处理和重试"""
    error = state.get("error", "")
    retry_count = state.get("retry_count", 0)
    pending_urls = list(state.get("pending_urls", []))

    print(f"\n[Healer] 检测到错误: {error}")
    print(f"[Healer] 重试次数: {retry_count}")

    # 如果重试次数过多，跳过当前URL
    if retry_count >= 3:
        print("[Healer] 重试次数过多，跳过当前URL")
        return {
            "error": None,
            "current_url": "",
            "retry_count": 0,
        }

    # 否则继续处理待访问队列
    if pending_urls:
        print("[Healer] 继续处理下一个URL...")
        return {
            "error": None,
            "current_url": "",
            "retry_count": retry_count,
        }
    else:
        print("[Healer] 没有待访问的URL，结束爬取")
        return {
            "error": None,
            "current_url": "",
            "retry_count": 0,
        }