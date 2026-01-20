#!/usr/bin/env python3
"""
删除 query_view_history 表中 ts_min 和 ts_max 在 20251106 的数据

使用方法:
    python scripts/delete_query_view_history.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("delete_query_view_history")


def get_database_engine():
    """获取数据库引擎"""
    if not settings.database_url:
        logger.error("数据库连接未配置，请设置 DATABASE_URL 环境变量")
        return None
    
    try:
        logger.info(f"正在连接数据库: {settings.database_url[:50]}...")
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            connect_args={"connect_timeout": 5} if "postgresql" in settings.database_url.lower() else {},
        )
        logger.info("数据库连接成功")
        return engine
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return None


def check_table_structure(engine):
    """检查表结构"""
    try:
        inspector = inspect(engine)
        if "query_view_history" not in inspector.get_table_names():
            logger.error("表 query_view_history 不存在")
            return False
        
        columns = inspector.get_columns("query_view_history")
        logger.info("表 query_view_history 的列信息:")
        for col in columns:
            logger.info(f"  - {col['name']}: {col['type']}")
        
        # 检查是否有 ts_min 和 ts_max 列
        column_names = [col['name'] for col in columns]
        if 'ts_min' not in column_names or 'ts_max' not in column_names:
            logger.error("表 query_view_history 中不存在 ts_min 或 ts_max 列")
            return False
        
        return True
    except Exception as e:
        logger.error(f"检查表结构失败: {str(e)}")
        return False


def count_records_to_delete(engine, date_str):
    """统计要删除的记录数"""
    try:
        with engine.connect() as conn:
            # 尝试不同的日期格式
            date_formats = [
                f"DATE(ts_min) = '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'",
                f"DATE(ts_max) = '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'",
                f"ts_min >= '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} 00:00:00' AND ts_min < '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} 23:59:59'",
                f"ts_max >= '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} 00:00:00' AND ts_max < '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} 23:59:59'",
                f"ts_min = {date_str}",
                f"ts_max = {date_str}",
            ]
            
            # 先尝试查询，看看哪种格式能匹配
            for fmt in date_formats:
                try:
                    sql = f"SELECT COUNT(*) as cnt FROM query_view_history WHERE {fmt} OR {fmt.replace('ts_min', 'ts_max')}"
                    result = conn.execute(text(sql))
                    count = result.fetchone()[0]
                    if count > 0:
                        logger.info(f"使用格式 '{fmt}' 找到 {count} 条记录")
                        return count, fmt
                except Exception as e:
                    logger.debug(f"格式 '{fmt}' 查询失败: {str(e)}")
                    continue
            
            # 如果上面的都不行，使用更通用的查询
            sql = f"""
            SELECT COUNT(*) as cnt 
            FROM query_view_history 
            WHERE (
                DATE(ts_min) = '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}' 
                OR DATE(ts_max) = '{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
                OR ts_min::text LIKE '{date_str}%'
                OR ts_max::text LIKE '{date_str}%'
            )
            """
            result = conn.execute(text(sql))
            count = result.fetchone()[0]
            logger.info(f"找到 {count} 条记录（使用通用查询）")
            return count, None
            
    except Exception as e:
        logger.error(f"统计记录数失败: {str(e)}")
        return 0, None


def delete_records(engine, date_str):
    """删除记录"""
    try:
        # 转换日期格式：20251106 -> 2025-11-06
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        with engine.connect() as conn:
            # 构建删除 SQL
            # 删除 ts_min 或 ts_max 在指定日期的记录
            delete_sql = f"""
            DELETE FROM query_view_history 
            WHERE (
                DATE(ts_min) = '{date_formatted}' 
                OR DATE(ts_max) = '{date_formatted}'
                OR (ts_min::text LIKE '{date_str}%' AND ts_min IS NOT NULL)
                OR (ts_max::text LIKE '{date_str}%' AND ts_max IS NOT NULL)
            )
            """
            
            logger.info(f"执行删除 SQL: {delete_sql}")
            result = conn.execute(text(delete_sql))
            deleted_count = result.rowcount
            conn.commit()
            
            logger.info(f"成功删除 {deleted_count} 条记录")
            return deleted_count
            
    except Exception as e:
        logger.error(f"删除记录失败: {str(e)}")
        raise


def main():
    """主函数"""
    date_str = "20251106"
    
    logger.info("=" * 60)
    logger.info("删除 query_view_history 表中的数据")
    logger.info(f"目标日期: {date_str}")
    logger.info("=" * 60)
    
    # 获取数据库引擎
    engine = get_database_engine()
    if not engine:
        logger.error("无法获取数据库连接")
        return 1
    
    # 检查表结构
    if not check_table_structure(engine):
        logger.error("表结构检查失败")
        return 1
    
    # 统计要删除的记录数
    logger.info("\n正在统计要删除的记录数...")
    count, date_format = count_records_to_delete(engine, date_str)
    
    if count == 0:
        logger.info("没有找到需要删除的记录")
        return 0
    
    # 确认删除
    logger.info(f"\n找到 {count} 条记录需要删除")
    confirm = input("确认删除这些记录吗？(yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        logger.info("操作已取消")
        return 0
    
    # 执行删除
    logger.info("\n正在删除记录...")
    try:
        deleted_count = delete_records(engine, date_str)
        logger.info(f"\n✅ 成功删除 {deleted_count} 条记录")
        return 0
    except Exception as e:
        logger.error(f"\n❌ 删除失败: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
