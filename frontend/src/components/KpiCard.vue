<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  loading: { type: Boolean, default: false },
  icon: { type: String, default: "" },
  tone: { type: String, default: "red" }, // red | navy | success | warning
});
</script>

<template>
  <div class="ie-kpi ie-card" :class="{ 'ie-kpi-with-icon': icon }">
    <div v-if="icon" class="ie-kpi-icon" :class="`ie-kpi-icon-${tone}`">
      <i :class="icon"></i>
    </div>
    <div class="ie-kpi-body">
      <div v-if="loading" class="ie-skeleton" style="height: 24px; width: 60%; margin-bottom: 6px;"></div>
      <b v-else>{{ value }}</b>
      <span>{{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.ie-kpi { padding: 18px; }
.ie-kpi b { display: block; font-size: 24px; color: var(--ie-navy); margin-bottom: 4px; }
.ie-kpi span { font-size: 12px; color: var(--ie-muted); }

.ie-kpi-with-icon { display: flex; align-items: center; gap: 14px; }
.ie-kpi-icon {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 18px;
}
.ie-kpi-icon-red { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-kpi-icon-navy { background: var(--ie-navy-soft); color: var(--ie-navy); }
.ie-kpi-icon-success { background: var(--ie-success-soft); color: var(--ie-success); }
.ie-kpi-icon-warning { background: var(--ie-warning-soft); color: var(--ie-warning); }
.ie-kpi-with-icon .ie-kpi-body b { margin-bottom: 2px; }
</style>
