-- ============================================================
-- market_data.db  Schema v1.0
-- 市場情報數據庫：各物種 × 地區 × 時間的養殖參數與價格
-- 用途：ROI銷售工具 / 內部定價分析 / 競品B組對標
-- ============================================================

-- 主表：市場 KPI 數值記錄
CREATE TABLE IF NOT EXISTS market_kpi (
    id              TEXT PRIMARY KEY,          -- sha256(region+species+kpi_id+source_url)
    region          TEXT NOT NULL,             -- CN_north/CN_south/CN_central/CN_northwest/TW_all/SEA_*
    country         TEXT,                      -- CN/TW/TH/VN/ID/MY/PH
    species         TEXT NOT NULL,             -- layer_hen/broiler/finisher_pig/livestock/shrimp/tilapia
    production_stage TEXT,                     -- starter/grower/finisher/peak/mid/late
    kpi_id          TEXT NOT NULL,             -- 對應 species_metrics.yaml kpi_id
    kpi_label       TEXT,                      -- 顯示名稱
    value           REAL,                      -- 數值
    value_min       REAL,                      -- 範圍下限（若有）
    value_max       REAL,                      -- 範圍上限（若有）
    unit            TEXT,                      -- % / ratio / CNY/500g / kg / days
    year            INTEGER,                   -- 數據所屬年份
    quarter         TEXT,                      -- Q1/Q2/Q3/Q4（若有）
    month           INTEGER,                   -- 月份（1-12，若有）
    credibility     INTEGER CHECK(credibility BETWEEN 1 AND 5),
    source_type     TEXT CHECK(source_type IN (
                    'gov_stats','industry_media','vendor_whitepaper',
                    'academic_background','market_report','social')),
    source_url      TEXT,
    source_title    TEXT,
    raw_text        TEXT,                      -- 原始段落（保留原文供驗證）
    language        TEXT DEFAULT 'zh-CN',
    confirmed       INTEGER DEFAULT 0,         -- 0=待人工確認 1=已確認
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- ROI 計算參數表（銷售工具用）
CREATE TABLE IF NOT EXISTS roi_params (
    id              TEXT PRIMARY KEY,
    region          TEXT NOT NULL,
    species         TEXT NOT NULL,
    product_dose_kg_per_ton REAL DEFAULT 20,   -- 每噸飼料添加量（固定20kg）
    feed_cost_per_ton REAL,                    -- 飼料成本 CNY/噸
    product_cost_per_kg REAL,                  -- 產品成本 CNY/kg（留空，內部填）
    baseline_fcr    REAL,                      -- 對照組FCR
    improved_fcr    REAL,                      -- 添加後FCR
    baseline_metric TEXT,                      -- 改善指標說明
    improvement_pct REAL,                      -- 改善幅度 %
    roi_ratio       REAL,                      -- 計算結果 1:X
    currency        TEXT DEFAULT 'CNY',
    year            INTEGER,
    source_kpi_ids  TEXT,                      -- JSON array，引用哪些 market_kpi.id
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 競品市場動向表
CREATE TABLE IF NOT EXISTS competitor_market (
    id              TEXT PRIMARY KEY,
    competitor_id   TEXT NOT NULL,             -- 對應 ingredients.yaml id（competitor/adjacent）
    competitor_name TEXT,
    region          TEXT,
    market_claim    TEXT,                      -- 競品宣稱效果
    claim_metric    TEXT,                      -- 宣稱指標
    claim_value     REAL,
    claim_unit      TEXT,
    species         TEXT,
    price_per_kg    REAL,                      -- 競品價格 CNY/kg（若已知）
    source_url      TEXT,
    source_type     TEXT,
    credibility     INTEGER CHECK(credibility BETWEEN 1 AND 5),
    year            INTEGER,
    raw_text        TEXT,
    confirmed       INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 新指標提議表（Qwen 發現市場中出現的新 KPI）
CREATE TABLE IF NOT EXISTS market_kpi_proposals (
    id              TEXT PRIMARY KEY,
    kpi_name        TEXT NOT NULL,
    kpi_unit        TEXT,
    species         TEXT,
    region          TEXT,
    source_url      TEXT,
    example_text    TEXT,
    proposed_at     TEXT DEFAULT (datetime('now')),
    status          TEXT DEFAULT 'pending'
        CHECK(status IN ('pending','approved','rejected')),
    approved_at     TEXT,
    rejection_note  TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_mk_region     ON market_kpi(region);
CREATE INDEX IF NOT EXISTS idx_mk_species    ON market_kpi(species);
CREATE INDEX IF NOT EXISTS idx_mk_kpi        ON market_kpi(kpi_id);
CREATE INDEX IF NOT EXISTS idx_mk_year       ON market_kpi(year);
CREATE INDEX IF NOT EXISTS idx_mk_confirmed  ON market_kpi(confirmed);
CREATE INDEX IF NOT EXISTS idx_mk_credibility ON market_kpi(credibility);
CREATE INDEX IF NOT EXISTS idx_roi_region    ON roi_params(region, species);
CREATE INDEX IF NOT EXISTS idx_cm_competitor ON competitor_market(competitor_id);
CREATE INDEX IF NOT EXISTS idx_cm_region     ON competitor_market(region, species);
CREATE INDEX IF NOT EXISTS idx_mkp_status    ON market_kpi_proposals(status);
