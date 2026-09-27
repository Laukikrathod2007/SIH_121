# Downloaded Files Status
## eRTMAC-NWIS Data Collection Progress

**Last Updated:** September 27, 2026  
**Auto-generated tracking document**

---

## ✅ Successfully Downloaded (Auto-Downloaded by AI)

| File Name | Size | Location | Status | Notes |
|-----------|------|----------|--------|-------|
| `78B-32-DailyDrillingReports-6-27thru7-31.pdf` | ~0.86 MB | `data/raw/forge/78b32_ddr/` | ✅ Downloaded | Utah FORGE DDRs (35 days) |

**Total Downloaded:** 1 file (~0.86 MB)

---

## 📋 Ready to Download (Direct Links Available)

### High Priority - Do These Next

| File Name | Source | Direct Link | Storage Location |
|-----------|--------|-------------|------------------|
| **UOU_FORGE-78B-32_R1A_Sonic.Pdf** | Utah FORGE | https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_R1A_Sonic.Pdf | `data/raw/forge/78b32_ddr/` |
| **UOU_FORGE-78B-32_Temperature_Log.Pdf** | Utah FORGE | https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_Temperature_Log_22Jul21_.Pdf | `data/raw/forge/78b32_ddr/` |

**Download Command (Copy-paste into PowerShell):**
```powershell
# Download Utah FORGE Sonic Log
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_R1A_Sonic.Pdf" -OutFile "data/raw/forge/78b32_ddr/UOU_FORGE-78B-32_R1A_Sonic.Pdf"

# Download Utah FORGE Temperature Log
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_Temperature_Log_22Jul21_.Pdf" -OutFile "data/raw/forge/78b32_ddr/UOU_FORGE-78B-32_Temperature_Log.Pdf"
```

---

## 🔄 Requires Manual Download (Large Datasets)

### 1. Equinor Volve Dataset (PRIMARY - HIGH PRIORITY)

**Why:** Main source for WCRs, DDRs, WITSML data

**Recommended Method: Kaggle (Fastest)**
- Link: https://www.kaggle.com/datasets/lamyalbert/volve-production-data
- Size: ~2-5 GB (subset) or ~30 GB (complete)
- Requires: Free Kaggle account
- Storage: `data/raw/volve/`

**Steps:**
1. Go to Kaggle link
2. Click "Download" (may prompt for login/signup)
3. Extract ZIP file
4. Move folders:
   - PDF reports → `data/raw/volve/ddr/` and `data/raw/volve/wcr/`
   - CSV files → `data/raw/volve/witsml/`
   - LAS files → `data/raw/volve/las_logs/`

**Alternative Method: Official Equinor Portal**
- Link: https://www.equinor.com/energy/volve-data-sharing
- Method: Microsoft Azure Storage Explorer or direct download
- See `DATA_DOWNLOAD_GUIDE.md` for detailed instructions

**Status:** ⏳ Pending manual download

---

### 2. Volve WITSML CSV Files (VALIDATION DATA)

**Why:** Ground truth for OCR validation

**Link:** https://www.ux.uis.no/~atunkiel/file_list.html

**Files to Download:**
- `15_9-F-11.csv` (Main well - ~50 MB)
- `15_9-F-12.csv` (Injection well - ~30 MB)
- `15_9-F-14.csv` (Development well - ~40 MB)

**Storage:** `data/raw/volve/witsml/`

**Status:** ⏳ Pending manual download

---

### 3. Norwegian SODIR Wellbore Data (METADATA)

**Why:** Structured wellbore metadata (no OCR needed)

**Link:** https://factpages.sodir.no/en/wellbore

**Steps:**
1. Visit link above
2. Search for "Volve" field wells
3. Select 10-20 wells
4. Export as CSV
5. Save to `data/raw/sodir/wellbore_master.csv`

**Status:** ⏳ Pending manual download

---

## 📊 Data Collection Progress

### Overall Status

| Category | Files Needed | Downloaded | Remaining | Progress |
|----------|--------------|------------|-----------|----------|
| **Utah FORGE DDRs** | 3 | 1 | 2 | 33% |
| **Volve WCRs** | 10-15 | 0 | 10-15 | 0% |
| **Volve DDRs** | 50-200 | 0 | 50-200 | 0% |
| **Volve WITSML** | 3-10 | 0 | 3-10 | 0% |
| **SODIR Data** | 1 | 0 | 1 | 0% |
| **TOTAL** | ~70-230 | 1 | ~69-229 | <1% |

---

## 🎯 Recommended Download Order

### Phase 1: OCR Development (Do This Week)
1. ✅ Utah FORGE 78B-32 DDR (Already downloaded!)
2. ⏳ Download 2 more Utah FORGE PDFs (links above)
3. ⏳ Download 10-20 Volve DDRs from Kaggle
4. ⏳ Download 3 Volve WITSML CSVs

**Estimated Time:** 1-2 hours  
**Estimated Size:** ~500 MB  
**Purpose:** Start OCR pipeline development immediately

### Phase 2: Full Dataset (Next Week)
5. ⏳ Download complete Volve dataset (30 GB)
6. ⏳ Export SODIR wellbore CSV

**Estimated Time:** 4-6 hours (mostly download time)  
**Estimated Size:** ~30 GB  
**Purpose:** Full-scale OCR processing and database population

---

## ✅ Data Verification Checklist

### For Each Downloaded File

- [ ] File size matches expected range (check against source)
- [ ] PDF files can be opened (not corrupted)
- [ ] CSV files have correct structure (headers present)
- [ ] File names match expected format
- [ ] Storage location is correct

### For Utah FORGE DDR (Already Downloaded)
- [x] File exists: `data/raw/forge/78b32_ddr/78B-32-DailyDrillingReports-6-27thru7-31.pdf`
- [ ] File opens successfully (verify PDF is readable)
- [ ] Contains 35 days of DDRs (June 27 - July 31)
- [ ] Has drilling parameters (depth, mud weight, etc.)
- [ ] Contains incident records (losses, kicks)

---

## 🚀 Quick Start After Downloads

Once you have Phase 1 files downloaded:

```powershell
# 1. Verify folder structure
Get-ChildItem -Path "data/raw" -Recurse -Directory

# 2. Count downloaded files
Get-ChildItem -Path "data/raw" -Recurse -File | Measure-Object

# 3. Check file sizes
Get-ChildItem -Path "data/raw" -Recurse -File | 
    Select-Object FullName, @{N="Size (MB)";E={[math]::Round($_.Length/1MB,2)}}

# 4. Verify PDFs are readable (opens first PDF found)
Get-ChildItem -Path "data/raw" -Recurse -Filter "*.pdf" | 
    Select-Object -First 1 | 
    Invoke-Item
```

---

## 📝 Manual Download Instructions

### For Kaggle Datasets:

1. **Create Kaggle Account** (if you don't have one)
   - Go to https://www.kaggle.com
   - Sign up with email or Google account
   - Verify your email

2. **Download Dataset**
   - Navigate to dataset page
   - Click "Download" button (top right)
   - Wait for download to complete
   - Extract ZIP file

3. **Organize Files**
   - Move PDFs to appropriate folders
   - Keep CSV files organized by well name
   - Rename files if needed for consistency

### For Direct Links (Utah FORGE):

```powershell
# Method 1: PowerShell command (recommended)
Invoke-WebRequest -Uri "<URL>" -OutFile "<destination>"

# Method 2: Browser download
1. Right-click link
2. "Save link as..."
3. Save to appropriate folder

# Method 3: Download manager
Use IDM, Free Download Manager, or similar tool
```

---

## 🆘 Troubleshooting

### Download Fails or Times Out

```powershell
# Retry with increased timeout
Invoke-WebRequest -Uri "<URL>" -OutFile "<destination>" -TimeoutSec 300

# Or download in chunks
# Use browser download manager for large files
```

### File Corrupted After Download

1. Check file size matches expected
2. Re-download the file
3. Try different download method (browser vs. PowerShell)
4. Check disk space availability

### Kaggle Download Requires Login

- Kaggle requires account for dataset downloads
- Free account is sufficient (no payment needed)
- Some datasets may require phone verification

---

## 📞 Need Help?

If any download fails or you're stuck:

1. Check `DATA_DOWNLOAD_GUIDE.md` for alternative sources
2. Search for dataset mirrors on GitHub
3. Ask team members if they've already downloaded
4. Check alternative sources:
   - Andy McDonald's Volve CSVs: https://www.andymcdonald.scot/data/volve/
   - Volve GitHub mirrors: Search "Volve dataset" on GitHub
   - FORGE data.gov mirror: https://catalog.data.gov/dataset/?tags=forge

---

## 🎉 Success Metrics

### Minimum Viable Dataset (MVP)
- ✅ 1 Utah FORGE DDR PDF (Done!)
- ⏳ 2 more Utah FORGE PDFs
- ⏳ 10 Volve DDRs
- ⏳ 3 Volve WITSML CSVs

**Status:** 25% complete (1/4 categories)

### Full Production Dataset
- All MVP files +
- 50-200 Volve DDRs
- 10-15 Volve WCRs
- Complete WITSML data
- SODIR metadata CSV

**Status:** <1% complete

---

## 🗓️ Next Actions

**Today:**
1. ✅ Verify downloaded Utah FORGE DDR opens correctly
2. ⏳ Download 2 more Utah FORGE PDFs (use commands above)
3. ⏳ Sign up for Kaggle account
4. ⏳ Start Volve dataset download from Kaggle

**Tomorrow:**
1. ⏳ Download Volve WITSML CSVs
2. ⏳ Test OCR on Utah FORGE DDR
3. ⏳ Begin Module 2 OCR pipeline development

**This Week:**
1. ⏳ Complete Phase 1 downloads
2. ⏳ Process 10 sample DDRs through OCR
3. ⏳ Validate extraction accuracy vs. WITSML ground truth

---

**Last Updated:** September 27, 2026 16:22 UTC  
**Next Update:** After manual downloads complete

**Note:** Update this file after each download session to track progress.
