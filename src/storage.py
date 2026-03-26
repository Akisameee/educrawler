"""JSONL 存储模块 - 用于持久化存储和去重"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from langchain_core.tools import tool


class JSONLStorage:
    """JSONL 存储类，按 domain 分文件存储"""

    _instance: Optional["JSONLStorage"] = None
    _domain: Optional[str] = None
    _data_dir: Path = Path("data")

    def __new__(cls, domain: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        if domain:
            cls._domain = cls._extract_domain(domain)
            cls._instance._ensure_dirs()
        return cls._instance

    @classmethod
    def _extract_domain(cls, url_or_domain: str) -> str:
        """从 URL 或域名提取干净的域名"""
        if "://" in url_or_domain:
            parsed = urlparse(url_or_domain)
            return parsed.netloc
        return url_or_domain

    @property
    def _storage_dir(self) -> Path:
        """获取当前 domain 的存储目录"""
        if not self._domain:
            raise ValueError("Domain 未设置，请先调用 set_domain() 或在初始化时传入")
        return self._data_dir / self._domain

    def _ensure_dirs(self):
        """确保存储目录存在"""
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def set_domain(self, domain: str):
        """设置当前 domain"""
        self._domain = self._extract_domain(domain)
        self._ensure_dirs()

    # ============ 文件路径 ============

    def _visited_file(self) -> Path:
        return self._storage_dir / "visited_urls.jsonl"

    def _pending_file(self) -> Path:
        return self._storage_dir / "pending_urls.jsonl"

    def _extracted_file(self) -> Path:
        return self._storage_dir / "extracted_data.jsonl"

    def _state_file(self) -> Path:
        return self._storage_dir / "state.json"

    # ============ JSONL 辅助方法 ============

    def _read_jsonl(self, file_path: Path) -> list[dict]:
        """读取 JSONL 文件"""
        if not file_path.exists():
            return []
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _append_jsonl(self, file_path: Path, record: dict):
        """追加一条记录到 JSONL 文件"""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _write_jsonl(self, file_path: Path, records: list[dict]):
        """覆盖写入 JSONL 文件"""
        with open(file_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ============ URL 去重 ============

    def is_url_visited(self, url: str) -> bool:
        """检查URL是否已访问"""
        visited = self._read_jsonl(self._visited_file())
        return any(v.get("url") == url for v in visited)

    def mark_url_visited(self, url: str) -> bool:
        """标记URL为已访问，返回是否为新标记"""
        if self.is_url_visited(url):
            return False
        record = {
            "url": url,
            "visited_at": datetime.now().isoformat(),
        }
        self._append_jsonl(self._visited_file(), record)
        # 从待访问队列中移除
        self._remove_from_pending(url)
        return True

    # ============ 待访问队列 ============

    def _remove_from_pending(self, url: str):
        """从待访问队列中移除 URL"""
        pending = self._read_jsonl(self._pending_file())
        pending = [p for p in pending if p.get("url") != url]
        self._write_jsonl(self._pending_file(), pending)

    def add_pending_url(self, url: str, priority: int = 0) -> bool:
        """添加URL到待访问队列"""
        # 先检查是否已访问
        if self.is_url_visited(url):
            return False

        # 检查是否已在队列中
        pending = self._read_jsonl(self._pending_file())
        if any(p.get("url") == url for p in pending):
            return False

        record = {
            "url": url,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
        }
        self._append_jsonl(self._pending_file(), record)
        return True

    def get_pending_urls(self, limit: int = 10) -> list[str]:
        """获取待访问URL列表（按优先级排序）"""
        pending = self._read_jsonl(self._pending_file())
        # 过滤已访问的
        pending = [p for p in pending if not self.is_url_visited(p.get("url"))]
        # 按优先级降序，创建时间升序排序
        pending.sort(key=lambda x: (-x.get("priority", 0), x.get("created_at", "")))
        # 取前 limit 个
        urls = [p.get("url") for p in pending[:limit]]
        # 从队列中移除已获取的 URL
        remaining = [p for p in pending if p.get("url") not in urls]
        self._write_jsonl(self._pending_file(), remaining)
        return urls

    def get_pending_count(self) -> int:
        """获取待访问URL数量"""
        pending = self._read_jsonl(self._pending_file())
        # 过滤已访问的
        pending = [p for p in pending if not self.is_url_visited(p.get("url"))]
        return len(pending)

    # ============ 数据存储 ============

    def save_extracted_data(self, url: str, data: dict) -> bool:
        """保存提取的数据"""
        records = self._read_jsonl(self._extracted_file())
        # 移除同 URL 的旧数据
        records = [r for r in records if r.get("url") != url]
        record = {
            "url": url,
            "data": data,
            "created_at": datetime.now().isoformat(),
        }
        records.append(record)
        self._write_jsonl(self._extracted_file(), records)
        return True

    def get_extracted_data(self, url: str) -> Optional[dict]:
        """获取已保存的数据"""
        records = self._read_jsonl(self._extracted_file())
        for record in records:
            if record.get("url") == url:
                return record.get("data")
        return None

    def list_extracted_data(self, limit: int = 100) -> list[dict]:
        """列出所有保存的数据"""
        records = self._read_jsonl(self._extracted_file())
        # 按创建时间降序
        records.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        results = []
        for record in records[:limit]:
            results.append({"url": record.get("url"), "data": record.get("data")})
        return results

    # ============ 爬虫状态 ============

    def save_state(self, state: dict) -> bool:
        """保存爬虫状态"""
        state_file = self._state_file()
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return True

    def load_state(self) -> Optional[dict]:
        """加载爬虫状态"""
        state_file = self._state_file()
        if not state_file.exists():
            return None
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # ============ 统计信息 ============

    def get_stats(self) -> dict:
        """获取统计信息"""
        visited = self._read_jsonl(self._visited_file())
        pending = self._read_jsonl(self._pending_file())
        extracted = self._read_jsonl(self._extracted_file())

        # 过滤待访问中已访问的
        pending = [p for p in pending if not self.is_url_visited(p.get("url"))]

        return {
            "visited_links": len(visited),
            "pending_links": len(pending),
            "extracted_data": len(extracted),
        }

    def clear_all(self):
        """清空所有数据"""
        self._visited_file().unlink(missing_ok=True)
        self._pending_file().unlink(missing_ok=True)
        self._extracted_file().unlink(missing_ok=True)
        self._state_file().unlink(missing_ok=True)


# 全局存储实例
_storage: Optional[JSONLStorage] = None


def get_storage(domain: Optional[str] = None) -> JSONLStorage:
    """获取存储实例"""
    global _storage
    if _storage is None:
        _storage = JSONLStorage(domain)
    elif domain:
        _storage.set_domain(domain)
    return _storage


# ============ LangChain 工具 ============


@tool
def is_url_visited(url: str) -> bool:
    """检查 URL 是否已经被访问过。

    Args:
        url: 要检查的 URL

    Returns:
        True 如果 URL 已访问过，False 如果未访问
    """
    return get_storage().is_url_visited(url)


@tool
def mark_url_visited(url: str) -> str:
    """标记 URL 为已访问。

    Args:
        url: 要标记的 URL

    Returns:
        操作结果信息
    """
    storage = get_storage()
    if storage.mark_url_visited(url):
        return f"URL '{url}' 已标记为已访问"
    return f"URL '{url}' 之前已被标记过"


@tool
def add_pending_url(url: str) -> str:
    """添加 URL 到待访问队列。

    Args:
        url: 要添加的 URL

    Returns:
        操作结果信息
    """
    storage = get_storage()
    if storage.add_pending_url(url):
        return f"URL '{url}' 已添加到待访问队列"
    return f"URL '{url}' 已访问过或已在队列中"


@tool
def get_pending_urls(limit: int = 10) -> list[str]:
    """获取待访问的 URL 列表。

    Args:
        limit: 最大返回数量，默认 10

    Returns:
        待访问的 URL 列表
    """
    return get_storage().get_pending_urls(limit)


@tool
def save_extracted_data(data: dict, source_url: str) -> str:
    """保存提取的数据。

    Args:
        data: 要保存的数据字典
        source_url: 数据来源的 URL

    Returns:
        操作结果信息
    """
    if get_storage().save_extracted_data(source_url, data):
        return f"数据已保存，来源: {source_url}"
    return f"保存失败: {source_url}"


@tool
def get_extracted_data(source_url: str) -> Optional[dict]:
    """获取已保存的提取数据。

    Args:
        source_url: 数据来源的 URL

    Returns:
        提取的数据字典，如果不存在返回 None
    """
    return get_storage().get_extracted_data(source_url)


@tool
def list_saved_data(limit: int = 100) -> list[dict]:
    """列出所有已保存的数据。

    Args:
        limit: 最大返回数量，默认 100

    Returns:
        已保存数据列表
    """
    return get_storage().list_extracted_data(limit)


def get_storage_tools():
    """获取所有存储工具列表"""
    return [
        is_url_visited,
        mark_url_visited,
        add_pending_url,
        get_pending_urls,
        save_extracted_data,
        get_extracted_data,
        list_saved_data,
    ]