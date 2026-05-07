"""
Research Digest - Weekly Telegram Push
每週日晚上 21:00 自動執行

用法：
  python digest.py              # 正常執行（只推本週新論文）
  python digest.py --test       # 測試模式（強制推送，不管有沒有新論文）
  python digest.py --dry-run    # 只印報告，不發 Telegram
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

import chromadb
from sentence_transformers import SentenceTransformer

# ─── 設定 ─────────────────────────────────────────────────────────────
DB_PATH        = "D:/LLM/knowledge/biotech/db"
COLLECTION     = "biotech_papers"
STATE_FILE     = Path("D:/LLM/workflows/research/digest_state.json")
LLM_ENDPOINT   = "http://127.0.0.1:1234/v1/chat/completions"
LLM_MODEL      = "Qwen3.6-35B-A3B-Q6_K"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = "8703702788"

TOPICS_ZH = {
    "octacosanol":       "二十八烷醇/Policosanol",
    "astaxanthin_animal":"蝦青素（動物）",
    "bacillus_protease": "枯草菌蛋白酶",
    "ch_osa_silicon":    "ch-OSA 生物矽",
    "gut_health_poultry":"家禽腸道健康",
}

CAT_EMOJI = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "📖", "E": "⚫"}
TAG_EMOJI = {
    "competitive_intel":  "🔴",
    "defense_ammo":       "🛡️",
    "mechanism_support":  "🔬",
    "opportunity_scan":   "🌱",
    "self_validation":    "✅",
}

# ─── 狀態管理（記錄上次推送時間）─────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_push": "2000-01-01T00:00:00", "total_pushed": 0}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ─── 從 ChromaDB 拿本週新論文 ─────────────────────────────────────────
def get_new_papers(since_iso, test_mode=False):
    client = chromadb.PersistentClient(path=DB_PATH)
    coll = client.get_collection(COLLECTION)
    all_data = coll.get(include=["metadatas"])
    metas = all_data["metadatas"]

    if test_mode:
        # 測試模式：拿最近 20 篇
        metas_sorted = sorted(
            metas,
            key=lambda m: m.get("indexed_at", ""),
            reverse=True
        )
        return metas_sorted[:20]

    # 正常模式：拿 since_iso 之後 indexed 的論文
    new = [
        m for m in metas
        if m.get("indexed_at", "") > since_iso
    ]
    new.sort(key=lambda m: m.get("indexed_at", ""), reverse=True)
    return new

# ─── Qwen 生成每篇一句話要點 ──────────────────────────────────────────
def generate_one_liner(paper):
    intel = paper.get("intel_summary", "") or ""
    if len(intel) < 30:
        return ""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是動物營養競爭情報分析師。用一句話（30字內）點出這篇論文對業界的最重要意義。繁體中文。"},
            {"role": "user", "content": f"標題：{paper.get('title', '')[:100]}\n情報摘要：{intel[:300]}"},
        ],
        "temperature": 0.2,
        "max_tokens": 100,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        r = requests.post(LLM_ENDPOINT, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return intel[:80] + "..."

# ─── 組裝週報訊息 ────────────────────────────────────────────────────
def build_digest(new_papers, week_num, total_in_db, test_mode=False):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # 按戰略標籤分組
    by_tag = defaultdict(list)
    for p in new_papers:
        sv = p.get("strategic_value", "") or ""
        tags = [t.strip() for t in sv.split(",") if t.strip()]
        # 取第一個最重要的 tag
        if "competitive_intel" in tags:
            by_tag["competitive_intel"].append(p)
        elif "defense_ammo" in tags:
            by_tag["defense_ammo"].append(p)
        elif "opportunity_scan" in tags:
            by_tag["opportunity_scan"].append(p)
        elif "mechanism_support" in tags:
            by_tag["mechanism_support"].append(p)
        else:
            by_tag["self_validation"].append(p)

    # 各主題計數
    topic_counts = Counter(p.get("topic", "?") for p in new_papers)

    lines = []
    mode_tag = " 【測試】" if test_mode else ""
    lines.append(f"📊 *動物營養情報週報 #{week_num}*{mode_tag}")
    lines.append(f"_{date_str}_ | 主庫總計：{total_in_db} 篇")
    lines.append("")

    added_count = 0

    # 競爭警報（最重要）
    ci = by_tag["competitive_intel"]
    if ci:
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append("🔴 *競爭警報*")
        lines.append("━━━━━━━━━━━━━━━━━")
        for p in ci[:3]:
            cat = p.get("category", "?")
            topic_zh = TOPICS_ZH.get(p.get("topic", ""), p.get("topic", ""))
            year = p.get("year", "")
            country = p.get("country", "") or ""
            title = (p.get("title") or "")[:60]
            one_liner = generate_one_liner(p)
            actor = (p.get("lead_institution") or "N/A")[:30]
            url = p.get("url", "") or ""

            lines.append(f"{CAT_EMOJI.get(cat, '⬜')} [{topic_zh}] {year} {country}")
            lines.append(f"*{title}*")
            if one_liner:
                lines.append(f"💡 {one_liner}")
            if actor != "N/A":
                lines.append(f"🏛 {actor}")
            if url:
                lines.append(f"🔗 {url}")
            lines.append("")
            added_count += 1

    # 防禦彈藥
    da = by_tag["defense_ammo"]
    if da:
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append("🛡️ *防禦彈藥*")
        lines.append("━━━━━━━━━━━━━━━━━")
        for p in da[:3]:
            cat = p.get("category", "?")
            topic_zh = TOPICS_ZH.get(p.get("topic", ""), p.get("topic", ""))
            year = p.get("year", "")
            title = (p.get("title") or "")[:60]
            one_liner = generate_one_liner(p)
            url = p.get("url", "") or ""

            lines.append(f"{CAT_EMOJI.get(cat, '⬜')} [{topic_zh}] {year}")
            lines.append(f"*{title}*")
            if one_liner:
                lines.append(f"💡 {one_liner}")
            if url:
                lines.append(f"🔗 {url}")
            lines.append("")
            added_count += 1

    # 新機會
    opp = by_tag["opportunity_scan"]
    if opp:
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append("🌱 *新機會偵測*")
        lines.append("━━━━━━━━━━━━━━━━━")
        for p in opp[:2]:
            cat = p.get("category", "?")
            topic_zh = TOPICS_ZH.get(p.get("topic", ""), p.get("topic", ""))
            year = p.get("year", "")
            title = (p.get("title") or "")[:60]
            one_liner = generate_one_liner(p)
            url = p.get("url", "") or ""

            lines.append(f"{CAT_EMOJI.get(cat, '⬜')} [{topic_zh}] {year}")
            lines.append(f"*{title}*")
            if one_liner:
                lines.append(f"💡 {one_liner}")
            if url:
                lines.append(f"🔗 {url}")
            lines.append("")
            added_count += 1

    # 機制支持（只列標題，不逐一 LLM 處理）
    mech = by_tag["mechanism_support"]
    if mech:
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append("🔬 *機制研究*")
        lines.append("━━━━━━━━━━━━━━━━━")
        for p in mech[:3]:
            topic_zh = TOPICS_ZH.get(p.get("topic", ""), p.get("topic", ""))
            year = p.get("year", "")
            title = (p.get("title") or "")[:60]
            lines.append(f"• [{topic_zh}] {year} {title}")
        lines.append("")

    # 本週統計
    if topic_counts:
        lines.append("━━━━━━━━━━━━━━━━━")
        lines.append("📈 *本週新增分布*")
        lines.append("━━━━━━━━━━━━━━━━━")
        for topic, count in topic_counts.most_common():
            topic_zh = TOPICS_ZH.get(topic, topic)
            lines.append(f"• {topic_zh}：+{count} 篇")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━")
    lines.append("🔍 *深入查詢*")
    lines.append("在 QClaw chat 輸入問題，research\\-search skill 自動查主庫")

    return "\n".join(lines)

# ─── 發送 Telegram ────────────────────────────────────────────────────
def send_telegram(text, dry_run=False):
    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - 以下是要發送的內容：")
        print("=" * 60)
        print(text)
        print("=" * 60)
        return True

    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN 環境變數未設定")
        return False

    # Telegram 單訊息上限 4096 字，超過要切割
    chunks = []
    while len(text) > 4000:
        split_at = text.rfind("\n", 0, 4000)
        if split_at == -1:
            split_at = 4000
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    chunks.append(text)

    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": TELEGRAM_CHAT,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            print(f"[OK] Sent chunk {i+1}/{len(chunks)}")
        except Exception as e:
            print(f"[ERROR] Failed to send chunk {i+1}: {e}")
            # 嘗試移除 Markdown，用純文字重送
            payload["parse_mode"] = ""
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json=payload,
                    timeout=30,
                )
                print(f"[OK] Sent chunk {i+1} as plain text")
            except Exception as e2:
                print(f"[FAIL] {e2}")
                return False
    return True

# ─── 主流程 ──────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test",    action="store_true", help="測試模式（強制推送最近 20 篇）")
    ap.add_argument("--dry-run", action="store_true", help="只印不發")
    args = ap.parse_args()

    state = load_state()
    since = state["last_push"]
    week_num = state.get("total_pushed", 0) + 1

    print(f"[digest] 開始執行 | since={since} | test={args.test}")

    # 拿新論文
    new_papers = get_new_papers(since, test_mode=args.test)
    print(f"[digest] 找到 {len(new_papers)} 篇新論文")

    # 主庫總數
    client = chromadb.PersistentClient(path=DB_PATH)
    total_in_db = client.get_collection(COLLECTION).count()

    if not new_papers and not args.test:
        print("[digest] 本週無新論文，跳過推送")
        return

    # 建週報
    print(f"[digest] 生成週報（含 Qwen 一句話要點）...")
    digest_text = build_digest(new_papers, week_num, total_in_db, args.test)

    # 發送
    ok = send_telegram(digest_text, dry_run=args.dry_run)

    if ok and not args.dry_run:
        state["last_push"] = datetime.now().isoformat()
        state["total_pushed"] = week_num
        save_state(state)
        print(f"[digest] 完成 | week #{week_num} | 推送 {len(new_papers)} 篇")
    elif args.dry_run:
        print("[digest] dry-run 完成，state 未更新")

if __name__ == "__main__":
    main()
