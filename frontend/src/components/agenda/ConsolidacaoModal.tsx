// ============================================================
// ConsolidacaoModal — Consolidação, desconsolidação, exportação e
//                     painel de inconsistências com navegação
// ============================================================
import { useState, useMemo } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import type { DateRange, InconsistenciaUsuario, Pendencia } from '@/types/agenda'
import {
  consolidarPeriodo,
  desconsolidarPeriodo,
  exportarInconsistenciasCSV,
} from '@/api/agenda'
import Modal from '@/components/ui/Modal'
import { Button, Badge } from '@/components/ui/Common'
import styles from './Agenda.module.css'

interface ConsolidacaoModalProps {
  open: boolean
  onClose: () => void
  dateRange: DateRange | null
  usuarioIds: number[]
}

// ── helpers ──────────────────────────────────────────────────

function agruparPorUsuario(pendencias: Pendencia[]): InconsistenciaUsuario[] {
  const mapa: Record<number, InconsistenciaUsuario> = {}
  for (const p of pendencias) {
    if (!mapa[p.usuario_id]) {
      mapa[p.usuario_id] = {
        usuario_id: p.usuario_id,
        usuario_nome: p.usuario_nome ?? `Usuário ${p.usuario_id}`,
        dias: [],
        total_minutos_nao_lancados: 0,
      }
    }
    mapa[p.usuario_id].dias.push({
      data: p.data,
      tipo: p.tipo,
      motivo: p.motivo,
      minutos_nao_lancados: p.minutos_nao_lancados,
    })
    mapa[p.usuario_id].total_minutos_nao_lancados += p.minutos_nao_lancados ?? 0
  }
  return Object.values(mapa).sort((a, b) => a.usuario_nome.localeCompare(b.usuario_nome))
}

function fmtHoras(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

const TIPO_LABEL: Record<string, string> = {
  SEM_LANCAMENTO: 'Sem lançamento',
  LANCAMENTO_INCOMPLETO: 'Incompleto',
  INDISPONIBILIDADE_NAO_TRATADA: 'Indisp. não tratada',
  INCONSISTENCIA_CALENDARIO: 'Inconsistência',
}

// ── componente ───────────────────────────────────────────────

export default function ConsolidacaoModal({
  open,
  onClose,
  dateRange,
  usuarioIds,
}: ConsolidacaoModalProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Estado de resultado
  const [pendencias, setPendencias] = useState<Pendencia[]>([])
  const [consolidado, setConsolidado] = useState(false)
  const [mensagem, setMensagem] = useState('')

  // Desconsolidação
  const [desconsolidado, setDesconsolidado] = useState(false)
  const [diasReabertos, setDiasReabertos] = useState(0)
  const [msgDesconsolidacao, setMsgDesconsolidacao] = useState('')

  // Hover no painel de inconsistências
  const [hovUsuario, setHovUsuario] = useState<number | null>(null)

  // CSV export
  const [exportando, setExportando] = useState(false)
  const [erroExport, setErroExport] = useState('')

  // ── mutations ─────────────────────────────────────────────

  const consolidarMutation = useMutation({
    mutationFn: consolidarPeriodo,
    onSuccess: (result) => {
      setPendencias(result.pendencias)
      setConsolidado(result.consolidado)
      setMensagem(result.mensagem)
      if (result.consolidado) {
        queryClient.invalidateQueries({ queryKey: ['agenda'] })
        queryClient.invalidateQueries({ queryKey: ['capacidade'] })
      }
    },
  })

  const desconsolidarMutation = useMutation({
    mutationFn: desconsolidarPeriodo,
    onSuccess: (result) => {
      setDesconsolidado(result.desconsolidado)
      setDiasReabertos(result.dias_reabertos)
      setMsgDesconsolidacao(result.mensagem)
      queryClient.invalidateQueries({ queryKey: ['agenda'] })
      queryClient.invalidateQueries({ queryKey: ['capacidade'] })
    },
  })

  // ── handlers ──────────────────────────────────────────────

  const handleConsolidar = (ignorarPendencias = false) => {
    if (!dateRange) return
    consolidarMutation.mutate({
      data_inicio: format(dateRange.start, 'yyyy-MM-dd'),
      data_fim: format(dateRange.end, 'yyyy-MM-dd'),
      usuarios_ids: usuarioIds.length > 0 ? usuarioIds : undefined,
      ignorar_pendencias: ignorarPendencias,
    })
  }

  const handleDesconsolidar = () => {
    if (!dateRange || usuarioIds.length === 0) return
    desconsolidarMutation.mutate({
      data_inicio: format(dateRange.start, 'yyyy-MM-dd'),
      data_fim: format(dateRange.end, 'yyyy-MM-dd'),
      usuarios_ids: usuarioIds,
    })
  }

  const handleExportarCSV = async () => {
    if (!dateRange || usuarioIds.length === 0) return
    setExportando(true)
    setErroExport('')
    try {
      await exportarInconsistenciasCSV(
        format(dateRange.start, 'yyyy-MM-dd'),
        format(dateRange.end, 'yyyy-MM-dd'),
        usuarioIds,
      )
    } catch {
      setErroExport('Não foi possível gerar o arquivo CSV.')
    } finally {
      setExportando(false)
    }
  }

  const handleNavigateToUsuario = (usuarioId: number) => {
    onClose()
    navigate(`/agenda-realizada?usuario_id=${usuarioId}`)
  }

  const handleClose = () => {
    setPendencias([])
    setConsolidado(false)
    setMensagem('')
    setDesconsolidado(false)
    setDiasReabertos(0)
    setMsgDesconsolidacao('')
    setHovUsuario(null)
    setErroExport('')
    onClose()
  }

  // ── dados derivados ───────────────────────────────────────

  const hasPendencias = pendencias.length > 0
  const inconsistencias = useMemo(() => agruparPorUsuario(pendencias), [pendencias])
  const usuarioHovered = inconsistencias.find((u) => u.usuario_id === hovUsuario)

  // ── render ────────────────────────────────────────────────

  return (
    <Modal open={open} onClose={handleClose} title="Gestão de Consolidação" size="lg">
      <div className={styles.consolidacaoContent}>

        {/* Período selecionado */}
        {dateRange && (
          <div className={styles.consolidacaoPeriodo}>
            <span className={styles.consolidacaoLabel}>Período:</span>
            <span className={styles.consolidacaoValue}>
              {format(dateRange.start, "d 'de' MMMM", { locale: ptBR })}
              {' — '}
              {format(dateRange.end, "d 'de' MMMM 'de' yyyy", { locale: ptBR })}
            </span>
          </div>
        )}

        {/* ── Desconsolidação bem-sucedida ── */}
        {desconsolidado && (
          <div className={styles.consolidacaoSuccess}>
            <div className={styles.successIcon}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 11l3 3 5-5" />
                <circle cx="12" cy="12" r="10" />
              </svg>
            </div>
            <h4>Período reaberto para edição</h4>
            <p>{msgDesconsolidacao} ({diasReabertos} dias desconsolidados)</p>
          </div>
        )}

        {/* ── Loading ── */}
        {(consolidarMutation.isPending || desconsolidarMutation.isPending) && (
          <div className={styles.consolidacaoLoading}>
            <div className={styles.spinner} />
            <p>{consolidarMutation.isPending ? 'Verificando pendências e consolidando...' : 'Desconsolidando período...'}</p>
          </div>
        )}

        {/* ── Estado inicial (sem resultados) ── */}
        {!consolidarMutation.isSuccess && !consolidarMutation.isPending
          && !desconsolidado && !desconsolidarMutation.isPending && (
          <div className={styles.consolidacaoInfo}>
            <div className={styles.infoIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4M12 8h.01" />
              </svg>
            </div>
            <h4>Gestão de consolidação</h4>
            <p>
              <strong>Consolidar</strong> bloqueia edições de operadores no período.
              O sistema verificará automaticamente pendências antes de consolidar.
            </p>
            <p>
              <strong>Desconsolidar</strong> reabre o período para edição, permitindo
              correções antes de uma nova consolidação.
            </p>
          </div>
        )}

        {/* ── Consolidação bem-sucedida ── */}
        {consolidado && !hasPendencias && (
          <div className={styles.consolidacaoSuccess}>
            <div className={styles.successIcon}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22,4 12,14.01 9,11.01" />
              </svg>
            </div>
            <h4>Período consolidado com sucesso!</h4>
            <p>{mensagem}</p>
          </div>
        )}

        {/* ── Consolidado com pendências ignoradas ── */}
        {consolidado && hasPendencias && (
          <div className={styles.consolidacaoWarn}>
            <div className={styles.warnIcon}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div>
              <h4>Consolidado com pendências</h4>
              <p>{mensagem}</p>
            </div>
          </div>
        )}

        {/* ── Painel de inconsistências (pendências) ── */}
        {hasPendencias && (
          <div className={styles.inconsistenciasWrap}>
            <div className={styles.inconsistenciasHeader}>
              <span className={styles.inconsistenciasTitle}>
                {consolidado ? '⚠ Pendências ignoradas' : '⚠ Pendências encontradas'}
              </span>
              <Badge variant="error" size="sm">{pendencias.length}</Badge>

              {/* Botão exportar CSV */}
              <button
                type="button"
                className={styles.exportCsvBtn}
                onClick={handleExportarCSV}
                disabled={exportando}
                title="Exportar CSV com usuário, data e horas não lançadas"
              >
                {exportando ? 'Gerando...' : '⬇ Exportar CSV'}
              </button>
            </div>

            {erroExport && (
              <div className={styles.consolidacaoError}><p>{erroExport}</p></div>
            )}

            {/* Lista de usuários com hover mostrando dias */}
            <div className={styles.inconsistenciasCols}>
              {/* Coluna esquerda: lista de usuários */}
              <div className={styles.inconsistenciasLista}>
                {inconsistencias.map((u) => (
                  <div
                    key={u.usuario_id}
                    className={`${styles.inconsistenciaUsuarioRow} ${hovUsuario === u.usuario_id ? styles.inconsistenciaUsuarioHov : ''}`}
                    onMouseEnter={() => setHovUsuario(u.usuario_id)}
                    onMouseLeave={() => setHovUsuario(null)}
                  >
                    <span className={styles.inconsistenciaAvatar}>
                      {u.usuario_nome.charAt(0).toUpperCase()}
                    </span>
                    <span className={styles.inconsistenciaNome}>{u.usuario_nome}</span>
                    <span className={styles.inconsistenciaBadges}>
                      <Badge variant="error" size="sm">{u.dias.length} dias</Badge>
                      {u.total_minutos_nao_lancados > 0 && (
                        <Badge variant="warning" size="sm">{fmtHoras(u.total_minutos_nao_lancados)}</Badge>
                      )}
                    </span>
                    {/* Botão navegar para agenda */}
                    <button
                      type="button"
                      className={styles.inconsistenciaNavBtn}
                      onClick={() => handleNavigateToUsuario(u.usuario_id)}
                      title="Abrir agenda deste usuário"
                    >
                      →
                    </button>
                  </div>
                ))}
              </div>

              {/* Coluna direita: dias do usuário hovered */}
              <div className={styles.inconsistenciaDetalhe}>
                {usuarioHovered ? (
                  <>
                    <div className={styles.inconsistenciaDetalheHeader}>
                      {usuarioHovered.usuario_nome} — dias pendentes
                    </div>
                    <div className={styles.inconsistenciaDetalheScroll}>
                      {usuarioHovered.dias
                        .slice()
                        .sort((a, b) => a.data.localeCompare(b.data))
                        .map((dia, i) => (
                          <div key={i} className={styles.inconsistenciaDiaRow}>
                            <span className={styles.inconsistenciaDiaData}>
                              {format(new Date(dia.data + 'T12:00:00'), 'EEE dd/MM', { locale: ptBR })}
                            </span>
                            <span className={styles.inconsistenciaDiaTipo}>
                              {TIPO_LABEL[dia.tipo] ?? dia.tipo}
                            </span>
                            {dia.minutos_nao_lancados != null && dia.minutos_nao_lancados > 0 && (
                              <span className={styles.inconsistenciaDiaHoras}>
                                {fmtHoras(dia.minutos_nao_lancados)}
                              </span>
                            )}
                          </div>
                        ))}
                    </div>
                  </>
                ) : (
                  <div className={styles.inconsistenciaDetalheVazio}>
                    Passe o mouse sobre um usuário para ver os dias pendentes
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Erros ── */}
        {(consolidarMutation.isError || desconsolidarMutation.isError) && (
          <div className={styles.consolidacaoError}>
            <p>
              Erro: {((consolidarMutation.error || desconsolidarMutation.error) as Error)?.message}
            </p>
          </div>
        )}
      </div>

      {/* ── Rodapé de ações ── */}
      <Modal.Footer>
        {/* Sempre disponível: exportar CSV se houver pendências ou resultado */}
        {(consolidado || hasPendencias) ? (
          <>
            {/* Exportar CSV sempre visível quando há dados */}
            {hasPendencias && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleExportarCSV}
                loading={exportando}
              >
                Exportar CSV
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={handleClose}>Fechar</Button>
          </>
        ) : desconsolidado ? (
          <Button variant="primary" size="sm" onClick={handleClose}>Fechar</Button>
        ) : (
          <>
            <Button variant="ghost" size="sm" onClick={handleClose} disabled={consolidarMutation.isPending || desconsolidarMutation.isPending}>
              Cancelar
            </Button>

            {/* Desconsolidar — somente admin, sempre disponível */}
            {usuarioIds.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDesconsolidar}
                loading={desconsolidarMutation.isPending}
                disabled={consolidarMutation.isPending}
              >
                Desconsolidar período
              </Button>
            )}

            {hasPendencias && (
              <Button
                variant="danger"
                size="sm"
                onClick={() => handleConsolidar(true)}
                loading={consolidarMutation.isPending}
                disabled={desconsolidarMutation.isPending}
              >
                Ignorar e consolidar
              </Button>
            )}

            <Button
              variant="primary"
              size="sm"
              onClick={() => handleConsolidar(false)}
              loading={consolidarMutation.isPending}
              disabled={desconsolidarMutation.isPending}
            >
              {hasPendencias ? 'Verificar novamente' : 'Consolidar período'}
            </Button>
          </>
        )}
      </Modal.Footer>
    </Modal>
  )
}
