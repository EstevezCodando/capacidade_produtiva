import { getKpiProjetos, getSyncStatus } from "@/api/endpoints";
import { useAuth } from "@/context/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import styles from "./Dashboard.module.css";

function ProgressBar({ value }: { value: number }) {
  const pct = Math.round((value ?? 0) * 100);
  const color =
    pct >= 80 ? "var(--ok)" : pct >= 40 ? "var(--info)" : "var(--warn)";
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
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className={styles.statCard}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      {sub && <span className={styles.statSub}>{sub}</span>}
    </div>
  );
}

export default function Dashboard() {
  const { ehAdmin } = useAuth();

  const {
    data: kpi,
    isLoading: kpiLoading,
    error: kpiError,
  } = useQuery({
    queryKey: ["kpiProjetos"],
    queryFn: getKpiProjetos,
    refetchInterval: 60_000,
  });

  const { data: sync } = useQuery({
    queryKey: ["syncStatus"],
    queryFn: getSyncStatus,
    enabled: ehAdmin,
  });

  const projetos = kpi?.projetos ?? [];
  const totalPts = projetos.reduce((a, p) => a + (p.pontos_total ?? 0), 0);
  const concluidos = projetos.reduce(
    (a, p) => a + (p.pontos_concluidos ?? 0),
    0,
  );
  const progGeral = totalPts > 0 ? concluidos / totalPts : 0;

  const kpiTs = kpi?.kpi_calculado_em
    ? formatDistanceToNow(parseISO(kpi.kpi_calculado_em), {
        addSuffix: true,
        locale: ptBR,
      })
    : null;

  return (
    <div className={styles.root}>
      {/* ── Cabeçalho ─────────────────────────────────────── */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <p className={styles.pageSubtitle}>
            KPI de produção por projeto
            {kpiTs && (
              <span className={styles.staleness}> · calculado {kpiTs}</span>
            )}
          </p>
        </div>
      </div>

      {/* ── Stats gerais ──────────────────────────────────── */}
      <div className={styles.statsRow}>
        <StatCard label="Projetos ativos" value={projetos.length} />
        <StatCard
          label="Progresso geral"
          value={`${Math.round(progGeral * 100)}%`}
          sub={`${concluidos.toFixed(0)} / ${totalPts.toFixed(0)} pts`}
        />
        <StatCard
          label="Pontos concluídos"
          value={concluidos.toFixed(0)}
          sub="pontos totais completados"
        />
        {ehAdmin && sync && (
          <StatCard
            label="Última sync SAP"
            value={sync.ultima_execucao_status === "ok" ? "✓ OK" : "⚠ Falha"}
            sub={
              sync.sap_snapshot_atualizado_em
                ? formatDistanceToNow(
                    parseISO(sync.sap_snapshot_atualizado_em),
                    { addSuffix: true, locale: ptBR },
                  )
                : "nunca"
            }
          />
        )}
      </div>

      {/* ── Projetos ─────────────────────────────────────── */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Projetos</h2>

        {kpiLoading && (
          <div className={styles.loadingRows}>
            {[1, 2, 3].map((i) => (
              <div key={i} className={styles.skeletonRow} />
            ))}
          </div>
        )}

        {kpiError && (
          <div className={styles.errorBox}>
            <span>⚠</span>
            Não foi possível carregar os dados. Verifique a conexão com o
            backend.
          </div>
        )}

        {!kpiLoading && !kpiError && projetos.length === 0 && (
          <div className={styles.emptyState}>
            Nenhum projeto ativo encontrado.
            {ehAdmin && " Verifique se a sincronização SAP foi executada."}
          </div>
        )}

        {projetos.map((p) => (
          <div key={p.projeto_id} className={styles.projetoRow}>
            <div className={styles.projetoInfo}>
              <span className={styles.projetoNome}>{p.nome}</span>
              <span className={styles.projetoPts}>
                {(p.pontos_concluidos ?? 0).toFixed(0)} /{" "}
                {(p.pontos_total ?? 0).toFixed(0)} pts
              </span>
            </div>
            <ProgressBar value={p.progresso ?? 0} />
          </div>
        ))}
      </div>

      {/* ── Capacidade (placeholder) ──────────────────────── */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Capacidade</h2>
        <div className={styles.placeholderBox}>
          <span className={styles.placeholderIcon}>◰</span>
          <span>Gráfico de capacidade por operador — Em Elaboração</span>
        </div>
      </div>
    </div>
  );
}
