# Dev helper: capture /story frames in the background.
#   powershell -File scripts/story-frames.ps1 7 30 44
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
  Where-Object { $_.CommandLine -match 'headless' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
$env:FILM_URL = 'http://localhost:5173/story'
node scripts/film-frames.mjs @args *> film-frames/log.txt
"done" | Out-File -Append film-frames/log.txt
