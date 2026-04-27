// ============================================================
// LancamentoLoteModal — Lançamento em lote para múltiplos dias
// Suporta: operador (1 usuário, N dias) e admin (N usuários × N dias)
// ============================================================
import { useEffect, useMemo, useState } from 'react'
import { format, isWeekend } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Modal from '@/components/ui/Modal'
import { Button } from '@/components/ui/Common'
import { criarLancamentoLote, criarLancamentoAdminLote } from '@/api/agenda'
import type {
  CodigoAtividade,
  FaixaMinuto,
  TipoAtividade,
  UsuarioResumo,
} from '@/types/agenda'
import styles from './Agenda.module.css'

// ── helpers ──────────────────────────────────────────────────

type UnidadeTempo = 'HORAS' | 'MINUTOS'

function fmtMin(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h > 0 && m > 0) return `${h}h ${m}min`
  if (h > 0) return `${h}h`
  return `${m}min`
}

function obterNome(u: UsuarioResumo): string {
  return u.nome_guerra?.trim() || u.nome
}

// ── props ─────────────────────────────────────────────────────

interface LancamentoLoteModalProps {
  open: boolean
  onClose: () => void
  /** Dias selecionados pelo usuário (todos os dias do calendário, filtrados aqui) */
  selectedDates: Date[]
  /** Lista de 'yyyy-MM-dd' feriados para exclusão */
  feriados: string[]
  /** ID do usuário logado (operador) */
  usuarioIdAtual?: number
  /** Lista completa de usuários (admin) */
  usuariosDisponiveis: UsuarioResumo[]
  /** Tipos de atividade disponíveis */
  tiposAtividade: TipoAtividade[]
  isAdmin: boolean
  onSuccess: () => void
}

// ── componente ────────────────────────────────────────────────

export default function LancamentoLoteModal({
  open,
  onClose,
  selectedDates,
  feriados,
  usuariosDisponiveis,
  tiposAtividade,
  isAdmin,
  onSuccess,
}: LancamentoLoteModalProps) {
  const queryClient = useQueryClient()

  // ── form state ───────────────────────────────────────────
  const [selectedUsuarioIds, setSelectedUsuarioIds] = useState<number[]>([])
  const [tipoAtividadeId, setTipoAtividadeId] = useState<string>('')
  const [faixa, setFaixa] = useState<FaixaMinuto>('NORMAL')
  const [unidadeTempo, setUnidadeTempo] = useState<UnidadeTempo>('HORAS')
  const [quantidade, setQuantidade] = useState('1')
  const [descricao, setDescricao] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [resultado, setResultado] = useState<{ criados: number; erros: string[] } | null>(null)

  // Inicializar seleção de usuários (admin = todos por padrão)
  useEffect(() => {
    if (!open) return
    setErro(null)
    setResultado(null)
    if (tiposAtividade.length > 0 && !tipoAtividadeId) {
      setTipoAtividadeId(String(tiposAtividade[0].id))
    }
    if (isAdmin && selectedUsuarioIds.length === 0 && usuariosDisponiveis.length > 0) {
      // Admin começa com nenhum selecionado (deve escolher)
      setSelectedUsuarioIds([])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // ── dados derivados ──────────────────────────────────────
  const feriadosSet = useMemo(() => new Set(feriados), [feriados])

  /** Apenas dias úteis (sem fins de semana e feriados) */
  const diasUteis = useMemo(() =>
    selectedDates.filter((d) => !isWeekend(d) && !feriadosSet.has(format(d, 'yyyy-MM-dd'))),
    [selectedDates, feriadosSet]
  )

  const minutosTotais = useMemo(() => {
    const v = Number(quantidade)
    if (!Number.isFinite(v) || v <= 0) return 0
    return unidadeTempo === 'HORAS' ? Math.round(v * 60) : Math.round(v)
  }, [quantidade, unidadeTempo])

  const tipoSelecionado = useMemo(
    () => tiposAtividade.find((t) => String(t.id) === tipoAtividadeId) ?? null,
    [tiposAtividade, tipoAtividadeId],
  )

  // bloco_id vem diretamente do tipo atividade (como em AgendaRealizada)
  const blocoIdParaApi = tipoSelecionado?.origem === 'BLOCO' ? (tipoSelecionado.bloco_id ?? null) : null

  const totalLancamentos = isAdmin
    ? diasUteis.length * selectedUsuarioIds.length
    : diasUteis.length

  // ── toggle usuário ───────────────────────────────────────
  function toggleUsuario(id: number) {
    setSelectedUsuarioIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  function toggleTodos() {
    if (selectedUsuarioIds.length === usuariosDisponiveis.length) {
      setSelectedUsuarioIds([])
    } else {
      setSelectedUsuarioIds(usuariosDisponiveis.map((u) => u.id))
    }
  }

  // ── mutation ─────────────────────────────────────────────
  const loteMutation = useMutation({
    mutationFn: async () => {
      const datas = diasUteis.map((d) => format(d, 'yyyy-MM-dd'))
      const tipo = tipoSelecionado!.codigo as CodigoAtividade

      if (isAdmin) {
        return criarLancamentoAdminLote({
          datas,
          bloco_id: blocoIdParaApi,
          tipo_atividade: tipo,
          faixa,
          minutos: minutosTotais,
          descricao: descricao.trim() || null,
          usuario_ids: selectedUsuarioIds,
        })
      } else {
        return criarLancamentoLote({
          datas,
          bloco_id: blocoIdParaApi,
          tipo_atividade: tipo,
          faixa,
          minutos: minutosTotais,
          descricao: descricao.trim() || null,
        })
      }
    },
    onSuccess: (res) => {
      setResultado(res)
      queryClient.invalidateQueries({ queryKey: ['agenda'] })
      queryClient.invalidateQueries({ queryKey: ['capacidade'] })
      onSuccess()
    },
    onError: (err: Error) => {
      setErro(err.message ?? 'Erro ao criar lançamentos.')
    },
  })

  // ── validar ──────────────────────────────────────────────
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErro(null)
    if (diasUteis.length === 0) { setErro('Nenhum dia útil selecionado.'); return }
    if (!tipoSelecionado) { setErro('Selecione o tipo de atividade.'); return }
    if (minutosTotais <= 0) { setErro('Informe uma duração válida.'); return }
    if (isAdmin && selectedUsuarioIds.length === 0) { setErro('Selecione ao menos um usuário.'); return }
    loteMutation.mutate()
  }

  function handleClose() {
    setErro(null)
    setResultado(null)
    loteMutation.reset()
    onClose()
  }

  // ── render ────────────────────────────────────────────────
  return (
    <Modal open={open} onClose={handleClose} title="Lançamento em lote" size="lg">
      {resultado ? (
        /* ── Resultado ── */
        <div className={styles.consolidacaoSuccess}>
          <div className={styles.successIcon}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22,4 12,14.01 9,11.01" />
            </svg>
          </div>
          <h4>{resultado.criados} lançamento{resultado.criados !== 1 ? 's' : ''} criado{resultado.criados !== 1 ? 's' : ''}!</h4>
          {resultado.erros.length > 0 && (
            <div className={styles.consolidacaoWarn} style={{ marginTop: 12, textAlign: 'left' }}>
              <div className={styles.warnIcon}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <div>
                <h4>{resultado.erros.length} erro{resultado.erros.length !== 1 ? 's' : ''}</h4>
                <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', fontSize: 12, color: 'var(--tx-secondary)' }}>
                  {resultado.erros.slice(0, 5).map((e, i) => <li key={i}>{e}</li>)}
                  {resultado.erros.length > 5 && <li>...e mais {resultado.erros.length - 5}</li>}
                </ul>
              </div>
            </div>
          )}
          <Modal.Footer>
            <Button variant="primary" size="sm" onClick={handleClose}>Fechar</Button>
          </Modal.Footer>
        </div>
      ) : (
        /* ── Formulário ── */
        <form className={styles.modalForm} onSubmit={handleSubmit}>

          {/* Resumo do período selecionado */}
          <div className={styles.modalSection}>
            <div className={styles.selectionInfoGrid}>
              <div className={styles.selectionInfoCard}>
                <span className={styles.selectionInfoLabel}>Dias úteis</span>
                <strong>{diasUteis.length}</strong>
              </div>
              {isAdmin && (
                <div className={styles.selectionInfoCard}>
                  <span className={styles.selectionInfoLabel}>Usuários</span>
                  <strong>{selectedUsuarioIds.length}</strong>
                </div>
              )}
              <div className={styles.selectionInfoCard}>
                <span className={styles.selectionInfoLabel}>Total</span>
                <strong>{totalLancamentos} lançamentos</strong>
              </div>
              <div className={styles.selectionInfoCard}>
                <span className={styles.selectionInfoLabel}>Carga/dia</span>
                <strong>{minutosTotais > 0 ? fmtMin(minutosTotais) : '—'}</strong>
              </div>
            </div>

            {/* Preview dos dias selecionados */}
            <div className={styles.loteDatasList}>
              {diasUteis.slice(0, 12).map((d) => (
                <span key={format(d, 'yyyy-MM-dd')} className={styles.loteDiaChip}>
                  {format(d, 'EEE dd/MM', { locale: ptBR })}
                </span>
              ))}
              {diasUteis.length > 12 && (
                <span className={styles.loteDiaChip} style={{ opacity: 0.6 }}>
                  +{diasUteis.length - 12} dias
                </span>
              )}
            </div>
          </div>

          {/* Seleção de usuários (admin) */}
          {isAdmin && (
            <div className={styles.modalSection}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <h3 className={styles.modalSectionTitle} style={{ margin: 0 }}>Usuários</h3>
                <button type="button" className={styles.exportCsvBtn} onClick={toggleTodos}>
                  {selectedUsuarioIds.length === usuariosDisponiveis.length ? 'Desmarcar todos' : 'Selecionar todos'}
                </button>
              </div>
              <div className={styles.loteUsuariosList}>
                {usuariosDisponiveis.map((u) => {
                  const ativo = selectedUsuarioIds.includes(u.id)
                  return (
                    <label key={u.id} className={`${styles.loteUsuarioRow} ${ativo ? styles.loteUsuarioAtivo : ''}`}>
                      <input
                        type="checkbox"
                        checked={ativo}
                        onChange={() => toggleUsuario(u.id)}
                        style={{ display: 'none' }}
                      />
                      <span className={styles.inconsistenciaAvatar}>{obterNome(u).charAt(0).toUpperCase()}</span>
                      <span className={styles.inconsistenciaNome}>{obterNome(u)}</span>
                      {ativo && (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" strokeWidth="2.5">
                          <polyline points="20,6 9,17 4,12" />
                        </svg>
                      )}
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {/* Campos do lançamento */}
          <div className={styles.formGrid}>
            <label className={styles.fieldGroup}>
              <span className={styles.fieldLabel}>Tipo de atividade</span>
              <select
                className={styles.fieldControl}
                value={tipoAtividadeId}
                onChange={(e) => setTipoAtividadeId(e.target.value)}
              >
                <option value="" disabled>Selecione...</option>
                {tiposAtividade.map((t) => (
                  <option key={t.id} value={String(t.id)}>{t.nome}</option>
                ))}
              </select>
            </label>

            <label className={styles.fieldGroup}>
              <span className={styles.fieldLabel}>Faixa</span>
              <select
                className={styles.fieldControl}
                value={faixa}
                onChange={(e) => setFaixa(e.target.value as FaixaMinuto)}
              >
                <option value="NORMAL">Normal</option>
                <option value="EXTRA">Hora extra</option>
              </select>
            </label>

            <label className={styles.fieldGroup}>
              <span className={styles.fieldLabel}>Unidade</span>
              <select
                className={styles.fieldControl}
                value={unidadeTempo}
                onChange={(e) => setUnidadeTempo(e.target.value as UnidadeTempo)}
              >
                <option value="HORAS">Horas</option>
                <option value="MINUTOS">Minutos</option>
              </select>
            </label>

            <label className={styles.fieldGroup}>
              <span className={styles.fieldLabel}>Quantidade</span>
              <input
                className={styles.fieldControl}
                type="number"
                min="1"
                step={unidadeTempo === 'HORAS' ? '0.5' : '15'}
                value={quantidade}
                onChange={(e) => setQuantidade(e.target.value)}
              />
            </label>
          </div>

          {/* Atalhos rápidos de minutos */}
          <div className={styles.quickMinutes}>
            {[30, 60, 90, 120, 180, 240, 360].map((m) => (
              <button
                key={m}
                type="button"
                className={`${styles.quickBtn} ${minutosTotais === m ? styles.quickBtnActive : ''}`}
                onClick={() => { setUnidadeTempo('MINUTOS'); setQuantidade(String(m)) }}
              >
                {m >= 60 ? `${m / 60}h` : `${m}min`}
              </button>
            ))}
          </div>

          <label className={styles.fieldGroup}>
            <span className={styles.fieldLabel}>Descrição (opcional)</span>
            <textarea
              className={`${styles.fieldControl} ${styles.textareaControl}`}
              rows={3}
              placeholder="Detalhes adicionais..."
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
            />
          </label>

          {tipoSelecionado && minutosTotais > 0 && (
            <div className={styles.planejamentoPreview}>
              <span className={styles.planejamentoPreviewTitle}>Prévia</span>
              <p>
                <strong>{tipoSelecionado.nome}</strong> · {faixa === 'NORMAL' ? 'Normal' : 'Hora extra'} · {fmtMin(minutosTotais)}/dia
                {' → '}<strong>{totalLancamentos} lançamento{totalLancamentos !== 1 ? 's' : ''}</strong>
                {isAdmin && selectedUsuarioIds.length > 0 && ` para ${selectedUsuarioIds.length} usuário${selectedUsuarioIds.length !== 1 ? 's' : ''}`}
              </p>
            </div>
          )}

          {erro && <div className={styles.formError}>{erro}</div>}

          <Modal.Footer>
            <Button type="button" variant="ghost" size="sm" onClick={handleClose} disabled={loteMutation.isPending}>
              Cancelar
            </Button>
            <Button type="submit" variant="primary" size="sm" loading={loteMutation.isPending}>
              Criar {totalLancamentos > 0 ? totalLancamentos : ''} lançamento{totalLancamentos !== 1 ? 's' : ''}
            </Button>
          </Modal.Footer>
        </form>
      )}
    </Modal>
  )
}
