import { jwtDecode } from "../utils/jwt";
import { defineStore } from "pinia";
import api from "../services/api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: localStorage.getItem("ie_access_token") || null,
    refreshToken: localStorage.getItem("ie_refresh_token") || null,
    user: null,
    role: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },
  actions: {
    async login(username, password) {
      const { data } = await api.post("/auth/login/", { username, password });
      this._setTokens(data.access, data.refresh);
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
        if (this.refreshToken) {
          await api.post("/auth/logout/", { refresh: this.refreshToken });
        }
      } catch (e) {
        // best-effort : le token expirera de toute façon côté serveur
      }
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      this.role = null;
      localStorage.removeItem("ie_access_token");
      localStorage.removeItem("ie_refresh_token");
    },
    async restoreSession() {
      if (!this.accessToken) return;
      try {
        await this.fetchMe();
      } catch (e) {
        await this.logout();
      }
    },
    _setTokens(access, refresh) {
      this.accessToken = access;
      this.refreshToken = refresh;
      localStorage.setItem("ie_access_token", access);
      localStorage.setItem("ie_refresh_token", refresh);
      const payload = jwtDecode(access);
      this.role = payload?.role || null;
    },
  },
});
