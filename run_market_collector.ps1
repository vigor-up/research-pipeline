$env:PLAYWRIGHT_BROWSERS_PATH = 'D:\playwright-browsers'
$env:FORCE_FULL = 'false'
cd 'D:\LLM\workflows\research-pipeline-v2'
& 'C:\Users\Richtrong\AppData\Local\Programs\Python\Python311\python.exe' 'D:\LLM\workflows\research-pipeline-v2\collect\market_collector.py' >> 'D:\LLM\workflows\research-pipeline-v2\logs\market_collector.log' 2>&1
