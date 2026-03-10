// ============================================================
// LancamentoForm — Formulário de criação/edição de lançamento
// ============================================================
import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { CodigoAtividade, FaixaMinuto, Lancamento, LancamentoInput } from '@/types/agenda'
import { criarLancamento, editarLancamento, removerLancamento } from '@/api/agenda'
import Modal from '@/components/ui/Modal'
import { Button, Input, Textarea, Select } from '@/components/ui/Common'
import styles from './Agenda.module.css'

interface LancamentoFormProps {
  open: boolean
  onClose: () => void
  date: Date | null
  lancamento?: Lancamento | null
  blocos?: { id: number; nome: string }[]
}

const TIPOS_ATIVIDADE: { value: CodigoAtividade; label: string }[] = [
  { value: 'BLOCO', label: 'Bloco' },
  { value: 'EXTERNA', label: 'Atividade Externa' },
  { value: 'AJUSTE', label: 'Ajuste' },
]

export default function LancamentoForm({ open, onClose, date, lancamento, blocos = [] }: LancamentoFormProps) {
  const queryClient = useQueryClient()
  const isEditing = !!lancamento

  const [tipoAtividade, setTipoAtividade] = useState<CodigoAtividade>('BLOCO')
  const [blocoId, setBlocoId] = useState<string>('')
  const [faixa, setFaixa] = useState<FaixaMinuto>('NORMAL')
  const [minutos, setMinutos] = useState<string>('60')
  const [descricao, setDescricao] = useState<string>('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (open) {
      if (lancamento) {
        setTipoAtividade(lancamento.tipo_atividade_codigo)
        setBlocoId(lancamento.bloco_id?.toString() ?? '')
        setFaixa(lancamento.faixa_minuto)
        setMinutos(lancamento.minutos.toString())
        setDescricao(lancamento.descricao ?? '')
      } else {
        setTipoAtividade('BLOCO')
        setBlocoId(blocos[0]?.id?.toString() ?? '')
        setFaixa('NORMAL')
        setMinutos('60')
        setDescricao('')
      }
      setErrors({})
    }
  }, [open, lancamento, blocos])

  const criarMutation = useMutation({
    mutationFn: criarLancamento,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['agenda'] }); onClose() },
    onError: (error: Error) => setErrors({ submit: error.message }),
  })

  const editarMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { minutos?: number; descricao?: string } }) => editarLancamento(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['agenda'] }); onClose() },
    onError: (error: Error) => setErrors({ submit: error.message }),
  })

  const removerMutation = useMutation({
    mutationFn: removerLancamento,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['agenda'] }); onClose() },
  })

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}
    const minutosNum = parseInt(minutos, 10)
    if (isNaN(minutosNum) || minutosNum <= 0) newErrors.minutos = 'Informe um valor válido'
    if (tipoAtividade === 'BLOCO' && !blocoId) newErrors.blocoId = 'Selecione um bloco'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate() || !date) return

    if (isEditing && lancamento) {
      editarMutation.mutate({ id: lancamento.id, data: { minutos: parseInt(minutos, 10), descricao: descricao || undefined } })
    } else {
      const input: LancamentoInput = {
        data: format(date, 'yyyy-MM-dd'),
        bloco_id: tipoAtividade === 'BLOCO' ? parseInt(blocoId, 10) : null,
        tipo_atividade: tipoAtividade,
        faixa,
        minutos: parseInt(minutos, 10),
        descricao: descricao || undefined,
      }
      criarMutation.mutate(input)
    }
  }

  const handleDelete = () => {
    if (lancamento && confirm('Excluir este lançamento?')) removerMutation.mutate(lancamento.id)
  }

  const isLoading = criarMutation.isPending || editarMutation.isPending || removerMutation.isPending

  return (
    <Modal open={open} onClose={onClose} title={isEditing ? 'Editar Lançamento' : 'Novo Lançamento'} size="md">
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.dateHeader}>
          <span className={styles.dateLabel}>Data:</span>
          <span className={styles.dateValue}>{date ? format(date, "EEEE, d 'de' MMMM 'de' yyyy", { locale: ptBR }) : '—'}</span>
        </div>

        {!isEditing && (
          <div className={styles.field}>
            <label className={styles.label}>Tipo de Atividade</label>
            <Select value={tipoAtividade} onChange={(v) => setTipoAtividade(v as CodigoAtividade)} options={TIPOS_ATIVIDADE} disabled={isLoading} />
          </div>
        )}

        {tipoAtividade === 'BLOCO' && !isEditing && (
          <div className={styles.field}>
            <label className={styles.label}>Bloco</label>
            <Select value={blocoId} onChange={setBlocoId} options={blocos.map((b) => ({ value: b.id.toString(), label: b.nome }))} placeholder="Selecione um bloco" disabled={isLoading} />
            {errors.blocoId && <span className={styles.error}>{errors.blocoId}</span>}
          </div>
        )}

        {!isEditing && (
          <div className={styles.field}>
            <label className={styles.label}>Faixa</label>
            <div className={styles.radioGroup}>
              {(['NORMAL', 'EXTRA'] as FaixaMinuto[]).map((f) => (
                <label key={f} className={styles.radioLabel}>
                  <input type="radio" name="faixa" value={f} checked={faixa === f} onChange={() => setFaixa(f)} disabled={isLoading} className={styles.radioInput} />
                  <span className={`${styles.radioBox} ${faixa === f ? styles.radioBoxActive : ''}`}>{f === 'NORMAL' ? 'Normal' : 'Hora Extra'}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className={styles.field}>
          <Input label="Minutos" type="number" min="1" max="480" step="5" value={minutos} onChange={(e) => setMinutos(e.target.value)} error={errors.minutos} disabled={isLoading} />
          <div className={styles.quickMinutes}>
            {[30, 60, 90, 120, 180, 240].map((m) => (
              <button key={m} type="button" className={`${styles.quickBtn} ${parseInt(minutos) === m ? styles.quickBtnActive : ''}`} onClick={() => setMinutos(m.toString())}>{m >= 60 ? `${m / 60}h` : `${m}min`}</button>
            ))}
          </div>
        </div>

        <div className={styles.field}>
          <Textarea label="Descrição (opcional)" value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Detalhes adicionais..." rows={3} disabled={isLoading} />
        </div>

        {errors.submit && <div className={styles.submitError}>{errors.submit}</div>}

        <Modal.Footer>
          {isEditing && <Button type="button" variant="danger" size="sm" onClick={handleDelete} loading={removerMutation.isPending}>Excluir</Button>}
          <div style={{ flex: 1 }} />
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={isLoading}>Cancelar</Button>
          <Button type="submit" variant="primary" size="sm" loading={criarMutation.isPending || editarMutation.isPending}>{isEditing ? 'Salvar' : 'Criar Lançamento'}</Button>
        </Modal.Footer>
      </form>
    </Modal>
  )
}
