<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../api.js'

const record = ref(null)
const expanded = ref(false)

async function load() {
  try {
    const res = await apiFetch('/api/track-record')
    record.value = await res.json()
  } catch {
    record.value = null
  }
}

function breakdownRows(key) {
  return (record.value?.[key] || []).slice(0, 8)
}

onMounted(load)
defineExpose({ reload: load })
</script>

<template>
  <div v-if="record" class="relative">
    <button
      type="button"
      class="text-xs text-neutral-500 flex items-center gap-3 hover:text-neutral-300"
      @click="expanded = !expanded"
    >
      <span v-if="record.win_rate !== null">
        <span class="text-neutral-300 font-medium">{{ record.win_rate }}%</span> win rate
        <span class="text-neutral-600">({{ record.wins }}W / {{ record.losses }}L / {{ record.flats }} flat)</span>
      </span>
      <span v-else class="text-neutral-600">No resolved calls yet</span>
      <span class="text-neutral-700">·</span>
      <span>{{ record.total_calls }} calls logged</span>
      <span class="text-neutral-700">{{ expanded ? '▲' : '▼' }}</span>
    </button>

    <div
      v-if="expanded"
      class="absolute right-0 mt-2 w-80 bg-neutral-900 border border-neutral-800 rounded-lg shadow-lg p-4 z-20 space-y-4 text-left"
    >
      <div v-for="(label, key) in { by_symbol: 'By symbol', by_timeframe: 'By timeframe', by_confidence: 'By confidence' }" :key="key">
        <div class="text-[10px] uppercase tracking-wide text-neutral-500 mb-1.5">{{ label }}</div>
        <div v-if="!breakdownRows(key).length" class="text-xs text-neutral-600">No resolved calls yet</div>
        <div v-else class="space-y-1">
          <div v-for="row in breakdownRows(key)" :key="row.key" class="flex items-center justify-between text-xs">
            <span class="text-neutral-400">{{ row.key }}</span>
            <span class="font-mono">
              <span v-if="row.win_rate !== null" class="text-neutral-300">{{ row.win_rate }}%</span>
              <span v-else class="text-neutral-600">—</span>
              <span class="text-neutral-600"> ({{ row.total }})</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
