from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Literal

class BaseLink(BaseModel):
    url: str = Field(description="链接地址")
    @model_validator(mode="after")
    def _model_validate(self) -> "BaseLink":
        self.url = self.url.rstrip('/')
        return self


class Link(BaseLink):
    """链接信息模型"""
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
    
    def __str__(self) -> str:
        anchor_text = self.anchor_text if len(self.anchor_text) < 20 else f"{self.anchor_text[:40]}..."
        return f"{self.url} {anchor_text}"
    
    def __repr__(self):
        return super().__repr__()
    

class RecommandedLink(BaseLink):
    """推荐链接模型，包含权重评分"""
    score: Optional[int] = Field(0, description="链接权重评分")
    is_pagination: bool = Field(description="是否为翻页按钮（如：下一页、加载更多）")
    

class DiscoveryResult(BaseModel):
    """页面发现结果模型"""
    current_page_type: Literal["LIST", "DETAIL", "INDEX", "OTHER"] = Field(description="当前页面的类型")
    recommended_links: List[RecommandedLink] = Field(description="提取出的高价值链接列表，包含 url、文本、权重、原因和是否为翻页按钮")
    strategic_advice: str = Field(description="对后续爬取策略的建议")


class ExtractedData(BaseModel):
    """提取的数据模型"""
    url: str = Field(description="页面链接")
    topic_title: str = Field(description="页面主题/帖子标题")
    raw_extract: str = Field(description="用户原始发言片段")
    appeal: str = Field(description="精炼后的核心诉求 (动作+对象+目的)")
    category: Literal[
        "学科辅导", "升学建议", "留学申请", "公职考编",
        "职业考证", "技能进阶", "求职就业", "资源共享",
        "择校建议", "心理健康", "机构测评", "其他"
    ] = Field(description="所属分类")
    sentiment: Literal["积极", "中立", "负面"] = Field(description="情绪极性")
    pain_point: str = Field(description="用户目前遇到的阻碍")
    keywords: List[str] = Field(description="关键词，最多5个")


class JudgeResult(BaseModel):
    """页面评估结果模型"""
    has_value: bool = Field(description="页面是否包含目标数据")
    judge_result: str = Field(description="对页面价值的简短描述或分类原因")
    datas: List[ExtractedData] = Field(default_factory=list, description="从页面中提取出的结构化数据列表")

    