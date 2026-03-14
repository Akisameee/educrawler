from pydantic import BaseModel
from typing import Optional



class Link(BaseModel):
    """链接信息模型"""
    url: str
    anchor_text: str = ""
    score: Optional[int] = None
    judge_result: str = "Unvisited"

    def __lt__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        
        if self.score is None and other.score is not None:
            return False
        if self.score is not None and other.score is None:
            return True
        if self.score is None and other.score is None:
            return self.url < other.url

        if self.score != other.score:
            return self.score > other.score
        
        return self.url < other.url

    def __gt__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return other.__lt__(self)