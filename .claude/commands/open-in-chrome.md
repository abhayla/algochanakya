# Open in Chrome Command

Opens AlgoChanakya in Chrome browser with authentication for manual testing.

## Usage

```
/open-in-chrome [path]
```

## Examples

```
/open-in-chrome              # Opens /dashboard (default)
/open-in-chrome /positions   # Opens positions page
/open-in-chrome /autopilot   # Opens AutoPilot dashboard
/open-in-chrome /strategy    # Opens Strategy Builder
/open-in-chrome /optionchain # Opens Option Chain
```

## Implementation Workflow

### Step 1: Check Prerequisites
```
1. Verify backend is running on localhost:8000
2. Verify frontend is running on localhost:5173
3. Verify Claude Chrome extension is connected
```

### Step 2: Get Full Auth State
```
1. Read auth state from tests/config/.auth-state.json
2. Also check token from tests/config/.auth-token for expiry validation
3. If auth state doesn't exist:
   - Ask user for TOTP
   - Perform Kite OAuth login via Playwright setup
   - Save auth state for future use
4. If auth state exists:
   - Check if token is expired (decode JWT payload, check exp timestamp)
   - If expired, prompt user to run: npm test (to refresh auth)
   - If valid, proceed to Step 3
```

### Step 3: Open in Chrome with Full Auth State
```
1. Navigate to localhost:5173{path}
2. Apply full authentication state:
   a. Add cookies from auth state to browser context
   b. Inject localStorage items from auth state
   c. Inject sessionStorage items from auth state
3. Refresh the page
4. Verify authentication succeeded:
   - Check if stayed on requested page (no redirect to login)
   - Verify dashboard elements are visible
   - Check for auth-related console errors
5. Report success or failure to user
```

**IMPORTANT:** Use the full `.auth-state.json` file (like Playwright tests), not just the token. This includes:
- localStorage (including auth token)
- sessionStorage
- Cookies
- IndexedDB (if any)

**Why Full State?** Injecting only the token into localStorage is insufficient. The router and authentication system may rely on cookies or other storage that's included in the full auth state.

## Token Validation

**JWT Token Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": 123,
    "broker_connection_id": 456,
    "exp": 1704067200  // Unix timestamp
  }
}
```

**Check Expiry:**
```javascript
const payload = JSON.parse(atob(token.split('.')[1]));
const isExpired = payload.exp * 1000 < Date.now();
```

## Error Handling

### Token File Missing
```
Error: Auth token file not found at tests/config/.auth-token

Solution:
1. Prompt user: "I need to authenticate. Please provide your TOTP code."
2. Perform fresh Kite OAuth login
3. Save token to tests/config/.auth-token
```

### Token Expired
```
Error: Auth token expired

Solution:
1. Inform user: "Your auth token has expired"
2. Ask: "Please provide your TOTP code to re-authenticate"
3. Perform fresh Kite OAuth login
4. Overwrite tests/config/.auth-token with new token
```

### Frontend Not Running
```
Error: Failed to navigate to localhost:5173 (connection refused)

Solution:
1. Check if frontend is running
2. Inform user: "Frontend is not running. Please start it with: cd frontend && npm run dev"
3. Wait for user confirmation
4. Retry
```

### Backend Not Running
```
Error: Authentication failed (cannot reach backend)

Solution:
1. Check if backend is reachable at localhost:8000
2. Inform user: "Backend is not running. Please start it with: cd backend && python run.py"
3. Wait for user confirmation
4. Retry
```

### Authentication Failed After Token Injection
```
Error: Token injection succeeded but still redirected to login

Possible causes:
1. Token is invalid or malformed
2. Backend session expired
3. CORS or cookie issues

Solution:
1. Perform fresh login with TOTP
2. Save new token
3. Retry
```

## Full Example Workflow

### Scenario: User runs `/open-in-chrome /positions`

**Step-by-step execution:**

1. **Check prerequisites:**
   ```
   Checking if backend is running... ✓
   Checking if frontend is running... ✓
   Checking Chrome connection... ✓
   ```

2. **Get auth token:**
   ```
   Reading token from tests/config/.auth-token... ✓
   Validating token... ✓ (expires in 6 hours)
   ```

3. **Open with authentication:**
   ```
   Navigating to localhost:5173/positions...
   Injecting auth token into localStorage...
   Refreshing page...
   Verifying authentication... ✓
   ```

4. **Report success:**
   ```
   ✓ Successfully opened Positions page in Chrome
   ✓ Authenticated as user (from token)
   ✓ Ready for manual testing

   You can now:
   - Test exit/add position modals
   - Verify live P&L updates
   - Check WebSocket connection
   ```

## Integration with chrome.helper.cjs

This command uses the utility functions from `tests/e2e/helpers/chrome.helper.cjs`:

```javascript
const chromeHelper = require('./tests/e2e/helpers/chrome.helper.cjs');

// Get full auth state (RECOMMENDED)
const authState = chromeHelper.getAuthState();
const cookies = chromeHelper.getCookiesFromAuthState(authState);

// Also get token for expiry checking
const token = chromeHelper.getAuthToken();
const isExpired = chromeHelper.isTokenExpired(token);

// Generate URL
const url = chromeHelper.getUrl('/positions');  // localhost:5173/positions

// Apply auth state to Playwright page
await page.context().addCookies(cookies);
await chromeHelper.applyAuthState(page, authState);
```

**Key Functions:**
- `getAuthState()` - Read full `.auth-state.json` file
- `getCookiesFromAuthState(authState)` - Extract cookies for browser context
- `applyAuthState(page, authState)` - Apply localStorage and sessionStorage
- `getAuthToken()` - Read token for expiry validation
- `isTokenExpired(token)` - Check if token is expired
- `getUrl(path)` - Generate full URL

## Advanced Usage

### Open multiple screens in tabs
```
/open-in-chrome /strategy /positions /optionchain
```
**Result:** Opens 3 tabs, all authenticated

### Open with specific state
```
/open-in-chrome /strategy?legs=2
```
**Result:** Opens Strategy Builder with query parameters (if supported)

## Notes

- Auth state is shared with Playwright tests (same `.auth-state.json` file)
- Auth token is also available separately in `.auth-token` for expiry checking
- Token has same expiry as backend JWT_EXPIRY_HOURS setting
- Manual testing doesn't affect automated test auth state
- Chrome extension must be connected (`claude --chrome`)
- If auth expires, run `npm test` to refresh the auth state

## Technical Details

### Auth State File Structure

The `.auth-state.json` file contains:

```json
{
  "cookies": [
    { "name": "...", "value": "...", "domain": "...", ... }
  ],
  "origins": [
    {
      "origin": "http://localhost:5173",
      "localStorage": [
        { "name": "token", "value": "eyJ..." }
      ],
      "sessionStorage": []
    }
  ]
}
```

### Why Full Auth State Works

**Token-only approach (FAILED):**
```javascript
// ❌ This causes login redirect
localStorage.setItem('token', token);
```

**Full auth state approach (WORKS):**
```javascript
// ✅ This maintains authentication
await context.addCookies(authState.cookies);
await page.evaluate((items) => {
  items.forEach(item => localStorage.setItem(item.name, item.value));
}, authState.origins[0].localStorage);
```

**Root Cause:** The application's router and authentication guards check for multiple pieces of state (not just localStorage token). The full auth state ensures all necessary authentication artifacts are present.
