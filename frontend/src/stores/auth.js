import { defineStore } from "pinia";
import api from "../services/api";
import { setAccessToken } from "../services/authToken";

// Supprime les anciens JWT persistés par les versions antérieures de l'app.
if (typeof localStorage !== "undefined") {
  localStorage.removeItem("ie_access_token");
  localStorage.removeItem("ie_refresh_token");
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: null,
    user: null,
    role: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },
  actions: {
    async login(username, password) {
      const { data } = await api.post("/auth/login/", { username, password });
      this._setTokens(data.access);
      await this.fetchMe();
    },
    async register(payload) {
      await api.post("/auth/register/", payload);
    },
    async fetchMe() {
      const { data } = await api.get("/auth/me/");
      this.user = data;
      this.role = data.role;
    },
    async logout() {
      try {
        await api.post("/auth/logout/", {}, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      } catch (e) {
        // best-effort : le token expirera de toute façon côté serveur
      }
      this.accessToken = null;
      this.user = null;
      this.role = null;
      setAccessToken(null);
    },
    async restoreSession() {
      try {
        const { data } = await api.post("/auth/refresh/", {}, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        this._setTokens(data.access);
        await this.fetchMe();
      } catch (e) {
        this.accessToken = null;
        this.user = null;
        this.role = null;
        setAccessToken(null);
      }
    },
    _setTokens(access) {
      this.accessToken = access;
      setAccessToken(access);
    },
  },
});

if (typeof window !== "undefined") {
  window.addEventListener("ie-access-token-changed", (event) => {
    useAuthStore().accessToken = event.detail;
  });
}
