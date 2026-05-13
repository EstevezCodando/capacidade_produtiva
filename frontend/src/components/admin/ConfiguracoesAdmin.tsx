// ============================================================
// ConfiguracoesAdmin — Painel de configurações do sistema
// ============================================================
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getConfigTeto, atualizarConfigTeto } from '@/api/agenda'
import { Card, Button, Input, StatCard, Skeleton } from '@/components/ui/Common'
import styles from './Configuracoes.module.css'

export default function ConfiguracoesAdmin() {
  const queryClient = useQueryClient()
  const [tetoNormal, setTetoNormal] = useState('')
  const [tetoSexta, setTetoSexta] = useState('')
  const [tetoExtra, setTetoExtra] = useState('')
  const [editando, setEditando] = useState(false)
  const [erro, setErro] = useState('')

  const { data: config, isLoading } = useQuery({
    queryKey: ['configTeto'],
    queryFn: getConfigTeto,
    staleTime: 60000,
  })

  useEffect(() => {
    if (config) {
      setTetoNormal(config.teto_normal_min.toString())
      setTetoSexta(config.teto_sexta_min.toString())
      setTetoExtra(config.teto_extra_min.toString())
    }
  }, [config])

  const mutation = useMutation({
    mutationFn: atualizarConfigTeto,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configTeto'] })
      queryClient.invalidateQueries({ queryKey: ['agenda'] })
      queryClient.invalidateQueries({ queryKey: ['capacidade'] })
      setEditando(false)
      setErro('')
    },
    onError: (error: Error) => {
      setErro(error.message)
    },
  })

  const handleSalvar = () => {
    const normalMin = parseInt(tetoNormal, 10)
    const sextaMin = parseInt(tetoSexta, 10)
    const extraMin = parseInt(tetoExtra, 10)

    if (isNaN(normalMin) || normalMin <= 0) {
      setErro('Teto Seg–Qui deve ser maior que zero')
      return
    }
    if (isNaN(sextaMin) || sextaMin <= 0) {
      setErro('Teto Sexta deve ser maior que zero')
      return
    }
    if (isNaN(extraMin) || extraMin < 0) {
      setErro('Teto extra deve ser zero ou maior')
      return
    }

    mutation.mutate({ teto_normal_min: normalMin, teto_sexta_min: sextaMin, teto_extra_min: extraMin })
  }

  const handleCancelar = () => {
    if (config) {
      setTetoNormal(config.teto_normal_min.toString())
      setTetoSexta(config.teto_sexta_min.toString())
      setTetoExtra(config.teto_extra_min.toString())
    }
    setEditando(false)
    setErro('')
  }

  const formatMinutosHoras = (min: number) => {
    const h = Math.floor(min / 60)
    const m = min % 60
    if (m === 0) return `${h}h`
    return `${h}h ${m}min`
  }

  if (isLoading) {
    return (
      <Card title="Configurações de Capacidade">
        <div className={styles.loading}>
          <Skeleton height={80} />
          <Skeleton height={80} />
          <Skeleton height={80} />
        </div>
      </Card>
    )
  }

  return (
    <Card
      title="Configurações de Capacidade"
      subtitle="Teto diário por tipo de dia"
      action={
        !editando ? (
          <Button variant="secondary" size="sm" onClick={() => setEditando(true)}>Editar</Button>
        ) : null
      }
    >
      <div className={styles.content}>
        <div className={styles.configGrid}>
          {editando ? (
            <>
              <div className={styles.field}>
                <Input
                  label="Seg–Qui — Normal (minutos/dia)"
                  type="number"
                  min="1"
                  max="720"
                  value={tetoNormal}
                  onChange={(e) => setTetoNormal(e.target.value)}
                  hint={`= ${formatMinutosHoras(parseInt(tetoNormal) || 0)}`}
                />
              </div>
              <div className={styles.field}>
                <Input
                  label="Sexta — Normal (minutos/dia)"
                  type="number"
                  min="1"
                  max="720"
                  value={tetoSexta}
                  onChange={(e) => setTetoSexta(e.target.value)}
                  hint={`= ${formatMinutosHoras(parseInt(tetoSexta) || 0)}`}
                />
              </div>
              <div className={styles.field}>
                <Input
                  label="Hora Extra — Máximo (minutos/dia)"
                  type="number"
                  min="0"
                  max="720"
                  value={tetoExtra}
                  onChange={(e) => setTetoExtra(e.target.value)}
                  hint={`= ${formatMinutosHoras(parseInt(tetoExtra) || 0)}`}
                />
              </div>
            </>
          ) : (
            <>
              <div className={styles.statBox}>
                <StatCard
                  label="Seg–Qui (normal)"
                  value={formatMinutosHoras(config?.teto_normal_min ?? 0)}
                  variant="accent"
                  size="md"
                />
                <span className={styles.statDetail}>{config?.teto_normal_min ?? 0} min/dia</span>
              </div>
              <div className={styles.statBox}>
                <StatCard
                  label="Sexta (normal)"
                  value={formatMinutosHoras(config?.teto_sexta_min ?? 0)}
                  variant="accent"
                  size="md"
                />
                <span className={styles.statDetail}>{config?.teto_sexta_min ?? 0} min/dia</span>
              </div>
              <div className={styles.statBox}>
                <StatCard
                  label="Hora Extra — Máximo"
                  value={formatMinutosHoras(config?.teto_extra_min ?? 0)}
                  variant="warning"
                  size="md"
                />
                <span className={styles.statDetail}>{config?.teto_extra_min ?? 0} min/dia</span>
              </div>
            </>
          )}
        </div>

        {config && !editando && (
          <div className={styles.vigencia}>
            <span className={styles.vigenciaLabel}>Vigência:</span>
            <span className={styles.vigenciaValue}>
              Desde {new Date(config.vigencia_inicio).toLocaleDateString('pt-BR')}
              {config.vigencia_fim && ` até ${new Date(config.vigencia_fim).toLocaleDateString('pt-BR')}`}
            </span>
          </div>
        )}

        {erro && <div className={styles.erro}>{erro}</div>}

        {editando && (
          <div className={styles.actions}>
            <Button variant="ghost" size="sm" onClick={handleCancelar}>Cancelar</Button>
            <Button variant="primary" size="sm" onClick={handleSalvar} loading={mutation.isPending}>Salvar alterações</Button>
          </div>
        )}

        <div className={styles.info}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
          <p>Seg–Qui e Sexta definem o teto normal por dia. Hora Extra define o máximo permitido por dia. Alterações afetam novos cálculos de capacidade.</p>
        </div>
      </div>
    </Card>
  )
}
