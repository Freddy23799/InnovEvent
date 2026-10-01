<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const form = reactive({ first_name: "", last_name: "", email: "", phone: "" });
const loading = ref(true);
const saving = ref(false);
const message = ref("");
const errorMessage = ref("");

async function loadProfile() {
  loading.value = true;
  await auth.fetchMe();
  Object.assign(form, {
    first_name: auth.user.first_name,
    last_name: auth.user.last_name,
    email: auth.user.email,
    phone: auth.user.phone,
  });
  loading.value = false;
}

async function saveProfile() {
  message.value = "";
  errorMessage.value = "";
  saving.value = true;
  try {
    await api.patch("/auth/me/", form);
    await auth.fetchMe();
    message.value = "Profil mis à jour avec succès.";
  } catch (e) {
    errorMessage.value = "Impossible de mettre à jour le profil.";
  } finally {
    saving.value = false;
  }
}

onMounted(loadProfile);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-user" style="color: var(--ie-red); margin-right: 8px;"></i>Mon profil</h1>

    <div class="ie-card" style="max-width: 560px; padding: 24px; margin-top: 20px;">
      <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>
      <form v-else @submit.prevent="saveProfile">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Prénom</label>
            <input v-model="form.first_name" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Nom</label>
            <input v-model="form.last_name" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Email</label>
        <input v-model="form.email" type="email" class="ie-input" />
        <label class="ie-label" style="margin-top: 14px;">Téléphone</label>
        <input v-model="form.phone" class="ie-input" />

        <div style="margin-top: 14px; font-size: 13px; color: var(--ie-muted);">
          Rôle : <span class="ie-badge ie-badge-neutral">{{ auth.role }}</span>
        </div>

        <p v-if="message" style="color: var(--ie-success); font-size: 13px; margin-top: 12px;">{{ message }}</p>
        <p v-if="errorMessage" style="color: var(--ie-red); font-size: 13px; margin-top: 12px;">{{ errorMessage }}</p>

        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="saving">
          {{ saving ? "Enregistrement…" : "Enregistrer" }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.ie-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
