# research-pipeline

競爭情報爬蟲 + AB 對照數據庫

## 架構

```
GitHub repo (public)          Cloudflare R2 (private)       EVO-X2 本地 (不上傳)
────────────────────          ───────────────────────        ───────────────────
.github/workflows/            configs/ingredients.yaml       b_group.db
collect/github_collector.py   raw_papers/latest.json         chromadb/
collect/credibility_scorer.py raw_papers/YYYY-WW.json        configs/*.yaml (本地副本)
collect/push_to_r2.py         models/ (GLD 模型)
local/upload_ingredients_to_r2.py
local/download_and_analyze.py
local/compare.py
```

## GitHub Secrets 必填

| Secret | 說明 |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare R2 帳號 ID |
| `R2_ACCESS_KEY_ID` | R2 存取金鑰 |
| `R2_SECRET_ACCESS_KEY` | R2 私密金鑰 |
| `R2_BUCKET` | bucket 名稱（richtrong-collect）|
| `SEMANTIC_SCHOLAR_KEY` | Semantic Scholar API key（選填）|
| `LENS_API_TOKEN` | Lens.org API token（選填，有則啟用專利）|

## 更新 ingredients.yaml 流程

```powershell
# 1. 編輯本地設定
notepad D:\LLM\workflows\research-pipeline-v2\configs\ingredients.yaml

# 2. 上傳到 R2（或由 Telegram 指揮台按鈕觸發）
cd D:\LLM\workflows\research-pipeline-v2
python local\upload_ingredients_to_r2.py

# 3. 下次 Actions 排程（每週六 19:00 UTC）自動讀取新設定
# 4. 或手動觸發：GitHub → Actions → Run workflow
```

## 排程

- 自動：每週六 19:00 UTC（= 週日 03:00 台灣時間）
- 手動：GitHub Actions → workflow_dispatch，可指定 topics 和 force_full
