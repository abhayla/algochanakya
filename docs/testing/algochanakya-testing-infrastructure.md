# AlgoChanakya Testing Infrastructure

> Industry-standard testing setup with Allure Reports, GitHub Actions CI/CD, BDD documentation, and coverage tracking.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Allure Reporting Setup](#2-allure-reporting-setup)
3. [GitHub Actions CI/CD](#3-github-actions-cicd)
4. [BDD Test Specifications](#4-bdd-test-specifications)
5. [Test Coverage Matrix](#5-test-coverage-matrix)
6. [Test Documentation](#6-test-documentation)
7. [Claude Code Implementation Prompt](#7-claude-code-implementation-prompt)

---

## 1. Project Structure

```
algochanakya/
├── .github/
│   └── workflows/
│       ├── backend-tests.yml
│       ├── frontend-tests.yml
│       └── e2e-tests.yml
├── backend/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_models.py
│   │   │   └── test_utils.py
│   │   ├── api/
│   │   │   ├── test_auth.py
│   │   │   ├── test_watchlist.py
│   │   │   ├── test_option_chain.py
│   │   │   ├── test_strategy_builder.py
│   │   │   ├── test_positions.py
│   │   │   └── test_strategy_wizard.py
│   │   └── integration/
│   │       └── test_full_flows.py
│   ├── pytest.ini
│   └── pyproject.toml
├── frontend/
│   ├── tests/
│   │   ├── e2e/
│   │   │   ├── specs/
│   │   │   │   ├── auth/
│   │   │   │   │   ├── auth.happy.spec.js
│   │   │   │   │   ├── auth.edge.spec.js
│   │   │   │   │   └── auth.visual.spec.js
│   │   │   │   ├── watchlist/
│   │   │   │   ├── option-chain/
│   │   │   │   ├── strategy-builder/
│   │   │   │   ├── positions/
│   │   │   │   └── strategy-library/
│   │   │   ├── fixtures/
│   │   │   │   ├── auth.fixtures.js
│   │   │   │   ├── strategies.fixtures.js
│   │   │   │   └── mock-data.js
│   │   │   └── support/
│   │   │       ├── commands.js
│   │   │       └── helpers.js
│   │   └── unit/
│   │       └── stores/
│   ├── playwright.config.js
│   └── package.json
├── docs/
│   └── testing/
│       ├── README.md
│       ├── test-plan.md
│       ├── test-cases.md
│       ├── coverage-matrix.md
│       └── bdd-specs/
│           ├── auth.feature
│           ├── watchlist.feature
│           ├── option-chain.feature
│           ├── strategy-builder.feature
│           ├── positions.feature
│           └── strategy-library.feature
├── allure-results/
├── allure-report/
└── test-results/
```

---

## 2. Allure Reporting Setup

### 2.1 Backend (Python/Pytest)

**Install Dependencies:**

```bash
cd backend
pip install allure-pytest pytest-html pytest-cov
```

**pytest.ini:**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    -v
    --alluredir=allure-results
    --cov=app
    --cov-report=html:coverage-report
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    api: API tests
    integration: Integration tests
    slow: Slow running tests
```

**conftest.py additions:**

```python
import pytest
import allure
from typing import Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Allure Environment Info
def pytest_configure(config):
    allure.environment(
        Project="AlgoChanakya",
        Backend="FastAPI",
        Database="PostgreSQL",
        Python="3.11"
    )

# Allure Step Decorator Helper
def allure_step(title: str):
    """Decorator to add Allure step to test functions"""
    def decorator(func):
        @allure.step(title)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Screenshot on Failure (for API responses)
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        # Attach any relevant data on failure
        if hasattr(item, 'funcargs'):
            if 'response' in item.funcargs:
                allure.attach(
                    str(item.funcargs['response'].json()),
                    name="API Response",
                    attachment_type=allure.attachment_type.JSON
                )

# Fixtures with Allure Labels
@pytest.fixture
@allure.title("Database Session")
async def db_session() -> Generator[AsyncSession, None, None]:
    """Async database session for tests"""
    # ... existing implementation
    pass

@pytest.fixture
@allure.title("Authenticated Client")
async def auth_client(db_session) -> AsyncClient:
    """HTTP client with authentication"""
    # ... existing implementation
    pass

@pytest.fixture
@allure.title("Sample Strategy Templates")
async def seeded_templates(db_session):
    """Seed strategy templates for testing"""
    # ... implementation
    pass
```

**Example Test with Allure Annotations:**

```python
import pytest
import allure
from httpx import AsyncClient

@allure.epic("Strategy Library")
@allure.feature("Strategy Wizard")
class TestStrategyWizard:
    
    @allure.story("Get Recommendations")
    @allure.title("Wizard returns recommendations for bullish outlook")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    async def test_wizard_bullish_recommendations(self, auth_client: AsyncClient):
        """
        Test that the wizard returns appropriate strategies for bullish outlook
        """
        with allure.step("Send wizard request with bullish inputs"):
            response = await auth_client.post(
                "/api/strategy-wizard/wizard",
                json={
                    "outlook": "mild_bullish",
                    "volatility": "high",
                    "risk": "low"
                }
            )
        
        with allure.step("Verify response status"):
            assert response.status_code == 200
        
        with allure.step("Verify recommendations returned"):
            data = response.json()
            assert "recommendations" in data
            assert len(data["recommendations"]) > 0
        
        with allure.step("Verify bull_put_spread is recommended"):
            strategy_names = [r["template"]["name"] for r in data["recommendations"]]
            assert "bull_put_spread" in strategy_names
        
        allure.attach(
            str(data),
            name="Wizard Response",
            attachment_type=allure.attachment_type.JSON
        )
    
    @allure.story("Deploy Strategy")
    @allure.title("Deploy Iron Condor with live prices")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.api
    async def test_deploy_iron_condor(self, auth_client: AsyncClient, mock_kite):
        """
        Test deploying Iron Condor strategy with real strikes
        """
        with allure.step("Send deploy request"):
            response = await auth_client.post(
                "/api/strategy-wizard/deploy",
                json={
                    "template_name": "iron_condor",
                    "underlying": "NIFTY",
                    "expiry": "25D09",
                    "lots": 1
                }
            )
        
        with allure.step("Verify 4 legs created"):
            data = response.json()
            assert len(data["legs"]) == 4
        
        with allure.step("Verify leg structure"):
            leg_types = [(l["contract_type"], l["transaction_type"]) for l in data["legs"]]
            expected = [("PE", "BUY"), ("PE", "SELL"), ("CE", "SELL"), ("CE", "BUY")]
            assert leg_types == expected
```

### 2.2 Frontend (Playwright)

**Install Dependencies:**

```bash
cd frontend
npm install -D allure-playwright allure-commandline
```

**playwright.config.js:**

```javascript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e/specs',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : 4,

  // Reporters: heavy ones (JSON, JUnit, Allure) only in CI
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ...(process.env.CI ? [
      ['json', { outputFile: 'test-results/results.json' }],
      ['junit', { outputFile: 'test-results/junit.xml' }],
      ['allure-playwright', {
        outputFolder: 'allure-results',
        suiteTitle: true,
        categories: [
          {
            name: 'Outdated tests',
            messageRegex: '.*FileNotFound.*'
          },
          {
            name: 'Product defects',
            messageRegex: '.*AssertionError.*'
          }
        ],
        environmentInfo: {
          Project: 'AlgoChanakya',
          Framework: 'Vue.js 3',
          Browser: 'Chromium'
        }
      }]
    ] : []),
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    storageState: './tests/config/.auth-state.json',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    { name: 'setup', testMatch: /global-setup\.spec\.js/ },
    { name: 'chromium', dependencies: ['setup'], testIgnore: /.*\.isolated\.spec\.js/ },
    { name: 'isolated', testMatch: /.*\.isolated\.spec\.js/, use: { storageState: undefined } },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

**Example E2E Test with Allure:**

```javascript
// tests/e2e/specs/strategy-library/strategy-library.happy.spec.js

import { test, expect } from '@playwright/test';
import { allure } from 'allure-playwright';

test.describe('Strategy Library - Happy Path', () => {
  
  test.beforeEach(async ({ page }) => {
    await allure.epic('Strategy Library');
    await allure.feature('Browse Strategies');
    
    // Login first
    await page.goto('/login');
    // ... login steps
    await page.goto('/strategies');
  });

  test('should display all strategy categories', async ({ page }) => {
    await allure.story('Category Navigation');
    await allure.severity('critical');
    
    await allure.step('Verify page loaded', async () => {
      await expect(page.locator('h1')).toContainText('Strategy Library');
    });
    
    await allure.step('Verify all 6 categories visible', async () => {
      const categories = ['bullish', 'bearish', 'neutral', 'volatile', 'income', 'advanced'];
      for (const cat of categories) {
        await expect(page.locator(`.pill:has-text("${cat}")`)).toBeVisible();
      }
    });
    
    await allure.step('Take screenshot', async () => {
      const screenshot = await page.screenshot();
      await allure.attachment('Strategy Library Page', screenshot, 'image/png');
    });
  });

  test('should filter strategies by category', async ({ page }) => {
    await allure.story('Category Filter');
    await allure.severity('normal');
    
    await allure.step('Click on Neutral category', async () => {
      await page.click('.pill:has-text("neutral")');
    });
    
    await allure.step('Verify only neutral strategies shown', async () => {
      const cards = page.locator('.strategy-card');
      const count = await cards.count();
      
      for (let i = 0; i < count; i++) {
        await expect(cards.nth(i).locator('.category-badge')).toContainText('neutral');
      }
    });
  });

  test('should complete strategy wizard flow', async ({ page }) => {
    await allure.story('Strategy Wizard');
    await allure.severity('critical');
    
    await allure.step('Open wizard modal', async () => {
      await page.click('button:has-text("Strategy Wizard")');
      await expect(page.locator('.wizard-modal')).toBeVisible();
    });
    
    await allure.step('Step 1: Select market outlook', async () => {
      await page.click('[data-outlook="mild_bullish"]');
      await page.click('button:has-text("Next")');
    });
    
    await allure.step('Step 2: Select volatility expectation', async () => {
      await page.click('[data-volatility="high"]');
      await page.click('button:has-text("Next")');
    });
    
    await allure.step('Step 3: Select risk appetite', async () => {
      await page.click('[data-risk="low"]');
      await page.click('button:has-text("Get Recommendations")');
    });
    
    await allure.step('Verify recommendations displayed', async () => {
      await expect(page.locator('.recommendations-section')).toBeVisible();
      await expect(page.locator('.rec-card')).toHaveCount({ min: 1 });
    });
    
    // Attach final screenshot
    const screenshot = await page.screenshot({ fullPage: true });
    await allure.attachment('Wizard Recommendations', screenshot, 'image/png');
  });

  test('should deploy strategy from library', async ({ page }) => {
    await allure.story('Deploy Strategy');
    await allure.severity('critical');
    
    await allure.step('Click deploy on Iron Condor', async () => {
      await page.click('.strategy-card:has-text("Iron Condor") .btn-deploy');
    });
    
    await allure.step('Configure deployment', async () => {
      await page.selectOption('[name="underlying"]', 'NIFTY');
      await page.selectOption('[name="expiry"]', { index: 1 });
      await page.fill('[name="lots"]', '1');
    });
    
    await allure.step('Verify legs preview', async () => {
      await expect(page.locator('.leg-preview')).toHaveCount(4);
    });
    
    await allure.step('Click deploy button', async () => {
      await page.click('button:has-text("Deploy to Builder")');
    });
    
    await allure.step('Verify navigation to Strategy Builder', async () => {
      await expect(page).toHaveURL(/\/strategy/);
    });
  });
});
```

**package.json scripts:**

```json
{
  "scripts": {
    "test": "playwright test",
    "test:ui": "playwright test --ui",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "test:report": "playwright show-report",
    "allure:generate": "allure generate allure-results --clean -o allure-report",
    "allure:open": "allure open allure-report",
    "allure:serve": "allure serve allure-results",
    "test:allure": "playwright test && npm run allure:generate && npm run allure:open"
  }
}
```

---

## 3. GitHub Actions CI/CD

### 3.1 Backend Tests Workflow

**.github/workflows/backend-tests.yml:**

```yaml
name: Backend Tests

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'
      - '.github/workflows/backend-tests.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'backend/**'

env:
  DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/algochanakya_test
  REDIS_URL: redis://localhost:6379
  SECRET_KEY: test-secret-key-for-ci

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: algochanakya_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        working-directory: backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov allure-pytest httpx

      - name: Run database migrations
        working-directory: backend
        run: |
          alembic upgrade head

      - name: Run tests with coverage
        working-directory: backend
        run: |
          pytest tests/ \
            -v \
            --cov=app \
            --cov-report=xml:coverage.xml \
            --cov-report=html:coverage-report \
            --alluredir=allure-results \
            --junitxml=test-results/junit.xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: backend/coverage.xml
          flags: backend
          name: backend-coverage

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: backend-allure-results
          path: backend/allure-results/
          retention-days: 30

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: backend-test-results
          path: backend/test-results/

  allure-report:
    needs: test
    runs-on: ubuntu-latest
    if: always()
    
    steps:
      - name: Download Allure results
        uses: actions/download-artifact@v4
        with:
          name: backend-allure-results
          path: allure-results

      - name: Generate Allure Report
        uses: simple-elf/allure-report-action@master
        with:
          allure_results: allure-results
          allure_history: allure-history
          keep_reports: 20

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        if: github.ref == 'refs/heads/main'
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: allure-history
          destination_dir: backend-tests
```

### 3.2 Frontend E2E Tests Workflow

**.github/workflows/e2e-tests.yml:**

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:
    inputs:
      browser:
        description: 'Browser to test'
        required: false
        default: 'chromium'
        type: choice
        options:
          - chromium
          - firefox
          - all

env:
  CI: true
  BASE_URL: http://localhost:5173
  API_URL: http://localhost:8000

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: algochanakya_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install backend dependencies
        working-directory: backend
        run: |
          pip install -r requirements.txt

      - name: Install frontend dependencies
        working-directory: frontend
        run: |
          npm ci

      - name: Install Playwright browsers
        working-directory: frontend
        run: |
          npx playwright install --with-deps chromium firefox

      - name: Start backend server
        working-directory: backend
        run: |
          alembic upgrade head
          python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 10
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/algochanakya_test

      - name: Start frontend dev server
        working-directory: frontend
        run: |
          npm run dev &
          sleep 10

      - name: Run E2E tests
        working-directory: frontend
        run: |
          npx playwright test --project=chromium

      - name: Upload Playwright report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 30

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-allure-results
          path: frontend/allure-results/
          retention-days: 30

      - name: Upload test videos
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: test-videos
          path: frontend/test-results/
          retention-days: 7

  allure-report:
    needs: e2e-tests
    runs-on: ubuntu-latest
    if: always()
    
    steps:
      - name: Download Allure results
        uses: actions/download-artifact@v4
        with:
          name: e2e-allure-results
          path: allure-results

      - name: Get Allure history
        uses: actions/checkout@v4
        if: always()
        continue-on-error: true
        with:
          ref: gh-pages
          path: gh-pages

      - name: Generate Allure Report
        uses: simple-elf/allure-report-action@master
        if: always()
        with:
          allure_results: allure-results
          allure_history: allure-history
          keep_reports: 20

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        if: github.ref == 'refs/heads/main'
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: allure-history
          destination_dir: e2e-tests
```

### 3.3 Combined Test Status Badge

Add to README.md:

```markdown
## Test Status

[![Backend Tests](https://github.com/yourusername/algochanakya/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/yourusername/algochanakya/actions/workflows/backend-tests.yml)
[![E2E Tests](https://github.com/yourusername/algochanakya/actions/workflows/e2e-tests.yml/badge.svg)](https://github.com/yourusername/algochanakya/actions/workflows/e2e-tests.yml)
[![codecov](https://codecov.io/gh/yourusername/algochanakya/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/algochanakya)

### Test Reports
- [Backend Test Report](https://yourusername.github.io/algochanakya/backend-tests)
- [E2E Test Report](https://yourusername.github.io/algochanakya/e2e-tests)
```

---

## 4. BDD Test Specifications

### 4.1 Strategy Library Feature

**docs/testing/bdd-specs/strategy-library.feature:**

```gherkin
Feature: Strategy Library
  As an options trader
  I want to browse pre-built option strategies
  So that I can quickly deploy proven trading setups

  Background:
    Given I am logged in as a verified user
    And I am on the Strategy Library page

  # ============ BROWSE STRATEGIES ============
  
  @happy @smoke
  Scenario: View all strategy categories
    Then I should see the following category filters:
      | Category | Icon |
      | bullish  | 📈   |
      | bearish  | 📉   |
      | neutral  | ➡️   |
      | volatile | 🌋   |
      | income   | 💰   |
      | advanced | 🎓   |
    And I should see at least 20 strategy cards

  @happy
  Scenario: Filter strategies by category
    When I click on the "neutral" category filter
    Then I should only see strategies with category "neutral"
    And I should see "Iron Condor" in the results
    And I should see "Short Strangle" in the results
    And I should NOT see "Bull Call Spread" in the results

  @happy
  Scenario: Search for a strategy
    When I type "iron" in the search box
    Then I should see "Iron Condor" in the results
    And I should see "Iron Butterfly" in the results
    And I should NOT see "Bull Put Spread" in the results

  @edge
  Scenario: Search with no results
    When I type "xyz123nonexistent" in the search box
    Then I should see "No strategies found" message
    And I should see a "Clear search" button

  # ============ STRATEGY WIZARD ============

  @happy @critical
  Scenario: Complete strategy wizard for bullish outlook
    When I click the "Strategy Wizard" button
    Then I should see the wizard modal
    
    When I select "Mild Bullish" for market outlook
    And I click "Next"
    Then I should be on step 2
    
    When I select "High" for expected volatility
    And I click "Next"
    Then I should be on step 3
    
    When I select "Low" for risk appetite
    And I click "Get Recommendations"
    Then I should see at least 3 strategy recommendations
    And "Bull Put Spread" should be in the top 3 recommendations
    And each recommendation should show:
      | Field            |
      | Match Percentage |
      | Reasons          |
      | Win Probability  |

  @happy
  Scenario Outline: Wizard recommends appropriate strategies
    When I complete the wizard with:
      | Outlook   | Volatility   | Risk   |
      | <outlook> | <volatility> | <risk> |
    Then "<expected_strategy>" should be in the recommendations

    Examples:
      | outlook        | volatility | risk   | expected_strategy    |
      | mild_bullish   | high       | low    | Bull Put Spread      |
      | mild_bearish   | high       | low    | Bear Call Spread     |
      | neutral        | high       | medium | Iron Condor          |
      | volatile       | low        | medium | Long Straddle        |
      | strong_bullish | any        | high   | Synthetic Long       |

  @edge
  Scenario: Wizard back navigation
    Given I am on step 3 of the wizard
    When I click "Back"
    Then I should be on step 2
    And my previous selection should be preserved
    
    When I click "Back" again
    Then I should be on step 1
    And my previous selection should be preserved

  # ============ STRATEGY DETAILS ============

  @happy
  Scenario: View strategy details
    When I click "View Details" on "Iron Condor"
    Then I should see the strategy details modal
    And I should see the following sections:
      | Section           |
      | Description       |
      | When to Use       |
      | When to Avoid     |
      | Pros              |
      | Cons              |
      | Common Mistakes   |
      | Exit Rules        |
      | Example Setup     |
    And I should see these metrics:
      | Metric          | Value    |
      | Max Profit      | Limited  |
      | Max Loss        | Limited  |
      | Win Probability | 68%      |
      | Risk Level      | Medium   |
    And I should see Greeks badges: "θ+" and "Δ0"

  @happy
  Scenario: Close strategy details modal
    Given the strategy details modal is open
    When I click the close button
    Then the modal should close
    And I should see the strategy library page

  # ============ DEPLOY STRATEGY ============

  @happy @critical
  Scenario: Deploy Iron Condor strategy
    When I click "Deploy" on "Iron Condor"
    Then I should see the deploy modal
    And underlying should default to "NIFTY"
    
    When I select expiry "2025-12-11"
    And I set lots to "1"
    Then I should see 4 legs preview:
      | Type | Strike | Transaction |
      | PE   | 25600  | BUY         |
      | PE   | 25800  | SELL        |
      | CE   | 26200  | SELL        |
      | CE   | 26400  | BUY         |
    And I should see net premium displayed
    
    When I click "Deploy to Builder"
    Then I should be navigated to "/strategy"
    And the Strategy Builder should have 4 legs populated

  @happy
  Scenario: Change underlying in deploy modal
    Given the deploy modal is open for "Iron Condor"
    When I change underlying to "BANKNIFTY"
    Then the strike step should change to 100
    And lot size should change to 15
    And leg strikes should be recalculated

  @edge
  Scenario: Deploy with multiple lots
    Given the deploy modal is open for "Bull Call Spread"
    When I set lots to "3"
    Then quantity for each leg should be "225" (75 * 3)
    And net premium should be multiplied by 3

  # ============ STRATEGY COMPARISON ============

  @happy
  Scenario: Compare two strategies
    When I click the compare icon on "Iron Condor"
    And I click the compare icon on "Iron Butterfly"
    Then the comparison bar should appear
    And it should show "2 strategies selected"
    
    When I click "Compare"
    Then I should see the comparison modal
    And I should see side-by-side metrics:
      | Metric          | Iron Condor | Iron Butterfly |
      | Max Profit      | Limited     | Limited        |
      | Win Probability | 68%         | 40%            |
      | Breakevens      | 2           | 2              |

  @edge
  Scenario: Cannot compare more than 5 strategies
    Given I have 5 strategies selected for comparison
    When I try to add a 6th strategy
    Then I should see an error message "Maximum 5 strategies for comparison"

  @edge
  Scenario: Clear comparison selection
    Given I have 3 strategies selected for comparison
    When I click "Clear" on the comparison bar
    Then the comparison bar should disappear
    And no strategies should be selected
```

### 4.2 Positions Feature

**docs/testing/bdd-specs/positions.feature:**

```gherkin
Feature: Positions Management
  As an options trader
  I want to view and manage my open F&O positions
  So that I can monitor P&L and exit trades

  Background:
    Given I am logged in
    And I have open F&O positions
    And I am on the Positions page

  # ============ VIEW POSITIONS ============

  @happy @smoke
  Scenario: View day positions
    Given the "Day" tab is selected
    Then I should see my intraday positions
    And each position should show:
      | Field           |
      | Instrument      |
      | Product         |
      | Quantity        |
      | Average Price   |
      | LTP             |
      | Day Change      |
      | P&L             |
      | Change %        |
    And total P&L should be displayed in the header

  @happy
  Scenario: View net positions
    When I click the "Net" tab
    Then I should see my net (carried forward) positions
    And the P&L should reflect overall position P&L

  @happy
  Scenario: Positions auto-refresh
    Given auto-refresh is enabled
    When 5 seconds pass
    Then positions should be refreshed
    And LTP and P&L should be updated

  @edge
  Scenario: No open positions
    Given I have no open positions
    Then I should see "No Open Positions" message
    And I should see a link to "Go to Option Chain"

  # ============ EXIT POSITIONS ============

  @happy @critical
  Scenario: Exit position at market price
    When I click "Exit" on a NIFTY 26000 CE position
    Then I should see the exit modal
    And "MARKET" should be selected by default
    
    When I click "Exit Position"
    Then an opposite order should be placed
    And I should see "Order placed successfully"
    And the position should be removed from the list

  @happy
  Scenario: Exit position at limit price
    Given the exit modal is open
    When I select "LIMIT" order type
    And I enter price "125.50"
    And I click "Exit Position"
    Then a limit order should be placed at 125.50

  @happy @critical
  Scenario: Exit all positions
    When I click "Exit All" button
    Then I should see a confirmation dialog
    And the dialog should warn about exiting all positions
    
    When I click "Yes, Exit All"
    Then all positions should have exit orders placed
    And I should see the number of orders placed

  @edge
  Scenario: Cancel exit modal
    Given the exit modal is open
    When I click "Cancel" or the X button
    Then the modal should close
    And no order should be placed

  # ============ ADD TO POSITION ============

  @happy
  Scenario: Add to existing long position
    Given I have a long position in NIFTY 26000 CE
    When I click "Add" on that position
    Then I should see the add modal
    And "BUY" should be selected
    
    When I enter quantity "75"
    And I enter price "130"
    And I click "Add to Position"
    Then a buy order should be placed
    And I should see "Order placed successfully"

  @happy
  Scenario: Add to existing short position
    Given I have a short position in NIFTY 26000 PE
    When I click "Add" on that position
    And I select "SELL"
    And I enter quantity "75"
    And I enter price "45"
    And I click "Add to Position"
    Then a sell order should be placed

  # ============ P&L DISPLAY ============

  @happy
  Scenario: Profit position styling
    Given I have a profitable position
    Then the P&L column should be green
    And the row should have a green tint

  @happy
  Scenario: Loss position styling
    Given I have a losing position
    Then the P&L column should be red
    And the row should have a red tint

  @happy
  Scenario: Total P&L calculation
    Given I have multiple positions
    Then total P&L should be the sum of all position P&Ls
    And total P&L box should be green if positive
    And total P&L box should be red if negative
```

---

## 5. Test Coverage Matrix

### 5.1 Feature Coverage Matrix

**docs/testing/coverage-matrix.md:**

```markdown
# AlgoChanakya Test Coverage Matrix

Last Updated: 2025-12-08

## Legend
- ✅ Implemented and passing
- 🟡 Partially implemented
- ❌ Not implemented
- 🔄 In progress
- N/A Not applicable

## Backend API Tests

| Endpoint | Unit | API | Integration | Edge Cases | Auth |
|----------|------|-----|-------------|------------|------|
| **Authentication** |
| POST /auth/login | ✅ | ✅ | ✅ | ✅ | N/A |
| GET /auth/callback | ✅ | ✅ | ✅ | ✅ | N/A |
| POST /auth/logout | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /auth/me | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Watchlist** |
| GET /watchlist | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /watchlist | ✅ | ✅ | ✅ | ✅ | ✅ |
| DELETE /watchlist/{id} | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Option Chain** |
| GET /optionchain | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /optionchain/expiries | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Strategy Builder** |
| POST /strategy/calculate | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /strategy/payoff | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Positions** |
| GET /positions | ✅ | ✅ | 🟡 | ✅ | ✅ |
| POST /positions/exit | ✅ | ✅ | 🟡 | ✅ | ✅ |
| POST /positions/add | ✅ | ✅ | 🟡 | ✅ | ✅ |
| POST /positions/exit-all | ✅ | ✅ | 🟡 | ✅ | ✅ |
| **Strategy Wizard** |
| GET /strategy-wizard/templates | 🔄 | 🔄 | ❌ | ❌ | ✅ |
| GET /strategy-wizard/templates/{name} | 🔄 | 🔄 | ❌ | ❌ | ✅ |
| POST /strategy-wizard/wizard | 🔄 | 🔄 | ❌ | ❌ | ✅ |
| POST /strategy-wizard/deploy | 🔄 | 🔄 | ❌ | ❌ | ✅ |
| GET /strategy-wizard/popular | 🔄 | 🔄 | ❌ | ❌ | ✅ |

## Frontend E2E Tests

| Feature | Happy Path | Edge Cases | Visual | API Mock | Accessibility |
|---------|------------|------------|--------|----------|---------------|
| **Authentication** |
| Login page | ✅ | ✅ | ✅ | ✅ | 🟡 |
| OAuth callback | ✅ | ✅ | N/A | ✅ | N/A |
| Session management | ✅ | ✅ | N/A | ✅ | N/A |
| **Dashboard** |
| Market overview | ✅ | 🟡 | ✅ | ✅ | 🟡 |
| Quick actions | ✅ | ✅ | ✅ | ✅ | 🟡 |
| **Watchlist** |
| View watchlist | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Add symbol | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Remove symbol | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Live prices | ✅ | 🟡 | ✅ | ✅ | N/A |
| **Option Chain** |
| View chain | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Change expiry | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Greeks display | ✅ | ✅ | ✅ | ✅ | 🟡 |
| OI analysis | ✅ | ✅ | ✅ | ✅ | 🟡 |
| **Strategy Builder** |
| Add legs | ✅ | ✅ | ✅ | ✅ | 🟡 |
| P&L calculation | ✅ | ✅ | ✅ | ✅ | N/A |
| Payoff chart | ✅ | ✅ | ✅ | ✅ | N/A |
| Place orders | ✅ | ✅ | ✅ | ✅ | 🟡 |
| **Positions** |
| View positions | 🔄 | 🔄 | 🔄 | 🔄 | ❌ |
| Exit position | 🔄 | 🔄 | 🔄 | 🔄 | ❌ |
| Add to position | 🔄 | 🔄 | 🔄 | 🔄 | ❌ |
| Exit all | 🔄 | 🔄 | 🔄 | 🔄 | ❌ |
| **Strategy Library** |
| Browse strategies | ❌ | ❌ | ❌ | ❌ | ❌ |
| Strategy wizard | ❌ | ❌ | ❌ | ❌ | ❌ |
| Deploy strategy | ❌ | ❌ | ❌ | ❌ | ❌ |
| Compare strategies | ❌ | ❌ | ❌ | ❌ | ❌ |

## Test Statistics

| Category | Total | Passing | Failing | Skipped | Coverage |
|----------|-------|---------|---------|---------|----------|
| Backend Unit | 45 | 45 | 0 | 0 | 92% |
| Backend API | 62 | 60 | 2 | 0 | 88% |
| Backend Integration | 15 | 12 | 0 | 3 | 75% |
| Frontend E2E | 77 | 77 | 0 | 0 | 85% |
| **Total** | **199** | **194** | **2** | **3** | **85%** |

## Priority Test Gaps

### High Priority (Must implement)
1. Strategy Library - All tests missing
2. Positions - Integration tests incomplete
3. Accessibility tests - Mostly missing

### Medium Priority
1. Visual regression tests expansion
2. Performance tests
3. Load tests for WebSocket

### Low Priority
1. Cross-browser testing (Firefox, Safari)
2. Mobile responsive tests
3. Offline mode tests
```

---

## 6. Test Documentation

### 6.1 Test Plan

**docs/testing/test-plan.md:**

```markdown
# AlgoChanakya Test Plan

## 1. Introduction

### 1.1 Purpose
This document outlines the testing strategy for AlgoChanakya, an options trading platform.

### 1.2 Scope
- Backend API testing (Python/FastAPI)
- Frontend E2E testing (Vue.js/Playwright)
- Integration testing
- Performance testing

### 1.3 References
- [BDD Specifications](./bdd-specs/)
- [Coverage Matrix](./coverage-matrix.md)
- [Test Cases](./test-cases.md)

## 2. Test Strategy

### 2.1 Testing Levels

| Level | Description | Tools | Responsibility |
|-------|-------------|-------|----------------|
| Unit | Individual functions/methods | pytest, Vitest | Developers |
| API | HTTP endpoint testing | pytest, httpx | Developers |
| Integration | Multi-component flows | pytest | QA/Developers |
| E2E | Full user journeys | Playwright | QA |
| Performance | Load and stress | k6, Locust | DevOps |

### 2.2 Test Types

1. **Functional Testing**
   - Happy path scenarios
   - Edge cases and error handling
   - Business logic validation

2. **Non-Functional Testing**
   - Performance (response times)
   - Security (authentication, authorization)
   - Usability (accessibility)

3. **Regression Testing**
   - Run on every PR
   - Full suite before release

### 2.3 Test Data Management

- Use fixtures for consistent test data
- Seed scripts for database setup
- Mock external APIs (Kite Connect)

## 3. Test Environment

### 3.1 Local Development
```
Frontend: http://localhost:5173
Backend: http://localhost:8000
Database: PostgreSQL (localhost:5432)
Redis: localhost:6379
```

### 3.2 CI/CD
```
GitHub Actions runners
Dockerized services
Isolated test database
```

## 4. Entry and Exit Criteria

### 4.1 Entry Criteria
- Code complete and committed
- Unit tests written and passing
- API documentation updated

### 4.2 Exit Criteria
- All critical tests passing
- Code coverage > 80%
- No high/critical bugs open
- Performance benchmarks met

## 5. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Kite API changes | Medium | High | Mock API, contract tests |
| Flaky E2E tests | High | Medium | Retry logic, stable selectors |
| Test data pollution | Medium | Medium | Database isolation, cleanup |

## 6. Schedule

| Phase | Duration | Activities |
|-------|----------|------------|
| Sprint tests | 2 days | New feature tests |
| Regression | 1 day | Full suite execution |
| Bug fix verification | Ongoing | Targeted tests |

## 7. Deliverables

1. Test reports (Allure)
2. Coverage reports (Codecov)
3. Bug reports (GitHub Issues)
4. Test documentation updates
```

---

## 7. Claude Code Implementation Prompt

Use this prompt to implement the entire testing infrastructure:

```
Implement comprehensive testing infrastructure for AlgoChanakya based on docs/testing/algochanakya-testing-infrastructure.md

## Implementation Order

### Step 1: Backend Test Setup
1. Update `backend/pytest.ini` with Allure configuration
2. Update `backend/tests/conftest.py` with:
   - Allure environment info
   - Fixtures with Allure labels
   - Screenshot on failure hook
3. Install: `pip install allure-pytest pytest-cov`

### Step 2: Create Backend Test Files
Create tests for Strategy Wizard API in `backend/tests/api/test_strategy_wizard.py`:
- Test all endpoints with Allure annotations
- Use @allure.epic, @allure.feature, @allure.story decorators
- Add allure.step() for each test action
- Attach responses on failure

### Step 3: Frontend Test Setup
1. Install: `npm install -D allure-playwright`
2. Update `playwright.config.js` with Allure reporter
3. Add npm scripts for Allure report generation

### Step 4: Create E2E Test Files
Create tests in `frontend/tests/e2e/specs/strategy-library/`:
- strategy-library.happy.spec.js
- strategy-library.edge.spec.js
- strategy-library.visual.spec.js

### Step 5: GitHub Actions Setup
Create workflows:
- `.github/workflows/backend-tests.yml`
- `.github/workflows/e2e-tests.yml`

### Step 6: Documentation
Create in `docs/testing/`:
- README.md
- test-plan.md
- coverage-matrix.md
- bdd-specs/strategy-library.feature
- bdd-specs/positions.feature

## Requirements
1. Use Allure for all test reports
2. Follow BDD style for E2E tests
3. Maintain >80% code coverage
4. Run tests on every PR via GitHub Actions
5. Deploy reports to GitHub Pages

## Commands to Run After Implementation
```bash
# Backend
cd backend
pytest tests/ -v --alluredir=allure-results
allure serve allure-results

# Frontend
cd frontend
npm run test:allure
```

Start with Step 1 and proceed sequentially. Show each file as you create it.
```

---

## Quick Start Commands

```bash
# Install all test dependencies
cd backend && pip install allure-pytest pytest-cov pytest-asyncio httpx
cd frontend && npm install -D allure-playwright allure-commandline

# Run backend tests with Allure
cd backend
pytest tests/ -v --alluredir=allure-results --cov=app
allure serve allure-results

# Run frontend E2E tests with Allure
cd frontend
npx playwright test
npm run allure:serve

# Generate coverage report
pytest tests/ --cov=app --cov-report=html
open coverage-report/index.html
```
