<script setup>
import { ref, watch } from 'vue'
import { apiFetch } from '../api.js'

const props = defineProps({
  symbol: { type: String, required: true },
  exchange: { type: String, required: true },
  timeframe: { type: String, required: true },
})

const history = ref([])

const CALL_COLOR = {
  STRONG_SELL: 'text-red-400', SELL: 'text-red-400',
  NEUTRAL: 'text-neutral-400',
  BUY: 'text-emerald-400', STRONG_BUY: 'text-emerald-400',
}
const OUTCOME_DOT = { win: 'bg-emerald-400', loss: 'bg-red-400', flat: 'bg-neutral-500' }

function fmtDate(ts) {
  return new Date(ts * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  if (!props.symbol || !props.exchange) return
  try {
    const params = new URLSearchParams({ symbol: props.symbol, exchange: props.exchange, timeframe: props.timeframe })
    const res = await apiFetch(`/api/history?${params}`)
    history.value = await res.json()
  } catch {
    history.value = []
  }
}

watch(() => [props.symbol, props.exchange, props.timeframe], load, { immediate: true })
</script>

<template>
  <div v-if="history.length" class="p-5 border-b border-neutral-800">
    <div class="text-xs uppercase tracking-wide text-neutral-500 mb-2">Recent calls for this symbol</div>
    <div class="space-y-1.5">
      <div v-for="h in history" :key="h.id" class="flex items-center justify-between text-xs gap-2">
        <span class="text-neutral-500 w-28 shrink-0">{{ fmtDate(h.created_at) }}</span>
        <span :class="CALL_COLOR[h.call]" class="font-medium">{{ h.call }}</span>
        <span class="text-neutral-500 flex-1 text-right">{{ h.confidence }}</span>
        <span class="w-14 flex items-center gap-1.5 justify-end">
          <span v-if="h.outcome" :class="OUTCOME_DOT[h.outcome]" class="w-2 h-2 rounded-full inline-block" :title="h.outcome"></span>
          <span v-else class="text-neutral-700">pending</span>
        </span>
      </div>
    </div>
  </div>
</template>
