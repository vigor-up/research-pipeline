"""
tg_commander.py — Telegram 遙控指揮官 v1.1
修復：啟動時跳過積壓舊訊息 + 單例鎖防重複啟動
"""

import os
import sys
import socket
import asyncio
import logging
import subprocess
import httpx
from pathlib import Path
from datetime import datetime

# ── 單例鎖（防止重複啟動）────────────────────────────────────────────────────
_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    _lock_socket.bind(("127.0.0.1", 47291))
except OSError:
    print("tg_commander 已在執行中，退出。")
    sys.exit(0)

# ── 設定 ──────────────────────────────────────────────────────────────────────
BOT_TOKEN       = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = int(os.environ.get("TG_OWNER_CHAT_ID", "897274134"))

QCLAW_URL     = "http://127.0.0.1:18789"
QCLAW_TOKEN   = os.environ.get("QCLAW_TOKEN", "64872614502156c84e94dcaf7cd1872f54447c009005c5e8")
LLM_URL       = "http://127.0.0.1:1234"

PIPELINE_DIR  = Path(r"D:\LLM\workflows\research-pipeline-v2")
RESEARCH_DIR  = Path(r"D:\LLM\workflows\research")
STOP_ALL_BAT  = Path(r"D:\LLM\Stop_All.bat")
START_LLM_BAT = Path(r"D:\LLM\Qwen3.6-35B_Optimized.bat")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

Path(r"D:\LLM\logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(r"D:\LLM\logs\tg_commander.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ── Telegram helpers ──────────────────────────────────────────────────────────
async def tg_post(client: httpx.AsyncClient, method: str, **kwargs):
    r = await client.post(f"{TG_API}/{method}", json=kwargs, timeout=30)
    return r.json()

async def send(client, text: str, chat_id: int = None, parse_mode="HTML",
               reply_markup=None):
    cid = chat_id or ALLOWED_CHAT_ID
    payload = dict(chat_id=cid, text=text[:4000], parse_mode=parse_mode)
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await tg_post(client, "sendMessage", **payload)

async def send_main_menu(client):
    kb = {
        "inline_keyboard": [
            [
                {"text": "📊 系統狀態",             "callback_data": "cmd:status"},
                {"text": "🔄 重啟 LLM",             "callback_data": "cmd:restart_llm"},
            ],
            [
                {"text": "🚀 部署 ingredients.yaml", "callback_data": "cmd:deploy_ingredients"},
                {"text": "📦 跑 Pipeline",           "callback_data": "cmd:run_pipeline"},
            ],
            [
                {"text": "📰 Telegram 月報",         "callback_data": "cmd:digest_test"},
                {"text": "🔍 提議確認清單",           "callback_data": "cmd:proposals"},
            ],
            [
                {"text": "💬 問 QClaw...",            "callback_data": "cmd:ask_mode"},
                {"text": "⛔ 停止所有服務",           "callback_data": "cmd:stop_all"},
            ],
        ]
    }
    await send(client,
        "🖥️ <b>EVO-X2 指揮台</b>\n選擇指令或直接傳文字問 QClaw：",
        reply_markup=kb)

# ── 指令執行 ──────────────────────────────────────────────────────────────────
async def cmd_status(client: httpx.AsyncClient) -> str:
    lines = ["<b>📊 系統狀態</b>", f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M')}</code>"]

    try:
        await client.get(f"{LLM_URL}/health", timeout=5)
        lines.append("✅ LLM (port 1234): <b>OK</b>")
    except Exception:
        lines.append("❌ LLM (port 1234): <b>離線</b>")

    try:
        r = await client.get(
            f"{QCLAW_URL}/health",
            headers={"Authorization": f"Bearer {QCLAW_TOKEN}"},
            timeout=5
        )
        d = r.json()
        lines.append(f"✅ QClaw (port 18789): <b>{d.get('status','?')}</b>")
    except Exception:
        lines.append("❌ QClaw (port 18789): <b>離線</b>")

    try:
        result = subprocess.run(
            ["python", "-c",
             "import chromadb; c=chromadb.PersistentClient("
             "path='D:/LLM/knowledge/biotech/db')"
             ".get_collection('biotech_papers'); print(c.count())"],
            capture_output=True, text=True, timeout=15
        )
        lines.append(f"📚 ChromaDB: <b>{result.stdout.strip()} 篇</b>")
    except Exception:
        lines.append("⚠️ ChromaDB: 無法讀取")

    try:
        result = subprocess.run(
            ["python", "-c",
             "import sqlite3; c=sqlite3.connect("
             r"r'D:\LLM\workflows\research-pipeline-v2\b_group.db')"
             ".execute('SELECT COUNT(*) FROM b_group').fetchone()[0]; print(c)"],
            capture_output=True, text=True, timeout=10
        )
        lines.append(f"🔬 B組對照: <b>{result.stdout.strip()} 筆</b>")
    except Exception:
        lines.append("⚠️ b_group.db: 未初始化")

    try:
        result = subprocess.run(
            ["python", "-c",
             "import sqlite3; db=sqlite3.connect("
             r"r'D:\LLM\workflows\research-pipeline-v2\b_group.db');"
             "mp=db.execute(\"SELECT COUNT(*) FROM metric_proposals WHERE status='pending'\").fetchone()[0];"
             "ip=db.execute(\"SELECT COUNT(*) FROM ingredient_proposals WHERE status='pending'\").fetchone()[0];"
             "print(f'{mp},{ip}')"],
            capture_output=True, text=True, timeout=10
        )
        mp, ip = result.stdout.strip().split(",")
        if int(mp) + int(ip) > 0:
            lines.append(f"⚠️ 待確認：指標 <b>{mp}</b> 個，原料 <b>{ip}</b> 個")
    except Exception:
        pass

    return "\n".join(lines)


async def cmd_restart_llm(client: httpx.AsyncClient) -> str:
    await send(client, "⏳ 重啟 LLM 中（約 30 秒）...")
    try:
        subprocess.Popen(
            ["cmd", "/c", str(START_LLM_BAT)],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return "🔄 LLM 重啟指令已發送，30 秒後確認狀態"
    except Exception as e:
        return f"❌ 重啟失敗：{e}"


async def cmd_stop_all(client: httpx.AsyncClient) -> str:
    try:
        subprocess.Popen(["cmd", "/c", str(STOP_ALL_BAT)],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        return "⛔ Stop_All.bat 已執行，所有服務停止中"
    except Exception as e:
        return f"❌ 失敗：{e}"


async def cmd_deploy_ingredients(client: httpx.AsyncClient) -> str:
    src = Path(r"D:\LLM\workflows\research-pipeline-v2\configs\ingredients.yaml")
    if not src.exists():
        return f"❌ 找不到 {src}"
    try:
        import yaml
        with open(src, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        count = len(cfg.get("ingredients", []))

        # 同時上傳到 R2
        upload = subprocess.run(
            ["python", r"D:\LLM\workflows\research-pipeline-v2\local\upload_ingredients_to_r2.py"],
            capture_output=True, text=True, timeout=30
        )
        if upload.returncode == 0:
            return (f"✅ ingredients.yaml 已驗證並上傳 R2\n"
                    f"原料數：<b>{count} 個</b>")
        else:
            return (f"✅ YAML 驗證通過（{count} 個原料）\n"
                    f"⚠️ R2 上傳失敗：<code>{upload.stderr[-200:]}</code>")
    except Exception as e:
        return f"❌ 錯誤：{e}"


async def cmd_run_pipeline(client: httpx.AsyncClient) -> str:
    await send(client, "⏳ 啟動 Pipeline（背景執行）...")
    script = PIPELINE_DIR / "local" / "download_and_analyze.py"
    if not script.exists():
        return f"❌ 找不到 {script}"
    try:
        proc = subprocess.Popen(
            ["python", str(script), "--notify-telegram"],
            cwd=str(PIPELINE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return f"🚀 Pipeline 已啟動（PID {proc.pid}）\n完成後自動推播"
    except Exception as e:
        return f"❌ 啟動失敗：{e}"


async def cmd_digest_test(client: httpx.AsyncClient) -> str:
    await send(client, "⏳ 發送測試月報...")
    try:
        result = subprocess.run(
            ["python", "digest.py", "--test"],
            cwd=str(RESEARCH_DIR),
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return "✅ 月報測試推播完成"
        return f"❌ 失敗：\n<code>{result.stderr[-500:]}</code>"
    except Exception as e:
        return f"❌ {e}"


async def cmd_proposals(client: httpx.AsyncClient) -> str:
    try:
        import sqlite3
        db = sqlite3.connect(str(PIPELINE_DIR / "b_group.db"))
        mp = db.execute(
            "SELECT metric_name, species, example_claim FROM metric_proposals "
            "WHERE status='pending' LIMIT 5"
        ).fetchall()
        ip = db.execute(
            "SELECT ingredient_name, suggested_role, example_context FROM ingredient_proposals "
            "WHERE status='pending' LIMIT 5"
        ).fetchall()
        db.close()

        lines = ["<b>⚠️ 待確認提議</b>"]
        if mp:
            lines.append("\n<b>新指標：</b>")
            for row in mp:
                lines.append(f"  • {row[0]} ({row[1]})\n    {row[2][:80]}")
        if ip:
            lines.append("\n<b>新原料：</b>")
            for row in ip:
                lines.append(f"  • {row[0]} [{row[1]}]\n    {row[2][:80]}")
        if not mp and not ip:
            lines.append("✅ 無待確認項目")
        else:
            lines.append("\n⌨️ 回 EVO-X2 執行：\n<code>python proposal_review.py</code>")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 無法讀取 b_group.db：{e}"


# ── QClaw 對話轉發 ────────────────────────────────────────────────────────────
async def ask_qclaw(client: httpx.AsyncClient, text: str) -> str:
    try:
        payload = {
            "model": "qclaw/modelroute",
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 1024,
            "stream": False,
        }
        r = await client.post(
            f"{QCLAW_URL}/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {QCLAW_TOKEN}",
                     "Content-Type": "application/json"},
            timeout=120
        )
        reply = r.json()["choices"][0]["message"]["content"]
        if len(reply) > 3800:
            reply = reply[:3800] + "\n\n…（截斷，完整結果請在 QClaw 查看）"
        return reply
    except Exception as e:
        return f"❌ QClaw 無回應：{e}"


# ── 主迴圈 ────────────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        sys.exit("❌ 未設定 TELEGRAM_BOT_TOKEN 環境變數")

    log.info(f"tg_commander v1.1 啟動，只接受 chat_id={ALLOWED_CHAT_ID}")

    ask_mode_sessions: set = set()

    async with httpx.AsyncClient() as client:

        # ── 啟動時跳過所有積壓舊訊息 ────────────────────────────────────────
        try:
            r = await client.get(
                f"{TG_API}/getUpdates",
                params={"offset": -1, "limit": 1},
                timeout=10
            )
            updates = r.json().get("result", [])
            offset = (updates[-1]["update_id"] + 1) if updates else 0
            log.info(f"跳過積壓訊息，啟動 offset={offset}")
        except Exception:
            offset = 0

        # 通知上線
        await send(client,
            "🟢 <b>EVO-X2 指揮台上線</b>\n"
            f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>")
        await send_main_menu(client)

        while True:
            try:
                r = await client.get(
                    f"{TG_API}/getUpdates",
                    params={"offset": offset, "timeout": 30, "limit": 10},
                    timeout=40
                )
                updates = r.json().get("result", [])
            except Exception as e:
                log.warning(f"getUpdates 失敗：{e}")
                await asyncio.sleep(5)
                continue

            for upd in updates:
                offset = upd["update_id"] + 1

                # ── 按鈕回調 ────────────────────────────────────────────────
                if "callback_query" in upd:
                    cb   = upd["callback_query"]
                    cid  = cb["from"]["id"]
                    data = cb["data"]

                    if cid != ALLOWED_CHAT_ID:
                        continue

                    await tg_post(client, "answerCallbackQuery",
                                  callback_query_id=cb["id"])

                    if data == "cmd:status":
                        result = await cmd_status(client)
                    elif data == "cmd:restart_llm":
                        result = await cmd_restart_llm(client)
                    elif data == "cmd:stop_all":
                        result = await cmd_stop_all(client)
                    elif data == "cmd:deploy_ingredients":
                        result = await cmd_deploy_ingredients(client)
                    elif data == "cmd:run_pipeline":
                        result = await cmd_run_pipeline(client)
                    elif data == "cmd:digest_test":
                        result = await cmd_digest_test(client)
                    elif data == "cmd:proposals":
                        result = await cmd_proposals(client)
                    elif data == "cmd:ask_mode":
                        ask_mode_sessions.add(cid)
                        result = ("💬 <b>QClaw 對話模式</b>\n"
                                  "直接輸入問題，傳 /menu 退出")
                    else:
                        result = f"未知指令：{data}"

                    await send(client, result)
                    if data != "cmd:ask_mode":
                        await send_main_menu(client)

                # ── 文字訊息 ─────────────────────────────────────────────────
                elif "message" in upd and "text" in upd["message"]:
                    msg = upd["message"]
                    cid = msg["from"]["id"]
                    txt = msg["text"].strip()

                    if cid != ALLOWED_CHAT_ID:
                        continue

                    log.info(f"收到：{txt[:80]}")

                    if txt in ("/start", "/menu"):
                        ask_mode_sessions.discard(cid)
                        await send_main_menu(client)

                    elif txt == "/status":
                        result = await cmd_status(client)
                        await send(client, result)
                        await send_main_menu(client)

                    elif cid in ask_mode_sessions or txt.startswith("/ask "):
                        question = txt.replace("/ask ", "", 1)
                        await send(client, "⏳ 問 QClaw 中...")
                        reply = await ask_qclaw(client, question)
                        await send(client, f"🤖 <b>QClaw：</b>\n{reply}")

                    else:
                        await send(client, "⏳ 轉發 QClaw 中...")
                        reply = await ask_qclaw(client, txt)
                        await send(client, f"🤖 <b>QClaw：</b>\n{reply}")

            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
