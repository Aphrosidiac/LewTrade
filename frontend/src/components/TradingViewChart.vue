<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  symbol: { type: String, required: true },
  exchange: { type: String, required: true },
  timeframe: { type: String, default: '1h' },
})

const containerId = `tv-chart-${Math.random().toString(36).slice(2)}`
const containerEl = ref(null)

const INTERVAL_MAP = { '15m': '15', '1h': '60', '4h': '240', '1D': 'D' }

let scriptLoadPromise = null
function loadTvScript() {
  if (window.TradingView) return Promise.resolve()
  if (scriptLoadPromise) return scriptLoadPromise
  scriptLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/tv.js'
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
  return scriptLoadPromise
}

async function render() {
  await loadTvScript()
  if (!window.TradingView || !containerEl.value) return
  containerEl.value.innerHTML = ''
  new window.TradingView.widget({
    autosize: true,
    symbol: `${props.exchange}:${props.symbol}`,
    interval: INTERVAL_MAP[props.timeframe] || '60',
    timezone: 'Etc/UTC',
    theme: 'dark',
    style: '1',
    locale: 'en',
    toolbar_bg: '#0a0a0a',
    hide_top_toolbar: false,
    hide_legend: false,
    container_id: containerId,
  })
}

onMounted(render)
watch(() => [props.symbol, props.exchange, props.timeframe], render)
</script>

<template>
  <div class="w-full h-96 rounded-lg overflow-hidden border border-neutral-800">
    <div :id="containerId" ref="containerEl" class="w-full h-full"></div>
  </div>
</template>
