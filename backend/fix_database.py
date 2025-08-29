#!/usr/bin/env python3
"""
手动修复数据库表结构
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.append(str(Path(__file__).parent))

from core.database import init_db, engine
from models.base import Base
from sqlalchemy import text


async def fix_database():
    """手动修复数据库表结构"""
    print("🔧 开始修复数据库表结构")
    print("=" * 60)
    
    try:
        # 1. 删除现有数据库文件（如果存在）
        db_file = "database.db"
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"✅ 删除现有数据库文件: {db_file}")
        else:
            print(f"ℹ️ 数据库文件不存在: {db_file}")
        
        # 2. 强制重新创建所有表
        print("🔄 强制重新创建所有表...")
        async with engine.begin() as conn:
            # 删除所有表
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ 删除所有现有表")
            
            # 重新创建所有表
            await conn.run_sync(Base.metadata.create_all)
            print("✅ 重新创建所有表")
        
        # 3. 验证表结构
        print("🔍 验证表结构...")
        async with engine.begin() as conn:
            # 检查articles表的列
            result = await conn.execute(text("PRAGMA table_info(articles)"))
            columns = result.fetchall()
            
            print("📊 articles表的列:")
            column_names = []
            for col in columns:
                column_names.append(col[1])  # col[1] 是列名
                print(f"  - {col[1]} ({col[2]})")  # col[2] 是数据类型
            
            # 检查pdf_emails列是否存在
            if 'pdf_emails' in column_names:
                print("✅ pdf_emails列存在")
            else:
                print("❌ pdf_emails列不存在")
                return False
            
            # 检查searches表
            result = await conn.execute(text("PRAGMA table_info(searches)"))
            columns = result.fetchall()
            
            print("\n📊 searches表的列:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        print("\n🎉 数据库表结构修复完成！")
        return True
        
    except Exception as e:
        print(f"❌ 修复数据库时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database():
    """测试数据库连接和基本操作"""
    print("\n🧪 测试数据库连接和基本操作")
    print("=" * 60)
    
    try:
        from core.database import AsyncSessionLocal
        from models.article import SearchDB, ArticleDB
        
        async with AsyncSessionLocal() as session:
            # 测试创建一个搜索记录
            search = SearchDB(
                keyword="test",
                num_results=10,
                year_filter=None,
                status="completed"
            )
            session.add(search)
            await session.commit()
            await session.refresh(search)
            
            print(f"✅ 成功创建搜索记录，ID: {search.id}")
            
            # 测试创建一个文章记录（包含pdf_emails字段）
            article = ArticleDB(
                search_id=search.id,
                title="Test Article",
                authors=["Test Author"],
                author_links=[],
                author_emails=[],
                pdf_emails=["test@example.com"],  # 测试pdf_emails字段
                venue="Test Venue",
                year=2024,
                citations=0,
                url="https://example.com"
            )
            session.add(article)
            await session.commit()
            await session.refresh(article)
            
            print(f"✅ 成功创建文章记录，ID: {article.id}")
            print(f"✅ pdf_emails字段值: {article.pdf_emails}")
            
            # 测试查询
            from sqlalchemy import select
            result = await session.execute(
                select(ArticleDB).where(ArticleDB.search_id == search.id)
            )
            articles = result.scalars().all()
            
            print(f"✅ 成功查询到 {len(articles)} 篇文章")
            
            return True
            
    except Exception as e:
        print(f"❌ 测试数据库时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("🎯 数据库修复工具")
    print("=" * 80)
    
    # 1. 修复数据库表结构
    success = await fix_database()
    if not success:
        print("❌ 数据库修复失败")
        return
    
    # 2. 测试数据库
    success = await test_database()
    if not success:
        print("❌ 数据库测试失败")
        return
    
    print("\n🎉 数据库修复和测试完成！")
    print("💡 现在可以重启后端服务了")


if __name__ == "__main__":
    asyncio.run(main())
