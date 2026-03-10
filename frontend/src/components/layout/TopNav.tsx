// ============================================================
// TopNav — barra superior final do sistema
// Contém: logo, tabs de navegação, alertas, sync badge, perfil
// ============================================================
import { useState, useRef, useEffect }         from 'react'
import { useNavigate, useLocation, NavLink }   from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth }                              from '@/context/AuthContext'
import { getSyncStatus, executarSync, getInconsistencias } from '@/api/endpoints'
import { formatDistanceToNow }                 from 'date-fns'
import { ptBR }                                from 'date-fns/locale'
import styles                                  from './TopNav.module.css'

// ── Tabs por perfil ──────────────────────────────────────────
const TABS_COMUNS = [
  { path: '/',           label: 'Dashboard'        },
  { path: '/blocos',     label: 'Blocos do Projeto' },
  { path: '/atividades', label: 'Atividades'        },
  { path: '/exportar',   label: 'Exportar'          },
]

const TABS_OPERADOR = [
  { path: '/agenda-prevista',  label: 'Agenda Prevista'  },
  { path: '/agenda-realizada', label: 'Agenda Realizada' },
]

const TABS_ADMIN = [
  { path: '/agenda-prevista',  label: 'Agenda Prevista'  },
  { path: '/agenda-realizada', label: 'Agenda Realizada' },
  { path: '/operadores', label: 'Operadores'        },
]

function useTabs(ehAdmin: boolean) {
  if (ehAdmin) return [...TABS_COMUNS, ...TABS_ADMIN]
  return [...TABS_COMUNS, ...TABS_OPERADOR]
}

// ── Ícones SVG inline ─────────────────────────────────────────
function IconoBell({ count }: { count: number }) {
  return (
    <span className={styles.iconBtn} aria-label={`${count} alertas`}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>
      {count > 0 && <span className={styles.badge}>{count > 99 ? '99+' : count}</span>}
    </span>
  )
}

function IconoSync({ spinning }: { spinning: boolean }) {
  return (
    <svg
      width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.2"
      className={spinning ? styles.spinIcon : ''}
    >
      <path d="M23 4v6h-6"/>
      <path d="M1 20v-6h6"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
  )
}

// ── Dropdown de alertas ──────────────────────────────────────
function AlertasDropdown({ onClose }: { onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ['inconsistencias'],
    queryFn:  getInconsistencias,
    staleTime: 60_000,
  })

  const itens = data?.itens ?? []

  const sevIcon: Record<string, string> = {
    NOTA_AUSENTE:             '⊘',
    NOTA_INVALIDA:            '⊘',
    INCONSISTENTE_CICLO:      '△',
    INCONSISTENTE_DIFICULDADE:'△',
  }

  return (
    <div className={styles.dropdown} role="dialog" aria-label="Alertas">
      <div className={styles.dropdownHeader}>
        <span>Inconsistências</span>
        <span className={styles.dropdownCount}>{data?.total ?? '—'}</span>
      </div>
      <div className={styles.dropdownBody}>
        {isLoading && (
          <p className={styles.dropdownEmpty}>Carregando…</p>
        )}
        {!isLoading && itens.length === 0 && (
          <p className={styles.dropdownEmpty}>Nenhuma inconsistência encontrada</p>
        )}
        {itens.slice(0, 8).map((item) => (
          <div key={item.ut_id} className={styles.alertItem}>
            <span className={styles.alertIcon}>{sevIcon[item.ocorrencia] ?? '!'}</span>
            <div className={styles.alertContent}>
              <span className={styles.alertTitle}>UT {item.ut_id} — {item.ocorrencia.replace(/_/g, ' ')}</span>
              <span className={styles.alertMeta}>
                {item.projeto_nome ?? '—'} · {item.subfase_nome ?? '—'} · {item.nome_executor ?? '—'}
              </span>
            </div>
          </div>
        ))}
        {itens.length > 8 && (
          <p className={styles.dropdownMore}>+{itens.length - 8} ocorrências — ver em Atividades</p>
        )}
      </div>
      <div className={styles.dropdownFooter}>
        <button className={styles.dropdownClose} onClick={onClose}>Fechar</button>
      </div>
    </div>
  )
}

// ── Dropdown de perfil ───────────────────────────────────────
function PerfilDropdown({ onClose }: { onClose: () => void }) {
  const { usuario, sessao, logout, ehAdmin } = useAuth()
  const navigate = useNavigate()

  const loginEm = sessao?.login_em
    ? formatDistanceToNow(new Date(sessao.login_em), { addSuffix: true, locale: ptBR })
    : '—'

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className={styles.dropdown} role="dialog" aria-label="Perfil">
      {/* Identidade */}
      <div className={styles.perfilHeader}>
        <div className={styles.avatar}>
          {(usuario?.nome_guerra ?? usuario?.nome ?? '?')[0].toUpperCase()}
        </div>
        <div>
          <p className={styles.perfilNome}>{usuario?.nome ?? '—'}</p>
          <p className={styles.perfilGuerra}>{usuario?.nome_guerra ?? ''}</p>
          <span className={`${styles.perfilBadge} ${ehAdmin ? styles.perfilBadgeAdmin : styles.perfilBadgeOp}`}>
            {ehAdmin ? 'Administrador' : 'Operador'}
          </span>
        </div>
      </div>

      {/* Log de acesso */}
      <div className={styles.perfilMeta}>
        <div className={styles.perfilMetaRow}>
          <span className={styles.perfilMetaLabel}>Último acesso</span>
          <span className={styles.perfilMetaVal}>{loginEm}</span>
        </div>
        <div className={styles.perfilMetaRow}>
          <span className={styles.perfilMetaLabel}>UUID</span>
          <span className={`${styles.perfilMetaVal} ${styles.perfilUuid}`}>
            {usuario?.usuario_uuid.slice(0, 8)}…
          </span>
        </div>
      </div>

      {/* Ações */}
      <div className={styles.perfilAcoes}>
        <button
          className={styles.perfilAcao}
          onClick={() => { navigate('/perfil'); onClose() }}
        >
          Ver perfil completo
        </button>
        {ehAdmin && (
          <button
            className={styles.perfilAcao}
            onClick={() => { navigate('/perfil?tab=configuracoes'); onClose() }}
          >
            Configurações do sistema
          </button>
        )}
        <button className={`${styles.perfilAcao} ${styles.perfilAcaoLogout}`} onClick={handleLogout}>
          Sair
        </button>
      </div>
    </div>
  )
}

// ── TopNav principal ─────────────────────────────────────────
export default function TopNav() {
  const { usuario, ehAdmin, sessao } = useAuth()
  const location  = useLocation()
  const queryClient = useQueryClient()

  const tabs = useTabs(ehAdmin)

  const [alertasAberto, setAlertasAberto] = useState(false)
  const [perfilAberto,  setPerfilAberto]  = useState(false)

  const alertasRef = useRef<HTMLDivElement>(null)
  const perfilRef  = useRef<HTMLDivElement>(null)

  // Fecha dropdowns ao clicar fora
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (alertasRef.current && !alertasRef.current.contains(e.target as Node)) {
        setAlertasAberto(false)
      }
      if (perfilRef.current && !perfilRef.current.contains(e.target as Node)) {
        setPerfilAberto(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Sync status
  const { data: syncData } = useQuery({
    queryKey:  ['syncStatus'],
    queryFn:   getSyncStatus,
    refetchInterval: 30_000,
    enabled:   ehAdmin,
  })

  const syncMut = useMutation({
    mutationFn: executarSync,
    onSuccess:  () => {
      void queryClient.invalidateQueries({ queryKey: ['syncStatus'] })
    },
  })

  // Inconsistências para badge
  const { data: inconsData } = useQuery({
    queryKey:  ['inconsistencias'],
    queryFn:   getInconsistencias,
    staleTime: 60_000,
    enabled:   ehAdmin,
  })

  const nAlertas  = inconsData?.total ?? 0
  const syncTs    = syncData?.sap_snapshot_atualizado_em
  const syncLabel = syncTs
    ? formatDistanceToNow(new Date(syncTs), { addSuffix: true, locale: ptBR })
    : 'nunca'

  const initials = (usuario?.nome_guerra ?? usuario?.nome ?? 'U')
    .split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()

  return (
    <header className={styles.nav}>
      {/* ── Esquerda: logo + tabs ─────────────────────────── */}
      <div className={styles.left}>
        <div className={styles.logo}>
          <span className={styles.logoMark}>CP</span>
          <span className={styles.logoName}>CapacidadeProdutiva</span>
        </div>

        <nav className={styles.tabs} aria-label="Navegação principal">
          {tabs.map((tab) => {
            const exact = tab.path === '/'
            const active = exact
              ? location.pathname === '/'
              : location.pathname.startsWith(tab.path)
            return (
              <NavLink
                key={tab.path}
                to={tab.path}
                className={`${styles.tab} ${active ? styles.tabActive : ''}`}
              >
                {tab.label}
              </NavLink>
            )
          })}
        </nav>
      </div>

      {/* ── Direita: sync + alertas + perfil ─────────────── */}
      <div className={styles.right}>

        {/* Sync badge + botão (só admin) */}
        {ehAdmin && (
          <div className={styles.syncWrap}>
            <span className={styles.syncLabel}>SAP {syncLabel}</span>
            <button
              className={styles.syncBtn}
              onClick={() => syncMut.mutate()}
              disabled={syncMut.isPending}
              title="Sincronizar SAP agora"
            >
              <IconoSync spinning={syncMut.isPending} />
              Sincronizar
            </button>
          </div>
        )}

        {/* Alertas (só admin) */}
        {ehAdmin && (
          <div className={styles.dropdownWrap} ref={alertasRef}>
            <button
              className={`${styles.navBtn} ${alertasAberto ? styles.navBtnActive : ''}`}
              onClick={() => { setAlertasAberto((v) => !v); setPerfilAberto(false) }}
              aria-expanded={alertasAberto}
            >
              <IconoBell count={nAlertas} />
            </button>
            {alertasAberto && <AlertasDropdown onClose={() => setAlertasAberto(false)} />}
          </div>
        )}

        {/* Perfil */}
        <div className={styles.dropdownWrap} ref={perfilRef}>
          <button
            className={`${styles.avatarBtn} ${perfilAberto ? styles.avatarBtnActive : ''}`}
            onClick={() => { setPerfilAberto((v) => !v); setAlertasAberto(false) }}
            aria-expanded={perfilAberto}
            aria-label="Menu do usuário"
          >
            <span className={styles.avatarCircle}>{initials}</span>
            <div className={styles.avatarInfo}>
              <span className={styles.avatarNome}>{usuario?.nome_guerra ?? usuario?.nome}</span>
              <span className={styles.avatarRole}>{ehAdmin ? 'Admin' : 'Operador'}</span>
            </div>
            <span className={styles.avatarChevron}>▾</span>
          </button>
          {perfilAberto && <PerfilDropdown onClose={() => setPerfilAberto(false)} />}
        </div>

      </div>
    </header>
  )
}
