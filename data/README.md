# Data Directory
## eRTMAC-NWIS Data Collection

**Purpose:** Central repository for all drilling data used in OCR/NLP pipeline and system modules

---

## 📁 Directory Structure

```
data/
├── raw/                          # Original unmodified source data
│   ├── volve/                    # Equinor Volve Field dataset
│   │   ├── wcr/                  # Well Completion Reports (PDF)
│   │   ├── ddr/                  # Daily Drilling Reports (PDF)
│   │   ├── witsml/               # Real-time WITSML data (CSV/XML)
│   │   ├── mud_reports/          # Mud logging reports (PDF)
│   │   └── las_logs/             # Well logs (LAS format)
│   ├── forge/                    # Utah FORGE geothermal drilling data
│   │   ├── 78b32_ddr/            # ✅ Well 78B-32 DDRs
│   │   ├── 56-32_logs/           # Well 56-32 logs
│   │   └── incident_reports/     # NPT event records
│   └── sodir/                    # Norwegian SODIR wellbore data
│       ├── wellbore_master.csv   # Wellbore metadata
│       ├── casing_programs.csv   # Casing data
│       └── incidents.csv         # Historical incidents
│
├── processed/                    # Processed/transformed data
│   ├── extracted_json/           # OCR output in JSON format
│   ├── validated/                # Human-verified extraction samples
│   └── training_labels/          # Labels for ML model training
│
├── synthetic/                    # Generated synthetic data
│   └── oil_india_mock/           # Synthetic OIL India wells
│
├── DATA_DOWNLOAD_GUIDE.md        # 📖 Step-by-step download instructions
├── DOWNLOADED_FILES_STATUS.md    # 📊 Progress tracking
└── README.md                     # 📄 This file
```

---

## 🎯 Current Status

### ✅ Downloaded (Ready to Use)
- **Utah FORGE 78B-32 DDR** (0.83 MB) - 35 days of drilling reports

### ⏳ Pending Download (Manual)
- Equinor Volve dataset (10-200 PDFs + CSVs)
- Utah FORGE additional logs (2 PDFs)
- Norwegian SODIR wellbore CSV
- Volve WITSML ground truth CSVs

**See `DOWNLOADED_FILES_STATUS.md` for detailed progress tracking**

---

## 📖 Quick Reference

### For Data Downloaders

**Start Here:**
1. Read `DATA_DOWNLOAD_GUIDE.md` for detailed instructions
2. Follow Phase 1 (Quick Start) downloads
3. Update `DOWNLOADED_FILES_STATUS.md` after each download

**Priority Downloads:**
1. Utah FORGE 78B-32 additional PDFs (2 files, ~10 MB) - ⏳ Pending
2. Volve dataset from Kaggle (2-5 GB) - ⏳ Pending
3. Volve WITSML CSVs (3 files, ~120 MB) - ⏳ Pending

### For OCR Pipeline Developers

**Available Now:**
- `data/raw/forge/78b32_ddr/78B-32-DailyDrillingReports-6-27thru7-31.pdf`
  - 35 pages of DDRs (June 27 - July 31)
  - Real drilling parameters: depth, mud weight, ROP
  - Real incidents: lost circulation events
  - Mixed quality: handwritten notes, typed reports

**Coming Soon:**
- Volve DDRs (50-200 PDFs) for large-scale OCR testing
- Volve WITSML CSVs for validation ground truth
- Volve WCRs (10-15 PDFs) for formation tops extraction

### For Database/Module Developers

**Use This Data:**
- Once Volve WITSML CSVs downloaded → Populate Module 1 database
- Once OCR extracts JSON → Feed to Module 4 (Offset Relevance)
- Incident records → Train Module 7 (Risk Prediction)

---

## 🔄 Data Flow Through Modules

```
Raw PDFs (data/raw/)
      ↓
Module 2: OCR/NLP Pipeline
      ↓
Extracted JSON (data/processed/extracted_json/)
      ↓
Module 1: Database Population
      ↓
Module 4: Offset Relevance ← Uses well metadata
Module 5: Depth Correlation ← Uses formation tops
Module 6: Hybrid Search ← Uses document chunks
Module 7: Risk Prediction ← Uses incident records
Module 8: Alert Generation ← Uses predictions
```

---

## 📊 Data Categories & Purpose

| Category | Format | Volume | Usage |
|----------|--------|--------|-------|
| **Well Completion Reports** | PDF | 10-15 files | Formation tops, casing programs, well metadata |
| **Daily Drilling Reports** | PDF | 50-200 files | Drilling parameters, incidents, NPT |
| **WITSML Real-time Data** | CSV/XML | 3-10 files | Ground truth for OCR validation |
| **Well Logs** | LAS | 50-100 files | Depth correlation, lithology |
| **Wellbore Metadata** | CSV | 1 file | Validation baseline, structured data |
| **Synthetic OIL Data** | JSON | 20 wells | Demo with OIL India context |

---

## ✅ Data Quality Standards

### Raw Data
- **Immutable:** Never modify files in `data/raw/`
- **Organized:** Follow folder structure strictly
- **Named Consistently:** Use original filenames from source
- **Documented:** Log source, download date, file size

### Processed Data
- **JSON Schema:** Follow target schema in `04-data-collection-plan.md`
- **Validated:** At least 50 samples human-verified
- **Timestamped:** Include processing date in metadata
- **Confidence Scored:** Flag low-quality OCR extractions

### Synthetic Data
- **Realistic:** Use Volve parameters as templates
- **Labeled:** Clear distinction from real data
- **Documented:** Mapping between Volve → OIL India nomenclature
- **Consistent:** Follow same JSON schema as real data

---

## 🚀 Quick Commands

### Verify Downloads
```powershell
# List all downloaded files
Get-ChildItem -Path "data/raw" -Recurse -File | 
    Select-Object FullName, @{N="Size (MB)";E={[math]::Round($_.Length/1MB,2)}}

# Count files by source
Write-Host "Utah FORGE: " -NoNewline
(Get-ChildItem -Path "data/raw/forge" -Recurse -File).Count

Write-Host "Volve: " -NoNewline
(Get-ChildItem -Path "data/raw/volve" -Recurse -File).Count

Write-Host "SODIR: " -NoNewline
(Get-ChildItem -Path "data/raw/sodir" -Recurse -File).Count
```

### Check Data Coverage
```powershell
# Check each category
$categories = @("wcr", "ddr", "witsml", "mud_reports", "las_logs")
foreach ($cat in $categories) {
    $count = (Get-ChildItem -Path "data/raw/volve/$cat" -File -ErrorAction SilentlyContinue).Count
    Write-Host "$cat : $count files"
}
```

### Open Sample PDF
```powershell
# Open first available PDF for inspection
Get-ChildItem -Path "data/raw" -Recurse -Filter "*.pdf" | 
    Select-Object -First 1 | 
    Invoke-Item
```

---

## 📝 Data Provenance

### Equinor Volve Field
- **Source:** Equinor ASA (Norway)
- **Licence:** Equinor Open Data Licence (CC BY-style with restrictions)
- **Region:** North Sea, Norwegian Continental Shelf (15/9 block)
- **Period:** 2008-2016 operations
- **Purpose:** Research, education, technology development
- **Attribution Required:** Yes - cite Equinor as data owner

### Utah FORGE
- **Source:** U.S. Department of Energy (DOE)
- **Licence:** Public domain (U.S. Government work)
- **Region:** Milford, Utah, USA (geothermal)
- **Period:** 2020-2021 drilling campaigns
- **Purpose:** Enhanced geothermal research
- **Attribution Required:** Recommended but not legally required

### Norwegian SODIR
- **Source:** Norwegian Offshore Directorate
- **Licence:** Norwegian Licence for Open Government Data (NLOD)
- **Region:** Norwegian Continental Shelf (all areas)
- **Period:** 1960s-present (historical + current)
- **Purpose:** Public information, transparency
- **Attribution Required:** Yes - cite SODIR/NPD

---

## 🔒 Data Usage Guidelines

### For Hackathon Demo
✅ **Allowed:**
- Use all datasets for OCR development
- Train ML models on this data
- Generate synthetic OIL India wells using Volve templates
- Display in hackathon presentation

❌ **Not Allowed:**
- Resell or commercialize the datasets
- Claim datasets as OIL India proprietary data
- Remove attribution to original sources
- Share datasets beyond team members

### For Production Deployment
- **Phase 1 (Demo):** Use Volve + synthetic OIL data
- **Phase 2 (OIL Pilot):** Replace with actual OIL India data
- **Architecture:** OCR pipeline designed to accept OIL data without changes
- **Transparency:** Clearly state in presentation that demo uses public analogous data

---

## 🆘 Troubleshooting

### Problem: Not Enough Disk Space
**Solution:** Start with Phase 1 only (~500 MB), download full dataset later

### Problem: Download Failed or Corrupted
**Solution:** 
1. Check file size matches expected
2. Re-download using `DATA_DOWNLOAD_GUIDE.md` instructions
3. Try alternative source (Kaggle vs. official portal)

### Problem: Can't Find Specific File
**Solution:**
1. Check `DOWNLOADED_FILES_STATUS.md` for expected location
2. Verify folder structure matches this README
3. Re-run download commands from guide

### Problem: PDF Won't Open
**Solution:**
1. Check file size > 0 KB
2. Try different PDF reader (Adobe, Foxit, SumatraPDF)
3. Re-download the file

---

## 📞 Data Team Contacts

**Data Collection Lead:** [Team Member Name]  
**OCR Pipeline Lead:** [Team Member Name]  
**Database Lead:** [Team Member Name]

**Issue Tracking:** Use project Discord/Slack channel for data-related questions

---

## 📅 Update Log

| Date | Action | Files Added | By |
|------|--------|-------------|-----|
| 2026-09-27 | Initial setup | Utah FORGE 78B-32 DDR (1 file, 0.83 MB) | AI Assistant |
| [TBD] | Volve download | [Pending] | [Team Member] |
| [TBD] | SODIR export | [Pending] | [Team Member] |

---

## 🎓 Learning Resources

### Understanding Drilling Data
- **Daily Drilling Reports (DDR):** Daily summary of operations, parameters, incidents
- **Well Completion Reports (WCR):** Final report with formation tops, casing, cement
- **WITSML:** Wellsite Information Transfer Standard Markup Language (real-time data)
- **LAS:** Log ASCII Standard (well log format)

### Useful References
- WITSML Standards: https://www.energistics.org/witsml-standards/
- LAS Format Spec: https://www.cwls.org/products/#products-las
- Drilling Parameters Guide: Check `docs/` folder for glossary

---

**For detailed download instructions, see:** `DATA_DOWNLOAD_GUIDE.md`  
**For progress tracking, see:** `DOWNLOADED_FILES_STATUS.md`  
**For data source strategy, see:** `../docs/04-data-collection-plan.md`
