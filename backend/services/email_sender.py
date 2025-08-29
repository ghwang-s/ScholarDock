#!/usr/bin/env python3
"""
邮件发送服务
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Dict, Any, Optional
import logging
from jinja2 import Template
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""
    
    def __init__(self):
        """初始化邮件发送器"""
        # 从环境变量读取邮件配置
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')

        # 如果环境变量没有，尝试从settings读取
        if not self.email_address or not self.email_password:
            try:
                from core.config import settings
                self.email_address = settings.email_address
                self.email_password = settings.email_password
            except ImportError:
                pass

        if not self.email_address or not self.email_password:
            raise ValueError("邮件配置不完整，请检查 .env 文件中的 EMAIL_ADDRESS 和 EMAIL_PASSWORD")
        
        # 163邮箱SMTP配置
        self.smtp_server = "smtp.163.com"
        self.smtp_port = 465  # SSL端口
        
        logger.info(f"邮件发送器初始化完成，发送方: {self.email_address}")
    
    def load_email_template(self, template_data: Dict[str, Any]) -> str:
        """加载并渲染邮件模板"""
        try:
            # 读取邮件模板文件
            template_path = Path(__file__).parent.parent.parent / "templates" / "email_template.html"
            
            if not template_path.exists():
                raise FileNotFoundError(f"邮件模板文件不存在: {template_path}")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 使用Jinja2渲染模板
            template = Template(template_content)
            
            # 准备模板变量
            author_name = template_data.get('author_name', 'Dear Researcher')
            template_vars = {
                'author_name': author_name,
                'paper_title': template_data.get('paper_title', 'your research'),
                'paper_venue_text': self._format_venue_text(template_data.get('paper_venue')),
                'paper_year_text': self._format_year_text(template_data.get('paper_year')),
                'sender_email': self.email_address
            }
            
            rendered_content = template.render(**template_vars)
            logger.info(f"邮件模板渲染成功，作者: {template_vars['author_name']}")
            
            return rendered_content
            
        except Exception as e:
            logger.error(f"加载邮件模板失败: {e}")
            raise
    
    def _format_venue_text(self, venue: Optional[str]) -> str:
        """格式化期刊/会议信息"""
        # 不再生成"published in"文本
        return ""
    
    def _format_year_text(self, year: Optional[int]) -> str:
        """格式化年份信息"""
        if year:
            return f" ({year})"
        return ""
    

    
    def send_email(self, 
                   to_email: str, 
                   subject: str, 
                   template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            template_data: 模板数据，包含作者信息、论文信息等
            
        Returns:
            发送结果字典
        """
        try:
            logger.info(f"开始发送邮件到: {to_email}")
            
            # 渲染邮件内容
            html_content = self.load_email_template(template_data)
            
            # 创建邮件对象
            msg = MIMEMultipart('alternative')
            msg['From'] = Header(f"Guanghui Wang <{self.email_address}>", 'utf-8')
            msg['To'] = Header(to_email, 'utf-8')
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 连接SMTP服务器并发送邮件
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            logger.info(f"邮件发送成功: {to_email}")
            
            return {
                'success': True,
                'message': '邮件发送成功',
                'to_email': to_email,
                'subject': subject,
                'sent_at': None  # 可以添加时间戳
            }
            
        except Exception as e:
            error_msg = f"邮件发送失败: {str(e)}"
            logger.error(f"发送邮件到 {to_email} 失败: {e}")
            
            return {
                'success': False,
                'message': error_msg,
                'to_email': to_email,
                'subject': subject,
                'error': str(e)
            }
    
    def preview_email(self, template_data: Dict[str, Any]) -> str:
        """
        预览邮件内容（不发送）
        
        Args:
            template_data: 模板数据
            
        Returns:
            渲染后的HTML内容
        """
        try:
            html_content = self.load_email_template(template_data)
            logger.info("邮件预览生成成功")
            return html_content
            
        except Exception as e:
            logger.error(f"生成邮件预览失败: {e}")
            raise
    
    def validate_email_config(self) -> Dict[str, Any]:
        """
        验证邮件配置
        
        Returns:
            验证结果
        """
        try:
            # 测试SMTP连接
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.email_address, self.email_password)
            
            return {
                'valid': True,
                'message': '邮件配置验证成功',
                'email_address': self.email_address,
                'smtp_server': self.smtp_server
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'邮件配置验证失败: {str(e)}',
                'email_address': self.email_address,
                'error': str(e)
            }


# 全局邮件发送器实例
email_sender = None

def get_email_sender() -> EmailSender:
    """获取邮件发送器实例"""
    global email_sender
    if email_sender is None:
        email_sender = EmailSender()
    return email_sender
