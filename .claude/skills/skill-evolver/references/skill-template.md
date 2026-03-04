# Skill Template

Use this template when creating new skills via `skill-evolver create`.

```markdown
---
name: {skill-name}
description: {One-line description of what this skill does, when to use it, and trigger keywords.}
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: {workflow|meta-workflow|code-gen|testing|broker|debugging}
  created_by: skill-evolver
  created_from: {discover|user-request|reflect-deep}
---

# {Skill Display Name}

**Purpose:** {2-3 sentences explaining what this skill does and why it exists.}

## When to Use

- {Trigger condition 1}
- {Trigger condition 2}
- On explicit invocation: "{trigger keywords}"

## When NOT to Use

- {Anti-pattern 1 — what similar skill handles this instead}
- {Anti-pattern 2}

---

## Steps

### Step 1: {Name}

**Purpose:** {What this step accomplishes}

{Algorithm, code examples, or instructions}

### Step 2: {Name}

{Continue for each step}

---

## Output Format

```
{Example output the skill produces}
```

---

## Integration

- **Upstream:** {Skills that feed into this one}
- **Downstream:** {Skills this one triggers}
- **Data:** {knowledge.db tables used, if any}

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| {Common issue} | {Root cause} | {Solution} |

---

## References

- Created by skill-evolver from {source}
- Related skills: {list}
```

## Naming Conventions

- Skill directory name: `kebab-case` (e.g., `migration-fixer`)
- Skill file: always `SKILL.md` (uppercase)
- References directory: `references/` (lowercase)
- Category values: `workflow`, `meta-workflow`, `code-gen`, `testing`, `broker`, `debugging`

## Required Sections Checklist

- [ ] YAML frontmatter with name, description, metadata
- [ ] Purpose statement
- [ ] When to Use (with trigger conditions)
- [ ] When NOT to Use (with alternatives)
- [ ] Steps or Algorithm (the actual logic)
- [ ] Output format example
- [ ] Integration points
