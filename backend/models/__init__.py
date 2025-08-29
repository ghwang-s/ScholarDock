# 导入所有模型以确保SQLAlchemy能够发现它们
from .base import Base
from .article import ArticleDB, SearchDB

__all__ = ["Base", "ArticleDB", "SearchDB"]