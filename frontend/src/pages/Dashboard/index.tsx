// ============================================================
// Dashboard — visão de KPI e capacidade
// Operador: blocos vinculados, pontos por papel, timeline
// Admin:    visão global, projetos, sync SAP
// ============================================================
import {
  getMeuDashboard, executarSync, getKpiDashboard, getKpiProjetos, getSyncStatus,
  getMinhaPizzaMensal, getPizzaMensal, getUsuarios, getKpiTimelineDiario,
} from "@/api/endpoints"
import { useAuth } from "@/context/AuthContext"
import type {
  AlertaNotaAusente, BlocoDetalheUsuario, BlocoDestaque, DiaHorasResposta,
  DistribuicaoCiclo, MesTrilha, PizzaFatia, PontosSubfaseResposta,
  RankingOperador, SemanaVelocidade, SubfaseDisponivel,
} from "@/types"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { format, formatDistanceToNow, parseISO, subMonths, startOfMonth } from "date-fns"
import { ptBR } from "date-fns/locale"
import { useMemo, useState } from "react"
import styles from "./Dashboard.module.css"

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

/** Gera lista de meses dos últimos N meses (inclusive o atual), do mais recente ao mais antigo */
function gerarMesesOpcoes(n = 24): { value: string; label: string }[] {
  const hoje = startOfMonth(new Date())
  return Array.from({ length: n }, (_, i) => {
    const d = subMonths(hoje, i)
    return {
      value: format(d, "yyyy-MM"),
      label: format(d, "MMMM yyyy", { locale: ptBR }),
    }
  })
}

const MESES_OPCOES = gerarMesesOpcoes(36)

/** Select elegante de mês — "março 2026" — sem risco de estado parcial */
function MesSeletor({
  value,
  onChange,
  className,
}: {
  value: string
  onChange: (v: string) => void
  className?: string
}) {
  return (
    <select
      className={className ?? styles.timelineMesPicker}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {MESES_OPCOES.map((m) => (
        <option key={m.value} value={m.value}>{m.label}</option>
      ))}
    </select>
  )
}

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
const CHART_H = 160
const PAD = { top: 10, right: 20, bottom: 34, left: 50 }
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
        {yTicks.map((h) => (
          <g key={h}>
            <line x1={PAD.left} y1={yOf(h * 60)} x2={PAD.left + INNER_W} y2={yOf(h * 60)} className={styles.gridLine} />
            <text x={PAD.left - 8} y={yOf(h * 60) + 4} className={styles.axisLabel} textAnchor="end">{h}h</text>
          </g>
        ))}
        {dados.map((d, i) => i % xLabelStep === 0 && (
          <text key={d.data} x={xOf(i)} y={CHART_H - 4} className={styles.axisLabel} textAnchor="middle">
            {format(parseISO(d.data), "dd/MM")}
          </text>
        ))}
        {n > 1 && <polyline points={polyJ} fill="none" className={styles.linePrevista} strokeDasharray="6 3" />}
        {n > 1 && <polyline points={polyK} fill="none" className={styles.lineNormal} />}
        {n > 1 && <polyline points={polyP} fill="none" className={styles.lineLancada} />}
        {dados.map((_, i) => {
          const w = n > 1 ? INNER_W / (n - 1) : INNER_W
          return <rect key={i} x={xOf(i) - w / 2} y={PAD.top} width={w} height={INNER_H} fill="transparent" onMouseEnter={() => setHovIdx(i)} />
        })}
        {hovIdx !== null && (
          <>
            <line x1={xOf(hovIdx)} y1={PAD.top} x2={xOf(hovIdx)} y2={PAD.top + INNER_H} className={styles.hoverLine} />
            <circle cx={xOf(hovIdx)} cy={yOf(acum[hovIdx].j)} r={3.5} className={styles.dotPrev} />
            <circle cx={xOf(hovIdx)} cy={yOf(acum[hovIdx].k)} r={3.5} className={styles.dotNormal} />
            <circle cx={xOf(hovIdx)} cy={yOf(acum[hovIdx].p)} r={3.5} className={styles.dotLanc} />
          </>
        )}
      </svg>

      {/* Legenda elegante — sem prefixos J/K/P */}
      <div className={styles.chartLegend}>
        <span className={styles.legendItem}>
          <span className={`${styles.legendSym} ${styles.legendSymDash} ${styles.legendJ}`} />
          <span className={styles.legendJ}>Previsto acum.</span>
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.legendSym} ${styles.legendK}`} />
          <span className={styles.legendK}>Realizadas acum.</span>
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.legendSym} ${styles.legendP}`} />
          <span className={styles.legendP}>Real. + Extra acum.</span>
        </span>
      </div>

      {/* Barra de dados — abaixo do SVG, fora das linhas */}
      <div className={styles.chartDataBar}>
        {hovIdx !== null ? (
          <>
            <span className={styles.chartDataBarDate}>{format(parseISO(dados[hovIdx].data), "dd/MM/yyyy", { locale: ptBR })}</span>
            <span className={styles.tooltipJ}>Previsto {fmtMin(acum[hovIdx].j)}</span>
            <span className={styles.tooltipK}>Realizadas {fmtMin(acum[hovIdx].k)}</span>
            <span className={styles.tooltipP}>Real.+Extra {fmtMin(acum[hovIdx].p)}</span>
          </>
        ) : (
          <span className={styles.chartDataBarHint}>↔ passe o cursor sobre o gráfico</span>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// SVG Gráfico mensal acumulado (admin) — mesma estrutura, dados mensais
// ─────────────────────────────────────────────────────────────

function GraficoMensal({ dados, isDaily = false }: { dados: MesTrilha[]; isDaily?: boolean }) {
  const [hovIdx, setHovIdx] = useState<number | null>(null)

  const maxD = useMemo(
    () => Math.max(...dados.map((d) => d.minutos_divergente_acum ?? 0), 0),
    [dados],
  )
  const showD = maxD > 0

  const maxMin = useMemo(
    () => Math.max(
      ...dados.map((d) => Math.max(
        d.minutos_previstos_acum,
        d.minutos_lancados_normal_acum,
        d.minutos_lancados_total_acum,
        d.minutos_divergente_acum ?? 0,
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
  const polyD = showD
    ? dados.map((d, i) => `${xOf(i)},${yOf(d.minutos_divergente_acum ?? 0)}`).join(" ")
    : ""

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
        {yTicks.map((h) => (
          <g key={h}>
            <line x1={PAD.left} y1={yOf(h * 60)} x2={PAD.left + INNER_W} y2={yOf(h * 60)} className={styles.gridLine} />
            <text x={PAD.left - 8} y={yOf(h * 60) + 4} className={styles.axisLabel} textAnchor="end">{h}h</text>
          </g>
        ))}
        {dados.map((d, i) => i % xLabelStep === 0 && (
          <text key={d.mes} x={xOf(i)} y={CHART_H - 4} className={styles.axisLabel} textAnchor="middle">
            {isDaily
              ? format(parseISO(d.mes), "dd/MM")
              : format(parseISO(d.mes), "MMM/yy", { locale: ptBR })}
          </text>
        ))}
        <polyline points={polyJ} fill="none" className={styles.linePrevista} strokeDasharray="6 3" />
        <polyline points={polyK} fill="none" className={styles.lineNormal} />
        <polyline points={polyP} fill="none" className={styles.lineLancada} />
        {showD && <polyline points={polyD} fill="none" className={styles.lineDivergente} strokeDasharray="4 4" />}
        {dados.map((_, i) => {
          const w = n > 1 ? INNER_W / (n - 1) : INNER_W
          return <rect key={i} x={xOf(i) - w / 2} y={PAD.top} width={w} height={INNER_H} fill="transparent" onMouseEnter={() => setHovIdx(i)} />
        })}
        {hovIdx !== null && (
          <>
            <line x1={xOf(hovIdx)} y1={PAD.top} x2={xOf(hovIdx)} y2={PAD.top + INNER_H} className={styles.hoverLine} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_previstos_acum)} r={3.5} className={styles.dotPrev} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_lancados_normal_acum)} r={3.5} className={styles.dotNormal} />
            <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_lancados_total_acum)} r={3.5} className={styles.dotLanc} />
            {showD && <circle cx={xOf(hovIdx)} cy={yOf(dados[hovIdx].minutos_divergente_acum ?? 0)} r={3.5} className={styles.dotDiv} />}
          </>
        )}
      </svg>

      {/* Legenda elegante — nome sem prefixo J/K/P */}
      <div className={styles.chartLegend}>
        <span className={styles.legendItem}>
          <span className={`${styles.legendSym} ${styles.legendSymDash} ${styles.legendJ}`} />
          <span className={styles.legendJ}>Previsto acum.</span>
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.legendSym} ${styles.legendK}`} />
          <span className={styles.legendK}>Realizadas acum.</span>
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.legendSym} ${styles.legendP}`} />
          <span className={styles.legendP}>Real. + Extra acum.</span>
        </span>
        {showD && (
          <span className={styles.legendItem}>
            <span className={`${styles.legendSym} ${styles.legendSymDash} ${styles.legendD}`} />
            <span className={styles.legendD}>Fora do bloco acum.</span>
          </span>
        )}
      </div>

      {/* Barra de dados — abaixo do SVG, fora das linhas */}
      <div className={styles.chartDataBar}>
        {hovIdx !== null ? (
          <>
            <span className={styles.chartDataBarDate}>
              {isDaily
                ? format(parseISO(dados[hovIdx].mes), "dd 'de' MMMM", { locale: ptBR })
                : format(parseISO(dados[hovIdx].mes), "MMMM yyyy", { locale: ptBR })}
            </span>
            <span className={styles.tooltipJ}>Previsto {fmtMin(dados[hovIdx].minutos_previstos_acum)}</span>
            <span className={styles.tooltipK}>Realizadas {fmtMin(dados[hovIdx].minutos_lancados_normal_acum)}</span>
            <span className={styles.tooltipP}>Real.+Extra {fmtMin(dados[hovIdx].minutos_lancados_total_acum)}</span>
            {showD && <span className={styles.tooltipD}>Fora bloco {fmtMin(dados[hovIdx].minutos_divergente_acum ?? 0)}</span>}
          </>
        ) : (
          <span className={styles.chartDataBarHint}>↔ passe o cursor sobre o gráfico</span>
        )}
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
        {/* Centro — mostra % alocado ou detalhe da fatia ao hover */}
        {hovIdx === null ? (
          <>
            <text x={PIZZA_CX} y={PIZZA_CY - 12} textAnchor="middle" className={styles.pizzaCenterPct}>
              {pctAlocado}%
            </text>
            <text x={PIZZA_CX} y={PIZZA_CY + 6} textAnchor="middle" className={styles.pizzaCenterSub}>
              alocado
            </text>
            <text x={PIZZA_CX} y={PIZZA_CY + 22} textAnchor="middle" className={styles.pizzaCenterCap}>
              {fmtMin(base)}
            </text>
          </>
        ) : (
          <>
            <text x={PIZZA_CX} y={PIZZA_CY - 6} textAnchor="middle" className={styles.pizzaCenterPct}>
              {allSlices[hovIdx].percentual.toFixed(1)}%
            </text>
            <text x={PIZZA_CX} y={PIZZA_CY + 12} textAnchor="middle" className={styles.pizzaCenterMin}>
              {fmtMin(allSlices[hovIdx].minutos)}
            </text>
          </>
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
        <div className={styles.pizzaCapacidadeTotal}>
          <span>Capacidade total (dias úteis):</span>
          <strong>{fmtMin(base)}</strong>
        </div>
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
// BlocoProgressoCard — card por bloco com UTs, pontos e top performers
// ─────────────────────────────────────────────────────────────

function BlocoProgressoCard({ bloco }: { bloco: BlocoDestaque }) {
  const prog = bloco.progresso ?? 0
  const progColor = prog >= 70 ? "#10B981" : prog >= 35 ? "#F59E0B" : "#EF4444"
  const ptsFaltam = bloco.pontos_total - bloco.pontos_realizados

  return (
    <div className={styles.blocoDestaqueCard}>
      {/* strip de cor à esquerda indicando progresso */}
      <div className={styles.blocoDestaqueStrip} style={{ background: progColor }} />

      <div className={styles.blocoDestaqueMain}>
        {/* Cabeçalho */}
        <div className={styles.blocoDestaqueHeader}>
          <div className={styles.blocoDestaqueNome} title={bloco.bloco_nome}>{bloco.bloco_nome}</div>
          <div className={styles.blocoDestaqueMeta} title={`${bloco.projeto_nome} · ${bloco.lote_nome}`}>
            {bloco.projeto_nome} · {bloco.lote_nome}
          </div>
        </div>

        {/* Barra de progresso */}
        <div className={styles.blocoDestaqueProg}>
          <div className={styles.blocoDestaqueTrack}>
            <div
              className={styles.blocoDestaqueFill}
              style={{ width: `${Math.min(100, prog)}%`, background: progColor }}
            />
          </div>
          <span className={styles.blocoDestaquePct} style={{ color: progColor }}>
            {prog.toFixed(1)}%
          </span>
        </div>

        {/* Contagem de UTs */}
        <div className={styles.blocoDestaqueUts}>
          <span className={styles.utConcluida}>{bloco.uts_concluidas} concluídas</span>
          {bloco.uts_em_andamento > 0 && (
            <span className={styles.utAndamento}>{bloco.uts_em_andamento} em andamento</span>
          )}
          {bloco.uts_sem_inicio > 0 && (
            <span className={styles.utPendente}>{bloco.uts_sem_inicio} não iniciadas</span>
          )}
          <span className={styles.utTotal}>/{bloco.uts_total} total</span>
        </div>

        {/* Pontos */}
        <div className={styles.blocoDestaquePontos}>
          <span className={styles.ptsReal}>{fmtPts(bloco.pontos_realizados)} pts</span>
          <span className={styles.ptsSep}> / </span>
          <span className={styles.ptsTotal}>{fmtPts(bloco.pontos_total)} pts</span>
          {ptsFaltam > 0.01 && (
            <span className={styles.ptsFaltam}> · {fmtPts(ptsFaltam)} restam</span>
          )}
        </div>

        {/* Top performers */}
        {(bloco.top_executores.length > 0 || bloco.top_revisores.length > 0) && (
          <div className={styles.blocoDestaqueRanks}>
            {bloco.top_executores.length > 0 && (
              <div className={styles.rankCol}>
                <div className={styles.rankColTitle}>
                  <span className={styles.rankIcon}>★</span> Execução
                </div>
                {bloco.top_executores.map((c, i) => (
                  <div key={c.usuario_id} className={styles.rankRow}>
                    <span className={styles.rankPos}>{i + 1}</span>
                    <span className={styles.rankNome}>{c.nome_guerra}</span>
                    <span className={styles.rankPts}>{fmtPts(c.pontos)}</span>
                    <span className={styles.rankPct}>{c.percentual.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
            {bloco.top_revisores.length > 0 && (
              <div className={styles.rankCol}>
                <div className={styles.rankColTitle}>
                  <span className={styles.rankIconRev}>✦</span> Revisão
                </div>
                {bloco.top_revisores.map((c, i) => (
                  <div key={c.usuario_id} className={styles.rankRow}>
                    <span className={styles.rankPos}>{i + 1}</span>
                    <span className={styles.rankNome}>{c.nome_guerra}</span>
                    <span className={styles.rankPts}>{fmtPts(c.pontos)}</span>
                    <span className={styles.rankPct}>{c.percentual.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// RankingPanel — tabela global de operadores com mini-bar, filtros e ordenação
// ─────────────────────────────────────────────────────────────

type FuncaoFiltro = "todos" | "executor" | "revisor" | "corretor"
type SortCol = "nome" | "executor" | "revisor" | "corretor" | "total"

interface RankingPanelProps {
  operadores: RankingOperador[]
  subfases: SubfaseDisponivel[]
  subfaseFiltro: number | null
  blocoFiltro: number | null
  onSubfaseFiltro: (subfaseId: number | null, blocoId?: number | null) => void
}

function RankingPanel({ operadores, subfases, subfaseFiltro, blocoFiltro, onSubfaseFiltro }: RankingPanelProps) {
  const [funcao, setFuncao] = useState<FuncaoFiltro>("todos")
  const [sortCol, setSortCol] = useState<SortCol>("total")
  const [sortAsc, setSortAsc] = useState(false)

  const pontosFuncao = (op: RankingOperador): number => {
    if (funcao === "executor") return op.pontos_executor
    if (funcao === "revisor")  return op.pontos_revisor
    if (funcao === "corretor") return op.pontos_corretor
    return op.pontos_total
  }

  const sorted = useMemo(() => {
    const arr = [...operadores]
    const dir = sortAsc ? 1 : -1
    arr.sort((a, b) => {
      if (sortCol === "nome")     return dir * a.nome_guerra.localeCompare(b.nome_guerra)
      if (sortCol === "executor") return dir * (a.pontos_executor - b.pontos_executor)
      if (sortCol === "revisor")  return dir * (a.pontos_revisor  - b.pontos_revisor)
      if (sortCol === "corretor") return dir * (a.pontos_corretor - b.pontos_corretor)
      // total (default): ordena pela função ativa
      return dir * (pontosFuncao(a) - pontosFuncao(b))
    })
    return arr
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [operadores, sortCol, sortAsc, funcao])

  const maxPts = Math.max(...sorted.map(pontosFuncao), 1)

  function handleSort(col: SortCol) {
    if (sortCol === col) setSortAsc((v) => !v)
    else { setSortCol(col); setSortAsc(false) }
  }

  function SortIcon({ col }: { col: SortCol }) {
    if (sortCol !== col) return <span className={styles.sortIconInactive}>↕</span>
    return <span className={styles.sortIconActive}>{sortAsc ? "↑" : "↓"}</span>
  }

  // Quando não há bloco selecionado, usa chave composta "blocoId_subfaseId" para
  // auto-selecionar o bloco junto com a subfase. Quando bloco já está filtrado, usa só subfase_id.
  function subfaseOptionValue(sf: SubfaseDisponivel): string {
    if (blocoFiltro) return String(sf.subfase_id)
    return sf.bloco_id ? `${sf.bloco_id}_${sf.subfase_id}` : String(sf.subfase_id)
  }

  function subfaseOptionLabel(sf: SubfaseDisponivel): string {
    if (blocoFiltro || !sf.bloco_nome) return sf.subfase_nome
    return `${sf.bloco_nome} — ${sf.subfase_nome}`
  }

  function handleSubfaseChange(val: string) {
    if (!val) { onSubfaseFiltro(null, null); return }
    if (val.includes("_")) {
      const [bId, sfId] = val.split("_")
      onSubfaseFiltro(Number(sfId), Number(bId))
    } else {
      onSubfaseFiltro(Number(val))
    }
  }

  // Valor atual do select — constrói a chave composta se não há bloco ativo
  const subfaseSelectValue = (() => {
    if (!subfaseFiltro) return ""
    if (blocoFiltro) return String(subfaseFiltro)
    const sf = subfases.find((s) => s.subfase_id === subfaseFiltro)
    return sf ? subfaseOptionValue(sf) : String(subfaseFiltro)
  })()

  return (
    <div className={styles.rankingWrap}>
      {/* Barra de filtros — sempre visível mesmo sem resultados */}
      <div className={styles.rankingFilters}>
        <div className={styles.rankingFilterGroup}>
          <label className={styles.rankingFilterLabel}>Subfase</label>
          <select
            className={styles.rankingFilterSelect}
            value={subfaseSelectValue}
            onChange={(e) => handleSubfaseChange(e.target.value)}
          >
            <option value="">Todas as subfases</option>
            {subfases.map((sf) => (
              <option key={subfaseOptionValue(sf)} value={subfaseOptionValue(sf)}>
                {subfaseOptionLabel(sf)}
              </option>
            ))}
          </select>
        </div>
        <div className={styles.rankingFilterGroup}>
          <label className={styles.rankingFilterLabel}>Função</label>
          <div className={styles.rankingFuncaoBtns}>
            {(["todos", "executor", "revisor", "corretor"] as FuncaoFiltro[]).map((f) => (
              <button
                key={f}
                type="button"
                className={`${styles.rankingFuncaoBtn} ${funcao === f ? styles.rankingFuncaoBtnActive : ""}`}
                onClick={() => setFuncao(f)}
              >
                {f === "todos" ? "Todos" : f === "executor" ? "Exec." : f === "revisor" ? "Rev." : "Cor."}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sem resultados — abaixo dos filtros para que o usuário possa alterar a seleção */}
      {operadores.length === 0 && (
        <div className={styles.emptyState}>Nenhum operador com produção registrada para este contexto.</div>
      )}

      {/* Tabela */}
      {operadores.length > 0 && <div className={styles.rankingTable}>
        <div className={styles.rankingHead}>
          <span className={styles.rankingCellPos}>#</span>
          <button type="button" className={`${styles.rankingCellNome} ${styles.rankingSortBtn}`} onClick={() => handleSort("nome")}>
            Operador <SortIcon col="nome" />
          </button>
          {(funcao === "todos" || funcao === "executor") && (
            <button type="button" className={`${styles.rankingCellPts} ${styles.rankingSortBtn}`} onClick={() => handleSort("executor")} title="Pontos como executor">
              Exec. <SortIcon col="executor" />
            </button>
          )}
          {(funcao === "todos" || funcao === "revisor") && (
            <button type="button" className={`${styles.rankingCellPts} ${styles.rankingSortBtn}`} onClick={() => handleSort("revisor")} title="Pontos como revisor">
              Rev. <SortIcon col="revisor" />
            </button>
          )}
          {(funcao === "todos" || funcao === "corretor") && (
            <button type="button" className={`${styles.rankingCellPts} ${styles.rankingSortBtn}`} onClick={() => handleSort("corretor")} title="Pontos como corretor">
              Cor. <SortIcon col="corretor" />
            </button>
          )}
          <button type="button" className={`${styles.rankingCellTotal} ${styles.rankingSortBtn}`} onClick={() => handleSort("total")}>
            {funcao === "todos" ? "Total" : funcao === "executor" ? "Pontos Exec." : funcao === "revisor" ? "Pontos Rev." : "Pontos Cor."}
            {" "}<SortIcon col="total" />
          </button>
          <span className={styles.rankingCellBar} />
        </div>

        {sorted.map((op, idx) => {
          const pts = pontosFuncao(op)
          const barW    = Math.round((pts / maxPts) * 100)
          const safeTot = op.pontos_total || 1
          const barExec = Math.round((op.pontos_executor / safeTot) * 100)
          const barRev  = Math.round((op.pontos_revisor  / safeTot) * 100)
          return (
            <div key={op.usuario_id} className={styles.rankingRow}>
              <span className={styles.rankingCellPos}>{idx + 1}</span>
              <span className={styles.rankingCellNome}>{op.nome_guerra}</span>
              {(funcao === "todos" || funcao === "executor") && (
                <span className={`${styles.rankingCellPts} ${funcao === "executor" ? styles.rankingCellPtsActive : ""}`}>
                  {fmtPts(op.pontos_executor)}
                </span>
              )}
              {(funcao === "todos" || funcao === "revisor") && (
                <span className={`${styles.rankingCellPts} ${funcao === "revisor" ? styles.rankingCellPtsActive : ""}`}>
                  {fmtPts(op.pontos_revisor)}
                </span>
              )}
              {(funcao === "todos" || funcao === "corretor") && (
                <span className={`${styles.rankingCellPts} ${funcao === "corretor" ? styles.rankingCellPtsActive : ""}`}>
                  {fmtPts(op.pontos_corretor)}
                </span>
              )}
              <span className={styles.rankingCellTotal}>{fmtPts(pts)}</span>
              <span className={styles.rankingCellBar}>
                <span className={styles.rankingBarTrack} style={{ width: `${barW}%` }}>
                  {funcao === "todos" ? (
                    <>
                      <span className={styles.rankingBarExec} style={{ width: `${barExec}%` }} />
                      <span className={styles.rankingBarRev}  style={{ width: `${barRev}%`, left: `${barExec}%` }} />
                    </>
                  ) : (
                    <span
                      className={
                        funcao === "executor" ? styles.rankingBarExec
                        : funcao === "revisor"  ? styles.rankingBarRev
                        : styles.rankingBarCor
                      }
                      style={{ width: "100%" }}
                    />
                  )}
                </span>
              </span>
            </div>
          )
        })}

        <div className={styles.rankingLegend}>
          <span className={styles.rlExec}>■ Execução</span>
          <span className={styles.rlRev}>■ Revisão</span>
          <span className={styles.rlCor}>■ Correção</span>
        </div>
      </div>}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// GraficoVelocidade — barras semanais de UTs concluídas
// ─────────────────────────────────────────────────────────────

const VEL_W = 800
const VEL_H = 130
const VEL_PAD = { top: 10, right: 16, bottom: 30, left: 36 }
const VEL_IW = VEL_W - VEL_PAD.left - VEL_PAD.right
const VEL_IH = VEL_H - VEL_PAD.top - VEL_PAD.bottom

function GraficoVelocidade({ dados }: { dados: SemanaVelocidade[] }) {
  const [hovIdx, setHovIdx] = useState<number | null>(null)
  const n = dados.length
  if (n === 0) return <div className={styles.emptyState}>Sem dados de velocidade.</div>

  const maxUts = Math.max(...dados.map((d) => d.uts_concluidas), 1)
  const barW   = Math.floor(VEL_IW / n) - 4
  const barX   = (i: number) => VEL_PAD.left + i * (VEL_IW / n) + (VEL_IW / n - barW) / 2
  const barH   = (v: number) => Math.max(0, (v / maxUts) * VEL_IH)
  const barY   = (v: number) => VEL_PAD.top + VEL_IH - barH(v)

  const yTicks = Array.from({ length: Math.min(maxUts + 1, 6) }, (_, k) =>
    Math.round((k * maxUts) / Math.min(maxUts, 5))
  )

  return (
    <div className={styles.chartWrap}>
      <svg viewBox={`0 0 ${VEL_W} ${VEL_H}`} className={styles.chartSvg}
        onMouseLeave={() => setHovIdx(null)}>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={VEL_PAD.left} y1={barY(v)} x2={VEL_PAD.left + VEL_IW} y2={barY(v)} className={styles.gridLine} />
            <text x={VEL_PAD.left - 4} y={barY(v) + 3} className={styles.axisLabel} textAnchor="end">{v}</text>
          </g>
        ))}
        {dados.map((d, i) => (
          <g key={d.semana_inicio}>
            <rect
              x={barX(i)} y={barY(d.uts_concluidas)}
              width={barW} height={barH(d.uts_concluidas)}
              className={hovIdx === i ? styles.velBarHov : styles.velBar}
              rx={2}
              onMouseEnter={() => setHovIdx(i)}
            />
            <text x={barX(i) + barW / 2} y={VEL_H - 3} className={styles.axisLabel} textAnchor="middle">
              {d.semana_label}
            </text>
            {d.uts_concluidas > 0 && (
              <text x={barX(i) + barW / 2} y={barY(d.uts_concluidas) - 3} className={styles.velBarLabel} textAnchor="middle">
                {d.uts_concluidas}
              </text>
            )}
          </g>
        ))}
      </svg>

      {/* Barra de dados — abaixo do SVG, fora das barras */}
      <div className={styles.chartDataBar}>
        {hovIdx !== null ? (
          <>
            <span className={styles.chartDataBarDate}>semana {dados[hovIdx].semana_label}</span>
            <span className={styles.tooltipK}>{dados[hovIdx].uts_concluidas} UTs concluídas</span>
            <span className={styles.tooltipP}>{fmtPts(dados[hovIdx].pontos_realizados)} pts</span>
          </>
        ) : (
          <span className={styles.chartDataBarHint}>↔ passe o cursor sobre uma barra</span>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// DistribuicaoCiclos — barras horizontais por ciclo
// ─────────────────────────────────────────────────────────────

const CICLO_LABELS: Record<string, string> = {
  CICLO_1_PADRAO:             "Ciclo 1 — Padrão",
  CICLO_2_REVISAO_CORRECAO:   "Ciclo 2 — Rev+Cor",
  CICLO_3_SEM_CORRECAO:       "Ciclo 3 — Sem Cor.",
  CICLO_4_REVISAO_FINAL:      "Ciclo 4 — Rev Final",
  INCONSISTENTE_CICLO:        "Inconsistente",
  DESCONHECIDO:               "Desconhecido",
}
const CICLO_COLORS: Record<string, string> = {
  CICLO_1_PADRAO:           "#10B981",
  CICLO_2_REVISAO_CORRECAO: "#6366F1",
  CICLO_3_SEM_CORRECAO:     "#F59E0B",
  CICLO_4_REVISAO_FINAL:    "#14B8A6",
  INCONSISTENTE_CICLO:      "#EF4444",
  DESCONHECIDO:             "#94A3B8",
}

function DistribuicaoCiclos({ dados }: { dados: DistribuicaoCiclo[] }) {
  if (dados.length === 0) return <div className={styles.emptyState}>Sem dados de distribuição por ciclo.</div>
  return (
    <div className={styles.ciclosWrap}>
      {dados.map((c) => (
        <div key={c.ciclo} className={styles.cicloRow}>
          <div className={styles.cicloLabel}>
            {CICLO_LABELS[c.ciclo] ?? c.ciclo}
          </div>
          <div className={styles.cicloTrack}>
            <div
              className={styles.cicloFill}
              style={{
                width: `${Math.min(100, c.percentual)}%`,
                background: CICLO_COLORS[c.ciclo] ?? "#94A3B8",
              }}
            />
          </div>
          <span className={styles.cicloQtd}>{c.quantidade}</span>
          <span className={styles.cicloPct}>{c.percentual.toFixed(0)}%</span>
        </div>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// AlertasNotaTable — planilha de UTs concluídas sem nota
// ─────────────────────────────────────────────────────────────

const OCORRENCIA_LABEL: Record<string, string> = {
  NOTA_AUSENTE:  "Nota ausente",
  NOTA_INVALIDA: "Nota inválida",
}

function AlertasNotaTable({ alertas }: { alertas: AlertaNotaAusente[] }) {
  if (alertas.length === 0) return (
    <div className={styles.emptyStateOk}>✓ Nenhuma UT com problema de nota — qualidade em dia.</div>
  )
  return (
    <div className={styles.alertasWrap}>
      <div className={styles.alertasScrollArea}>
        <table className={styles.alertasTable}>
          <thead>
            <tr className={styles.alertasHead}>
              <th className={styles.alertaTh}>Bloco</th>
              <th className={styles.alertaTh}>Subfase</th>
              <th className={styles.alertaTh}>UT</th>
              <th className={styles.alertaTh}>Executor</th>
              <th className={styles.alertaTh}>Revisor</th>
              <th className={styles.alertaTh}>Ativ. Correção</th>
              <th className={styles.alertaTh}>Problema</th>
            </tr>
          </thead>
          <tbody>
            {alertas.map((a) => (
              <tr key={a.ut_id} className={styles.alertaRow}>
                <td className={styles.alertaTd}>
                  <span className={styles.alertaBlocoNome}>{a.bloco_nome}</span>
                  <span className={styles.alertaLote}>{a.lote_nome}</span>
                </td>
                <td className={styles.alertaTd}>{a.subfase_nome}</td>
                <td className={`${styles.alertaTd} ${styles.alertaId}`}>{a.ut_id}</td>
                <td className={styles.alertaTd}>{a.nome_executor ?? "—"}</td>
                <td className={styles.alertaTd}>{a.nome_revisor ?? "—"}</td>
                <td className={`${styles.alertaTd} ${styles.alertaId}`}>
                  {a.cor_atividade_id ?? "—"}
                </td>
                <td className={styles.alertaTd}>
                  <span className={
                    a.ocorrencia === "NOTA_AUSENTE"
                      ? styles.alertaBadgeAusente
                      : styles.alertaBadgeInvalida
                  }>
                    {OCORRENCIA_LABEL[a.ocorrencia] ?? a.ocorrencia}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
  const p = Math.min(100, Math.round(value ?? 0))
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
          <MesSeletor value={mesPizza} onChange={setMesPizza} className={styles.mesInput} />
        </div>
        {pizzaData ? (
          <GraficoPizza
            fatias={pizzaData.fatias}
            totalCapacidadeMin={pizzaData.total_capacidade_min}
            naoAlocadoMin={pizzaData.nao_alocado_min}
          />
        ) : (
          <div className={styles.emptyState}>Carregando…</div>
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
  const [blocoFiltro, setBlocoFiltro] = useState<number | null>(null)
  const [subfaseFiltro, setSubfaseFiltro] = useState<number | null>(null)

  const { data: kpiProjetos, isLoading: kpiLoading, error: kpiError } = useQuery({
    queryKey: ["kpiProjetos"],
    queryFn: getKpiProjetos,
    refetchInterval: 60_000,
  })

  const { data: dashboard } = useQuery({
    queryKey: ["kpiDashboard", blocoFiltro, subfaseFiltro],
    queryFn: () => getKpiDashboard(blocoFiltro ?? undefined, subfaseFiltro ?? undefined),
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

  // ── Timeline: contexto Ano ou Mês ─────────────────────────
  const [timelineContexto, setTimelineContexto] = useState<"ano" | "mes">("ano")
  const [timelineMes, setTimelineMes] = useState(() => format(new Date(), "yyyy-MM"))

  const { data: timelineDiaria } = useQuery({
    queryKey: ["timelineDiario", timelineMes, blocoFiltro],
    queryFn: () => getKpiTimelineDiario(timelineMes, blocoFiltro ?? undefined),
    enabled: timelineContexto === "mes",
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
        <div className={styles.headerActions}>
          {/* Seletor de bloco — filtra todos os widgets */}
          {(dashboard?.blocos_destaque ?? []).length > 0 && (
            <div className={styles.blocoSelector}>
              <select
                className={styles.blocoSelectorSelect}
                value={blocoFiltro ?? ""}
                onChange={(e) => setBlocoFiltro(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Todos os blocos</option>
                {dashboard!.blocos_destaque.map((b) => (
                  <option key={b.bloco_id} value={b.bloco_id}>{b.bloco_nome}</option>
                ))}
              </select>
              {blocoFiltro && (
                <button
                  type="button"
                  onClick={() => setBlocoFiltro(null)}
                  className={styles.blocoSelectorClear}
                >
                  ✕ Limpar
                </button>
              )}
            </div>
          )}
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
      </div>

      <div className={styles.statsRow}>
        <StatCard
          label="Blocos SAP"
          value={blocoFiltro && dashboard ? 1 : (dashboard?.blocos_sap_cadastrados ?? 0)}
          sub={blocoFiltro && dashboard ? (dashboard.bloco_filtro_nome ?? "bloco selecionado") : "blocos no snapshot"}
        />
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

      {/* ── Blocos em destaque ── */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Situação dos blocos
          {(dashboard?.blocos_destaque ?? []).length > 0 && (
            <span className={styles.sectionCount}>{dashboard!.blocos_destaque.length}</span>
          )}
        </h2>
        {(dashboard?.blocos_destaque ?? []).length === 0 ? (
          <div className={styles.emptyState}>
            {dashboard ? "Nenhum bloco ativo encontrado." : "Carregando dados dos blocos…"}
          </div>
        ) : (
          <div className={styles.blocoDestaqueGrid}>
            {dashboard!.blocos_destaque.map((b) => (
              <BlocoProgressoCard key={b.bloco_id} bloco={b} />
            ))}
          </div>
        )}
      </div>

      {/* ── Timeline acumulada ── */}
      {dashboard && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>
            Evolução acumulada de horas em produção — todos os operadores
          </h2>
          {/* Barra de contexto: Ano / Mês + seletor de mês */}
          <div className={styles.timelineContextBar} style={{ marginBottom: 10 }}>
            <button
              type="button"
              className={`${styles.timelineContextBtn} ${timelineContexto === "ano" ? styles.timelineContextBtnActive : ""}`}
              onClick={() => setTimelineContexto("ano")}
            >
              12 meses
            </button>
            <button
              type="button"
              className={`${styles.timelineContextBtn} ${timelineContexto === "mes" ? styles.timelineContextBtnActive : ""}`}
              onClick={() => setTimelineContexto("mes")}
            >
              Mês
            </button>
            {timelineContexto === "mes" && (
              <MesSeletor value={timelineMes} onChange={setTimelineMes} />
            )}
          </div>
          <div className={styles.chartCard}>
            {timelineContexto === "ano" ? (
              <GraficoMensal dados={dashboard.timeline_mensal ?? []} />
            ) : (
              <GraficoMensal
                dados={timelineDiaria ?? []}
                isDaily
              />
            )}
          </div>
        </div>
      )}

      {/* ── Ranking global de operadores (full-width) ── */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Ranking de produção
          {(dashboard?.ranking_operadores ?? []).length > 0 && (
            <span className={styles.sectionCount}>{dashboard!.ranking_operadores.length}</span>
          )}
          {dashboard?.subfase_filtro_nome && (
            <span className={styles.rankingContextBadge}>{dashboard.subfase_filtro_nome}</span>
          )}
        </h2>
        <RankingPanel
          operadores={dashboard?.ranking_operadores ?? []}
          subfases={dashboard?.subfases_disponiveis ?? []}
          subfaseFiltro={subfaseFiltro}
          blocoFiltro={blocoFiltro}
          onSubfaseFiltro={(sfId, bId) => {
            setSubfaseFiltro(sfId)
            if (bId !== undefined) setBlocoFiltro(bId)
          }}
        />
      </div>

      {/* ── Velocidade semanal (abaixo do ranking) ── */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Velocidade — últimas 8 semanas (UTs/sem)</h2>
        <div className={styles.chartCard}>
          <GraficoVelocidade dados={dashboard?.velocidade_semanal ?? []} />
        </div>
      </div>

      {/* ── Pizza + distribuição por ciclo ── */}
      <div className={styles.pizzaCiclosRow}>
        <div className={styles.pizzaCiclosColPizza}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>
              Distribuição de horas —{" "}
              {format(parseISO(`${mesPizza}-01`), "MMMM yyyy", { locale: ptBR })}
            </h2>
            <div className={styles.pizzaControls}>
              <MesSeletor value={mesPizza} onChange={setMesPizza} className={styles.mesInput} />
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
          {pizzaData ? (
            <GraficoPizza
              fatias={pizzaData.fatias}
              totalCapacidadeMin={pizzaData.total_capacidade_min}
              naoAlocadoMin={pizzaData.nao_alocado_min}
            />
          ) : (
            <div className={styles.emptyState}>Carregando…</div>
          )}
        </div>

        <div className={styles.pizzaCiclosColCiclos}>
          <h2 className={styles.sectionTitle} style={{ marginBottom: 12 }}>
            Distribuição por ciclo
          </h2>
          <div className={styles.chartCard}>
            <DistribuicaoCiclos dados={dashboard?.distribuicao_ciclos ?? []} />
          </div>
        </div>
      </div>

      {/* ── Alertas de qualidade ── */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <span className={styles.alertasTitulo}>
            {(dashboard?.alertas_nota ?? []).length > 0 ? "⚠ Alertas de nota" : "Alertas de nota"}
          </span>
          {(dashboard?.alertas_nota ?? []).length > 0 && (
            <span className={styles.sectionCountWarn}>{dashboard!.alertas_nota.length}</span>
          )}
        </h2>
        {(dashboard?.alertas_nota ?? []).length > 0 && (
          <p className={styles.alertasDesc}>
            UTs concluídas sem nota de qualidade ou com nota inválida.
            Verifique o revisor responsável e, se aplicável, a atividade de correção.
          </p>
        )}
        <AlertasNotaTable alertas={dashboard?.alertas_nota ?? []} />
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
