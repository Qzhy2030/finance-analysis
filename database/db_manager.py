"""
数据库管理器
开发环境使用 SQLite，生产环境自动切换 PostgreSQL
"""
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import DB_TYPE, SQLITE_PATH

# ── 建表 SQL（SQLite 兼容版）───────────────────────────

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code      VARCHAR(10) UNIQUE NOT NULL,
    short_name      VARCHAR(100) NOT NULL,
    full_name       VARCHAR(300),
    market          VARCHAR(10) DEFAULT 'SZ',
    industry        VARCHAR(100),
    listing_date    TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS financial_highlights (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_date     TEXT NOT NULL,
    report_year     INTEGER NOT NULL,
    revenue         REAL,
    net_profit      REAL,
    total_assets    REAL,
    total_liab      REAL,
    equity          REAL,
    gross_margin    REAL,
    net_margin      REAL,
    roe             REAL,
    eps             REAL,
    bvps            REAL,
    source          TEXT DEFAULT 'cninfo',
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(company_id, report_date)
);

CREATE TABLE IF NOT EXISTS financial_statements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_type     VARCHAR(20) NOT NULL,
    report_date     TEXT NOT NULL,
    report_year     INTEGER NOT NULL,
    report_quarter  INTEGER DEFAULT 4,
    item_code       VARCHAR(50) NOT NULL,
    item_name       VARCHAR(200) NOT NULL,
    amount          REAL,
    currency        VARCHAR(10) DEFAULT 'CNY',
    source          TEXT DEFAULT 'cninfo',
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(company_id, report_type, report_date, item_code)
);

CREATE TABLE IF NOT EXISTS business_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_year     INTEGER NOT NULL,
    segment_name    VARCHAR(200) NOT NULL,
    revenue         REAL,
    revenue_pct     REAL,
    cost            REAL,
    profit          REAL,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS construction_projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_year     INTEGER NOT NULL,
    project_name    VARCHAR(300) NOT NULL,
    budget_amount   REAL,
    invested_amount REAL,
    progress_pct    REAL,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_year     INTEGER NOT NULL,
    report_quarter  INTEGER DEFAULT 4,
    report_title    TEXT,
    report_html     TEXT,
    summary         TEXT,
    model_used      TEXT DEFAULT 'deepseek-chat',
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS scraper_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          VARCHAR(50) NOT NULL,
    company_id      INTEGER REFERENCES companies(id),
    report_type     TEXT,
    status          TEXT DEFAULT 'pending',
    records_count   INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);
"""


class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self, db_path: str = SQLITE_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    def init_db(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        cursor.executescript(SQLITE_SCHEMA)
        self.conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── 公司相关 ──────────────────────────────────────

    def upsert_company(self, stock_code: str, short_name: str,
                       full_name: str = "", market: str = "SZ",
                       industry: str = "") -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO companies (stock_code, short_name, full_name, market, industry)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(stock_code) DO UPDATE SET
                short_name=excluded.short_name,
                full_name=excluded.full_name,
                market=excluded.market,
                industry=excluded.industry,
                updated_at=datetime('now','localtime')
        """, (stock_code, short_name, full_name, market, industry))
        self.conn.commit()
        # 获取确定性的company_id
        cursor.execute("SELECT id FROM companies WHERE stock_code=?", (stock_code,))
        row = cursor.fetchone()
        return row["id"] if row else cursor.lastrowid or 0

    def get_company(self, company_id: int) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE id=?", (company_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_company_by_code(self, code: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE stock_code=?", (code,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ── 财务数据 ──────────────────────────────────────

    def save_highlights(self, company_id: int, data: dict):
        """保存/更新财务指标汇总"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO financial_highlights
                (company_id, report_date, report_year,
                 revenue, net_profit, total_assets, total_liab, equity,
                 gross_margin, net_margin, roe, eps, bvps, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id, report_date) DO UPDATE SET
                revenue=excluded.revenue, net_profit=excluded.net_profit,
                total_assets=excluded.total_assets, total_liab=excluded.total_liab,
                equity=excluded.equity, gross_margin=excluded.gross_margin,
                net_margin=excluded.net_margin, roe=excluded.roe,
                eps=excluded.eps, bvps=excluded.bvps
        """, (
            company_id, data["report_date"], data["report_year"],
            data.get("revenue"), data.get("net_profit"),
            data.get("total_assets"), data.get("total_liab"), data.get("equity"),
            data.get("gross_margin"), data.get("net_margin"),
            data.get("roe"), data.get("eps"), data.get("bvps"),
            data.get("source", "cninfo"),
        ))
        self.conn.commit()

    def get_highlights(self, company_id: int, years: int = 5) -> List[dict]:
        """获取公司最近N年的财务指标"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM financial_highlights
            WHERE company_id=?
            ORDER BY report_year DESC, report_date DESC
            LIMIT ?
        """, (company_id, years))
        return [dict(row) for row in cursor.fetchall()]

    def get_revenue_trend(self, company_id: int) -> List[dict]:
        """获取营收趋势数据"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT report_year, report_date, revenue, net_profit
            FROM financial_highlights
            WHERE company_id=? AND revenue IS NOT NULL
            ORDER BY report_year ASC, report_date ASC
        """, (company_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ── 业务板块 ──────────────────────────────────────

    def save_business_segments(self, company_id: int, segments: List[dict]):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM business_segments WHERE company_id=?", (company_id,))
        for seg in segments:
            cursor.execute("""
                INSERT INTO business_segments
                    (company_id, report_year, segment_name, revenue, revenue_pct, cost, profit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_id, seg["report_year"], seg["segment_name"],
                  seg.get("revenue"), seg.get("revenue_pct"),
                  seg.get("cost"), seg.get("profit")))
        self.conn.commit()

    # ── 在建工程 ──────────────────────────────────────

    def save_projects(self, company_id: int, projects: List[dict]):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM construction_projects WHERE company_id=?", (company_id,))
        for proj in projects:
            cursor.execute("""
                INSERT INTO construction_projects
                    (company_id, report_year, project_name, budget_amount, invested_amount, progress_pct)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (company_id, proj["report_year"], proj["project_name"],
                  proj.get("budget_amount"), proj.get("invested_amount"),
                  proj.get("progress_pct")))
        self.conn.commit()

    # ── 分析报告 ──────────────────────────────────────

    def save_report(self, company_id: int, report_year: int, report_quarter: int,
                    title: str, html: str, summary: str = "",
                    model: str = "deepseek-chat") -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO analysis_reports
                (company_id, report_year, report_quarter, report_title, report_html, summary, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (company_id, report_year, report_quarter, title, html, summary, model))
        self.conn.commit()
        return cursor.lastrowid

    def get_reports(self, company_id: int, limit: int = 10) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM analysis_reports
            WHERE company_id=?
            ORDER BY created_at DESC LIMIT ?
        """, (company_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    # ── 爬虫日志 ──────────────────────────────────────

    def log_scraper(self, source: str, company_id: Optional[int] = None,
                    report_type: str = "", status: str = "pending",
                    records: int = 0, error: str = ""):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scraper_logs
                (source, company_id, report_type, status, records_count, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source, company_id, report_type, status, records, error))
        self.conn.commit()


    # ── 同步状态查询（去重检测） ────────────────────

    def get_synced_company_codes(self) -> set:
        """查询已有财务数据的公司股票代码集合"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.stock_code FROM companies c
            INNER JOIN financial_highlights fh ON c.id = fh.company_id
        """)
        return {row[0] for row in cursor.fetchall()}

    def is_company_synced(self, stock_code: str) -> bool:
        """检查某公司是否已有财务数据"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM companies WHERE stock_code=?", (stock_code,))
        company_row = cursor.fetchone()
        if not company_row:
            return False
        cursor.execute(
            "SELECT COUNT(*) FROM financial_highlights WHERE company_id=?",
            (company_row["id"],)
        )
        return cursor.fetchone()[0] > 0

    def get_company_sync_detail(self, stock_code: str) -> dict:
        """获取某公司的同步详情（记录数、最近同步时间等）"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM companies WHERE stock_code=?", (stock_code,))
        company_row = cursor.fetchone()
        if not company_row:
            return {"synced": False, "records": 0, "last_sync": None, "years": []}
        cid = company_row["id"]
        cursor.execute("""
            SELECT COUNT(*) as cnt, MAX(created_at) as last_sync
            FROM financial_highlights WHERE company_id=?
        """, (cid,))
        row = cursor.fetchone()
        cursor.execute("""
            SELECT DISTINCT report_year FROM financial_highlights
            WHERE company_id=? ORDER BY report_year DESC
        """, (cid,))
        years = [r[0] for r in cursor.fetchall()]
        return {
            "synced": row["cnt"] > 0,
            "records": row["cnt"],
            "last_sync": row["last_sync"],
            "years": years,
        }

    def get_unsynced_companies(self) -> list:
        """查询所有未同步财务数据的公司（LEFT JOIN找出缺少highlights的公司）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.id, c.stock_code, c.short_name, c.full_name, c.market, c.industry
            FROM companies c
            LEFT JOIN financial_highlights fh ON c.id = fh.company_id
            WHERE fh.id IS NULL
            ORDER BY c.industry, c.stock_code
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_sync_summary(self) -> dict:
        """获取整体同步状态概览"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM companies")
        total = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(DISTINCT company_id) FROM financial_highlights
        """)
        synced = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM financial_highlights")
        total_records = cursor.fetchone()[0]
        cursor.execute("""
            SELECT c.industry, COUNT(DISTINCT c.id) as total,
                   COUNT(DISTINCT fh.company_id) as synced
            FROM companies c
            LEFT JOIN financial_highlights fh ON c.id = fh.company_id
            GROUP BY c.industry
            ORDER BY c.industry
        """)
        by_industry = [dict(row) for row in cursor.fetchall()]
        return {
            "total_companies": total,
            "synced_companies": synced,
            "unsynced_companies": total - synced,
            "total_records": total_records,
            "by_industry": by_industry,
        }

    def get_all_companies_sync_status(self) -> list:
        """获取所有公司的同步状态（含已/未同步标记）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.id, c.stock_code, c.short_name, c.full_name, c.market, c.industry,
                   COUNT(fh.id) as record_count,
                   MAX(fh.created_at) as last_sync
            FROM companies c
            LEFT JOIN financial_highlights fh ON c.id = fh.company_id
            GROUP BY c.id
            ORDER BY record_count DESC, c.stock_code
        """)
        return [dict(row) for row in cursor.fetchall()]
_db: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db
