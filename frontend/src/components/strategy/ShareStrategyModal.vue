<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen px-4">
      <!-- Backdrop -->
      <div class="fixed inset-0 bg-black bg-opacity-50" @click="$emit('close')"></div>

      <!-- Modal -->
      <div class="relative bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Share Strategy</h3>

        <p class="text-sm text-gray-600 mb-4">
          Share this link with others to let them view your strategy:
        </p>

        <div class="flex items-center gap-2 mb-4">
          <input
            ref="urlInput"
            type="text"
            :value="shareUrl"
            readonly
            class="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
          />
          <button
            @click="copyToClipboard"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              copied
                ? 'text-white bg-green-600'
                : 'text-white bg-blue-600 hover:bg-blue-700'
            ]"
          >
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>

        <div class="flex justify-end">
          <button
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  shareUrl: {
    type: String,
    required: true
  }
})

defineEmits(['close'])

const urlInput = ref(null)
const copied = ref(false)

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(urlInput.value.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    // Fallback for older browsers
    urlInput.value.select()
    document.execCommand('copy')
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}
</script>
