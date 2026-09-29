# Data Download Guide
## eRTMAC-NWIS Required Datasets

**Last Updated:** September 27, 2026  
**Purpose:** Step-by-step instructions to download all required datasets for OCR/NLP pipeline

---

## 📊 Overview: What Data We Need

| Category | Format | Volume | Priority | Status |
|----------|--------|--------|----------|--------|
| **Volve WCRs** (Well Completion Reports) | PDF | 10-15 files | HIGH | Manual download |
| **Volve DDRs** (Daily Drilling Reports) | PDF | 50-200 files | HIGH | Manual download |
| **Volve WITSML** (Real-time data) | CSV/XML | ~500 MB | HIGH | Direct download available |
| **Volve Well Logs** | LAS | 50-100 files | MEDIUM | Manual download |
| **Utah FORGE DDRs** (78B-32) | PDF | 10-20 files | MEDIUM | Direct download available ✅ |
| **SODIR Wellbore Data** | CSV | 1 file | LOW | Web export |
| **Synthetic OIL India Data** | JSON | Generated | HIGH | To be created |

---

## 🎯 Priority Download Order

### PHASE 1: Quick Start (Do This First) - 2 Hours

**Goal:** Get 10-20 sample documents to start OCR pipeline development

1. ✅ **Utah FORGE 78B-32 DDRs** (Easiest - Direct PDF links)
2. ✅ **Volve WITSML CSVs** (For validation ground truth)
3. **Volve Sample DDRs** (10-20 PDFs from Kaggle)

### PHASE 2: Full Dataset - 1 Day

4. **Complete Volve Dataset** (40,000 files via Azure or Kaggle)
5. **SODIR CSV Export** (Wellbore metadata)

---

## 📥 DETAILED DOWNLOAD INSTRUCTIONS

---

### 1. Utah FORGE 78B-32 Daily Drilling Reports ✅ (DIRECT DOWNLOAD)

**Why:** Perfect for OCR testing - messy scanned PDFs with real drilling data

**Direct Download Link:**
```
https://gdr.openei.org/files/1330/78B-32-DailyDrillingReports-6-27thru7-31.pdf
```

**Storage Location:**
```
data/raw/forge/78b32_ddr/
```

**Manual Steps:**
1. Open browser: https://gdr.openei.org/submissions/1330
2. Look for "Submission Downloads" section at bottom
3. Download these files:
   - `78B-32-DailyDrillingReports-6-27thru7-31.pdf` (35 days of DDRs)
   - `UOU_FORGE-78B-32_R1A_Sonic.Pdf` (Well logs)
   - `UOU_FORGE-78B-32_Temperature_Log_22Jul21_.Pdf` (Temperature logs)

4. Save all PDFs to: `data/raw/forge/78b32_ddr/`

**What You'll Get:**
- 35 days of daily drilling reports (June 27 - July 31)
- Real incidents: lost circulation, mud weight changes
- Handwritten notes and poor-quality scans (perfect for OCR stress testing)

---

### 2. Equinor Volve Field Dataset (PRIMARY SOURCE)

**Why:** Industry-standard dataset with WCRs, DDRs, WITSML, well logs

#### Option A: Kaggle (Recommended - Fastest) ⭐

**Link:** https://www.kaggle.com/datasets/lamyalbert/volve-production-data

**Steps:**
1. Go to Kaggle link above
2. Click "Download" button (may require free Kaggle account)
3. Extract ZIP file
4. Move folders:
   - PDFs of reports → `data/raw/volve/ddr/` and `data/raw/volve/wcr/`
   - CSV files → `data/raw/volve/witsml/`
   - LAS files → `data/raw/volve/las_logs/`

**What You'll Get:**
- Pre-organized subset of Volve data (~2-5 GB)
- Ready-to-use CSV files (no OCR needed for quick start)
- Sample PDFs for OCR testing

#### Option B: Equinor Official Portal (Complete Dataset)

**Link:** https://www.equinor.com/energy/volve-data-sharing

**Steps:**
1. Visit the official portal
2. Scroll to "Access the Volve dataset"
3. Two download methods:
   - **Microsoft Azure Storage Explorer** (Recommended for full 40,000 files)
   - **Direct download links** (Smaller subsets)

**For Azure Storage Explorer:**
1. Download Azure Storage Explorer: https://azure.microsoft.com/en-us/products/storage/storage-explorer/
2. Install and open the application
3. Connect to Volve storage:
   - Storage Account Name: `datavillagesa`
   - Container: `volve`
   - Access: Anonymous (public access)
4. Navigate folders:
   - `/reports/` → Download DDRs and WCRs
   - `/witsml/` → Download real-time drilling data
   - `/las/` → Download well logs

**Storage Location:**
```
data/raw/volve/
├── wcr/              # Well Completion Reports
├── ddr/              # Daily Drilling Reports
├── witsml/           # Real-time WITSML data
├── mud_reports/      # Mud logging reports
└── las_logs/         # Well log files (LAS format)
```

#### Option C: Andy McDonald's Pre-parsed CSVs (Quick Start)

**Link:** https://www.andymcdonald.scot/data/volve/

**Why:** Pre-digitized CSVs, no OCR needed for initial testing

**Steps:**
1. Visit the link above
2. Download CSV files from GitHub repositories linked on the page
3. Save to `data/raw/volve/witsml/`

**What You'll Get:**
- Pre-parsed drilling parameters (depth, ROP, WOB, RPM, etc.)
- Time-series data ready for database import
- No OCR required - use for quick Module 1 validation

---

### 3. Volve WITSML Real-time Data ✅ (DIRECT CSV DOWNLOAD)

**Why:** Ground truth for validating OCR extraction accuracy

**Link:** https://www.ux.uis.no/~atunkiel/file_list.html

**Steps:**
1. Visit the link above
2. Download CSV files (multiple wells available)
3. Save to `data/raw/volve/witsml/`

**Recommended Files:**
- `15_9-F-11.csv` (Main production well)
- `15_9-F-12.csv` (Injection well)
- `15_9-F-14.csv` (Development well)

**Storage Location:**
```
data/raw/volve/witsml/
```

**What You'll Get:**
- Timestamp, depth, ROP, WOB, RPM, torque, SPP, flow rate
- Real-time drilling parameters (1-minute intervals)
- Use this to validate OCR-extracted DDR data

---

### 4. Norwegian SODIR Wellbore Data (CSV Export)

**Why:** Structured metadata for validation baseline (no OCR needed)

**Link:** https://factpages.sodir.no/en/wellbore

**Steps:**
1. Visit the link above
2. Click "Search" (no login required)
3. Apply filters:
   - Field: "Volve" (to match our primary dataset)
   - Status: "Production" or "Completed"
   - Purpose: "Development"
4. Select wells (10-20 wells recommended)
5. Click "Export" → Choose "CSV" format
6. Save as `data/raw/sodir/wellbore_master.csv`

**Alternative - Full Database Export:**
- Go to: https://factpages.sodir.no/en/wellbore
- Bottom of page: "Download full dataset" link
- Export complete wellbore database (~5,000 wells)

**Storage Location:**
```
data/raw/sodir/
├── wellbore_master.csv
├── casing_programs.csv (if available)
└── incidents.csv (if available)
```

**What You'll Get:**
- Well names, locations (lat/lng), depths
- Casing programs, formation tops
- Incident records (kicks, blowouts, losses)

---

### 5. Additional Optional Sources

#### Utah FORGE Well 56-32 Data

**Link:** https://gdr.openei.org (Search "FORGE 56-32")

**Storage Location:** `data/raw/forge/56-32_logs/`

#### Utah FORGE Well 16A(78)-32 Data (More Recent)

**Link:** https://catalog.data.gov/dataset/utah-forge-well-16a78-32-drilling-data

**What's Available:**
- Survey data
- Daily reports (2020-2021 drilling)
- Summaries of daily operations
- Rig photos

**Storage Location:** `data/raw/forge/incident_reports/`

---

## 📁 Final Folder Structure (After All Downloads)

```
data/
├── raw/
│   ├── volve/
│   │   ├── wcr/                    # 10-15 Well Completion Reports (PDF)
│   │   ├── ddr/                    # 50-200 Daily Drilling Reports (PDF)
│   │   ├── witsml/                 # Real-time drilling data (CSV)
│   │   │   ├── 15_9-F-11.csv
│   │   │   ├── 15_9-F-12.csv
│   │   │   └── 15_9-F-14.csv
│   │   ├── mud_reports/            # Mud logging reports (PDF)
│   │   └── las_logs/               # Well logs (LAS format)
│   │
│   ├── forge/
│   │   ├── 78b32_ddr/
│   │   │   ├── 78B-32-DailyDrillingReports-6-27thru7-31.pdf ✅
│   │   │   ├── UOU_FORGE-78B-32_R1A_Sonic.Pdf
│   │   │   └── UOU_FORGE-78B-32_Temperature_Log_22Jul21_.Pdf
│   │   ├── 56-32_logs/             # Well 56-32 data
│   │   └── incident_reports/       # NPT event records
│   │
│   └── sodir/
│       ├── wellbore_master.csv     # Wellbore metadata
│       ├── casing_programs.csv     # Casing data
│       └── incidents.csv           # Historical incidents
│
├── processed/
│   ├── extracted_json/             # OCR output (JSON format)
│   ├── validated/                  # Human-verified samples
│   └── training_labels/            # Labels for ML model training
│
└── synthetic/
    └── oil_india_mock/             # Synthetic OIL India wells (to be generated)
```

---

## ✅ Data Download Checklist

### Phase 1: Quick Start (Today)
- [ ] Download Utah FORGE 78B-32 DDRs PDF (1 file, ~10 MB)
- [ ] Download Volve WITSML CSVs (3 files, ~50 MB)
- [ ] Download 10 sample Volve DDRs from Kaggle

### Phase 2: Full Dataset (This Week)
- [ ] Download complete Volve dataset via Kaggle or Azure Storage Explorer
- [ ] Export SODIR wellbore CSV (1 file, ~5 MB)
- [ ] Organize all files into folder structure above

### Phase 3: Validation (Next Week)
- [ ] Verify file integrity (check file sizes, open sample PDFs)
- [ ] Test OCR on 5 sample PDFs
- [ ] Compare OCR output vs. WITSML ground truth

---

## 🚀 Quick Start Commands

After downloading datasets, verify your folder structure:

```powershell
# Check what you've downloaded
Get-ChildItem -Path "data/raw" -Recurse -File | Select-Object FullName, Length

# Count files by category
(Get-ChildItem -Path "data/raw/volve/ddr" -File).Count
(Get-ChildItem -Path "data/raw/volve/witsml" -File).Count
(Get-ChildItem -Path "data/raw/forge/78b32_ddr" -File).Count
```

---

## 🆘 Troubleshooting

### Issue: Equinor Volve portal not loading
**Solution:** Use Kaggle mirror: https://www.kaggle.com/datasets/lamyalbert/volve-production-data

### Issue: Azure Storage Explorer connection fails
**Solution:** 
1. Check internet connection
2. Try direct download links on Equinor portal
3. Use Andy McDonald's pre-parsed CSVs as fallback

### Issue: FORGE PDFs not downloading
**Solution:**
- Try different browser (Chrome recommended)
- Right-click PDF link → "Save link as..."
- Check data.gov mirror: https://catalog.data.gov/dataset/?tags=forge

### Issue: SODIR export not working
**Solution:**
- Use Apify scraper: https://apify.com/jungle_synthesizer/sodir-norway-petroleum-factpages-scraper
- Or manually copy data from individual well pages (10-20 wells only)

---

## 📊 Data Volume Summary

| Source | File Count | Estimated Size | Download Time |
|--------|-----------|----------------|---------------|
| Utah FORGE 78B-32 | 3-5 PDFs | 50 MB | 5 minutes |
| Volve WITSML CSVs | 3-10 files | 100 MB | 10 minutes |
| Volve DDRs (sample) | 10-20 PDFs | 200 MB | 30 minutes |
| Volve Complete Dataset | 40,000 files | 20-30 GB | 1-6 hours |
| SODIR Wellbore CSV | 1 file | 5 MB | 5 minutes |
| **TOTAL (Quick Start)** | **~20 files** | **~350 MB** | **~1 hour** |
| **TOTAL (Full Dataset)** | **~40,000 files** | **~30 GB** | **~6 hours** |

---

## 📞 Need Help?

If any download link is broken or inaccessible:
1. Check the `04-data-collection-plan.md` document for alternative sources
2. Search GitHub for "Volve dataset" - many researchers have mirrors
3. Contact Equinor Open Data team: https://www.equinor.com/energy/volve-data-sharing (support email on page)

---

## ✨ Next Steps After Download

1. **Verify downloads:** Check file sizes match expected values
2. **Test OCR on 5 PDFs:** Ensure PaddleOCR can extract text
3. **Load WITSML CSVs into database:** Populate Module 1 tables
4. **Generate synthetic OIL India data:** Use Volve as templates
5. **Start Module 2 OCR pipeline:** Process all DDRs systematically

---

**Pro Tip:** Don't wait to download everything! Start with Phase 1 (Utah FORGE + Volve CSVs) and begin OCR development immediately. Download the full Volve dataset overnight while you're building the pipeline.
