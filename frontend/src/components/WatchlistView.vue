<script setup>
import { ref, onMounted } from 'vue'
import SymbolPicker from './SymbolPicker.vue'
import { apiFetch, apiFetchJson } from '../api.js'

const emit = defineEmits(['select'])

const items = ref([])
const results = ref({}) // watchlist_id -> analysis result
const newSymbol = ref('')
const newExchange = ref('')
const newTimeframe = ref('1h')
const scanning = ref(false)
const error = ref('')

const CALL_COLOR = {
  STRONG_SELL: 'text-red-400', SELL: 'text-red-400',
  NEUTRAL: 'text-neutral-400',
  BUY: 'text-emerald-400', STRONG_BUY: 'text-emerald-400',
}

async function loadWatchlist() {
  const res = await apiFetch('/api/watchlist')
  items.value = await res.json()
}

async function addSymbol() {
  if (!newSymbol.value.trim()) return
  error.value = ''
  try {
    const res = await apiFetch('/api/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol: newSymbol.value.trim().toUpperCase(),
        exchange: newExchange.value.trim() || null,
        timeframe: newTimeframe.value,
      }),
    })
    items.value = await res.json()
    newSymbol.value = ''
    newExchange.value = ''
  } catch (e) {
    error.value = 'Failed to add symbol'
  }
}

async function removeItem(id) {
  const res = await apiFetch(`/api/watchlist/${id}`, { method: 'DELETE' })
  items.value = await res.json()
  delete results.value[id]
}

async function scanAll() {
  if (!items.value.length) return
  scanning.value = true
  error.value = ''
  try {
    const data = await apiFetchJson('/api/watchlist/scan')
    const map = {}
    for (const r of data) {
      if (r.watchlist_id) map[r.watchlist_id] = r
    }
    results.value = map
  } catch (e) {
    error.value = e.message || 'Scan failed'
  } finally {
    scanning.value = false
  }
}

onMounted(loadWatchlist)
</script>

<template>
  <div>
    <form @submit.prevent="addSymbol" class="flex gap-2 mb-4">
      <SymbolPicker
        v-model="newSymbol"
        placeholder="Add symbol e.g. XAUUSD, BTCUSDT"
        @pick="(s) => (newExchange = s.exchange)"
      />
      <select v-model="newTimeframe" class="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-600">
        <option value="15m">15m</option>
        <option value="1h">1h</option>
        <option value="4h">4h</option>
        <option value="1D">1D</option>
      </select>
      <button type="submit" class="bg-white text-neutral-950 font-medium text-sm rounded-lg px-4 py-2">Add</button>
    </form>

    <div v-if="error" class="text-red-400 text-sm mb-4">{{ error }}</div>

    <div v-if="!items.length" class="text-neutral-600 text-sm py-8 text-center border border-dashed border-neutral-800 rounded-lg">
      No symbols yet — add one above.
    </div>

    <template v-else>
      <button
        @click="scanAll"
        :disabled="scanning"
        class="bg-neutral-100 text-neutral-950 font-medium text-sm rounded-lg px-4 py-2 mb-4 disabled:opacity-50"
      >
        {{ scanning ? 'Scanning…' : 'Scan all' }}
      </button>

      <div class="border border-neutral-800 rounded-xl overflow-hidden divide-y divide-neutral-800">
        <div
          v-for="item in items"
          :key="item.id"
          class="p-4 flex items-center justify-between hover:bg-neutral-900/50 cursor-pointer"
          @click="emit('select', item)"
        >
          <div>
            <div class="font-medium">{{ item.symbol }}</div>
            <div class="text-xs text-neutral-500">{{ item.exchange }} · {{ item.timeframe }}</div>
          </div>

          <div class="flex items-center gap-4">
            <template v-if="results[item.id] && !results[item.id].error">
              <div class="text-right">
                <div :class="CALL_COLOR[results[item.id].verdict.call]" class="text-sm font-semibold">
                  {{ results[item.id].verdict.call }}
                </div>
                <div class="text-xs text-neutral-500">{{ results[item.id].verdict.confidence }}</div>
              </div>
              <div class="text-sm font-mono text-neutral-400 w-20 text-right">{{ results[item.id].price.current_price }}</div>
            </template>
            <template v-else-if="results[item.id]?.error">
              <span class="text-xs text-red-400 max-w-64 truncate" :title="results[item.id].error">
                {{ results[item.id].error }}
              </span>
            </template>

            <button
              @click.stop="removeItem(item.id)"
              class="text-neutral-600 hover:text-red-400 text-xs px-2"
            >
              remove
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
