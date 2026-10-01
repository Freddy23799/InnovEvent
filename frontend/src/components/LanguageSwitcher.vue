<script setup>
import { useI18n } from "vue-i18n";
import { SUPPORTED_LOCALES, setLocale } from "../i18n";

const { locale } = useI18n();
</script>

<template>
  <div class="ie-lang-switcher">
    <button
      v-for="l in SUPPORTED_LOCALES" :key="l.code" type="button"
      class="ie-lang-pill" :class="{ 'is-active': locale === l.code }"
      :aria-label="l.label" @click="setLocale(l.code)"
    >
      {{ l.code.toUpperCase() }}
    </button>
  </div>
</template>

<style scoped>
.ie-lang-switcher { display: flex; gap: 2px; background: var(--ie-navy-soft); border-radius: 999px; padding: 2px; }
.ie-lang-pill {
  border: 0; background: transparent; padding: 5px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.02em; color: var(--ie-muted); cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.ie-lang-pill.is-active { background: #fff; color: var(--ie-navy); box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
.ie-lang-pill:hover:not(.is-active) { color: var(--ie-ink); }
</style>
