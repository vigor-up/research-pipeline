"""
Research Knowledge Base Search Engine
Used by both: standalone CLI and OpenClaw skill
"""

import sys
import json
import argparse
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
import requests

DB_PATH = "D:/LLM/knowledge/biotech/db"
COLLECTION = "biotech_papers"
EMBED_MODEL = "BAAI/bge-m3"
LLM_ENDPOINT = "http://127.0.0.1:1234/v1/chat/completions"
LLM_MODEL = "Qwen3.6-35B-A3B-Q6_K"

_model_cache = {"embed": None}


def get_embed_model():
    if _model_cache["embed"] is None:
        _model_cache["embed"] = SentenceTransformer(EMBED_MODEL)
    return _model_cache["embed"]


def search(query, k=10, topic=None, category=None, strategic_value=None,
           min_quality=0, year_from=None):
    client = chromadb.PersistentClient(path=DB_PATH)
    coll = client.get_collection(COLLECTION)
    model = get_embed_model()

    qvec = model.encode([query], normalize_embeddings=True).tolist()

    where_clauses = []
    if topic:
        where_clauses.append({"topic": topic})
    if category:
        where_clauses.append({"category": category})
    if min_quality > 0:
        where_clauses.append({"quality_score": {"$gte": min_quality}})
    where = None
    if len(where_clauses) == 1:
        where = where_clauses[0]
    elif len(where_clauses) > 1:
        where = {"$and": where_clauses}

    results = coll.query(
        query_embeddings=qvec,
        n_results=k * 3,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for i in range(len(results["documents"][0])):
        meta = results["metadatas"][0][i]
        doc = results["documents"][0][i]
        dist = results["distances"][0][i]

        if strategic_value:
            sv = meta.get("strategic_value", "") or ""
            if strategic_value not in sv:
                continue

        if year_from:
            try:
                if int(meta.get("year", "0") or "0") < int(year_from):
                    continue
            except ValueError:
                pass

        hits.append({
            "similarity": round(1 - dist, 3),
            "title": meta.get("title", ""),
            "year": meta.get("year", ""),
            "topic": meta.get("topic", ""),
            "category": meta.get("category", ""),
            "category_label": meta.get("category_label", ""),
            "quality": meta.get("quality_score", 0),
            "species": meta.get("species", ""),
            "compound": meta.get("compound", ""),
            "dose": meta.get("dose", ""),
            "FCR": meta.get("FCR", ""),
            "ADG": meta.get("ADG", ""),
            "intel_summary": meta.get("intel_summary", ""),
            "strategic_value": meta.get("strategic_value", ""),
            "actor": meta.get("lead_institution", ""),
            "country": meta.get("country", ""),
            "is_industry": meta.get("is_industry", ""),
            "url": meta.get("url", ""),
            "_doc": doc,
        })

    return hits[:k]


def synthesize(query, hits, max_tokens=1500):
    if not hits:
        return "在主庫中找不到相關論文。請確認查詢是否在追蹤主題範圍內：octacosanol / astaxanthin_animal / bacillus_protease / ch_osa_silicon / gut_health_poultry"

    context_parts = []
    for i, h in enumerate(hits, 1):
        context_parts.append(
            f"[論文{i}] (相似度 {h['similarity']:.2f}, 品質 {h['quality']}/5, {h['category']}類)\n"
            f"標題：{h['title']}\n"
            f"年份：{h['year']} | 主題：{h['topic']} | 物種：{h['species']}\n"
            f"化合物：{h['compound']} | 劑量：{h['dose']}\n"
            f"表現：FCR={h['FCR']} | ADG={h['ADG']}\n"
            f"作者機構：{h['actor']} ({h['country']}) | 業界：{h['is_industry']}\n"
            f"戰略標籤：{h['strategic_value']}\n"
            f"情報摘要：{h['intel_summary']}\n"
            f"URL: {h['url']}"
        )

    context = "\n\n".join(context_parts)

    prompt = (
        f"你是動物營養領域的競爭情報分析師。基於下列論文資料，回答使用者的問題。\n\n"
        f"使用者問題：{query}\n\n"
        f"主庫檢索結果（共 {len(hits)} 篇，按相似度排序）：\n\n"
        f"{context}\n\n"
        "回答要求：\n"
        "1. 用繁體中文回答\n"
        "2. 直接給出戰略結論，不要囉嗦\n"
        "3. 引用論文時用 [論文N] 標註\n"
        "4. 如果資料不足以回答，明確指出\n"
        "5. 對「沒有相關論文」這種情況，視為戰略洞察（代表領域空缺 = 機會 or 你領先）\n"
        "6. 涉及 FCR/ADG/劑量等數字時務必精確引用\n"
        "7. 結尾給 2-3 條「戰略建議」或「值得追蹤的後續」\n"
        "8. 字數控制在 600 字內\n\n"
        "直接回答，不要重複問題。"
    )

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是動物營養 R&D 競爭情報分析師。簡潔、戰略導向、繁體中文。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    try:
        r = requests.post(LLM_ENDPOINT, json=payload, timeout=180)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM 調用失敗：{e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="自然語言問題")
    ap.add_argument("--k", type=int, default=8, help="檢索數量")
    ap.add_argument("--topic", default=None)
    ap.add_argument("--category", default=None)
    ap.add_argument("--strategic-value", default=None)
    ap.add_argument("--min-quality", type=int, default=0)
    ap.add_argument("--year-from", default=None)
    ap.add_argument("--raw", action="store_true", help="只列檢索結果，不調用 LLM")
    ap.add_argument("--json", action="store_true", help="JSON 輸出")
    args = ap.parse_args()

    hits = search(
        args.query,
        k=args.k,
        topic=args.topic,
        category=args.category,
        strategic_value=args.strategic_value,
        min_quality=args.min_quality,
        year_from=args.year_from,
    )

    if args.json:
        out = [{k: v for k, v in h.items() if k != "_doc"} for h in hits]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.raw:
        print(f"\n=== 檢索結果 ({len(hits)} 篇) ===\n")
        for i, h in enumerate(hits, 1):
            print(f"[{i}] sim={h['similarity']} | q={h['quality']} | {h['category']} | {h['year']} | {h['topic']}")
            print(f"    {h['title'][:90]}")
            print(f"    Tags: {h['strategic_value']}")
            print(f"    Actor: {h['actor']} ({h['country']})")
            print()
        return

    print(f"\n=== 查詢：{args.query} ===")
    print(f"=== 檢索 {len(hits)} 篇相關論文，整合中... ===\n")
    answer = synthesize(args.query, hits)
    print(answer)
    print(f"\n=== 引用來源 ===")
    for i, h in enumerate(hits, 1):
        print(f"[論文{i}] {h['title'][:80]}")
        if h['url']:
            print(f"        {h['url']}")


if __name__ == "__main__":
    main()
