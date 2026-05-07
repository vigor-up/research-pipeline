"""
fix_openclaw_models.py
清除 OpenClaw 所有雲端模型，只保留本地 Qwen3.6 + DeepSeek 兜底
"""
import json
import shutil
from datetime import datetime

path = r"C:\Users\Richtrong\.openclaw\openclaw.json"
backup = rf"C:\Users\Richtrong\.openclaw\openclaw.json.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# 備份原檔
shutil.copy2(path, backup)
print(f"Backup: {backup}")

with open(path, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

# 1. 清除 aliases，只保留兩個
cfg.setdefault("agents", {}).setdefault("defaults", {}).setdefault("model", {})
cfg["agents"]["defaults"]["model"]["aliases"] = {
    "Qwen3.6": "custom-127-0-0-1-1234/Qwen3.6-35B-A3B-Q6_K",
    "DeepSeek": "deepseek/deepseek-chat"
}

# 2. 清除 providers，只保留本地 + deepseek
keep = ["custom-127-0-0-1-1234", "deepseek"]
providers = cfg.get("models", {}).get("providers", {})
to_delete = [k for k in list(providers.keys()) if not any(k.startswith(p) for p in keep)]
for k in to_delete:
    del providers[k]
    print(f"Removed provider: {k}")

# 3. 確保 fallback 正確
cfg["agents"]["defaults"]["model"]["fallbacks"] = ["deepseek/deepseek-chat"]

# 4. 確保 timeoutSeconds 正確
cfg["agents"]["defaults"]["timeoutSeconds"] = 120

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

print("\nDone. Remaining models:")
for k in cfg.get("models", {}).get("providers", {}):
    print(f"  - {k}")
print(f"Fallbacks: {cfg['agents']['defaults']['model']['fallbacks']}")
print(f"timeoutSeconds: {cfg['agents']['defaults']['timeoutSeconds']}")
