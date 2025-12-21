# Vue Component Templates

Complete component examples for common patterns in AlgoChanakya.

---

## Modal Component with Form

```vue
<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 overflow-y-auto"
      data-testid="myscreen-form-modal"
    >
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        @click="handleClose"
        data-testid="myscreen-form-modal-backdrop"
      ></div>

      <!-- Modal Dialog -->
      <div class="flex min-h-screen items-center justify-center p-4">
        <div
          class="relative bg-white rounded-lg shadow-xl max-w-lg w-full"
          @click.stop
          data-testid="myscreen-form-modal-container"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b">
            <h2 class="text-xl font-semibold">{{ title }}</h2>
            <button
              @click="handleClose"
              class="text-gray-400 hover:text-gray-600"
              data-testid="myscreen-form-modal-close-button"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <form @submit.prevent="handleSubmit" class="px-6 py-4 space-y-4">
            <!-- Name Input -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                v-model="formData.name"
                type="text"
                class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                :class="{ 'border-red-500': errors.name }"
                data-testid="myscreen-form-modal-name-input"
                required
              />
              <p v-if="errors.name" class="text-red-500 text-sm mt-1">
                {{ errors.name }}
              </p>
            </div>

            <!-- Description Textarea -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                v-model="formData.description"
                class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                rows="3"
                data-testid="myscreen-form-modal-description-textarea"
              ></textarea>
            </div>

            <!-- Select Dropdown -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                v-model="formData.category"
                class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                data-testid="myscreen-form-modal-category-dropdown"
              >
                <option value="" data-testid="myscreen-form-modal-category-option-empty">
                  Select category
                </option>
                <option
                  v-for="cat in categories"
                  :key="cat.value"
                  :value="cat.value"
                  :data-testid="`myscreen-form-modal-category-option-${cat.value}`"
                >
                  {{ cat.label }}
                </option>
              </select>
            </div>

            <!-- Checkbox -->
            <div class="flex items-center">
              <input
                v-model="formData.active"
                type="checkbox"
                class="h-4 w-4 text-blue-600 rounded"
                data-testid="myscreen-form-modal-active-checkbox"
              />
              <label class="ml-2 text-sm text-gray-700">
                Active
              </label>
            </div>

            <!-- Error Message -->
            <div v-if="submitError" class="bg-red-50 border border-red-200 rounded-lg p-3">
              <p class="text-red-600 text-sm">{{ submitError }}</p>
            </div>

            <!-- Footer Buttons -->
            <div class="flex justify-end space-x-3 pt-4 border-t">
              <button
                type="button"
                @click="handleClose"
                class="px-4 py-2 text-gray-700 bg-white border rounded-lg hover:bg-gray-50"
                data-testid="myscreen-form-modal-cancel-button"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                :disabled="isSubmitting"
                data-testid="myscreen-form-modal-submit-button"
              >
                {{ isSubmitting ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: 'Form'
  },
  initialData: {
    type: Object,
    default: () => ({})
  },
  categories: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const formData = ref({
  name: '',
  description: '',
  category: '',
  active: true,
  ...props.initialData
})

const errors = ref({})
const submitError = ref(null)
const isSubmitting = ref(false)

watch(() => props.initialData, (newData) => {
  formData.value = { ...formData.value, ...newData }
}, { deep: true })

const handleClose = () => {
  emit('update:modelValue', false)
  resetForm()
}

const resetForm = () => {
  formData.value = {
    name: '',
    description: '',
    category: '',
    active: true
  }
  errors.value = {}
  submitError.value = null
}

const handleSubmit = async () => {
  errors.value = {}
  submitError.value = null

  // Validation
  if (!formData.value.name.trim()) {
    errors.value.name = 'Name is required'
    return
  }

  isSubmitting.value = true

  try {
    await emit('submit', formData.value)
    handleClose()
  } catch (err) {
    submitError.value = err.message || 'Failed to save'
  } finally {
    isSubmitting.value = false
  }
}
</script>
```

---

## Data Table Component

```vue
<template>
  <div class="bg-white rounded-lg shadow" data-testid="myscreen-table">
    <!-- Table Header -->
    <div class="px-6 py-4 border-b flex items-center justify-between">
      <h2 class="text-lg font-semibold">{{ title }}</h2>
      <div class="flex items-center space-x-3">
        <!-- Search -->
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search..."
          class="px-3 py-2 border rounded-lg text-sm"
          data-testid="myscreen-table-search-input"
        />
        <!-- Refresh Button -->
        <button
          @click="emit('refresh')"
          class="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          data-testid="myscreen-table-refresh-button"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="w-full">
        <thead class="bg-gray-50 border-b">
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              {{ column.label }}
            </th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <!-- Loading State -->
          <tr v-if="isLoading">
            <td :colspan="columns.length + 1" class="px-6 py-12 text-center">
              <div class="flex justify-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            </td>
          </tr>

          <!-- Empty State -->
          <tr v-else-if="filteredRows.length === 0">
            <td :colspan="columns.length + 1" class="px-6 py-12 text-center text-gray-500">
              No data found
            </td>
          </tr>

          <!-- Data Rows -->
          <tr
            v-else
            v-for="(row, index) in filteredRows"
            :key="row.id || index"
            class="hover:bg-gray-50"
            :data-testid="`myscreen-table-row-${index}`"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-4 whitespace-nowrap text-sm"
            >
              <!-- Use slot for custom cell rendering -->
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
                {{ row[column.key] }}
              </slot>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
              <button
                @click="emit('edit', row)"
                class="text-blue-600 hover:text-blue-800"
                :data-testid="`myscreen-table-row-${index}-edit-button`"
              >
                Edit
              </button>
              <button
                @click="emit('delete', row)"
                class="text-red-600 hover:text-red-800"
                :data-testid="`myscreen-table-row-${index}-delete-button`"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="px-6 py-4 border-t flex items-center justify-between">
      <p class="text-sm text-gray-700">
        Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalRows) }} of {{ totalRows }} results
      </p>
      <div class="flex space-x-2">
        <button
          @click="emit('page-change', currentPage - 1)"
          :disabled="currentPage === 1"
          class="px-3 py-1 border rounded-lg disabled:opacity-50"
          data-testid="myscreen-table-prev-button"
        >
          Previous
        </button>
        <button
          @click="emit('page-change', currentPage + 1)"
          :disabled="currentPage === totalPages"
          class="px-3 py-1 border rounded-lg disabled:opacity-50"
          data-testid="myscreen-table-next-button"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Data Table'
  },
  columns: {
    type: Array,
    required: true  // [{ key: 'name', label: 'Name' }, ...]
  },
  rows: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  currentPage: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 20
  },
  totalRows: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['refresh', 'edit', 'delete', 'page-change'])

const searchQuery = ref('')

const filteredRows = computed(() => {
  if (!searchQuery.value) return props.rows

  const query = searchQuery.value.toLowerCase()
  return props.rows.filter(row => {
    return props.columns.some(col => {
      const value = row[col.key]
      return value && String(value).toLowerCase().includes(query)
    })
  })
})

const totalPages = computed(() => Math.ceil(props.totalRows / props.pageSize))
</script>
```

---

## Card Component with Stats

```vue
<template>
  <div
    class="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
    :class="{ 'border-l-4 border-blue-500': highlighted }"
    data-testid="myscreen-stats-card"
  >
    <!-- Icon and Title -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center space-x-3">
        <div
          class="p-3 rounded-full"
          :class="iconBgClass"
        >
          <slot name="icon">
            <svg class="w-6 h-6" :class="iconClass" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
            </svg>
          </slot>
        </div>
        <h3 class="text-lg font-semibold text-gray-800">{{ title }}</h3>
      </div>

      <!-- Badge -->
      <span
        v-if="badge"
        class="px-2 py-1 text-xs font-semibold rounded-full"
        :class="badgeClass"
      >
        {{ badge }}
      </span>
    </div>

    <!-- Value -->
    <div class="mb-2">
      <p class="text-3xl font-bold" :class="valueClass">
        {{ formattedValue }}
      </p>
      <p v-if="subtitle" class="text-sm text-gray-500 mt-1">
        {{ subtitle }}
      </p>
    </div>

    <!-- Change Indicator -->
    <div v-if="change !== null" class="flex items-center space-x-2">
      <svg
        v-if="change > 0"
        class="w-4 h-4 text-green-600"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
      </svg>
      <svg
        v-else-if="change < 0"
        class="w-4 h-4 text-red-600"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clip-rule="evenodd" />
      </svg>
      <span class="text-sm" :class="changeClass">
        {{ changeText }}
      </span>
    </div>

    <!-- Footer Slot -->
    <div v-if="$slots.footer" class="mt-4 pt-4 border-t">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  subtitle: {
    type: String,
    default: null
  },
  change: {
    type: Number,
    default: null
  },
  badge: {
    type: String,
    default: null
  },
  badgeVariant: {
    type: String,
    default: 'blue'  // 'blue', 'green', 'red', 'yellow'
  },
  valueColor: {
    type: String,
    default: 'default'  // 'default', 'green', 'red'
  },
  iconVariant: {
    type: String,
    default: 'blue'
  },
  highlighted: {
    type: Boolean,
    default: false
  },
  formatValue: {
    type: Function,
    default: (val) => val
  }
})

const formattedValue = computed(() => props.formatValue(props.value))

const valueClass = computed(() => {
  if (props.valueColor === 'green') return 'text-green-600'
  if (props.valueColor === 'red') return 'text-red-600'
  return 'text-gray-900'
})

const changeClass = computed(() => {
  if (props.change > 0) return 'text-green-600'
  if (props.change < 0) return 'text-red-600'
  return 'text-gray-600'
})

const changeText = computed(() => {
  if (props.change === null) return ''
  const sign = props.change > 0 ? '+' : ''
  return `${sign}${props.change.toFixed(2)}%`
})

const badgeClass = computed(() => {
  const variants = {
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    red: 'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800'
  }
  return variants[props.badgeVariant] || variants.blue
})

const iconClass = computed(() => {
  const variants = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    red: 'text-red-600',
    yellow: 'text-yellow-600'
  }
  return variants[props.iconVariant] || variants.blue
})

const iconBgClass = computed(() => {
  const variants = {
    blue: 'bg-blue-100',
    green: 'bg-green-100',
    red: 'bg-red-100',
    yellow: 'bg-yellow-100'
  }
  return variants[props.iconVariant] || variants.blue
})
</script>
```

---

## List with Infinite Scroll

```vue
<template>
  <div
    ref="containerRef"
    class="space-y-3 max-h-screen overflow-y-auto"
    @scroll="handleScroll"
    data-testid="myscreen-infinite-list"
  >
    <div
      v-for="(item, index) in items"
      :key="item.id"
      class="bg-white p-4 rounded-lg shadow hover:shadow-md transition-shadow"
      :data-testid="`myscreen-infinite-list-item-${index}`"
    >
      <slot :item="item" :index="index">
        <p>{{ item.name }}</p>
      </slot>
    </div>

    <!-- Loading Indicator -->
    <div v-if="isLoading" class="flex justify-center py-4">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <!-- End of List -->
    <div v-if="!hasMore && items.length > 0" class="text-center py-4 text-gray-500">
      No more items to load
    </div>

    <!-- Empty State -->
    <div
      v-if="!isLoading && items.length === 0"
      class="text-center py-12 text-gray-500"
      data-testid="myscreen-infinite-list-empty-state"
    >
      <slot name="empty">
        No items found
      </slot>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  hasMore: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['load-more'])

const containerRef = ref(null)

const handleScroll = () => {
  if (!containerRef.value || !props.hasMore || props.isLoading) return

  const { scrollTop, scrollHeight, clientHeight } = containerRef.value

  // Load more when scrolled to 80% of container
  if (scrollTop + clientHeight >= scrollHeight * 0.8) {
    emit('load-more')
  }
}

onMounted(() => {
  if (containerRef.value) {
    containerRef.value.addEventListener('scroll', handleScroll)
  }
})

onBeforeUnmount(() => {
  if (containerRef.value) {
    containerRef.value.removeEventListener('scroll', handleScroll)
  }
})
</script>
```

---

## Toast Notification Component

```vue
<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-50 space-y-2" data-testid="myscreen-toast-container">
      <Transition
        v-for="toast in toasts"
        :key="toast.id"
        name="toast"
        appear
      >
        <div
          class="flex items-center space-x-3 px-4 py-3 rounded-lg shadow-lg max-w-sm"
          :class="toastClass(toast.type)"
          :data-testid="`myscreen-toast-${toast.type}`"
        >
          <!-- Icon -->
          <svg class="w-5 h-5 flex-shrink-0" :class="iconClass(toast.type)" fill="currentColor" viewBox="0 0 20 20">
            <path v-if="toast.type === 'success'" fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            <path v-else-if="toast.type === 'error'" fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            <path v-else fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>

          <!-- Message -->
          <p class="flex-1 text-sm font-medium">{{ toast.message }}</p>

          <!-- Close Button -->
          <button
            @click="removeToast(toast.id)"
            class="text-current opacity-70 hover:opacity-100"
            :data-testid="`myscreen-toast-${toast.type}-close-button`"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </Transition>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const toasts = ref([])
let nextId = 1

const toastClass = (type) => {
  const classes = {
    success: 'bg-green-50 text-green-800 border border-green-200',
    error: 'bg-red-50 text-red-800 border border-red-200',
    warning: 'bg-yellow-50 text-yellow-800 border border-yellow-200',
    info: 'bg-blue-50 text-blue-800 border border-blue-200'
  }
  return classes[type] || classes.info
}

const iconClass = (type) => {
  const classes = {
    success: 'text-green-600',
    error: 'text-red-600',
    warning: 'text-yellow-600',
    info: 'text-blue-600'
  }
  return classes[type] || classes.info
}

const showToast = (message, type = 'info', duration = 3000) => {
  const id = nextId++
  toasts.value.push({ id, message, type })

  if (duration > 0) {
    setTimeout(() => {
      removeToast(id)
    }, duration)
  }
}

const removeToast = (id) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index !== -1) {
    toasts.value.splice(index, 1)
  }
}

defineExpose({
  showToast,
  success: (msg, duration) => showToast(msg, 'success', duration),
  error: (msg, duration) => showToast(msg, 'error', duration),
  warning: (msg, duration) => showToast(msg, 'warning', duration),
  info: (msg, duration) => showToast(msg, 'info', duration)
})
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
```

**Usage:**
```vue
<script setup>
import { ref } from 'vue'
import Toast from '@/components/Toast.vue'

const toastRef = ref(null)

const handleSuccess = () => {
  toastRef.value?.success('Operation completed successfully!')
}
</script>

<template>
  <button @click="handleSuccess">Show Toast</button>
  <Toast ref="toastRef" />
</template>
```
