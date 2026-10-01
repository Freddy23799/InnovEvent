<script setup>
import { computed } from "vue";

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  readonly: { type: Boolean, default: true },
  size: { type: Number, default: 15 },
  count: { type: Number, default: 0 },
});
const emit = defineEmits(["update:modelValue"]);

const stars = computed(() =>
  Array.from({ length: 5 }, (_, i) => {
    const diff = props.modelValue - i;
    if (diff >= 1) return "full";
    if (diff >= 0.5) return "half";
    return "empty";
  })
);

function pick(index, event) {
  if (props.readonly) return;
  const rect = event.currentTarget.getBoundingClientRect();
  const half = event.clientX - rect.left < rect.width / 2;
  emit("update:modelValue", half ? index + 0.5 : index + 1);
}
</script>

<template>
  <span class="ie-star-rating" :class="{ 'is-interactive': !readonly }" :style="{ fontSize: size + 'px' }">
    <span
      v-for="(state, i) in stars" :key="i" class="ie-star" :class="`is-${state}`"
      @click="pick(i, $event)"
    >
      <i class="fa-solid fa-star ie-star-bg"></i>
      <i class="fa-solid fa-star ie-star-fg"></i>
    </span>
    <span v-if="count" class="ie-star-count">({{ count }})</span>
  </span>
</template>

<style scoped>
.ie-star-rating { display: inline-flex; align-items: center; gap: 1px; line-height: 1; }
.ie-star { position: relative; display: inline-block; width: 1em; height: 1em; }
.ie-star.is-interactive { cursor: pointer; }
.ie-star-bg { position: absolute; inset: 0; color: #e2e5ea; }
.ie-star-fg { position: absolute; inset: 0; color: #d4a017; overflow: hidden; width: 0; }
.ie-star.is-full .ie-star-fg { width: 100%; }
.ie-star.is-half .ie-star-fg { width: 50%; }
.ie-star-count { margin-left: 6px; font-size: 0.75em; color: var(--ie-muted); }
</style>
