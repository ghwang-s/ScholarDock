import httpx
import asyncio
import re
import json
import os
from typing import List, Optional
from bs4 import BeautifulSoup
from datetime import datetime
import time # Re-add for synchronous selenium part

from core.config import settings
from core.proxy_config import get_proxy
from models.article import ArticleSchema

# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class OriginalScholarSpider:
    """Based on the original working google_scholar_spider.py"""
    
    def __init__(self):
        # Get the project root directory (one level up from 'backend')
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.base_url = 'https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5'
        self.startyear_url = '&as_ylo={}'
        self.endyear_url = '&as_yhi={}'
        self.robot_keywords = ['unusual traffic from your computer network', 'not a robot']
        self.session = None
        self.driver = None

        # User-Agent轮换
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        self.current_ua_index = 0

        # 配置代理
        self.proxy = get_proxy()
        self.proxies = None
        if self.proxy:
            self.proxies = {
                'http://': self.proxy,
                'https://': self.proxy
            }
            print(f"🔧 OriginalScholarSpider 使用代理: {self.proxy}")
        
    async def __aenter__(self):
        # Create an httpx async client
        self.session = httpx.AsyncClient(proxies=self.proxies, timeout=30)

        # Set User-Agent
        self.session.headers.update({
            'User-Agent': self.user_agents[self.current_ua_index]
        })
        print(f"🔧 使用User-Agent: {self.user_agents[self.current_ua_index]}")

        # Test proxy connection
        if self.proxies:
            await self._test_proxy_connection()

        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
        if self.driver:
            self.driver.quit()

    async def _test_proxy_connection(self):
        """测试代理连接"""
        try:
            print(f"🔧 测试代理连接: {self.proxy}")
            test_url = "https://www.google.com"
            response = await self.session.get(test_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ 代理连接正常")
            else:
                print(f"⚠️ 代理连接异常，状态码: {response.status_code}")
                raise Exception(f"代理连接测试失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ 代理连接失败: {e}")
            raise Exception(f"代理连接失败: {str(e)}，请检查代理服务是否正常运行")
    
    def _create_main_url(self, start_year: Optional[int] = None, end_year: Optional[int] = None) -> str:
        """Create main URL based on year filters"""
        gscholar_main_url = self.base_url
        
        if start_year:
            gscholar_main_url = gscholar_main_url + self.startyear_url.format(start_year)
            
        if end_year and end_year != datetime.now().year:
            gscholar_main_url = gscholar_main_url + self.endyear_url.format(end_year)
            
        return gscholar_main_url
    
    def _get_citations(self, content: str) -> int:
        """Extract citation count from content"""
        citation_start = content.find('Cited by ')
        if citation_start == -1:
            return 0
        citation_end = content.find('<', citation_start)
        try:
            return int(content[citation_start + 9:citation_end])
        except:
            return 0
    
    def _get_year(self, content: str) -> int:
        """Extract year from content"""
        try:
            for char in range(len(content)):
                if content[char] == '-':
                    out = content[char - 5:char - 1]
                    if out.isdigit():
                        return int(out)
        except:
            pass
        return 0
    
    def _get_author(self, content: str) -> str:
        """Extract author from content"""
        try:
            author_end = content.find('-')
            return content[2:author_end - 1] if author_end > 2 else content
        except:
            return "Author not found"

    def _get_author_and_links(self, gs_a_div) -> tuple[str, list]:
        """Extract author names and their Google Scholar profile links"""
        try:
            # 获取所有作者链接（前3个）
            author_links = []
            author_names = []

            # 查找所有作者链接
            links = gs_a_div.find_all('a', href=True)

            for link in links[:3]:  # 只取前3个作者
                href = link.get('href', '')
                # 检查是否是Google Scholar个人主页链接
                if 'citations?user=' in href:
                    # 确保是完整的URL
                    if href.startswith('/'):
                        href = 'https://scholar.google.com' + href
                    elif not href.startswith('http'):
                        href = 'https://scholar.google.com/' + href

                    author_name = link.text.strip()
                    if author_name:
                        author_links.append({
                            'name': author_name,
                            'scholar_url': href
                        })
                        author_names.append(author_name)

            # 如果没有找到作者链接，使用原来的方法提取作者名字
            if not author_names:
                gs_a_text = gs_a_div.text
                author_text = self._get_author(gs_a_text)
                return author_text, []

            # 返回作者名字字符串和链接列表
            authors_str = ', '.join(author_names)
            return authors_str, author_links

        except Exception as e:
            print(f"Error extracting author links: {e}")
            # 回退到原来的方法
            gs_a_text = gs_a_div.text if gs_a_div else ""
            return self._get_author(gs_a_text), []
    
    def _setup_driver(self):
        """Setup Chrome driver like the original code"""
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium not available")
            return None
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # Don't use headless mode for CAPTCHA solving
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"❌ Failed to setup Chrome driver: {e}")
            return None
    
    def _get_element_sync(self, driver, xpath, attempts=5, count=0):
        """Synchronous safe get_element method"""
        try:
            element = driver.find_element(By.XPATH, xpath)
            return element
        except Exception as e:
            if count < attempts:
                time.sleep(1)
                return self._get_element_sync(driver, xpath, attempts=attempts, count=count + 1)
            else:
                print("Element not found")
                return None
    
    def _get_content_with_selenium_sync(self, url):
        """Synchronous version of getting content with Selenium"""
        try:
            if not self.driver:
                self.driver = self._setup_driver()
            if not self.driver:
                return None

            print(f"🌐 Opening URL with Selenium: {url}")
            self.driver.get(url)

            el = self._get_element_sync(self.driver, "/html/body")
            if not el:
                return None

            content = el.get_attribute('innerHTML')

            if any(kw in content for kw in self.robot_keywords):
                print("🚨 CAPTCHA detected! Please solve manually...")
                print("The browser window should be open. Solve the CAPTCHA and the search will continue automatically.")
                
                time.sleep(30)  # Give user time to solve CAPTCHA

                self.driver.get(url)
                el = self._get_element_sync(self.driver, "/html/body")
                if el:
                    content = el.get_attribute('innerHTML')

            return content.encode('utf-8')
        except Exception as e:
            print(f"❌ Selenium error: {e}")
            return None

    async def _get_content_with_selenium(self, url):
        """Asynchronously run the synchronous Selenium logic in a separate thread"""
        if not SELENIUM_AVAILABLE:
            return None
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._get_content_with_selenium_sync, url
        )
    
    def _parse_gs_or_div(self, div) -> Optional[ArticleSchema]:
        """Parse a single gs_or div element to extract article data"""
        try:
            # Title and link
            title_elem = div.find('h3')
            if not title_elem:
                return None

            title_link = title_elem.find('a')
            if title_link:
                title = title_link.text.strip()
                url = title_link.get('href', '')
            else:
                title = title_elem.text.strip()
                url = None

            # Citations
            citations = self._get_citations(str(div))

            # Author info from gs_a div
            gs_a_div = div.find('div', {'class': 'gs_a'})
            if gs_a_div:
                gs_a_text = gs_a_div.text

                # Year
                year = self._get_year(gs_a_text)

                # Author and author links
                author, author_links = self._get_author_and_links(gs_a_div)

                # Publisher and venue
                try:
                    parts = gs_a_text.split("-")
                    publisher = parts[-1].strip() if len(parts) > 1 else "Publisher not found"

                    if len(parts) > 2:
                        venue_part = parts[-2]
                        venue = " ".join(venue_part.split(",")[:-1]).strip()
                    else:
                        venue = "Venue not found"
                except:
                    publisher = "Publisher not found"
                    venue = "Venue not found"
            else:
                year = 0
                author = "Author not found"
                author_links = []
                publisher = "Publisher not found"
                venue = "Venue not found"

            # Description from gs_rs div
            description = None
            gs_rs_div = div.find('div', {'class': 'gs_rs'})
            if gs_rs_div:
                description = gs_rs_div.text.strip()

            # Calculate citations per year
            citations_per_year = 0.0
            if year > 0 and citations > 0:
                years_passed = max(1, datetime.now().year - year)
                citations_per_year = round(citations / years_passed, 2)

            return ArticleSchema(
                title=title,
                authors=author,
                author_links=author_links,  # 新增字段
                venue=venue,
                publisher=publisher,
                year=year if year > 0 else None,
                citations=citations,
                citations_per_year=citations_per_year,
                description=description,
                url=url
            )
            
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None

    async def search(self, keyword: str, num_results: int = 50,
                     start_year: Optional[int] = None,
                     end_year: Optional[int] = None,
                     filter_by_title: bool = False,
                     exclude_duplicates: bool = False,
                     existing_titles: set = None) -> List[ArticleSchema]:
        """Search Google Scholar and optionally filter results by title."""
        
        articles = []
        gscholar_main_url = self._create_main_url(start_year, end_year)
        
        # Process keywords: split by comma and strip whitespace
        search_keywords = [k.strip().lower() for k in keyword.split(',') if k.strip()]
        
        print(f"🔍 Searching Google Scholar for '{keyword}' (target: {num_results} results)")
        if filter_by_title:
            print(f"🔎 Title filter enabled. Keywords to match: {search_keywords}")
        
        # Use existing titles from the database if provided
        history_titles = existing_titles if existing_titles is not None else set()
        if exclude_duplicates:
            print(f"🔎 Duplicate exclusion enabled. Using {len(history_titles)} titles from the database.")

        print(f"🌐 Using URL pattern: {gscholar_main_url}")
        
        # The number of results to fetch per page is 10
        # We may need to fetch more pages if filtering is enabled
        retrieved_articles = []
        n = 0
        # Safeguard to prevent infinite loops. Fetch a maximum of 50 pages.
        max_pages = 50
        page_num = 0

        while len(retrieved_articles) < num_results and page_num < max_pages:
            url = gscholar_main_url.format(str(n), keyword.replace(' ', '+'))
            print(f"📖 Fetching page {page_num + 1}, URL: {url}")
            
            try:
                # Make request with proxy
                print(f"🌐 发送请求到: {url}")
                if self.proxies:
                    print(f"🔧 使用代理: {self.proxies}")

                page = await self.session.get(url)
                print(f"📡 响应状态码: {page.status_code}")

                if page.status_code != 200:
                    print(f"❌ HTTP错误: {page.status_code}")
                    if page.status_code == 429:
                        print("🔄 检测到频率限制，等待30秒后重试...")
                        await asyncio.sleep(30)
                        # 重试一次
                        try:
                            page = await self.session.get(url)
                            if page.status_code == 200:
                                print("✅ 重试成功")
                            else:
                                raise Exception("重试后仍然被限制，请稍后再试")
                        except:
                            raise Exception("请求频率过高，被Google Scholar限制，请等待一段时间后重试")
                    elif page.status_code == 403:
                        raise Exception("访问被拒绝，可能被Google Scholar阻止")
                    else:
                        raise Exception(f"HTTP错误: {page.status_code}")

                content = page.content
                
                # Check for robot detection
                content_str = content.decode('ISO-8859-1', errors='ignore')
                if any(kw in content_str for kw in self.robot_keywords):
                    print("🤖 Robot checking detected, trying Selenium...")
                    # Use Selenium fallback like the original code
                    try:
                        content = await self._get_content_with_selenium(url)
                        if not content:
                            print("❌ Selenium fallback failed")
                            continue
                    except Exception as e:
                        print(f"❌ Selenium error: {e}")
                        continue
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser', from_encoding='utf-8')
                
                # Find articles using the original selector
                mydivs = soup.findAll("div", {"class": "gs_or"})
                print(f"📄 Found {len(mydivs)} article divs on this page")
                
                if not mydivs:
                    print("⚠️  No articles found, might be blocked or end of results")
                    break
                
                # Parse each article
                page_articles_count = 0
                for div in mydivs:
                    article = self._parse_gs_or_div(div)
                    if article and article.title and article.title != 'Could not catch title':
                        title_lower = article.title.lower()

                        # 1. Check for duplicates if enabled
                        if exclude_duplicates and title_lower in history_titles:
                            print(f"🚫 Parsed & Skipped (duplicate): {article.title[:60]}...")
                            continue

                        # 2. Check for title filter if enabled
                        if filter_by_title:
                            if any(phrase in title_lower for phrase in search_keywords):
                                retrieved_articles.append(article)
                                page_articles_count += 1
                                print(f"✅ Parsed & Matched: {article.title[:60]}...")
                            else:
                                print(f"🚫 Parsed & Skipped (title mismatch): {article.title[:60]}...")
                        else:
                            retrieved_articles.append(article)
                            page_articles_count += 1
                            print(f"✅ Parsed: {article.title[:60]}... ({article.citations} citations)")

                    if len(retrieved_articles) >= num_results:
                        break
                
                print(f"📊 Successfully parsed {page_articles_count} articles from this page")
                
                if len(retrieved_articles) >= num_results:
                    break
                
                # Increased delay to avoid rate limiting
                print("⏳ Waiting 5s before next request...")
                await asyncio.sleep(5)
                
                n += 10
                page_num += 1

            except Exception as e:
                print(f"❌ Error fetching page {page_num + 1}: {e}")

                # 如果是第一页就失败，抛出异常
                if page_num == 0:
                    print(f"🚨 第一页请求失败，无法继续搜索")
                    raise Exception(f"搜索失败: {str(e)}")

                # 其他页面失败则继续
                continue
        
        articles = retrieved_articles[:num_results]
        print(f"🎉 Search completed: {len(articles)} articles found")

        return articles