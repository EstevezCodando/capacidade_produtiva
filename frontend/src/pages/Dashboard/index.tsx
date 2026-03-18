// ============================================================
// Dashboard — visão de KPI e capacidade
// Operador: blocos vinculados, pontos por papel, timeline
// Admin:    visão global, projetos, sync SAP
// ============================================================
import {
  getMeuDashboard, executarSync, getKpiDashboard, getKpiProjetos, getSyncStatus,
  getMinhaPizzaMensal, getPizzaMensal, getUsuarios,
} from "@/api/endpoints"
import { useAuth } from "@/context/AuthContext"
import type { BlocoDetalheUsuario, DiaHorasResposta, MesTrilha, PizzaFatia, PontosSubfaseResposta } from "@/types"
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
// SVG Gráfico diário acumulado — 3 retas: J previsto, K normal, P total
// ─────────────────────────────────────────────────────────────

const CHART_W = 800
const CHART_H = 200
const PAD = { top: 14, right: 20, bottom: 40, left: 50 }
const INNER_W = CHART_W - PAD.left - PAD.right
const INNER_H = CHART_H - PAD.top - PAD.bottom

// Legado — mantido para satisfazer tipagem herdada, não renderizado
function _GraficoMensalLegado(_: { dados: MesTrilha[] }) { return null }
void _GraficoMensalLegado

function GraficoDiario({ dados }: { dados: DiaHorasResposta[] }) {
  const [hovIdx, setHovIdx] = useState<number | null>(null)

  // Acumula J/K/P dia-a-dia
  const acum = useMemo(() => {
    let j = 0, k = 0, p = 0
    return dados.map((d) => {
      j += d.minutos_previstos
      k += d.minutos_lancados_normal
      p += d.minutos_lancados
      return { j, k, p }
    })
  }, [dados])

  const maxMin = useMemo(
    () => Math.max(...acum.map((a) => Math.max(a.j, a.k, a.p)), 60),
    [acum],
  )
  const maxH = Math.ceil((maxMin * 1.1) / 60)

  const n = dados.length
  const xOf = (i: number) => PAD.left + (n > 1 ? (i / (n - 1)) * INNER_W : INNER_W / 2)
  const yOf = (min: number) => PAD.top + INNER_H - (min / (maxH * 60)) * INNER_H

  const polyJ = acum.map((a, i) => `${xOf(i)},${yOf(a.j)}`).join(" ")
  const polyK = acum.map((a, i) => `${xOf(i)},${yOf(a.k)}`).join(" ")
  const polyP = acum.map((a, i) => `${xOf(i)},${yOf(a.p)}`).join(" ")

  const yStep = Math.max(1, Math.ceil(maxH / 6))
  const yTicks = Array.from({ length: Math.floor(maxH / yStep) + 1 }, (_, k) => k * yStep)

  // Só mostra 1 label por semana para não sobrecarregar o eixo X
  const xLabelStep = Math.max(1, Math.floor(n / 7))

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

        {/* Rótulos X — datas (a cada ~7 dias) */}
        {dados.map((d, i) => i % xLabelStep === 0 && (
          <text key={d.data} x={xOf(i)} y={CHART_H - 6} className={styles.axisLabel} textAnchor="middle">
            {format(parseISO(d.data), "dd/MM")}
          </text>
        ))}

        {/* Reta J — Previsto acumulado (tracejada) */}
        {n > 1 && <polyline points={polyJ} fill="none" className={styles.linePrevista} strokeDasharray="6 3" />}

        {/* Reta K — Normal lançado acumulado */}
        {n > 1 && <polyline points={polyK} fill="none" className={styles.lineNormal} />}

        {/* Reta P — Total lançado acumulado (normal + extra) */}
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
            <circle cx={xOf(hovIdx)} cy={yOf(acum[hovIdx].j)} r={4} className={styles.dotPrev} />
            <circle cx={xOf(hovIdx)} cy={yOf(acum[hovIdx].k)} r={4} className={styles.dotNormal} />
            <circle cx={xOf(hovIdx)} cy={yOf(acum[hovIdx].p)} r={4} className={styles.dotLanc} />
          </>
        )}
      </svg>

      {/* Tooltip */}
      {hovIdx !== null && (
        <div className={styles.chartTooltip}>
          <span className={styles.tooltipDate}>
            {format(parseISO(dados[hovIdx].data), "dd/MM/yyyy", { locale: ptBR })}
          </span>
          <span className={styles.tooltipJ}>J Previsto: {fmtMin(acum[hovIdx].j)}</span>
          <span className={styles.tooltipK}>K Normal: {fmtMin(acum[hovIdx].k)}</span>
          <span className={styles.tooltipP}>P Total: {fmtMin(acum[hovIdx].p)}</span>
        </div>
      )}

      {/* Legenda */}
      <div className={styles.chartLegend}>
        <span className={styles.legendJ}>- - J Previsto acum.</span>
        <span className={styles.legendK}>── K Normal acum.</span>
        <span className={styles.legendP}>── P Total acum. (normal + extra)</span>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// SVG Gráfico mensal acumulado (admin) — mesma estrutura, dados mensais
// ─────────────────────────────────────────────────────────────

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
  const maxH = Math.ceil((maxMin * 1.1) / 60)

  const n = dados.length
  if (n === 0) return <div className={styles.emptyState}>Sem dados de timeline disponíveis.</div>

  const xOf = (i: number) => PAD.left + (n > 1 ? (i / (n - 1)) * INNER_W : INNER_W / 2)
  const yOf = (min: number) => PAD.top + INNER_H - (min / (maxH * 60)) * INNER_H

  const polyJ = dados.map((d, i) => `${xOf(i)},${yOf(d.minutos_previstos_acum)}`).join(" ")
  const polyK = dados.map((d, i) => `${xOf(i)},${yOf(d.minutos_lancados_normal_acum)}`).join(" ")
  const polyP = dados.map((d, i) => `${xOf(i)},${yOf(d.minutos_lancados_total_acum)}`).join(" ")

  const yStep = Math.max(1, Math.ceil(maxH / 6))
  const yTicks = Array.from({ length: Math.floor(maxH / yStep) + 1 }, (_, k) => k * yStep)

  // Mostra no máximo ~8 labels no eixo X para evitar sobreposição
  const xLabelStep = Math.max(1, Math.ceil(n / 8))

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
            <line x1={PAD.left} y1={yOf(h * 60)} x2={PAD.left + INNER_W} y2={yOf(h * 60)} className={styles.gridLine} />
            <text x={PAD.left - 8} y={yOf(h * 60) + 4} className={styles.axisLabel} textAnchor="end">{h}h</text>
          </g>
        ))}

        {/* Rótulos X — um por ~2 meses para não sobrecarregar */}
        {dados.map((d, i) => i % xLabelStep === 0 && (
          <text key={d.mes} x={xOf(i)} y={CHART_H - 6} className={styles.axisLabel} textAnchor="middle">
            {format(parseISO(d.mes), "MMM/yy", { locale: ptBR })}
          </text>
        ))}

        {/* Retas */}
        <polyline points={polyJ} fill="none" className={styles.linePrevista} strokeDasharray="6 3" />
        <polyline points={polyK} fill="none" className={styles.lineNormal} />
        <polyline points={polyP} fill="none" className={styles.lineLancada} />

        {/* Áreas de hover */}
        {dados.map((_, i) => {
          const w = n > 1 ? INNER_W / (n - 1) : INNER_W
          return (
            <rect key={i} x={xOf(i) - w / 2} y={PAD.top} width={w} height={INNER_H} fill="transparent"
              onMouseEnter={() => setHovIdx(i)} />
          )
        })}

        {/* Linha de hover + pontos */}
        {hovIdx !== null && (
          <>
            <line x1={xOf(hovIdx)} y1={PAD.top} x2={xOf(hovIdx)} y2={PAD.top + INNER_H} className={styles.hoverLine} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_previstos_acum)} r={4} className={styles.dotPrev} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_lancados_normal_acum)} r={4} className={styles.dotNormal} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_lancados_total_acum)} r={4} className={styles.dotLanc} />
          </>
        )}
      </svg>

      {/* Tooltip */}
      {hovIdx !== null && (
        <div className={styles.chartTooltip}>
          <span className={styles.tooltipDate}>{format(parseISO(dados[hovIdx].mes), "MMMM yyyy", { locale: ptBR })}</span>
          <span className={styles.tooltipJ}>J Previsto: {fmtMin(dados[hovIdx].minutos_previstos_acum)}</span>
          <span className={styles.tooltipK}>K Normal: {fmtMin(dados[hovIdx].minutos_lancados_normal_acum)}</span>
          <span className={styles.tooltipP}>P Total: {fmtMin(dados[hovIdx].minutos_lancados_total_acum)}</span>
        </div>
      )}

      {/* Legenda */}
      <div className={styles.chartLegend}>
        <span className={styles.legendJ}>- - J Previsto acum.</span>
        <span className={styles.legendK}>── K Normal acum.</span>
        <span className={styles.legendP}>── P Total acum. (normal + extra)</span>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// SVG Gráfico de Pizza (donut) — distribuição de horas por atividade
// ─────────────────────────────────────────────────────────────

const PIZZA_R  = 88   // raio externo
const PIZZA_r  = 50   // raio interno (buraco)
const PIZZA_CX = 120
const PIZZA_CY = 120

function arcPath(sa: number, ea: number, R: number, ri: number, cx: number, cy: number): string {
  if (Math.abs(ea - sa) >= 2 * Math.PI - 0.001) {
    // Círculo completo: desenha dois arcos de 180°
    const mid = sa + Math.PI
    const x1o = cx + R * Math.cos(sa), y1o = cy + R * Math.sin(sa)
    const xmo = cx + R * Math.cos(mid), ymo = cy + R * Math.sin(mid)
    const x1i = cx + ri * Math.cos(ea), y1i = cy + ri * Math.sin(ea)
    const xmi = cx + ri * Math.cos(mid), ymi = cy + ri * Math.sin(mid)
    return `M ${x1o} ${y1o} A ${R} ${R} 0 1 1 ${xmo} ${ymo} A ${R} ${R} 0 1 1 ${x1o} ${y1o}
            M ${x1i} ${y1i} A ${ri} ${ri} 0 1 0 ${xmi} ${ymi} A ${ri} ${ri} 0 1 0 ${x1i} ${y1i} Z`
  }
  const la = ea - sa > Math.PI ? 1 : 0
  const x1 = cx + R * Math.cos(sa),  y1 = cy + R * Math.sin(sa)
  const x2 = cx + R * Math.cos(ea),  y2 = cy + R * Math.sin(ea)
  const x3 = cx + ri * Math.cos(ea), y3 = cy + ri * Math.sin(ea)
  const x4 = cx + ri * Math.cos(sa), y4 = cy + ri * Math.sin(sa)
  return `M ${x1} ${y1} A ${R} ${R} 0 ${la} 1 ${x2} ${y2} L ${x3} ${y3} A ${ri} ${ri} 0 ${la} 0 ${x4} ${y4} Z`
}

interface PizzaSlice extends PizzaFatia { isNaoAlocado?: boolean }

function GraficoPizza({
  fatias,
  totalCapacidadeMin,
  naoAlocadoMin,
}: {
  fatias: PizzaFatia[]
  totalCapacidadeMin: number
  naoAlocadoMin: number
}) {
  const [hovIdx, setHovIdx] = useState<number | null>(null)

  const base = Math.max(totalCapacidadeMin, fatias.reduce((s, f) => s + f.minutos, 0), 1)

  const allSlices: PizzaSlice[] = useMemo(() => {
    const slices: PizzaSlice[] = fatias.map((f) => ({ ...f }))
    if (naoAlocadoMin > 0) {
      slices.push({
        nome: "Não alocado",
        cor: "#d0d5dd",
        minutos: naoAlocadoMin,
        percentual: Math.round((naoAlocadoMin / base) * 1000) / 10,
        isNaoAlocado: true,
      })
    }
    return slices
  }, [fatias, naoAlocadoMin, base])

  const arcs = useMemo(() => {
    let angle = -Math.PI / 2
    return allSlices.map((slice) => {
      const span = (slice.minutos / base) * 2 * Math.PI
      const sa = angle
      angle += span
      return { sa, ea: angle, slice }
    })
  }, [allSlices, base])

  const pctAlocado = Math.round(((base - naoAlocadoMin) / base) * 100)

  return (
    <div className={styles.pizzaWrap}>
      <svg viewBox="0 0 240 240" className={styles.pizzaSvg}>
        {arcs.map(({ sa, ea, slice }, i) => (
          <path
            key={i}
            d={arcPath(sa, ea, PIZZA_R, PIZZA_r, PIZZA_CX, PIZZA_CY)}
            fill={slice.cor}
            opacity={hovIdx === null || hovIdx === i ? 1 : 0.55}
            className={styles.pizzaSlice}
            onMouseEnter={() => setHovIdx(i)}
            onMouseLeave={() => setHovIdx(null)}
          />
        ))}
        {/* Centro */}
        <text x={PIZZA_CX} y={PIZZA_CY - 10} textAnchor="middle" className={styles.pizzaCenterPct}>
          {pctAlocado}%
        </text>
        <text x={PIZZA_CX} y={PIZZA_CY + 8} textAnchor="middle" className={styles.pizzaCenterSub}>
          alocado
        </text>
        {/* Tooltip da fatia hovered */}
        {hovIdx !== null && (
          <text x={PIZZA_CX} y={PIZZA_CY + 24} textAnchor="middle" className={styles.pizzaCenterMin}>
            {fmtMin(allSlices[hovIdx].minutos)}
          </text>
        )}
      </svg>

      <div className={styles.pizzaLegenda}>
        {allSlices.map((s, i) => (
          <div
            key={i}
            className={`${styles.pizzaLegItem} ${hovIdx === i ? styles.pizzaLegItemHov : ""}`}
            onMouseEnter={() => setHovIdx(i)}
            onMouseLeave={() => setHovIdx(null)}
          >
            <span className={styles.pizzaDot} style={{ background: s.cor }} />
            <span className={styles.pizzaNome}>{s.nome}</span>
            <span className={styles.pizzaPct}>{s.percentual.toFixed(1)}%</span>
            <span className={styles.pizzaHoras}>{fmtMin(s.minutos)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Barra de contribuição do usuário em relação ao total alocado
//   totalAlocado    = pontos_alocados_bloco (kpi.fluxo_ut)      = 100%
//   totalDistribuido= pontos_total_bloco    (distribuicao_pontos)= K
//   usuario         = pontos_usuario_bloco
// ─────────────────────────────────────────────────────────────

function ProgressoDuplo({
  totalAlocado,
  totalDistribuido,
  usuario,
  label,
}: {
  totalAlocado: number
  totalDistribuido: number
  usuario: number
  label?: string
}) {
  const base       = Math.max(totalAlocado, totalDistribuido, 1)
  const pctUsuario = pct(usuario, base)
  const pctDistrib = pct(totalDistribuido, base)

  return (
    <div className={styles.progressoDuplo}>
      {label && <span className={styles.progressoLabel}>{label}</span>}
      <div className={styles.progressoTrack}>
        {/* Camada 1 — todos os pontos já distribuídos */}
        <div className={styles.progressoOutros} style={{ width: `${pctDistrib}%` }} />
        {/* Camada 2 — contribuição do usuário (sobrepõe) */}
        <div className={styles.progressoUsuario} style={{ width: `${pctUsuario}%` }} />
      </div>
      <div className={styles.progressoLegenda}>
        <span className={styles.legUsuario}>
          <span className={styles.legDotUsuario} />
          {` Sua contribuição: ${fmtPts(usuario)} pts (${pctUsuario}%)`}
        </span>
        <span className={styles.legDistribuido}>
          <span className={styles.legDotOutros} />
          {` Pontos já distribuídos: ${fmtPts(totalDistribuido)} pts (${pctDistrib}%)`}
        </span>
        <span className={styles.legTotal}>{`Total de pontos: ${fmtPts(base)} pts (100%)`}</span>
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
              <td className={styles.subfasePts}>
                <span className={styles.sfPtsUser}>{fmtPts(sf.pontos)}</span>
                {sf.pontos_total_subfase > 0 && (
                  <span className={styles.sfPtsTotal}>{` / ${fmtPts(sf.pontos_total_subfase)} pts`}</span>
                )}
              </td>
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

  // Base para o header = total alocado (fluxo_ut); fallback para total distribuído
  const baseBloco  = Math.max(bloco.pontos_alocados_bloco, bloco.pontos_total_bloco, 1)
  const pctContrib = pct(ptsUsuario, baseBloco)
  const pctDistrib = pct(bloco.pontos_total_bloco, baseBloco)

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
              {/* distribuídos a todos */}
              <div className={styles.blocoBarTotal} style={{ width: `${pctDistrib}%` }} />
              {/* contribuição do usuário */}
              <div className={styles.blocoBarUser} style={{ width: `${pctContrib}%` }} />
            </div>
          </div>
          <span className={styles.blocoStats}>
            <span className={styles.blocoUserPts}>{fmtPts(ptsUsuario)} pts</span>
            {" / "}
            <span className={styles.blocoTotalPts}>{fmtPts(baseBloco)} pts</span>
            <span className={styles.blocoContrib}>{` (${pctContrib}%)`}</span>
          </span>
          <span className={styles.blocoToggle}>{aberto ? "▲" : "▼"}</span>
        </div>
      </button>
      {aberto && (
        <div className={styles.blocoBody}>
          <div className={styles.blocoProgressSection}>
            <ProgressoDuplo
              totalAlocado={bloco.pontos_alocados_bloco}
              totalDistribuido={bloco.pontos_total_bloco}
              usuario={ptsUsuario}
            />
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

  const [mesPizza, setMesPizza] = useState(() => format(new Date(), "yyyy-MM"))
  const { data: pizzaData } = useQuery({
    queryKey: ["minhaPizza", mesPizza],
    queryFn: () => getMinhaPizzaMensal(mesPizza),
  })

  const kpiTs = data?.kpi_calculado_em
    ? formatDistanceToNow(parseISO(data.kpi_calculado_em), { addSuffix: true, locale: ptBR })
    : null

  const totalBlocos      = data?.blocos.length ?? 0
  const ptsTotalGeral    = data?.pontos_total_geral ?? 0   // total distribuído (K)
  const ptsUsuarioGeral  = data?.pontos_usuario_geral ?? 0
  const ptsAlocadoGeral  = data?.blocos.reduce((s, b) => s + b.pontos_alocados_bloco, 0) ?? 0  // total alocado (Y)
  const baseGeral        = Math.max(ptsAlocadoGeral, ptsTotalGeral, 1)
  const pctGeral         = pct(ptsUsuarioGeral, baseGeral)

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
          sub={`${fmtPts(ptsUsuarioGeral)} pts / ${fmtPts(baseGeral)} pts totais`}
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
        <h2 className={styles.sectionTitle}>Sua contribuição em relação ao total</h2>
        <div className={styles.progressoCard}>
          <ProgressoDuplo
            totalAlocado={ptsAlocadoGeral}
            totalDistribuido={ptsTotalGeral}
            usuario={ptsUsuarioGeral}
          />
        </div>
      </div>

      {data && data.timeline.length > 0 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Evolução acumulada de horas em produção (últimos 45 dias)</h2>
          <div className={styles.chartCard}>
            <GraficoDiario dados={data.timeline} />
          </div>
          <p className={styles.chartCaption}>
            Reta J = meta prevista acum. · Reta K = horas normais acum. · Reta P = normal + extra acum.
          </p>
        </div>
      )}

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>
            Distribuição de horas —{" "}
            {format(parseISO(`${mesPizza}-01`), "MMMM yyyy", { locale: ptBR })}
          </h2>
          <input
            type="month"
            value={mesPizza}
            onChange={(e) => setMesPizza(e.target.value)}
            className={styles.mesInput}
          />
        </div>
        {pizzaData && pizzaData.total_capacidade_min > 0 ? (
          <GraficoPizza
            fatias={pizzaData.fatias}
            totalCapacidadeMin={pizzaData.total_capacidade_min}
            naoAlocadoMin={pizzaData.nao_alocado_min}
          />
        ) : (
          <div className={styles.emptyState}>Nenhum lançamento registrado neste mês.</div>
        )}
      </div>

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

  const { data: usuarios } = useQuery({
    queryKey: ["usuarios"],
    queryFn: getUsuarios,
  })

  const [mesPizza, setMesPizza] = useState(() => format(new Date(), "yyyy-MM"))
  const [usuarioPizza, setUsuarioPizza] = useState(0)
  const { data: pizzaData } = useQuery({
    queryKey: ["pizzaAdmin", mesPizza, usuarioPizza],
    queryFn: () => getPizzaMensal(mesPizza, usuarioPizza),
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

      {dashboard && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Evolução acumulada de horas em produção — todos os operadores</h2>
          <div className={styles.chartCard}>
            <GraficoMensal dados={dashboard.timeline_mensal ?? []} />
          </div>
          <p className={styles.chartCaption}>
            Reta J = meta prevista acum. · Reta K = horas normais acum. · Reta P = normal + extra acum.
          </p>
        </div>
      )}

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>
            Distribuição de horas —{" "}
            {format(parseISO(`${mesPizza}-01`), "MMMM yyyy", { locale: ptBR })}
          </h2>
          <div className={styles.pizzaControls}>
            <input
              type="month"
              value={mesPizza}
              onChange={(e) => setMesPizza(e.target.value)}
              className={styles.mesInput}
            />
            <select
              value={usuarioPizza}
              onChange={(e) => setUsuarioPizza(Number(e.target.value))}
              className={styles.usuarioSelect}
            >
              <option value={0}>Todos os operadores</option>
              {(usuarios ?? []).map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome_guerra ?? u.nome}
                </option>
              ))}
            </select>
          </div>
        </div>
        {pizzaData && pizzaData.total_capacidade_min > 0 ? (
          <GraficoPizza
            fatias={pizzaData.fatias}
            totalCapacidadeMin={pizzaData.total_capacidade_min}
            naoAlocadoMin={pizzaData.nao_alocado_min}
          />
        ) : (
          <div className={styles.emptyState}>Nenhum lançamento registrado neste mês.</div>
        )}
      </div>

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
