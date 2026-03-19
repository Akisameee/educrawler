"""SQLite3 存储模块 - 用于持久化存储和去重"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


class SQLiteStorage:
    """SQLite3 存储类"""

    _instance: Optional["SQLiteStorage"] = None
    _db_path: str = "data/crawler.db"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """初始化数据库表"""
        # 确保数据目录存在
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # 已访问URL表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visited_urls (
                url TEXT PRIMARY KEY,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 待访问URL表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 提取的数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_datas (
                url TEXT PRIMARY KEY,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 爬虫状态表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawler_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self._db_path)

    # ============ URL 去重 ============

    def is_url_visited(self, url: str) -> bool:
        """检查URL是否已访问"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM visited_urls WHERE url = ?", (url,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def mark_url_visited(self, url: str) -> bool:
        """标记URL为已访问，返回是否为新标记"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO visited_urls (url) VALUES (?)", (url,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    # ============ 待访问队列 ============

    def add_pending_url(self, url: str, priority: int = 0) -> bool:
        """添加URL到待访问队列"""
        # 先检查是否已访问
        if self.is_url_visited(url):
            return False

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO pending_urls (url, priority) VALUES (?, ?)",
                (url, priority),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_pending_urls(self, limit: int = 10) -> list[str]:
        """获取待访问URL列表（按优先级排序）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM pending_urls WHERE url IN (SELECT url FROM visited_urls)"
        )
        cursor.execute(
            """
            SELECT url FROM pending_urls
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        """,
            (limit,),
        )
        urls = [row[0] for row in cursor.fetchall()]
        # 删除已获取的URL
        if urls:
            placeholders = ",".join("?" * len(urls))
            cursor.execute(
                f"DELETE FROM pending_urls WHERE url IN ({placeholders})", urls
            )
        conn.commit()
        conn.close()
        return urls

    def get_pending_count(self) -> int:
        """获取待访问URL数量"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pending_urls")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ============ 数据存储 ============

    def save_extracted_data(self, url: str, data: dict) -> bool:
        """保存提取的数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO extracted_data (url, data) VALUES (?, ?)",
                (url, json.dumps(data, ensure_ascii=False)),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_extracted_data(self, url: str) -> Optional[dict]:
        """获取已保存的数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM extracted_data WHERE url = ?", (url,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return json.loads(result[0])
        return None

    def list_extracted_data(self, limit: int = 100) -> list[dict]:
        """列出所有保存的数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url, data FROM extracted_data ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        results = []
        for url, data_str in cursor.fetchall():
            results.append({"url": url, "data": json.loads(data_str)})
        conn.close()
        return results

    # ============ 爬虫状态 ============

    def save_state(self, state: dict) -> bool:
        """保存爬虫状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO crawler_state (id, state) VALUES (1, ?)",
                (json.dumps(state, ensure_ascii=False),),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def load_state(self) -> Optional[dict]:
        """加载爬虫状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM crawler_state WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        if result:
            return json.loads(result[0])
        return None

    # ============ 统计信息 ============

    def get_stats(self) -> dict:
        """获取统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM visited_urls")
        visited_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pending_urls")
        pending_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM extracted_data")
        data_count = cursor.fetchone()[0]

        conn.close()

        return {
            "visited_links": visited_count,
            "pending_links": pending_count,
            "extracted_data": data_count,
        }

    def clear_all(self):
        """清空所有数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM visited_urls")
        cursor.execute("DELETE FROM pending_urls")
        cursor.execute("DELETE FROM extracted_data")
        cursor.execute("DELETE FROM crawler_state")
        conn.commit()
        conn.close()


# 全局存储实例
_storage: Optional[SQLiteStorage] = None


def get_storage() -> SQLiteStorage:
    """获取存储实例"""
    global _storage
    if _storage is None:
        _storage = SQLiteStorage()
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