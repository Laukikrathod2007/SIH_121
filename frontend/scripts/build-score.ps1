# Builds public/story/score.mp3 (74 s) from "Aphelion" by Scott Buckley
# (www.scottbuckley.com.au), CC BY 4.0. Needs ffmpeg and internet.
#   powershell -File scripts/build-score.ps1
#
# Cut to the story: the quiet, suspended opening (0-19 s) under the Earth
# and "drilling blind"; the slow build (40-60 s) under the buried reports
# and extraction; the full orchestra and synth (118-160 s) under the
# solution and the alert. 3 s equal-power crossfades, faded in and out,
# loudness normalised to -17 LUFS (a bed under the story, not over it).
$tmp = Join-Path $env:TEMP 'Aphelion.mp3'
curl.exe -s -L --max-time 240 -o $tmp 'https://www.scottbuckley.com.au/library/wp-content/uploads/2026/04/Aphelion.mp3'
ffmpeg -y -loglevel error -i $tmp -i $tmp -i $tmp -filter_complex "[0:a]atrim=0:19,asetpts=PTS-STARTPTS[a];[1:a]atrim=40:60,asetpts=PTS-STARTPTS[b];[2:a]atrim=118:160,asetpts=PTS-STARTPTS[c];[a][b]acrossfade=d=3:c1=qsin:c2=qsin[ab];[ab][c]acrossfade=d=3:c1=qsin:c2=qsin,afade=t=in:d=1.5,atrim=0:74,afade=t=out:st=69:d=5,loudnorm=I=-17:TP=-1.5:LRA=11" -ac 2 -ar 44100 -b:a 128k public/story/score.mp3
