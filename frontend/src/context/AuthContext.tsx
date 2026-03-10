// ============================================================
// AuthContext — gerencia sessão JWT no localStorage
// ============================================================
import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react'
import type { UsuarioMe, SessaoLocal } from '@/types'

const STORAGE_KEY = 'cp_sessao'

interface AuthContextValue {
  sessao:   SessaoLocal | null
  usuario:  UsuarioMe   | null
  token:    string      | null
  login:    (token: string, usuario: UsuarioMe) => void
  logout:   () => void
  ehAdmin:  boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function lerSessaoStorage(): SessaoLocal | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as SessaoLocal) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sessao, setSessao] = useState<SessaoLocal | null>(lerSessaoStorage)

  const login = useCallback((token: string, usuario: UsuarioMe) => {
    const nova: SessaoLocal = {
      token,
      usuario,
      login_em: new Date().toISOString(),
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nova))
    setSessao(nova)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setSessao(null)
  }, [])

  const value: AuthContextValue = {
    sessao,
    usuario:  sessao?.usuario ?? null,
    token:    sessao?.token   ?? null,
    login,
    logout,
    ehAdmin:  sessao?.usuario.administrador ?? false,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
