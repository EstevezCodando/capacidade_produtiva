import { useMemo } from 'react'
import { format, differenceInDays } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { DiaDaAgenda, DateRange } from '@/types/agenda'
import Drawer from '@/components/ui/Drawer'
import { Badge, CapacityBar, StatCard, Button, EmptyState } from '@/components/ui/Common'
import styles from './Agenda.module.css'

interface DayDetailPanelProps {
  open: boolean
  onClose: () => void
  selectedDates: Date[]
  selectedRange: DateRange | null
  getDiaData: (date: Date) => DiaDaAgenda | undefined
  isAdmin: boolean
  onAddLancamento?: (date: Date) => void
  onAddPlanejamento?: (date: Date) => void
  onEditLancamento?: (id: number) => void
  onConsolidar?: () => void
  exibirPlanejamento?: boolean
  tituloLancamentos?: string
  tituloPlanejamento?: string
  podeAdicionarLancamento?: (date: Date, dia: DiaDaAgenda) => boolean
}

export default function DayDetailPanel({
  open,
  onClose,
  selectedDates,
  selectedRange,
  getDiaData,
  isAdmin,
  onAddLancamento,
  onAddPlanejamento,
  onEditLancamento,
  onConsolidar,
  exibirPlanejamento = true,
  tituloLancamentos = 'Lançamentos',
  tituloPlanejamento = 'Planejamento',
  podeAdicionarLancamento,
}: DayDetailPanelProps) {
  const isSingleDay = selectedDates.length === 1
  const singleDayData = isSingleDay ? getDiaData(selectedDates[0]) : undefined

  const drawerTitle = useMemo(() => {
    if (selectedDates.length === 0) return 'Selecione um período'
    if (isSingleDay) {
      return format(selectedDates[0], "EEEE, d 'de' MMMM", { locale: ptBR })
    }
    const dias = differenceInDays(selectedRange!.end, selectedRange!.start) + 1
    return `${dias} dias selecionados`
  }, [selectedDates, selectedRange, isSingleDay])

  const drawerSubtitle = useMemo(() => {
    if (!selectedRange) return ''
    if (isSingleDay) return format(selectedDates[0], 'yyyy', { locale: ptBR })
    return `${format(selectedRange.start, 'd MMM', { locale: ptBR })} — ${format(selectedRange.end, "d MMM yyyy", { locale: ptBR })}`
  }, [selectedRange, selectedDates, isSingleDay])

  const agregado = useMemo(() => {
    if (selectedDates.length === 0) return null

    let tetoNormal = 0
    let tetoExtra = 0
    let apontadoNormal = 0
    let apontadoExtra = 0
    let ociosos = 0
    let diasUteis = 0
    let diasFeriado = 0
    let diasIndisponivel = 0
    let diasConsolidados = 0
    let diasAbertos = 0
    const lancamentosTotal: DiaDaAgenda['lancamentos'] = []
    const planejamentosTotal: DiaDaAgenda['planejamento'] = []

    for (const date of selectedDates) {
      const dia = getDiaData(date)
      if (!dia) continue

      if (dia.eh_dia_util) diasUteis += 1
      if (dia.eh_feriado) diasFeriado += 1
      if (dia.eh_indisponivel) diasIndisponivel += 1
      if (dia.status === 'CONSOLIDADO') diasConsolidados += 1
      if (dia.status === 'ABERTO') diasAbertos += 1

      tetoNormal += dia.teto_normal_min
      tetoExtra += dia.teto_extra_min
      apontadoNormal += dia.apontado_normal_min
      apontadoExtra += dia.apontado_extra_min
      ociosos += dia.minutos_ociosos

      lancamentosTotal.push(...dia.lancamentos)
      planejamentosTotal.push(...dia.planejamento)
    }

    return {
      tetoNormal,
      tetoExtra,
      apontadoNormal,
      apontadoExtra,
      ociosos,
      diasUteis,
      diasFeriado,
      diasIndisponivel,
      diasConsolidados,
      diasAbertos,
      lancamentos: lancamentosTotal,
      planejamentos: planejamentosTotal,
    }
  }, [selectedDates, getDiaData])

  function formatMinutos(min: number) {
    const h = Math.floor(min / 60)
    const m = min % 60
    if (h === 0) return `${m}min`
    if (m === 0) return `${h}h`
    return `${h}h ${m}min`
  }

  if (selectedDates.length === 0) {
    return (
      <Drawer open={open} onClose={onClose} title="Detalhes" width={440}>
        <div className={styles.emptyState}>
          <EmptyState
            icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>}
            title="Nenhum período selecionado"
            description="Clique em um dia ou arraste para selecionar"
          />
        </div>
      </Drawer>
    )
  }

  const botaoLancamentoHabilitado = Boolean(
    isSingleDay &&
    singleDayData &&
    onAddLancamento &&
    (podeAdicionarLancamento ? podeAdicionarLancamento(selectedDates[0], singleDayData) : singleDayData.status === 'ABERTO')
  )

  return (
    <Drawer open={open} onClose={onClose} title={drawerTitle} subtitle={drawerSubtitle} width={460}>
      {singleDayData && (
        <Drawer.Section>
          <div className={styles.statusRow}>
            <Badge variant={singleDayData.status === 'CONSOLIDADO' ? 'success' : 'default'}>{singleDayData.status}</Badge>
            {singleDayData.eh_feriado && <Badge variant="info">Feriado</Badge>}
            {singleDayData.eh_indisponivel && <Badge variant="warning">{singleDayData.tipo_indisponibilidade}</Badge>}
            {!singleDayData.eh_dia_util && !singleDayData.eh_feriado && <Badge variant="default">Fim de semana</Badge>}
          </div>
        </Drawer.Section>
      )}

      <Drawer.Section title="Resumo do período">
        <div className={styles.statsGrid}>
          <div className={styles.statItem}><StatCard label="Capacidade Normal" value={formatMinutos(agregado?.tetoNormal ?? 0)} variant="default" size="sm" /></div>
          <div className={styles.statItem}><StatCard label="Realizado Normal" value={formatMinutos(agregado?.apontadoNormal ?? 0)} variant="accent" size="sm" /></div>
          <div className={styles.statItem}><StatCard label="Hora Extra" value={formatMinutos(agregado?.apontadoExtra ?? 0)} variant="warning" size="sm" /></div>
          <div className={styles.statItem}><StatCard label="Ociosos" value={formatMinutos(agregado?.ociosos ?? 0)} variant={agregado?.ociosos && agregado.ociosos > 0 ? 'error' : 'default'} size="sm" /></div>
        </div>
      </Drawer.Section>

      {agregado && (
        <Drawer.Section title="Utilização">
          <CapacityBar normalValue={agregado.apontadoNormal} normalMax={agregado.tetoNormal} extraValue={agregado.apontadoExtra} extraMax={agregado.tetoExtra} size="lg" />
          <div className={styles.utilizacaoLegend}>
            <span className={styles.legendItem}><span className={styles.legendDot} style={{ background: 'var(--accent)' }} />Normal: {Math.round((agregado.apontadoNormal / Math.max(agregado.tetoNormal, 1)) * 100)}%</span>
            {agregado.apontadoExtra > 0 && <span className={styles.legendItem}><span className={styles.legendDot} style={{ background: 'var(--warn)' }} />Extra: {formatMinutos(agregado.apontadoExtra)}</span>}
          </div>
        </Drawer.Section>
      )}

      {exibirPlanejamento && agregado && agregado.planejamentos.length > 0 && (
        <Drawer.Section title={`${tituloPlanejamento} (${agregado.planejamentos.length})`}>
          <div className={styles.itemsList}>
            {agregado.planejamentos.slice(0, 8).map((p) => (
              <div key={p.id} className={styles.itemCard}>
                <div className={styles.itemHeader}>
                  <span className={styles.itemBloco}>{p.bloco_id ? `Bloco ${p.bloco_id}` : 'Sem bloco'}</span>
                  <span className={styles.itemMinutos}>{p.minutos_planejados_normais}min{p.minutos_planejados_extras > 0 && <span className={styles.itemExtra}>+{p.minutos_planejados_extras}</span>}</span>
                </div>
                {p.descricao && <p className={styles.itemDesc}>{p.descricao}</p>}
              </div>
            ))}
          </div>
        </Drawer.Section>
      )}

      {agregado && agregado.lancamentos.length > 0 && (
        <Drawer.Section title={`${tituloLancamentos} (${agregado.lancamentos.length})`}>
          <div className={styles.itemsList}>
            {agregado.lancamentos.slice(0, 8).map((l) => (
              <div key={l.id} className={`${styles.itemCard} ${styles.itemCardClickable}`} onClick={() => onEditLancamento?.(l.id)}>
                <div className={styles.itemHeader}>
                  <span className={styles.itemTipo}>
                    <span className={styles.tipoIcon} style={{ color: l.tipo_atividade_cor ?? 'var(--accent)' }}>●</span>
                    {l.usuario_nome ? `${l.usuario_nome} • ` : ''}{l.tipo_atividade_nome ?? l.tipo_atividade}
                  </span>
                  <span className={`${styles.itemMinutos} ${l.faixa === 'EXTRA' ? styles.itemExtra : ''}`}>{l.minutos}min{l.faixa === 'EXTRA' && <Badge variant="warning" size="sm">HE</Badge>}</span>
                </div>
                {l.descricao && <p className={styles.itemDesc}>{l.descricao}</p>}
              </div>
            ))}
          </div>
        </Drawer.Section>
      )}

      {!isSingleDay && agregado && (
        <Drawer.Section title="Composição do período">
          <div className={styles.periodoInfo}>
            <div className={styles.periodoItem}><span className={styles.periodoLabel}>Dias úteis</span><span className={styles.periodoValue}>{agregado.diasUteis}</span></div>
            {agregado.diasFeriado > 0 && <div className={styles.periodoItem}><span className={styles.periodoLabel}>Feriados</span><span className={styles.periodoValue}>{agregado.diasFeriado}</span></div>}
            <div className={styles.periodoItem}><span className={styles.periodoLabel}>Abertos</span><span className={styles.periodoValue}>{agregado.diasAbertos}</span></div>
            <div className={styles.periodoItem}><span className={styles.periodoLabel}>Consolidados</span><span className={styles.periodoValue}>{agregado.diasConsolidados}</span></div>
          </div>
        </Drawer.Section>
      )}

      <Drawer.Footer>
        {botaoLancamentoHabilitado && (
          <Button variant="secondary" size="sm" onClick={() => onAddLancamento?.(selectedDates[0])}>+ Lançamento</Button>
        )}
        {isAdmin && isSingleDay && singleDayData && exibirPlanejamento && singleDayData.status === 'ABERTO' && onAddPlanejamento && (
          <Button variant="secondary" size="sm" onClick={() => onAddPlanejamento?.(selectedDates[0])}>+ Planejamento</Button>
        )}
        {isAdmin && agregado && agregado.diasAbertos > 0 && onConsolidar && <Button variant="primary" size="sm" onClick={onConsolidar}>Consolidar período</Button>}
      </Drawer.Footer>
    </Drawer>
  )
}
