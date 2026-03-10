// ============================================================
// API Client — Axios com interceptor JWT
// Base URL: /api  (proxied to localhost:3050 em dev)
// ============================================================
import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api",
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

// Injeta token em toda requisição autenticada
apiClient.interceptors.request.use((config) => {
  const raw = localStorage.getItem("cp_sessao");
  if (raw) {
    try {
      const sessao = JSON.parse(raw) as { token: string };
      // Garante que o token tenha prefixo Bearer
      const token = sessao.token;
      if (token) {
        config.headers.Authorization = token.startsWith("Bearer ")
          ? token
          : `Bearer ${token}`;
      }
    } catch {
      // sessão corrompida — ignora
    }
  }
  return config;
});

// Redireciona para login em 401
apiClient.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("cp_sessao");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);
