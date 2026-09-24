#Requires -Version 5.1
# MEV kurulum — tek komut:
#   powershell -ExecutionPolicy Bypass -File kur.ps1
$ErrorActionPreference = "Stop"
$MevDir = Split-Path -Parent $MyInvocation.MyCommand.Path

try { $py = (python --version 2>&1) } catch { Write-Host "Python bulunamadi: https://www.python.org/downloads/"; exit 1 }
Write-Host "Bulundu: $py (klasor: $MevDir)"

Write-Host "`n[1/3] Dogrulama calistiriliyor..."
& python "$MevDir\test_all.py" | Select-Object -Last 1
if ($LASTEXITCODE -ne 0) { Write-Host "Testler basarisiz (exit $LASTEXITCODE). Durduruldu."; exit 1 }

Write-Host "`n[2/3] Skill kopyalaniyor..."
$SkillSrc = Join-Path $MevDir ".opencode\skills\mev"
if (-not (Test-Path -LiteralPath "$SkillSrc\SKILL.md")) { Write-Host "SKILL.md bulunamadi: $SkillSrc"; exit 1 }
$Targets = @(
  "$env:USERPROFILE\.config\opencode\skills\mev",
  "$env:USERPROFILE\.claude\skills\mev",
  "$env:USERPROFILE\.agents\skills\mev"
)
foreach ($t in $Targets) {
  New-Item -ItemType Directory -Path $t -Force | Out-Null
  Copy-Item -Path "$SkillSrc\SKILL.md" -Destination "$t\SKILL.md" -Force
  Write-Host "  + $t"
}

Write-Host "`n[3/3] MCP kaydi (opencode.json'a ekle):"
$mcp = '{"mcp":{"mev":{"type":"local","command":["python","' + ($MevDir -replace '\\','/') + '/mcp_server.py"],"enabled":true}}}'
Write-Host "  $mcp"

Write-Host "`nBitti. SON ADIM (sart): IDE'yi kapatip yeniden ac"
Write-Host "(Cursor / Antigravity / terminal). MCP ve skill'ler acilista yuklenir,"
Write-Host "yeniden baslatmadan gorunmez."
Write-Host "`nKokpit: python `"$MevDir\dashboard.py`"  ->  http://127.0.0.1:47921"
