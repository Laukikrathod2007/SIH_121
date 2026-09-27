# Alternative Data Strategy (REALISTIC)
## For Hackathon - What You Actually Need

**Created:** September 27, 2026  
**Purpose:** Pragmatic approach when full Volve dataset is inaccessible

---

## 🎯 Reality Check

### The Problem
1. ❌ Kaggle "Volve" dataset is only 2 MB (just metadata, no PDFs)
2. ❌ UiS CSV link (http://www.ux.uis.no/~atunkiel/) is currently blocked (403 Forbidden)
3. ⚠️ Full Volve dataset is 23 GB via Azure Storage (takes hours to download)

### The Solution
**You DON'T need 40,000 files for a hackathon!** Use what you have + smart alternatives.

---

## ✅ What You ALREADY Have

### 1. Utah FORGE DDR (Downloaded) ✅
- Location: `data/raw/forge/78b32_ddr/78B-32-DailyDrillingReports-6-27thru7-31.pdf`
- Size: 0.83 MB
- Contains: 35 days of real drilling operations
- Quality: Perfect for OCR testing (mixed handwritten + typed)

**This is enough to:**
- Build and test OCR pipeline
- Extract drilling parameters
- Identify incidents
- Validate extraction logic

---

## 🚀 Pragmatic 3-Step Strategy

### Step 1: Use Utah FORGE as Primary OCR Source ✅

**What you have:**
- 1 DDR PDF with 35 days of operations
- Real drilling parameters: depth, mud weight, ROP
- Real incidents: lost circulation events

**Download 2 more files:**
```powershell
cd C:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS

# Sonic log
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_R1A_Sonic.Pdf" -OutFile "data/raw/forge/78b32_ddr/UOU_FORGE-78B-32_Sonic.Pdf"

# Temperature log
Invoke-WebRequest -Uri "https://gdr.openei.org/files/1330/UOU_FORGE-78B-32_Temperature_Log_22Jul21_.Pdf" -OutFile "data/raw/forge/78b32_ddr/UOU_FORGE-78B-32_Temperature.Pdf"
```

**Result:** 3 PDFs for OCR development ✅

---

### Step 2: Download More Utah FORGE Wells

Search for additional FORGE wells:

**Well 16A(78)-32 (More Recent)**
- Link: https://catalog.data.gov/dataset/utah-forge-well-16a78-32-drilling-data
- Contains: Survey data, daily reports (2020-2021), summaries

**Well 56-32**
- Link: https://gdr.openei.org (Search "FORGE 56-32")
- Contains: Pason data, mud logs, daily reports

**Download Strategy:**
1. Go to https://gdr.openei.org
2. Search: "FORGE drilling reports"
3. Download any PDFs you find (aim for 5-10 total)
4. Save to: `data/raw/forge/`

**Target:** 10 PDFs total from FORGE (free, public domain, no restrictions)

---

### Step 3: Create Synthetic Volve-Style Data

**Why:** You can't easily get real Volve PDFs, but you can simulate them!

**Approach:**

1. **Use your FORGE data as templates**
   - Extract real drilling parameters from FORGE PDFs
   - Real incident patterns
   - Authentic operational narratives

2. **Remap to "OIL India" context**
   - Well names: "Nahorkatiya-A1", "Moran-B2", "Digboi-C3"
   - Formations: Barail Formation, Girujan Clay
   - Locations: Upper Assam coordinates

3. **Generate 20 synthetic wells**
   - Use script in Module 3 (Synthetic Data Generator)
   - Output format: JSON (structured data)
   - Store: `data/synthetic/oil_india_mock/`

**Script Outline:**
```python
# data_generator.py
import random
from datetime import datetime, timedelta

# Template from FORGE extraction
forge_template = {
    "depth": [3400, 3500, 3600],  # Real values from FORGE
    "rop": [12.5, 15.3, 10.2],
    "mud_weight": [9.2, 9.4, 9.3],
    "incidents": ["Lost circulation @ 3420 ft (15 bbl)"]
}

# Generate OIL India well
oil_well = {
    "well_name": "Nahorkatiya-A1",
    "field": "Nahorkatiya",
    "location": {"lat": 26.75, "lng": 95.35},
    "spud_date": "2024-01-15",
    "drilling_params": forge_template,  # Use real engineering values
    "formations": [
        {"name": "Barail Formation", "depth_md": 3456, "hazard": True}
    ]
}
```

---

## 📊 Alternative Data Sources

### Option A: GitHub Volve Processing Repos

Several researchers have processed Volve data and shared subsets:

1. **f0nzie/volve-drilling**
   - Link: https://github.com/f0nzie/volve-drilling
   - Contains: R notebooks with Volve WITSML processing
   - Has: Sample data extracts

2. **sgk2004/Volve-Dataset**
   - Link: https://github.com/sgk2004/Volve-Dataset
   - Contains: ML-ready processed Volve data
   - Has: Downhole pressure predictions

3. **andymcdgeo/spwla_volve**
   - Link: https://github.com/andymcdgeo/spwla_volve
   - Contains: Volve LAS well logs
   - Has: Sample extracted data

**Strategy:** Clone repos, extract any CSV/JSON data, use as baseline

---

### Option B: Manual Volve Download (If You Have Time)

**Only if you need actual Volve PDFs and have 2+ hours:**

1. **Download Azure Storage Explorer**
   - Link: https://azure.microsoft.com/products/storage/storage-explorer/
   - Install on Windows

2. **Connect to Volve Storage**
   - Open Azure Storage Explorer
   - Click "Connect" → "Storage account or service"
   - Select "Blob container"
   - Display name: "Volve Dataset"
   - Connection string: `DefaultEndpointsProtocol=https;AccountName=datavillagesa;EndpointSuffix=core.windows.net`
   - Anonymous access (no key needed)

3. **Navigate and Download Selectively**
   - Browse to `/Daily Drilling Reports/` or `/Well Completion Reports/`
   - Download 10-20 files ONLY (not entire folder!)
   - Right-click → Download

**Warning:** Each DDR can be 5-50 MB. Be selective!

---

### Option C: Norwegian SODIR (Structured Baseline)

**If you need structured data (no OCR needed):**

1. Go to: https://factpages.sodir.no/en/wellbore
2. Search: "15/9-F" (Volve field wells)
3. Select 5-10 wells
4. Export as CSV
5. Save to: `data/raw/sodir/volve_wells.csv`

**What you get:**
- Well metadata (names, locations, depths)
- Casing programs
- Formation tops
- Incident records

**Use:** Validation baseline (compare OCR vs. structured data)

---

## 🎯 Recommended Final Dataset Mix

| Source | Files | Purpose | Status |
|--------|-------|---------|--------|
| **Utah FORGE DDRs** | 10 PDFs | OCR development, incident extraction | ✅ 1 downloaded, download 9 more |
| **SODIR Volve Wells** | 1 CSV | Structured validation baseline | ⏳ Manual export |
| **Synthetic OIL Data** | 20 JSON files | Demo with OIL India context | ⏳ Generate with script |
| **Volve Sample (optional)** | 5-10 PDFs | Extra validation if time allows | ⏳ Azure download |

**Total:** ~15-20 PDFs + 1 CSV + 20 JSON = **Full hackathon demo dataset**

---

## ✅ Success Metrics (Revised)

### Minimum Viable Dataset
- [x] 1 Utah FORGE DDR ✅
- [ ] 9 more Utah FORGE PDFs ⏳
- [ ] 1 SODIR CSV ⏳
- [ ] 20 synthetic OIL JSON files ⏳

**With this, you can:**
- ✅ Build complete OCR pipeline
- ✅ Validate extraction accuracy
- ✅ Populate database (Module 1)
- ✅ Train risk models (Module 7)
- ✅ Demo full system with "OIL India" data

### Optional: Enhanced Dataset
- [ ] 5-10 Volve DDRs from Azure
- [ ] GitHub Volve processed data
- [ ] More FORGE wells

**Only if you have extra time!**

---

## 🚀 Immediate Action Plan

### Today (30 minutes):
1. ✅ Verify you have Utah FORGE DDR
2. ⏳ Download 2 more FORGE PDFs (run PowerShell commands above)
3. ⏳ Search GDR for more FORGE wells (aim for 5-10 PDFs)

### This Week (2 hours):
1. ⏳ Export SODIR Volve CSV (10 wells)
2. ⏳ Start synthetic data generator script
3. ⏳ Generate 20 OIL India wells

### Optional (If Time Permits):
1. Install Azure Storage Explorer
2. Download 5-10 Volve DDRs
3. Clone GitHub Volve repos for processed data

---

## 📝 Presentation Strategy

**In your hackathon demo, be transparent:**

> "We built our OCR pipeline on publicly available Utah FORGE drilling data (DOE-funded, fully open). For demonstration, we generated 20 synthetic wells styled on OIL India operations (Nahorkatiya, Moran fields) using engineering parameters from real drilling operations. Our pipeline is designed to accept OIL India's actual DDR/WCR corpus post-deployment without architectural changes."

**Why this works:**
- ✅ Honest about data sources
- ✅ Shows understanding of data governance
- ✅ Demonstrates technical capability
- ✅ More credible than claiming "fake OIL data"

---

## 🆘 If Still Stuck

### Can't Download Enough PDFs?
**Solution:** Focus quality over quantity
- 3-5 FORGE PDFs is enough for OCR development
- Use synthetic data for bulk testing
- Demonstrate extraction on 1 PDF live in demo

### No Time for Azure Download?
**Solution:** Skip Volve PDFs entirely
- FORGE data is sufficient
- Cite Volve in presentation ("would use in production")
- Generate synthetic Volve-style data

### Need CSV Data for Validation?
**Solution:** Create your own ground truth
- Manually transcribe 1-2 FORGE DDRs to JSON
- Use this as "gold standard" for accuracy calc
- Calculate OCR vs. manual extraction accuracy

---

## 🎓 Pro Tips

1. **Don't chase Volve** - FORGE is equally valid for proving OCR capability
2. **Synthetic is OK** - Judges care about pipeline architecture, not data volume
3. **Be transparent** - Honesty about data sources builds credibility
4. **Demo live extraction** - Process 1 PDF live in presentation (most impressive)

---

## 📞 Data Collection Support

**If links are broken:**
1. Search "Utah FORGE drilling data" on data.gov
2. Search "FORGE GDR" on https://gdr.openei.org
3. Email DOE GDR support (listed on GDR portal)

**For SODIR access issues:**
- Try different browser
- Use incognito mode
- Export small batches (5 wells at a time)

---

**Bottom Line:** You have enough data to build a complete, functional system. Focus on building the pipeline, not collecting thousands of files!
