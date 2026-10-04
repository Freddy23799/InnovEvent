import axios from "axios";
import { getAccessToken, setAccessToken } from "./authToken";

// En production l'API est publiée derrière le même domaine que le frontend.
// Une URL relative évite qu'un build oublié tente d'appeler le localhost du
// visiteur, ce qui rendrait l'application vide hors environnement local.
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const api = axios.create({ baseURL, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let pendingRequests = [];

function resolvePending(token, error = null) {
  pendingRequests.forEach((callback) => callback(token, error));
  pendingRequests = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    if (!response || response.status !== 401 || config._retried) {
      return Promise.reject(error);
    }

    if (!getAccessToken() || String(config.url || "").includes("/auth/refresh/")) {
      return Promise.reject(error);
    }

    config._retried = true;

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingRequests.push((token, refreshError) => {
          if (refreshError) {
            reject(refreshError);
            return;
          }
          config.headers.Authorization = `Bearer ${token}`;
          resolve(api(config));
        });
      });
    }

    isRefreshing = true;
    try {
      const { data } = await axios.post(`${baseURL}/auth/refresh/`, {}, {
        withCredentials: true,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      setAccessToken(data.access);
      resolvePending(data.access);
      config.headers.Authorization = `Bearer ${data.access}`;
      return api(config);
    } catch (refreshError) {
      resolvePending(null, refreshError);
      setAccessToken(null);
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
