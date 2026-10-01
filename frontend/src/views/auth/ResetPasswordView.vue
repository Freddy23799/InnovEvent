<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import logo from "../../assets/images/logo-mark.png";
import api from "../../services/api";

const route = useRoute();
const router = useRouter();

const uid = computed(() => route.query.uid || "");
const token = computed(() => route.query.token || "");
const linkMissing = computed(() => !uid.value || !token.value);

const newPassword = ref("");
const confirmPassword = ref("");
const showPassword = ref(false);
const loading = ref(false);
const errorMessage = ref("");
const success = ref(false);
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
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = "Les deux mots de passe ne correspondent pas.";
    return;
  }
  loading.value = true;
  try {
    await api.post("/auth/password-reset/confirm/", {
      uid: uid.value,
      token: token.value,
      new_password: newPassword.value,
    });
    success.value = true;
    setTimeout(() => router.push({ name: "login" }), 2500);
  } catch (e) {
    const detail = e?.response?.data?.detail;
    errorMessage.value = typeof detail === "string" ? detail : "Ce lien de réinitialisation est invalide ou a expiré.";
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
          <h1>Choisissez<br />un nouveau mot de passe.</h1>
          <p class="ie-split-hero-lede">Pour votre sécurité, choisissez un mot de passe d'au moins 12 caractères que vous n'utilisez sur aucun autre site.</p>
        </div>
        <p class="ie-split-footer">© 2026 InnovEvent Group · Douala · Yaoundé · Bafoussam</p>
      </div>
    </aside>

    <main class="ie-split-form">
      <div class="ie-split-form-inner">
        <template v-if="linkMissing">
          <h2>Lien invalide</h2>
          <p class="ie-split-lead">Ce lien de réinitialisation est incomplet ou invalide. Refaites une demande depuis la page de connexion.</p>
        </template>

        <template v-else-if="success">
          <div class="ie-auth-success-icon"><i class="fa-solid fa-circle-check"></i></div>
          <h2>Mot de passe mis à jour</h2>
          <p class="ie-split-lead">Votre mot de passe a été réinitialisé avec succès. Redirection vers la connexion…</p>
        </template>

        <template v-else>
          <h2>Nouveau mot de passe</h2>
          <p class="ie-split-lead">Choisissez un nouveau mot de passe pour votre compte.</p>

          <form @submit.prevent="handleSubmit">
            <label class="ie-label" for="newPassword">Nouveau mot de passe</label>
            <div class="ie-split-input-wrap">
              <i class="fa-solid fa-lock"></i>
              <input id="newPassword" v-model="newPassword" :type="showPassword ? 'text' : 'password'" class="ie-input" required minlength="12" placeholder="••••••••••" />
              <button type="button" class="ie-split-toggle-pw" @click="showPassword = !showPassword" :aria-label="showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'">
                <i class="fa-solid" :class="showPassword ? 'fa-eye-slash' : 'fa-eye'"></i>
              </button>
            </div>

            <label class="ie-label" for="confirmPassword" style="margin-top: 16px;">Confirmer le mot de passe</label>
            <div class="ie-split-input-wrap">
              <i class="fa-solid fa-lock"></i>
              <input id="confirmPassword" v-model="confirmPassword" :type="showPassword ? 'text' : 'password'" class="ie-input" required minlength="12" placeholder="••••••••••" />
            </div>

            <p v-if="errorMessage" class="ie-auth-error">{{ errorMessage }}</p>

            <button class="ie-btn ie-btn-primary ie-split-submit" type="submit" :disabled="loading">
              {{ loading ? "Mise à jour…" : "Réinitialiser mon mot de passe" }} <i v-if="!loading" class="fa-solid fa-arrow-right"></i>
            </button>
          </form>
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
.ie-split-toggle-pw {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  display: flex; align-items: center; justify-content: center; width: 28px; height: 28px;
  background: none; border: 0; color: var(--ie-muted); cursor: pointer; font-size: 14px; border-radius: 8px;
  transition: color 0.2s, background 0.2s;
}
.ie-split-toggle-pw:hover { color: var(--ie-ink); background: var(--ie-navy-soft); }
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
