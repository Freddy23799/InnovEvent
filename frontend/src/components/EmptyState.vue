<script setup>
defineProps({
  icon: { type: String, default: "fa-solid fa-inbox" },
  text: { type: String, required: true },
});
</script>

<template>
  <div class="ie-empty-state">
    <i :class="icon"></i>
    {{ text }}
    <div v-if="$slots.default" style="margin-top: 14px;">
      <slot />
    </div>
  </div>
</template>
