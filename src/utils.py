import json
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

@cache
def load_prompt(skill_name: str) -> str:
    """加载提示词"""
    skill_path = Path(__file__).parent / "prompts" / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""


def parse_json_response(content: str) -> dict:
    """解析LLM返回的JSON"""
    try:
        # 处理markdown代码块
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
        return json.loads(content.strip())
    except Exception:
        return {}
    

def check_domain(url: str, target_domain: str) -> bool:
    """检查URL是否属于目标域名"""
    parsed_url = urlparse(url)
    return parsed_url.netloc == target_domain or parsed_url.netloc.endswith(f".{target_domain}")
