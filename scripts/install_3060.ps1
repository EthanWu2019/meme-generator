$ErrorActionPreference = "Continue"
# 一键部署自建表情包到 3060
# 用法: 在仓库根目录执行 .\scripts\install_3060.ps1

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$ServiceDir = "D:\TRSSYUNZAI\MemeService\app"
$PluginDir  = "D:\TRSSYUNZAI\Yunzai-Bot\plugins\meme-plugin"
$Venv       = "D:\TRSSYUNZAI\MemeService\.venv"

function Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }

Step "1/5 建目录"
New-Item -ItemType Directory -Force -Path $ServiceDir          | Out-Null
New-Item -ItemType Directory -Force -Path "$ServiceDir\resources" | Out-Null
New-Item -ItemType Directory -Force -Path $PluginDir           | Out-Null
New-Item -ItemType Directory -Force -Path "$PluginDir\resources"| Out-Null

Step "2/5 建 venv 并装依赖"
if (-not (Test-Path "$Venv\Scripts\python.exe")) {
    uv venv $Venv --python 3.12
}
uv pip install --python "$Venv\Scripts\python.exe" meme-generator fastapi uvicorn pillow python-multipart

Step "3/5 铺文件"
Copy-Item "$RepoRoot\service\server.py"           $ServiceDir -Force
Copy-Item "$RepoRoot\service\fetch_resources.py"  $ServiceDir -Force
Copy-Item "$RepoRoot\service\start.bat"           $ServiceDir -Force
Copy-Item "$RepoRoot\plugin\index.js"              $PluginDir  -Force
Copy-Item "$RepoRoot\plugin\package.json"          $PluginDir  -Force
Copy-Item "$RepoRoot\plugin\resources\memes.json"  "$PluginDir\resources" -Force

Step "4/5 下载素材(约 400MB,只需第一次)"
Push-Location $ServiceDir
& "$Venv\Scripts\python.exe" fetch_resources.py
Pop-Location

Step "5/5 注册计划任务"
Unregister-ScheduledTask -TaskName 'MemeService' -Confirm:$false -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute "$ServiceDir\start.bat" -WorkingDirectory $ServiceDir
$t1 = New-ScheduledTaskTrigger -AtStartup
$t2 = New-ScheduledTaskTrigger -AtLogOn
$set = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
  -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
  -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
$prin = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest -LogonType ServiceAccount
Register-ScheduledTask -TaskName 'MemeService' -Action $action -Trigger @($t1,$t2) `
  -Settings $set -Principal $prin -Force | Out-Null
Start-ScheduledTask -TaskName 'MemeService'

Write-Host "`n完成。检查 http://127.0.0.1:8766/health" -ForegroundColor Green
