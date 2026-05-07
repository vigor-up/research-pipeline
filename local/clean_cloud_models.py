"""
clean_cloud_models.py
只清除 aliases 和 configured models 中的雲端模型
不動 agents.defaults.model 的物件結構
"""
import json, shutil
from datetime import datetime

path = r"C:\Users\Richtrong\.openclaw\openclaw.json"
bak = path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy2(path, bak)
print(f"Backup: {bak}")

with open(path, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

# 1. 清除 aliases — 只保留 Qwen3.6 和 DeepSeek
model = cfg["agents"]["defaults"]["model"]
old_aliases = model.get("aliases", {})
model["aliases"] = {
    "Qwen3.6": "custom-127-0-0-1-1234/Qwen3.6-35B-A3B-Q6_K",
    "DeepSeek": "deepseek/deepseek-chat"
}
removed_aliases = [k for k in old_aliases if k not in ("Qwen3.6", "DeepSeek")]
print(f"Removed aliases: {removed_aliases}")

# 2. 確保 fallback 正確（只動 list，不動物件結構）
model["fallbacks"] = ["deepseek/deepseek-chat"]
print(f"Fallbacks set: {model['fallbacks']}")

# 3. 確保 timeoutSeconds 正確
cfg["agents"]["defaults"]["timeoutSeconds"] = 120
print(f"timeoutSeconds: 120")

# 4. 清除 models.providers 中非本地非 deepseek 的項目
keep_prefixes = ["custom-127-0-0-1-1234", "deepseek"]
providers = cfg.get("models", {}).get("providers", {})
to_remove = [k for k in list(providers.keys())
             if not any(k.startswith(p) for p in keep_prefixes)]
for k in to_remove:
    del providers[k]
    print(f"Removed provider: {k}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

print("\nDone. Verify with: openclaw models status")
