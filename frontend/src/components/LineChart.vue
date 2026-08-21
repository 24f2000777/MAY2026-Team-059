<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  points: { type: Array, required: true },
  height: { type: Number, default: 180 },
  color: { type: String, default: '#2F8F5B' }
})

const width = 560
const padding = 24
const maxValue = computed(() => Math.max(1, ...props.points.map((p) => p.value)))

const coords = computed(() => {
  const n = props.points.length
  const stepX = (width - padding * 2) / Math.max(1, n - 1)
  return props.points.map((p, i) => {
    const x = padding + i * stepX
    const y = padding + (1 - p.value / maxValue.value) * (props.height - padding * 2)
    return { x, y, ...p }
  })
})

const linePath = computed(() =>
  coords.value.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ')
)

const areaPath = computed(() => {
  if (coords.value.length === 0) return ''
  const first = coords.value[0]
  const last = coords.value[coords.value.length - 1]
  return `${linePath.value} L ${last.x} ${props.height - padding} L ${first.x} ${props.height - padding} Z`
})

const drawn = ref(false)
onMounted(() => {
  requestAnimationFrame(() => { drawn.value = true })
})
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" style="width: 100%; height: auto;">
    <defs>
      <linearGradient id="lineFade" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.22" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>

    <path :d="areaPath" fill="url(#lineFade)" :style="{ opacity: drawn ? 1 : 0, transition: 'opacity 1s ease .4s' }" />

    <path
      :d="linePath" fill="none" :stroke="color" stroke-width="2.5"
      stroke-linecap="round" stroke-linejoin="round"
      pathLength="500"
      :stroke-dasharray="500"
      :stroke-dashoffset="drawn ? 0 : 500"
      style="transition: stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1);"
    />

    <g v-for="(c, i) in coords" :key="i">
      <circle
        :cx="c.x" :cy="c.y" r="3.5" :fill="color"
        :style="{ opacity: drawn ? 1 : 0, transition: `opacity .3s ease ${0.6 + i * 0.05}s` }"
      />
    </g>

    <g v-for="(c, i) in coords" :key="'lbl' + i">
      <text v-if="i % 2 === 0 || coords.length < 8" :x="c.x" :y="height - 4" text-anchor="middle" font-size="9" fill="var(--text-dim)">{{ c.label }}</text>
    </g>
  </svg>
</template>