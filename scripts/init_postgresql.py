#!/usr/bin/env python3
"""
PostgreSQL 数据库初始化脚本
用于生产环境部署时一键创建数据库和表结构

使用：
    python scripts/init_postgresql.py                    # 默认配置
    python scripts/init_postgresql.py --host 127.0.0.1   # 指定主机
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import subprocess

from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS
from config import SQLITE_PATH, DATA_DIR


def check_postgresql():
    """检查PostgreSQL是否可用"""
    try:
        result = subprocess.run(
            ["psql", "--version"],
            capture_output=True, text=True, timeout=5
        )
        print(f"✅ PostgreSQL客户端可用: {result.stdout.strip()}")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠ 未检测到psql客户端")
        return False


def init_with_sqlalchemy():
    """使用SQLAlchemy初始化PostgreSQL数据库"""
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import OperationalError

        # 先连接到默认的postgres数据库创建目标数据库
        default_url = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/postgres"
        engine = create_engine(default_url)

        with engine.connect() as conn:
            conn.execute(text("COMMIT"))  # 结束事务
            # 检查数据库是否存在
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname='{PG_DB}'")
            )
            if result.fetchone():
                print(f"✅ 数据库 '{PG_DB}' 已存在")
            else:
                conn.execute(text(f'CREATE DATABASE "{PG_DB}" ENCODING "UTF8"'))
                print(f"✅ 数据库 '{PG_DB}' 创建成功")
        engine.dispose()

        # 连接到目标数据库创建表结构
        db_url = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
        engine = create_engine(db_url)

        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with engine.connect() as conn:
            conn.execute(text(schema_sql))
            conn.commit()

        print("✅ 所有表结构创建成功")
        engine.dispose()
        return True

    except ImportError:
        print("❌ 请先安装SQLAlchemy: pip install sqlalchemy psycopg2-binary")
        return False
    except OperationalError as e:
        print(f"❌ PostgreSQL连接失败: {e}")
        print("  请确保PostgreSQL服务已启动")
        print(f"  Host: {PG_HOST}:{PG_PORT}")
        print(f"  User: {PG_USER}")
        return False
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False


def init_sqlite_fallback():
    """回退到SQLite（开发模式）"""
    print(f"\n📦 回退到SQLite模式:")
    print(f"   数据库路径: {SQLITE_PATH}")

    from database.db_manager import get_db
    db = get_db()
    db.init_db()

    # 验证
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"   已创建 {len(tables)} 张表: {', '.join(tables)}")
    print("✅ SQLite 数据库初始化完成")
    return True


def migrate_data():
    """从SQLite迁移数据到PostgreSQL"""
    print("\n🔄 数据迁移...")

    try:
        from sqlalchemy import create_engine, MetaData, Table
        import sqlite3

        # 读取SQLite数据
        sqlite_conn = sqlite3.connect(SQLITE_PATH)
        sqlite_conn.row_factory = sqlite3.Row

        # 连接到PostgreSQL
        pg_url = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
        pg_engine = create_engine(pg_url)
        pg_meta = MetaData()
        pg_meta.reflect(bind=pg_engine)

        tables_to_migrate = ["companies", "financial_highlights"]

        for table_name in tables_to_migrate:
            if table_name not in pg_meta.tables:
                print(f"  ⚠ 表 {table_name} 不存在于PostgreSQL，跳过")
                continue

            cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if not rows:
                print(f"  - {table_name}: 无数据，跳过")
                continue

            pg_table = pg_meta.tables[table_name]
            columns = [col.name for col in pg_table.columns
                       if col.name != "id" and not col.name.startswith("created")]

            with pg_engine.connect() as conn:
                for row in rows:
                    row_dict = dict(row)
                    data = {col: row_dict.get(col) for col in columns}
                    conn.execute(pg_table.insert().values(**data))
                conn.commit()

            print(f"  ✅ {table_name}: 迁移 {len(rows)} 条记录")

        sqlite_conn.close()
        pg_engine.dispose()
        print("✅ 数据迁移完成")

    except Exception as e:
        print(f"  ⚠ 数据迁移跳过: {e}")


def main():
    parser = argparse.ArgumentParser(description="数据库初始化工具")
    parser.add_argument("--host", default=PG_HOST, help="PostgreSQL主机")
    parser.add_argument("--port", type=int, default=PG_PORT, help="PostgreSQL端口")
    parser.add_argument("--db", default=PG_DB, help="数据库名")
    parser.add_argument("--user", default=PG_USER, help="用户名")
    parser.add_argument("--password", default=PG_PASS, help="密码")
    parser.add_argument("--migrate", action="store_true",
                        help="同时从SQLite迁移数据到PostgreSQL")
    parser.add_argument("--force-sqlite", action="store_true",
                        help="强制使用SQLite")
    args = parser.parse_args()

    print("=" * 60)
    print("🗄️  财务数据分析平台 - 数据库初始化")
    print("=" * 60)

    if args.force_sqlite:
        init_sqlite_fallback()
        return

    # 检查PostgreSQL
    if check_postgresql():
        print(f"\n🔌 正在连接 PostgreSQL:")
        print(f"   Host: {args.host}:{args.port}")
        print(f"   DB:   {args.db}")
        print(f"   User: {args.user}")

        success = init_with_sqlalchemy()
        if success and args.migrate:
            migrate_data()
    else:
        print("\n⚠ PostgreSQL不可用，使用SQLite作为本地数据库")
        init_sqlite_fallback()


if __name__ == "__main__":
    main()
