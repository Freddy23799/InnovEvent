<script setup>
import { nextTick, onMounted, ref } from "vue";

const props = defineProps({
  items: { type: Array, required: true }, // [{ label, value, display, color }]
});

const animated = ref(false);

onMounted(async () => {
  await nextTick();
  requestAnimationFrame(() => {
    animated.value = true;
  });
});

function widthFor(item) {
  const max = Math.max(...props.items.map((i) => i.value), 1);
  return animated.value ? Math.max((item.value / max) * 100, item.value > 0 ? 3 : 0) : 0;
}
</script>

<template>
  <div class="ie-hbar-list">
    <div v-for="item in items" :key="item.label" class="ie-hbar-row">
      <span class="ie-hbar-label">{{ item.label }}</span>
      <div class="ie-hbar-track">
        <div
          class="ie-hbar-fill"
          :style="{ width: widthFor(item) + '%', background: item.color || 'var(--ie-red)' }"
        ></div>
      </div>
      <span class="ie-hbar-value">{{ item.display ?? item.value }}</span>
    </div>
    <div v-if="!items.length" class="ie-empty-state">Aucune donnée à afficher.</div>
  </div>
</template>

<style scoped>
.ie-hbar-list { display: flex; flex-direction: column; gap: 14px; }
.ie-hbar-row { display: grid; grid-template-columns: 150px 1fr 110px; align-items: center; gap: 12px; }
.ie-hbar-label { font-size: 13px; font-weight: 600; color: var(--ie-navy); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ie-hbar-track { background: #eef0f2; border-radius: 999px; height: 11px; overflow: hidden; }
.ie-hbar-fill {
  height: 100%; border-radius: 999px;
  transition: width 1s cubic-bezier(0.22, 1, 0.36, 1);
}
.ie-hbar-value { font-size: 12.5px; text-align: right; color: var(--ie-muted); white-space: nowrap; }

@media (max-width: 640px) {
  .ie-hbar-row { grid-template-columns: 100px 1fr 80px; }
}
</style>
