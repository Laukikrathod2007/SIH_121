# NWIS Nearby Wells Map

Standalone interactive map: user-defined radius search around an active well, offset wells colour-ringed by incident type, click a well to see its incident history with source-document citations that open a real PDF viewer.

Extracted from the NWIS project (SIH PS 26121). No backend framework needed — just a tiny PDF file server.

## Run it (2 terminals)

```bash
# Terminal 1 — the app
npm install
npm run dev
# -> http://localhost:5180

# Terminal 2 — evidence PDF server (for the "open source document" links)
cd server
npm install
npm start
# -> http://localhost:4000
```

## What's in here

- `src/NearbyWellsMap.tsx` — the map itself. Radius slider, hazard filters, basemap switch (light/streets/satellite), distance lines, well markers ringed by incident mix. **Zero backend dependency** — pure client-side, works with any `WellPoint[]` array.
- `src/WellDetailPanel.tsx` — right-side panel shown when you click an offset well: stats + incident timeline by depth + "what they did" + citation.
- `src/EvidenceViewer.tsx` — the drawer that opens a cited PDF at the right page. Needs the tiny `server/`.
- `src/wells-data.json` / `src/events-data.json` — real demo data (12 wells, Upper Assam basin, 39 incidents) copied from the source project.
- `src/App.tsx` — wires the three components together. **This is the file to copy from** if you're integrating into your own app.
- `server/` — ~30-line Express server that serves the bundled sample PDFs so citations resolve to real documents.

## Use with your own data

Replace `wells-data.json` with your own wells in this shape:

```json
{
  "well_id": "...", "well_name": "...", "field": "...",
  "lat": 0, "lon": 0, "status": "...", "well_type": "...",
  "total_depth_md_m": 0, "total_events": 0, "npt_hours": 0,
  "events_by_type": { "MUD_LOSS": 2 }
}
```

And `events-data.json` (keyed by `well_id`) in the shape documented in `WellDetailPanel.tsx`'s `WellEvent` type. Point `EvidenceViewer`'s `apiBase` prop at your own PDF-serving endpoint, or keep using `server/` with your own PDFs dropped into `server/pdfs/`.

## No evidence server needed?

If you just want the map (no click-through detail panel / PDFs), use `NearbyWellsMap` alone — it has no dependency on the other two files.
