<script setup>
import { Chart, registerables } from "chart.js";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

Chart.register(...registerables);

const props = defineProps({
  type: { type: String, default: "bar" },
  data: { type: Object, required: true },
  options: { type: Object, default: () => ({}) },
});

const canvasEl = ref(null);
let chartInstance = null;

function render() {
  if (!canvasEl.value) return;
  if (chartInstance) {
    chartInstance.data = props.data;
    chartInstance.options = props.options;
    chartInstance.update();
    return;
  }
  chartInstance = new Chart(canvasEl.value, {
    type: props.type,
    data: props.data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      ...props.options,
    },
  });
}

onMounted(render);
watch(() => [props.data, props.type], render, { deep: true });

onBeforeUnmount(() => {
  chartInstance?.destroy();
});
</script>

<template>
  <div class="ie-chart-wrap">
    <canvas ref="canvasEl"></canvas>
  </div>
</template>

<style scoped>
.ie-chart-wrap { position: relative; width: 100%; height: 280px; }
</style>
