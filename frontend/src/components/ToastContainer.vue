<script setup>
import { useToastStore } from "../stores/toast";

const toast = useToastStore();
</script>

<template>
  <Teleport to="body">
    <div class="ie-toast-stack">
      <TransitionGroup name="ie-toast">
        <div
          v-for="t in toast.toasts" :key="t.id"
          class="ie-toast" :class="`ie-toast-${t.type}`"
          @click="toast.dismiss(t.id)"
        >
          <i class="fa-solid" :class="t.type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'"></i>
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.ie-toast-stack {
  position: fixed; bottom: 22px; right: 22px; z-index: 2000;
  display: flex; flex-direction: column; gap: 8px; align-items: flex-end;
  pointer-events: none;
}
.ie-toast {
  display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-radius: 10px;
  font-size: 13px; font-weight: 600; color: #fff; box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
  cursor: pointer; pointer-events: auto; max-width: 360px;
}
.ie-toast-success { background: #1E7B4D; }
.ie-toast-error { background: var(--ie-red); }
.ie-toast i { font-size: 15px; flex-shrink: 0; }

.ie-toast-enter-active, .ie-toast-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.ie-toast-enter-from, .ie-toast-leave-to { opacity: 0; transform: translateY(8px); }

@media (max-width: 480px) {
  .ie-toast-stack { left: 16px; right: 16px; bottom: 16px; align-items: stretch; }
  .ie-toast { max-width: none; }
}
</style>
