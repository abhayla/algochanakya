# Error Fingerprinting Reference

Complete guide to error fingerprinting algorithm for deduplication and pattern matching.

## Purpose

Error fingerprinting creates a **unique identifier** for each error pattern by normalizing error messages and file paths. This enables:
- **Deduplication:** Same error in different contexts → same fingerprint
- **Pattern Matching:** Find historical fixes for similar errors
- **Cross-session Learning:** Errors from past sessions match current errors

---

## Algorithm

### Fingerprint Function

```python
def fingerprint(error_type: str, message: str, file_path: Optional[str] = None) -> str:
    """Generate error fingerprint by normalizing and hashing."""

    # 1. Normalize message
    norm_msg = message
    norm_msg = re.sub(r'\bline \d+\b', 'line N', norm_msg, flags=re.IGNORECASE)
    norm_msg = re.sub(r"'[^']*'", "'X'", norm_msg)
    norm_msg = re.sub(r'"[^"]*"', '"X"', norm_msg)
    norm_msg = re.sub(r'\b\d{4}-\d{2}-\d{2}', 'DATE', norm_msg)
    norm_msg = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', 'UUID', norm_msg, flags=re.IGNORECASE)
    norm_msg = re.sub(r'\d+', 'N', norm_msg)

    # 2. Normalize file path to pattern
    if file_path:
        file_path = file_path.replace('\\', '/')
        norm_file = re.sub(r'/[^/]+\.py$', '/*.py', file_path)
        norm_file = re.sub(r'/[^/]+\.js$', '/*.js', norm_file)
        norm_file = re.sub(r'/[^/]+\.vue$', '/*.vue', norm_file)
    else:
        norm_file = ''

    # 3. Hash normalized components
    raw = f"{error_type}|{norm_msg}|{norm_file}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

---

## Normalization Rules

### 1. Line Numbers → "line N"
**Purpose:** Line numbers change with code edits but don't affect error type.

```python
# Original
"ImportError at line 42: cannot import name 'Foo'"

# Normalized
"ImportError at line N: cannot import name 'X'"
```

### 2. Quoted Values → "X"
**Purpose:** Specific values (class names, variable names) are placeholders for pattern.

```python
# Original
"cannot import name 'SuggestionPriority' from 'app.models'"

# Normalized
"cannot import name 'X' from 'X'"
```

### 3. Dates → "DATE"
**Purpose:** Timestamps don't affect error type.

```python
# Original
"Test failed on 2025-01-15"

# Normalized
"Test failed on DATE"
```

### 4. UUIDs → "UUID"
**Purpose:** UUIDs are dynamic identifiers.

```python
# Original
"Session a1b2c3d4-e5f6-7890-abcd-ef1234567890 not found"

# Normalized
"Session UUID not found"
```

### 5. All Numbers → "N"
**Purpose:** Catch-all for numeric values (port numbers, counts, IDs).

```python
# Original
"Connection refused on port 8000"

# Normalized
"Connection refused on port N"
```

### 6. File Paths → Patterns
**Purpose:** Same error in different files (but same type) should match.

```python
# Original
"backend/app/services/autopilot/suggestion_engine.py"

# Normalized (pattern)
"backend/app/services/autopilot/*.py"

# Multiple levels deep
"backend/app/models/autopilot_models.py" → "backend/app/models/*.py"
```

---

## Error Type Examples

### ImportError

**Raw Error:**
```
ImportError: cannot import name 'SuggestionPriority' from 'app.models.autopilot_models' (backend/app/models/autopilot_models.py:142)
```

**Fingerprint Input:**
```python
error_type = "ImportError"
message = "cannot import name 'SuggestionPriority' from 'app.models.autopilot_models'"
file_path = "backend/app/services/autopilot/suggestion_engine.py"
```

**Normalization:**
```
error_type: "ImportError"
norm_msg:   "cannot import name 'X' from 'X'"
norm_file:  "backend/app/services/autopilot/*.py"
```

**Fingerprint:** `a3f8e9d1c2b4a567` (16-char SHA256 prefix)

**Result:** All ImportErrors with "cannot import name" pattern in `autopilot/*.py` files → same fingerprint

---

### TestFailure (Selector Not Found)

**Raw Error:**
```
Error: Locator 'data-testid=positions-exit-modal' not found (tests/e2e/specs/positions/exit.spec.js:42)
```

**Fingerprint Input:**
```python
error_type = "TestFailure"
message = "Locator 'data-testid=positions-exit-modal' not found"
file_path = "tests/e2e/specs/positions/exit.spec.js"
```

**Normalization:**
```
error_type: "TestFailure"
norm_msg:   "Locator 'X' not found"
norm_file:  "tests/e2e/specs/positions/*.js"
```

**Fingerprint:** `b7c2d4e1f3a5b890`

**Result:** All "Locator not found" errors in `positions/*.js` tests → same fingerprint

---

### ModuleNotFoundError

**Raw Error:**
```
ModuleNotFoundError: No module named 'pandas' (backend/app/services/analytics.py:5)
```

**Fingerprint Input:**
```python
error_type = "ModuleNotFoundError"
message = "No module named 'pandas'"
file_path = "backend/app/services/analytics.py"
```

**Normalization:**
```
error_type: "ModuleNotFoundError"
norm_msg:   "No module named 'X'"
norm_file:  "backend/app/services/*.py"
```

**Fingerprint:** `c8d3e5f2a4b6c901`

**Result:** All "No module named" errors in `services/*.py` → same fingerprint

---

### BuildError

**Raw Error:**
```
Build failed: Cannot resolve module './components/StrategyCard.vue' (frontend/src/views/StrategyView.vue:12)
```

**Fingerprint Input:**
```python
error_type = "BuildError"
message = "Cannot resolve module './components/StrategyCard.vue'"
file_path = "frontend/src/views/StrategyView.vue"
```

**Normalization:**
```
error_type: "BuildError"
norm_msg:   "Cannot resolve module 'X'"
norm_file:  "frontend/src/views/*.vue"
```

**Fingerprint:** `d9e4f6a3b5c7d012`

**Result:** All "Cannot resolve module" errors in `views/*.vue` → same fingerprint

---

## Edge Cases

### Same Error, Different Files
**Should produce SAME fingerprint** (pattern matching)

```python
# Error 1
fingerprint("ImportError", "cannot import name 'Foo'", "backend/app/services/service_a.py")
# → "abc123..."

# Error 2
fingerprint("ImportError", "cannot import name 'Bar'", "backend/app/services/service_b.py")
# → "abc123..." (SAME! Both are ImportError in services/*.py)
```

### Different Error Types, Same Message
**Should produce DIFFERENT fingerprints** (error type matters)

```python
# Error 1
fingerprint("ImportError", "Module not found", "file.py")
# → "abc123..."

# Error 2
fingerprint("ModuleNotFoundError", "Module not found", "file.py")
# → "def456..." (DIFFERENT! Error types differ)
```

### File Path vs No File Path
**Should produce DIFFERENT fingerprints** (file context matters)

```python
# Error 1
fingerprint("TestFailure", "Timeout", None)
# → "abc123..."

# Error 2
fingerprint("TestFailure", "Timeout", "tests/e2e/test.spec.js")
# → "def456..." (DIFFERENT! File path provides context)
```

### Cross-Platform Paths
**Windows `\` vs Unix `/` should produce SAME fingerprint**

```python
# Windows
fingerprint("ImportError", "Foo", "backend\\app\\services\\bar.py")
# → Normalized to "backend/app/services/*.py"

# Unix
fingerprint("ImportError", "Foo", "backend/app/services/bar.py")
# → Normalized to "backend/app/services/*.py"

# Result: SAME fingerprint!
```

---

## Deduplication Examples

### Scenario 1: Repeated ImportError After File Move

**Session 1 (Jan 10):**
```
Error: cannot import name 'SuggestionPriority' from 'app.models.autopilot_models'
File: backend/app/services/autopilot/suggestion_engine.py
Fingerprint: abc123def456
```

**Session 2 (Jan 15, same error still present):**
```
Error: cannot import name 'SuggestionPriority' from 'app.models.autopilot_models'
File: backend/app/services/autopilot/suggestion_engine.py
Fingerprint: abc123def456 (SAME!)
```

**Result:**
- `error_patterns` table: `occurrence_count = 2`, `last_seen` updated
- Learning engine retrieves fix strategies from Session 1
- No duplicate pattern created

---

### Scenario 2: Similar Errors in Different Files

**Error A:**
```
ImportError: cannot import name 'OrderStatus' from 'app.models.order_models'
File: backend/app/services/orders/order_service.py
Fingerprint: xyz789abc123
```

**Error B:**
```
ImportError: cannot import name 'PositionType' from 'app.models.position_models'
File: backend/app/services/positions/position_service.py
Fingerprint: xyz789abc123 (SAME!)
```

**Result:**
- Both map to same error pattern (ImportError in services/*.py with "cannot import name")
- Strategies learned from fixing Error A apply to Error B
- Cross-service learning achieved

---

## Testing Fingerprints

### Manual Test Script

```python
from db_helper import fingerprint

# Test normalization
fp1 = fingerprint("ImportError", "cannot import 'Foo' at line 42", "app/services/a.py")
fp2 = fingerprint("ImportError", "cannot import 'Bar' at line 99", "app/services/b.py")

assert fp1 == fp2, "Should be same pattern!"
print(f"✓ Fingerprint deduplication works: {fp1}")

# Test uniqueness
fp3 = fingerprint("ModuleNotFoundError", "cannot import 'Foo'", "app/services/a.py")
assert fp1 != fp3, "Different error types should differ!"
print(f"✓ Fingerprint uniqueness works")
```

---

## Best Practices

1. **Always normalize before hashing** - Don't skip normalization steps
2. **Include file pattern if available** - Provides valuable context
3. **Use consistent error types** - Map backend exceptions to standard types
4. **Test edge cases** - Verify cross-platform path handling
5. **Monitor collision rate** - If too many unrelated errors map to same fingerprint, refine normalization

---

## Fingerprint Storage

**Database Column:**
```sql
fingerprint TEXT UNIQUE NOT NULL  -- 16-char SHA256 prefix
```

**Index:** `CREATE INDEX idx_error_fingerprint ON error_patterns(fingerprint);`

**Query Pattern:**
```python
cursor.execute(
    "SELECT id FROM error_patterns WHERE fingerprint = ?",
    (fp,)
)
```

**Collision Handling:**
- SHA256 prefix collision rate: ~1 in 18 quintillion (negligible)
- If collision occurs: SQLite UNIQUE constraint prevents duplicate
- 16 characters provide sufficient uniqueness for this use case
