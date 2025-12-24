# Cleanup Rules

This reference document defines file organization rules and cleanup guidelines for the AlgoChanakya project.

## Proactive Detection vs. Cleanup

**Proactive Detection (Automatic):**
- Runs after every documentation update
- Scans for orphaned files
- Alerts user with categorized list
- Does NOT move files automatically
- Suggests running `/docs-maintainer cleanup`

**Cleanup Workflow (Manual):**
- Requires explicit user request
- Moves files to proper locations
- Updates references in code
- Runs verification builds

## Root Folder Allowed Files

These files are **allowed** to remain in the project root:

### Configuration Files
- `README.md` - Project overview
- `CLAUDE.md` - Claude Code instructions
- `CHANGELOG.md` - Project-wide changelog
- `package.json` - Node.js project configuration
- `package-lock.json` - Locked dependencies
- `playwright.config.js` - Test configuration
- `.gitignore` - Git ignore rules
- `.eslintrc*` - ESLint configuration
- `.prettierrc*` - Prettier configuration
- `tsconfig.json` / `jsconfig.json` - TypeScript/JavaScript config
- `vite.config.js` / `vue.config.js` - Build tool config

### Standard Files
All other files should be organized into subdirectories.

---

## File Relocation Rules

| File Pattern | Current Location | Target Location | Action |
|--------------|------------------|-----------------|--------|
| **Documentation** |
| `*.md` (docs) | Root | `docs/{appropriate-folder}/` | Move |
| `AUTOPILOT_*.md` | Root | `docs/autopilot/` | Move |
| `*_TEST_*.md` | Root | `docs/testing/` | Move |
| `*_IMPLEMENTATION*.md` | Root | `docs/autopilot/` or `docs/plans/` | Move |
| `DATABASE_*.md` | Root | `docs/guides/` | Move |
| `VPS_*.md` | Root | `docs/guides/` | Move |
| **Test/Debug Scripts** |
| `test_*.py` | Root | `scripts/debug/` | Move |
| `test-*.js` | Root | `scripts/testing/` | Move |
| `*-test.js` | Root | `scripts/testing/` or `tests/e2e/` | Move |
| `debug-*.js` | Root | `scripts/debug/` | Move |
| `cleanup-*.mjs` | Root | `scripts/` | Move |
| `run-*.bat` | Root | `scripts/` | Move |
| `run-*.sh` | Root | `scripts/` | Move |
| **Temporary Files** |
| `*.log` | Anywhere | N/A | Delete + add to .gitignore |
| `test-output.txt` | Root | N/A | Delete + add to .gitignore |
| `*-output.txt` | Root | N/A | Delete + add to .gitignore |
| `*.pid` | Root | N/A | Delete + add to .gitignore |
| `NUL` | Root | N/A | Delete |
| **Screenshots/Images** |
| `error-screenshot.png` | Root | N/A | Delete (temp file) |
| `*.png` (temp) | Root | `docs/assets/screenshots/` | Move or delete |
| Logo files | Root | `frontend/src/assets/logos/` | Move |
| `images/` folder | Root | `docs/assets/screenshots/{context}/` | Move |

---

## docs/features/ Organization

**Rule:** Documentation in `docs/features/` must follow the folder structure pattern.

### Correct Structure
```
docs/features/
├── watchlist/
│   ├── README.md
│   ├── REQUIREMENTS.md
│   └── CHANGELOG.md
├── positions/
│   ├── README.md
│   ├── REQUIREMENTS.md
│   └── CHANGELOG.md
└── ...
```

### Incorrect Structure (Legacy)
```
docs/features/
├── watchlist.md          ← ORPHAN - should be in watchlist/README.md
├── positions.md          ← ORPHAN - should be in positions/README.md
└── ...
```

### Orphan File Handling

When standalone `.md` files are found in `docs/features/`:

1. **Check if folder exists:**
   ```bash
   ls docs/features/watchlist/README.md
   ```

2. **If folder/README exists:**
   - Rename orphan to `.bak` extension
   - `mv watchlist.md watchlist.md.bak`
   - Keep as backup, don't delete

3. **If folder doesn't exist:**
   - Create folder structure
   - Move/rename file to `README.md`
   - Create `REQUIREMENTS.md` and `CHANGELOG.md`

---

## .gitignore Pattern Rules

Add these patterns to `.gitignore` to prevent temporary files from being committed:

```gitignore
# Log files
*.log
logs/

# Process files
*.pid

# Test output
test-output.txt
*-output.txt
autopilot-test-results.txt

# Temporary test/debug scripts (root level only)
/test_*.py
test-*.js
debug-*.js

# Temporary screenshots (root level)
error-screenshot.png
dashboard-screenshot.png

# Temporary implementation docs (root level - docs/ versions are tracked)
/AUTOPILOT_*.md
/IMPLEMENTATION_*.md
/PHASE*_*.md
/TEST_RESULTS*.md
/TESTING_*.md
```

**Note:** Use leading `/` to match root-level files only, allowing the same names in subdirectories.

---

## Script Organization

### scripts/ Folder Structure

```
scripts/
├── debug/              ← Python/JS debugging scripts
│   ├── test_connections.py
│   ├── test_postgres.py
│   └── test_api_debug.py
├── testing/            ← Test utilities and helpers
│   ├── test-strike-finders.js
│   └── manual-test-*.js
├── deployment/         ← Deployment scripts
├── data/              ← Data migration/seeding scripts
└── *.sh, *.bat        ← Top-level utility scripts
```

### When to Keep in Root vs scripts/

| File Type | Root | scripts/ |
|-----------|------|----------|
| One-time setup scripts | ✅ | ❌ |
| Recurring debug scripts | ❌ | ✅ `scripts/debug/` |
| Test runners | ❌ | ✅ `scripts/` |
| Build scripts (npm) | ✅ package.json | ❌ |
| Deployment scripts | ❌ | ✅ `scripts/deployment/` |

---

## Reference Update Checklist

After moving files, **always check and update references:**

### Frontend (Vue/React)
```bash
# Image imports
grep -r "assets/" frontend/src/

# Example: ../assets/logo.png → ../assets/logos/logo.png
```

### Backend (Python)
```bash
# Import statements
grep -r "from.*import" backend/app/

# Relative imports may break after moving files
```

### Documentation
```bash
# Markdown links
grep -r "\[.*\](.*\.md)" docs/

# Example: [Guide](../GUIDE.md) → [Guide](docs/guides/guide.md)
```

### Scripts
```bash
# Path references in package.json
cat package.json | grep "scripts"

# Example: "./run-test.sh" → "./scripts/run-test.sh"
```

---

## Verification Steps

After cleanup, verify nothing broke:

### 1. Build Verification
```bash
# Frontend
cd frontend && npm run build

# Backend syntax
cd backend && python -m py_compile run.py
```

### 2. Test Run (Optional)
```bash
# Run test suite if applicable
npm test
```

### 3. Manual Check
- Open the app in browser
- Verify images load correctly
- Check that documentation links work
- Ensure scripts can still be executed

---

## Summary: Quick Decision Tree

```
File found in root?
├─ Is it in "Allowed Files" list? → YES → Leave it
└─ NO → Check file type:
    ├─ *.md (doc) → Move to docs/{folder}/
    ├─ test_*.py → Move to scripts/debug/
    ├─ test-*.js → Move to scripts/testing/
    ├─ *.log → Delete + .gitignore
    └─ *.png (temp) → Delete or move to docs/assets/

File found in docs/features/?
├─ Is it a folder with README.md? → YES → Correct structure
└─ Is it standalone *.md? → YES → Orphan:
    ├─ Folder exists? → Rename to .bak
    └─ Folder missing? → Create folder, move file
```
