#!/usr/bin/env python3
"""
代理配置管理
"""
import os
from typing import Optional


class ProxyConfig:
    """代理配置管理器"""
    
    # 默认代理配置（按优先级排序）
    DEFAULT_PROXIES = [
        "http://127.0.0.1:7890",  # Clash
        "http://127.0.0.1:1080",  # V2Ray/Shadowsocks
    ]
    
    @classmethod
    def get_proxy(cls) -> Optional[str]:
        """
        获取代理配置
        
        优先级：
        1. 环境变量 SCHOLARDOCK_PROXY
        2. 默认代理配置
        
        Returns:
            代理URL或None
        """
        # 1. 环境变量
        env_proxy = os.environ.get("SCHOLARDOCK_PROXY")
        if env_proxy:
            return env_proxy
        
        # 2. 默认配置
        return cls.DEFAULT_PROXIES[0] if cls.DEFAULT_PROXIES else None
    
    @classmethod
    def set_proxy(cls, proxy_url: str):
        """
        设置代理（通过环境变量）
        
        Args:
            proxy_url: 代理URL
        """
        os.environ["SCHOLARDOCK_PROXY"] = proxy_url
    
    @classmethod
    def clear_proxy(cls):
        """清除代理设置"""
        if "SCHOLARDOCK_PROXY" in os.environ:
            del os.environ["SCHOLARDOCK_PROXY"]
    
    @classmethod
    def is_proxy_enabled(cls) -> bool:
        """检查是否启用了代理"""
        return cls.get_proxy() is not None


# 便捷函数
def get_proxy() -> Optional[str]:
    """获取代理配置"""
    return ProxyConfig.get_proxy()


def set_proxy(proxy_url: str):
    """设置代理"""
    ProxyConfig.set_proxy(proxy_url)


def clear_proxy():
    """清除代理"""
    ProxyConfig.clear_proxy()


def is_proxy_enabled() -> bool:
    """检查是否启用代理"""
    return ProxyConfig.is_proxy_enabled()


# 在模块加载时自动设置默认代理（如果没有环境变量）
if not os.environ.get("SCHOLARDOCK_PROXY"):
    # 设置默认代理
    default_proxy = ProxyConfig.get_proxy()
    if default_proxy:
        print(f"🔧 使用默认代理配置: {default_proxy}")
        os.environ["SCHOLARDOCK_PROXY"] = default_proxy
