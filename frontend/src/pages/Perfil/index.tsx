import { useState, useEffect }              from 'react'
import { useSearchParams }                   from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth }                           from '@/context/AuthContext'
import { getSyncStatus, executarSync }       from '@/api/endpoints'
import { getTiposAtividadeConfiguracao, atualizarCorTipoAtividade } from '@/api/agenda'
import ConfiguracoesAdmin from '@/components/admin/ConfiguracoesAdmin'
import { formatDistanceToNow, parseISO, format } from 'date-fns'
import { ptBR }                              from 'date-fns/locale'
import styles                               from './Perfil.module.css'

// ── Tipos locais ─────────────────────────────────────────────
interface TipoAtividadeConfiguravel {
  id: number
  codigo: string
  nome: string
  grupo: string
  bloco_id?: number | null
  cor: string
}

// ── Tab: Meu Perfil ──────────────────────────────────────────
function TabPerfil() {
  const { usuario, sessao } = useAuth()
  const loginEm = sessao?.login_em
    ? format(parseISO(sessao.login_em), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
    : '—'
  const loginHa = sessao?.login_em
    ? formatDistanceToNow(parseISO(sessao.login_em), { addSuffix: true, locale: ptBR })
    : '—'

  return (
    <div className={styles.tabContent}>
      <div className={styles.profileCard}>
        {/* Avatar grande */}
        <div className={styles.profileAvatarWrap}>
          <div className={styles.profileAvatar}>
            {(usuario?.nome_guerra ?? usuario?.nome ?? '?')[0].toUpperCase()}
          </div>
          <div>
            <h2 className={styles.profileNome}>{usuario?.nome ?? '—'}</h2>
            {usuario?.nome_guerra && (
              <p className={styles.profileGuerra}>"{usuario.nome_guerra}"</p>
            )}
            <span className={`${styles.profileBadge} ${usuario?.administrador ? styles.badgeAdmin : styles.badgeOp}`}>
              {usuario?.administrador ? 'Administrador' : 'Operador'}
            </span>
          </div>
        </div>

        {/* Dados */}
        <div className={styles.profileFields}>
          <div className={styles.fieldRow}>
            <span className={styles.fieldLabel}>ID interno</span>
            <span className={styles.fieldValue}>{usuario?.usuario_id ?? '—'}</span>
          </div>
          <div className={styles.fieldRow}>
            <span className={styles.fieldLabel}>UUID</span>
            <code className={styles.fieldCode}>{usuario?.usuario_uuid ?? '—'}</code>
          </div>
          <div className={styles.fieldRow}>
            <span className={styles.fieldLabel}>Último login</span>
            <div>
              <span className={styles.fieldValue}>{loginEm}</span>
              <span className={styles.fieldSub}> ({loginHa})</span>
            </div>
          </div>
          <div className={styles.fieldRow}>
            <span className={styles.fieldLabel}>Perfil</span>
            <span className={styles.fieldValue}>
              {usuario?.administrador ? 'Administrador — acesso total' : 'Operador — acesso restrito'}
            </span>
          </div>
        </div>
      </div>

      {/* Pontos pessoais (placeholder) */}
      <div className={styles.sectionCard}>
        <h3 className={styles.sectionCardTitle}>Produção — Em Elaboração</h3>
        <div className={styles.statsGrid}>
          {['Pontos como Executor', 'Pontos como Revisor', 'Pontos como Corretor'].map(l => (
            <div key={l} className={styles.miniStat}>
              <span className={styles.miniStatLabel}>{l}</span>
              <span className={styles.miniStatValue}>—</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Tab: Configurações (admin only) ─────────────────────────
function TabConfiguracoes() {
  const queryClient = useQueryClient()

  const { data: sync, isLoading: syncLoading } = useQuery({
    queryKey: ['syncStatus'],
    queryFn: getSyncStatus,
    refetchInterval: 30_000,
  })

  const { data: tiposAtividade = [] } = useQuery<TipoAtividadeConfiguravel[]>({
    queryKey: ['tipos-atividade-configuracao'],
    queryFn: getTiposAtividadeConfiguracao,
    staleTime: 60_000,
  })

  const atualizarCorMutation = useMutation({
    mutationFn: ({ id, cor }: { id: number; cor: string }) => atualizarCorTipoAtividade(id, cor),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tipos-atividade-configuracao'] })
      void queryClient.invalidateQueries({ queryKey: ['tipos-atividade'] })
      void queryClient.invalidateQueries({ queryKey: ['agenda'] })
      void queryClient.invalidateQueries({ queryKey: ['agenda-prevista-multiusuario'] })
    },
  })

  const syncMut = useMutation({
    mutationFn: executarSync,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['syncStatus'] })
      void queryClient.invalidateQueries({ queryKey: ['tipos-atividade-configuracao'] })
      void queryClient.invalidateQueries({ queryKey: ['tipos-atividade'] })
    },
  })

  const syncTs = sync?.sap_snapshot_atualizado_em
    ? format(parseISO(sync.sap_snapshot_atualizado_em), "dd/MM/yyyy HH:mm", { locale: ptBR })
    : 'nunca'
  const syncHa = sync?.sap_snapshot_atualizado_em
    ? formatDistanceToNow(parseISO(sync.sap_snapshot_atualizado_em), { addSuffix: true, locale: ptBR })
    : null

  return (
    <div className={styles.tabContent}>
      <div className={styles.sectionCard}>
        <h3 className={styles.sectionCardTitle}>Sincronização SAP</h3>
        <p className={styles.sectionCardDesc}>O pipeline atualiza o snapshot, sincroniza os blocos como atividades configuráveis e recalcula os indicadores.</p>

        <div className={styles.syncStatus}>
          <div className={styles.syncStatusRow}>
            <span className={styles.syncStatusLabel}>Última execução</span>
            <div className={styles.syncStatusVal}>
              <span className={`${styles.syncDot} ${
                sync?.ultima_execucao_status === 'ok' ? styles.syncDotOk :
                sync?.ultima_execucao_status ? styles.syncDotErr : styles.syncDotMuted
              }`} />
              <span>{syncTs}</span>
              {syncHa && <span className={styles.syncHa}>({syncHa})</span>}
            </div>
          </div>
          <div className={styles.syncStatusRow}>
            <span className={styles.syncStatusLabel}>Status</span>
            <span className={`${styles.syncStatusBadge} ${
              sync?.ultima_execucao_status === 'ok' ? styles.syncBadgeOk : styles.syncBadgeErr
            }`}>
              {syncLoading ? '…' : sync?.ultima_execucao_status ?? 'desconhecido'}
            </span>
          </div>
        </div>

        <button className={styles.syncBtn} onClick={() => syncMut.mutate()} disabled={syncMut.isPending}>
          {syncMut.isPending ? <><span className={styles.spinner} /> Sincronizando…</> : <><span>↺</span> Sincronizar SAP agora</>}
        </button>
      </div>

      <ConfiguracoesAdmin />

      <div className={styles.sectionCard}>
        <h3 className={styles.sectionCardTitle}>Cores das atividades</h3>
        <p className={styles.sectionCardDesc}>Somente administradores podem alterar as cores. O valor persiste no banco e é reutilizado em toda a agenda.</p>

        <div className={styles.profileFields}>
          {tiposAtividade.map((tipo) => (
            <div key={tipo.id} className={styles.fieldRow}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ width: 14, height: 14, borderRadius: 999, background: tipo.cor, border: '1px solid rgba(255,255,255,0.16)' }} />
                <div>
                  <span className={styles.fieldValue}>{tipo.nome}</span>
                  <div className={styles.fieldSub}>{tipo.bloco_id ? `Bloco ${tipo.bloco_id}` : tipo.codigo}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <code className={styles.fieldCode}>{tipo.cor}</code>
                <input
                  type="color"
                  value={tipo.cor}
                  onChange={(e) => atualizarCorMutation.mutate({ id: tipo.id, cor: e.target.value.toUpperCase() })}
                  style={{ width: 42, height: 32, background: 'transparent', border: 'none', cursor: 'pointer' }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Página principal ─────────────────────────────────────────
export default function Perfil() {
  const { ehAdmin } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')

  const tabs = [
    { id: 'perfil',         label: 'Meu Perfil' },
    ...(ehAdmin ? [{ id: 'configuracoes', label: 'Configurações do Sistema' }] : []),
  ]

  const [activeTab, setActiveTab] = useState(
    tabParam === 'configuracoes' && ehAdmin ? 'configuracoes' : 'perfil'
  )

  useEffect(() => {
    if (tabParam === 'configuracoes' && ehAdmin) setActiveTab('configuracoes')
  }, [tabParam, ehAdmin])

  function handleTab(id: string) {
    setActiveTab(id)
    setSearchParams(id === 'perfil' ? {} : { tab: id })
  }

  return (
    <div className={styles.root}>
      <div className={styles.inner}>
        {/* ── Cabeçalho ───────────────────────────────────── */}
        <div className={styles.pageHeader}>
          <h1 className={styles.pageTitle}>Perfil</h1>
        </div>

        {/* ── Tabs ─────────────────────────────────────────── */}
        <div className={styles.tabBar} role="tablist">
          {tabs.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={activeTab === t.id}
              className={`${styles.tabBtn} ${activeTab === t.id ? styles.tabBtnActive : ''}`}
              onClick={() => handleTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Conteúdo ─────────────────────────────────────── */}
        {activeTab === 'perfil'         && <TabPerfil />}
        {activeTab === 'configuracoes'  && ehAdmin && <TabConfiguracoes />}
      </div>
    </div>
  )
}
