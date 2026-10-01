import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ie_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let pendingRequests = [];

function resolvePending(token) {
  pendingRequests.forEach((cb) => cb(token));
  pendingRequests = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    if (!response || response.status !== 401 || config._retried) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("ie_refresh_token");
    if (!refreshToken) {
      return Promise.reject(error);
    }

    config._retried = true;

    if (isRefreshing) {
      return new Promise((resolve) => {
        pendingRequests.push((token) => {
          config.headers.Authorization = `Bearer ${token}`;
          resolve(api(config));
        });
      });
    }

    isRefreshing = true;
    try {
      const { data } = await axios.post(`${baseURL}/auth/refresh/`, { refresh: refreshToken });
      localStorage.setItem("ie_access_token", data.access);
      resolvePending(data.access);
      config.headers.Authorization = `Bearer ${data.access}`;
      return api(config);
    } catch (refreshError) {
      localStorage.removeItem("ie_access_token");
      localStorage.removeItem("ie_refresh_token");
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
