<script setup>
import { onMounted, ref } from "vue";
import logo from "../../assets/images/logo-mark.png";
import api from "../../services/api";

const email = ref("");
const loading = ref(false);
const errorMessage = ref("");
const submitted = ref(false);
const heroPhoto = ref(null);

onMounted(async () => {
  try {
    const { data } = await api.get("/public/landing-media/", { params: { category: "realisation" } });
    heroPhoto.value = data.find((item) => item.photo)?.photo || null;
  } catch {
    heroPhoto.value = null;
  }
});

async function handleSubmit() {
  errorMessage.value = "";
  loading.value = true;
  try {
    await api.post("/auth/password-reset/", { email: email.value });
    submitted.value = true;
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'envoyer l'email pour le moment. Réessayez plus tard.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="ie-split">
    <aside class="ie-split-hero" :style="heroPhoto ? { backgroundImage: `url(${heroPhoto})` } : {}">
      <div class="ie-split-hero-scrim"></div>
      <div class="ie-split-hero-inner">
        <router-link :to="{ name: 'landing' }" class="ie-split-brand">
          <img :src="logo" alt="InnovEvent" class="ie-split-logo" />
          <span class="ie-split-brand-word">InnovEvent<span>Group</span></span>
        </router-link>
        <div class="ie-split-hero-body">
          <p class="ie-split-eyebrow">Espace client</p>
          <h1>Récupérez<br />l'accès à votre compte.</h1>
          <p class="ie-split-hero-lede">Indiquez l'adresse email associée à votre compte : nous vous envoyons un lien sécurisé pour choisir un nouveau mot de passe.</p>
        </div>
        <p class="ie-split-footer">© 2026 InnovEvent Group · Douala · Yaoundé · Bafoussam</p>
      </div>
    </aside>

    <main class="ie-split-form">
      <div class="ie-split-form-inner">
        <template v-if="!submitted">
          <h2>Mot de passe oublié ?</h2>
          <p class="ie-split-lead">Saisissez votre adresse email, nous vous enverrons un lien de réinitialisation.</p>

          <form @submit.prevent="handleSubmit">
            <label class="ie-label" for="email">Adresse email</label>
            <div class="ie-split-input-wrap">
              <i class="fa-solid fa-envelope"></i>
              <input id="email" v-model="email" type="email" class="ie-input" required autofocus placeholder="vous@exemple.com" />
            </div>

            <p v-if="errorMessage" class="ie-auth-error">{{ errorMessage }}</p>

            <button class="ie-btn ie-btn-primary ie-split-submit" type="submit" :disabled="loading">
              {{ loading ? "Envoi en cours…" : "Envoyer le lien de réinitialisation" }} <i v-if="!loading" class="fa-solid fa-paper-plane"></i>
            </button>
          </form>
        </template>

        <template v-else>
          <div class="ie-auth-success-icon"><i class="fa-solid fa-envelope-circle-check"></i></div>
          <h2>Vérifiez votre boîte mail</h2>
          <p class="ie-split-lead">Si un compte existe pour <strong>{{ email }}</strong>, un email contenant un lien de réinitialisation vient de lui être envoyé. Pensez à vérifier vos spams.</p>
        </template>

        <p class="ie-auth-footer"><router-link :to="{ name: 'login' }"><i class="fa-solid fa-arrow-left" style="margin-right: 6px;"></i>Retour à la connexion</router-link></p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.ie-split {
  min-height: 100vh; display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
.ie-split :is(h1, h2) { font-family: "Fraunces", Georgia, serif; text-wrap: balance; }

.ie-split-hero {
  position: relative; display: flex; background: #1c2530 center/cover no-repeat; color: #fff;
  padding: 52px 56px; overflow: hidden;
}
.ie-split-hero-scrim {
  position: absolute; inset: 0;
  background:
    radial-gradient(120% 90% at 100% 0%, rgba(192, 39, 45, 0.38), transparent 55%),
    linear-gradient(195deg, rgba(20, 27, 36, 0.97) 20%, rgba(30, 20, 26, 0.93) 75%, rgba(58, 16, 22, 0.9) 130%);
}
.ie-split-hero-inner { position: relative; display: flex; flex-direction: column; justify-content: space-between; width: 100%; height: 100%; animation: ie-rise 0.6s cubic-bezier(0.22, 0.68, 0, 1) both; }
.ie-split-brand { display: flex; align-items: center; gap: 11px; }
.ie-split-logo { height: 34px; width: auto; }
.ie-split-brand-word { font-size: 1.02rem; font-weight: 700; letter-spacing: -0.01em; }
.ie-split-brand-word span { color: var(--ie-red-soft); text-transform: uppercase; font-size: 0.6em; letter-spacing: 0.16em; margin-left: 4px; font-weight: 800; }

.ie-split-hero-body { max-width: 460px; margin: auto 0; padding: 48px 0; }
.ie-split-eyebrow {
  display: inline-flex; align-items: center; gap: 8px; font-size: 0.72rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.16em; color: rgba(255, 255, 255, 0.62); margin: 0 0 18px;
}
.ie-split-eyebrow::before { content: ""; width: 22px; height: 1.5px; background: var(--ie-red); display: inline-block; }
.ie-split-hero-body h1 { font-size: clamp(2rem, 3.4vw, 2.75rem); font-weight: 500; line-height: 1.14; letter-spacing: -0.01em; margin: 0 0 20px; color: #fff; }
.ie-split-hero-lede { color: rgba(255, 255, 255, 0.72); font-size: 1rem; line-height: 1.65; margin: 0 0 34px; }

.ie-split-footer { font-size: 0.76rem; color: rgba(255, 255, 255, 0.4); letter-spacing: 0.01em; }

.ie-split-form { display: flex; align-items: center; justify-content: center; padding: 40px 32px; background: var(--ie-white); overflow-y: auto; }
.ie-split-form-inner { width: 100%; max-width: 384px; animation: ie-rise 0.6s 0.08s cubic-bezier(0.22, 0.68, 0, 1) both; }
.ie-split-form-inner h2 { font-size: 1.85rem; font-weight: 500; color: var(--ie-ink); margin: 0 0 10px; letter-spacing: -0.01em; }
.ie-split-lead { color: var(--ie-muted); font-size: 0.93rem; line-height: 1.5; margin-bottom: 32px; }

.ie-split-input-wrap { position: relative; }
.ie-split-input-wrap i:first-child { position: absolute; left: 15px; top: 50%; transform: translateY(-50%); color: var(--ie-muted); font-size: 14px; pointer-events: none; }
.ie-split-input-wrap .ie-input {
  padding: 13px 44px 13px 42px; border-radius: 10px; border-color: var(--ie-line);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.ie-split-input-wrap .ie-input:focus {
  outline: none; border-color: var(--ie-navy); box-shadow: 0 0 0 3.5px rgba(57, 73, 91, 0.12);
}
.ie-split-submit {
  width: 100%; margin-top: 26px; padding: 13px; border-radius: 10px; font-size: 0.95rem;
  display: flex; align-items: center; justify-content: center; gap: 9px;
  box-shadow: 0 10px 24px rgba(192, 39, 45, 0.22); transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
.ie-split-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 30px rgba(192, 39, 45, 0.3); }
.ie-split-submit i { font-size: 13px; transition: transform 0.2s ease; }
.ie-split-submit:hover:not(:disabled) i { transform: translateX(3px); }

.ie-auth-error { color: var(--ie-red); font-size: 13px; margin-top: 12px; text-align: left; }
.ie-auth-footer { text-align: center; font-size: 0.86rem; color: var(--ie-muted); margin-top: 26px; }
.ie-auth-footer a { color: var(--ie-red); font-weight: 700; }

.ie-auth-success-icon { font-size: 40px; color: var(--ie-red); margin-bottom: 18px; }

@keyframes ie-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { .ie-split-hero-inner, .ie-split-form-inner { animation: none; } }

@media (max-width: 920px) {
  .ie-split { grid-template-columns: 1fr; }
  .ie-split-hero { padding: 32px 24px; min-height: 300px; }
  .ie-split-hero-body { padding: 24px 0; margin: 0; }
  .ie-split-hero-body h1 { font-size: 1.7rem; }
  .ie-split-hero-lede { margin-bottom: 20px; }
  .ie-split-form { padding: 32px 24px 48px; }
}
</style>
