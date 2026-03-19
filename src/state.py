"""LangGraph Agent - 基于 SPEC 架构的爬虫智能体"""
import operator
import heapq
from pydantic import BaseModel
from typing import Annotated, Dict, List, TypedDict, Optional, Literal, Union
from langgraph.graph.message import add_messages

from src.base import BaseLink, Link, ExtractedData

class LinksUpdate(BaseModel):
    reduce: Literal["merge", "replace"]
    data: List[BaseLink] | Dict[str, BaseLink]

def reduce_pending_links(
    current_links: List[BaseLink],
    update_links: Union[List[BaseLink], LinksUpdate]
) -> List[BaseLink]:
    if not update_links: return current_links

    if isinstance(update_links, list): update_links = LinksUpdate(reduce="merge", data=update_links)
    if update_links.reduce == "merge":
        links_map = {link.url: link for link in current_links}
        for link in update_links.data:
            if link.url not in links_map:
                links_map[link.url] = link
            else:
                pass
        updated_links = list(links_map.values())
        heapq.heapify(updated_links)
        return updated_links
    elif update_links.reduce == "replace":
        updated_links = update_links.data
        heapq.heapify(updated_links)
        return updated_links
    

def reduce_visited_links(
    current_links: Dict[str, Link],
    update_links: Union[Dict[str, Link], LinksUpdate]
) -> Dict[str, Link]:
    if not update_links: return current_links

    if isinstance(update_links, list): update_links = LinksUpdate(reduce="merge", data=update_links)
    if update_links.reduce == "merge":
        current_links.update(update_links.data)
        return current_links
    elif update_links.reduce == "replace":
        return update_links.data
    

MAX_PAGES = 30
# ============ 状态定义 ============
class CrawlerState(TypedDict):
    """爬虫状态"""
    target_domain: str

    current_link: Optional[Link]
    current_page_links: Dict[str, Link]
    current_page_content: str
    discovered_links: List[Link]

    working_links: List[Link]
    pending_links: Annotated[List[Link], reduce_pending_links]
    visited_links: Annotated[Dict[str, Link], reduce_visited_links]

    extracted_datas: Annotated[List[ExtractedData], operator.add]
    error: str | None
    retry_count: int