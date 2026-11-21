# Builds public/story/score.mp3 (67 s) from "Lightless Dawn" by Kevin
# MacLeod (incompetech.com), CC BY 4.0. Needs ffmpeg and internet.
#   powershell -File scripts/build-score.ps1
#
# Cut: the piece's quiet opening (2-24 s), its build (152-179 s) and its
# climax (307-335 s), crossfaded 4 s each, faded in/out, loudness
# normalised to -18 LUFS (a bed under the story, not over it).
$tmp = Join-Path $env:TEMP 'Lightless_Dawn.mp3'
curl.exe -s -L --max-time 180 -o $tmp 'https://incompetech.com/music/royalty-free/mp3-royaltyfree/Lightless%20Dawn.mp3'
ffmpeg -y -loglevel error -i $tmp -i $tmp -i $tmp -filter_complex "[0:a]atrim=2:24,asetpts=PTS-STARTPTS[a];[1:a]atrim=152:179,asetpts=PTS-STARTPTS[b];[2:a]atrim=307:335,asetpts=PTS-STARTPTS[c];[a][b]acrossfade=d=4:c1=tri:c2=tri[ab];[ab][c]acrossfade=d=4:c1=tri:c2=tri,afade=t=in:d=2.5,afade=t=out:st=62:d=5,atrim=0:67,loudnorm=I=-18:TP=-2:LRA=11" -ac 2 -ar 44100 -b:a 128k public/story/score.mp3
