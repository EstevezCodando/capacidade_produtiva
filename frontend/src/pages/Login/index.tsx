// ============================================================
// Login — autentica via proxy do backend CP
// ============================================================
import { apiClient } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Login.module.css";

interface LoginResponse {
  success: boolean;
  token: string;
  uuid: string;
  administrador: boolean;
}

interface UsuarioMe {
  uuid: string;
  login: string;
  nome: string;
  administrador: boolean;
}

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true);
    setError(null);

    try {
      // 1. Autentica via proxy do backend CP
      //    POST /api/login → { usuario, senha }
      //    O backend repassa para o servico_autenticacao
      const loginRes = await apiClient.post<LoginResponse>("/login", {
        usuario: username,
        senha: password,
      });

      const { token, uuid, administrador } = loginRes.data;

      if (!token) {
        throw new Error("Token não retornado pelo serviço de autenticação");
      }

      // 2. Injeta token para buscar perfil completo
      apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;

      // 3. Busca dados do usuário
      let usuario: UsuarioMe;
      try {
        const meRes = await apiClient.get<UsuarioMe>("/usuarios/me");
        usuario = meRes.data;
      } catch {
        // Se /usuarios/me falhar, usa dados do login
        usuario = {
          uuid,
          login: username,
          nome: username,
          administrador,
        };
      }

      // 4. Salva sessão
      login(token, usuario);
      navigate("/", { replace: true });
    } catch (err) {
      let msg = "Erro ao autenticar";
      if (err instanceof Error) {
        msg = err.message;
      }
      // Axios error
      if (typeof err === "object" && err !== null && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        msg = axiosErr.response?.data?.detail ?? msg;
      }
      setError(msg);
      delete apiClient.defaults.headers.common["Authorization"];
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.root}>
      {/* Grade de fundo decorativa */}
      <div className={styles.grid} aria-hidden="true" />

      <div className={styles.card}>
        {/* Logo / título */}
        <div className={styles.header}>
          <img src="/dsg-logo.png" alt="DSG" className={styles.logoImg} />
          <div>
            <h1 className={styles.title}>DSG</h1>
            <p className={styles.subtitle}>Sistema de Gestão Operacional</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className={styles.form} noValidate>
          <div className={styles.field}>
            <label htmlFor="username" className={styles.label}>
              Usuário
            </label>
            <input
              id="username"
              type="text"
              className={styles.input}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              disabled={loading}
              placeholder="login"
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="password" className={styles.label}>
              Senha
            </label>
            <input
              id="password"
              type="password"
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              disabled={loading}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className={styles.errorBox} role="alert">
              <span className={styles.errorIcon}>⚠</span>
              {error}
            </div>
          )}

          <button
            type="submit"
            className={styles.btn}
            disabled={loading || !username || !password}
          >
            {loading ? (
              <span className={styles.spinner} aria-hidden="true" />
            ) : null}
            {loading ? "Autenticando…" : "Entrar"}
          </button>
        </form>

        <p className={styles.footer}>
          Autenticação via serviço centralizado de identidade
        </p>
      </div>
    </div>
  );
}
