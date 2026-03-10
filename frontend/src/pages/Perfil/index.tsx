import { useState, useEffect }              from 'react'
import { useSearchParams }                   from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth }                           from '@/context/AuthContext'
import { getSyncStatus, executarSync }       from '@/api/endpoints'
import { formatDistanceToNow, parseISO, format } from 'date-fns'
import { ptBR }                              from 'date-fns/locale'
import styles                               from './Perfil.module.css'

// ── Tipos locais ─────────────────────────────────────────────
interface ConfigSistema {
  intervalo_sync_min:  number
  teto_normal_min:     number
  teto_extra_min:      number
}

// Lê config do localStorage (sem backend ainda)
function lerConfig(): ConfigSistema {
  try {
    const raw = localStorage.getItem('cp_config_sistema')
    return raw ? JSON.parse(raw) : { intervalo_sync_min: 30, teto_normal_min: 360, teto_extra_min: 600 }
  } catch {
    return { intervalo_sync_min: 30, teto_normal_min: 360, teto_extra_min: 600 }
  }
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
  const [config, setConfig] = useState<ConfigSistema>(lerConfig)
  const [saved,  setSaved]  = useState(false)

  const { data: sync, isLoading: syncLoading } = useQuery({
    queryKey: ['syncStatus'],
    queryFn:  getSyncStatus,
    refetchInterval: 30_000,
  })

  const syncMut = useMutation({
    mutationFn: executarSync,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['syncStatus'] })
    },
  })

  function salvarConfig() {
    localStorage.setItem('cp_config_sistema', JSON.stringify(config))
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const syncTs = sync?.sap_snapshot_atualizado_em
    ? format(parseISO(sync.sap_snapshot_atualizado_em), "dd/MM/yyyy HH:mm", { locale: ptBR })
    : 'nunca'
  const syncHa = sync?.sap_snapshot_atualizado_em
    ? formatDistanceToNow(parseISO(sync.sap_snapshot_atualizado_em), { addSuffix: true, locale: ptBR })
    : null

  return (
    <div className={styles.tabContent}>

      {/* ── Bloco: Sincronização SAP ───────────────────────── */}
      <div className={styles.sectionCard}>
        <h3 className={styles.sectionCardTitle}>Sincronização SAP</h3>
        <p className={styles.sectionCardDesc}>
          O pipeline lê o banco SAP, atualiza o sap_snapshot e recalcula todos os KPIs.
          Roda automaticamente conforme o intervalo abaixo e pode ser disparado manualmente.
        </p>

        <div className={styles.configGrid}>
          <div className={styles.configField}>
            <label className={styles.configLabel}>
              Intervalo automático (minutos)
            </label>
            <div className={styles.configInputRow}>
              <input
                type="number"
                min={5}
                max={240}
                step={5}
                className={styles.configInput}
                value={config.intervalo_sync_min}
                onChange={(e) => setConfig({ ...config, intervalo_sync_min: Number(e.target.value) })}
              />
              <span className={styles.configHint}>
                min 5 min · max 240 min
              </span>
            </div>
          </div>
        </div>

        {/* Status da última sync */}
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
          <div className={styles.syncStatusRow}>
            <span className={styles.syncStatusLabel}>KPI calculado em</span>
            <span className={styles.syncStatusVal}>
              {sync?.kpi_calculado_em
                ? format(parseISO(sync.kpi_calculado_em), "dd/MM/yyyy HH:mm", { locale: ptBR })
                : '—'}
            </span>
          </div>
        </div>

        <button
          className={styles.syncBtn}
          onClick={() => syncMut.mutate()}
          disabled={syncMut.isPending}
        >
          {syncMut.isPending ? (
            <><span className={styles.spinner} /> Sincronizando…</>
          ) : (
            <><span>↺</span> Sincronizar SAP agora</>
          )}
        </button>

        {syncMut.isSuccess && (
          <p className={styles.successMsg}>✓ Sincronização enfileirada com sucesso.</p>
        )}
        {syncMut.isError && (
          <p className={styles.errorMsg}>⚠ Falha ao disparar sincronização. Verifique o backend.</p>
        )}
      </div>

      {/* ── Bloco: Capacidade ────────────────────────────────── */}
      <div className={styles.sectionCard}>
        <h3 className={styles.sectionCardTitle}>Tetos de Capacidade</h3>
        <p className={styles.sectionCardDesc}>
          Define o máximo de minutos permitidos por dia para lançamentos normais e extras.
          Alterações aqui afetam todos os operadores a partir do próximo dia.
        </p>

        <div className={styles.configGrid}>
          <div className={styles.configField}>
            <label className={styles.configLabel}>Teto normal (minutos/dia)</label>
            <div className={styles.configInputRow}>
              <input
                type="number"
                min={60}
                max={600}
                step={30}
                className={styles.configInput}
                value={config.teto_normal_min}
                onChange={(e) => setConfig({ ...config, teto_normal_min: Number(e.target.value) })}
              />
              <span className={styles.configHint}>
                = {(config.teto_normal_min / 60).toFixed(1)}h
              </span>
            </div>
          </div>

          <div className={styles.configField}>
            <label className={styles.configLabel}>Teto extra (minutos/dia)</label>
            <div className={styles.configInputRow}>
              <input
                type="number"
                min={60}
                max={720}
                step={30}
                className={styles.configInput}
                value={config.teto_extra_min}
                onChange={(e) => setConfig({ ...config, teto_extra_min: Number(e.target.value) })}
              />
              <span className={styles.configHint}>
                = {(config.teto_extra_min / 60).toFixed(1)}h
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Salvar ───────────────────────────────────────────── */}
      <div className={styles.saveRow}>
        <button className={styles.saveBtn} onClick={salvarConfig}>
          {saved ? '✓ Configurações salvas' : 'Salvar configurações'}
        </button>
        <span className={styles.saveNote}>
          * Intervalo de sync e tetos serão aplicados pelo backend via endpoint /api/capacidade/config
        </span>
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
