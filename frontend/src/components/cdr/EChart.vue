<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <div ref="container" class="cdr-echart" :style="{ height }" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { AriaComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  BarChart,
  LineChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
])

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' },
})

// item-click: a series element was clicked. grid-click: any point inside the grid was clicked; the
// payload carries the category index so empty (zero) buckets can still be selected.
const emit = defineEmits(['item-click', 'grid-click'])

const container = ref(null)
let chart = null
let observer = null

function applyOption(option) {
  chart?.setOption({ aria: { enabled: true }, ...option }, { notMerge: true })
}

onMounted(() => {
  chart = init(container.value, null, { renderer: 'canvas' })
  applyOption(props.option)

  chart.on('click', (params) => emit('item-click', params))
  chart.getZr().on('click', (event) => {
    const point = [event.offsetX, event.offsetY]
    if (!chart.containPixel({ gridIndex: 0 }, point)) {
      return
    }
    const [x, y] = chart.convertFromPixel({ gridIndex: 0 }, point)
    emit('grid-click', { x, y })
  })

  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(container.value)
})

watch(
  () => props.option,
  (option) => applyOption(option),
)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>
