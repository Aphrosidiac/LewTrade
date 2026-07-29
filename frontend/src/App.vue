<script setup>
import { ref } from 'vue'
import TradingViewChart from './components/TradingViewChart.vue'
import TrackRecordBadge from './components/TrackRecordBadge.vue'
import WatchlistView from './components/WatchlistView.vue'
import SymbolPicker from './components/SymbolPicker.vue'
import CallHistory from './components/CallHistory.vue'
import PriceLevels from './components/PriceLevels.vue'
import { apiFetch, apiFetchJson } from './api.js'

const tab = ref('analyze') // 'analyze' | 'watchlist'

const symbol = ref('XAUUSD')
const exchange = ref('')
const timeframe = ref('1h')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const addedToWatchlist = ref(false)
const trackRecordBadge = ref(null)

const CALL_STYLE = {
  STRONG_SELL: { label: 'STRONG SELL', color: 'text-red-400' },
  SELL: { label: 'SELL', color: 'text-red-400' },
  NEUTRAL: { label: 'NEUTRAL', color: 'text-neutral-300' },
  BUY: { label: 'BUY', color: 'text-emerald-400' },
  STRONG_BUY: { label: 'STRONG BUY', color: 'text-emerald-400' },
}

const BIAS_COLOR = { Bullish: 'text-emerald-400', Bearish: 'text-red-400' }

async function runAnalysis() {
  if (!symbol.value.trim()) return
  loading.value = true
  error.value = ''
  result.value = null
  addedToWatchlist.value = false
  try {
    const params = new URLSearchParams({ symbol: symbol.value.trim().toUpperCase(), timeframe: timeframe.value })
    if (exchange.value.trim()) params.set('exchange', exchange.value.trim().toUpperCase())
    result.value = await apiFetchJson(`/api/analyze?${params}`)
    trackRecordBadge.value?.reload()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function addToWatchlist() {
  if (!result.value) return
  await apiFetch('/api/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol: result.value.symbol, exchange: result.value.exchange, timeframe: result.value.timeframe }),
  })
  addedToWatchlist.value = true
}

function selectFromWatchlist(item) {
  symbol.value = item.symbol
  exchange.value = item.exchange
  timeframe.value = item.timeframe
  tab.value = 'analyze'
  runAnalysis()
}
</script>

<template>
  <div class="min-h-screen bg-neutral-950 text-neutral-100">
    <div class="max-w-2xl mx-auto px-4 py-10">
      <header class="mb-6">
        <div class="flex items-baseline justify-between flex-wrap gap-2">
          <h1 class="text-2xl font-semibold tracking-tight">LewTrade</h1>
          <TrackRecordBadge ref="trackRecordBadge" />
        </div>
        <p class="text-neutral-500 text-sm mt-1">Trend · support &amp; resistance · news · price action, combined into one call.</p>
      </header>

      <div class="flex gap-1 mb-6 border-b border-neutral-800">
        <button
          @click="tab = 'analyze'"
          :class="tab === 'analyze' ? 'border-white text-white' : 'border-transparent text-neutral-500'"
          class="px-3 py-2 text-sm border-b-2 -mb-px"
        >Analyze</button>
        <button
          @click="tab = 'watchlist'"
          :class="tab === 'watchlist' ? 'border-white text-white' : 'border-transparent text-neutral-500'"
          class="px-3 py-2 text-sm border-b-2 -mb-px"
        >Watchlist</button>
      </div>

      <WatchlistView v-if="tab === 'watchlist'" @select="selectFromWatchlist" />

      <template v-else>
        <form @submit.prevent="runAnalysis" class="flex flex-wrap gap-2 mb-8">
          <SymbolPicker
            v-model="symbol"
            placeholder="Symbol e.g. XAUUSD, BTCUSDT, AAPL"
            @pick="(s) => (exchange = s.exchange)"
          />
          <input
            v-model="exchange"
            placeholder="Exchange (optional)"
            class="w-40 bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-600"
          />
          <select v-model="timeframe" class="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-600">
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1D">1D</option>
          </select>
          <button
            type="submit"
            :disabled="loading"
            class="bg-white text-neutral-950 font-medium text-sm rounded-lg px-4 py-2 disabled:opacity-50"
          >
            {{ loading ? 'Analyzing…' : 'Analyze' }}
          </button>
        </form>

        <div v-if="error" class="text-red-400 text-sm mb-6">{{ error }}</div>
        <div v-if="loading" class="text-neutral-500 text-sm mb-6">Pulling technicals, multi-timeframe confluence, news, and sentiment — this takes ~10-15s.</div>

        <div v-if="result" class="space-y-4">
          <TradingViewChart :symbol="result.symbol" :exchange="result.exchange" :timeframe="result.timeframe" />

          <div class="border border-neutral-800 rounded-xl overflow-hidden">
            <div class="p-5 border-b border-neutral-800 flex items-baseline justify-between">
              <div>
                <div class="text-lg font-semibold">{{ result.symbol }}</div>
                <div class="text-xs text-neutral-500">
                  {{ result.timeframe }} chart · data via {{ result.exchange }}
                  <span v-if="result.cached" class="text-neutral-600">· cached</span>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="text-right">
                  <div class="text-xl font-mono">{{ result.price.current_price }}</div>
                  <div :class="result.price.change_percent >= 0 ? 'text-emerald-400' : 'text-red-400'" class="text-sm font-mono">
                    {{ result.price.change_percent >= 0 ? '+' : '' }}{{ result.price.change_percent }}%
                  </div>
                </div>
                <button
                  @click="addToWatchlist"
                  class="text-xs border border-neutral-800 rounded-lg px-2 py-1.5 text-neutral-400 hover:text-white hover:border-neutral-600"
                >
                  {{ addedToWatchlist ? 'Added ✓' : '+ Watchlist' }}
                </button>
              </div>
            </div>

            <!-- Multi-timeframe confluence -->
            <div v-if="result.multi_timeframe" class="p-5 border-b border-neutral-800">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs uppercase tracking-wide text-neutral-500">Multi-Timeframe Confluence</span>
                <span class="text-xs text-neutral-400">{{ result.multi_timeframe.alignment }}</span>
              </div>
              <div class="flex gap-2 flex-wrap">
                <div
                  v-for="(d, tf) in result.multi_timeframe.per_timeframe"
                  :key="tf"
                  class="text-xs px-2 py-1 rounded bg-neutral-900 border border-neutral-800"
                >
                  <span class="text-neutral-500">{{ tf }}</span>
                  <span :class="BIAS_COLOR[d.bias] || 'text-neutral-400'" class="ml-1 font-medium">{{ d.bias }}</span>
                </div>
              </div>
            </div>

            <div class="p-5 border-b border-neutral-800">
              <div class="text-xs uppercase tracking-wide text-neutral-500 mb-2">The Call</div>
              <div class="flex items-center justify-between mb-3">
                <span :class="CALL_STYLE[result.verdict.call]?.color" class="text-xl font-bold">
                  {{ CALL_STYLE[result.verdict.call]?.label || result.verdict.call }}
                </span>
                <span class="text-xs text-neutral-500">{{ result.verdict.confidence }} confidence</span>
              </div>
              <div class="h-2 rounded-full bg-neutral-800 relative mb-1">
                <div class="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-neutral-950" :style="{ left: `calc(${result.verdict.gauge}% - 6px)` }"></div>
              </div>
              <div class="flex justify-between text-[10px] text-neutral-600 mb-4">
                <span>SELL</span><span>BUY</span>
              </div>

              <p class="text-sm text-neutral-300 mb-3">{{ result.verdict.trend_label }}</p>
              <ul class="space-y-1.5 mb-4">
                <li v-for="(b, i) in result.verdict.bullets" :key="i" class="text-sm text-neutral-400 flex gap-2">
                  <span class="text-neutral-600">•</span>{{ b }}
                </li>
              </ul>
              <div class="text-xs bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-400 mb-3">
                <span class="text-neutral-500">What flips it:</span> {{ result.verdict.what_flips_it }}
              </div>

              <div v-if="result.trade_levels" class="grid grid-cols-4 gap-2 text-center">
                <div class="bg-neutral-900 border border-neutral-800 rounded-lg py-2">
                  <div class="text-[10px] uppercase tracking-wide text-neutral-500">Entry</div>
                  <div class="text-sm font-mono">{{ result.trade_levels.entry }}</div>
                </div>
                <div class="bg-neutral-900 border border-neutral-800 rounded-lg py-2">
                  <div class="text-[10px] uppercase tracking-wide text-neutral-500">Stop</div>
                  <div class="text-sm font-mono text-red-400">{{ result.trade_levels.stop }}</div>
                </div>
                <div class="bg-neutral-900 border border-neutral-800 rounded-lg py-2">
                  <div class="text-[10px] uppercase tracking-wide text-neutral-500">Target</div>
                  <div class="text-sm font-mono text-emerald-400">{{ result.trade_levels.target }}</div>
                </div>
                <div class="bg-neutral-900 border border-neutral-800 rounded-lg py-2">
                  <div class="text-[10px] uppercase tracking-wide text-neutral-500">R:R</div>
                  <div class="text-sm font-mono">{{ result.trade_levels.risk_reward }}</div>
                </div>
              </div>
              <div v-else-if="['BUY','STRONG_BUY','SELL','STRONG_SELL'].includes(result.verdict.call)" class="text-xs text-neutral-600">
                No clean support/resistance levels to size a stop/target from.
              </div>
            </div>

            <PriceLevels
              :price="result.price.current_price"
              :support-resistance="result.support_resistance"
              :trade-levels="result.trade_levels"
            />

            <div class="p-5 border-b border-neutral-800 grid grid-cols-2 gap-4 text-sm">
              <div>
                <div class="text-xs uppercase tracking-wide text-neutral-500 mb-1">Trend</div>
                <div>{{ result.market_structure.trend }} · {{ result.market_structure.trend_strength }}</div>
              </div>
              <div>
                <div class="text-xs uppercase tracking-wide text-neutral-500 mb-1">Support / Resistance</div>
                <div>S {{ result.support_resistance.nearest_support }} · R {{ result.support_resistance.nearest_resistance }}</div>
              </div>
              <div v-if="result.volume_analysis">
                <div class="text-xs uppercase tracking-wide text-neutral-500 mb-1">Volume</div>
                <div>{{ result.volume_analysis.signal }}<template v-if="result.volume_analysis.ratio"> ({{ result.volume_analysis.ratio }}x avg)</template></div>
              </div>
              <div v-if="result.social_sentiment">
                <div class="text-xs uppercase tracking-wide text-neutral-500 mb-1">Reddit Sentiment</div>
                <div>{{ result.social_sentiment.sentiment_label }} ({{ result.social_sentiment.posts_analyzed }} posts)</div>
              </div>
            </div>

            <CallHistory :symbol="result.symbol" :exchange="result.exchange" :timeframe="result.timeframe" />

            <div class="p-5" v-if="result.news?.length">
              <div class="text-xs uppercase tracking-wide text-neutral-500 mb-2">News considered</div>
              <ul class="space-y-2">
                <li v-for="(n, i) in result.news.slice(0, 4)" :key="i" class="text-sm text-neutral-400">
                  <a :href="n.url" target="_blank" rel="noopener" class="hover:text-neutral-200">{{ n.title }}</a>
                  <span class="text-neutral-600 text-xs"> — {{ n.source }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
