<script setup>
import { computed } from 'vue'

const props = defineProps({
  price: { type: Number, required: true },
  supportResistance: { type: Object, required: true },
  tradeLevels: { type: Object, default: null },
})

// Drawn in viewBox units so the whole thing scales with the card width.
const W = 600
const H = 340
const LINE_X1 = 44
const LINE_X2 = 452
const TOP_PAD = 18
const BOT_PAD = 18
const MIN_LABEL_GAP = 15 // px between label baselines before we nudge them apart

const LEVEL_DEFS = [
  { key: 'resistance_3', label: 'R3', kind: 'resistance' },
  { key: 'resistance_2', label: 'R2', kind: 'resistance' },
  { key: 'resistance_1', label: 'R1', kind: 'resistance' },
  { key: 'pivot', label: 'PP', kind: 'pivot' },
  { key: 'support_1', label: 'S1', kind: 'support' },
  { key: 'support_2', label: 'S2', kind: 'support' },
  { key: 'support_3', label: 'S3', kind: 'support' },
]

const KIND_COLOR = {
  resistance: '#f87171', // red-400
  support: '#34d399',    // emerald-400
  pivot: '#a3a3a3',      // neutral-400
}

const levels = computed(() =>
  LEVEL_DEFS
    .map((d) => ({ ...d, value: props.supportResistance?.[d.key] }))
    .filter((d) => typeof d.value === 'number' && isFinite(d.value))
)

// The nearest levels are the ones the verdict and trade_levels actually key off,
// so mark them rather than letting them look like any other line.
const nearest = computed(() => ({
  resistance: props.supportResistance?.nearest_resistance,
  support: props.supportResistance?.nearest_support,
}))

// Scale spans every drawn price — levels, current price, and the trade levels —
// so nothing can fall outside the box.
const scale = computed(() => {
  const prices = [...levels.value.map((l) => l.value), props.price]
  if (props.tradeLevels) {
    prices.push(props.tradeLevels.stop, props.tradeLevels.target, props.tradeLevels.entry)
  }
  const clean = prices.filter((p) => typeof p === 'number' && isFinite(p))
  let min = Math.min(...clean)
  let max = Math.max(...clean)
  const span = max - min || Math.abs(max) * 0.01 || 1 // guard: all levels identical
  min -= span * 0.06
  max += span * 0.06
  return { min, max, span: max - min }
})

function y(price) {
  const { min, span } = scale.value
  const frac = (price - min) / span
  return H - BOT_PAD - frac * (H - TOP_PAD - BOT_PAD)
}

function pct(level) {
  return ((level - props.price) / props.price) * 100
}

function fmt(n) {
  if (!isFinite(n)) return '—'
  const abs = Math.abs(n)
  // Keep small-priced instruments readable without spamming zeros on large ones.
  const decimals = abs >= 1000 ? 2 : abs >= 1 ? 3 : 6
  return n.toFixed(decimals)
}

// Rows carry their own label y, nudged apart when levels cluster tightly so the
// text stays legible even though the lines themselves stay at true price.
const rows = computed(() => {
  const out = levels.value
    .map((l) => ({
      ...l,
      lineY: y(l.value),
      labelY: y(l.value),
      pct: pct(l.value),
      isNearest: l.value === nearest.value.resistance || l.value === nearest.value.support,
    }))
    .sort((a, b) => a.lineY - b.lineY)

  for (let i = 1; i < out.length; i++) {
    const gap = out[i].labelY - out[i - 1].labelY
    if (gap < MIN_LABEL_GAP) out[i].labelY = out[i - 1].labelY + MIN_LABEL_GAP
  }
  return out
})

const priceY = computed(() => y(props.price))

// Risk band = entry→stop, reward band = entry→target. Works for both directions:
// on a SELL the stop is above and target below, and the rects just flip.
function band(from, to) {
  const a = y(from)
  const b = y(to)
  return { y: Math.min(a, b), height: Math.abs(a - b) }
}

const riskBand = computed(() =>
  props.tradeLevels ? band(props.tradeLevels.entry, props.tradeLevels.stop) : null
)
const rewardBand = computed(() =>
  props.tradeLevels ? band(props.tradeLevels.entry, props.tradeLevels.target) : null
)
</script>

<template>
  <div class="p-5 border-b border-neutral-800">
    <div class="flex items-baseline justify-between mb-3">
      <span class="text-xs uppercase tracking-wide text-neutral-500">Price Levels</span>
      <span v-if="tradeLevels" class="text-xs text-neutral-500">
        risk <span class="font-mono text-red-400">{{ fmt(Math.abs(tradeLevels.entry - tradeLevels.stop)) }}</span>
        · reward <span class="font-mono text-emerald-400">{{ fmt(Math.abs(tradeLevels.target - tradeLevels.entry)) }}</span>
      </span>
    </div>

    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full" role="img"
         aria-label="Support and resistance levels relative to current price">
      <!-- reward first so the risk band wins any overlap -->
      <rect v-if="rewardBand" :x="LINE_X1" :y="rewardBand.y" :width="LINE_X2 - LINE_X1"
            :height="rewardBand.height" fill="#34d399" opacity="0.09" />
      <rect v-if="riskBand" :x="LINE_X1" :y="riskBand.y" :width="LINE_X2 - LINE_X1"
            :height="riskBand.height" fill="#f87171" opacity="0.09" />

      <g v-for="row in rows" :key="row.key">
        <line :x1="LINE_X1" :y1="row.lineY" :x2="LINE_X2" :y2="row.lineY"
              :stroke="KIND_COLOR[row.kind]" :stroke-width="row.isNearest ? 1.4 : 0.8"
              :stroke-dasharray="row.isNearest ? 'none' : '3 3'"
              :opacity="row.isNearest ? 0.95 : 0.5" />
        <!-- leader line when the label was nudged off its true price -->
        <line v-if="Math.abs(row.labelY - row.lineY) > 1"
              :x1="LINE_X1 - 4" :y1="row.lineY" :x2="LINE_X1 - 10" :y2="row.labelY"
              :stroke="KIND_COLOR[row.kind]" stroke-width="0.5" opacity="0.4" />
        <text x="8" :y="row.labelY + 3.5" font-size="11"
              :fill="KIND_COLOR[row.kind]" :opacity="row.isNearest ? 1 : 0.75"
              :font-weight="row.isNearest ? 600 : 400">{{ row.label }}</text>
        <text :x="LINE_X2 + 10" :y="row.labelY + 3.5" font-size="11"
              font-family="ui-monospace, monospace" fill="#d4d4d4"
              :opacity="row.isNearest ? 1 : 0.6">{{ fmt(row.value) }}</text>
        <text :x="W - 8" :y="row.labelY + 3.5" font-size="10" text-anchor="end"
              font-family="ui-monospace, monospace"
              :fill="row.pct >= 0 ? '#f87171' : '#34d399'"
              :opacity="row.isNearest ? 0.95 : 0.55">
          {{ row.pct >= 0 ? '+' : '' }}{{ row.pct.toFixed(2) }}%
        </text>
      </g>

      <!-- current price drawn last so it sits on top of every level -->
      <line :x1="LINE_X1 - 6" :y1="priceY" :x2="LINE_X2" :y2="priceY"
            stroke="#ffffff" stroke-width="1.6" />
      <circle :cx="LINE_X1 - 6" :cy="priceY" r="3" fill="#ffffff" />
      <text :x="LINE_X2 + 10" :y="priceY + 3.5" font-size="11.5" font-weight="600"
            font-family="ui-monospace, monospace" fill="#ffffff">{{ fmt(price) }}</text>
      <text :x="W - 8" :y="priceY + 3.5" font-size="9" text-anchor="end"
            fill="#a3a3a3" letter-spacing="0.5">NOW</text>
    </svg>

    <div v-if="tradeLevels" class="flex items-center gap-4 mt-2 text-[10px] text-neutral-500">
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2 rounded-sm" style="background:#f8717133"></span>risk (entry→stop)
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2 rounded-sm" style="background:#34d39933"></span>reward (entry→target)
      </span>
      <span class="text-neutral-600">solid line = nearest level the call uses</span>
    </div>
  </div>
</template>
