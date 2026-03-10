import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import AppShell    from '@/components/layout/AppShell'
import Login       from '@/pages/Login'
import Dashboard       from '@/pages/Dashboard'
import MinhaAgenda     from '@/pages/MinhaAgenda'
import GerenciarAgendas from '@/pages/GerenciarAgendas'
import Operadores      from '@/pages/Operadores'
import BlocosProjeto   from '@/pages/BlocosProjeto'
import Atividades      from '@/pages/Atividades'
import Exportar        from '@/pages/Exportar'
import Perfil          from '@/pages/Perfil'

// Rota protegida — redireciona para /login se não autenticado
function Protected({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { sessao, ehAdmin } = useAuth()
  if (!sessao) return <Navigate to="/login" replace />
  if (adminOnly && !ehAdmin) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  const { sessao } = useAuth()

  return (
    <Routes>
      {/* Login — redireciona para home se já autenticado */}
      <Route
        path="/login"
        element={sessao ? <Navigate to="/" replace /> : <Login />}
      />

      {/* Área autenticada */}
      <Route
        path="/*"
        element={
          <Protected>
            <AppShell>
              <Routes>
                <Route index                element={<Dashboard />} />
                <Route path="blocos"        element={<BlocosProjeto />} />
                <Route path="atividades"    element={<Atividades />} />
                <Route path="exportar"      element={<Exportar />} />
                <Route path="agenda"        element={<MinhaAgenda />} />
                <Route path="agendas"       element={<Protected adminOnly><GerenciarAgendas /></Protected>} />
                <Route path="operadores"    element={<Protected adminOnly><Operadores /></Protected>} />
                <Route path="perfil"        element={<Perfil />} />
                <Route path="*"             element={<Navigate to="/" replace />} />
              </Routes>
            </AppShell>
          </Protected>
        }
      />
    </Routes>
  )
}
