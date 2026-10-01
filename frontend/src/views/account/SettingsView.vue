<script setup>
import { reactive, ref } from "vue";
import api from "../../services/api";

const form = reactive({ old_password: "", new_password: "", new_password_confirm: "" });
const saving = ref(false);
const message = ref("");
const errorMessage = ref("");

async function changePassword() {
  message.value = "";
  errorMessage.value = "";
  if (form.new_password !== form.new_password_confirm) {
    errorMessage.value = "Les nouveaux mots de passe ne correspondent pas.";
    return;
  }
  saving.value = true;
  try {
    await api.post("/auth/change-password/", { old_password: form.old_password, new_password: form.new_password });
    message.value = "Mot de passe mis à jour avec succès.";
    form.old_password = "";
    form.new_password = "";
    form.new_password_confirm = "";
  } catch (e) {
    errorMessage.value = e?.response?.data?.old_password?.[0] || "Impossible de changer le mot de passe.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-gear" style="color: var(--ie-red); margin-right: 8px;"></i>Paramètres du compte</h1>

    <div class="ie-card" style="max-width: 480px; padding: 24px; margin-top: 20px;">
      <h2 style="margin-bottom: 16px;">Sécurité</h2>
      <form @submit.prevent="changePassword">
        <label class="ie-label">Mot de passe actuel</label>
        <input v-model="form.old_password" type="password" class="ie-input" required />

        <label class="ie-label" style="margin-top: 14px;">Nouveau mot de passe</label>
        <input v-model="form.new_password" type="password" class="ie-input" required />

        <label class="ie-label" style="margin-top: 14px;">Confirmer le nouveau mot de passe</label>
        <input v-model="form.new_password_confirm" type="password" class="ie-input" required />

        <p v-if="message" style="color: var(--ie-success); font-size: 13px; margin-top: 12px;">{{ message }}</p>
        <p v-if="errorMessage" style="color: var(--ie-red); font-size: 13px; margin-top: 12px;">{{ errorMessage }}</p>

        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="saving">
          {{ saving ? "Mise à jour…" : "Changer le mot de passe" }}
        </button>
      </form>
    </div>
  </div>
</template>
