<script setup>
import logo from "../assets/images/logo-mark.png";
</script>

<template>
  <div class="ie-public-shell">
    <header class="ie-public-header">
      <router-link :to="{ name: 'landing' }" class="ie-public-brand">
        <img :src="logo" alt="InnovEvent" />
        <span>InnovEvent<em>Group</em></span>
      </router-link>
      <div class="ie-public-actions">
        <router-link :to="{ name: 'landing' }" class="ie-btn ie-btn-ghost ie-btn-sm">
          <i class="fa-solid fa-arrow-left"></i> Accueil
        </router-link>
        <router-link :to="{ name: 'login' }" class="ie-btn ie-btn-secondary ie-btn-sm">Connexion</router-link>
        <router-link :to="{ name: 'register' }" class="ie-btn ie-btn-primary ie-btn-sm">Créer mon projet</router-link>
      </div>
    </header>
    <main class="ie-public-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.ie-public-shell { min-height: 100vh; background: var(--ie-surface); }
.ie-public-header {
  position: sticky; top: 0; z-index: 40; background: #fff; border-bottom: 1px solid var(--ie-line);
  padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
}
.ie-public-brand { display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--ie-navy); font-size: 16px; }
.ie-public-brand img { height: 34px; width: auto; display: block; }
.ie-public-brand em { color: var(--ie-red); font-style: normal; text-transform: uppercase; font-size: 0.6em; letter-spacing: 0.1em; margin-left: 4px; }
.ie-public-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ie-public-content { width: 100%; max-width: 1240px; min-width: 0; margin: 0 auto; padding: 24px; }
@media (max-width: 640px) {
  .ie-public-header { padding: 12px 16px; }
  .ie-public-header { gap: 10px; }
  .ie-public-actions { width: 100%; display: grid; grid-template-columns: 1fr 1fr; }
  .ie-public-actions > :last-child { grid-column: 1 / -1; }
  .ie-public-actions .ie-btn { width: 100%; }
  .ie-public-content { padding: 16px 12px; }
}
</style>
