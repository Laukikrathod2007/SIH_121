# PowerShell script to reorganize FORGE well data
# Run this from data/ folder

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  FORGE Well Data Reorganization Script" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

$rawPath = "raw"

# Well 4: Extract 56-32 files
Write-Host "[4/5] Organizing Well 56-32..." -ForegroundColor Yellow
Expand-Archive -Path "$rawPath/56-32 Daily Drilling Reports.zip" -DestinationPath "$rawPath/well_4" -Force
Copy-Item "$rawPath/56-32 EOWR - Final 22 July 2021.pdf" -Destination "$rawPath/well_4/" -Force
Write-Host "    ✓ Well 56-32 organized" -ForegroundColor Green

# Well 5: Extract 58-32 files  
Write-Host "[5/5] Organizing Well 58-32..." -ForegroundColor Yellow
Expand-Archive -Path "$rawPath/DailyDrillingReports_Well58-32.zip" -DestinationPath "$rawPath/well_5" -Force
Expand-Archive -Path "$rawPath/58-32_EOWR.zip" -DestinationPath "$rawPath/well_5" -Force
Write-Host "    ✓ Well 58-32 organized" -ForegroundColor Green

Write-Host ""
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  Cleaning up old files..." -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

# Remove old folders
Write-Host "Removing old folders..." -ForegroundColor Yellow
Remove-Item -Path "$rawPath/forge" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$rawPath/sodir" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$rawPath/volve" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "    ✓ Removed: forge/, sodir/, volve/" -ForegroundColor Green

# Remove zip files (data is extracted)
Write-Host "Removing zip files..." -ForegroundColor Yellow
Remove-Item "$rawPath/*.zip" -Force -ErrorAction SilentlyContinue
Write-Host "    ✓ Removed all .zip files" -ForegroundColor Green

Write-Host ""
Write-Host "===================================================================" -ForegroundColor Green
Write-Host "  ✓ REORGANIZATION COMPLETE!" -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Final structure:" -ForegroundColor Cyan
Write-Host "  data/raw/" -ForegroundColor White
Write-Host "    ├── well_1/  (78B-32)" -ForegroundColor White
Write-Host "    ├── well_2/  (16A)" -ForegroundColor White
Write-Host "    ├── well_3/  (16B)" -ForegroundColor White
Write-Host "    ├── well_4/  (56-32)" -ForegroundColor White
Write-Host "    └── well_5/  (58-32)" -ForegroundColor White
Write-Host ""
Write-Host "Next step: Review data/WELL_MAPPING.md to see which well is which" -ForegroundColor Cyan
Write-Host ""
