// ============================================================
// Dashboard — visão de KPI e capacidade
// Operador: blocos vinculados, pontos por papel, timeline
// Admin:    visão global, projetos, sync SAP
// ============================================================
import { getMeuDashboard, executarSync, getKpiDashboard, getKpiProjetos, getSyncStatus } from "@/api/endpoints"
import { useAuth } from "@/context/AuthContext"
import type { BlocoDetalheUsuario, DiaHorasResposta, MesTrilha, PontosSubfaseResposta } from "@/types"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { format, formatDistanceToNow, parseISO } from "date-fns"
import { ptBR } from "date-fns/locale"
import { useMemo, useState } from "react"
import styles from "./Dashboard.module.css"

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function fmtMin(minutos: number): string {
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

function fmtPts(pts: number): string {
  return pts >= 1000
    ? `${(pts / 1000).toFixed(1)}k`
    : pts.toFixed(pts % 1 === 0 ? 0 : 1)
}

function pct(valor: number, total: number): number {
  if (!total) return 0
  return Math.min(100, Math.round((valor / total) * 100))
}

function fmtDataHora(iso: string | null | undefined): string {
  if (!iso) return "nunca"
  return format(parseISO(iso), "dd/MM/yyyy HH:mm", { locale: ptBR })
}

// ─────────────────────────────────────────────────────────────
// SVG Gráfico mensal acumulado — 3 retas: J previsto, K normal, P total
// ─────────────────────────────────────────────────────────────

const CHART_W = 800
const CHART_H = 200
const PAD = { top: 14, right: 20, bottom: 40, left: 50 }
const INNER_W = CHART_W - PAD.left - PAD.right
const INNER_H = CHART_H - PAD.top - PAD.bottom

// Mantido apenas para satisfazer a tipagem herdada — não renderizado
function _LineChartLegado(_: { dados: DiaHorasResposta[] }) { return null }
void _LineChartLegado

function GraficoMensal({ dados }: { dados: MesTrilha[] }) {
  const [hovIdx, setHovIdx] = useState<number | null>(null)

  const maxMin = useMemo(
    () => Math.max(
      ...dados.map((d) => Math.max(
        d.minutos_previstos_acum,
        d.minutos_lancados_normal_acum,
        d.minutos_lancados_total_acum,
      )),
      60,
    ),
    [dados],
  )
  // Arredonda para próxima hora inteira com folga de 10%
  const maxH = Math.ceil((maxMin * 1.1) / 60)

  const n = dados.length
  const xOf = (i: number) => PAD.left + (n > 1 ? (i / (n - 1)) * INNER_W : INNER_W / 2)
  const yOf = (min: number) => PAD.top + INNER_H - (min / (maxH * 60)) * INNER_H

  const polyJ = dados.map((d, i) => `${xOf(i)},${yOf(d.minutos_previstos_acum)}`).join(" ")
  const polyK = dados.map((d, i) => `${xOf(i)},${yOf(d.minutos_lancados_normal_acum)}`).join(" ")
  const polyP = dados.map((d, i) => `${xOf(i)},${yOf(d.minutos_lancados_total_acum)}`).join(" ")

  // Ticks Y: a cada hora inteira, mas limitar a ~6 ticks
  const yStep = Math.max(1, Math.ceil(maxH / 6))
  const yTicks = Array.from({ length: Math.floor(maxH / yStep) + 1 }, (_, k) => k * yStep)

  const hov = hovIdx !== null ? dados[hovIdx] : null

  return (
    <div className={styles.chartWrap}>
      <svg
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        className={styles.chartSvg}
        onMouseLeave={() => setHovIdx(null)}
      >
        {/* Grade Y */}
        {yTicks.map((h) => (
          <g key={h}>
            <line
              x1={PAD.left} y1={yOf(h * 60)}
              x2={PAD.left + INNER_W} y2={yOf(h * 60)}
              className={styles.gridLine}
            />
            <text x={PAD.left - 8} y={yOf(h * 60) + 4} className={styles.axisLabel} textAnchor="end">
              {h}h
            </text>
          </g>
        ))}

        {/* Rótulos X — meses */}
        {dados.map((d, i) => (
          <text key={d.mes} x={xOf(i)} y={CHART_H - 6} className={styles.axisLabel} textAnchor="middle">
            {format(parseISO(d.mes), "MMM/yy", { locale: ptBR })}
          </text>
        ))}

        {/* Reta J — Previsto (tracejada, info) */}
        {n > 1 && <polyline points={polyJ} fill="none" className={styles.linePrevista} strokeDasharray="6 3" />}

        {/* Reta K — Normal lançado (contínua, secundária) */}
        {n > 1 && <polyline points={polyK} fill="none" className={styles.lineNormal} />}

        {/* Reta P — Total lançado normal+extra (contínua, accent) */}
        {n > 1 && <polyline points={polyP} fill="none" className={styles.lineLancada} />}

        {/* Áreas de hover */}
        {dados.map((_, i) => {
          const w = n > 1 ? INNER_W / (n - 1) : INNER_W
          return (
            <rect
              key={i}
              x={xOf(i) - w / 2}
              y={PAD.top}
              width={w}
              height={INNER_H}
              fill="transparent"
              onMouseEnter={() => setHovIdx(i)}
            />
          )
        })}

        {/* Linha de hover + pontos */}
        {hovIdx !== null && (
          <>
            <line
              x1={xOf(hovIdx)} y1={PAD.top}
              x2={xOf(hovIdx)} y2={PAD.top + INNER_H}
              className={styles.hoverLine}
            />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_previstos_acum)} r={4} className={styles.dotPrev} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_lancados_normal_acum)} r={4} className={styles.dotNormal} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_lancados_total_acum)} r={4} className={styles.dotLanc} />
          </>
        )}
      </svg>

      {/* Tooltip */}
      {hov && (
        <div className={styles.chartTooltip}>
          <span className={styles.tooltipDate}>
            {format(parseISO(hov.mes), "MMMM yyyy", { locale: ptBR })}
          </span>
          <span className={styles.tooltipJ}>J Previsto: {fmtMin(hov.minutos_previstos_acum)}</span>
          <span className={styles.tooltipK}>K Normal: {fmtMin(hov.minutos_lancados_normal_acum)}</span>
          <span className={styles.tooltipP}>P Total: {fmtMin(hov.minutos_lancados_total_acum)}</span>
        </div>
      )}

      {/* Legenda */}
      <div className={styles.chartLegend}>
        <span className={styles.legendJ}>- - J Previsto</span>
        <span className={styles.legendK}>── K Normal</span>
        <span className={styles.legendP}>── P Total (normal + extra)</span>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Barra de progresso dupla (usuario em destaque)
// ─────────────────────────────────────────────────────────────

function ProgressoDuplo({ total, usuario, label }: { total: number; usuario: number; label?: string }) {
  const pctU = pct(usuario, total)
  const pctO = pct(Math.max(0, total - usuario), total)
  return (
    <div className={styles.progressoDuplo}>
      {label && <span className={styles.progressoLabel}>{label}</span>}
      <div className={styles.progressoTrack}>
        <div className={styles.progressoUsuario} style={{ width: `${pctU}%` }} />
        <div className={styles.progressoOutros} style={{ width: `${pctO}%` }} />
      </div>
      <div className={styles.progressoLegenda}>
        <span className={styles.legUsuario}>
          <span className={styles.legDotUsuario} />
          {` Sua contribuição: ${fmtPts(usuario)} pts (${pctU}%)`}
        </span>
        <span className={styles.legOutros}>
          <span className={styles.legDotOutros} />
          {` Outros: ${fmtPts(Math.max(0, total - usuario))} pts`}
        </span>
        <span className={styles.legTotal}>{`Total realizado: ${fmtPts(total)} pts`}</span>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Tabela de subfases por papel
// ─────────────────────────────────────────────────────────────

function SubfaseTabela({ titulo, itens, corClass }: { titulo: string; itens: PontosSubfaseResposta[]; corClass: string }) {
  if (itens.length === 0) return null
  return (
    <div className={styles.papelBloco}>
      <span className={`${styles.papelTitulo} ${corClass}`}>{titulo}</span>
      <table className={styles.subfaseTabela}>
        <tbody>
          {itens.map((sf) => (
            <tr key={sf.subfase_id} className={styles.subfaseRow}>
              <td className={styles.subfaseNome}>{sf.subfase_nome}</td>
              <td className={styles.subfasePts}>{fmtPts(sf.pontos)} pts</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Card de bloco (expandável)
// ─────────────────────────────────────────────────────────────

function BlocoCard({ bloco }: { bloco: BlocoDetalheUsuario }) {
  const [aberto, setAberto] = useState(false)

  const ptsUsuario =
    bloco.como_executor.reduce((s, x) => s + x.pontos, 0) +
    bloco.como_revisor.reduce((s, x) => s + x.pontos, 0) +
    bloco.como_corretor.reduce((s, x) => s + x.pontos, 0)

  const pctContrib = pct(ptsUsuario, bloco.pontos_total_bloco)

  return (
    <div className={`${styles.blocoCard} ${aberto ? styles.blocoAberto : ""}`}>
      <button className={styles.blocoHeader} onClick={() => setAberto((v) => !v)} type="button">
        <div className={styles.blocoHeaderLeft}>
          <span className={styles.blocoNome}>{bloco.bloco_nome}</span>
          <span className={styles.blocoProjeto}>{bloco.projeto_nome}</span>
        </div>
        <div className={styles.blocoHeaderRight}>
          <div className={styles.blocoBarWrap}>
            <div className={styles.blocoBarTrack}>
              <div className={styles.blocoBarTotal} style={{ width: "100%" }} />
              <div className={styles.blocoBarUser} style={{ width: `${pctContrib}%` }} />
            </div>
          </div>
          <span className={styles.blocoStats}>
            <span className={styles.blocoUserPts}>{fmtPts(ptsUsuario)} pts</span>
            {" / "}
            <span className={styles.blocoTotalPts}>{fmtPts(bloco.pontos_total_bloco)} pts</span>
            <span className={styles.blocoContrib}>{` (${pctContrib}%)`}</span>
          </span>
          <span className={styles.blocoToggle}>{aberto ? "▲" : "▼"}</span>
        </div>
      </button>
      {aberto && (
        <div className={styles.blocoBody}>
          <div className={styles.blocoProgressSection}>
            <ProgressoDuplo total={bloco.pontos_total_bloco} usuario={ptsUsuario} />
          </div>
          <div className={styles.papelGrid}>
            <SubfaseTabela titulo="Como Executor" itens={bloco.como_executor} corClass={styles.papelExecutor} />
            <SubfaseTabela titulo="Como Revisor" itens={bloco.como_revisor} corClass={styles.papelRevisor} />
            <SubfaseTabela titulo="Como Corretor" itens={bloco.como_corretor} corClass={styles.papelCorretor} />
          </div>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// StatCard
// ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: boolean }) {
  return (
    <div className={`${styles.statCard} ${accent ? styles.statCardAccent : ""}`}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      {sub && <span className={styles.statSub}>{sub}</span>}
    </div>
  )
}

function ProgressBar({ value }: { value: number }) {
  const p = Math.round((value ?? 0) * 100)
  const color = p >= 80 ? "var(--ok)" : p >= 40 ? "var(--info)" : "var(--warn)"
  return (
    <div className={styles.progressWrap}>
      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: `${p}%`, background: color }} />
      </div>
      <span className={styles.progressPct} style={{ color }}>{p}%</span>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// View do Operador
// ─────────────────────────────────────────────────────────────

function OperadorDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["meuDashboard"],
    queryFn: getMeuDashboard,
    refetchInterval: 120_000,
  })

  const kpiTs = data?.kpi_calculado_em
    ? formatDistanceToNow(parseISO(data.kpi_calculado_em), { addSuffix: true, locale: ptBR })
    : null

  const totalBlocos     = data?.blocos.length ?? 0
  const ptsTotalGeral   = data?.pontos_total_geral ?? 0
  const ptsUsuarioGeral = data?.pontos_usuario_geral ?? 0
  const pctGeral        = pct(ptsUsuarioGeral, ptsTotalGeral)

  if (isLoading) {
    return (
      <div className={styles.loadingRows}>
        {[1, 2, 3, 4].map((k) => <div key={k} className={styles.skeletonRow} />)}
      </div>
    )
  }

  return (
    <>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <p className={styles.pageSubtitle}>
            Seu desempenho e capacidade
            {kpiTs && <span className={styles.staleness}>{` · KPI calculado ${kpiTs}`}</span>}
          </p>
        </div>
      </div>

      <div className={styles.statsRow}>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Blocos vinculados</span>
          <span className={styles.statValue}>{totalBlocos}</span>
          <span
            className={styles.statSub}
            title={data?.blocos.map((b) => b.bloco_nome).join(", ")}
          >
            {totalBlocos > 0
              ? `${data!.blocos.slice(0, 2).map((b) => b.bloco_nome).join(", ")}${totalBlocos > 2 ? ` +${totalBlocos - 2}` : ""}`
              : "sem participação registrada"}
          </span>
        </div>
        <StatCard
          label="Contribuição geral"
          value={`${pctGeral}%`}
          sub={`${fmtPts(ptsUsuarioGeral)} / ${fmtPts(ptsTotalGeral)} pts`}
          accent
        />
        <StatCard
          label="Horas previstas em produção"
          value={fmtMin(data?.horas_previstas_producao_min ?? 0)}
          sub="planejadas em blocos"
        />
        <StatCard
          label="Horas lançadas"
          value={fmtMin((data?.horas_lancadas_producao_min ?? 0) + (data?.horas_lancadas_externas_min ?? 0))}
          sub={`${fmtMin(data?.horas_lancadas_producao_min ?? 0)} produção · ${fmtMin(data?.horas_lancadas_externas_min ?? 0)} externas`}
        />
      </div>

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Progresso geral dos blocos vinculados</h2>
        <div className={styles.progressoCard}>
          <ProgressoDuplo
            total={ptsTotalGeral}
            usuario={ptsUsuarioGeral}
            label={`${fmtPts(ptsTotalGeral)} pts realizados nos blocos em que você participou`}
          />
        </div>
      </div>

      {data && data.timeline_mensal.length > 0 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Evolução acumulada de horas em produção</h2>
          <div className={styles.chartCard}>
            <GraficoMensal dados={data.timeline_mensal} />
          </div>
          <p className={styles.chartCaption}>
            Reta J = meta prevista pelo administrador · Reta K = horas normais realizadas · Reta P = normal + hora extra
          </p>
        </div>
      )}

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Detalhamento por bloco
          {totalBlocos > 0 && <span className={styles.sectionCount}>{totalBlocos}</span>}
        </h2>
        {totalBlocos === 0 ? (
          <div className={styles.emptyState}>
            Nenhum lançamento de pontos encontrado. Verifique se a sincronização SAP foi executada.
          </div>
        ) : (
          <div className={styles.blocosList}>
            {data!.blocos.map((bloco) => (
              <BlocoCard key={bloco.bloco_id} bloco={bloco} />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

// ─────────────────────────────────────────────────────────────
// View do Administrador
// ─────────────────────────────────────────────────────────────

function AdminDashboard() {
  const queryClient = useQueryClient()

  const { data: kpiProjetos, isLoading: kpiLoading, error: kpiError } = useQuery({
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
    refetchInterval: (query) =>
      query.state.data?.ultima_execucao_status === "executando" ? 5_000 : 60_000,
  })

  const sincMutation = useMutation({
    mutationFn: executarSync,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["syncStatus"] })
      await queryClient.invalidateQueries({ queryKey: ["kpiDashboard"] })
      await queryClient.invalidateQueries({ queryKey: ["kpiProjetos"] })
    },
  })

  const projetos      = kpiProjetos?.projetos ?? []
  const kpiTs         = kpiProjetos?.kpi_calculado_em
    ? formatDistanceToNow(parseISO(kpiProjetos.kpi_calculado_em), { addSuffix: true, locale: ptBR })
    : null
  const ptsTotais     = dashboard?.pontos_totais     ?? projetos.reduce((a, p) => a + (p.pontos_total ?? 0), 0)
  const ptsRealizados = dashboard?.pontos_realizados ?? projetos.reduce((a, p) => a + (p.pontos_concluidos ?? 0), 0)
  const progGeral     = dashboard?.progresso_geral   ?? pct(ptsRealizados, ptsTotais)

  return (
    <>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <p className={styles.pageSubtitle}>
            KPI de produção e capacidade — visão global
            {kpiTs && <span className={styles.staleness}>{` · calculado ${kpiTs}`}</span>}
          </p>
        </div>
        <button
          type="button"
          className={styles.syncButton}
          onClick={() => sincMutation.mutate()}
          disabled={sincMutation.isPending || sync?.ultima_execucao_status === "executando"}
        >
          {sincMutation.isPending || sync?.ultima_execucao_status === "executando"
            ? "Sincronizando..."
            : "Sincronizar SAP"}
        </button>
      </div>

      <div className={styles.statsRow}>
        <StatCard label="Blocos SAP" value={dashboard?.blocos_sap_cadastrados ?? 0} sub="blocos no snapshot" />
        <StatCard
          label="Progresso geral"
          value={`${Math.round(progGeral ?? 0)}%`}
          sub={`${fmtPts(ptsRealizados)} / ${fmtPts(ptsTotais)} pts`}
          accent
        />
        <StatCard
          label="Horas previstas em produção"
          value={fmtMin(dashboard?.horas_previstas_producao_min ?? 0)}
          sub="todos os usuários"
        />
        <StatCard
          label="Horas lançadas em produção"
          value={fmtMin(dashboard?.horas_lancadas_producao_min ?? 0)}
          sub="todos os usuários"
        />
        {sync && (
          <StatCard
            label="Última sync SAP"
            value={fmtDataHora(sync.ultima_execucao_em ?? sync.sap_snapshot_atualizado_em)}
            sub={
              sync.ultima_execucao_status === "executando"
                ? "em andamento…"
                : (sync.ultima_execucao_mensagem ?? sync.ultima_execucao_status ?? "—")
            }
          />
        )}
      </div>

      {dashboard && (dashboard.timeline_mensal ?? []).length > 0 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Evolução acumulada de horas em produção — todos os operadores</h2>
          <div className={styles.chartCard}>
            <GraficoMensal dados={dashboard.timeline_mensal ?? []} />
          </div>
          <p className={styles.chartCaption}>
            Reta J = meta prevista · Reta K = horas normais realizadas · Reta P = normal + hora extra
          </p>
        </div>
      )}

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Projetos</h2>
        {kpiLoading && (
          <div className={styles.loadingRows}>
            {[1, 2, 3].map((k) => <div key={k} className={styles.skeletonRow} />)}
          </div>
        )}
        {kpiError && <div className={styles.errorBox}>⚠ Não foi possível carregar os dados.</div>}
        {!kpiLoading && !kpiError && projetos.length === 0 && (
          <div className={styles.emptyState}>Nenhum projeto ativo. Execute a sincronização SAP.</div>
        )}
        {projetos.map((projeto) => (
          <div key={projeto.projeto_id} className={styles.projetoRow}>
            <div className={styles.projetoInfo}>
              <span className={styles.projetoNome}>{projeto.nome}</span>
              <span className={styles.projetoPts}>
                {fmtPts(projeto.pontos_concluidos)} / {fmtPts(projeto.pontos_total)} pts
              </span>
            </div>
            <ProgressBar value={projeto.progresso ?? 0} />
          </div>
        ))}
      </div>
    </>
  )
}

// ─────────────────────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { ehAdmin } = useAuth()
  return (
    <div className={styles.root}>
      {ehAdmin ? <AdminDashboard /> : <OperadorDashboard />}
    </div>
  )
}
