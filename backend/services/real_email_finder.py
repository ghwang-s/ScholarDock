#!/usr/bin/env python3
"""
真实邮箱查找器
从Google Scholar个人主页提取个人网站链接，然后从个人网站提取邮箱
"""
import asyncio
import aiohttp
import re
from typing import List, Optional
from bs4 import BeautifulSoup
import urllib.parse


class RealEmailFinder:
    """真实邮箱查找器"""
    
    def __init__(self, proxy: Optional[str] = None):
        """
        初始化邮箱查找器
        
        Args:
            proxy: 代理设置，例如 "http://127.0.0.1:7890"
        """
        self.proxy = proxy
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector()

        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=60)  # 增加超时时间
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def _get_personal_website_from_scholar_profile(self, scholar_url: str) -> Optional[str]:
        """
        从Google Scholar个人主页提取个人网站链接

        Args:
            scholar_url: Google Scholar个人主页URL

        Returns:
            个人网站URL或None
        """
        try:
            print(f"🌐 正在访问Google Scholar个人主页: {scholar_url}")

            # 设置代理
            proxy_url = self.proxy if self.proxy else None

            async with self.session.get(scholar_url, proxy=proxy_url) as response:
                if response.status != 200:
                    print(f"❌ 访问Google Scholar失败，状态码: {response.status}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # 查找个人主页链接
                homepage_links = []

                print(f"🔍 开始解析Google Scholar个人主页源代码...")

                # 方法1: 直接在页面源代码中搜索 github.io 链接
                print(f"📍 方法1: 在页面源代码中搜索 github.io 链接...")
                import re

                # 使用正则表达式在整个HTML源代码中查找github.io链接
                github_io_pattern = r'https?://[a-zA-Z0-9\-_.]+\.github\.io[/]?[^"\s<>]*'
                github_links = re.findall(github_io_pattern, html)

                for link in github_links:
                    # 清理链接，移除可能的尾部字符
                    clean_link = link.rstrip('",;')
                    if self._is_external_personal_website(clean_link):
                        homepage_links.append(clean_link)
                        print(f"✅ 从源代码正则匹配找到GitHub Pages: {clean_link}")

                # 方法2: 查找个人信息区域的链接
                print(f"📍 方法2: 查找个人信息区域的链接...")
                info_sections = [
                    soup.find('div', id='gsc_prf_i'),  # 个人信息主区域
                    soup.find('div', id='gsc_prf_ivh'),  # 个人信息验证区域
                    soup.find('div', class_='gsc_prf_il'),  # 个人信息列表
                ]

                for section in info_sections:
                    if section:
                        for link in section.find_all('a', href=True):
                            href = link.get('href')
                            if href and 'github.io' in href.lower():
                                if self._is_external_personal_website(href):
                                    homepage_links.append(href)
                                    print(f"✅ 从个人信息区域找到GitHub Pages: {href}")

                # 方法3: 查找所有包含github.io的链接
                print(f"📍 方法3: 查找所有包含github.io的链接...")
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href')
                    if href and 'github.io' in href.lower():
                        if self._is_external_personal_website(href):
                            homepage_links.append(href)
                            link_text = link.get_text().strip()
                            print(f"✅ 从HTML链接找到GitHub Pages: {href} (文本: {link_text})")

                # 方法4: 使用CSS选择器专门查找github.io链接
                print(f"📍 方法4: 使用CSS选择器查找github.io链接...")
                css_selectors = [
                    'a[href*="github.io"]',  # 直接查找包含github.io的链接
                    'a.gsc_prf_ila[href*="github.io"]',  # 个人信息区域的github.io链接
                ]

                for selector in css_selectors:
                    try:
                        links = soup.select(selector)
                        for link in links:
                            href = link.get('href')
                            if href and self._is_external_personal_website(href):
                                homepage_links.append(href)
                                print(f"✅ 从CSS选择器 {selector} 找到GitHub Pages: {href}")
                    except Exception as e:
                        print(f"⚠️ CSS选择器 {selector} 解析失败: {e}")

                # 方法5: 在页面文本中查找可能的github.io链接
                print(f"📍 方法5: 在页面文本中查找github.io链接...")
                page_text = soup.get_text()
                text_github_links = re.findall(github_io_pattern, page_text)
                for link in text_github_links:
                    clean_link = link.rstrip('",;')
                    if self._is_external_personal_website(clean_link):
                        homepage_links.append(clean_link)
                        print(f"✅ 从页面文本找到GitHub Pages: {clean_link}")

                # 去重
                homepage_links = list(set(homepage_links))

                if homepage_links:
                    print(f"🎯 总共找到 {len(homepage_links)} 个候选个人主页链接")

                    # 专门查找以 github.io/ 结尾的个人主页
                    github_pages_links = []
                    for link in homepage_links:
                        # 检查是否以 github.io/ 结尾（允许有或没有尾部斜杠）
                        if link.lower().rstrip('/').endswith('github.io'):
                            github_pages_links.append(link)
                            print(f"🎯 找到GitHub Pages个人主页: {link}")

                    if github_pages_links:
                        # 如果找到多个GitHub Pages链接，选择第一个
                        selected_link = github_pages_links[0]
                        print(f"✅ 选择GitHub Pages个人主页: {selected_link}")
                        return selected_link
                    else:
                        print(f"⚠️ 未找到以 github.io/ 结尾的个人主页")
                        print(f"📋 找到的链接:")
                        for i, link in enumerate(homepage_links):
                            print(f"   {i+1}. {link}")
                        print(f"💡 只接受以 github.io/ 结尾的个人主页")
                        return None

                print(f"⚠️ 未在Google Scholar个人主页中找到个人网站链接")
                return None

        except Exception as e:
            print(f"❌ 提取个人网站链接时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_external_personal_website(self, url: str) -> bool:
        """
        判断是否是外部个人网站链接（专门查找 GitHub Pages）

        Args:
            url: 要检查的URL

        Returns:
            是否是 GitHub Pages 个人网站
        """
        if not url:
            return False

        # 排除Google Scholar内部链接
        if 'scholar.google.com' in url:
            return False

        # 排除其他Google服务
        google_domains = ['google.com', 'gmail.com', 'googleusercontent.com', 'gstatic.com']
        if any(domain in url.lower() for domain in google_domains):
            return False

        # 排除明显的非个人网站
        excluded_patterns = [
            'javascript:', 'mailto:', '#',
            'facebook.com', 'twitter.com', 'linkedin.com',
            'researchgate.net', 'orcid.org'
        ]
        if any(pattern in url.lower() for pattern in excluded_patterns):
            return False

        # 必须是HTTP/HTTPS链接
        if not url.startswith(('http://', 'https://')):
            return False

        # 专门查找 GitHub Pages (以 github.io 结尾)
        if url.lower().rstrip('/').endswith('github.io'):
            return True

        # 不接受其他类型的个人网站
        return False
    
    async def _extract_emails_from_website(self, website_url: str) -> List[str]:
        """
        从个人网站提取邮箱，优先查找 mailto: 链接

        Args:
            website_url: 个人网站URL

        Returns:
            邮箱列表
        """
        try:
            print(f"🌐 正在访问个人网站: {website_url}")

            # 设置代理
            proxy_url = self.proxy if self.proxy else None

            async with self.session.get(website_url, proxy=proxy_url) as response:
                if response.status != 200:
                    print(f"❌ 访问个人网站失败，状态码: {response.status}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                emails = set()

                print(f"🔍 开始从个人网站提取邮箱...")

                # 只查找 mailto: 链接（最可靠且真实的方法）
                print(f"📧 查找 mailto: 链接...")
                mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))

                if mailto_links:
                    for i, link in enumerate(mailto_links):
                        href = link.get('href')
                        if href:
                            # 提取邮箱地址，处理 mailto:email@domain.com?subject=... 格式
                            email_part = href.replace('mailto:', '').split('?')[0].split('&')[0].strip()
                            if self._is_valid_email(email_part) and not self._is_spam_email(email_part):
                                emails.add(email_part)
                                print(f"✅ 从 mailto: 链接找到邮箱 {i+1}: {email_part}")
                                print(f"   完整链接: {href}")
                else:
                    print(f"⚠️ 未找到任何 mailto: 链接")

                # 在特定元素中查找 mailto: 链接
                print(f"📧 在特定元素中查找 mailto: 链接...")
                contact_selectors = [
                    '.contact', '.email', '#contact', '#email',
                    '.contact-info', '.contact-email', '.author-email',
                    '[class*="contact"]', '[class*="email"]', '[class*="mail"]',
                    '[id*="contact"]', '[id*="email"]', '[id*="mail"]',
                    'footer', '.footer', '#footer',
                    '.about', '#about', '.bio', '#bio'
                ]

                for selector in contact_selectors:
                    try:
                        elements = soup.select(selector)
                        for element in elements:
                            # 只检查元素中的 mailto 链接
                            element_mailto_links = element.find_all('a', href=re.compile(r'^mailto:', re.I))
                            for link in element_mailto_links:
                                href = link.get('href')
                                if href:
                                    email_part = href.replace('mailto:', '').split('?')[0].split('&')[0].strip()
                                    if self._is_valid_email(email_part) and not self._is_spam_email(email_part):
                                        emails.add(email_part)
                                        print(f"✅ 从 {selector} 元素的 mailto: 链接找到邮箱: {email_part}")
                    except Exception as e:
                        print(f"⚠️ 处理选择器 {selector} 时出错: {e}")
                        continue

                # 方法3: 查找页面文本中的标准邮箱格式（如 user@mail.domain.com）
                print(f"📧 方法3: 查找页面文本中的标准邮箱...")
                text_emails = self._find_text_emails(soup)
                for email in text_emails:
                    if self._is_valid_email(email) and not self._is_spam_email(email):
                        emails.add(email)
                        print(f"✅ 从页面文本找到邮箱: {email}")

                # 方法4: 查找混淆格式的邮箱（如 "user AT domain DOT com"）
                print(f"📧 方法4: 查找混淆格式的邮箱...")
                obfuscated_emails = self._find_obfuscated_emails(soup)
                for email in obfuscated_emails:
                    if self._is_valid_email(email) and not self._is_spam_email(email):
                        emails.add(email)
                        print(f"✅ 从混淆格式找到邮箱: {email}")

                # 方法5: 查找合并格式的邮箱（如 {user1,user2}@domain.com）
                print(f"📧 方法5: 查找合并格式的邮箱...")
                merged_emails = self._find_merged_emails(soup)
                for email in merged_emails:
                    if self._is_valid_email(email) and not self._is_spam_email(email):
                        emails.add(email)
                        print(f"✅ 从合并格式找到邮箱: {email}")

                email_list = list(emails)
                if email_list:
                    print(f"🎉 总共找到 {len(email_list)} 个真实邮箱 (仅来自 mailto: 链接):")
                    for i, email in enumerate(email_list):
                        print(f"   {i+1}. {email}")
                else:
                    print(f"⚠️ 未在个人网站中找到任何 mailto: 邮箱链接")

                return email_list

        except Exception as e:
            print(f"❌ 从个人网站提取邮箱时出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式是否有效"""
        if not email or len(email) > 254:
            return False
        
        # 基本的邮箱格式验证
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_spam_email(self, email: str) -> bool:
        """检查是否是垃圾邮箱或无效邮箱"""
        email_lower = email.lower()

        # 明显的垃圾邮箱域名
        spam_domains = [
            'example.com', 'test.com', 'dummy.com', 'localhost',
            'tempmail.com', '10minutemail.com', 'guerrillamail.com'
        ]

        # 通用的系统邮箱前缀
        spam_prefixes = [
            'noreply', 'no-reply', 'donotreply', 'do-not-reply',
            'admin', 'webmaster', 'info', 'support', 'contact',
            'hello', 'help', 'service', 'sales', 'marketing',
            'postmaster', 'mailer-daemon', 'root', 'daemon'
        ]

        # 检查域名
        for domain in spam_domains:
            if domain in email_lower:
                return True

        # 检查邮箱前缀（@符号前的部分）
        email_prefix = email_lower.split('@')[0] if '@' in email_lower else email_lower
        for prefix in spam_prefixes:
            if email_prefix == prefix:  # 完全匹配
                return True

        # 检查是否包含明显的测试字符串
        test_patterns = ['test', 'demo', 'sample', 'fake', 'invalid']
        for pattern in test_patterns:
            if pattern in email_prefix:
                return True

        return False

    def _find_text_emails(self, soup: BeautifulSoup) -> List[str]:
        """
        查找页面文本中的标准邮箱格式

        支持的格式：
        - user@mail.domain.com
        - researcher@cs.university.edu
        - admin@dept.nankai.edu.cn

        Args:
            soup: BeautifulSoup对象

        Returns:
            找到的邮箱列表
        """
        emails = []

        try:
            # 获取页面文本
            page_text = soup.get_text()

            # 标准邮箱的正则表达式
            # 匹配标准的邮箱格式，但排除已经在mailto链接中的
            email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'

            print(f"🔍 在页面文本中搜索标准邮箱格式...")

            # 查找所有匹配的邮箱
            matches = re.finditer(email_pattern, page_text, re.IGNORECASE)

            for match in matches:
                email = match.group(0).strip()

                # 检查是否已经在mailto链接中（避免重复）
                if not self._is_email_in_mailto_links(soup, email):
                    emails.append(email)
                    print(f"✅ 找到文本邮箱: {email}")
                else:
                    print(f"⚠️ 邮箱已在mailto链接中，跳过: {email}")

            # 去重
            unique_emails = list(set(emails))

            if unique_emails:
                print(f"🎯 总共找到 {len(unique_emails)} 个文本邮箱")
            else:
                print(f"⚠️ 未找到文本邮箱")

            return unique_emails

        except Exception as e:
            print(f"❌ 查找文本邮箱时出错: {e}")
            return []

    def _is_email_in_mailto_links(self, soup: BeautifulSoup, email: str) -> bool:
        """
        检查邮箱是否已经在mailto链接中

        Args:
            soup: BeautifulSoup对象
            email: 要检查的邮箱

        Returns:
            如果邮箱已在mailto链接中返回True，否则返回False
        """
        try:
            import re
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))

            for link in mailto_links:
                href = link.get('href')
                if href:
                    # 提取mailto链接中的邮箱
                    email_part = href.replace('mailto:', '').split('?')[0].split('&')[0].strip()
                    if email_part.lower() == email.lower():
                        return True

            return False

        except Exception as e:
            print(f"⚠️ 检查mailto链接时出错: {e}")
            return False

    def _find_obfuscated_emails(self, soup: BeautifulSoup) -> List[str]:
        """
        查找混淆格式的邮箱

        支持的格式：
        - user AT domain DOT com
        - user at domain dot com
        - user [AT] domain [DOT] com
        - user (at) domain (dot) com
        - fushuo.huo AT connect dot polyu dot hk

        Args:
            soup: BeautifulSoup对象

        Returns:
            找到的邮箱列表
        """
        emails = []

        try:
            # 获取页面文本
            page_text = soup.get_text()

            # 定义混淆邮箱的正则表达式模式
            obfuscated_patterns = [
                # 基本的 AT/DOT 格式（域名被DOT分隔）
                r'\b([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+)\s+DOT\s+([a-zA-Z]{2,})\b',
                r'\b([a-zA-Z0-9._%+-]+)\s+at\s+([a-zA-Z0-9.-]+)\s+dot\s+([a-zA-Z]{2,})\b',

                # 带括号的格式（域名被DOT分隔）
                r'\b([a-zA-Z0-9._%+-]+)\s*\[AT\]\s*([a-zA-Z0-9.-]+)\s*\[DOT\]\s*([a-zA-Z]{2,})\b',
                r'\b([a-zA-Z0-9._%+-]+)\s*\(at\)\s*([a-zA-Z0-9.-]+)\s*\(dot\)\s*([a-zA-Z]{2,})\b',
                r'\b([a-zA-Z0-9._%+-]+)\s*\(AT\)\s*([a-zA-Z0-9.-]+)\s*\(DOT\)\s*([a-zA-Z]{2,})\b',

                # 更复杂的格式，支持多个点（如 connect dot polyu dot hk）
                r'\b([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+(?:\s+dot\s+[a-zA-Z0-9.-]+)*)\s+dot\s+([a-zA-Z]{2,})\b',
                r'\b([a-zA-Z0-9._%+-]+)\s+at\s+([a-zA-Z0-9.-]+(?:\s+dot\s+[a-zA-Z0-9.-]+)*)\s+dot\s+([a-zA-Z]{2,})\b',
            ]

            # 新增：完整域名格式（域名不被DOT分隔，如 user [AT] mail.nankai.edu.cn）
            complete_domain_patterns = [
                # 带括号的完整域名格式
                r'\b([a-zA-Z0-9._%+-]+)\s*\[AT\]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                r'\b([a-zA-Z0-9._%+-]+)\s*\(AT\)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                r'\b([a-zA-Z0-9._%+-]+)\s*\(at\)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',

                # 基本的完整域名格式
                r'\b([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                r'\b([a-zA-Z0-9._%+-]+)\s+at\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            ]

            print(f"🔍 在页面文本中搜索混淆邮箱...")

            # 处理传统的三组格式（user AT domain DOT tld）
            for pattern in obfuscated_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)

                for match in matches:
                    try:
                        if len(match.groups()) == 3:
                            # 基本格式：user AT domain DOT tld
                            user_part = match.group(1).strip()
                            domain_part = match.group(2).strip()
                            tld_part = match.group(3).strip()

                            # 处理域名部分可能包含多个 dot 的情况
                            domain_part = domain_part.replace(' dot ', '.').replace(' DOT ', '.')

                            # 构建邮箱
                            email = f"{user_part}@{domain_part}.{tld_part}"
                            emails.append(email)

                            print(f"✅ 找到混淆邮箱（三组格式）: {match.group(0)} → {email}")

                    except Exception as e:
                        print(f"⚠️ 解析混淆邮箱时出错: {e}")
                        continue

            # 处理完整域名格式（user [AT] complete.domain.com）
            for pattern in complete_domain_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)

                for match in matches:
                    try:
                        if len(match.groups()) == 2:
                            # 完整域名格式：user [AT] complete.domain.com
                            user_part = match.group(1).strip()
                            domain_part = match.group(2).strip()

                            # 直接构建邮箱
                            email = f"{user_part}@{domain_part}"
                            emails.append(email)

                            print(f"✅ 找到混淆邮箱（完整域名格式）: {match.group(0)} → {email}")

                    except Exception as e:
                        print(f"⚠️ 解析完整域名混淆邮箱时出错: {e}")
                        continue

            # 特殊处理：查找 "Email:" 后面的混淆格式
            # 三组格式（域名被DOT分隔）
            email_patterns_3groups = [
                r'Email:\s*([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+(?:\s+dot\s+[a-zA-Z0-9.-]+)*)\s+dot\s+([a-zA-Z]{2,})',
                r'E-mail:\s*([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+(?:\s+dot\s+[a-zA-Z0-9.-]+)*)\s+dot\s+([a-zA-Z]{2,})',
                r'Contact:\s*([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+(?:\s+dot\s+[a-zA-Z0-9.-]+)*)\s+dot\s+([a-zA-Z]{2,})',
            ]

            for pattern in email_patterns_3groups:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)

                for match in matches:
                    try:
                        user_part = match.group(1).strip()
                        domain_part = match.group(2).strip()
                        tld_part = match.group(3).strip()

                        # 处理域名部分
                        domain_part = domain_part.replace(' dot ', '.').replace(' DOT ', '.')

                        # 构建邮箱
                        email = f"{user_part}@{domain_part}.{tld_part}"
                        emails.append(email)

                        print(f"✅ 从Email标签找到混淆邮箱（三组格式）: {match.group(0)} → {email}")

                    except Exception as e:
                        print(f"⚠️ 解析Email标签混淆邮箱时出错: {e}")
                        continue

            # 两组格式（完整域名）
            email_patterns_2groups = [
                r'Email:\s*([a-zA-Z0-9._%+-]+)\s*\[AT\]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'E-mail:\s*([a-zA-Z0-9._%+-]+)\s*\[AT\]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'Contact:\s*([a-zA-Z0-9._%+-]+)\s*\[AT\]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'Email:\s*([a-zA-Z0-9._%+-]+)\s*\(AT\)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'E-mail:\s*([a-zA-Z0-9._%+-]+)\s*\(AT\)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'Contact:\s*([a-zA-Z0-9._%+-]+)\s*\(AT\)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'Email:\s*([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'E-mail:\s*([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'Contact:\s*([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            ]

            for pattern in email_patterns_2groups:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)

                for match in matches:
                    try:
                        user_part = match.group(1).strip()
                        domain_part = match.group(2).strip()

                        # 直接构建邮箱
                        email = f"{user_part}@{domain_part}"
                        emails.append(email)

                        print(f"✅ 从Email标签找到混淆邮箱（完整域名格式）: {match.group(0)} → {email}")

                    except Exception as e:
                        print(f"⚠️ 解析Email标签完整域名混淆邮箱时出错: {e}")
                        continue

            # 去重
            unique_emails = list(set(emails))

            if unique_emails:
                print(f"🎯 总共找到 {len(unique_emails)} 个混淆格式邮箱")
            else:
                print(f"⚠️ 未找到混淆格式邮箱")

            return unique_emails

        except Exception as e:
            print(f"❌ 查找混淆邮箱时出错: {e}")
            return []

    def _find_merged_emails(self, soup: BeautifulSoup) -> List[str]:
        """
        查找合并格式的邮箱

        支持的格式：
        - {user1,user2,user3}@domain.com
        - {shawnxxh,chongyangtao,hishentao}@gmail.com
        - {minglii,tianyi}@umd.edu

        Args:
            soup: BeautifulSoup对象

        Returns:
            展开后的邮箱列表
        """
        emails = []

        try:
            # 获取页面文本
            page_text = soup.get_text()

            print(f"🔍 在页面文本中搜索合并格式邮箱...")

            # 合并格式的正则表达式
            # 匹配 {user1,user2,user3}@domain.com 格式
            merged_pattern = r'\{([a-zA-Z0-9._-]+(?:,[a-zA-Z0-9._-]+)*)\}@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'

            matches = re.finditer(merged_pattern, page_text, re.IGNORECASE)

            for match in matches:
                try:
                    users_part = match.group(1)  # user1,user2,user3
                    domain_part = match.group(2)  # domain.com

                    # 分割用户名
                    usernames = [username.strip() for username in users_part.split(',')]

                    print(f"🎯 找到合并格式: {{{users_part}}}@{domain_part}")
                    print(f"📧 包含 {len(usernames)} 个用户名: {usernames}")

                    # 为每个用户名生成邮箱
                    for username in usernames:
                        if username:  # 确保用户名不为空
                            email = f"{username}@{domain_part}"
                            emails.append(email)
                            print(f"   ✅ 展开邮箱: {email}")

                except Exception as e:
                    print(f"⚠️ 处理合并格式时出错: {e}")
                    continue

            # 去重
            unique_emails = list(set(emails))

            if unique_emails:
                print(f"🎯 总共展开 {len(unique_emails)} 个合并格式邮箱")
            else:
                print(f"⚠️ 未找到合并格式邮箱")

            return unique_emails

        except Exception as e:
            print(f"❌ 查找合并格式邮箱时出错: {e}")
            return []


# 测试函数
async def test_email_finder():
    """测试邮箱查找器"""
    print("🧪 测试RealEmailFinder")
    print("=" * 50)
    
    test_url = "https://scholar.google.com/citations?user=zF9dr1sAAAAJ&hl=zh-CN&oi=sra"
    
    async with RealEmailFinder() as finder:
        # 测试提取个人主页
        homepage = await finder._get_personal_website_from_scholar_profile(test_url)
        print(f"个人主页: {homepage}")
        
        if homepage:
            # 测试提取邮箱
            emails = await finder._extract_emails_from_website(homepage)
            print(f"找到的邮箱: {emails}")


if __name__ == "__main__":
    asyncio.run(test_email_finder())
