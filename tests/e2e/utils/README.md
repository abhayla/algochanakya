# Screenshot Capture Utility

Automated Playwright script to capture screenshots of all AutoPilot screens for documentation.

## Quick Start

```bash
# Make sure backend and frontend are running
cd backend && python run.py  # Terminal 1
cd frontend && npm run dev   # Terminal 2

# Run screenshot capture (from project root)
npm run capture:screenshots
```

## What It Does

The script automatically captures screenshots of:

1. **AutoPilot Dashboard** - Active strategies overview
2. **Strategy Builder (New)** - Create new strategy form
3. **Strategy Builder (Edit)** - Edit existing strategy
4. **Strategy Detail** - Real-time monitoring view
5. **Settings** - Risk limits & preferences
6. **Template Library** - Pre-built strategy templates
7. **Trade Journal** - Execution history
8. **Analytics** - Performance metrics & charts
9. **Reports** - Detailed statistics
10. **Backtests** - Historical simulations
11. **Shared Strategies** - Community strategies list
12. **Modals & Components** - Key UI elements

## Prerequisites

### 1. Services Running
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### 2. Authentication Token
You need a valid authentication token in one of these locations:
- `tests/config/.auth-token` file
- `TEST_AUTH_TOKEN` environment variable

**Get a token:**
```bash
npm run test:oauth:auto  # Follow TOTP prompt
```

### 3. Test Data (Recommended)
For better screenshots, seed some test data:
- AutoPilot strategies (at least 1-2 active)
- Strategy templates
- Trade history
- Analytics data

You can create test data by:
1. Running the app manually and creating strategies
2. Using API seeding scripts (if available)
3. Running E2E tests that create test data

## Configuration

Edit `tests/e2e/utils/screenshot-capture.js` to customize:

```javascript
// Configuration
const SCREENSHOTS_DIR = path.join(__dirname, '../../../docs/assets/screenshots');
const VIEWPORT = { width: 1920, height: 1080 }; // Full HD
const WAIT_FOR_LOAD = 2000; // Wait 2s for dynamic content
```

## Output

Screenshots are saved to:
```
docs/assets/screenshots/
├── autopilot-dashboard.png
├── autopilot-strategy-builder-new.png
├── autopilot-strategy-builder-filled.png
├── autopilot-strategy-builder-edit.png
├── autopilot-strategy-detail.png
├── autopilot-settings.png
├── autopilot-template-library.png
├── autopilot-template-details-modal.png
├── autopilot-trade-journal.png
├── autopilot-analytics.png
├── autopilot-reports.png
├── autopilot-reports-generate-modal.png
├── autopilot-backtests.png
├── autopilot-backtest-config-modal.png
├── autopilot-shared-strategies.png
└── autopilot-kill-switch-modal.png
```

## Troubleshooting

### Error: "No valid auth token available"
**Solution:** Run `npm run test:oauth:auto` to generate a token

### Error: "Failed to load page"
**Solution:** Ensure backend and frontend are running
```bash
# Check backend
curl http://localhost:8000/api/health

# Check frontend
curl http://localhost:5173
```

### Screenshots have empty states
**Solution:** Create some test data:
1. Log into the app manually
2. Create 1-2 AutoPilot strategies
3. Run the script again

### Browser doesn't close automatically
**Solution:** The script runs in non-headless mode for debugging. Close manually or set `headless: true` in the script.

### Screenshots look different from live app
**Possible causes:**
- Different viewport size (script uses 1920x1080)
- Charts/animations not fully loaded (increase `WAIT_FOR_LOAD`)
- Missing test data

## Advanced Usage

### Capture Single Screen

Modify the script to comment out screens you don't need:

```javascript
// Comment out sections you want to skip
// console.log('\n2️⃣  Strategy Builder (New Strategy)');
// ...
```

### Custom Viewport Size

```javascript
const VIEWPORT = { width: 1366, height: 768 }; // Laptop size
const VIEWPORT = { width: 2560, height: 1440 }; // 2K
```

### Headless Mode

For CI/CD pipelines:

```javascript
const browser = await chromium.launch({
  headless: true, // Run without visible browser
  args: ['--start-maximized']
});
```

### Capture with Different Themes

If your app supports themes:

```javascript
// Before capturing
await page.evaluate(() => {
  localStorage.setItem('theme', 'dark');
});
await page.reload();
```

## Integration with CI/CD

```yaml
# .github/workflows/screenshots.yml
name: Update Screenshots
on:
  workflow_dispatch:

jobs:
  screenshots:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm install
      - name: Start backend
        run: cd backend && python run.py &
      - name: Start frontend
        run: cd frontend && npm run dev &
      - name: Wait for services
        run: sleep 10
      - name: Capture screenshots
        run: npm run capture:screenshots
        env:
          TEST_AUTH_TOKEN: ${{ secrets.TEST_AUTH_TOKEN }}
      - name: Commit screenshots
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/assets/screenshots/
          git commit -m "docs: Update AutoPilot screenshots"
          git push
```

## Next Steps After Capture

1. **Review Screenshots**
   ```bash
   # Open screenshots folder
   explorer docs/assets/screenshots  # Windows
   open docs/assets/screenshots      # macOS
   ```

2. **Update Documentation**
   - Add screenshots to `docs/autopilot/README.md`
   - Update `docs/autopilot/ui-ux-design.md`
   - Reference in main `docs/README.md`

3. **Commit Changes**
   ```bash
   git add docs/assets/screenshots/autopilot-*.png
   git add docs/autopilot/*.md
   git commit -m "docs: Add AutoPilot screenshots for all screens"
   git push
   ```

## Script Architecture

```
screenshot-capture.js
├── Imports
│   ├── Playwright browser
│   ├── Auth fixture
│   └── Page Objects (10 classes)
├── Configuration
│   ├── Paths
│   ├── Viewport
│   └── Timeouts
├── Helper Functions
│   ├── waitForFullLoad()
│   └── captureScreenshot()
├── Main Function
│   ├── Launch browser
│   ├── Authenticate
│   ├── Navigate to each screen
│   ├── Capture screenshot
│   └── Close browser
└── Error Handling
```

## Related Files

- **Page Objects:** `tests/e2e/pages/AutoPilotDashboardPage.js`
- **Auth Fixture:** `tests/e2e/fixtures/auth.fixture.js`
- **Playwright Config:** `playwright.config.js`
- **Package Scripts:** `package.json`

## Support

For issues or questions:
1. Check this README first
2. Review script comments in `screenshot-capture.js`
3. Check Playwright documentation: https://playwright.dev
4. Open an issue on GitHub
