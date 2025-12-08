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
- [Implementation Plan](./implementation-plan.md)

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

## 8. Test Commands

### Backend Tests
```bash
# Run all backend tests with Allure
cd backend
pytest tests/ -v --alluredir=allure-results
allure serve allure-results

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### Frontend E2E Tests
```bash
# Run all E2E tests
npm test

# Run with Allure report
npm run test:allure

# Run by screen
npm run test:specs:strategylibrary
npm run test:specs:positions
```

### CI/CD
- Backend tests run on push/PR to `backend/**`
- E2E tests run on all pushes/PRs
- Allure reports published to GitHub Pages
