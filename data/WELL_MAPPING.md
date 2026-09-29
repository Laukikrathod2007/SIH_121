# FORGE Wells Mapping
## 5 Wells Organized by Folder

**Last Updated:** September 27, 2026  
**Data Source:** Utah FORGE (DOE Geothermal Energy Project)  
**Location:** Milford, Utah, USA (38.5°N, 112.9°W)

---

## 📁 Folder Structure

```
data/raw/
├── well_1/  → FORGE Well 78B-32
├── well_2/  → FORGE Well 16A(78)-32
├── well_3/  → FORGE Well 16B(78)-32
├── well_4/  → FORGE Well 56-32
└── well_5/  → FORGE Well 58-32
```

---

## 🔍 Well Details

### Well 1: FORGE 78B-32

**Folder:** `data/raw/well_1/`

**Files:**
- ✅ **DDR:** `78B-32-DailyDrillingReports-6-27thru7-31.pdf` (35 days)
- ✅ **WCR:** End of Well Report (from extracted zip)
- ✅ **Logs:** Sonic and Temperature logs

**Well Info:**
- **Spud Date:** June 2019
- **Total Depth:** ~3,550m (11,647 ft)
- **Purpose:** Geothermal production/injection well
- **Geology:** Granite basement rock

**Status:** ✅ Complete data (DDR + WCR)

**Use for:** Primary well for OCR extraction demo

---

### Well 2: FORGE 16A(78)-32

**Folder:** `data/raw/well_2/`

**Files:**
- ✅ **DDR:** Multiple daily reports (from extracted zip)
- ✅ **WCR:** `Drilling Summary Well 16A(78)-32.pdf`

**Well Info:**
- **Spud Date:** March 2017
- **Total Depth:** ~2,414m (7,920 ft)
- **Purpose:** First deep well at FORGE site
- **Geology:** Fractured granite, granitoid

**Status:** ✅ Complete data (DDR + WCR)

**Use for:** Offset well comparison, incident analysis

---

### Well 3: FORGE 16B(78)-32

**Folder:** `data/raw/well_3/`

**Files:**
- ✅ **DDR:** Multiple daily reports (from extracted zip)
- ✅ **WCR:** `End of Well Report-16B78-32-May_2024 (1).pdf`

**Well Info:**
- **Completion Date:** May 2024
- **Total Depth:** TBD (check WCR)
- **Purpose:** Production well
- **Geology:** Altered granite, geothermal reservoir

**Status:** ✅ Complete data (DDR + WCR)

**Use for:** Recent well data, modern drilling practices

---

### Well 4: FORGE 56-32

**Folder:** `data/raw/well_4/`

**Files:**
- ✅ **DDR:** Multiple daily reports (from extracted zip)
- ✅ **WCR:** `56-32 EOWR - Final 22 July 2021.pdf`

**Well Info:**
- **Completion Date:** July 2021
- **Total Depth:** TBD (check WCR)
- **Purpose:** Injection well
- **Geology:** Basement granite

**Status:** ✅ Complete data (DDR + WCR)

**Use for:** Injection well vs production well comparison

---

### Well 5: FORGE 58-32

**Folder:** `data/raw/well_5/`

**Files:**
- ✅ **DDR:** `DailyDrillingReports_Well58-32` (from extracted zip)
- ✅ **WCR:** `58-32_EOWR` (from extracted zip)

**Well Info:**
- **Spud Date:** TBD (check WCR)
- **Total Depth:** TBD (check WCR)
- **Purpose:** Production well
- **Geology:** Granite basement

**Status:** ✅ Complete data (DDR + WCR)

**Use for:** Additional offset well data

---

## 🎯 Recommended Usage for Modules

### Module 1 (OCR Extraction):
**Primary:** Well 1 (78B-32) - Start with this well  
**Validation:** Well 2 (16A) - Use to validate extraction accuracy  
**Test Set:** Wells 3, 4, 5 - Hold out for testing

### Module 2 (Map + 3D Visualization):
**Active Well:** Well 1 (78B-32) - Currently "drilling"  
**Offset Wells:** Wells 2, 3, 4, 5 - Show on map, select for 3D comparison

### Module 3-7 (Risk Analytics, Alerts, Dashboard):
**Training Data:** All 5 wells  
**Live Simulation:** Well 1 as active

---

## 🔄 Mapping to OIL India Context

For hackathon demo, remap FORGE wells to OIL India equivalents:

| FORGE Well | OIL India Well Name | Field | Location (Synthetic) |
|------------|---------------------|-------|----------------------|
| **78B-32** | **Nahorkatiya-A1** | Nahorkatiya | 26.52°N, 95.35°E |
| **16A** | **Nahorkatiya-A3** | Nahorkatiya | 26.48°N, 95.28°E |
| **16B** | **Nahorkatiya-A5** | Nahorkatiya | 26.55°N, 95.42°E |
| **56-32** | **Moran-B2** | Moran | 26.85°N, 94.92°E |
| **58-32** | **Digboi-C1** | Digboi | 27.38°N, 95.62°E |

**Formation Mapping:**
- Granite basement → Barail Formation
- Altered granite → Tipam Sandstone
- Volcanic → Kopili Formation

---

## 📊 Data Quality Assessment

| Well | DDR Quality | WCR Quality | Has Survey Data? | Has Incidents? |
|------|-------------|-------------|------------------|----------------|
| **Well 1** | ✅ Good | ✅ Good | ⚠️ Check | ✅ Yes |
| **Well 2** | ✅ Good | ✅ Good | ⚠️ Check | ✅ Yes |
| **Well 3** | ✅ Good | ✅ Good | ⚠️ Check | ⚠️ Check |
| **Well 4** | ✅ Good | ✅ Good | ⚠️ Check | ⚠️ Check |
| **Well 5** | ✅ Good | ✅ Good | ⚠️ Check | ⚠️ Check |

**Next Step:** Extract survey data from WCRs or generate synthetic surveys

---

## 📝 Notes

- All wells are geothermal wells (not oil/gas), but drilling operations are similar
- FORGE wells encounter granite/basement rock (map to sandstone formations for OIL context)
- Daily reports may have variable quality (scanned handwritten notes vs typed)
- End of Well Reports contain final summary data (formation tops, casing, etc.)

---

## 🚀 Next Actions

1. ✅ Data organized into 5 well folders
2. 🔲 Extract key metadata from each WCR (Module 1 OCR)
3. 🔲 Generate synthetic survey data if missing
4. 🔲 Load into PostgreSQL database
5. 🔲 Start Module 2 (Map visualization)

---

**Document Owner:** Harshal (Module 2)  
**Last Review:** September 27, 2026
