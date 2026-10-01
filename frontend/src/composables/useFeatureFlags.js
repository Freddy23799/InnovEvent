import { computed, unref } from "vue";
import api from "../services/api";

/**
 * Petite couche de lecture autour du moteur de permissions marketplace
 * (backend : apps.marketplace.feature_engine.resolve_features). Ne code
 * jamais de condition par fonctionnalité : elle se contente de lire ce que
 * l'API a déjà résolu pour l'utilisateur courant.
 */
export function useFeatureFlags(featuresRef) {
  const byKey = computed(() => {
    const list = unref(featuresRef) || [];
    return Object.fromEntries(list.map((f) => [f.key, f]));
  });

  function isVisible(key) {
    return byKey.value[key]?.visible ?? false;
  }
  function isLocked(key) {
    return byKey.value[key]?.locked ?? false;
  }
  function isUsable(key) {
    return isVisible(key) && !isLocked(key);
  }
  function upsellMessage(key) {
    return byKey.value[key]?.upsell_message || "";
  }

  return { byKey, isVisible, isLocked, isUsable, upsellMessage };
}

export async function fetchMarketplaceFeatures(marketplaceType) {
  const { data } = await api.get("/marketplace/features/resolve/", { params: { marketplace_type: marketplaceType } });
  return data;
}
