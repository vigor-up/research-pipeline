# setup_scheduler.ps1
# Windows Task Scheduler 設定 — 每日 03:00 自動跑 market_collector
# 執行方式：以系統管理員身份執行 PowerShell，貼上此腳本

$TaskName   = "ResearchPipeline-MarketCollector"
$PythonPath = "C:\Users\Richtrong\AppData\Local\Programs\Python\Python311\python.exe"
$ScriptPath = "D:\LLM\workflows\research-pipeline-v2\collect\market_collector.py"
$WorkDir    = "D:\LLM\workflows\research-pipeline-v2"
$LogPath    = "D:\LLM\workflows\research-pipeline-v2\logs\market_collector.log"

# 建立 logs 目錄
New-Item -ItemType Directory -Force -Path "D:\LLM\workflows\research-pipeline-v2\logs" | Out-Null

# 設定環境變數（PLAYWRIGHT_BROWSERS_PATH）
$EnvScript = @"
`$env:PLAYWRIGHT_BROWSERS_PATH = 'D:\playwright-browsers'
`$env:FORCE_FULL = 'false'
cd '$WorkDir'
& '$PythonPath' '$ScriptPath' >> '$LogPath' 2>&1
"@

$WrapperPath = "D:\LLM\workflows\research-pipeline-v2\run_market_collector.ps1"
$EnvScript | Out-File -FilePath $WrapperPath -Encoding utf8
Write-Host "Wrapper script created: $WrapperPath"

# 建立排程工作
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -File `"$WrapperPath`"" `
    -WorkingDirectory $WorkDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "03:00"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -WakeToRun $false

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# 移除舊工作（若存在）
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Research Pipeline: 每日 03:00 抓取市場KPI數據並同步至R2"

Write-Host ""
Write-Host "✅ Task '$TaskName' registered successfully"
Write-Host "   Schedule: Daily at 03:00"
Write-Host "   Script:   $ScriptPath"
Write-Host "   Log:      $LogPath"
Write-Host ""
Write-Host "立即測試執行（可選）："
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "查看執行狀態："
Write-Host "  Get-ScheduledTaskInfo -TaskName '$TaskName'"
