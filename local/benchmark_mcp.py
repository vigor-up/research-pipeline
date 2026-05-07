"""
benchmark_mcp.py v2
直接測試 llama-server (port 1234)
測試本地 Qwen3.6 在不同任務的完成率和速度
"""
import requests
import time
import json
from datetime import datetime

GATEWAY = "http://127.0.0.1:1234"
MODEL = "Qwen3.6-35B-A3B-Q6_K"
HEADERS = {"Content-Type": "application/json"}

TESTS = [
    {"id": "T1", "level": "簡單", "name": "純文字回應", "prompt": "用一句話解釋 FCR 是什麼", "max_tokens": 100},
    {"id": "T2", "level": "簡單", "name": "結構化 JSON", "prompt": "列出 3 個 Bacillus 蛋白酶對肉雞的效果，只輸出 JSON 不要其他文字", "max_tokens": 300},
    {"id": "T3", "level": "中等", "name": "繁體中文推理", "prompt": "分析 octacosanol 在肉雞飼料中的三個主要作用機制，每點不超過 50 字", "max_tokens": 400},
    {"id": "T4", "level": "中等", "name": "競品分析", "prompt": "DuPont Syncra SWI 和 Bacillus 蛋白酶複合製劑相比，各自的優缺點是什麼？用表格格式回答", "max_tokens": 500},
    {"id": "T5", "level": "困難", "name": "多步驟推理", "prompt": "假設客戶質疑你的飼料蛋白酶產品效果，請給出 3 個有數據支撐的反駁論點，每點包含：論點、數據來源、實際應用建議", "max_tokens": 800},
    {"id": "T6", "level": "困難", "name": "長文生成", "prompt": "寫一份 400 字的動物營養產品介紹，主題：枯草菌源蛋白酶在肉雞飼料中的應用，包含：產品特點、作用機制、試驗數據、使用建議", "max_tokens": 1000},
    {"id": "T7", "level": "壓力", "name": "大量 Token 生成", "prompt": "詳細說明 5 種動物（肉雞、蛋雞、豬、蝦、牛）使用蛋白酶飼料添加劑的效果差異，每種動物至少 100 字", "max_tokens": 2000},
]

def call_llama(prompt, max_tokens=500, timeout=120):
    url = f"{GATEWAY}/v1/chat/completions"
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "stream": False, "temperature": 0.7}
    start = time.time()
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=timeout)
        elapsed = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            ct = usage.get("completion_tokens", 0)
            pt = usage.get("prompt_tokens", 0)
            tps = round(ct / elapsed, 1) if elapsed > 0 else 0
            return {"success": True, "elapsed": round(elapsed, 2), "completion_tokens": ct, "prompt_tokens": pt, "tps": tps, "content_len": len(content), "content_preview": content[:120].replace("\n", " "), "finish_reason": data["choices"][0].get("finish_reason", "unknown")}
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}", "elapsed": round(time.time() - start, 2)}
    except Exception as e:
        return {"success": False, "error": str(e)[:100], "elapsed": round(time.time() - start, 2)}

def run_benchmark():
    print(f"\n{'='*65}")
    print(f"  llama-server Benchmark v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Model: {MODEL} @ {GATEWAY}")
    print(f"{'='*65}\n")

    results = []
    for test in TESTS:
        print(f"[{test['id']}] {test['level']} — {test['name']}")
        print(f"     Prompt: {test['prompt'][:70]}...")
        result = call_llama(test["prompt"], test["max_tokens"])
        result.update({"test_id": test["id"], "test_name": test["name"], "level": test["level"]})
        results.append(result)
        if result["success"]:
            status = "✅完整" if result["finish_reason"] != "length" else "⚠️截斷"
            print(f"     {status} | {result['elapsed']}s | {result['tps']} t/s | {result['completion_tokens']} tok")
            print(f"     Preview: {result['content_preview']}")
        else:
            print(f"     FAIL: {result['error']}")
        print()

    print(f"\n{'='*65}")
    print("  BENCHMARK 總結")
    print(f"{'='*65}")
    print(f"\n{'測試':<22} {'延遲':>8} {'t/s':>8} {'tokens':>8} {'狀態':>10}")
    print(f"{'-'*60}")

    success_count = complete_count = 0
    total_tps = []
    for r in results:
        if r["success"]:
            success_count += 1
            status = "✅完整" if r["finish_reason"] != "length" else "⚠️截斷"
            if r["finish_reason"] != "length":
                complete_count += 1
            total_tps.append(r["tps"])
            print(f"{r['test_name']:<22} {r['elapsed']:>7}s {r['tps']:>7} {r['completion_tokens']:>8} {status:>10}")
        else:
            print(f"{r['test_name']:<22} {'FAIL':>8} {'—':>8} {'—':>8} {'❌失敗':>10}")

    avg_tps = round(sum(total_tps)/len(total_tps), 1) if total_tps else 0
    print(f"\n成功率    : {success_count}/{len(TESTS)}")
    print(f"完整完成率 : {complete_count}/{len(TESTS)}")
    print(f"平均 t/s  : {avg_tps}")

    import os
    os.makedirs("D:\\LLM\\outputs", exist_ok=True)
    output_file = f"D:\\LLM\\outputs\\benchmark_mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n結果已儲存：{output_file}")
    print(f"\n{'='*65}\n")

if __name__ == "__main__":
    run_benchmark()
