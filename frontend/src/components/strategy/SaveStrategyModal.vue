<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen px-4">
      <!-- Backdrop -->
      <div class="fixed inset-0 bg-black bg-opacity-50" @click="$emit('close')"></div>

      <!-- Modal -->
      <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Save Strategy</h3>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Strategy Name</label>
          <input
            v-model="name"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="My Iron Condor Strategy"
            @keyup.enter="handleSave"
          />
        </div>

        <div class="flex justify-end gap-3">
          <button
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            @click="handleSave"
            :disabled="!name.trim()"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-lg',
              name.trim()
                ? 'text-white bg-blue-600 hover:bg-blue-700'
                : 'text-gray-400 bg-gray-200 cursor-not-allowed'
            ]"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  strategyName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['save', 'close'])

const name = ref(props.strategyName || '')

function handleSave() {
  if (name.value.trim()) {
    emit('save', name.value.trim())
  }
}
</script>
