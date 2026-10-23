import axios from "axios";
import { getAccessToken, setAccessToken } from "./authToken";
import { doneProgress, startProgress } from "./progress";

// En production l'API est publiée derrière le même domaine que le frontend.
// Une URL relative évite qu'un build oublié tente d'appeler le localhost du
// visiteur, ce qui rendrait l'application vide hors environnement local.
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const api = axios.create({ baseURL, withCredentials: true });

// Anti double envoi : deux requêtes d'écriture identiques (même méthode, même
// URL, même contenu) lancées pendant que la première est en cours — double
// clic, double appui sur Entrée — partagent la même réponse au lieu de créer
// deux fois la même chose côté serveur. Les envois de fichiers (FormData) ne
// sont pas comparables et passent normalement.
const defaultAdapter = axios.getAdapter(axios.defaults.adapter);
const inFlightWrites = new Map();

api.defaults.adapter = (config) => {
  const method = (config.method || "get").toLowerCase();
  if (method === "get" || (config.data != null && typeof config.data !== "string")) {
    return defaultAdapter(config);
  }
  const key = `${method} ${config.baseURL || ""}${config.url} ${config.data || ""} ${config.headers?.["Idempotency-Key"] || ""}`;
  if (inFlightWrites.has(key)) return inFlightWrites.get(key);
  const request = defaultAdapter(config).finally(() => inFlightWrites.delete(key));
  inFlightWrites.set(key, request);
  return request;
};

api.interceptors.request.use((config) => {
  if (!config._progressStarted) {
    config._progressStarted = true;
    startProgress();
  }
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

function finishProgress(config) {
  if (config?._progressStarted && !config._progressDone) {
    config._progressDone = true;
    doneProgress();
  }
}

api.interceptors.response.use(
  (response) => {
    finishProgress(response.config);
    return response;
  },
  async (error) => {
    finishProgress(error.config);
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
