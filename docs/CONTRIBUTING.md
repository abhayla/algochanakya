# Documentation Contributing Guidelines

## Where to Put Documentation

| Document Type | Location | Example |
|---------------|----------|---------|
| Feature docs | `docs/features/{feature}.md` | `features/alerts.md` |
| Setup guides | `docs/guides/{topic}.md` | `guides/deployment.md` |
| Architecture | `docs/architecture/{component}.md` | `architecture/caching.md` |
| API docs | `docs/api/{resource}.md` | `api/websocket.md` |
| Test docs | `docs/testing/{topic}.md` | `testing/unit-tests.md` |
| Plans/specs | `docs/plans/{name}.md` | `plans/mobile-app.md` |
| Decisions | `docs/decisions/{NNN}-{title}.md` | `decisions/002-redis.md` |

## File Naming Conventions

- Use **lowercase with hyphens**: `strategy-builder.md`
- Not PascalCase: `StrategyBuilder.md`
- Not snake_case: `strategy_builder.md`
- Be descriptive: `websocket-reconnection.md` not `ws.md`

## Screenshot Naming

Location: `docs/assets/screenshots/`

Format: `{feature}-{description}.png`

Examples:
- `login-zerodha-button.png`
- `optionchain-nifty-atm.png`
- `positions-exit-modal.png`
- `strategy-iron-condor-payoff.png`

## Document Structure

Every documentation file should include:

1. **Title** (H1) - Clear, descriptive name
2. **Overview** - Brief description (2-3 sentences)
3. **Content** - Main documentation with headers
4. **Related** - Links to related docs

## Using Templates

Templates are in `docs/templates/`. Copy and customize:

```bash
# New feature doc
cp docs/templates/feature.md docs/features/{name}.md

# New guide
cp docs/templates/guide.md docs/guides/{name}.md

# New ADR
cp docs/templates/adr.md docs/decisions/{NNN}-{title}.md
```

## Checklist Before Committing

- [ ] File is in correct location
- [ ] Filename uses lowercase-hyphens
- [ ] `docs/README.md` index updated with link
- [ ] `CHANGELOG.md` updated (if new feature)
- [ ] Screenshots optimized (max 1200px width)
- [ ] All internal links work

## Important Rules

1. **NEVER** create `.md` files in project root (except README.md, CLAUDE.md, CHANGELOG.md)
2. **ALWAYS** update `docs/README.md` when adding new docs
3. **USE** templates for consistency
4. **TEST** all links before committing
