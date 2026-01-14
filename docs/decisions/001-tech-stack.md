# ADR-001: Technology Stack Selection

**Status:** Accepted

**Date:** 2024-12-03

**Decision Makers:** Development Team

## Context

We need to build an options trading platform similar to Sensibull. The platform requires:

1. Real-time price streaming via WebSocket
2. Complex P/L calculations (Black-Scholes)
3. Integration with broker APIs (Zerodha Kite Connect)
4. Responsive web interface
5. Scalable architecture for future growth

## Decision

We chose the following technology stack:

### Backend

| Component | Choice | Reason |
|-----------|--------|--------|
| Framework | **FastAPI** | Async support, automatic OpenAPI docs, Python ecosystem |
| ORM | **SQLAlchemy (async)** | Mature, async support, Alembic migrations |
| Database | **PostgreSQL** | Reliable, JSONB support, VPS hosting available |
| Cache/Sessions | **Redis** | Fast, pub/sub for real-time, session storage |
| Broker SDK | **kiteconnect** | Official Zerodha Python SDK |

### Frontend

| Component | Choice | Reason |
|-----------|--------|--------|
| Framework | **Vue.js 3** | Composition API, smaller bundle, easier learning curve |
| Build Tool | **Vite** | Fast HMR, ESM-native, Vue 3 optimized |
| State | **Pinia** | Vue 3 native, TypeScript support |
| Styling | **Tailwind CSS** | Utility-first, rapid development |

### Testing

| Component | Choice | Reason |
|-----------|--------|--------|
| E2E | **Playwright** | Cross-browser, auto-wait, screenshot comparison |

## Consequences

### Positive

- **FastAPI async** enables efficient WebSocket handling for thousands of concurrent connections
- **Python ecosystem** provides scipy for Black-Scholes calculations
- **Vue 3 Composition API** makes complex state management (strategy builder) more maintainable
- **Tailwind CSS** accelerates UI development with consistent design
- **Playwright** provides reliable E2E testing with visual regression

### Negative

- **Python performance** for heavy calculations (mitigated by scipy)
- **Vue smaller community** than React (sufficient for our needs)
- **Two languages** (Python + JavaScript) requires broader team skills

### Neutral

- PostgreSQL hosting on VPS works well for current scale
- Redis single instance sufficient for session storage

## Alternatives Considered

### Alternative 1: Django + React

**Description:** Django REST Framework backend with React frontend.

**Pros:**
- Larger Django community
- React's massive ecosystem
- Django ORM well-documented

**Cons:**
- Django not async-native (ASGI added complexity)
- React's JSX learning curve
- Larger bundle size for React

**Why rejected:** FastAPI's native async support better suited for WebSocket-heavy application. Vue's simpler mental model preferred for rapid development.

### Alternative 2: Node.js + Express + React

**Description:** Full JavaScript stack.

**Pros:**
- Single language (JavaScript)
- Large npm ecosystem
- Native WebSocket support

**Cons:**
- No scipy equivalent for Black-Scholes
- Kite Connect SDK is Python-first
- TypeORM less mature than SQLAlchemy

**Why rejected:** Zerodha's official SDK is Python. Mathematical calculations better supported in Python ecosystem.

### Alternative 3: Flask + Vue

**Description:** Flask backend with Vue frontend.

**Pros:**
- Flask is simpler than FastAPI
- Proven combination

**Cons:**
- Flask not async-native
- Manual OpenAPI documentation
- No dependency injection

**Why rejected:** FastAPI's async support and automatic docs generation provide significant developer experience improvements.

## Related Decisions

- [ADR-002](002-broker-abstraction.md) - Multi-Broker Abstraction Architecture

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)
- [Kite Connect Python SDK](https://kite.trade/docs/pykiteconnect/)
- [Playwright Documentation](https://playwright.dev/)
