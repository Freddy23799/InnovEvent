<template>
  <div class="ie-not-found">
    <h1>404</h1>
    <p>Cette page n'existe pas.</p>
    <router-link to="/" class="ie-btn ie-btn-primary">Retour à l'accueil</router-link>
  </div>
</template>

<style scoped>
.ie-not-found {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.ie-not-found h1 { font-size: 64px; color: var(--ie-red); }
</style>
