<script setup>
defineProps({
  rows: { type: Number, default: 4 },
});
</script>

<template>
  <div class="ie-skeleton-table">
    <div v-for="i in rows" :key="i" class="ie-skeleton ie-skeleton-row"></div>
  </div>
</template>
