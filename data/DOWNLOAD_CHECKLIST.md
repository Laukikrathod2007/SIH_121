# Data Download Checklist
## Track What You Have vs. What You Need

**Last Updated:** September 27, 2026  
**Status:** In Progress

---

## ✅ Already Downloaded (Automatic)

| File | Size | Location | Status |
|------|------|----------|--------|
| 78B-32 DDR (35 days) | 0.83 MB | `data/raw/forge/78b32_ddr/` | ✅ Done |
| FORGE Sonic Log | 2.63 MB | `data/raw/forge/78b32_ddr/` | ✅ Done |
| FORGE Temperature Log | 0.69 MB | `data/raw/forge/78b32_ddr/` | ✅ Done |

**Total Downloaded:** 3 PDFs (4.15 MB) ✅

---

## 🎯 Priority 1: Download These Next (High Priority)

### 1. More Utah FORGE Wells (Aim for 10 total PDFs)

**Currently have:** 3 PDFs  
**Need:** 7 more PDFs

**Where to download:**

#### Option A: Search GDR Portal (Recommended)
1. Go to: https://gdr.openei.org
2. Search: "FORGE well" or "FORGE drilling"
3. Look for these submissions:
   - Well 16A(78)-32 Drilling Data
   - Well 56-32 Drilling Data
   - Well 58-32 Data
4. Download any PDFs marked as "Daily Drilling Reports" or "Drilling Summary"

**Specific Links to Try:**

```powershell
# Well 16A(78)-32 Drilling Summary
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1296/Drilling%20Summary%20Well%2016A(78)-32.pdf" -OutFile "data/raw/forge/78b32_ddr/Well-16A-Drilling-Summary.pdf"
```

#### Option B: Data.gov Search
1. Go to: https://catalog.data.gov/dataset/?tags=forge
2. Search: "Utah FORGE drilling"
3. Look for datasets with "drilling reports" or "daily reports"
4. Download PDFs

**Target:** 7 more PDFs = 10 total FORGE PDFs ✅

---

### 2. Norwegian SODIR Wellbore Data (Validation Baseline)

**Currently have:** 0 CSV  
**Need:** 1 CSV file

**How to download:**

1. Go to: https://factpages.sodir.no/en/wellbore
2. In search box, type: "15/9-F" (Volve field)
3. You'll see wells like:
   - 15/9-F-1
   - 15/9-F-11 (Main production well)
   - 15/9-F-12 (Injection well)
   - 15/9-F-14
4. Select 10 wells (check boxes)
5. Click "Export" → Choose "CSV"
6. Save as: `data/raw/sodir/volve_wells.csv`

**Alternative if export doesn't work:**
- Export 5 wells at a time
- Use different browser (Chrome recommended)
- Or skip this - not critical for MVP

**Status:** ⏳ Pending

---

## 🎯 Priority 2: Optional Enhancement (Nice to Have)

### 3. Sample Volve DDRs via Azure Storage (Optional)

**Currently have:** 0 Volve PDFs  
**Need:** 5-10 PDFs (optional, for extra validation)

**Only do this if you have time and want extra validation data!**

**How to download:**

1. **Download Azure Storage Explorer:**
   - Link: https://azure.microsoft.com/products/storage/storage-explorer/
   - Install for Windows

2. **Connect to Volve storage:**
   - Open Azure Storage Explorer
   - Click "Connect" → "Blob container"
   - Display name: "Volve Dataset"
   - Use connection string:
     ```
     DefaultEndpointsProtocol=https;AccountName=datavillagesa;EndpointSuffix=core.windows.net
     ```
   - Click "Next" → "Connect"

3. **Download selectively:**
   - Navigate: Containers → "volve" → "Daily Drilling Reports" or "Well Completion Reports"
   - Select 5-10 files ONLY (not entire folder!)
   - Right-click → Download to `data/raw/volve/ddr/`

**Warning:** Each file can be 5-50 MB. Full dataset is 23 GB!

**Status:** ⏳ Optional (low priority)

---

## 🎯 Priority 3: Generate Synthetic Data (This Week)

### 4. Synthetic OIL India Wells

**Currently have:** 0 JSON files  
**Need:** 20 JSON files

**This you'll CREATE, not download!**

**Steps:**
1. Use data from FORGE PDFs as templates
2. Create Python script to generate synthetic wells
3. Map to OIL India context:
   - Well names: "Nahorkatiya-A1", "Moran-B2", "Digboi-C3"
   - Formations: Barail Formation, Girujan Clay
   - Locations: Upper Assam coordinates

**Script location:** To be created in Module 3
**Output location:** `data/synthetic/oil_india_mock/`

**Status:** ⏳ To be generated (requires coding)

---

## 📊 Current Progress Summary

| Category | Target | Downloaded | Remaining | Progress |
|----------|--------|------------|-----------|----------|
| **FORGE DDRs** | 10 PDFs | 3 ✅ | 7 | 30% |
| **SODIR CSV** | 1 file | 0 | 1 | 0% |
| **Volve PDFs (optional)** | 5-10 | 0 | 5-10 | 0% |
| **Synthetic OIL Data** | 20 JSON | 0 | 20 | 0% |
| **TOTAL** | ~40 files | 3 | ~37 | 7.5% |

---

## ✅ Minimum Viable Dataset (MVP)

**What you MUST have to start OCR development:**

- [x] 1-3 FORGE DDRs ✅ **You have this!**
- [ ] 7 more FORGE PDFs (aim for 10 total)
- [ ] 1 SODIR CSV (validation baseline)
- [ ] 20 synthetic OIL JSON (generate with script)

**With MVP, you can:**
- ✅ Build OCR pipeline
- ✅ Test extraction accuracy
- ✅ Populate database
- ✅ Train risk models
- ✅ Demo full system

---

## 🚀 Quick Actions (Do Today)

### Action 1: Search for More FORGE PDFs (30 min)

```powershell
# Navigate to project
cd C:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS

# Try downloading Well 16A drilling summary
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1296/Drilling%20Summary%20Well%2016A(78)-32.pdf" -OutFile "data/raw/forge/78b32_ddr/Well-16A-Summary.pdf"
```

Then manually search:
1. https://gdr.openei.org → Search "FORGE"
2. https://catalog.data.gov/dataset/?tags=forge
3. Download any drilling-related PDFs you find

### Action 2: Export SODIR CSV (15 min)

1. Open: https://factpages.sodir.no/en/wellbore
2. Search: "15/9-F"
3. Select 10 wells
4. Export as CSV
5. Save to: `data/raw/sodir/volve_wells.csv`

---

## 📝 Update This Checklist

After each download session, update the progress:

```powershell
# Check what you have
Get-ChildItem -Path "data/raw" -Recurse -File | 
    Where-Object {$_.Extension -in @('.pdf','.csv','.json')} | 
    Select-Object Name, @{Name="Size (MB)";Expression={[math]::Round($_.Length/1MB,2)}}
```

---

## 🎯 Success Criteria

### Week 1 Goal:
- [ ] 10 FORGE PDFs downloaded
- [ ] 1 SODIR CSV exported
- [ ] OCR pipeline started (using existing 3 PDFs)

### Week 2 Goal:
- [ ] 20 synthetic OIL India wells generated
- [ ] Database populated with all data
- [ ] OCR validation complete (>94% accuracy)

### Optional (If Time):
- [ ] 5-10 Volve PDFs downloaded via Azure
- [ ] Additional FORGE wells

---

## 🆘 If You Get Stuck

### Can't Find More FORGE PDFs?
**Solution:** You already have 3 PDFs (4.15 MB of real data). This is enough to:
- Build OCR pipeline
- Test extraction
- Validate accuracy
- Generate synthetic data for bulk testing

### SODIR Export Not Working?
**Solution:** Skip it for now. It's just for validation baseline - not critical for MVP.

### Don't Have Time for Full Downloads?
**Solution:** Focus on what you have:
- 3 FORGE PDFs ✅
- Generate synthetic data (faster than downloading)
- Use manual transcription for validation

---

## 📖 Related Documentation

- **START_HERE.md** - Quick data collection overview
- **ALTERNATIVE_DATA_STRATEGY.md** - Pragmatic approach explanation
- **DATA_DOWNLOAD_GUIDE.md** - Detailed download instructions

---

## 🎊 Remember:

**You already have enough data to start coding!**

The 3 FORGE PDFs you downloaded contain:
- 35+ days of drilling operations
- Real drilling parameters
- Real incidents
- Multiple log types

**Your teammate can start building the OCR pipeline TODAY with these 3 files!**

Don't let data collection block development. Start coding now, download more data in parallel.

---

**Last Updated:** September 27, 2026  
**Files Downloaded:** 3 PDFs (4.15 MB)  
**Next Priority:** Download 7 more FORGE PDFs from GDR portal
