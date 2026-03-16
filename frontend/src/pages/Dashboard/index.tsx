import { executarSync, getKpiDashboard, getKpiProjetos, getSyncStatus } from "@/api/endpoints"
import { useAuth } from "@/context/AuthContext"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { format, formatDistanceToNow, parseISO } from "date-fns"
import { ptBR } from "date-fns/locale"
import styles from "./Dashboard.module.css"

function ProgressBar({ value }: { value: number }) {
  const pct = Math.round((value ?? 0) * 100)
  const color = pct >= 80 ? "var(--ok)" : pct >= 40 ? "var(--info)" : "var(--warn)"

  return (
    <div className={styles.progressWrap}>
      <div className={styles.progressTrack}>
        <div
          className={styles.progressFill}
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className={styles.progressPct} style={{ color }}>
        {pct}%
      </span>
    </div>
  )
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <div className={styles.statCard}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      {sub && <span className={styles.statSub}>{sub}</span>}
    </div>
  )
}

function formatarMinutosComoHoras(minutos: number | null | undefined): string {
  const totalMinutos = minutos ?? 0
  const horas = totalMinutos / 60
  return `${horas.toFixed(1)}h`
}

function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return "nunca"

  const data = parseISO(iso)
  return format(data, "dd/MM/yyyy HH:mm", { locale: ptBR })
}

export default function Dashboard() {
  const { ehAdmin } = useAuth()
  const queryClient = useQueryClient()

  const {
    data: kpiProjetos,
    isLoading: kpiLoading,
    error: kpiError,
  } = useQuery({
    queryKey: ["kpiProjetos"],
    queryFn: getKpiProjetos,
    refetchInterval: 60_000,
  })

  const { data: dashboard } = useQuery({
    queryKey: ["kpiDashboard"],
    queryFn: getKpiDashboard,
    refetchInterval: 60_000,
  })

  const { data: sync } = useQuery({
    queryKey: ["syncStatus"],
    queryFn: getSyncStatus,
    enabled: ehAdmin,
    refetchInterval: (query) => {
      const status = query.state.data?.ultima_execucao_status
      return status === "executando" ? 5_000 : 60_000
    },
  })

  const sincronizarMutation = useMutation({
    mutationFn: executarSync,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["syncStatus"] })
      await queryClient.invalidateQueries({ queryKey: ["kpiDashboard"] })
      await queryClient.invalidateQueries({ queryKey: ["kpiProjetos"] })
    },
  })

  const projetos = kpiProjetos?.projetos ?? []
  const totalPts = projetos.reduce((acumulado, projeto) => acumulado + (projeto.pontos_total ?? 0), 0)
  const concluidos = projetos.reduce((acumulado, projeto) => acumulado + (projeto.pontos_concluidos ?? 0), 0)
  const progressoGeral = dashboard?.progresso_geral ?? (totalPts > 0 ? (concluidos / totalPts) * 100 : 0)

  const kpiTs = kpiProjetos?.kpi_calculado_em
    ? formatDistanceToNow(parseISO(kpiProjetos.kpi_calculado_em), {
        addSuffix: true,
        locale: ptBR,
      })
    : null

  return (
    <div className={styles.root}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <p className={styles.pageSubtitle}>
            KPI de produção e capacidade
            {kpiTs && <span className={styles.staleness}> · calculado {kpiTs}</span>}
          </p>
        </div>

        {ehAdmin && (
          <button
            type="button"
            className={styles.syncButton}
            onClick={() => sincronizarMutation.mutate()}
            disabled={sincronizarMutation.isPending || sync?.ultima_execucao_status === "executando"}
          >
            {sincronizarMutation.isPending || sync?.ultima_execucao_status === "executando"
              ? "Sincronizando..."
              : "Sincronizar SAP"}
          </button>
        )}
      </div>

      <div className={styles.statsRow}>
        <StatCard
          label="Blocos SAP"
          value={dashboard?.blocos_sap_cadastrados ?? 0}
          sub="blocos cadastrados no snapshot SAP"
        />
        <StatCard
          label="Progresso geral"
          value={`${Math.round(progressoGeral)}%`}
          sub={`${concluidos.toFixed(0)} / ${totalPts.toFixed(0)} pts`}
        />
        <StatCard
          label="Horas previstas em produção"
          value={formatarMinutosComoHoras(dashboard?.horas_previstas_producao_min)}
          sub="soma dos planejamentos vinculados a bloco"
        />
        <StatCard
          label="Horas lançadas em produção"
          value={formatarMinutosComoHoras(dashboard?.horas_lancadas_producao_min)}
          sub="soma dos lançamentos realizados em bloco"
        />
        {ehAdmin && sync && (
          <StatCard
            label="Última sync SAP"
            value={formatarDataHora(sync.ultima_execucao_em ?? sync.sap_snapshot_atualizado_em)}
            sub={
              sync.ultima_execucao_status === "executando"
                ? "sincronização em andamento"
                : sync.ultima_execucao_mensagem ?? sync.ultima_execucao_status ?? "sem histórico"
            }
          />
        )}
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Projetos</h2>

        {kpiLoading && (
          <div className={styles.loadingRows}>
            {[1, 2, 3].map((item) => (
              <div key={item} className={styles.skeletonRow} />
            ))}
          </div>
        )}

        {kpiError && (
          <div className={styles.errorBox}>
            <span>⚠</span>
            Não foi possível carregar os dados. Verifique a conexão com o backend.
          </div>
        )}

        {!kpiLoading && !kpiError && projetos.length === 0 && (
          <div className={styles.emptyState}>
            Nenhum projeto ativo encontrado.
            {ehAdmin && " Verifique se a sincronização SAP foi executada."}
          </div>
        )}

        {projetos.map((projeto) => (
          <div key={projeto.projeto_id} className={styles.projetoRow}>
            <div className={styles.projetoInfo}>
              <span className={styles.projetoNome}>{projeto.nome}</span>
              <span className={styles.projetoPts}>
                {(projeto.pontos_concluidos ?? 0).toFixed(0)} / {(projeto.pontos_total ?? 0).toFixed(0)} pts
              </span>
            </div>
            <ProgressBar value={projeto.progresso ?? 0} />
          </div>
        ))}
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Capacidade</h2>
        <div className={styles.placeholderBox}>
          <span className={styles.placeholderIcon}>◰</span>
          <span>Próximo passo: consolidar visual de capacidade por operador e por bloco.</span>
        </div>
      </div>
    </div>
  )
}
