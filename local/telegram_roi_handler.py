# -*- coding: utf-8 -*-
"""
telegram_roi_handler.py
QClaw Telegram Bot ROI 指令處理器
指令格式：
  /roi 育肥豬 FCR改善25% 115kg
  /roi 蛋雞 延長峰值14天 500日齡 10000隻
  /roi 肉雞 FCR改善10% 2.5kg
  /roi 蝦 存活率提升10% 10畝
  /roi 幫助
"""

import sys, json, re, requests, subprocess
from pathlib import Path

TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134
ROI_SCRIPT     = r'D:\LLM\workflows\research-pipeline-v2\local\roi_calculator.py'

def tg_send(msg):
    requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
        json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'},
        timeout=10)

# ── 自然語言解析 ───────────────────────────────────────
SPECIES_MAP = {
    '育肥豬': 'finisher_pig',
    '豬':     'finisher_pig',
    '生豬':   'finisher_pig',
    '蛋雞':   'layer_chicken',
    '母雞':   'layer_chicken',
    '肉雞':   'broiler',
    '白蝦':   'shrimp',
    '對蝦':   'shrimp',
    '蝦':     'shrimp',
    '乳牛':   'dairy_cow',
    '奶牛':   'dairy_cow',
    '肉牛':   'beef_cattle',
    '牛':     'beef_cattle',
}

def parse_command(text):
    """解析自然語言指令 → species + params"""
    text = text.strip()

    # 幫助
    if '幫助' in text or 'help' in text.lower():
        return 'help', {}

    # 識別物種
    species = None
    for cn, en in SPECIES_MAP.items():
        if cn in text:
            species = en
            break
    if not species:
        return None, {'error': '無法識別物種，請輸入：育肥豬/蛋雞/肉雞/蝦/肉牛'}

    params = {}

    # FCR 改善
    m = re.search(r'FCR.*?(\d+(?:\.\d+)?)%', text)
    if m:
        params['fcr_improvement'] = float(m.group(1))

    # 體重
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|公斤|千克)', text)
    if m:
        if species in ('finisher_pig',):
            params['body_weight'] = float(m.group(1))
        elif species == 'broiler':
            params['body_weight'] = float(m.group(1))

    # 日齡
    m = re.search(r'(\d+)\s*(?:日齡|天|日)', text)
    if m:
        params['age'] = int(m.group(1))

    # 延長峰值天數
    m = re.search(r'延長.*?(\d+)\s*天', text)
    if not m:
        m = re.search(r'峰值.*?(\d+)\s*天', text)
    if not m:
        m = re.search(r'多\s*(\d+)\s*週', text)
        if m:
            params['peak_extension_days'] = int(m.group(1)) * 7
    if m and 'peak_extension_days' not in params:
        params['peak_extension_days'] = int(m.group(1))

    # 雞隻數量
    m = re.search(r'(\d+(?:萬)?)\s*(?:隻|羽)', text)
    if m:
        n = m.group(1)
        params['flock_size'] = float(n.replace('萬','')) * 10000 if '萬' in n else float(n)

    # 存活率提升
    m = re.search(r'存活率.*?(\d+(?:\.\d+)?)%', text)
    if m:
        params['survival_improvement'] = float(m.group(1))

    # 池塘面積
    m = re.search(r'(\d+(?:\.\d+)?)\s*畝', text)
    if m:
        params['pond_area'] = float(m.group(1))

    return species, params

HELP_MSG = """🤖 <b>ROI 計算器 指令說明</b>

<b>育肥豬</b>
/roi 育肥豬 FCR改善25% 115kg

<b>蛋雞</b>
/roi 蛋雞 延長峰值14天 500日齡 10000隻
/roi 蛋雞 延長峰值2週 300日齡

<b>肉雞</b>
/roi 肉雞 FCR改善10% 2.5kg

<b>蝦</b>
/roi 蝦 存活率提升10% 10畝

<b>說明</b>
• 數據來源：本機DB（實時價格+生產性能基準）
• 客戶願付 = 淨增收 × 50% 分潤
• 建議報價 = 願付價格 × 40-60%

輸入 /roi 幫助 顯示此說明"""

def handle_roi_command(text):
    """主處理函數，從 QClaw Telegram bot 呼叫"""
    # 去掉 /roi 前綴
    text = re.sub(r'^/roi\s*', '', text, flags=re.IGNORECASE).strip()

    if not text or '幫助' in text:
        tg_send(HELP_MSG)
        return

    species, params = parse_command(text)

    if not species:
        tg_send(f'❌ {params.get("error","解析失敗")}\n\n輸入 /roi 幫助 查看說明')
        return

    tg_send('⏳ 計算中，從DB拉取實時數據...')

    # 呼叫 roi_calculator.py
    try:
        result = subprocess.run(
            ['python', ROI_SCRIPT,
             '--species', species,
             '--params', json.dumps(params, ensure_ascii=False),
             '--telegram'],
            capture_output=True, text=True, encoding='utf-8', timeout=30)

        if result.returncode == 0 and result.stdout:
            tg_send(result.stdout)
        else:
            err = result.stderr[:200] if result.stderr else '未知錯誤'
            tg_send(f'❌ 計算失敗: {err}')
    except subprocess.TimeoutExpired:
        tg_send('❌ 計算超時（DB可能正在被其他程序使用）')
    except Exception as e:
        tg_send(f'❌ 執行錯誤: {e}')

# ── QClaw skill 整合腳本 ───────────────────────────────
QCLAW_SKILL_MD = '''# ROI Calculator Skill

## 觸發條件
當用戶輸入包含以下關鍵字時觸發：
- /roi
- ROI計算
- 客戶願付
- 添加劑值多少錢

## 執行腳本
```powershell
python D:\\LLM\\workflows\\research-pipeline-v2\\local\\telegram_roi_handler.py --text "{user_input}"
```

## 說明
從本機 market_data.db 拉取實時數據，計算各物種添加劑ROI
支援：育肥豬/蛋雞/肉雞/蝦
'''

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--text', default='', help='Telegram 訊息文字')
    parser.add_argument('--write-skill', action='store_true',
                        help='輸出 QClaw skill SKILL.md')
    args = parser.parse_args()

    if args.write_skill:
        skill_path = Path(r'C:\Users\Richtrong\.qclaw\skills\roi-calculator\SKILL.md')
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(QCLAW_SKILL_MD, encoding='utf-8')
        print(f'Skill written to {skill_path}')
    elif args.text:
        handle_roi_command(args.text)
    else:
        # 互動測試模式
        print('ROI Handler 測試模式（輸入 quit 退出）')
        while True:
            text = input('/roi ').strip()
            if text == 'quit':
                break
            handle_roi_command('/roi ' + text)
