---
name: vitest-generator
description: Generate Vitest unit tests for Vue components, Pinia stores, and composables. Do NOT use this for E2E tests (use e2e-test-generator) or fixing failing tests (use test-fixer). Use when adding unit tests, test coverage, or writing Vitest tests in AlgoChanakya.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Vitest Generator

Generate Vitest unit tests following AlgoChanakya testing patterns.

## When to Use

- User asks to add unit tests
- User wants to test a Vue component
- User needs to test a Pinia store
- User wants to test a composable function
- User requests test coverage
- User asks to write Vitest tests

## When NOT to Use

- Generating E2E tests (use e2e-test-generator for Playwright tests)
- Fixing existing failing tests (use test-fixer for that)

---

## Vitest Configuration

AlgoChanakya uses:
- **Test Runner:** Vitest (fast, Vite-native test runner)
- **Environment:** happy-dom (lightweight DOM implementation)
- **Utilities:** @vue/test-utils for component testing
- **Mocking:** Vitest's built-in mocking (`vi.mock`, `vi.fn`)

**Config:** `frontend/vite.config.js` (test section)

---

## Test Structure

### Organized with Describe Blocks

```javascript
import { describe, it, expect, beforeEach } from 'vitest'

// ===================================================================
// INITIAL STATE TESTS
// ===================================================================
describe('MyComponent - Initial State', () => {
  beforeEach(() => {
    // Setup
  })

  it('initializes with default props', () => {
    // Test
  })
})

// ===================================================================
// COMPUTED PROPERTIES TESTS
// ===================================================================
describe('MyComponent - Computed Properties', () => {
  // Tests
})

// ===================================================================
// METHOD TESTS
// ===================================================================
describe('MyComponent - Methods', () => {
  // Tests
})

// ===================================================================
// ERROR HANDLING TESTS
// ===================================================================
describe('MyComponent - Error Handling', () => {
  // Tests
})
```

---

## Testing Pinia Stores

### Setup Pattern

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMyStore } from '@/stores/mystore'

// Mock API module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

import api from '@/services/api'

// Test data
const mockItem = {
  id: 1,
  name: 'Test Item',
  active: true
}

describe('MyStore - Initial State', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with default state', () => {
    const store = useMyStore()

    expect(store.items).toEqual([])
    expect(store.currentItem).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.error).toBeNull()
  })
})
```

---

### Testing Store Getters

```javascript
describe('MyStore - Getters', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useMyStore()
    vi.clearAllMocks()
  })

  describe('activeItems', () => {
    it('returns only active items', () => {
      store.items = [
        { id: 1, name: 'Active 1', active: true },
        { id: 2, name: 'Inactive', active: false },
        { id: 3, name: 'Active 2', active: true }
      ]

      expect(store.activeItems).toHaveLength(2)
      expect(store.activeItems.map(i => i.id)).toEqual([1, 3])
    })

    it('returns empty array when no active items', () => {
      store.items = [
        { id: 1, active: false },
        { id: 2, active: false }
      ]

      expect(store.activeItems).toHaveLength(0)
    })
  })

  describe('itemById', () => {
    it('returns item with matching ID', () => {
      store.items = [
        { id: 1, name: 'First' },
        { id: 2, name: 'Second' }
      ]

      expect(store.itemById(1)).toEqual({ id: 1, name: 'First' })
    })

    it('returns undefined for non-existent ID', () => {
      store.items = [{ id: 1, name: 'First' }]

      expect(store.itemById(999)).toBeUndefined()
    })
  })
})
```

---

### Testing Store Actions

```javascript
describe('MyStore - Actions', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useMyStore()
    vi.clearAllMocks()
  })

  describe('fetchItems', () => {
    it('fetches items successfully', async () => {
      const mockResponse = {
        data: [mockItem, { id: 2, name: 'Item 2' }]
      }
      api.get.mockResolvedValue(mockResponse)

      await store.fetchItems()

      expect(api.get).toHaveBeenCalledWith('/api/items')
      expect(store.items).toEqual(mockResponse.data)
      expect(store.isLoading).toBe(false)
    })

    it('sets loading during fetch', async () => {
      api.get.mockImplementation(() => new Promise(() => {}))  // Never resolves

      store.fetchItems()
      expect(store.isLoading).toBe(true)
    })

    it('handles fetch error', async () => {
      const errorResponse = {
        response: { data: { detail: 'Server error' } }
      }
      api.get.mockRejectedValue(errorResponse)

      await expect(store.fetchItems()).rejects.toEqual(errorResponse)
      expect(store.error).toBe('Server error')
      expect(store.isLoading).toBe(false)
    })

    it('applies filters to request', async () => {
      api.get.mockResolvedValue({ data: [] })

      await store.fetchItems({ status: 'active' })

      expect(api.get).toHaveBeenCalledWith('/api/items', {
        params: { status: 'active' }
      })
    })
  })

  describe('createItem', () => {
    it('creates item successfully', async () => {
      api.post.mockResolvedValue({ data: mockItem })

      await store.createItem({ name: 'New Item' })

      expect(api.post).toHaveBeenCalledWith('/api/items', { name: 'New Item' })
      expect(store.items[0]).toEqual(mockItem)
    })

    it('sets saving during create', async () => {
      api.post.mockImplementation(() => new Promise(() => {}))

      store.createItem({ name: 'Test' })
      expect(store.saving).toBe(true)
    })

    it('handles create error', async () => {
      api.post.mockRejectedValue({
        response: { data: { detail: 'Validation error' } }
      })

      await expect(store.createItem({})).rejects.toBeDefined()
      expect(store.error).toBe('Validation error')
    })
  })

  describe('updateItem', () => {
    it('updates item successfully', async () => {
      store.items = [{ ...mockItem }]
      const updatedItem = { ...mockItem, name: 'Updated Name' }
      api.put.mockResolvedValue({ data: updatedItem })

      await store.updateItem(1, { name: 'Updated Name' })

      expect(api.put).toHaveBeenCalledWith('/api/items/1', { name: 'Updated Name' })
      expect(store.items[0].name).toBe('Updated Name')
    })

    it('updates currentItem if same ID', async () => {
      store.currentItem = { ...mockItem }
      store.items = [{ ...mockItem }]
      const updatedItem = { ...mockItem, name: 'Updated' }
      api.put.mockResolvedValue({ data: updatedItem })

      await store.updateItem(1, { name: 'Updated' })

      expect(store.currentItem.name).toBe('Updated')
    })
  })

  describe('deleteItem', () => {
    it('deletes item successfully', async () => {
      store.items = [mockItem, { id: 2, name: 'Item 2' }]
      api.delete.mockResolvedValue({})

      await store.deleteItem(1)

      expect(api.delete).toHaveBeenCalledWith('/api/items/1')
      expect(store.items).toHaveLength(1)
      expect(store.items[0].id).toBe(2)
    })

    it('clears currentItem if same ID', async () => {
      store.currentItem = { ...mockItem }
      store.items = [mockItem]
      api.delete.mockResolvedValue({})

      await store.deleteItem(1)

      expect(store.currentItem).toBeNull()
    })
  })
})
```

---

## Testing Vue Components

### Component Setup

```javascript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MyComponent from '@/components/MyComponent.vue'

describe('MyComponent', () => {
  let wrapper
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  it('renders with default props', () => {
    wrapper = mount(MyComponent, {
      global: {
        plugins: [pinia]
      },
      props: {
        title: 'Test Title'
      }
    })

    expect(wrapper.text()).toContain('Test Title')
  })
})
```

---

### Testing Props

```javascript
describe('MyComponent - Props', () => {
  it('displays title prop', () => {
    wrapper = mount(MyComponent, {
      props: { title: 'Test Title' }
    })

    expect(wrapper.text()).toContain('Test Title')
  })

  it('uses default prop value', () => {
    wrapper = mount(MyComponent, {
      props: { title: 'Test' }
    })

    // component has default count=0
    expect(wrapper.vm.count).toBe(0)
  })

  it('validates required props', () => {
    // This would throw validation warning
    wrapper = mount(MyComponent, {
      props: {}  // Missing required prop
    })
  })
})
```

---

### Testing Emits

```javascript
describe('MyComponent - Emits', () => {
  it('emits submit event with data', async () => {
    wrapper = mount(MyComponent, {
      props: { title: 'Test' }
    })

    const button = wrapper.find('[data-testid="mycomponent-submit-button"]')
    await button.trigger('click')

    expect(wrapper.emitted('submit')).toBeTruthy()
    expect(wrapper.emitted('submit')[0]).toEqual([{ name: 'test' }])
  })

  it('emits update:modelValue on input change', async () => {
    wrapper = mount(MyComponent, {
      props: { modelValue: 'initial' }
    })

    const input = wrapper.find('[data-testid="mycomponent-input"]')
    await input.setValue('new value')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['new value'])
  })

  it('emits cancel event without data', async () => {
    wrapper = mount(MyComponent)

    const button = wrapper.find('[data-testid="mycomponent-cancel-button"]')
    await button.trigger('click')

    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('cancel')[0]).toEqual([])
  })
})
```

---

### Testing Computed Properties

```javascript
describe('MyComponent - Computed', () => {
  it('calculates total correctly', () => {
    wrapper = mount(MyComponent, {
      props: { price: 100, quantity: 3 }
    })

    expect(wrapper.vm.total).toBe(300)
  })

  it('filters active items', () => {
    wrapper = mount(MyComponent, {
      props: {
        items: [
          { id: 1, active: true },
          { id: 2, active: false },
          { id: 3, active: true }
        ]
      }
    })

    expect(wrapper.vm.activeItems).toHaveLength(2)
  })
})
```

---

### Testing User Interactions

```javascript
describe('MyComponent - User Interactions', () => {
  it('increments counter on button click', async () => {
    wrapper = mount(MyComponent)

    const button = wrapper.find('[data-testid="mycomponent-increment-button"]')
    await button.trigger('click')
    await button.trigger('click')

    expect(wrapper.vm.count).toBe(2)
    expect(wrapper.text()).toContain('2')
  })

  it('updates input value', async () => {
    wrapper = mount(MyComponent)

    const input = wrapper.find('[data-testid="mycomponent-name-input"]')
    await input.setValue('New Name')

    expect(wrapper.vm.name).toBe('New Name')
  })

  it('toggles checkbox', async () => {
    wrapper = mount(MyComponent)

    const checkbox = wrapper.find('[data-testid="mycomponent-active-checkbox"]')
    await checkbox.setChecked(true)

    expect(wrapper.vm.isActive).toBe(true)
  })

  it('selects dropdown option', async () => {
    wrapper = mount(MyComponent)

    const select = wrapper.find('[data-testid="mycomponent-type-dropdown"]')
    await select.setValue('option2')

    expect(wrapper.vm.selectedType).toBe('option2')
  })
})
```

---

## Testing Composables

### Basic Composable Test

```javascript
import { describe, it, expect } from 'vitest'
import { useCounter } from '@/composables/useCounter'

describe('useCounter', () => {
  it('initializes with default value', () => {
    const { count } = useCounter()
    expect(count.value).toBe(0)
  })

  it('initializes with custom value', () => {
    const { count } = useCounter(10)
    expect(count.value).toBe(10)
  })

  it('increments counter', () => {
    const { count, increment } = useCounter(5)
    increment()
    expect(count.value).toBe(6)
  })

  it('decrements counter', () => {
    const { count, decrement } = useCounter(5)
    decrement()
    expect(count.value).toBe(4)
  })

  it('resets counter to initial value', () => {
    const { count, increment, reset } = useCounter(5)
    increment()
    increment()
    reset()
    expect(count.value).toBe(5)
  })
})
```

---

### Testing WebSocket Composable

```javascript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useWebSocket } from '@/composables/useWebSocket'

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1

  constructor(url) {
    this.url = url
    this.readyState = MockWebSocket.OPEN
    this.sentMessages = []
  }

  send(data) {
    this.sentMessages.push(data)
  }

  close() {
    this.readyState = 3
  }
}

describe('useWebSocket', () => {
  let originalWebSocket

  beforeEach(() => {
    originalWebSocket = global.WebSocket
    global.WebSocket = MockWebSocket
    localStorage.setItem('access_token', 'test_token')
  })

  afterEach(() => {
    global.WebSocket = originalWebSocket
    localStorage.clear()
  })

  it('connects with correct URL', () => {
    const { connect } = useWebSocket()
    connect()
    // Test connection logic
  })

  it('sends messages when connected', () => {
    const { connect, send } = useWebSocket()
    connect()
    send('ping', {})
    // Test message sending
  })
})
```

---

## Mocking Patterns

### Mocking API Module

```javascript
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

import api from '@/services/api'

// In test:
api.get.mockResolvedValue({ data: mockData })
api.post.mockRejectedValue(new Error('Failed'))
```

---

### Mocking Pinia Store

```javascript
import { vi } from 'vitest'

vi.mock('@/stores/mystore', () => ({
  useMyStore: vi.fn(() => ({
    items: [],
    fetchItems: vi.fn(),
    isLoading: false
  }))
}))

import { useMyStore } from '@/stores/mystore'

// In test:
const mockStore = useMyStore()
mockStore.fetchItems.mockResolvedValue({ success: true })
```

---

### Mocking Router

```javascript
import { vi } from 'vitest'

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  currentRoute: { value: { name: 'home' } }
}

vi.mock('vue-router', () => ({
  useRouter: () => mockRouter,
  useRoute: () => mockRouter.currentRoute.value
}))
```

---

### Mocking localStorage

```javascript
beforeEach(() => {
  // Mock localStorage
  global.localStorage = {
    store: {},
    getItem(key) {
      return this.store[key] || null
    },
    setItem(key, value) {
      this.store[key] = String(value)
    },
    removeItem(key) {
      delete this.store[key]
    },
    clear() {
      this.store = {}
    }
  }
})
```

---

## Testing Async Operations

### Using Fake Timers

```javascript
import { vi } from 'vitest'

describe('Async Operations', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('calls function after delay', async () => {
    const callback = vi.fn()

    setTimeout(callback, 1000)

    await vi.advanceTimersByTimeAsync(1000)

    expect(callback).toHaveBeenCalled()
  })

  it('runs all pending timers', async () => {
    const callback1 = vi.fn()
    const callback2 = vi.fn()

    setTimeout(callback1, 1000)
    setTimeout(callback2, 2000)

    await vi.runAllTimersAsync()

    expect(callback1).toHaveBeenCalled()
    expect(callback2).toHaveBeenCalled()
  })
})
```

---

### Testing Promises

```javascript
it('resolves promise successfully', async () => {
  const promise = store.fetchItems()

  await expect(promise).resolves.toBeDefined()
})

it('rejects promise with error', async () => {
  api.get.mockRejectedValue(new Error('Failed'))

  await expect(store.fetchItems()).rejects.toThrow('Failed')
})
```

---

## Common Assertions

```javascript
// Equality
expect(value).toBe(expected)  // Strict equality
expect(value).toEqual(expected)  // Deep equality
expect(value).not.toBe(expected)

// Truthiness
expect(value).toBeTruthy()
expect(value).toBeFalsy()
expect(value).toBeNull()
expect(value).toBeUndefined()
expect(value).toBeDefined()

// Numbers
expect(number).toBeGreaterThan(3)
expect(number).toBeLessThan(10)
expect(number).toBeGreaterThanOrEqual(5)
expect(number).toBeLessThanOrEqual(8)
expect(number).toBeCloseTo(0.3)  // For floating point

// Strings
expect(string).toMatch(/pattern/)
expect(string).toContain('substring')

// Arrays
expect(array).toHaveLength(5)
expect(array).toContain(item)
expect(array).toEqual([1, 2, 3])

// Objects
expect(object).toHaveProperty('key')
expect(object).toHaveProperty('key', value)
expect(object).toMatchObject({ key: value })

// Functions
expect(fn).toHaveBeenCalled()
expect(fn).toHaveBeenCalledTimes(2)
expect(fn).toHaveBeenCalledWith(arg1, arg2)
expect(fn).toHaveBeenLastCalledWith(arg1, arg2)
```

---

## Running Tests

```bash
# Run all tests
npm run test

# Run in watch mode
npm run test

# Run once (no watch)
npm run test:run

# Run with coverage
npm run test:coverage

# Run specific test file
npm run test tests/stores/mystore.test.js
```

---

## Best Practices

1. **Organize with Describe Blocks** - Group related tests
2. **Use beforeEach/afterEach** - Setup/teardown for each test
3. **Clear Mocks** - Always clear mocks in beforeEach
4. **Test One Thing** - Each test should test one behavior
5. **Descriptive Names** - Use clear, descriptive test names
6. **Arrange-Act-Assert** - Structure tests clearly
7. **Mock External Dependencies** - Isolate unit under test
8. **Test Happy & Sad Paths** - Test both success and error cases
9. **Use Fake Timers** - For time-dependent tests
10. **Avoid Test Interdependence** - Tests should be independent

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `ReferenceError: setActivePinia is not defined` | Missing import | Add `import { setActivePinia, createPinia } from 'pinia'` |
| Mock not resetting between tests | Missing `vi.clearAllMocks()` | Add `vi.clearAllMocks()` in `beforeEach()` |
| Test fails with wrong environment | Using wrong test environment | Check `vite.config.js` has `environment: 'happy-dom'` |
| Store state persists across tests | Pinia not reset | Call `setActivePinia(createPinia())` in `beforeEach()` |
| API mock not working | Mock defined after import | Define `vi.mock()` BEFORE importing the mocked module |

---

## References

- [Test Patterns](./references/test-patterns.md) - Complete test examples

---

## Checklist

Before committing tests:

- [ ] Tests are in `tests/` directory with `.test.js` extension
- [ ] Imports use `@/` alias for src files
- [ ] All mocks are cleared in beforeEach
- [ ] Tests cover happy path and error cases
- [ ] Async operations use await
- [ ] Component tests use mount/shallowMount correctly
- [ ] Store tests use setActivePinia
- [ ] Tests are isolated and independent
- [ ] Descriptive test names used
- [ ] Coverage meets project standards
