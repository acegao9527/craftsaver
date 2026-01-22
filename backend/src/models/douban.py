from pydantic import BaseModel
from typing import Optional
from datetime import date


class DoubanMovie(BaseModel):
    """豆瓣电影模型"""
    douban_id: str
    title: str
    original_title: Optional[str] = None
    rating: Optional[float] = None              # 个人评分（0-5星）
    rating_star: Optional[str] = None           # 个人评分星级标记
    original_rating: Optional[float] = None     # 电影原始评分（豆瓣评分）
    original_rating_star: Optional[str] = None  # 原始评分星级标记
    date_added: Optional[str] = None            # 观看/添加日期
    comment: Optional[str] = None               # 个人短评
    tags: Optional[str] = None
    status: Optional[str] = None                # 状态：想看/在看/已看
    cover_url: Optional[str] = None
    directors: Optional[str] = None
    actors: Optional[str] = None
    year: Optional[int] = None
    country: Optional[str] = None
    genre: Optional[str] = None


class DoubanMovieCreate(DoubanMovie):
    """创建模型"""
    pass


class DoubanMovieInDB(DoubanMovie):
    """数据库模型"""
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class MovieQueryParams(BaseModel):
    """查询参数"""
    page: int = 1
    page_size: int = 20
    keyword: Optional[str] = None
    min_rating: Optional[float] = None
    status: Optional[str] = None
    genre: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    sort_by: str = "date_added"  # date_added, rating, year


class MovieStats(BaseModel):
    """统计信息"""
    total_count: int
    avg_rating: Optional[float] = None
    rating_distribution: dict
    status_distribution: dict
    genre_distribution: dict
    year_distribution: dict
