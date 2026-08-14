import axios from "axios";

const baseURL =
  typeof import.meta.env.VITE_API_URL === "string" &&
  import.meta.env.VITE_API_URL.length > 0
    ? import.meta.env.VITE_API_URL
    : "";

export const apiClient = axios.create({
  baseURL,
  timeout: 180_000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const path = window.location.pathname;
      if (path !== "/login" && path !== "/auth/callback") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
