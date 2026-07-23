<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  segments: { type: Array, required: true },
  size: { type: Number, default: 168 },
  thickness: { type: Number, default: 24 }
})

const total = computed(() => props.segments.reduce((sum, s) => sum + s.value, 0) || 1)
const radius = computed(() => (props.size - props.thickness) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)

const arcs = computed(() => {
  let cumulative = 0
  return props.segments.map((s) => {
    const length = (s.value / total.value) * circumference.value
    const arc = { ...s, length, offset: -cumulative }
    cumulative += length
    return arc
  })
})

const animated = ref(false)
onMounted(() => {
  requestAnimationFrame(() => { animated.value = true })
})
</script>

<template>
  <div class="donut-wrap">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <g :transform="`rotate(-90 ${size / 2} ${size / 2})`">
        <circle
          :cx="size / 2" :cy="size / 2" :r="radius"
          fill="none" stroke="var(--panel-alt)" :stroke-width="thickness"
        />
        <circle
          v-for="(arc, i) in arcs" :key="i"
          :cx="size / 2" :cy="size / 2" :r="radius"
          fill="none" :stroke="arc.color" :stroke-width="thickness"
          stroke-linecap="butt"
          :stroke-dasharray="animated ? `${arc.length} ${circumference - arc.length}` : `0 ${circumference}`"
          :stroke-dashoffset="arc.offset"
          style="transition: stroke-dasharray 1s cubic-bezier(.4,0,.2,1);"
        />
      </g>
      <text :x="size / 2" :y="size / 2 - 4" text-anchor="middle" font-size="22" font-weight="900" fill="var(--text)">{{ total }}</text>
      <text :x="size / 2" :y="size / 2 + 16" text-anchor="middle" font-size="10" fill="var(--text-dim)">TOTAL</text>
    </svg>

    <div class="donut-legend">
      <div v-for="(s, i) in segments" :key="i" class="donut-legend-row">
        <span class="donut-dot" :style="{ background: s.color }"></span>
        <span class="donut-legend-label">{{ s.label }}</span>
        <span class="donut-legend-value">{{ s.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.donut-wrap { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.donut-legend { display: flex; flex-direction: column; gap: 10px; flex: 1; min-width: 140px; }
.donut-legend-row { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.donut-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.donut-legend-label { color: var(--text-dim); flex: 1; }
.donut-legend-value { font-weight: 700; color: var(--text); }
</style>