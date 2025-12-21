---
name: vue-component-generator
description: Generate Vue 3 components and Pinia stores following AlgoChanakya conventions. Use when creating Vue components, adding frontend features, or creating new views.
---

# Vue Component Generator

Generate Vue 3 components with Pinia stores following AlgoChanakya project patterns.

## When to Use

- User asks to create a Vue component
- User wants to add a new frontend feature
- User needs a new view or page
- User requests component scaffolding
- User wants to create a modal, card, or widget

## Vue 3 + Composition API Patterns

AlgoChanakya uses **Vue 3 Composition API** with `<script setup>` syntax exclusively.

### Component Structure

```vue
<template>
  <!-- Use data-testid attributes for all interactive elements -->
  <div data-testid="myscreen-mycomponent-container">
    <button
      @click="handleClick"
      data-testid="myscreen-mycomponent-submit-button"
    >
      {{ buttonText }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useMyStore } from '@/stores/mystore'

// Props
const props = defineProps({
  title: {
    type: String,
    required: true
  },
  count: {
    type: Number,
    default: 0
  },
  options: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['submit', 'cancel', 'update:modelValue'])

// Store
const myStore = useMyStore()
const { data, isLoading } = storeToRefs(myStore)

// Reactive state
const localValue = ref('')
const isOpen = ref(false)

// Computed
const buttonText = computed(() => {
  return isLoading.value ? 'Loading...' : 'Submit'
})

// Methods
const handleClick = () => {
  emit('submit', localValue.value)
}

const handleCancel = () => {
  emit('cancel')
  isOpen.value = false
}

// Lifecycle
onMounted(() => {
  // Initialize component
  myStore.fetchData()
})
</script>

<style scoped>
/* Use Tailwind CSS utility classes in template when possible */
/* Only add scoped styles for custom styling not covered by Tailwind */
</style>
```

---

## Pinia Store Patterns

AlgoChanakya uses **setup-style stores** (NOT options-style).

### Store Structure

```javascript
// stores/mystore.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useMyStore = defineStore('mystore', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const items = ref([])
  const currentItem = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // ============================================================================
  // GETTERS (Computed)
  // ============================================================================

  const activeItems = computed(() => {
    return items.value.filter(item => item.active)
  })

  const itemCount = computed(() => items.value.length)

  // ============================================================================
  // ACTIONS
  // ============================================================================

  async function fetchItems() {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.get('/api/items')
      items.value = response.data
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch items'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function createItem(data) {
    try {
      const response = await api.post('/api/items', data)
      items.value.push(response.data)
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create item'
      return { success: false, error: error.value }
    }
  }

  async function updateItem(itemId, data) {
    try {
      const response = await api.put(`/api/items/${itemId}`, data)
      const index = items.value.findIndex(item => item.id === itemId)
      if (index !== -1) {
        items.value[index] = response.data
      }
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update item'
      return { success: false, error: error.value }
    }
  }

  async function deleteItem(itemId) {
    try {
      await api.delete(`/api/items/${itemId}`)
      items.value = items.value.filter(item => item.id !== itemId)
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete item'
      return { success: false, error: error.value }
    }
  }

  function setCurrentItem(item) {
    currentItem.value = item
  }

  function clearError() {
    error.value = null
  }

  // ============================================================================
  // RETURN (Public API)
  // ============================================================================

  return {
    // State
    items,
    currentItem,
    isLoading,
    error,

    // Getters
    activeItems,
    itemCount,

    // Actions
    fetchItems,
    createItem,
    updateItem,
    deleteItem,
    setCurrentItem,
    clearError
  }
})
```

---

## data-testid Convention

**CRITICAL:** All interactive elements MUST have `data-testid` attributes.

**Convention:** `[screen]-[component]-[element]`

**Examples:**
```vue
<!-- Screen: Positions, Component: ExitModal -->
<div data-testid="positions-exit-modal">
  <input data-testid="positions-exit-modal-price-input" />
  <select data-testid="positions-exit-modal-type-dropdown">
    <option data-testid="positions-exit-modal-type-option-market">Market</option>
  </select>
  <button data-testid="positions-exit-modal-submit-button">Exit</button>
  <button data-testid="positions-exit-modal-cancel-button">Cancel</button>
</div>
```

See [data-testid-conventions.md](./references/data-testid-conventions.md) for complete guide.

---

## API Integration

### Import API Service

```javascript
import api from '@/services/api'
```

### API Calls in Stores

**GET Request:**
```javascript
const response = await api.get('/api/endpoint')
const data = response.data
```

**GET with Query Params:**
```javascript
const response = await api.get('/api/endpoint', {
  params: { page: 1, limit: 20, filter: 'active' }
})
```

**POST Request:**
```javascript
const response = await api.post('/api/endpoint', {
  name: 'Example',
  value: 123
})
```

**PUT Request:**
```javascript
const response = await api.put(`/api/endpoint/${id}`, updateData)
```

**DELETE Request:**
```javascript
await api.delete(`/api/endpoint/${id}`)
```

### Error Handling Pattern

```javascript
try {
  const response = await api.get('/api/endpoint')
  // Success
  return { success: true, data: response.data }
} catch (err) {
  error.value = err.response?.data?.detail || 'Operation failed'
  return { success: false, error: error.value }
}
```

---

## Trading Constants Integration

**NEVER hardcode** lot sizes, strike steps, or index tokens.

```javascript
import { getLotSize, getStrikeStep, getIndexToken } from '@/constants/trading'

// In component or store
const underlying = ref('NIFTY')
const lotSize = computed(() => getLotSize(underlying.value))  // 25
const strikeStep = computed(() => getStrikeStep(underlying.value))  // 100

// Calculate total quantity
const totalQuantity = computed(() => {
  const lots = 3
  return lots * lotSize.value  // 75
})
```

See [trading-constants-reference.md](./references/trading-constants-reference.md) for complete guide.

---

## Component Templates

### Modal Component

```vue
<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 overflow-y-auto"
      data-testid="myscreen-mymodal"
    >
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        @click="handleClose"
        data-testid="myscreen-mymodal-backdrop"
      ></div>

      <!-- Modal -->
      <div class="flex min-h-screen items-center justify-center p-4">
        <div
          class="relative bg-white rounded-lg shadow-xl max-w-2xl w-full"
          @click.stop
          data-testid="myscreen-mymodal-container"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b">
            <h2 class="text-xl font-semibold">{{ title }}</h2>
            <button
              @click="handleClose"
              class="text-gray-400 hover:text-gray-600"
              data-testid="myscreen-mymodal-close-button"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="px-6 py-4">
            <slot></slot>
          </div>

          <!-- Footer -->
          <div class="flex justify-end space-x-3 px-6 py-4 border-t bg-gray-50">
            <button
              @click="handleClose"
              class="px-4 py-2 text-gray-700 bg-white border rounded-lg hover:bg-gray-50"
              data-testid="myscreen-mymodal-cancel-button"
            >
              Cancel
            </button>
            <button
              @click="handleSubmit"
              class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              :disabled="isSubmitting"
              data-testid="myscreen-mymodal-submit-button"
            >
              {{ submitText }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: 'Modal'
  },
  submitText: {
    type: String,
    default: 'Submit'
  }
})

const emit = defineEmits(['close', 'submit'])

const isSubmitting = ref(false)

const handleClose = () => {
  emit('close')
}

const handleSubmit = async () => {
  isSubmitting.value = true
  try {
    await emit('submit')
  } finally {
    isSubmitting.value = false
  }
}
</script>
```

### Card Component

```vue
<template>
  <div
    class="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
    data-testid="myscreen-mycard"
  >
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold">{{ title }}</h3>
      <slot name="actions"></slot>
    </div>

    <!-- Content -->
    <div class="space-y-4">
      <slot></slot>
    </div>

    <!-- Footer -->
    <div v-if="$slots.footer" class="mt-4 pt-4 border-t">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  }
})
</script>
```

---

## View Component Pattern

```vue
<template>
  <div class="container mx-auto px-4 py-6" data-testid="myscreen-view">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">My Screen</h1>
      <button
        @click="handleCreate"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg"
        data-testid="myscreen-view-create-button"
      >
        Create New
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-red-600">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="items.length === 0"
      class="text-center py-12"
      data-testid="myscreen-view-empty-state"
    >
      <p class="text-gray-500">No items found</p>
    </div>

    <!-- Content -->
    <div v-else class="space-y-4">
      <MyCard
        v-for="item in items"
        :key="item.id"
        :title="item.name"
        data-testid="myscreen-view-item-card"
      >
        <p>{{ item.description }}</p>
      </MyCard>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useMyStore } from '@/stores/mystore'
import MyCard from '@/components/MyCard.vue'

const myStore = useMyStore()
const { items, isLoading, error } = storeToRefs(myStore)

const handleCreate = () => {
  // Navigate to create page or open modal
}

onMounted(async () => {
  await myStore.fetchItems()
})
</script>
```

---

## Composable Functions

For reusable logic, create composables in `src/composables/`:

```javascript
// composables/useForm.js
import { ref, computed } from 'vue'

export function useForm(initialValues = {}) {
  const values = ref({ ...initialValues })
  const errors = ref({})
  const touched = ref({})

  const isValid = computed(() => {
    return Object.keys(errors.value).length === 0
  })

  const setFieldValue = (field, value) => {
    values.value[field] = value
    touched.value[field] = true
  }

  const setFieldError = (field, error) => {
    if (error) {
      errors.value[field] = error
    } else {
      delete errors.value[field]
    }
  }

  const reset = () => {
    values.value = { ...initialValues }
    errors.value = {}
    touched.value = {}
  }

  return {
    values,
    errors,
    touched,
    isValid,
    setFieldValue,
    setFieldError,
    reset
  }
}
```

**Usage:**
```vue
<script setup>
import { useForm } from '@/composables/useForm'

const { values, errors, isValid, setFieldValue } = useForm({
  name: '',
  email: ''
})
</script>
```

---

## Best Practices

1. **Use Composition API** - Always use `<script setup>` syntax
2. **Add data-testid** - Every interactive element needs `data-testid`
3. **Type Props** - Always define prop types with defaults
4. **Use Stores** - Don't put API logic in components, use Pinia stores
5. **Import Constants** - Never hardcode trading parameters
6. **Error Handling** - Always handle API errors in try-catch
7. **Loading States** - Show loading indicators for async operations
8. **Empty States** - Handle empty data with meaningful messages
9. **Tailwind First** - Use Tailwind utility classes, avoid custom CSS when possible
10. **Accessibility** - Use semantic HTML and ARIA attributes where needed

---

## Common Anti-Patterns

### ❌ WRONG - Options API

```vue
<script>
export default {
  data() {
    return { count: 0 }
  },
  methods: {
    increment() {
      this.count++
    }
  }
}
</script>
```

### ✅ RIGHT - Composition API

```vue
<script setup>
import { ref } from 'vue'

const count = ref(0)

const increment = () => {
  count.value++
}
</script>
```

---

### ❌ WRONG - API Logic in Component

```vue
<script setup>
import api from '@/services/api'

const items = ref([])

const fetchItems = async () => {
  const response = await api.get('/api/items')
  items.value = response.data
}
</script>
```

### ✅ RIGHT - Use Pinia Store

```vue
<script setup>
import { storeToRefs } from 'pinia'
import { useMyStore } from '@/stores/mystore'

const myStore = useMyStore()
const { items } = storeToRefs(myStore)

onMounted(() => {
  myStore.fetchItems()
})
</script>
```

---

### ❌ WRONG - Hardcoded Constants

```vue
<script setup>
const lotSize = 25  // Hardcoded!
</script>
```

### ✅ RIGHT - Import from Constants

```vue
<script setup>
import { getLotSize } from '@/constants/trading'

const underlying = ref('NIFTY')
const lotSize = computed(() => getLotSize(underlying.value))
</script>
```

---

### ❌ WRONG - Missing data-testid

```vue
<template>
  <button @click="submit">Submit</button>
</template>
```

### ✅ RIGHT - With data-testid

```vue
<template>
  <button
    @click="submit"
    data-testid="myscreen-mycomponent-submit-button"
  >
    Submit
  </button>
</template>
```

---

## References

- [Component Templates](./references/component-templates.md) - Complete component examples
- [Store Templates](./references/store-templates.md) - Pinia store patterns
- [data-testid Conventions](./references/data-testid-conventions.md) - Naming guide
- [Trading Constants Reference](./references/trading-constants-reference.md) - Using trading constants

---

## Checklist

Before committing a new component:

- [ ] Uses `<script setup>` syntax
- [ ] All props have type definitions
- [ ] All emits are declared with `defineEmits()`
- [ ] All interactive elements have `data-testid` attributes
- [ ] Uses Pinia store for API calls (not component-level)
- [ ] Trading constants imported (never hardcoded)
- [ ] Error handling for async operations
- [ ] Loading and empty states handled
- [ ] Tailwind CSS classes used (minimal custom CSS)
- [ ] Component is properly exported and imported
