<script setup>
import { ref, onMounted } from 'vue'

const record = ref(null)

async function load() {
  try {
    const res = await fetch('/api/track-record')
    record.value = await res.json()
  } catch {
    record.value = null
  }
}

onMounted(load)
defineExpose({ reload: load })
</script>

<template>
  <div v-if="record" class="text-xs text-neutral-500 flex items-center gap-3">
    <span v-if="record.win_rate !== null">
      <span class="text-neutral-300 font-medium">{{ record.win_rate }}%</span> win rate
      <span class="text-neutral-600">({{ record.wins }}W / {{ record.losses }}L / {{ record.flats }} flat)</span>
    </span>
    <span v-else class="text-neutral-600">No resolved calls yet</span>
    <span class="text-neutral-700">·</span>
    <span>{{ record.total_calls }} calls logged</span>
  </div>
</template>
