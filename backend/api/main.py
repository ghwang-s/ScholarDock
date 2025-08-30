from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import os
import asyncio
from pydantic import BaseModel, EmailStr

from core.config import settings
from core.database import init_db, get_db
from core.proxy_config import get_proxy
from models.article import SearchRequest, SearchResponse, SearchDB, ArticleDB, SearchSchema, ArticleSchema
from services.original_spider import OriginalScholarSpider
from core.proxy_config import get_proxy
import requests
from services.export import ExportService
from services.author_email_extractor import AuthorEmailExtractor
from services.email_sender import get_email_sender
from websocket_server import setup_websocket_endpoint, send_progress_update


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# 设置WebSocket端点
setup_websocket_endpoint(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version}


@app.post("/api/search", response_model=SearchResponse)
async def search_articles(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    search_record = SearchDB(
        keyword=request.keyword,
        start_year=request.start_year,
        end_year=request.end_year
    )
    db.add(search_record)
    await db.commit()
    await db.refresh(search_record)
    
    try:
        print(f"🔍 开始搜索: '{request.keyword}', 目标结果数: {request.num_results}")

        # 如果启用了排重，则从数据库获取所有现有标题
        existing_titles = set()
        if request.exclude_duplicates:
            result = await db.execute(select(ArticleDB.title))
            all_titles = result.scalars().all()
            existing_titles = {title.lower().strip() for title in all_titles if title}
            print(f"📚 从数据库加载了 {len(existing_titles)} 个已存在的标题用于去重")

        async with OriginalScholarSpider() as spider:
            articles = await spider.search(
                keyword=request.keyword,
                num_results=request.num_results,
                start_year=request.start_year,
                end_year=request.end_year,
                filter_by_title=request.filter_by_title,
                exclude_duplicates=request.exclude_duplicates,
                existing_titles=existing_titles
            )

        print(f"✅ 搜索完成，找到 {len(articles)} 篇文章")
        
        # Return empty results if nothing found
        if not articles:
            print(f"No results found for '{request.keyword}' - may be blocked by Google Scholar")
        
        if request.sort_by == "citations":
            articles.sort(key=lambda x: x.citations, reverse=True)
        elif request.sort_by == "citations_per_year":
            articles.sort(key=lambda x: x.citations_per_year, reverse=True)
        elif request.sort_by == "year":
            articles.sort(key=lambda x: x.year or 0, reverse=True)
        
        for article in articles:
            article_db = ArticleDB(
                title=article.title,
                authors=article.authors,
                author_links=article.author_links,  # 保存作者链接信息
                venue=article.venue,
                publisher=article.publisher,
                year=article.year,
                citations=article.citations,
                citations_per_year=article.citations_per_year,
                description=article.description,
                url=article.url,
                search_id=search_record.id
            )
            db.add(article_db)
        
        search_record.total_results = len(articles)
        await db.commit()
        
        return SearchResponse(
            search_id=search_record.id,
            keyword=request.keyword,
            total_results=len(articles),
            articles=articles
        )
        
    except Exception as e:
        print(f"❌ 搜索过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

        await db.rollback()

        # 提供更详细的错误信息
        error_message = str(e)
        if "timeout" in error_message.lower():
            error_message = "网络连接超时，请检查网络连接或代理设置"
        elif "proxy" in error_message.lower():
            error_message = "代理连接失败，请检查代理服务是否正常运行"
        elif "robot" in error_message.lower() or "unusual traffic" in error_message.lower():
            error_message = "被Google Scholar检测为机器人，请稍后再试或更换代理"
        elif "频率过高" in error_message or "429" in error_message:
            error_message = "请求频率过高，Google Scholar暂时限制了访问。请等待5-10分钟后重试，或尝试使用不同的关键词。"
        elif "connection" in error_message.lower():
            error_message = "网络连接失败，请检查网络连接"
        else:
            error_message = f"搜索失败: {error_message}"

        raise HTTPException(status_code=500, detail=error_message)


@app.get("/api/proxy/status")
async def get_proxy_status():
    """获取代理状态"""
    try:
        proxy = get_proxy()
        if not proxy:
            return {
                "status": "disabled",
                "message": "未配置代理",
                "proxy": None
            }

        # 测试代理连接
        proxies = {
            'http': proxy,
            'https': proxy
        }

        test_url = "https://www.google.com"
        response = requests.get(test_url, proxies=proxies, timeout=10)

        if response.status_code == 200:
            return {
                "status": "connected",
                "message": "代理连接正常",
                "proxy": proxy
            }
        else:
            return {
                "status": "error",
                "message": f"代理连接异常，状态码: {response.status_code}",
                "proxy": proxy
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"代理连接失败: {str(e)}",
            "proxy": get_proxy()
        }


@app.get("/api/searches", response_model=List[SearchSchema])
async def get_search_history(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SearchDB)
        .options(selectinload(SearchDB.articles))
        .order_by(SearchDB.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    searches = result.scalars().all()
    return searches


@app.get("/api/search/{search_id}", response_model=SearchSchema)
async def get_search_details(
    search_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SearchDB)
        .options(selectinload(SearchDB.articles))
        .where(SearchDB.id == search_id)
    )
    search = result.scalar_one_or_none()
    
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    
    return search


@app.get("/api/export/{search_id}")
async def export_search_results(
    search_id: int,
    format: str = "csv",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SearchDB)
        .options(selectinload(SearchDB.articles))
        .where(SearchDB.id == search_id)
    )
    search = result.scalar_one_or_none()
    
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    
    articles = [ArticleSchema.model_validate(article) for article in search.articles]
    
    if format == "csv":
        content = ExportService.to_csv(articles)
        media_type = "text/csv"
        filename = f"scholar_results_{search.keyword}.csv"
    elif format == "json":
        content = ExportService.to_json(articles)
        media_type = "application/json"
        filename = f"scholar_results_{search.keyword}.json"
    elif format == "excel":
        content = ExportService.to_excel(articles)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"scholar_results_{search.keyword}.xlsx"
    elif format == "bibtex":
        content = ExportService.to_bibtex(articles)
        media_type = "text/plain"
        filename = f"scholar_results_{search.keyword}.bib"
    else:
        raise HTTPException(status_code=400, detail="Invalid export format")
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.delete("/api/search/{search_id}")
async def delete_search(
    search_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SearchDB)
        .options(selectinload(SearchDB.articles))
        .where(SearchDB.id == search_id)
    )
    search = result.scalar_one_or_none()
    
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    
    await db.delete(search)
    await db.commit()
    
    return {"message": "Search deleted successfully"}


@app.post("/api/extract-author-emails/{article_id}")
async def extract_author_emails(
    article_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """提取指定论文的作者邮箱"""
    # 获取论文信息
    # 获取论文信息
    result = await db.execute(
        select(ArticleDB).where(ArticleDB.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if not article.author_links:
        raise HTTPException(status_code=400, detail="No author links available for this article")

    # 定义进度回调函数
    async def progress_callback(progress_data: dict):
        """进度回调函数，通过WebSocket发送进度更新"""
        try:
            await send_progress_update(str(article_id), progress_data)
        except Exception as e:
            print(f"发送进度更新失败: {e}")

    try:
        # 提取作者邮箱（使用代理）
        proxy = get_proxy()
        print(f"🔧 使用代理: {proxy}")
        async with AuthorEmailExtractor(proxy=proxy) as extractor:
            extraction_result = await extractor.extract_author_emails(article.author_links, progress_callback)

        # 处理返回结果
        if isinstance(extraction_result, dict):
            author_emails = extraction_result.get('author_emails', [])
            pdf_fallback_emails = extraction_result.get('pdf_fallback_emails', [])
        else:
            # 兼容旧格式
            author_emails = extraction_result
            pdf_fallback_emails = []

        # 更新数据库
        article.author_emails = author_emails
        # 如果有PDF邮箱，也保存到数据库
        if pdf_fallback_emails:
            article.pdf_fallback_emails = pdf_fallback_emails
        await db.commit()
        await db.refresh(article)

        # 发送完成消息
        await send_progress_update(str(article_id), {
            "type": "completion",
            "step": "extraction_complete",
            "title": "邮箱提取完成",
            "description": f"成功提取 {len([e for e in author_emails if e.get('email')])} 个作者邮箱",
            "status": "completed",
            "result": {
                "author_emails": author_emails
            }
        })

        return {
            "message": "Author emails extracted successfully",
            "article_id": article_id,
            "author_emails": author_emails,
            "pdf_fallback_emails": pdf_fallback_emails
        }

    except Exception as e:
        await db.rollback()
        
        # 发送错误消息
        await send_progress_update(str(article_id), {
            "type": "error",
            "step": "extraction_error",
            "title": "邮箱提取失败",
            "description": f"提取作者邮箱时发生错误: {str(e)}",
            "status": "failed"
        })
        
        raise HTTPException(status_code=500, detail=f"Failed to extract author emails: {str(e)}")


@app.post("/api/extract-all-author-emails/{search_id}")
async def extract_all_author_emails(
    search_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """提取指定搜索结果中所有论文的作者邮箱"""
    # 获取搜索记录和相关论文
    result = await db.execute(
        select(SearchDB)
        .options(selectinload(SearchDB.articles))
        .where(SearchDB.id == search_id)
    )
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    if not search.articles:
        raise HTTPException(status_code=400, detail="No articles found for this search")

    # 在后台任务中处理邮箱提取
    background_tasks.add_task(
        _extract_emails_for_search,
        search_id,
        db
    )

    return {
        "message": "Author email extraction started in background",
        "search_id": search_id,
        "total_articles": len(search.articles)
    }


async def _extract_emails_for_search(search_id: int, db: AsyncSession):
    """后台任务：为搜索结果中的所有论文提取作者邮箱"""
    try:
        # 重新获取搜索记录和论文
        result = await db.execute(
            select(SearchDB)
            .options(selectinload(SearchDB.articles))
            .where(SearchDB.id == search_id)
        )
        search = result.scalar_one_or_none()

        if not search or not search.articles:
            return

        proxy = get_proxy()
        print(f"🔧 批量提取使用代理: {proxy}")
        async with AuthorEmailExtractor(proxy=proxy) as extractor:
            for article in search.articles:
                if article.author_links and not article.author_emails:
                    try:
                        print(f"🔍 正在提取论文 '{article.title}' 的作者邮箱...")
                        extraction_result = await extractor.extract_author_emails(article.author_links)

                        # 处理返回结果
                        if isinstance(extraction_result, dict):
                            author_emails = extraction_result.get('author_emails', [])
                            pdf_fallback_emails = extraction_result.get('pdf_fallback_emails', [])
                        else:
                            # 兼容旧格式
                            author_emails = extraction_result
                            pdf_fallback_emails = []

                        # 更新论文的作者邮箱信息
                        article.author_emails = author_emails
                        # 如果有PDF邮箱，也保存到数据库
                        if pdf_fallback_emails:
                            article.pdf_fallback_emails = pdf_fallback_emails
                        await db.commit()

                        # 添加延迟避免请求过于频繁
                        print("⏳ 等待5秒后处理下一篇论文...")
                        await asyncio.sleep(5)

                        print(f"✅ 成功提取 {len(author_emails)} 个作者邮箱")

                    except Exception as e:
                        print(f"❌ 提取论文 '{article.title}' 作者邮箱失败: {e}")
                        await db.rollback()
                        continue

        print(f"🎉 搜索 {search_id} 的作者邮箱提取完成")

    except Exception as e:
        print(f"❌ 后台邮箱提取任务失败: {e}")


@app.get("/api/proxy-status")
async def get_proxy_status():
    """获取代理状态"""
    proxy = get_proxy()

    if not proxy:
        return {
            "proxy_enabled": False,
            "proxy_url": None,
            "status": "disabled"
        }

    # 测试代理连接
    try:
        import aiohttp

        connector = aiohttp.TCPConnector()
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:
            async with session.get("https://www.google.com", proxy=proxy) as response:
                if response.status == 200:
                    return {
                        "proxy_enabled": True,
                        "proxy_url": proxy,
                        "status": "connected",
                        "message": "代理连接正常"
                    }
                else:
                    return {
                        "proxy_enabled": True,
                        "proxy_url": proxy,
                        "status": "error",
                        "message": f"代理连接异常 (状态码: {response.status})"
                    }

    except Exception as e:
        return {
            "proxy_enabled": True,
            "proxy_url": proxy,
            "status": "error",
            "message": f"代理连接失败: {str(e)}"
        }


# 邮件相关的Pydantic模型
class EmailPreviewRequest(BaseModel):
    """邮件预览请求"""
    author_name: str
    paper_title: str
    paper_venue: Optional[str] = None
    paper_year: Optional[int] = None
    paper_citations: Optional[int] = None


class EmailSendRequest(BaseModel):
    """邮件发送请求"""
    to_email: EmailStr
    subject: str
    author_name: str
    paper_title: str
    paper_venue: Optional[str] = None
    paper_year: Optional[int] = None
    paper_citations: Optional[int] = None


class BatchEmailRequest(BaseModel):
    """批量邮件发送请求"""
    search_id: int
    subject: str
    include_author_emails: bool = True
    include_pdf_emails: bool = True


@app.post("/api/email/preview")
async def preview_email(request: EmailPreviewRequest):
    """预览邮件内容"""
    try:
        sender = get_email_sender()

        template_data = {
            'author_name': request.author_name,
            'paper_title': request.paper_title,
            'paper_venue': request.paper_venue,
            'paper_year': request.paper_year,
            'paper_citations': request.paper_citations
        }

        html_content = sender.preview_email(template_data)

        return {
            'success': True,
            'html_content': html_content,
            'template_data': template_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件预览失败: {str(e)}")


@app.post("/api/email/send")
async def send_email(request: EmailSendRequest):
    """发送邮件"""
    try:
        sender = get_email_sender()

        template_data = {
            'author_name': request.author_name,
            'paper_title': request.paper_title,
            'paper_venue': request.paper_venue,
            'paper_year': request.paper_year,
            'paper_citations': request.paper_citations
        }

        result = sender.send_email(
            to_email=request.to_email,
            subject=request.subject,
            template_data=template_data
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {str(e)}")


@app.get("/api/email/config")
async def get_email_config():
    """获取邮件配置状态"""
    try:
        sender = get_email_sender()
        return sender.validate_email_config()

    except Exception as e:
        return {
            'valid': False,
            'message': f'邮件配置错误: {str(e)}',
            'error': str(e)
        }


@app.post("/api/email/batch-send")
async def batch_send_emails(
    request: BatchEmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """批量发送邮件"""
    try:
        # 获取搜索记录和文章
        result = await db.execute(
            select(SearchDB)
            .options(selectinload(SearchDB.articles))
            .where(SearchDB.id == request.search_id)
        )
        search = result.scalar_one_or_none()

        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        if not search.articles:
            raise HTTPException(status_code=400, detail="No articles found for this search")

        # 获取之前已经发送过邮件的论文标题
        previously_sent_titles = await _get_previously_sent_articles(request.search_id, db)

        # 统计邮箱数量（排除重复论文）
        total_emails = 0
        skipped_count = 0
        for article in search.articles:
            # 检查论文是否已经发送过邮件
            normalized_title = article.title.lower().strip() if article.title else ""
            if normalized_title in previously_sent_titles:
                skipped_count += 1
                continue

            if request.include_author_emails and article.author_emails:
                total_emails += len([e for e in article.author_emails if e.get('email')])
            if request.include_pdf_emails and article.pdf_fallback_emails:
                total_emails += len(article.pdf_fallback_emails)

        print(f"📊 批量发送统计: 总论文 {len(search.articles)} 篇，跳过重复 {skipped_count} 篇，待发送邮箱 {total_emails} 个")

        if total_emails == 0:
            raise HTTPException(status_code=400, detail="No emails found to send")

        # 在后台任务中处理批量发送
        background_tasks.add_task(
            _batch_send_emails_task,
            request.search_id,
            request.subject,
            request.include_author_emails,
            request.include_pdf_emails,
            db
        )

        return {
            "message": "Batch email sending started",
            "search_id": request.search_id,
            "total_emails": total_emails,
            "total_articles": len(search.articles)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start batch email sending: {str(e)}")


async def _get_previously_sent_articles(search_id: int, db: AsyncSession) -> set:
    """获取之前搜索结果中已经发送过邮件的论文标题"""
    try:
        # 获取当前搜索之前的所有搜索记录
        result = await db.execute(
            select(SearchDB)
            .options(selectinload(SearchDB.articles))
            .where(SearchDB.id < search_id)
            .order_by(SearchDB.id.desc())
        )
        previous_searches = result.scalars().all()

        sent_article_titles = set()

        for search in previous_searches:
            for article in search.articles:
                # 检查这篇论文是否有邮箱信息（说明可能已经发送过邮件）
                if (article.author_emails and any(e.get('email') for e in article.author_emails)) or \
                   (article.pdf_fallback_emails and len(article.pdf_fallback_emails) > 0):
                    # 使用标题的标准化版本进行比较（去除空格、转小写）
                    normalized_title = article.title.lower().strip() if article.title else ""
                    if normalized_title:
                        sent_article_titles.add(normalized_title)

        print(f"🔍 找到 {len(sent_article_titles)} 篇之前处理过的论文")
        return sent_article_titles

    except Exception as e:
        print(f"❌ 获取之前发送记录失败: {e}")
        return set()


async def _batch_send_emails_task(
    search_id: int,
    subject: str,
    include_author_emails: bool,
    include_pdf_emails: bool,
    db: AsyncSession
):
    """后台任务：批量发送邮件"""
    try:
        # 重新获取搜索记录和文章
        result = await db.execute(
            select(SearchDB)
            .options(selectinload(SearchDB.articles))
            .where(SearchDB.id == search_id)
        )
        search = result.scalar_one_or_none()

        if not search or not search.articles:
            return

        # 获取之前已经发送过邮件的论文标题
        previously_sent_titles = await _get_previously_sent_articles(search_id, db)

        sender = get_email_sender()

        # 创建一个集合来跟踪已经发送的邮箱地址
        sent_emails = set()

        # 统计总邮箱数（排除重复论文和重复邮箱）
        total_emails = 0
        skipped_articles = 0
        for article in search.articles:
            # 检查论文是否已经发送过邮件
            normalized_title = article.title.lower().strip() if article.title else ""
            if normalized_title in previously_sent_titles:
                skipped_articles += 1
                print(f"⏭️ 跳过重复论文: {article.title[:50]}...")
                continue

            # 统计作者邮箱（去重）
            if include_author_emails and article.author_emails:
                for author_email in article.author_emails:
                    if author_email.get('email') and author_email['email'] not in sent_emails:
                        total_emails += 1

            # 统计PDF邮箱（去重）
            if include_pdf_emails and article.pdf_fallback_emails:
                for pdf_email in article.pdf_fallback_emails:
                    if pdf_email not in sent_emails:
                        total_emails += 1

        print(f"📊 统计结果: 总论文 {len(search.articles)} 篇，跳过重复 {skipped_articles} 篇，待发送邮箱 {total_emails} 个")

        sent_count = 0
        failed_count = 0

        # 发送进度更新
        await send_progress_update(f"batch_email_{search_id}", {
            "type": "progress",
            "step": "batch_sending",
            "title": "批量发送邮件",
            "description": f"开始发送 {total_emails} 封邮件",
            "progress": 0,
            "total": total_emails,
            "sent": 0,
            "failed": 0
        })

        for article in search.articles:
            # 检查论文是否已经发送过邮件
            normalized_title = article.title.lower().strip() if article.title else ""
            if normalized_title in previously_sent_titles:
                print(f"⏭️ 跳过重复论文: {article.title[:50]}...")
                continue

            # 发送作者邮箱
            if include_author_emails and article.author_emails:
                for author_email in article.author_emails:
                    if author_email.get('email') and author_email['email'] not in sent_emails:
                        try:
                            template_data = {
                                'author_name': author_email.get('name', 'Fellow Researcher'),
                                'paper_title': article.title,
                                'paper_venue': article.venue,
                                'paper_year': article.year,
                                'paper_citations': article.citations
                            }

                            result = sender.send_email(
                                to_email=author_email['email'],
                                subject=subject,
                                template_data=template_data
                            )

                            if result.get('success'):
                                sent_count += 1
                                # 将邮箱添加到已发送集合中
                                sent_emails.add(author_email['email'])
                                print(f"✅ 成功发送邮件到 {author_email['email']}")
                            else:
                                failed_count += 1
                                print(f"❌ 发送邮件到 {author_email['email']} 失败: {result.get('message')}")

                        except Exception as e:
                            failed_count += 1
                            print(f"❌ 发送邮件到 {author_email['email']} 异常: {e}")

                        # 更新进度
                        progress = int((sent_count + failed_count) / total_emails * 100)
                        await send_progress_update(f"batch_email_{search_id}", {
                            "type": "progress",
                            "step": "batch_sending",
                            "title": "批量发送邮件",
                            "description": f"已发送 {sent_count}/{total_emails} 封邮件",
                            "progress": progress,
                            "total": total_emails,
                            "sent": sent_count,
                            "failed": failed_count
                        })

                        # 添加延迟避免发送过快
                        await asyncio.sleep(5)

            # 发送PDF邮箱
            if include_pdf_emails and article.pdf_fallback_emails:
                for pdf_email in article.pdf_fallback_emails:
                    if pdf_email not in sent_emails:
                        try:
                            template_data = {
                                'author_name': 'Fellow Researcher',
                                'paper_title': article.title,
                                'paper_venue': article.venue,
                                'paper_year': article.year,
                                'paper_citations': article.citations
                            }

                            result = sender.send_email(
                                to_email=pdf_email,
                                subject=subject,
                                template_data=template_data
                            )

                            if result.get('success'):
                                sent_count += 1
                                # 将邮箱添加到已发送集合中
                                sent_emails.add(pdf_email)
                                print(f"✅ 成功发送邮件到 {pdf_email}")
                            else:
                                failed_count += 1
                                print(f"❌ 发送邮件到 {pdf_email} 失败: {result.get('message')}")

                        except Exception as e:
                            failed_count += 1
                            print(f"❌ 发送邮件到 {pdf_email} 异常: {e}")

                        # 更新进度
                        progress = int((sent_count + failed_count) / total_emails * 100)
                        await send_progress_update(f"batch_email_{search_id}", {
                            "type": "progress",
                            "step": "batch_sending",
                            "title": "批量发送邮件",
                            "description": f"已发送 {sent_count}/{total_emails} 封邮件",
                            "progress": progress,
                            "total": total_emails,
                            "sent": sent_count,
                            "failed": failed_count
                        })

                        # 添加延迟避免发送过快
                        await asyncio.sleep(5)

        # 发送完成消息
        await send_progress_update(f"batch_email_{search_id}", {
            "type": "completion",
            "step": "batch_complete",
            "title": "批量发送完成",
            "description": f"成功发送 {sent_count} 封邮件，失败 {failed_count} 封",
            "status": "completed",
            "result": {
                "total": total_emails,
                "sent": sent_count,
                "failed": failed_count
            }
        })

        print(f"🎉 批量发送完成: 成功 {sent_count}/{total_emails} 封邮件")

    except Exception as e:
        print(f"❌ 批量发送邮件失败: {e}")
        await send_progress_update(f"batch_email_{search_id}", {
            "type": "completion",
            "step": "batch_failed",
            "title": "批量发送失败",
            "description": f"批量发送邮件时发生错误: {str(e)}",
            "status": "failed"
        })


