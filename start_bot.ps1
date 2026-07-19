# ─── YT Live Bot Launcher ───────────────────────────────────────────────────
# UTF-8 encoding for emoji + unicode support
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding           = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# Go to script folder
Set-Location $PSScriptRoot

# Launch bot — auto-restart on crash or exit
while ($true) {
    python bot.py
    Write-Host ""
    Write-Host "  ⚠  Bot band ho gaya! 5 second mein dobara start hoga..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Write-Host "  ↺  Bot restart ho raha hai..." -ForegroundColor Cyan
}