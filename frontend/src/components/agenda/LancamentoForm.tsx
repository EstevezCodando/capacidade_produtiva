import { useState, useEffect, useMemo } from 'react'
import { format, isAfter, startOfDay } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  CodigoAtividade,
  FaixaMinuto,
  Lancamento,
  LancamentoInput,
  LancamentoAdminInput,
  TipoAtividade,
  Bloco,
} from '@/types/agenda'
import {
  criarLancamento,
  criarLancamentoAdmin,
  editarLancamento,
  editarLancamentoAdmin,
  removerLancamento,
  removerLancamentoAdmin,
} from '@/api/agenda'
import Modal from '@/components/ui/Modal'
import { Button, Input, Textarea, Select } from '@/components/ui/Common'
import styles from './Agenda.module.css'

interface LancamentoFormProps {
  open: boolean
  onClose: () => void
  date: Date | null
  lancamento?: Lancamento | null
  blocos?: Bloco[]
  tiposAtividade?: TipoAtividade[]
  isAdmin?: boolean
  usuarioId?: number | null
}

function buildTipoOptions(tiposAtividade: TipoAtividade[]) {
  return tiposAtividade
    .filter((tipo) => tipo.origem !== 'BLOCO')
    .map((tipo) => ({
      value: tipo.codigo,
      label: tipo.nome,
    }))
}

export default function LancamentoForm({
  open,
  onClose,
  date,
  lancamento,
  blocos = [],
  tiposAtividade = [],
  isAdmin = false,
  usuarioId = null,
}: LancamentoFormProps) {
  const queryClient = useQueryClient()
  const isEditing = !!lancamento

  const tipoOptions = useMemo(() => {
    const extras = buildTipoOptions(tiposAtividade)
    return [{ value: 'BLOCO', label: 'Bloco de produção' }, ...extras]
  }, [tiposAtividade])

  const [tipoAtividade, setTipoAtividade] = useState<CodigoAtividade>('BLOCO')
  const [blocoId, setBlocoId] = useState<string>('')
  const [faixa, setFaixa] = useState<FaixaMinuto>('NORMAL')
  const [minutos, setMinutos] = useState<string>('60')
  const [descricao, setDescricao] = useState<string>('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!open) return

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
  }, [open, lancamento, blocos])

  const criarMutation = useMutation({
    mutationFn: async () => {
      if (!date) throw new Error('Selecione uma data válida.')
      const minutosNumero = Number(minutos)
      const payloadBase: LancamentoInput = {
        data: format(date, 'yyyy-MM-dd'),
        bloco_id: tipoAtividade === 'BLOCO' ? Number(blocoId) : null,
        tipo_atividade: tipoAtividade,
        faixa,
        minutos: minutosNumero,
        descricao: descricao.trim() || undefined,
      }

      if (isAdmin) {
        if (!usuarioId) throw new Error('Selecione um usuário para lançar a atividade.')
        const payloadAdmin: LancamentoAdminInput = {
          ...payloadBase,
          usuario_id: usuarioId,
        }
        return criarLancamentoAdmin(payloadAdmin)
      }

      return criarLancamento(payloadBase)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agenda'] })
      await queryClient.invalidateQueries({ queryKey: ['capacidade'] })
      await queryClient.invalidateQueries({ queryKey: ['agenda-realizada-multiusuario'] })
      onClose()
    },
    onError: (error: Error) => setErrors({ submit: error.message }),
  })

  const editarMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { minutos?: number; descricao?: string } }) => {
      if (isAdmin) return editarLancamentoAdmin(id, data)
      return editarLancamento(id, data)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agenda'] })
      await queryClient.invalidateQueries({ queryKey: ['capacidade'] })
      await queryClient.invalidateQueries({ queryKey: ['agenda-realizada-multiusuario'] })
      onClose()
    },
    onError: (error: Error) => setErrors({ submit: error.message }),
  })

  const removerMutation = useMutation({
    mutationFn: (id: number) => {
      if (isAdmin) return removerLancamentoAdmin(id)
      return removerLancamento(id)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agenda'] })
      await queryClient.invalidateQueries({ queryKey: ['capacidade'] })
      await queryClient.invalidateQueries({ queryKey: ['agenda-realizada-multiusuario'] })
      onClose()
    },
    onError: (error: Error) => setErrors({ submit: error.message }),
  })

  function validate() {
    const newErrors: Record<string, string> = {}
    const minutosNumero = Number(minutos)

    if (!date) newErrors.date = 'Selecione uma data válida.'
    if (date && isAfter(startOfDay(date), startOfDay(new Date()))) {
      newErrors.date = 'Lançamentos só podem ser feitos até a data atual.'
    }
    if (!Number.isFinite(minutosNumero) || minutosNumero <= 0) {
      newErrors.minutos = 'Informe um valor válido de minutos.'
    }
    if (tipoAtividade === 'BLOCO' && !blocoId) {
      newErrors.blocoId = 'Selecione um bloco.'
    }
    if (isAdmin && !isEditing && !usuarioId) {
      newErrors.usuario = 'Selecione um usuário antes de lançar.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!validate()) return

    if (isEditing && lancamento) {
      editarMutation.mutate({
        id: lancamento.id,
        data: {
          minutos: Number(minutos),
          descricao: descricao.trim() || undefined,
        },
      })
      return
    }

    criarMutation.mutate()
  }

  function handleDelete() {
    if (!lancamento) return
    if (!confirm('Excluir este lançamento?')) return
    removerMutation.mutate(lancamento.id)
  }

  const isLoading = criarMutation.isPending || editarMutation.isPending || removerMutation.isPending

  return (
    <Modal open={open} onClose={onClose} title={isEditing ? 'Editar lançamento' : 'Novo lançamento'} size="md">
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.dateHeader}>
          <span className={styles.dateLabel}>Data:</span>
          <span className={styles.dateValue}>{date ? format(date, "EEEE, d 'de' MMMM 'de' yyyy", { locale: ptBR }) : '—'}</span>
        </div>

        {errors.date && <div className={styles.submitError}>{errors.date}</div>}
        {errors.usuario && <div className={styles.submitError}>{errors.usuario}</div>}

        {!isEditing && (
          <div className={styles.field}>
            <label className={styles.label}>Atividade</label>
            <Select
              value={tipoAtividade}
              onChange={(value) => setTipoAtividade(value as CodigoAtividade)}
              options={tipoOptions}
              disabled={isLoading}
            />
          </div>
        )}

        {!isEditing && tipoAtividade === 'BLOCO' && (
          <div className={styles.field}>
            <label className={styles.label}>Bloco</label>
            <Select
              value={blocoId}
              onChange={setBlocoId}
              options={blocos.map((bloco) => ({ value: bloco.id.toString(), label: bloco.nome }))}
              placeholder="Selecione um bloco"
              disabled={isLoading}
            />
            {errors.blocoId && <span className={styles.error}>{errors.blocoId}</span>}
          </div>
        )}

        {!isEditing && (
          <div className={styles.field}>
            <label className={styles.label}>Faixa</label>
            <div className={styles.radioGroup}>
              {(['NORMAL', 'EXTRA'] as FaixaMinuto[]).map((itemFaixa) => (
                <label key={itemFaixa} className={styles.radioLabel}>
                  <input
                    type="radio"
                    name="faixa"
                    value={itemFaixa}
                    checked={faixa === itemFaixa}
                    onChange={() => setFaixa(itemFaixa)}
                    disabled={isLoading}
                    className={styles.radioInput}
                  />
                  <span className={`${styles.radioBox} ${faixa === itemFaixa ? styles.radioBoxActive : ''}`}>
                    {itemFaixa === 'NORMAL' ? 'Normal' : 'Hora extra'}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className={styles.field}>
          <Input
            label="Minutos"
            type="number"
            min="1"
            max="480"
            step="5"
            value={minutos}
            onChange={(event) => setMinutos(event.target.value)}
            error={errors.minutos}
            disabled={isLoading}
          />
          <div className={styles.quickMinutes}>
            {[30, 60, 90, 120, 180, 240].map((valor) => (
              <button
                key={valor}
                type="button"
                className={`${styles.quickBtn} ${Number(minutos) === valor ? styles.quickBtnActive : ''}`}
                onClick={() => setMinutos(valor.toString())}
              >
                {valor >= 60 ? `${valor / 60}h` : `${valor}min`}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.field}>
          <Textarea
            label="Descrição"
            value={descricao}
            onChange={(event) => setDescricao(event.target.value)}
            placeholder="Detalhes do lançamento realizado"
            rows={3}
            disabled={isLoading}
          />
        </div>

        {errors.submit && <div className={styles.submitError}>{errors.submit}</div>}

        <Modal.Footer>
          {isEditing && <Button type="button" variant="danger" size="sm" onClick={handleDelete} loading={removerMutation.isPending}>Excluir</Button>}
          <div style={{ flex: 1 }} />
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={isLoading}>Cancelar</Button>
          <Button type="submit" variant="primary" size="sm" loading={criarMutation.isPending || editarMutation.isPending}>{isEditing ? 'Salvar' : 'Criar lançamento'}</Button>
        </Modal.Footer>
      </form>
    </Modal>
  )
}
