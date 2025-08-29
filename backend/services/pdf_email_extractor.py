#!/usr/bin/env python3
"""
PDF邮箱提取器
从论文PDF的第一页提取作者邮箱
"""
import re
import requests
import tempfile
import os
from typing import List, Optional, Set
from urllib.parse import urlparse
import aiohttp
import asyncio


class PDFEmailExtractor:
    """PDF邮箱提取器"""
    
    def __init__(self, proxy: Optional[str] = None):
        """
        初始化PDF邮箱提取器
        
        Args:
            proxy: 代理设置，例如 "http://127.0.0.1:7890"
        """
        self.proxy = proxy
        self.session = None
        
        # 检查PDF处理库
        self.pdf_libraries = self._check_pdf_libraries()
        
    def _check_pdf_libraries(self) -> dict:
        """检查可用的PDF处理库"""
        libraries = {}
        
        try:
            import PyPDF2
            libraries['PyPDF2'] = True
        except ImportError:
            libraries['PyPDF2'] = False
            
        try:
            import pdfplumber
            libraries['pdfplumber'] = True
        except ImportError:
            libraries['pdfplumber'] = False
            
        try:
            import fitz  # PyMuPDF
            libraries['PyMuPDF'] = True
        except ImportError:
            libraries['PyMuPDF'] = False
            
        return libraries
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector()
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def extract_emails_from_pdf_url(self, pdf_url: str) -> List[str]:
        """
        从PDF URL提取邮箱
        
        Args:
            pdf_url: PDF文件的URL
            
        Returns:
            提取到的邮箱列表
        """
        try:
            print(f"🔍 开始从PDF提取邮箱: {pdf_url}")
            
            # 下载PDF文件
            pdf_content = await self._download_pdf(pdf_url)
            if not pdf_content:
                print(f"❌ 无法下载PDF文件")
                return []
            
            # 提取第一页文本
            first_page_text = self._extract_first_page_text(pdf_content)
            if not first_page_text:
                print(f"❌ 无法提取PDF第一页文本")
                return []
            
            # 从文本中提取邮箱
            emails = self._extract_emails_from_text(first_page_text)
            
            print(f"🎉 从PDF第一页提取到 {len(emails)} 个邮箱")
            return emails
            
        except Exception as e:
            print(f"❌ PDF邮箱提取失败: {e}")
            return []
    
    async def _download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """下载PDF文件"""
        try:
            print(f"📥 下载PDF文件: {pdf_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with self.session.get(
                pdf_url, 
                headers=headers,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    print(f"✅ PDF下载成功，大小: {len(content)} bytes")
                    return content
                else:
                    print(f"❌ PDF下载失败，状态码: {response.status}")
                    return None
                    
        except Exception as e:
            print(f"❌ 下载PDF时出错: {e}")
            return None
    
    def _extract_first_page_text(self, pdf_content: bytes) -> Optional[str]:
        """提取PDF第一页文本"""
        
        # 尝试使用pdfplumber（推荐）
        if self.pdf_libraries.get('pdfplumber'):
            try:
                text = self._extract_with_pdfplumber(pdf_content)
                if text:
                    print(f"✅ 使用pdfplumber提取文本成功")
                    print("="*20 + " PDF PLUMBER RAW TEXT " + "="*20)
                    print(text)
                    print("="*50)
                    return text
            except Exception as e:
                print(f"⚠️ pdfplumber提取失败: {e}")
        
        # 尝试使用PyMuPDF
        if self.pdf_libraries.get('PyMuPDF'):
            try:
                text = self._extract_with_pymupdf(pdf_content)
                if text:
                    print(f"✅ 使用PyMuPDF提取文本成功")
                    print("="*20 + " PYMUPDF RAW TEXT " + "="*20)
                    print(text)
                    print("="*50)
                    return text
            except Exception as e:
                print(f"⚠️ PyMuPDF提取失败: {e}")
        
        # 尝试使用PyPDF2
        if self.pdf_libraries.get('PyPDF2'):
            try:
                text = self._extract_with_pypdf2(pdf_content)
                if text:
                    print(f"✅ 使用PyPDF2提取文本成功")
                    print("="*20 + " PYPDF2 RAW TEXT " + "="*20)
                    print(text)
                    print("="*50)
                    return text
            except Exception as e:
                print(f"⚠️ PyPDF2提取失败: {e}")
        
        print(f"❌ 所有PDF库都无法提取文本")
        return None
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> Optional[str]:
        """使用pdfplumber从内存中提取文本"""
        import pdfplumber
        import io
        
        try:
            with io.BytesIO(pdf_content) as pdf_stream:
                with pdfplumber.open(pdf_stream) as pdf:
                    if len(pdf.pages) > 0:
                        first_page = pdf.pages[0]
                        # 提取文本，同时保留布局信息，有助于查找邮箱
                        text = first_page.extract_text(x_tolerance=1, y_tolerance=3)
                        return text
        except Exception as e:
            print(f"⚠️ pdfplumber从内存流提取失败: {e}")
            # 作为备选方案，尝试临时文件方法
            return self._extract_with_pdfplumber_fallback(pdf_content)
        return None

    def _extract_with_pdfplumber_fallback(self, pdf_content: bytes) -> Optional[str]:
        """使用pdfplumber的临时文件回退方法"""
        import pdfplumber
        import tempfile
        import os
        
        tmp_file_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
                tmp_file.write(pdf_content)
            
            with pdfplumber.open(tmp_file_path) as pdf:
                if len(pdf.pages) > 0:
                    first_page = pdf.pages[0]
                    text = first_page.extract_text(x_tolerance=1, y_tolerance=3)
                    return text
        except Exception as e:
            print(f"⚠️ pdfplumber临时文件回退方法失败: {e}")
            return None
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        return None

    def _extract_with_pymupdf(self, pdf_content: bytes) -> Optional[str]:
        """使用PyMuPDF从内存中提取文本"""
        import fitz  # PyMuPDF
        import io

        try:
            # PyMuPDF可以直接从bytes打开
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            if len(doc) > 0:
                first_page = doc[0]
                text = first_page.get_text()
                doc.close()
                return text
        except Exception as e:
            print(f"⚠️ PyMuPDF从内存流提取失败: {e}")
        
        return None
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> Optional[str]:
        """使用PyPDF2提取文本"""
        import PyPDF2
        import io
        
        pdf_stream = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        
        if len(pdf_reader.pages) > 0:
            first_page = pdf_reader.pages[0]
            text = first_page.extract_text()
            return text
        
        return None
    
    def _extract_emails_from_text(self, text: str) -> List[str]:
        """从文本中提取邮箱"""
        emails = set()
        
        print(f"🔍 在PDF文本中搜索邮箱...")
        print(f"📄 文本长度: {len(text)} 字符")
        
        # 标准邮箱格式
        email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        matches = re.finditer(email_pattern, text, re.IGNORECASE)
        
        for match in matches:
            email = match.group(0).strip()
            if self._is_valid_email(email) and not self._is_spam_email(email):
                emails.add(email)
                print(f"✅ 找到邮箱: {email}")
        
        # 查找混淆格式的邮箱
        obfuscated_emails = self._find_obfuscated_emails_in_text(text)
        for email in obfuscated_emails:
            if self._is_valid_email(email) and not self._is_spam_email(email):
                emails.add(email)
                print(f"✅ 找到混淆邮箱: {email}")

        # 查找合并格式的邮箱（如 {user1,user2,user3}@domain.com）
        merged_emails = self._find_merged_emails_in_text(text)
        for email in merged_emails:
            if self._is_valid_email(email) and not self._is_spam_email(email):
                emails.add(email)
                print(f"✅ 找到合并格式邮箱: {email}")

        return list(emails)
    
    def _find_obfuscated_emails_in_text(self, text: str) -> List[str]:
        """在文本中查找混淆格式的邮箱"""
        emails = []
        
        # 基本的混淆格式
        patterns = [
            # AT/DOT格式
            r'\b([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+)\s+DOT\s+([a-zA-Z]{2,})\b',
            r'\b([a-zA-Z0-9._%+-]+)\s+at\s+([a-zA-Z0-9.-]+)\s+dot\s+([a-zA-Z]{2,})\b',
            
            # 完整域名格式
            r'\b([a-zA-Z0-9._%+-]+)\s*\[AT\]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            r'\b([a-zA-Z0-9._%+-]+)\s*\(AT\)\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            r'\b([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    if len(match.groups()) == 3:
                        # 三组格式
                        user_part = match.group(1).strip()
                        domain_part = match.group(2).strip()
                        tld_part = match.group(3).strip()
                        
                        domain_part = domain_part.replace(' dot ', '.').replace(' DOT ', '.')
                        email = f"{user_part}@{domain_part}.{tld_part}"
                        emails.append(email)
                        
                    elif len(match.groups()) == 2:
                        # 两组格式
                        user_part = match.group(1).strip()
                        domain_part = match.group(2).strip()
                        
                        email = f"{user_part}@{domain_part}"
                        emails.append(email)
                        
                except Exception as e:
                    continue
        
        return emails

    def _find_merged_emails_in_text(self, text: str) -> List[str]:
        """
        在文本中查找合并格式的邮箱

        支持的格式：
        - {user1,user2,user3}@domain.com
        - {shawnxxh,chongyangtao,hishentao}@gmail.com
        - {minglii,tianyi}@umd.edu

        Args:
            text: 要搜索的文本

        Returns:
            展开后的邮箱列表
        """
        emails = []

        try:
            print(f"🔍 搜索合并格式邮箱...")

            # 合并格式的正则表达式
            # 匹配 {user1,user2,user3}@domain.com 格式
            merged_pattern = r'\{([a-zA-Z0-9._-]+(?:,[a-zA-Z0-9._-]+)*)\}@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'

            matches = re.finditer(merged_pattern, text, re.IGNORECASE)

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
    
    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        if not email or '@' not in email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_spam_email(self, email: str) -> bool:
        """检查是否是垃圾邮箱"""
        email_lower = email.lower()
        
        spam_domains = [
            'example.com', 'test.com', 'demo.com',
            'localhost', '127.0.0.1', 'noreply'
        ]
        
        spam_prefixes = [
            'admin', 'test', 'demo', 'sample',
            'noreply', 'no-reply', 'donotreply'
        ]
        
        # 检查域名
        for domain in spam_domains:
            if domain in email_lower:
                return True
        
        # 检查前缀
        email_prefix = email_lower.split('@')[0] if '@' in email_lower else email_lower
        for prefix in spam_prefixes:
            if email_prefix == prefix:
                return True
        
        return False
