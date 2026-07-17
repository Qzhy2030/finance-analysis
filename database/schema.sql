-- ============================================================
-- 财务数据分析平台 - PostgreSQL 数据库表结构
-- 适用场景：生产环境部署
-- ============================================================

-- 1. 公司基本信息表
CREATE TABLE IF NOT EXISTS companies (
    id              SERIAL PRIMARY KEY,
    stock_code      VARCHAR(10) UNIQUE NOT NULL,        -- 股票代码
    short_name      VARCHAR(100) NOT NULL,               -- 股票简称
    full_name       VARCHAR(300),                        -- 公司全称
    market          VARCHAR(10) DEFAULT 'SZ',            -- 市场：SH/SZ/BJ
    industry        VARCHAR(100),                        -- 所属行业
    listing_date    DATE,                                -- 上市日期
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_companies_code ON companies(stock_code);
CREATE INDEX idx_companies_name ON companies(short_name);

-- 2. 财务报表主表（资产负债表 / 利润表 / 现金流量表 归一化存储）
CREATE TABLE IF NOT EXISTS financial_statements (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_type     VARCHAR(20) NOT NULL,                -- balance / income / cashflow
    report_date     DATE NOT NULL,                       -- 报告期
    report_year     INTEGER NOT NULL,                    -- 报告年份
    report_quarter  INTEGER DEFAULT 4,                   -- 季度: 1/2/3/4
    item_code       VARCHAR(50) NOT NULL,                -- 科目代码
    item_name       VARCHAR(200) NOT NULL,               -- 科目名称
    amount          NUMERIC(20, 2),                      -- 金额（万元）
    currency        VARCHAR(10) DEFAULT 'CNY',
    source          VARCHAR(50) DEFAULT 'cninfo',        -- 数据来源
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, report_type, report_date, item_code)
);

CREATE INDEX idx_fs_company      ON financial_statements(company_id);
CREATE INDEX idx_fs_report_date  ON financial_statements(report_date);
CREATE INDEX idx_fs_type         ON financial_statements(report_type);

-- 3. 关键财务指标汇总表
CREATE TABLE IF NOT EXISTS financial_highlights (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_date     DATE NOT NULL,
    report_year     INTEGER NOT NULL,
    revenue         NUMERIC(20, 2),                     -- 营业收入（万元）
    net_profit      NUMERIC(20, 2),                     -- 净利润（万元）
    total_assets    NUMERIC(20, 2),                     -- 总资产（万元）
    total_liab      NUMERIC(20, 2),                     -- 总负债（万元）
    equity          NUMERIC(20, 2),                     -- 净资产（万元）
    gross_margin    NUMERIC(6, 4),                      -- 毛利率
    net_margin      NUMERIC(6, 4),                      -- 净利率
    roe             NUMERIC(6, 4),                      -- ROE
    eps             NUMERIC(10, 4),                     -- 每股收益
    bvps            NUMERIC(10, 4),                     -- 每股净资产
    source          VARCHAR(50) DEFAULT 'cninfo',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, report_date)
);

CREATE INDEX idx_fh_company   ON financial_highlights(company_id);
CREATE INDEX idx_fh_year      ON financial_highlights(report_year);

-- 4. 公司主营业务表
CREATE TABLE IF NOT EXISTS business_segments (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_year     INTEGER NOT NULL,
    segment_name    VARCHAR(200) NOT NULL,               -- 业务板块名称
    revenue         NUMERIC(20, 2),                     -- 该板块收入
    revenue_pct     NUMERIC(6, 4),                      -- 收入占比
    cost            NUMERIC(20, 2),                     -- 成本
    profit          NUMERIC(20, 2),                     -- 利润
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 在建工程项目表
CREATE TABLE IF NOT EXISTS construction_projects (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_year     INTEGER NOT NULL,
    project_name    VARCHAR(300) NOT NULL,               -- 项目名称
    budget_amount   NUMERIC(20, 2),                     -- 预算金额
    invested_amount NUMERIC(20, 2),                     -- 已投入金额
    progress_pct    NUMERIC(6, 4),                      -- 工程进度
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. AI 生成的财报分析报告表
CREATE TABLE IF NOT EXISTS analysis_reports (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    report_year     INTEGER NOT NULL,
    report_quarter  INTEGER DEFAULT 4,
    report_title    VARCHAR(300),
    report_html     TEXT,                                -- 完整 HTML 报告
    summary         TEXT,                                -- 摘要文本
    model_used      VARCHAR(100) DEFAULT 'deepseek-chat',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ar_company ON analysis_reports(company_id);
CREATE INDEX idx_ar_year    ON analysis_reports(report_year);

-- 7. 数据抓取日志表
CREATE TABLE IF NOT EXISTS scraper_logs (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(50) NOT NULL,                -- 数据来源
    company_id      INTEGER REFERENCES companies(id),
    report_type     VARCHAR(50),                         -- 抓取类型
    status          VARCHAR(20) DEFAULT 'pending',       -- pending/running/success/failed
    records_count   INTEGER DEFAULT 0,                   -- 抓取记录数
    error_message   TEXT,
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
