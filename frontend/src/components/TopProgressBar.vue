<script setup>
import { progress } from "../services/progress";
</script>

<template>
  <div class="ie-top-progress" :class="{ visible: progress.visible }" role="progressbar" aria-label="Chargement en cours" :aria-valuenow="Math.round(progress.value)">
    <div class="ie-top-progress-bar" :style="{ transform: `scaleX(${progress.value / 100})` }"></div>
  </div>
</template>

<style scoped>
.ie-top-progress { position: fixed; inset: 0 0 auto; z-index: 3000; height: 3px; pointer-events: none; opacity: 0; transition: opacity 0.25s ease; }
.ie-top-progress.visible { opacity: 1; }
.ie-top-progress-bar { height: 100%; background: linear-gradient(90deg, var(--ie-red, #c0393d), #e8706f); box-shadow: 0 0 8px rgba(192, 57, 61, 0.45); transform-origin: left; transition: transform 0.25s ease; }
</style>
