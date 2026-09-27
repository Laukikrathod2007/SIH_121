# Git Workflow Guide
## eRTMAC-NWIS Project

**Repository:** https://github.com/Laukikrathod2007/SIH_121.git  
**Your Branch:** `harshal`  
**Last Updated:** September 27, 2026

---

## ✅ Initial Setup (Already Done)

Your project has been successfully pushed to the `harshal` branch! 

**What was pushed:**
- ✅ All documentation files (4 docs + 6 data guides)
- ✅ Data folder structure (with .gitkeep files)
- ✅ .gitignore (configured to exclude large data files)
- ✅ Problem statement

**Branch setup:**
```
Repository: SIH_121
├── main (protected - don't push here)
└── harshal (your working branch) ✅
```

---

## 📊 What's in Your Branch

### Files Pushed (19 files, 64.66 KB)

```
SIH_121/harshal/
├── .gitignore                           # Git ignore rules
├── problem_statement.txt                # Original problem statement
├── docs/
│   ├── 01-problem-requirements.md       # Functional & non-functional requirements
│   ├── 02-problem-analysis.md           # Problem decomposition
│   ├── 03-implementation-plan.md        # 10-module architecture
│   └── 04-data-collection-plan.md       # Data sources strategy
├── data/
│   ├── START_HERE.md                    # ⭐ Quick data collection guide
│   ├── ALTERNATIVE_DATA_STRATEGY.md     # Pragmatic approach
│   ├── DATA_DOWNLOAD_GUIDE.md           # Detailed download instructions
│   ├── DOWNLOADED_FILES_STATUS.md       # Progress tracking
│   ├── QUICK_START.md                   # 3-step data collection
│   ├── README.md                        # Data directory overview
│   ├── raw/                             # Raw data (PDFs, CSVs) - gitignored
│   ├── processed/                       # OCR output - gitignored
│   └── synthetic/                       # Generated data - gitignored
└── GIT_WORKFLOW.md                      # This file
```

### What's NOT Pushed (Intentionally)

The `.gitignore` excludes large data files:
- ❌ PDFs in `data/raw/` (too large for Git)
- ❌ CSVs in `data/processed/` (generated files)
- ❌ JSON in `data/synthetic/` (generated files)
- ✅ Only structure and documentation are tracked

---

## 🔄 Daily Git Workflow

### Every Time You Make Changes

```powershell
# Navigate to project
cd C:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS

# Check what changed
git status

# Add your changes
git add .

# Commit with descriptive message
git commit -m "Your descriptive message here"

# Push to harshal branch
git push origin harshal
```

### Example Commit Messages

**Good messages:**
```bash
git commit -m "Add OCR extraction module with PaddleOCR integration"
git commit -m "Update data collection guide with FORGE alternative sources"
git commit -m "Create synthetic data generator for OIL India wells"
git commit -m "Fix: Correct database schema for formation_tops table"
```

**Bad messages:**
```bash
git commit -m "changes"
git commit -m "update"
git commit -m "fix bug"
```

---

## 🌿 Working with Branches

### Check Current Branch
```powershell
git branch
# Output: * harshal (you're here)
#         main
```

### Switch Between Branches
```powershell
# Switch to your branch
git checkout harshal

# Switch to main (view only, don't commit!)
git checkout main

# Always switch back to harshal before working
git checkout harshal
```

### Pull Latest Changes from Remote
```powershell
# Before starting work each day
git checkout harshal
git pull origin harshal
```

---

## 👥 Collaborating with Team

### When Teammate Updates the Repo

1. **Fetch all changes:**
   ```powershell
   git fetch origin
   ```

2. **Pull their changes to your branch:**
   ```powershell
   git checkout harshal
   git pull origin harshal
   ```

3. **If there are conflicts:**
   ```powershell
   # Git will mark conflicts in files
   # Open conflicted files, resolve manually
   # Then:
   git add .
   git commit -m "Resolve merge conflicts"
   git push origin harshal
   ```

### When You Want to See Other Branches

```powershell
# List all remote branches
git branch -r

# Example: Check teammate's branch
git checkout -b teammate-branch origin/teammate-branch
# View their code, then switch back
git checkout harshal
```

---

## 🚀 Pushing Code Modules

### Module Development Workflow

**When you finish Module 2 (OCR Pipeline):**

```powershell
# Create module folder
New-Item -ItemType Directory -Path "backend/app/services/ingestion" -Force

# Add your OCR code
# ... work on your module ...

# Stage and commit
git add backend/app/services/ingestion/
git commit -m "Module 2: OCR pipeline with PaddleOCR and spaCy NLP extraction"

# Push to your branch
git push origin harshal
```

**Recommended commit frequency:**
- ✅ Commit after each working feature
- ✅ Commit at end of each work session
- ✅ Commit before pulling others' changes
- ✅ Commit before major refactoring

---

## 📦 What to Commit vs. What to Ignore

### ✅ DO Commit
- Source code (Python, JavaScript, TypeScript)
- Configuration files (requirements.txt, package.json)
- Documentation (README, guides, specs)
- Database schema files (.sql)
- Small sample data (< 1 MB)
- Scripts and notebooks

### ❌ DON'T Commit
- Large data files (PDFs, CSVs > 10 MB)
- Generated files (processed JSON, model outputs)
- Virtual environments (venv/, node_modules/)
- IDE config (.vscode/, .idea/)
- Secrets (.env with passwords/API keys)
- OS files (.DS_Store, Thumbs.db)

*All of these are already in .gitignore*

---

## 🆘 Common Git Issues & Solutions

### Issue 1: "I pushed to main by accident!"

```powershell
# DON'T PANIC! You can undo it
git checkout harshal
git push origin harshal --force

# Then contact repo admin to remove main commits
```

### Issue 2: "I have uncommitted changes and need to pull"

```powershell
# Option A: Commit your changes first
git add .
git commit -m "WIP: Save current work"
git pull origin harshal

# Option B: Stash changes temporarily
git stash
git pull origin harshal
git stash pop
```

### Issue 3: "Git says 'divergent branches'"

```powershell
# Configure pull strategy
git config pull.rebase false

# Then pull again
git pull origin harshal
```

### Issue 4: "I want to undo my last commit"

```powershell
# Undo commit but keep changes
git reset --soft HEAD~1

# Undo commit and discard changes (⚠️ careful!)
git reset --hard HEAD~1
```

---

## 📈 Viewing Your Work

### Check Commit History
```powershell
# See all commits
git log

# See last 5 commits (compact)
git log --oneline -5

# See what changed in last commit
git show HEAD
```

### See What You Changed
```powershell
# See unstaged changes
git diff

# See staged changes
git diff --staged

# See changes in specific file
git diff filename.py
```

### Check Repository Status
```powershell
# See modified files
git status

# See branch info
git branch -vv

# See remote connections
git remote -v
```

---

## 🎯 Pre-Push Checklist

Before every `git push`, verify:

- [ ] You're on the `harshal` branch (`git branch`)
- [ ] All files compile/run without errors
- [ ] No sensitive data (passwords, API keys) in commits
- [ ] Commit message is descriptive
- [ ] Large data files are gitignored
- [ ] You've pulled latest changes first (`git pull origin harshal`)

---

## 🔒 Security Best Practices

### Never Commit These:
```
.env files with real credentials
API keys
Database passwords
AWS/Azure access keys
Personal access tokens
```

### If You Accidentally Commit Secrets:
1. **Immediately rotate the secret** (change password/key)
2. Remove from Git history:
   ```powershell
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch .env" \
   --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push (⚠️ coordinate with team):
   ```powershell
   git push origin harshal --force
   ```

---

## 📞 Getting Help

### Git Documentation
- Official Git docs: https://git-scm.com/doc
- GitHub guides: https://docs.github.com
- Interactive Git tutorial: https://learngitbranching.js.org

### Team Contacts
- **Repo Admin:** Laukikrathod2007
- **Your Branch:** harshal
- **Issues:** Report via GitHub Issues tab

### Quick Commands Reference
```powershell
# Daily workflow
git status              # Check changes
git add .              # Stage all changes
git commit -m "msg"    # Commit changes
git push origin harshal # Push to your branch
git pull origin harshal # Pull updates

# Branch management
git branch             # List branches
git checkout harshal   # Switch to harshal
git branch -vv         # See branch tracking

# History
git log --oneline -10  # Last 10 commits
git diff               # See changes
git show HEAD          # Last commit details
```

---

## 🎓 Learning Resources

### Beginner Git Tutorials
1. GitHub's Git Handbook: https://guides.github.com/introduction/git-handbook/
2. Git Basics (15 min): https://git-scm.com/book/en/v2/Getting-Started-Git-Basics
3. Visualizing Git: http://git-school.github.io/visualizing-git/

### VS Code Git Integration
- Built-in Source Control panel (Ctrl+Shift+G)
- Visual commit history
- Inline diff viewing
- Branch switcher in bottom-left

---

## ✅ Summary

**Your Setup:**
- ✅ Repository: `SIH_121`
- ✅ Your Branch: `harshal` 
- ✅ Initial commit pushed (19 files, 64.66 KB)
- ✅ .gitignore configured (excludes large data files)
- ✅ Ready for development!

**Next Steps:**
1. Continue working on your modules
2. Commit frequently with good messages
3. Push to `harshal` branch regularly
4. Never push to `main` directly

**Important:** The `main` branch should only receive code via Pull Requests after team review. Always work on `harshal` branch!

---

**Last Updated:** September 27, 2026  
**Branch:** harshal  
**Commit:** 15575c7 - "Initial commit: Project structure with docs and data collection strategy"
