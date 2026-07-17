"""
财务数据分析网站 - 全局配置文件
"""
import os
from pathlib import Path

# 项目路径
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ===== DeepSeek API 配置 =====
# 优先级：Streamlit Cloud Secrets > 环境变量
try:
    import streamlit as st
    DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
except (ImportError, FileNotFoundError):
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ===== 数据库配置（默认使用SQLite，PostgreSQL备选）=====
DB_TYPE = os.getenv("FINANCE_DB_TYPE", "sqlite")  # sqlite 或 postgresql
SQLITE_PATH = str(DATA_DIR / "finance_data.db")

# PostgreSQL 配置（部署时使用）
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "finance_data")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("PG_PASS", "postgres")

# ===== 爬虫配置 =====
SCRAPER_TIMEOUT = 30
SCRAPER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ===== 公司-股票代码映射缓存文件 =====
COMPANY_MAPPING_FILE = DATA_DIR / "company_mapping.json"

# ===== Streamlit 页面配置 =====
PAGE_TITLE = "财务数据分析平台"
PAGE_ICON = "📊"
LAYOUT = "wide"
