#!/usr/bin/env python3
"""
作者邮箱提取服务
基于现有的RealEmailFinder，专门用于批量提取论文作者邮箱
"""
import asyncio
import os
from typing import List, Dict, Optional
from .real_email_finder import RealEmailFinder
from .pdf_email_extractor import PDFEmailExtractor


class AuthorEmailExtractor:
    """作者邮箱提取器"""

    def __init__(self, proxy: Optional[str] = None):
        """
        初始化邮箱提取器

        Args:
            proxy: 代理设置，例如 "http://127.0.0.1:7890"
        """
        # 优先使用传入的代理，然后使用配置管理器
        if proxy:
            self.proxy = proxy
        else:
            # 导入代理配置管理器
            try:
                from backend.core.proxy_config import get_proxy
                self.proxy = get_proxy()
            except ImportError:
                # 回退到环境变量
                self.proxy = os.environ.get("SCHOLARDOCK_PROXY", "http://127.0.0.1:7890")

        self.email_finder = None
        self.pdf_extractor = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.email_finder = RealEmailFinder(proxy=self.proxy)
        await self.email_finder.__aenter__()

        self.pdf_extractor = PDFEmailExtractor(proxy=self.proxy)
        await self.pdf_extractor.__aenter__()

        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.email_finder:
            await self.email_finder.__aexit__(exc_type, exc_val, exc_tb)
        if self.pdf_extractor:
            await self.pdf_extractor.__aexit__(exc_type, exc_val, exc_tb)
    
    async def extract_author_emails(self, author_links: List[Dict[str, str]], progress_callback=None) -> Dict:
        """
        批量提取作者邮箱

        Args:
            author_links: 作者链接列表 [{"name": "作者名", "scholar_url": "Google Scholar链接"}]
            progress_callback: 进度回调函数

        Returns:
            一个包含作者邮箱和PDF回退邮箱的字典
        """
        if not self.email_finder:
            raise RuntimeError("EmailFinder not initialized. Use async context manager.")

        author_emails = []

        print(f"🔍 开始提取 {len(author_links)} 个作者的邮箱...")

        # 更新进度：开始提取
        if progress_callback:
            await progress_callback({
                "step": "start_extraction",
                "title": "开始邮箱提取",
                "description": f"开始提取 {len(author_links)} 个作者的邮箱",
                "status": "in_progress"
            })

        # 第一阶段：尝试从个人主页提取所有作者的邮箱
        for author_info in author_links:
            author_name = author_info.get('name', '')
            scholar_url = author_info.get('scholar_url', '')

            if not scholar_url:
                print(f"⚠️ 作者 {author_name} 没有Google Scholar链接")
                author_emails.append({
                    'name': author_name,
                    'email': None,
                    'email_source': 'no_scholar_link'
                })
                continue

            try:
                print(f"🔍 正在提取作者 {author_name} 的邮箱...")
                print(f"🔗 Google Scholar链接: {scholar_url}")

                # 更新进度：提取个人主页
                if progress_callback:
                    await progress_callback({
                        "step": "extract_personal_homepage",
                        "title": "提取个人主页",
                        "description": f"正在提取作者 {author_name} 的个人主页链接",
                        "status": "in_progress"
                    })

                # 从Google Scholar个人主页提取个人网站链接
                personal_homepage = await self.email_finder._get_personal_website_from_scholar_profile(scholar_url)

                if personal_homepage:
                    print(f"🏠 找到个人主页: {personal_homepage}")

                    # 更新进度：从个人网站提取邮箱
                    if progress_callback:
                        await progress_callback({
                            "step": "extract_from_website",
                            "title": "从个人网站提取邮箱",
                            "description": f"正在从 {author_name} 的个人网站提取邮箱",
                            "status": "in_progress"
                        })

                    # 从个人网站提取邮箱
                    emails = await self.email_finder._extract_emails_from_website(personal_homepage)

                    if emails:
                        primary_email = emails[0]  # 使用第一个邮箱作为主要邮箱
                        print(f"✅ 成功提取邮箱: {primary_email}")

                        author_emails.append({
                            'name': author_name,
                            'email': primary_email,
                            'email_source': 'personal_website',
                            'homepage': personal_homepage
                        })
                    else:
                        print(f"⚠️ 作者 {author_name} 的个人主页中未找到邮箱，尝试PDF回退...")
                        # 个人主页未找到，立即为该作者尝试PDF回退
                        pdf_emails = await self._extract_emails_from_pdf_fallback([author_info], progress_callback)
                        if pdf_emails:
                            primary_email = pdf_emails[0]
                            print(f"✅ PDF回退成功，找到邮箱: {primary_email}")
                            author_emails.append({
                                'name': author_name,
                                'email': primary_email,
                                'email_source': 'pdf_fallback',
                                'homepage': personal_homepage
                            })
                        else:
                            print(f"⚠️ PDF回退也未找到作者 {author_name} 的邮箱")
                            author_emails.append({
                                'name': author_name,
                                'email': None,
                                'email_source': 'not_found_in_pdf',
                                'homepage': personal_homepage
                            })
                else:
                    print(f"⚠️ 作者 {author_name} 没有设置个人主页，尝试PDF回退...")
                    # 没有个人主页，立即为该作者尝试PDF回退
                    pdf_emails = await self._extract_emails_from_pdf_fallback([author_info], progress_callback)
                    if pdf_emails:
                        primary_email = pdf_emails[0]
                        print(f"✅ PDF回退成功，找到邮箱: {primary_email}")
                        author_emails.append({
                            'name': author_name,
                            'email': primary_email,
                            'email_source': 'pdf_fallback',
                            'homepage': None  # 没有个人主页
                        })
                    else:
                        print(f"⚠️ PDF回退也未找到作者 {author_name} 的邮箱")
                        author_emails.append({
                            'name': author_name,
                            'email': None,
                            'email_source': 'no_homepage_and_not_in_pdf',
                            'homepage': None
                        })

            except Exception as e:
                print(f"❌ 提取作者 {author_name} 邮箱时出错: {e}")
                author_emails.append({
                    'name': author_name,
                    'email': None,
                    'email_source': 'error'
                })

        print(f"\n📊 最终邮箱提取结果:")
        final_successful = sum(1 for email_info in author_emails if email_info.get('email'))
        print(f"✅ 成功提取: {final_successful}/{len(author_links)}")
        
        final_result = {
            "author_emails": author_emails
        }

        # 更新进度：完成提取
        if progress_callback:
            await progress_callback({
                "step": "extraction_complete",
                "title": "邮箱提取完成",
                "description": f"完成 {len(author_links)} 个作者的邮箱提取，成功 {final_successful} 个",
                "status": "completed",
                "result": {
                    "successful_extractions": final_successful,
                    "total_authors": len(author_links),
                    "author_emails": author_emails,
                }
            })

        for email_info in author_emails:
            name = email_info.get('name', '未知')
            email = email_info.get('email', 'None')
            source = email_info.get('email_source', '未知')
            print(f"👤 {name}: {email} ({source})")
        
        # 返回包含所有结果的字典
        return final_result

    async def _extract_emails_from_pdf_fallback(self, author_links: List[Dict[str, str]], progress_callback=None) -> List[str]:
        """
        PDF回退功能：从所有作者的论文PDF中提取所有不重复的邮箱。

        Args:
            author_links: 作者链接列表
            progress_callback: 进度回调函数

        Returns:
            一个包含所有从PDF中找到的、去重后的邮箱列表。
        """
        try:
            print(f"🔍 尝试为 {len(author_links)} 个作者从PDF中提取邮箱...")
            
            all_pdf_emails = set()

            # 为每个作者尝试PDF回退
            for author_info in author_links:
                author_name = author_info.get('name')
                scholar_url = author_info.get('scholar_url')

                if not scholar_url or not author_name:
                    continue

                # 更新进度：开始单个作者的PDF提取
                if progress_callback:
                    await progress_callback({
                        "step": "pdf_fallback_author",
                        "title": f"PDF回退: {author_name}",
                        "description": f"正在为作者 {author_name} 查找论文PDF",
                        "status": "in_progress"
                    })

                # 获取该作者的PDF链接
                pdf_urls = await self._get_author_pdf_urls(scholar_url)
                if not pdf_urls:
                    print(f"⚠️ 未找到作者 {author_name} 的PDF链接")
                    continue

                # 尝试从该作者的所有PDF中提取邮箱
                for i, pdf_url in enumerate(pdf_urls[:3]):  # 最多尝试3个PDF
                    try:
                        print(f"\n{'='*20} PROCESSING PDF URL {'='*20}")
                        print(f"URL: {pdf_url}")
                        print(f"{'='*58}\n")
                        emails = await self.pdf_extractor.extract_emails_from_pdf_url(pdf_url)
                        if emails:
                            print(f"✅ 从PDF {pdf_url} 找到 {len(emails)} 个邮箱")
                            for email in emails:
                                if len(all_pdf_emails) < 3:
                                    all_pdf_emails.add(email)
                                else:
                                    break
                            if len(all_pdf_emails) >= 3:
                                break
                    except Exception as e:
                        print(f"❌ 处理PDF {pdf_url} 失败: {e}")
                        continue
                
                if len(all_pdf_emails) >= 3:
                    break

            # 更新进度：完成
            final_emails = list(all_pdf_emails)
            if progress_callback:
                await progress_callback({
                    "step": "pdf_fallback_complete",
                    "title": "PDF回退完成",
                    "description": f"从PDF中总共找到 {len(final_emails)} 个独立邮箱",
                    "status": "completed"
                })
            
            print(f"✅ PDF回退完成，返回 {len(final_emails)} 个邮箱。")
            return final_emails

        except Exception as e:
            print(f"❌ PDF回退功能失败: {e}")
            import traceback
            print(f"📍 PDF回退错误详情: {traceback.format_exc()}")
            return []

    async def _get_author_pdf_urls(self, scholar_url: str) -> List[str]:
        """
        从Google Scholar作者页面获取论文PDF链接

        Args:
            scholar_url: Google Scholar作者链接

        Returns:
            PDF链接列表
        """
        try:
            print(f"🔍 从Google Scholar获取PDF链接...")

            # 访问作者的Google Scholar页面
            async with self.email_finder.session.get(scholar_url, proxy=self.proxy) as response:
                if response.status != 200:
                    print(f"❌ 无法访问Google Scholar页面，状态码: {response.status}")
                    return []

                html_content = await response.text()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')

                pdf_urls = []

                # 方法1: 查找meta标签中的PDF链接
                print(f"📍 方法1: 查找meta标签中的citation_pdf_url...")
                meta_tags = soup.find_all('meta', attrs={'name': 'citation_pdf_url'})
                for meta in meta_tags:
                    pdf_url = meta.get('content')
                    if pdf_url:
                        # 确保是完整的URL
                        if not pdf_url.startswith('http'):
                            pdf_url = f"http:{pdf_url}" if pdf_url.startswith('//') else f"http://{pdf_url}"
                        pdf_urls.append(pdf_url)
                        print(f"✅ 从meta标签找到PDF: {pdf_url}")

                # 方法2: 查找论文标题链接中的PDF
                print(f"📍 方法2: 查找论文标题链接...")
                title_links = soup.find_all('a', class_='gsc_a_at')  # Google Scholar论文标题链接
                for link in title_links[:5]:  # 只检查前5篇论文
                    href = link.get('href')
                    if href:
                        try:
                            # 访问论文详情页面查找PDF链接
                            paper_url = href if href.startswith('http') else f"https://scholar.google.com{href}"
                            print(f"🔍 检查论文页面: {paper_url}")

                            async with self.email_finder.session.get(paper_url, proxy=self.proxy) as paper_response:
                                if paper_response.status == 200:
                                    paper_html = await paper_response.text()
                                    paper_soup = BeautifulSoup(paper_html, 'html.parser')

                                    # 在论文页面查找PDF链接
                                    pdf_links = paper_soup.find_all('a', href=True)
                                    for pdf_link in pdf_links:
                                        pdf_href = pdf_link.get('href')
                                        if pdf_href and ('.pdf' in pdf_href.lower() or 'arxiv.org/pdf' in pdf_href):
                                            if not pdf_href.startswith('http'):
                                                pdf_href = f"https:{pdf_href}" if pdf_href.startswith('//') else f"https://{pdf_href}"
                                            pdf_urls.append(pdf_href)
                                            print(f"✅ 从论文页面找到PDF: {pdf_href}")
                                            break  # 每篇论文只取第一个PDF链接
                        except Exception as e:
                            print(f"⚠️ 检查论文页面失败: {e}")
                            continue

                # 方法3: 直接在当前页面查找PDF链接
                print(f"📍 方法3: 直接查找PDF链接...")
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href')
                    if href and ('.pdf' in href.lower() or 'arxiv.org/pdf' in href):
                        # 处理相对链接
                        if href.startswith('/'):
                            href = f"https://scholar.google.com{href}"
                        elif href.startswith('//'):
                            href = f"https:{href}"
                        elif not href.startswith('http'):
                            href = f"https://{href}"

                        pdf_urls.append(href)
                        print(f"✅ 直接找到PDF链接: {href}")

                # 去重并限制数量
                unique_pdf_urls = list(dict.fromkeys(pdf_urls))  # 保持顺序的去重
                limited_pdf_urls = unique_pdf_urls[:5]  # 最多5个PDF

                print(f"🎯 总共找到 {len(limited_pdf_urls)} 个唯一PDF链接")
                for i, url in enumerate(limited_pdf_urls):
                    print(f"  {i+1}. {url}")

                return limited_pdf_urls

        except Exception as e:
            print(f"❌ 获取PDF链接失败: {e}")
            return []
    

    
    async def extract_single_author_email(self, author_name: str, scholar_url: str) -> Optional[Dict[str, str]]:
        """
        提取单个作者的邮箱
        
        Args:
            author_name: 作者名字
            scholar_url: Google Scholar链接
        
        Returns:
            作者邮箱信息或None
        """
        author_links = [{'name': author_name, 'scholar_url': scholar_url}]
        emails = await self.extract_author_emails(author_links)
        return emails[0] if emails else None


# 便捷函数
async def extract_authors_emails_from_links(author_links: List[Dict[str, str]], 
                                          proxy: Optional[str] = None) -> Dict:
    """
    便捷函数：从作者链接列表提取邮箱
    
    Args:
        author_links: 作者链接列表
        proxy: 代理设置
    
    Returns:
        作者邮箱列表
    """
    async with AuthorEmailExtractor(proxy=proxy) as extractor:
        return await extractor.extract_author_emails(author_links)


# 测试函数
async def test_author_email_extraction():
    """测试作者邮箱提取功能"""
    print("🧪 测试作者邮箱提取功能")
    print("=" * 60)

    # 测试数据
    test_author_links = [
        {
            'name': '测试作者1 (有主页)',
            'scholar_url': 'https://scholar.google.com/citations?user=zF9dr1sAAAAJ&hl=zh-CN&oi=sra'
        },
        {
            'name': 'Alex Krizhevsky (无主页)',
            'scholar_url': 'https://scholar.google.com/citations?user=JicYpd0AAAAJ&hl=en'
        }
    ]

    try:
        async with AuthorEmailExtractor() as extractor:
            emails = await extractor.extract_author_emails(test_author_links)

            print(f"\n📊 提取结果:")
            author_emails_list = emails.get('author_emails', [])
            if author_emails_list:
                for email_info in author_emails_list:
                    print(f"👤 作者: {email_info.get('name', 'N/A')}")
                    print(f"📧 邮箱: {email_info.get('email', 'N/A')}")
                    print(f"🔗 来源: {email_info.get('email_source', 'N/A')}")
                    if 'homepage' in email_info and email_info['homepage']:
                        print(f"🏠 主页: {email_info['homepage']}")
                    print("-" * 40)
            else:
                print("⚠️ 未找到任何真实邮箱")

            return emails

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return []


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_author_email_extraction())
