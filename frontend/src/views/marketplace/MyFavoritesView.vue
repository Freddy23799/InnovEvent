<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import StarRating from "../../components/StarRating.vue";
import api from "../../services/api";

const favorites = ref([]);
const loading = ref(true);
const removing = reactive({});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/favorites/");
    favorites.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function removeFavorite(favorite) {
  removing[favorite.id] = true;
  try {
    await api.delete(`/marketplace/favorites/${favorite.id}/`);
    favorites.value = favorites.value.filter((f) => f.id !== favorite.id);
  } finally {
    removing[favorite.id] = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-heart" style="color: var(--ie-red); margin-right: 8px;"></i>Mes favoris</h1>
        <p class="ie-page-subtitle">Les prestataires que vous avez enregistrés pour les retrouver rapidement.</p>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>

    <div v-else-if="favorites.length" class="ie-favorites-grid">
      <div v-for="f in favorites" :key="f.id" class="ie-card ie-favorite-card">
        <button
          type="button" class="ie-favorite-remove" :disabled="removing[f.id]"
          @click="removeFavorite(f)" title="Retirer des favoris"
        >
          <i class="fa-solid fa-heart"></i>
        </button>
        <router-link :to="{ name: 'professional-profile-detail', params: { id: f.profile } }" class="ie-favorite-link">
          <div class="ie-favorite-cover">
            <img v-if="f.profile_detail.cover_photo" :src="f.profile_detail.cover_photo" :alt="f.profile_detail.business_name" />
            <i v-else class="fa-solid fa-image"></i>
          </div>
          <div class="ie-favorite-logo">
            <img v-if="f.profile_detail.logo" :src="f.profile_detail.logo" :alt="f.profile_detail.business_name" />
            <i v-else class="fa-solid fa-handshake"></i>
          </div>
          <div class="ie-card-body" style="padding-top: 6px;">
            <span class="ie-badge ie-badge-neutral">{{ f.profile_detail.category_display }}</span>
            <h3 style="margin-top: 8px;">{{ f.profile_detail.business_name }}</h3>
            <p v-if="f.profile_detail.city" class="ie-listing-provider"><i class="fa-solid fa-location-dot"></i> {{ f.profile_detail.city }}</p>
            <StarRating v-if="f.profile_detail.average_rating" :model-value="f.profile_detail.average_rating" :count="f.profile_detail.review_count" :size="12" />
          </div>
        </router-link>
      </div>
    </div>

    <EmptyState v-else icon="fa-solid fa-heart" text="Vous n'avez pas encore de prestataire favori." />
  </div>
</template>

<style scoped>
.ie-favorites-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 18px; }
.ie-favorite-card { position: relative; overflow: hidden; }
.ie-favorite-link { display: block; text-decoration: none; color: inherit; }
.ie-favorite-cover { height: 110px; background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center; }
.ie-favorite-cover img { width: 100%; height: 100%; object-fit: cover; }
.ie-favorite-cover i { font-size: 28px; color: var(--ie-navy); opacity: 0.3; }
.ie-favorite-logo {
  width: 56px; height: 56px; border-radius: 50%; overflow: hidden; background: #fff;
  border: 3px solid #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  margin: -32px 0 0 16px; display: flex; align-items: center; justify-content: center; position: relative;
}
.ie-favorite-logo img { width: 100%; height: 100%; object-fit: cover; }
.ie-favorite-logo i { font-size: 18px; color: var(--ie-navy); opacity: 0.4; }
.ie-favorite-remove {
  position: absolute; top: 8px; right: 8px; z-index: 2; width: 30px; height: 30px; border-radius: 50%;
  background: rgba(255,255,255,0.9); border: 0; display: flex; align-items: center; justify-content: center;
  color: var(--ie-red); font-size: 14px; cursor: pointer;
}
</style>
