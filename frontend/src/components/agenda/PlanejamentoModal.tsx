import { useEffect, useMemo, useState } from 'react'
import { eachDayOfInterval, format } from 'date-fns'
import Modal from '@/components/ui/Modal'
import { Button, Badge } from '@/components/ui/Common'
import { criarPlanejamento } from '@/api/agenda'
import type { DateRange, TipoAtividade, UsuarioResumo } from '@/types/agenda'
import styles from './Agenda.module.css'

interface PlanejamentoModalProps {
  open: boolean
  onClose: () => void
  periodoSelecionado: DateRange | null
  usuariosSelecionados: UsuarioResumo[]
  tiposAtividade: TipoAtividade[]
  onSuccess: () => Promise<void> | void
}

type TipoHorario = 'NORMAL' | 'EXTRA'
type UnidadeTempo = 'MINUTOS' | 'HORAS'

function formatarPeriodo(periodoSelecionado: DateRange | null): string {
  if (!periodoSelecionado) return 'Nenhum período selecionado'
  return `${format(periodoSelecionado.start, 'dd/MM/yyyy')} até ${format(periodoSelecionado.end, 'dd/MM/yyyy')}`
}

export default function PlanejamentoModal({
  open,
  onClose,
  periodoSelecionado,
  usuariosSelecionados,
  tiposAtividade,
  onSuccess,
}: PlanejamentoModalProps) {
  const [tipoAtividadeId, setTipoAtividadeId] = useState<number | ''>('')
  const [tipoHorario, setTipoHorario] = useState<TipoHorario>('NORMAL')
  const [unidadeTempo, setUnidadeTempo] = useState<UnidadeTempo>('HORAS')
  const [valorTempo, setValorTempo] = useState('1')
  const [descricao, setDescricao] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setErro(null)
    if (tiposAtividade.length > 0 && tipoAtividadeId === '') {
      setTipoAtividadeId(tiposAtividade[0].id)
    }
  }, [open, tipoAtividadeId, tiposAtividade])

  const diasSelecionados = useMemo(() => {
    if (!periodoSelecionado) return []
    return eachDayOfInterval({ start: periodoSelecionado.start, end: periodoSelecionado.end })
  }, [periodoSelecionado])

  const minutosTotais = useMemo(() => {
    const valor = Number(valorTempo)
    if (!Number.isFinite(valor) || valor <= 0) return 0
    return unidadeTempo === 'HORAS' ? Math.round(valor * 60) : Math.round(valor)
  }, [unidadeTempo, valorTempo])

  const tipoAtividadeSelecionado = useMemo(
    () => tiposAtividade.find((item) => item.id === tipoAtividadeId) ?? null,
    [tipoAtividadeId, tiposAtividade],
  )

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErro(null)

    if (!periodoSelecionado) {
      setErro('Selecione ao menos um dia na agenda antes de criar o planejamento.')
      return
    }

    if (usuariosSelecionados.length === 0) {
      setErro('Selecione pelo menos um usuário.')
      return
    }

    if (!tipoAtividadeSelecionado) {
      setErro('Selecione o tipo de atividade.')
      return
    }

    if (minutosTotais <= 0) {
      setErro('Informe uma duração válida para o lançamento.')
      return
    }

    setSalvando(true)

    try {
      const descricaoPersistida = [
        `Tipo de atividade: ${tipoAtividadeSelecionado.nome}`,
        descricao.trim() ? descricao.trim() : null,
      ]
        .filter(Boolean)
        .join(' • ')

      for (const usuario of usuariosSelecionados) {
        for (const dia of diasSelecionados) {
          await criarPlanejamento({
            usuario_id: usuario.id,
            data: format(dia, 'yyyy-MM-dd'),
            bloco_id: null,
            minutos_planejados_normais: tipoHorario === 'NORMAL' ? minutosTotais : 0,
            minutos_planejados_extras: tipoHorario === 'EXTRA' ? minutosTotais : 0,
            descricao: descricaoPersistida,
          })
        }
      }

      await onSuccess()
      onClose()
    } catch (error) {
      const mensagem =
        typeof error === 'object' && error !== null && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null
      setErro(mensagem ?? 'Não foi possível criar o planejamento para o período selecionado.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Criar planejamento" size="lg">
      <form className={styles.modalForm} onSubmit={handleSubmit}>
        <div className={styles.modalSection}>
          <div>
            <h3 className={styles.modalSectionTitle}>Período</h3>
            <p className={styles.modalSectionSubtitle}>{formatarPeriodo(periodoSelecionado)}</p>
          </div>
          <div className={styles.selectionInfoGrid}>
            <div className={styles.selectionInfoCard}>
              <span className={styles.selectionInfoLabel}>Dias</span>
              <strong>{diasSelecionados.length}</strong>
            </div>
            <div className={styles.selectionInfoCard}>
              <span className={styles.selectionInfoLabel}>Usuários</span>
              <strong>{usuariosSelecionados.length}</strong>
            </div>
            <div className={styles.selectionInfoCard}>
              <span className={styles.selectionInfoLabel}>Carga por dia</span>
              <strong>{minutosTotais} min</strong>
            </div>
          </div>
        </div>

        <div className={styles.modalSection}>
          <h3 className={styles.modalSectionTitle}>Usuários envolvidos</h3>
          <div className={styles.chipsWrap}>
            {usuariosSelecionados.map((usuario) => (
              <Badge key={usuario.id} variant="info" size="md">
                {usuario.nome_guerra || usuario.nome}
              </Badge>
            ))}
          </div>
        </div>

        <div className={styles.formGrid}>
          <label className={styles.fieldGroup}>
            <span className={styles.fieldLabel}>Tipo de atividade</span>
            <select
              className={styles.fieldControl}
              value={tipoAtividadeId}
              onChange={(event) => setTipoAtividadeId(Number(event.target.value))}
            >
              {tiposAtividade.map((tipo) => (
                <option key={tipo.id} value={tipo.id}>
                  {tipo.nome}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.fieldGroup}>
            <span className={styles.fieldLabel}>Tipo de horário</span>
            <select
              className={styles.fieldControl}
              value={tipoHorario}
              onChange={(event) => setTipoHorario(event.target.value as TipoHorario)}
            >
              <option value="NORMAL">Normal</option>
              <option value="EXTRA">Hora extra</option>
            </select>
          </label>

          <label className={styles.fieldGroup}>
            <span className={styles.fieldLabel}>Unidade do tempo</span>
            <select
              className={styles.fieldControl}
              value={unidadeTempo}
              onChange={(event) => setUnidadeTempo(event.target.value as UnidadeTempo)}
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
              value={valorTempo}
              onChange={(event) => setValorTempo(event.target.value)}
            />
          </label>
        </div>

        <label className={styles.fieldGroup}>
          <span className={styles.fieldLabel}>Descrição</span>
          <textarea
            className={`${styles.fieldControl} ${styles.textareaControl}`}
            rows={4}
            placeholder="Detalhes adicionais do planejamento"
            value={descricao}
            onChange={(event) => setDescricao(event.target.value)}
          />
        </label>

        {tipoAtividadeSelecionado && (
          <div className={styles.planejamentoPreview}>
            <span className={styles.planejamentoPreviewTitle}>Prévia do lançamento</span>
            <p>
              {tipoAtividadeSelecionado.nome} em regime {tipoHorario === 'NORMAL' ? 'normal' : 'hora extra'}, com {minutosTotais} minutos por dia.
            </p>
            <p className={styles.planejamentoPreviewNote}>
              O backend atual persiste o tipo de atividade na descrição do planejamento para manter compatibilidade com a API existente.
            </p>
          </div>
        )}

        {erro && <div className={styles.formError}>{erro}</div>}

        <Modal.Footer>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" loading={salvando}>
            Criar lançamento
          </Button>
        </Modal.Footer>
      </form>
    </Modal>
  )
}
