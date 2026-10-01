<script setup>
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import logo from "../../assets/images/logo-mark.png";
import LanguageSwitcher from "../../components/LanguageSwitcher.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const username = ref("");
const password = ref("");
const showPassword = ref(false);
const errorMessage = ref("");
const loading = ref(false);
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
    await auth.login(username.value, password.value);
    router.push(route.query.next || { name: "dashboard" });
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || t("auth.login.errorDefault");
  } finally {
    loading.value = false;
  }
}


</script>

<template>
  <div class="ie-split">
    <!-- ======================= PANNEAU DE GAUCHE ======================= -->
    <aside class="ie-split-hero" :style="heroPhoto ? { backgroundImage: `url(${heroPhoto})` } : {}">
      <div class="ie-split-hero-scrim"></div>
      <div class="ie-split-hero-inner">
        <div class="ie-split-brand-row">
          <router-link :to="{ name: 'landing' }" class="ie-split-brand">
            <img :src="logo" alt="InnovEvent" class="ie-split-logo" />
            <span class="ie-split-brand-word">InnovEvent<span>Group</span></span>
          </router-link>
          <LanguageSwitcher />
        </div>

        <div class="ie-split-hero-body">
          <p class="ie-split-eyebrow">Espace client</p>
          <h1>Un projet,<br />une seule équipe.</h1>
          <p class="ie-split-hero-lede">Rejoignez InnovEvent pour organiser vos événements, louer votre matériel ou suivre votre formation — depuis un espace unique et sécurisé.</p>

          <div class="ie-split-services">
            <div class="ie-split-service">
              <span class="ie-split-service-icon"><i class="fa-solid fa-calendar-week"></i></span>
              <div>
                <strong>Organisation d'événements</strong>
                <span>Salles, prestataires, billetterie et suivi budgétaire.</span>
              </div>
            </div>
            <div class="ie-split-service">
              <span class="ie-split-service-icon"><i class="fa-solid fa-sliders"></i></span>
              <div>
                <strong>Location de matériel</strong>
                <span>Mobilier, sonorisation, éclairage et chapiteaux.</span>
              </div>
            </div>
            <div class="ie-split-service">
              <span class="ie-split-service-icon"><i class="fa-solid fa-graduation-cap"></i></span>
              <div>
                <strong>InnovEvent Academy</strong>
                <span>Formations certifiantes aux métiers de l'événementiel.</span>
              </div>
            </div>
          </div>
        </div>

        <p class="ie-split-footer">© 2026 InnovEvent Group · Douala · Yaoundé · Bafoussam</p>
      </div>
    </aside>

    <!-- ======================= PANNEAU DE DROITE (FORMULAIRE) ======================= -->
    <main class="ie-split-form">
      <div class="ie-split-form-inner">
        <h2>{{ $t("auth.login.welcomeBack") }}</h2>
        <p class="ie-split-lead">{{ $t("auth.login.lead") }}</p>

        <form @submit.prevent="handleSubmit">
          <label class="ie-label" for="username">{{ $t("auth.login.username") }}</label>
          <div class="ie-split-input-wrap">
            <i class="fa-solid fa-user"></i>
            <input id="username" v-model="username" class="ie-input" required autofocus :placeholder="$t('auth.login.usernamePlaceholder')" />
          </div>

          <label class="ie-label" for="password" style="margin-top: 16px;">{{ $t("auth.login.password") }}</label>
          <div class="ie-split-input-wrap">
            <i class="fa-solid fa-lock"></i>
            <input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" class="ie-input" required placeholder="••••••••••" />
            <button type="button" class="ie-split-toggle-pw" @click="showPassword = !showPassword" :aria-label="showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'">
              <i class="fa-solid" :class="showPassword ? 'fa-eye-slash' : 'fa-eye'"></i>
            </button>
          </div>

          <p v-if="errorMessage" class="ie-auth-error">{{ errorMessage }}</p>

          <button class="ie-btn ie-btn-primary ie-split-submit" type="submit" :disabled="loading">
            {{ loading ? $t("auth.login.submitting") : $t("auth.login.submit") }} <i v-if="!loading" class="fa-solid fa-arrow-right"></i>
          </button>

          <router-link :to="{ name: 'forgot-password' }" class="ie-split-forgot-link">{{ $t("auth.login.forgotPassword") }}</router-link>
        </form>

        <p class="ie-auth-footer">{{ $t("auth.login.noAccount") }} <router-link to="/register">{{ $t("auth.login.createAccount") }}</router-link></p>
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

/* Panneau de gauche */
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
.ie-split-brand-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
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

.ie-split-services { display: flex; flex-direction: column; gap: 10px; }
.ie-split-service {
  display: flex; align-items: center; gap: 15px; background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 15px 17px;
  transition: background 0.25s ease, border-color 0.25s ease, transform 0.25s ease;
}
.ie-split-service:hover { background: rgba(255, 255, 255, 0.09); border-color: rgba(255, 255, 255, 0.2); transform: translateY(-1px); }
.ie-split-service-icon {
  width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
  background: linear-gradient(150deg, rgba(192, 39, 45, 0.35), rgba(192, 39, 45, 0.12));
  border: 1px solid rgba(192, 39, 45, 0.4); color: #f3b9bc;
  display: flex; align-items: center; justify-content: center; font-size: 15px;
}
.ie-split-service strong { display: block; font-size: 0.93rem; font-weight: 600; margin-bottom: 3px; letter-spacing: -0.005em; }
.ie-split-service span { display: block; font-size: 0.8rem; color: rgba(255, 255, 255, 0.62); line-height: 1.4; }

.ie-split-footer { font-size: 0.76rem; color: rgba(255, 255, 255, 0.4); letter-spacing: 0.01em; }

/* Panneau de droite */
.ie-split-form { display: flex; align-items: center; justify-content: center; padding: 40px 32px; background: var(--ie-white); overflow-y: auto; }
.ie-split-form-inner { width: 100%; max-width: 384px; animation: ie-rise 0.6s 0.08s cubic-bezier(0.22, 0.68, 0, 1) both; }
.ie-split-form-inner h2 { font-size: 1.85rem; font-weight: 500; color: var(--ie-ink); margin: 0 0 10px; letter-spacing: -0.01em; }
.ie-split-lead { color: var(--ie-muted); font-size: 0.93rem; line-height: 1.5; margin-bottom: 32px; }

.ie-split-forgot-link { display: block; text-align: center; margin-top: 16px; font-size: 0.84rem; font-weight: 600; color: var(--ie-red); }
.ie-split-forgot-link:hover { text-decoration: underline; }

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

@keyframes ie-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { .ie-split-hero-inner, .ie-split-form-inner { animation: none; } }

@media (max-width: 920px) {
  .ie-split { grid-template-columns: 1fr; }
  .ie-split-hero { padding: 32px 24px; min-height: 300px; }
  .ie-split-hero-body { padding: 24px 0; margin: 0; }
  .ie-split-hero-body h1 { font-size: 1.7rem; }
  .ie-split-hero-lede { margin-bottom: 20px; }
  .ie-split-services { display: none; }
  .ie-split-form { padding: 32px 24px 48px; }
}
</style>
