// ============================================================
// ConsolidacaoModal — Modal para consolidação de período
// ============================================================
import { useState } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { DateRange, Pendencia } from '@/types/agenda'
import { consolidarPeriodo } from '@/api/agenda'
import Modal from '@/components/ui/Modal'
import { Button, Badge } from '@/components/ui/Common'
import styles from './Agenda.module.css'

interface ConsolidacaoModalProps {
  open: boolean
  onClose: () => void
  dateRange: DateRange | null
  usuarioIds: number[]
}

export default function ConsolidacaoModal({ open, onClose, dateRange, usuarioIds }: ConsolidacaoModalProps) {
  const queryClient = useQueryClient()
  const [pendencias, setPendencias] = useState<Pendencia[]>([])
  const [consolidado, setConsolidado] = useState(false)
  const [mensagem, setMensagem] = useState('')

  const mutation = useMutation({
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

  const handleConsolidar = (ignorarPendencias = false) => {
    if (!dateRange) return
    mutation.mutate({
      data_inicio: format(dateRange.start, 'yyyy-MM-dd'),
      data_fim: format(dateRange.end, 'yyyy-MM-dd'),
      usuarios_ids: usuarioIds.length > 0 ? usuarioIds : undefined,
      ignorar_pendencias: ignorarPendencias,
    })
  }

  const handleClose = () => {
    setPendencias([])
    setConsolidado(false)
    setMensagem('')
    onClose()
  }

  const hasPendencias = pendencias.length > 0

  // Agrupar pendências por usuário
  const pendenciasPorUsuario = pendencias.reduce((acc, p) => {
    const key = p.usuario_id
    if (!acc[key]) acc[key] = { nome: p.usuario_nome ?? `Usuário ${p.usuario_id}`, items: [] }
    acc[key].items.push(p)
    return acc
  }, {} as Record<number, { nome: string; items: Pendencia[] }>)

  return (
    <Modal open={open} onClose={handleClose} title="Consolidar Período" size="lg">
      <div className={styles.consolidacaoContent}>
        {/* Período selecionado */}
        {dateRange && (
          <div className={styles.consolidacaoPeriodo}>
            <span className={styles.consolidacaoLabel}>Período:</span>
            <span className={styles.consolidacaoValue}>
              {format(dateRange.start, "d 'de' MMMM", { locale: ptBR })} — {format(dateRange.end, "d 'de' MMMM 'de' yyyy", { locale: ptBR })}
            </span>
          </div>
        )}

        {/* Estado inicial - sem verificação ainda */}
        {!mutation.isSuccess && !mutation.isPending && (
          <div className={styles.consolidacaoInfo}>
            <div className={styles.infoIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4M12 8h.01" />
              </svg>
            </div>
            <h4>Verificação de pendências</h4>
            <p>Ao consolidar, o sistema verificará se todos os usuários obrigatórios possuem lançamentos no período. Dias consolidados não podem mais ser editados por operadores.</p>
          </div>
        )}

        {/* Loading */}
        {mutation.isPending && (
          <div className={styles.consolidacaoLoading}>
            <div className={styles.spinner} />
            <p>Verificando pendências...</p>
          </div>
        )}

        {/* Resultado: Sucesso */}
        {consolidado && (
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

        {/* Resultado: Com pendências */}
        {hasPendencias && !consolidado && (
          <div className={styles.consolidacaoPendencias}>
            <div className={styles.pendenciasHeader}>
              <div className={styles.warningIcon}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <div>
                <h4>Pendências encontradas</h4>
                <p>{pendencias.length} pendência(s) impedem a consolidação</p>
              </div>
            </div>

            <div className={styles.pendenciasList}>
              {Object.entries(pendenciasPorUsuario).map(([userId, { nome, items }]) => (
                <div key={userId} className={styles.pendenciaGrupo}>
                  <div className={styles.pendenciaUsuario}>
                    <span className={styles.pendenciaAvatar}>{nome.charAt(0).toUpperCase()}</span>
                    <span className={styles.pendenciaNome}>{nome}</span>
                    <Badge variant="error" size="sm">{items.length}</Badge>
                  </div>
                  <div className={styles.pendenciaItems}>
                    {items.map((p, i) => (
                      <div key={i} className={styles.pendenciaItem}>
                        <span className={styles.pendenciaData}>{format(new Date(p.data), 'dd/MM')}</span>
                        <span className={styles.pendenciaTipo}>{p.tipo.replace(/_/g, ' ')}</span>
                        <span className={styles.pendenciaMotivo}>{p.motivo}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Erro */}
        {mutation.isError && (
          <div className={styles.consolidacaoError}>
            <p>Erro ao consolidar: {(mutation.error as Error).message}</p>
          </div>
        )}
      </div>

      <Modal.Footer>
        {consolidado ? (
          <Button variant="primary" size="sm" onClick={handleClose}>Fechar</Button>
        ) : (
          <>
            <Button variant="ghost" size="sm" onClick={handleClose}>Cancelar</Button>
            {hasPendencias && (
              <Button variant="danger" size="sm" onClick={() => handleConsolidar(true)} loading={mutation.isPending}>
                Ignorar e consolidar
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={() => handleConsolidar(false)} loading={mutation.isPending}>
              {hasPendencias ? 'Verificar novamente' : 'Consolidar período'}
            </Button>
          </>
        )}
      </Modal.Footer>
    </Modal>
  )
}
