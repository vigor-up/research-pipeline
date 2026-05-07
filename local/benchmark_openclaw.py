"""
OpenClaw / llama-server Response Benchmark v1
直連 llama-server port 1234，測量真實回應速度
結果存到 D:\LLM\outputs\benchmark_openclaw_YYYYMMDD_HHMMSS.txt
貼給 Claude 做優化分析
"""

import time
import json
import statistics
import urllib.request
import urllib.error
import os
from datetime import datetime

BASE_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "Qwen3.6-35B-A3B-Q6_K"

TESTS = [
    {
        "id": "cold_short",
        "label": "短回應（冷啟動）",
        "prompt": "Reply with exactly: OK",
        "max_tokens": 5,
        "runs": 3,
    },
    {
        "id": "prefill_1k",
        "label": "1k token prefill 速度",
        "prompt": "以下是一段測試文字，請回答最後的問題。" + ("這是填充文字用來測試 prefill 速度。" * 40) + " 問題：1+1=?，只輸出數字。",
        "max_tokens": 5,
        "runs": 2,
    },
    {
        "id": "prefill_4k",
        "label": "4k token prefill 速度",
        "prompt": "以下是一段測試文字，請回答最後的問題。" + ("這是填充文字用來測試 prefill 速度。" * 160) + " 問題：1+1=?，只輸出數字。",
        "max_tokens": 5,
        "runs": 2,
    },
    {
        "id": "generation_100",
        "label": "生成速度 100 tokens",
        "prompt": "Count from 1 to 50, one number per line, no other text:",
        "max_tokens": 150,
        "runs": 3,
    },
    {
        "id": "chinese_task",
        "label": "中文任務（實際工作場景）",
        "prompt": "用三句話說明飼料轉化率FCR的定義和重要性，直接輸出不要解釋。",
        "max_tokens": 150,
        "runs": 2,
    },
    {
        "id": "json_output",
        "label": "JSON 格式輸出",
        "prompt": 'Output ONLY valid JSON: {"status":"ok","model":"qwen","value":42}',
        "max_tokens": 40,
        "runs": 3,
    },
    {
        "id": "tool_instruction",
        "label": "指令遵從（工具呼叫場景）",
        "prompt": (
            "You are an AI assistant. The user wants to search for information. "
            "Reply with ONLY a JSON object: {\"action\": \"search\", \"query\": \"feed conversion ratio\"}"
        ),
        "max_tokens": 50,
        "runs": 2,
    },
]


def call(prompt, max_tokens, timeout=60):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        BASE_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = (time.time() - t0) * 1000
            body = json.loads(resp.read().decode("utf-8"))
            content = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "") or ""
            ).strip()
            usage = body.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            tps = completion_tokens / (latency / 1000) if latency > 0 else 0
            ttft = latency  # 非 streaming 模式用總延遲近似
            return {
                "ok": True,
                "latency_ms": round(latency),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "tps": round(tps, 1),
                "content": content[:80],
                "error": None,
            }
    except Exception as e:
        return {
            "ok": False,
            "latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "tps": 0,
            "content": "",
            "error": str(e)[:100],
        }


def run():
    print("\n" + "=" * 60)
    print("  OpenClaw llama-server Benchmark v1")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Model: {MODEL}")
    print("=" * 60)

    # 健康確認
    try:
        with urllib.request.urlopen("http://127.0.0.1:1234/health", timeout=5) as r:
            print(f"\n  llama-server: {r.read().decode()}")
    except Exception as e:
        print(f"\n  [ERROR] llama-server not reachable: {e}")
        input("  按 Enter 結束...")
        return

    results = {}
    lines = []
    lines.append(f"OpenClaw llama-server Benchmark — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Model: {MODEL}")
    lines.append("=" * 60)

    for test in TESTS:
        tid = test["id"]
        print(f"\n{'─'*60}")
        print(f"  {test['label']}")
        print(f"{'─'*60}")

        run_results = []
        for i in range(test["runs"]):
            r = call(test["prompt"], test["max_tokens"])
            run_results.append(r)
            if r["ok"]:
                print(f"  run{i+1}: ✅ {r['latency_ms']}ms | {r['tps']} t/s | {r['completion_tokens']} tok | '{r['content'][:40]}'")
            else:
                print(f"  run{i+1}: ❌ {r['error']}")

        ok_runs = [r for r in run_results if r["ok"]]
        if ok_runs:
            avg_lat = round(statistics.median(r["latency_ms"] for r in ok_runs))
            avg_tps = round(statistics.median(r["tps"] for r in ok_runs), 1)
            avg_ptok = round(statistics.median(r["prompt_tokens"] for r in ok_runs))
            avg_ctok = round(statistics.median(r["completion_tokens"] for r in ok_runs))
        else:
            avg_lat = avg_tps = avg_ptok = avg_ctok = 0

        results[tid] = {
            "label": test["label"],
            "avg_latency_ms": avg_lat,
            "avg_tps": avg_tps,
            "avg_prompt_tokens": avg_ptok,
            "avg_completion_tokens": avg_ctok,
            "pass": len(ok_runs),
            "total": test["runs"],
        }

        print(f"  → 中位延遲: {avg_lat}ms | t/s: {avg_tps} | prompt: {avg_ptok} tok")
        lines.append(f"\n[{test['label']}]")
        lines.append(f"  延遲: {avg_lat}ms | t/s: {avg_tps} | prompt tokens: {avg_ptok} | completion: {avg_ctok}")
        lines.append(f"  通過: {len(ok_runs)}/{test['runs']}")

    # 總結報告
    print("\n" + "=" * 60)
    print("  📊 總結報告")
    print("=" * 60)
    print(f"  {'測試':<22} {'延遲':>8} {'t/s':>7} {'prompt tok':>10}")
    print("  " + "─" * 52)
    for tid, v in results.items():
        print(f"  {v['label']:<22} {v['avg_latency_ms']:>7}ms {v['avg_tps']:>7} {v['avg_prompt_tokens']:>10}")

    lines.append("\n" + "=" * 60)
    lines.append("總結")
    lines.append(f"{'測試':<22} {'延遲':>8} {'t/s':>7} {'prompt tok':>10}")
    for tid, v in results.items():
        lines.append(f"{v['label']:<22} {v['avg_latency_ms']:>7}ms {v['avg_tps']:>7} {v['avg_prompt_tokens']:>10}")

    # prefill 速度分析
    if "prefill_1k" in results and "prefill_4k" in results:
        l1 = results["prefill_1k"]["avg_latency_ms"]
        l4 = results["prefill_4k"]["avg_latency_ms"]
        ratio = round(l4 / l1, 1) if l1 > 0 else 0
        note = f"\nPrefill 分析：1k={l1}ms, 4k={l4}ms, 比值={ratio}x"
        if ratio < 2:
            note += " ✅ prefill 線性，KV cache 效率佳"
        elif ratio < 4:
            note += " ⚠️ prefill 略呈非線性，context 累積會變慢"
        else:
            note += " ❌ prefill 非線性嚴重，建議降低 contextWindow"
        print(note)
        lines.append(note)

    # 儲存
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = rf"D:\LLM\outputs\benchmark_openclaw_{ts}.txt"
    report = "\n".join(lines)

    try:
        os.makedirs(r"D:\LLM\outputs", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  💾 報告儲存：{out_path}")
    except Exception:
        with open(f"/tmp/benchmark_openclaw_{ts}.txt", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  💾 報告儲存：/tmp/benchmark_openclaw_{ts}.txt")

    print("\n  把 TXT 內容貼給 Claude 做優化分析。\n")
    input("  按 Enter 關閉視窗...")


if __name__ == "__main__":
    run()
