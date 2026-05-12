// ============================================================
// Operadores — listagem de operadores com detalhe de pontos
// e lançamentos de agenda (visão do administrador)
// ============================================================
import {
  getDashboardUsuario,
  getAgendaUsuario,
  getUsuarios,
  getKpiDashboard,
} from '@/api/endpoints'
import type {
  BlocoDetalheUsuario,
  MeuDashboardResponse,
  PontosSubfaseResposta,
  RankingOperador,
  UsuarioResumo,
} from '@/types'
import type { ApontamentoResumo } from '@/types/agenda'
import { useQuery } from '@tanstack/react-query'
import {
  endOfMonth,
  format,
  parse,
  parseISO,
  startOfMonth,
  subMonths,
} from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useMemo, useState } from 'react'
import styles from './Operadores.module.css'

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function fmtPts(pts: number): string {
  return pts >= 1000
    ? `${(pts / 1000).toFixed(1)}k`
    : pts.toFixed(pts % 1 === 0 ? 0 : 1)
}

function fmtMin(minutos: number): string {
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

function gerarMesesOpcoes(n = 24): { value: string; label: string }[] {
  const hoje = startOfMonth(new Date())
  return Array.from({ length: n }, (_, i) => {
    const d = subMonths(hoje, i)
    return {
      value: format(d, 'yyyy-MM'),
      label: format(d, 'MMMM yyyy', { locale: ptBR }),
    }
  })
}

const MESES = gerarMesesOpcoes(36)

// ─────────────────────────────────────────────────────────────
// SubfaseBar — barra de pontos de uma subfase por papel
// ─────────────────────────────────────────────────────────────

function SubfaseItem({
  sf,
  total,
  barClass,
}: {
  sf: PontosSubfaseResposta
  total: number
  barClass: string
}) {
  const pct = Math.round((sf.pontos / (total || 1)) * 100)
  return (
    <div className={styles.subfase}>
      <span className={styles.subfaseNome}>{sf.subfase_nome}</span>
      <span className={styles.subfasePts}>{fmtPts(sf.pontos)}</span>
      <span className={styles.subfaseBar}>
        <span className={`${styles.subfaseBarFill} ${barClass}`} style={{ width: `${pct}%` }} />
      </span>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// BlocoDetalhe — bloco com subfases por papel
// ─────────────────────────────────────────────────────────────

function BlocoDetalhe({ bloco }: { bloco: BlocoDetalheUsuario }) {
  const tot = bloco.pontos_usuario_bloco || 1
  return (
    <div className={styles.bloco}>
      <div className={styles.blocoHeader}>
        <span className={styles.blocoNome}>{bloco.bloco_nome}</span>
        <span className={styles.blocoProjeto}>{bloco.projeto_nome}</span>
        <span className={styles.blocoPts}>{fmtPts(bloco.pontos_usuario_bloco)} pts</span>
      </div>
      {bloco.como_executor.length > 0 && (
        <div className={styles.papel}>
          <span className={styles.papelLabel}>Execução</span>
          {bloco.como_executor.map((sf) => (
            <SubfaseItem key={sf.subfase_id} sf={sf} total={tot} barClass={styles.barExec} />
          ))}
        </div>
      )}
      {bloco.como_revisor.length > 0 && (
        <div className={styles.papel}>
          <span className={styles.papelLabel}>Revisão</span>
          {bloco.como_revisor.map((sf) => (
            <SubfaseItem key={sf.subfase_id} sf={sf} total={tot} barClass={styles.barRev} />
          ))}
        </div>
      )}
      {bloco.como_corretor.length > 0 && (
        <div className={styles.papel}>
          <span className={styles.papelLabel}>Correção</span>
          {bloco.como_corretor.map((sf) => (
            <SubfaseItem key={sf.subfase_id} sf={sf} total={tot} barClass={styles.barCor} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// AbaLancamentos — tabela de lançamentos do mês
// ─────────────────────────────────────────────────────────────

function AbaLancamentos({ usuarioId }: { usuarioId: number }) {
  const [mesSel, setMesSel] = useState(() => format(new Date(), 'yyyy-MM'))
  const dataInicio = `${mesSel}-01`
  const dataFim = format(endOfMonth(parse(mesSel, 'yyyy-MM', new Date())), 'yyyy-MM-dd')

  const { data: agenda, isLoading } = useQuery({
    queryKey: ['agendaUsuario', usuarioId, mesSel],
    queryFn: () => getAgendaUsuario(usuarioId, dataInicio, dataFim),
    staleTime: 60_000,
  })

  const lancamentos = useMemo<(ApontamentoResumo & { data: string })[]>(() => {
    if (!agenda) return []
    return agenda.dias
      .filter((d) => d.lancamentos.length > 0)
      .flatMap((d) => d.lancamentos.map((l) => ({ ...l, data: d.data })))
  }, [agenda])

  return (
    <div className={styles.detalheCorpo}>
      <div className={styles.lancMesRow}>
        <span className={styles.lancMesLabel}>Mês:</span>
        <select
          className={styles.lancMesPicker}
          value={mesSel}
          onChange={(e) => setMesSel(e.target.value)}
        >
          {MESES.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      {isLoading && <div className={styles.loading}>Carregando lançamentos…</div>}

      {!isLoading && lancamentos.length === 0 && (
        <div className={styles.emptyState}>Nenhum lançamento neste mês.</div>
      )}

      {!isLoading && lancamentos.length > 0 && (
        <table className={styles.lancTable}>
          <thead>
            <tr>
              <th>Data</th>
              <th>Tipo / Bloco</th>
              <th>Min</th>
              <th>Faixa</th>
            </tr>
          </thead>
          <tbody>
            {lancamentos.map((l) => (
              <tr key={l.id} className={styles.lancRow}>
                <td className={styles.lancData}>{format(parseISO(l.data), 'dd/MM')}</td>
                <td>
                  <span
                    className={styles.lancTipo}
                    style={{ borderLeftColor: l.tipo_atividade_cor }}
                  >
                    {l.tipo_atividade_nome}
                    {l.bloco_nome && (
                      <span className={styles.lancBloco}> · {l.bloco_nome}</span>
                    )}
                  </span>
                  {l.descricao && (
                    <span className={styles.lancDesc}>{l.descricao}</span>
                  )}
                </td>
                <td className={styles.lancMin}>{l.minutos}m</td>
                <td>
                  <span className={l.faixa === 'EXTRA' ? styles.faixaExtra : styles.faixaNormal}>
                    {l.faixa === 'EXTRA' ? 'Extra' : 'Normal'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// AbaPontos — pontos por bloco/subfase/papel
// ─────────────────────────────────────────────────────────────

function AbaPontos({ dados }: { dados: MeuDashboardResponse | undefined }) {
  if (!dados) return <div className={styles.loading}>Carregando pontos…</div>
  if (dados.blocos.length === 0) {
    return <div className={styles.emptyState}>Nenhum ponto registrado para este operador.</div>
  }
  return (
    <div className={styles.detalheCorpo}>
      {dados.blocos.map((bloco) => (
        <BlocoDetalhe key={bloco.bloco_id} bloco={bloco} />
      ))}
      <div className={styles.horasRow}>
        <div className={styles.horasCard}>
          <span className={styles.horasLabel}>Previstas (produção)</span>
          <span className={styles.horasVal}>{fmtMin(dados.horas_previstas_producao_min)}</span>
        </div>
        <div className={styles.horasCard}>
          <span className={styles.horasLabel}>Lançadas (produção)</span>
          <span className={styles.horasVal}>{fmtMin(dados.horas_lancadas_producao_min)}</span>
        </div>
        <div className={styles.horasCard}>
          <span className={styles.horasLabel}>Lançadas (externas)</span>
          <span className={styles.horasVal}>{fmtMin(dados.horas_lancadas_externas_min)}</span>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// PainelDetalhe — header + abas + conteúdo
// ─────────────────────────────────────────────────────────────

function PainelDetalhe({
  usuarioId,
  nome,
  rankingInfo,
}: {
  usuarioId: number
  nome: string
  rankingInfo: RankingOperador | undefined
}) {
  const [aba, setAba] = useState<'pontos' | 'lancamentos'>('pontos')

  const { data: dashboard } = useQuery({
    queryKey: ['dashboardUsuario', usuarioId],
    queryFn: () => getDashboardUsuario(usuarioId),
    staleTime: 30_000,
  })

  return (
    <div className={styles.detalheCard}>
      {/* Cabeçalho */}
      <div className={styles.detalheHeader}>
        <h2 className={styles.detalheNome}>{nome}</h2>
        <div className={styles.detalheMeta}>
          <span className={styles.detalheMetaItem}>
            Total: <strong>{fmtPts(rankingInfo?.pontos_total ?? dashboard?.pontos_usuario_geral ?? 0)} pts</strong>
          </span>
          {rankingInfo && (
            <>
              <span className={styles.detalheMetaItem}>
                Exec: <strong>{fmtPts(rankingInfo.pontos_executor)}</strong>
              </span>
              <span className={styles.detalheMetaItem}>
                Rev: <strong>{fmtPts(rankingInfo.pontos_revisor)}</strong>
              </span>
              {rankingInfo.pontos_corretor > 0 && (
                <span className={styles.detalheMetaItem}>
                  Cor: <strong>{fmtPts(rankingInfo.pontos_corretor)}</strong>
                </span>
              )}
              <span className={styles.detalheMetaItem}>
                UTs: <strong>{rankingInfo.uts_executadas} exec · {rankingInfo.uts_revisadas} rev</strong>
              </span>
            </>
          )}
        </div>
      </div>

      {/* Abas */}
      <div className={styles.abas}>
        <button
          type="button"
          className={`${styles.aba} ${aba === 'pontos' ? styles.abaAtiva : ''}`}
          onClick={() => setAba('pontos')}
        >
          Pontos por bloco
        </button>
        <button
          type="button"
          className={`${styles.aba} ${aba === 'lancamentos' ? styles.abaAtiva : ''}`}
          onClick={() => setAba('lancamentos')}
        >
          Lançamentos
        </button>
      </div>

      {/* Conteúdo */}
      {aba === 'pontos' && <AbaPontos dados={dashboard} />}
      {aba === 'lancamentos' && <AbaLancamentos usuarioId={usuarioId} />}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Linha da lista de operadores
// ─────────────────────────────────────────────────────────────

function OperadorLinha({
  usuario,
  rankingInfo,
  ativo,
  onClick,
}: {
  usuario: UsuarioResumo
  rankingInfo: RankingOperador | undefined
  ativo: boolean
  onClick: () => void
}) {
  const nome = usuario.nome_guerra ?? usuario.nome
  return (
    <div
      className={`${styles.operadorRow} ${ativo ? styles.operadorRowAtivo : ''}`}
      onClick={onClick}
      title={`Ver detalhe de ${nome}`}
    >
      <span className={styles.operadorPosicao}>{rankingInfo?.posicao ?? '—'}</span>
      <span className={styles.operadorNome}>{nome}</span>
      <span className={styles.operadorPts}>{rankingInfo ? fmtPts(rankingInfo.pontos_executor) : '—'}</span>
      <span className={styles.operadorPts}>{rankingInfo ? fmtPts(rankingInfo.pontos_revisor) : '—'}</span>
      <span className={styles.operadorPts}>{rankingInfo ? fmtPts(rankingInfo.pontos_corretor) : '—'}</span>
      <span className={styles.operadorTotal}>{rankingInfo ? fmtPts(rankingInfo.pontos_total) : '—'}</span>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Página principal
// ─────────────────────────────────────────────────────────────

export default function Operadores() {
  const [busca, setBusca] = useState('')
  const [selecionado, setSelecionado] = useState<UsuarioResumo | null>(null)

  const { data: usuarios = [] } = useQuery({
    queryKey: ['usuarios'],
    queryFn: getUsuarios,
    staleTime: 60_000,
  })

  const { data: kpi } = useQuery({
    queryKey: ['kpiDashboard', null, null],
    queryFn: () => getKpiDashboard(),
    staleTime: 60_000,
    refetchInterval: 120_000,
  })

  const rankingMap = useMemo<Map<number, RankingOperador>>(() => {
    const m = new Map<number, RankingOperador>()
    for (const op of kpi?.ranking_operadores ?? []) {
      m.set(op.usuario_id, op)
    }
    return m
  }, [kpi?.ranking_operadores])

  const usuariosFiltrados = useMemo(() => {
    const q = busca.trim().toLowerCase()
    const lista = [...usuarios].sort((a, b) => {
      const pa = rankingMap.get(a.id)?.posicao ?? 9999
      const pb = rankingMap.get(b.id)?.posicao ?? 9999
      return pa - pb
    })
    if (!q) return lista
    return lista.filter((u) =>
      (u.nome_guerra ?? u.nome).toLowerCase().includes(q) ||
      u.nome.toLowerCase().includes(q)
    )
  }, [usuarios, busca, rankingMap])

  const selecionadoRanking = selecionado ? rankingMap.get(selecionado.id) : undefined

  return (
    <div className={styles.root}>
      {/* Cabeçalho */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>
            Operadores
            {usuarios.length > 0 && (
              <span className={styles.count}>{usuarios.length}</span>
            )}
          </h1>
          <p className={styles.pageSubtitle}>
            Pontuação por papel, produção e lançamentos de cada operador
          </p>
        </div>
        <div className={styles.searchBox}>
          <span className={styles.searchIcon}>⌕</span>
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Buscar operador…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>
      </div>

      {/* Layout split */}
      <div className={styles.layout}>
        {/* ── Lista ── */}
        <div className={styles.listaCard}>
          <div className={styles.listaHeader}>
            <span className={styles.listaHeaderCell}>#</span>
            <span className={styles.listaHeaderCell} style={{ textAlign: 'left' }}>Nome</span>
            <span className={styles.listaHeaderCell}>Exec</span>
            <span className={styles.listaHeaderCell}>Rev</span>
            <span className={styles.listaHeaderCell}>Cor</span>
            <span className={styles.listaHeaderCell}>Total</span>
          </div>
          <div className={styles.listaScroll}>
            {usuariosFiltrados.length === 0 && (
              <span className={styles.semRankingRow}>Nenhum operador encontrado.</span>
            )}
            {usuariosFiltrados.map((u) => (
              <OperadorLinha
                key={u.id}
                usuario={u}
                rankingInfo={rankingMap.get(u.id)}
                ativo={selecionado?.id === u.id}
                onClick={() => setSelecionado(u.id === selecionado?.id ? null : u)}
              />
            ))}
          </div>
        </div>

        {/* ── Painel de detalhe ── */}
        {selecionado ? (
          <PainelDetalhe
            key={selecionado.id}
            usuarioId={selecionado.id}
            nome={selecionado.nome_guerra ?? selecionado.nome}
            rankingInfo={selecionadoRanking}
          />
        ) : (
          <div className={styles.detalheCard}>
            <div className={styles.detalheVazio}>
              <span className={styles.detalheVazioIcone}>◉</span>
              <span className={styles.detalheVazioTexto}>
                Selecione um operador na lista<br />para ver pontos e lançamentos
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
