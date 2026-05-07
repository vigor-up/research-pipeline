import json, shutil
from datetime import datetime

path = r"C:\Users\Richtrong\.openclaw\openclaw.json"
shutil.copy2(path, path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

with open(path, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

to_disable = ["healthcheck", "node-connect", "taskflow-inbox-triage", "weather"]

skills = cfg.setdefault("skills", {}).setdefault("entries", {})
for skill in to_disable:
    skills.setdefault(skill, {})["enabled"] = False
    print(f"Disabled: {skill}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

print("Done")
