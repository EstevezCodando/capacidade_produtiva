// ============================================================
// useCalendarNavigation — Hook para controle de navegação temporal
// ============================================================
import { useState, useCallback, useMemo } from 'react'
import {
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  addMonths,
  subMonths,
  addWeeks,
  subWeeks,
  addDays,
  subDays,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  isWeekend,
  eachDayOfInterval,
  startOfDay,
} from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { CalendarView, CalendarDay, DateRange, DiaDaAgenda } from '@/types/agenda'

interface UseCalendarNavigationOptions {
  initialDate?: Date
  initialView?: CalendarView
  weekStartsOn?: 0 | 1 | 2 | 3 | 4 | 5 | 6
}

export function useCalendarNavigation(options: UseCalendarNavigationOptions = {}) {
  const { 
    initialDate = new Date(), 
    initialView = 'month',
    weekStartsOn = 1 // Segunda-feira
  } = options

  const [currentDate, setCurrentDate] = useState(startOfDay(initialDate))
  const [view, setView] = useState<CalendarView>(initialView)
  const [selectedDates, setSelectedDates] = useState<Date[]>([])

  // Range do período atual baseado na view
  const dateRange = useMemo((): DateRange => {
    switch (view) {
      case 'day':
        return { start: currentDate, end: currentDate }
      case 'week':
        return {
          start: startOfWeek(currentDate, { weekStartsOn }),
          end: endOfWeek(currentDate, { weekStartsOn }),
        }
      case 'month':
      default:
        return {
          start: startOfMonth(currentDate),
          end: endOfMonth(currentDate),
        }
    }
  }, [currentDate, view, weekStartsOn])

  // Dias do calendário (incluindo dias de meses adjacentes para preencher grid)
  const calendarDays = useMemo((): CalendarDay[] => {
    const monthStart = startOfMonth(currentDate)
    const monthEnd = endOfMonth(currentDate)
    const calStart = startOfWeek(monthStart, { weekStartsOn })
    const calEnd = endOfWeek(monthEnd, { weekStartsOn })

    return eachDayOfInterval({ start: calStart, end: calEnd }).map((date) => ({
      date,
      isCurrentMonth: isSameMonth(date, currentDate),
      isToday: isToday(date),
      isWeekend: isWeekend(date),
    }))
  }, [currentDate, weekStartsOn])

  // Dias da semana para header
  const weekDays = useMemo(() => {
    const start = startOfWeek(new Date(), { weekStartsOn })
    return eachDayOfInterval({ start, end: addDays(start, 6) }).map((date) => ({
      short: format(date, 'EEE', { locale: ptBR }),
      full: format(date, 'EEEE', { locale: ptBR }),
    }))
  }, [weekStartsOn])

  // Label do período atual
  const periodLabel = useMemo(() => {
    switch (view) {
      case 'day':
        return format(currentDate, "d 'de' MMMM 'de' yyyy", { locale: ptBR })
      case 'week':
        const weekStart = startOfWeek(currentDate, { weekStartsOn })
        const weekEnd = endOfWeek(currentDate, { weekStartsOn })
        return `${format(weekStart, 'd MMM', { locale: ptBR })} — ${format(weekEnd, "d MMM yyyy", { locale: ptBR })}`
      case 'month':
      default:
        return format(currentDate, "MMMM 'de' yyyy", { locale: ptBR })
    }
  }, [currentDate, view, weekStartsOn])

  // Navegação
  const goToNext = useCallback(() => {
    setCurrentDate((date) => {
      switch (view) {
        case 'day': return addDays(date, 1)
        case 'week': return addWeeks(date, 1)
        case 'month': return addMonths(date, 1)
        default: return addMonths(date, 1)
      }
    })
  }, [view])

  const goToPrev = useCallback(() => {
    setCurrentDate((date) => {
      switch (view) {
        case 'day': return subDays(date, 1)
        case 'week': return subWeeks(date, 1)
        case 'month': return subMonths(date, 1)
        default: return subMonths(date, 1)
      }
    })
  }, [view])

  const goToToday = useCallback(() => {
    setCurrentDate(startOfDay(new Date()))
  }, [])

  const goToDate = useCallback((date: Date) => {
    setCurrentDate(startOfDay(date))
  }, [])

  // Seleção de datas
  const selectDate = useCallback((date: Date, addToSelection = false) => {
    if (addToSelection) {
      setSelectedDates((prev) => {
        const exists = prev.some((d) => isSameDay(d, date))
        if (exists) {
          return prev.filter((d) => !isSameDay(d, date))
        }
        return [...prev, date].sort((a, b) => a.getTime() - b.getTime())
      })
    } else {
      setSelectedDates([date])
    }
  }, [])

  const selectRange = useCallback((start: Date, end: Date) => {
    const days = eachDayOfInterval({
      start: start < end ? start : end,
      end: start < end ? end : start,
    })
    setSelectedDates(days)
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedDates([])
  }, [])

  const isSelected = useCallback((date: Date) => {
    return selectedDates.some((d) => isSameDay(d, date))
  }, [selectedDates])

  // Range selecionado (para API calls)
  const selectedRange = useMemo((): DateRange | null => {
    if (selectedDates.length === 0) return null
    const sorted = [...selectedDates].sort((a, b) => a.getTime() - b.getTime())
    return {
      start: sorted[0],
      end: sorted[sorted.length - 1],
    }
  }, [selectedDates])

  // Formatar datas para API (YYYY-MM-DD)
  const formatForApi = useCallback((date: Date) => {
    return format(date, 'yyyy-MM-dd')
  }, [])

  return {
    // Estado
    currentDate,
    view,
    selectedDates,
    selectedRange,
    
    // Dados computados
    dateRange,
    calendarDays,
    weekDays,
    periodLabel,
    
    // Navegação
    goToNext,
    goToPrev,
    goToToday,
    goToDate,
    setView,
    
    // Seleção
    selectDate,
    selectRange,
    clearSelection,
    isSelected,
    
    // Utilitários
    formatForApi,
  }
}

// ============================================================
// useAgendaData — Hook para carregar dados da agenda
// ============================================================
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  getMeuPlanejamento,
  getAgendaUsuario,
  getMeuPeriodo,
  getCapacidadeUsuario,
  getFeriados,
} from '@/api/agenda'

interface UseAgendaDataOptions {
  usuarioId?: number
  isAdmin?: boolean
  dataInicio: string
  dataFim: string
  blocoId?: number
  enabled?: boolean
}

export function useAgendaData(options: UseAgendaDataOptions) {
  const {
    usuarioId,
    isAdmin = false,
    dataInicio,
    dataFim,
    blocoId,
    enabled = true,
  } = options

  const queryClient = useQueryClient()

  // Query de agenda completa
  const agendaQuery = useQuery({
    queryKey: ['agenda', usuarioId, dataInicio, dataFim],
    queryFn: () => {
      if (isAdmin && usuarioId) {
        return getAgendaUsuario(usuarioId, dataInicio, dataFim)
      }
      return getMeuPlanejamento(dataInicio, dataFim)
    },
    enabled: enabled && !!dataInicio && !!dataFim,
    staleTime: 30_000,
  })

  // Query de capacidade/resumo do período
  const capacidadeQuery = useQuery({
    queryKey: ['capacidade', usuarioId, dataInicio, dataFim, blocoId],
    queryFn: async () => {
      try {
        if (isAdmin && usuarioId) {
          return await getCapacidadeUsuario(usuarioId, dataInicio, dataFim, blocoId)
        }
        return await getMeuPeriodo(dataInicio, dataFim, blocoId)
      } catch {
        return null
      }
    },
    enabled: enabled && !!dataInicio && !!dataFim,
    staleTime: 30_000,
  })

  // Query de feriados
  const feriadosQuery = useQuery({
    queryKey: ['feriados'],
    queryFn: getFeriados,
    staleTime: 5 * 60 * 1000, // 5 minutos
  })

  // Mapa de dados por dia para acesso rápido
  const diasMap = useMemo(() => {
    const map = new Map<string, DiaDaAgenda>()
    if (agendaQuery.data?.dias) {
      for (const dia of agendaQuery.data.dias) {
        map.set(dia.data, dia)
      }
    }
    return map
  }, [agendaQuery.data])

  // Função helper para obter dados de um dia
  const getDiaData = useCallback((date: Date): DiaDaAgenda | undefined => {
    const key = format(date, 'yyyy-MM-dd')
    return diasMap.get(key)
  }, [diasMap])

  // Invalidar queries
  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['agenda'] })
    void queryClient.invalidateQueries({ queryKey: ['capacidade'] })
  }, [queryClient])

  return {
    agenda: agendaQuery.data,
    capacidade: capacidadeQuery.data,
    feriados: feriadosQuery.data?.feriados ?? [],
    diasMap,
    getDiaData,
    isLoading: agendaQuery.isLoading || capacidadeQuery.isLoading,
    isError: agendaQuery.isError,
    error: agendaQuery.error,
    capacidadeError: capacidadeQuery.error,
    invalidate,
  }
}
