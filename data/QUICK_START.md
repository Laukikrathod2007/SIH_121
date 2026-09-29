# Quick Start: Data Collection
## Get Your Datasets in 3 Steps

---

## ✅ Step 1: We Already Downloaded This For You!

**Utah FORGE 78B-32 Daily Drilling Reports**
- Location: `data/raw/forge/78b32_ddr/78B-32-DailyDrillingReports-6-27thru7-31.pdf`
- Size: 0.83 MB
- Contains: 35 days of drilling reports (June 27 - July 31)
- Status: ✅ **READY TO USE** - Start OCR testing with this file!

---

## ⚡ Step 2: Download These 2 Files (5 Minutes)

Copy-paste these commands into PowerShell:

```powershell
# Navigate to project directory
cd C:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS

# Download Utah FORGE Sonic Log
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_R1A_Sonic.Pdf" -OutFile "data/raw/forge/78b32_ddr/UOU_FORGE-78B-32_R1A_Sonic.Pdf"

# Download Utah FORGE Temperature Log  
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_Temperature_Log_22Jul21_.Pdf" -OutFile "data/raw/forge/78b32_ddr/UOU_FORGE-78B-32_Temperature_Log.Pdf"

Write-Host "✅ Download complete! You now have 3 PDFs ready for OCR testing." -ForegroundColor Green
```

---

## 🎯 Step 3: Download Main Dataset (Updated - Realistic Approach)

### ⚠️ IMPORTANT: Volve Full Dataset Reality Check

The **complete Volve dataset is ~23 GB** and requires Azure Storage Explorer. For your hackathon, you DON'T need all 40,000 files!

### Option A: Pragmatic Approach (Recommended) ⭐

**What you actually need for MVP:**
- 10-20 sample DDR PDFs for OCR testing
- You already have 1 Utah FORGE DDR ✅
- Generate synthetic data for remaining demos

**Where to get sample Volve data:**

1. **GitHub Repositories with Processed Data:**
   - https://github.com/f0nzie/volve-drilling (Has WITSML processing examples)
   - https://github.com/sgk2004/Volve-Dataset (ML-ready processed data)
   - https://github.com/985185/volve-metadata-index (Metadata index)

2. **Andy McDonald's Blog** (Trusted petroleum data scientist)
   - Blog: https://www.andymcdonald.scot/data/volve/
   - GitHub: https://github.com/andymcdgeo/ (Check for Volve repos)
   - Pre-processed well data available

### Option B: Azure Storage Explorer (For Full Dataset - Optional)

**Only if you need the complete 23 GB dataset:**

1. Download Azure Storage Explorer: https://azure.microsoft.com/products/storage/storage-explorer/
2. Install and open
3. Connect to Azure storage (anonymous access):
   - Storage Account: `datavillagesa`
   - Container: Select "Blob containers" → Search for Volve
4. Navigate to `/Daily Drilling Reports/` folder
5. Download 10-20 PDF files (not the entire folder!)

**Note:** Full download takes hours. For hackathon, sample is sufficient!

---

## 🎊 You're Done! What You Have Now:

### Minimum Viable Dataset (MVP)
- ✅ 1 Utah FORGE DDR (already downloaded)
- ✅ 2 more Utah FORGE PDFs (after Step 2)
- ⏳ 10-20 Volve PDFs (after Step 3)
- ⏳ 3 Volve WITSML CSVs (after Step 3)

**This is enough to:**
- Start OCR pipeline development
- Test extraction accuracy
- Populate database (Module 1)
- Train risk models (Module 7)

---

## 🚀 Next Actions

### For OCR Developer
```powershell
# Open the downloaded DDR to verify it works
Invoke-Item "data/raw/forge/78b32_ddr/78B-32-DailyDrillingReports-6-27thru7-31.pdf"

# Now start building OCR pipeline to extract:
# - Well name
# - Date
# - Depth
# - Drilling parameters
# - Incidents
```

### For Database Developer
```powershell
# Once Volve CSVs downloaded, load into database
# CSVs are already in structured format - no OCR needed!
```

### For ML Developer
```powershell
# Use incident records from DDRs as training labels
# Extract incidents: kicks, losses, stuck pipe, NPT
```

---

## 📊 What Data Looks Like

### Daily Drilling Report (PDF) Contains:
```
Date: June 27, 2021
Well: 78B-32
Current Depth: 3,456 ft
ROP: 25 ft/hr
Mud Weight: 9.2 ppg
Incidents: Lost circulation @ 3,420 ft (15 bbl loss)
NPT: 2.5 hours (waiting on cement)
```

### WITSML CSV Contains:
```csv
timestamp,depth_m,rop_m_hr,wob_kg,rpm,torque_nm,spp_bar,flow_rate_lpm
2008-03-14T06:00:00Z,1234.5,12.3,45000,120,15000,180,1200
2008-03-14T06:01:00Z,1235.2,12.8,46000,125,15500,182,1210
```

---

## 🆘 Problems?

### "PowerShell command doesn't work"
```powershell
# Try with full path
cd "C:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS"
# Then run Invoke-WebRequest commands
```

### "Kaggle requires payment"
**No!** Kaggle is free. You just need to:
1. Create account (free)
2. Verify email
3. Download (no payment needed)

### "Download is too slow"
- Utah FORGE: Try browser download (right-click link → "Save as...")
- Volve: Download overnight, it's 2-5 GB
- Or use Volve CSVs only (skip PDFs initially)

### "I don't have enough disk space"
- Minimum: ~500 MB (Utah FORGE + Volve CSVs)
- Recommended: ~5 GB (includes 10-20 Volve PDFs)
- Full dataset: ~30 GB (optional, download later)

---

## 📖 Full Documentation

- **Detailed Instructions:** `DATA_DOWNLOAD_GUIDE.md`
- **Progress Tracking:** `DOWNLOADED_FILES_STATUS.md`
- **Data Organization:** `README.md`
- **Strategic Planning:** `../docs/04-data-collection-plan.md`

---

## ⏱️ Time Estimate

| Task | Time | Status |
|------|------|--------|
| Step 1 (Already done) | 0 min | ✅ Complete |
| Step 2 (Utah FORGE PDFs) | 5 min | ⏳ Run commands above |
| Step 3 (Volve CSVs) | 30 min | ⏳ Manual download |
| Step 3 (Volve full dataset) | 1-2 hours | ⏳ Optional, can do later |

**Total for MVP: 35 minutes** 🎯

---

## 🎓 Pro Tips

1. **Don't wait for everything** - Start OCR development with the 1 PDF we already downloaded
2. **Use CSVs first** - Skip OCR complexity initially, use pre-parsed Volve CSVs
3. **Download overnight** - Full Volve dataset is large, download while sleeping
4. **Organize as you go** - Follow folder structure strictly from the start

---

**Ready to start?** Run the Step 2 PowerShell commands above! ⚡
