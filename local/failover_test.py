"""
OpenClaw Gateway Failover Test v1
測試：本地模型斷線後 fallback 到 DeepSeek 的完整流程
- 自動關閉 llama-server
- 透過 OpenClaw gateway 發送請求
- 確認 fallback 觸發時間和成功率
- 重啟本地模型確認恢復
結果存到 D:\LLM\outputs\failover_test_YYYYMMDD_HHMMSS.txt
"""

import time
import json
import subprocess
import urllib.request
import urllib.error
import os
from datetime import datetime

GATEWAY_URL = "http://127.0.0.1:18789"
GATEWAY_TOKEN = "28641603120269119a3b18a29e33b96d569fdf7a5c8e79b5"
LOCAL_HEALTH = "http://127.0.0.1:1234/health"
LLAMA_BAT = r"D:\LLM\Qwen3.6-35B_Optimized.bat"


def check_health(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return True, r.read().decode()
    except Exception as e:
        return False, str(e)[:60]


def gateway_chat(prompt, timeout=90):
    """透過 OpenClaw gateway /v1/chat/completions 發送訊息"""
    payload = json.dumps({
        "model": "openclaw",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "user": "failover-test",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{GATEWAY_URL}/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GATEWAY_TOKEN}",
            "x-openclaw-agent-id": "main",
        },
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
            ).strip()[:100]
            model_used = body.get("model", "unknown")
            return {
                "ok": True,
                "latency_ms": round(latency),
                "content": content,
                "model": model_used,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        latency = (time.time() - t0) * 1000
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")[:120]
        except Exception:
            pass
        return {
            "ok": False,
            "latency_ms": round(latency),
            "content": "",
            "model": "unknown",
            "error": f"HTTP {e.code}: {body_text}",
        }
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return {
            "ok": False,
            "latency_ms": round(latency),
            "content": "",
            "model": "unknown",
            "error": str(e)[:100],
        }


def kill_llama():
    """關閉 llama-server"""
    subprocess.run(
        ["taskkill", "/f", "/im", "llama-server.exe"],
        capture_output=True
    )
    time.sleep(2)


def start_llama():
    """重啟 llama-server（背景執行）"""
    subprocess.Popen(
        ["cmd", "/c", LLAMA_BAT],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def run():
    lines = []
    ts_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 60)
    print("  OpenClaw Gateway Failover Test v1")
    print(f"  {ts_start}")
    print("=" * 60)
    lines.append(f"OpenClaw Gateway Failover Test — {ts_start}")
    lines.append("=" * 60)

    # ── 步驟 1：確認初始狀態 ──
    print("\n[1/6] 確認初始狀態...")
    gw_ok, gw_msg = check_health(f"{GATEWAY_URL}/health")
    lm_ok, lm_msg = check_health(LOCAL_HEALTH)

    print(f"  Gateway : {'✅' if gw_ok else '❌'} {gw_msg}")
    print(f"  本地模型: {'✅' if lm_ok else '❌'} {lm_msg}")
    lines.append(f"\n[初始狀態]")
    lines.append(f"  Gateway: {'OK' if gw_ok else 'FAIL'} {gw_msg}")
    lines.append(f"  本地模型: {'OK' if lm_ok else 'FAIL'} {lm_msg}")

    if not gw_ok:
        print("\n  [ERROR] Gateway 未運行，請先啟動 openclaw gateway run")
        input("  按 Enter 結束...")
        return

    # ── 步驟 2：正常狀態下測試 ──
    print("\n[2/6] 正常狀態基準測試（本地模型在線）...")
    baseline = gateway_chat("你好，請用一句話回答：現在是哪個模型在運行？")
    status = "✅" if baseline["ok"] else "❌"
    print(f"  {status} {baseline['latency_ms']}ms | model={baseline['model']} | '{baseline['content'][:50]}'")
    lines.append(f"\n[正常狀態基準]")
    lines.append(f"  {'OK' if baseline['ok'] else 'FAIL'} | {baseline['latency_ms']}ms | {baseline['model']}")
    lines.append(f"  回應: {baseline['content'][:80]}")

    # ── 步驟 3：關閉本地模型 ──
    print("\n[3/6] 關閉本地模型（模擬斷線）...")
    kill_llama()
    lm_ok2, _ = check_health(LOCAL_HEALTH, timeout=3)
    print(f"  本地模型狀態: {'❌ 已關閉' if not lm_ok2 else '⚠️ 仍在運行'}")
    lines.append(f"\n[關閉本地模型]")
    lines.append(f"  本地模型: {'關閉成功' if not lm_ok2 else '仍在運行'}")

    # ── 步驟 4：測試 fallback 觸發 ──
    print("\n[4/6] 測試 fallback 觸發（應自動切換到 DeepSeek）...")
    print("  等待 OpenClaw 偵測到超時（最多 90 秒）...")

    fallback_results = []
    for i in range(3):
        print(f"  發送測試訊息 {i+1}/3...")
        t0 = time.time()
        r = gateway_chat(
            f"這是 fallback 測試訊息 {i+1}，請回答：你是哪個模型？只輸出模型名稱。",
            timeout=120
        )
        elapsed = round((time.time() - t0) * 1000)
        fallback_results.append(r)
        status = "✅" if r["ok"] else "❌"
        fallback_hint = "→ DeepSeek ✅" if "deepseek" in r["model"].lower() else ""
        print(f"  {status} {elapsed}ms | model={r['model']} {fallback_hint}")
        print(f"    回應: '{r['content'][:60]}'")
        if r["error"]:
            print(f"    錯誤: {r['error']}")

    lines.append(f"\n[Fallback 測試]")
    for i, r in enumerate(fallback_results):
        lines.append(f"  訊息{i+1}: {'OK' if r['ok'] else 'FAIL'} | {r['latency_ms']}ms | model={r['model']}")
        lines.append(f"    回應: {r['content'][:80]}")

    # ── 步驟 5：分析結果 ──
    print("\n[5/6] 分析結果...")
    ok_count = sum(1 for r in fallback_results if r["ok"])
    deepseek_count = sum(1 for r in fallback_results if "deepseek" in r["model"].lower())
    avg_lat = round(sum(r["latency_ms"] for r in fallback_results if r["ok"]) / max(ok_count, 1))

    print(f"  成功率: {ok_count}/3")
    print(f"  DeepSeek 接管: {deepseek_count}/3")
    print(f"  平均延遲: {avg_lat}ms")

    if ok_count == 3 and deepseek_count >= 2:
        verdict = "✅ Fallback 正常運作"
    elif ok_count >= 2:
        verdict = "⚠️ Fallback 部分成功，建議檢查 log"
    else:
        verdict = "❌ Fallback 失敗，需要排查"

    print(f"  結論: {verdict}")
    lines.append(f"\n[結果分析]")
    lines.append(f"  成功率: {ok_count}/3")
    lines.append(f"  DeepSeek 接管: {deepseek_count}/3")
    lines.append(f"  平均延遲: {avg_lat}ms")
    lines.append(f"  結論: {verdict}")

    # ── 步驟 6：重啟本地模型 ──
    print("\n[6/6] 重啟本地模型...")
    start_llama()
    print("  等待 45 秒讓模型載入...")
    for i in range(45, 0, -5):
        print(f"  還需 {i} 秒...", end="\r")
        time.sleep(5)
    print()

    lm_ok3, lm_msg3 = check_health(LOCAL_HEALTH, timeout=10)
    print(f"  本地模型: {'✅ 已恢復' if lm_ok3 else '⚠️ 還在載入，稍後手動確認'}")
    lines.append(f"\n[重啟本地模型]")
    lines.append(f"  狀態: {'已恢復' if lm_ok3 else '載入中'} {lm_msg3}")

    if lm_ok3:
        print("\n  提醒：在 OpenClaw 對話窗輸入 /new 切回本地模型")
        lines.append("  提醒：需在 OpenClaw 對話窗輸入 /new 切回本地模型")

    # ── 儲存報告 ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = rf"D:\LLM\outputs\failover_test_{ts}.txt"
    report = "\n".join(lines)

    try:
        os.makedirs(r"D:\LLM\outputs", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  💾 報告儲存：{out_path}")
    except Exception:
        with open(f"/tmp/failover_test_{ts}.txt", "w", encoding="utf-8") as f:
            f.write(report)

    print("\n  測試完成，把報告貼給 Claude 做分析。\n")
    input("  按 Enter 關閉視窗...")


if __name__ == "__main__":
    run()
