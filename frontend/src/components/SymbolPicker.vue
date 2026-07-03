<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Symbol' },
})
const emit = defineEmits(['update:modelValue', 'pick'])

const suggestions = ref([])
const open = ref(false)
let debounceHandle = null

function onInput(e) {
  const value = e.target.value
  emit('update:modelValue', value)
  clearTimeout(debounceHandle)
  if (!value.trim()) {
    suggestions.value = []
    open.value = false
    return
  }
  debounceHandle = setTimeout(async () => {
    try {
      const res = await fetch(`/api/symbols/search?q=${encodeURIComponent(value.trim())}`)
      suggestions.value = await res.json()
      open.value = suggestions.value.length > 0
    } catch {
      suggestions.value = []
    }
  }, 200)
}

function pick(s) {
  emit('update:modelValue', s.symbol)
  emit('pick', s) // { symbol, exchange }
  open.value = false
}

function onBlur() {
  // let a click on a suggestion register before closing
  setTimeout(() => { open.value = false }, 150)
}
</script>

<template>
  <div class="relative flex-1 min-w-48">
    <input
      :value="modelValue"
      @input="onInput"
      @focus="open = suggestions.length > 0"
      @blur="onBlur"
      :placeholder="placeholder"
      autocomplete="off"
      class="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-600"
    />
    <div
      v-if="open"
      class="absolute z-10 mt-1 w-full max-h-64 overflow-y-auto bg-neutral-900 border border-neutral-800 rounded-lg shadow-lg"
    >
      <button
        v-for="s in suggestions"
        :key="`${s.exchange}:${s.symbol}`"
        type="button"
        @mousedown.prevent="pick(s)"
        class="w-full text-left px-3 py-2 text-sm hover:bg-neutral-800 flex items-center justify-between"
      >
        <span class="font-medium">{{ s.symbol }}</span>
        <span class="text-xs text-neutral-500">{{ s.exchange }}</span>
      </button>
    </div>
  </div>
</template>
