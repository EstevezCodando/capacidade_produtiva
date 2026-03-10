// ============================================================
// Configuracoes — Página de configurações administrativas
// ============================================================
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { getConfigTeto, atualizarConfigTeto, getFeriados, criarFeriado, removerFeriado } from '@/api/agenda'
import { Button, Input, Card, Badge, EmptyState } from '@/components/ui/Common'
import Modal from '@/components/ui/Modal'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import styles from './Configuracoes.module.css'

export default function Configuracoes() {
  const { ehAdmin } = useAuth()
  const queryClient = useQueryClient()

  // Query de configuração de teto
  const { data: configTeto, isLoading: loadingConfig } = useQuery({
    queryKey: ['configTeto'],
    queryFn: getConfigTeto,
    enabled: ehAdmin,
  })

  // Query de feriados
  const { data: feriadosData, isLoading: loadingFeriados } = useQuery({
    queryKey: ['feriados'],
    queryFn: getFeriados,
    enabled: ehAdmin,
  })

  // Estado do formulário de teto
  const [tetoNormal, setTetoNormal] = useState('')
  const [tetoExtra, setTetoExtra] = useState('')

  // Preencher valores quando carregar
  useEffect(() => {
    if (configTeto) {
      setTetoNormal(configTeto.teto_normal_min.toString())
      setTetoExtra(configTeto.teto_extra_min.toString())
    }
  }, [configTeto])

  // Mutation para atualizar teto
  const updateTetoMutation = useMutation({
    mutationFn: () => atualizarConfigTeto({
      teto_normal_min: parseInt(tetoNormal),
      teto_extra_min: parseInt(tetoExtra),
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['configTeto'] })
    },
  })

  // Estado do modal de novo feriado
  const [feriadoModalOpen, setFeriadoModalOpen] = useState(false)
  const [feriadoData, setFeriadoData] = useState('')
  const [feriadoDescricao, setFeriadoDescricao] = useState('')

  // Mutation para criar feriado
  const createFeriadoMutation = useMutation({
    mutationFn: () => criarFeriado({
      data: feriadoData,
      descricao: feriadoDescricao,
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['feriados'] })
      setFeriadoModalOpen(false)
      setFeriadoData('')
      setFeriadoDescricao('')
    },
  })

  // Mutation para remover feriado
  const removeFeriadoMutation = useMutation({
    mutationFn: removerFeriado,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['feriados'] })
    },
  })

  if (!ehAdmin) {
    return (
      <div className={styles.page}>
        <EmptyState
          title="Acesso restrito"
          description="Esta página é acessível apenas para administradores"
        />
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Configurações</h1>
        <p className={styles.subtitle}>Parâmetros de capacidade e calendário</p>
      </div>

      <div className={styles.content}>
        {/* Configuração de Teto */}
        <Card title="Capacidade Diária" subtitle="Limites de minutos por dia">
          <div className={styles.configForm}>
            <div className={styles.configRow}>
              <div className={styles.configField}>
                <Input
                  label="Minutos Normais (por dia)"
                  type="number"
                  value={tetoNormal}
                  onChange={(e) => setTetoNormal(e.target.value)}
                  placeholder="360"
                  min={0}
                />
                <span className={styles.configHint}>
                  Equivale a {tetoNormal ? Math.round(parseInt(tetoNormal) / 60) : 0} horas
                </span>
              </div>
              <div className={styles.configField}>
                <Input
                  label="Minutos Extras (máximo por dia)"
                  type="number"
                  value={tetoExtra}
                  onChange={(e) => setTetoExtra(e.target.value)}
                  placeholder="240"
                  min={0}
                />
                <span className={styles.configHint}>
                  Equivale a {tetoExtra ? Math.round(parseInt(tetoExtra) / 60) : 0} horas
                </span>
              </div>
            </div>

            {configTeto && (
              <div className={styles.configInfo}>
                <span className={styles.configInfoLabel}>Vigência atual:</span>
                <span className={styles.configInfoValue}>
                  {format(new Date(configTeto.vigencia_inicio), "d 'de' MMMM 'de' yyyy", { locale: ptBR })}
                  {configTeto.vigencia_fim 
                    ? ` — ${format(new Date(configTeto.vigencia_fim), "d 'de' MMMM 'de' yyyy", { locale: ptBR })}`
                    : ' — Indefinido'
                  }
                </span>
              </div>
            )}

            <div className={styles.configActions}>
              <Button
                variant="primary"
                onClick={() => updateTetoMutation.mutate()}
                loading={updateTetoMutation.isPending}
                disabled={!tetoNormal || !tetoExtra}
              >
                Salvar configurações
              </Button>
              {updateTetoMutation.isSuccess && (
                <Badge variant="success">Salvo com sucesso!</Badge>
              )}
              {updateTetoMutation.isError && (
                <Badge variant="error">Erro ao salvar</Badge>
              )}
            </div>
          </div>
        </Card>

        {/* Feriados */}
        <Card 
          title="Feriados" 
          subtitle="Dias sem capacidade produtiva"
          action={
            <Button variant="secondary" size="sm" onClick={() => setFeriadoModalOpen(true)}>
              Adicionar feriado
            </Button>
          }
        >
          {loadingFeriados ? (
            <div className={styles.loading}>Carregando...</div>
          ) : feriadosData?.feriados.length === 0 ? (
            <EmptyState
              title="Nenhum feriado cadastrado"
              description="Adicione feriados para bloquear dias no calendário"
              action={
                <Button variant="primary" size="sm" onClick={() => setFeriadoModalOpen(true)}>
                  Adicionar feriado
                </Button>
              }
            />
          ) : (
            <div className={styles.feriadosList}>
              {feriadosData?.feriados
                .sort((a, b) => new Date(a.data).getTime() - new Date(b.data).getTime())
                .map((feriado) => (
                  <div key={feriado.id} className={styles.feriadoItem}>
                    <div className={styles.feriadoInfo}>
                      <span className={styles.feriadoData}>
                        {format(new Date(feriado.data), "dd/MM/yyyy")}
                      </span>
                      <span className={styles.feriadoDescricao}>
                        {feriado.descricao}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        if (confirm('Remover este feriado?')) {
                          removeFeriadoMutation.mutate(feriado.id)
                        }
                      }}
                      loading={removeFeriadoMutation.isPending}
                    >
                      Remover
                    </Button>
                  </div>
                ))
              }
            </div>
          )}
        </Card>
      </div>

      {/* Modal de novo feriado */}
      <Modal
        open={feriadoModalOpen}
        onClose={() => setFeriadoModalOpen(false)}
        title="Adicionar Feriado"
        size="sm"
      >
        <div className={styles.feriadoForm}>
          <Input
            label="Data"
            type="date"
            value={feriadoData}
            onChange={(e) => setFeriadoData(e.target.value)}
          />
          <Input
            label="Descrição"
            type="text"
            value={feriadoDescricao}
            onChange={(e) => setFeriadoDescricao(e.target.value)}
            placeholder="Ex: Natal, Ano Novo, etc."
          />
        </div>
        <Modal.Footer>
          <Button variant="ghost" onClick={() => setFeriadoModalOpen(false)}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={() => createFeriadoMutation.mutate()}
            loading={createFeriadoMutation.isPending}
            disabled={!feriadoData || !feriadoDescricao}
          >
            Adicionar
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
