import {
    consolidarPeriodo,
    criarPlanejamentoLote,
    editarPlanejamento,
    getAgendaUsuario,
    getConfigTeto,
    getFeriados,
    getTiposAtividade,
    getUsuarios,
    removerPlanejamento,
    removerPlanejamentoLote,
} from "@/api/agenda";
import ConsolidacaoModal from "@/components/agenda/ConsolidacaoModal";
import CalendarGrid from "@/components/calendar/CalendarGrid";
import CalendarHeader from "@/components/calendar/CalendarHeader";
import {
    Button,
    Card,
    Input,
    Select,
    Skeleton,
    StatCard,
    Textarea,
} from "@/components/ui/Common";
import Modal from "@/components/ui/Modal";
import { useAuth } from "@/context/AuthContext";
import { useAgendaData, useCalendarNavigation } from "@/hooks/useCalendar";
import type {
    AgendaCompleta,
    TipoAtividade,
    UsuarioResumo,
} from "@/types/agenda";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { useEffect, useMemo, useRef, useState } from "react";
import styles from "./AgendaPage.module.css";

interface FormularioPlanejamento {
  tipoAtividadeId: string;
  tipoHorario: "NORMAL" | "EXTRA";
  unidadeTempo: "HORAS" | "MINUTOS";
  quantidade: string;
  descricao: string;
}

interface SegmentoBarraDia {
  cor: string;
  minutos: number;
  percentual?: number;
}

interface AtividadeDetalheDia {
  planejamentoId: number;
  usuarioId: number;
  data: string;
  descricao: string;
  minutos: number;
  faixa: "NORMAL" | "EXTRA";
  cor: string;
}

interface UsuarioResumoDia {
  usuarioId: number;
  nome: string;
  minutosPlanejados: number;
  minutosNormaisPlanejados: number;
  minutosExtrasPlanejados: number;
  capacidadeMaxima: number;
  atividades: AtividadeDetalheDia[];
  segmentos: SegmentoBarraDia[];
}

interface PlanejamentoEdicaoState {
  planejamentoId: number;
  usuarioId: number;
  usuarioNome: string;
  data: string;
  faixa: "NORMAL" | "EXTRA";
  minutos: number;
  descricao: string;
  capacidadeMaxima: number;
  totalNormalDia: number;
}

const ESTADO_INICIAL_FORM: FormularioPlanejamento = {
  tipoAtividadeId: "",
  tipoHorario: "NORMAL",
  unidadeTempo: "HORAS",
  quantidade: "1",
  descricao: "",
};

function obterNomeUsuario(usuario: UsuarioResumo): string {
  return usuario.nome_guerra?.trim() || usuario.nome;
}

function formatarHorasMinutos(minutos: number): string {
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  if (horas > 0 && resto > 0) return `${horas}h ${resto}min`;
  if (horas > 0) return `${horas}h`;
  return `${resto}min`;
}

function criarResumoUsuarioDia(
  usuarioId: number,
  nome: string,
  capacidadeMaxima: number,
): UsuarioResumoDia {
  return {
    usuarioId,
    nome,
    minutosPlanejados: 0,
    minutosNormaisPlanejados: 0,
    minutosExtrasPlanejados: 0,
    capacidadeMaxima,
    atividades: [],
    segmentos: [],
  };
}

function normalizarCorHex(cor?: string | null): string {
  const valor = (cor ?? "").trim().toUpperCase();
  if (/^#[0-9A-F]{6}$/.test(valor)) return valor;
  return "var(--accent)";
}

function extrairNomeTipoDaDescricao(descricao?: string | null): string | null {
  const texto = descricao?.trim();
  if (!texto) return null;
  const match = texto.match(/^\[([^\]]+)]/);
  return match?.[1]?.trim() || null;
}

function obterCorPlanejamento(
  planejamento: { bloco_id: number | null; descricao: string | null },
  tiposAtividade: TipoAtividade[],
): string {
  if (planejamento.bloco_id) {
    const tipoBloco = tiposAtividade.find(
      (item) =>
        item.origem === "BLOCO" && item.bloco_id === planejamento.bloco_id,
    );
    if (tipoBloco?.cor) return normalizarCorHex(tipoBloco.cor);
  }

  const nomeTipo = extrairNomeTipoDaDescricao(planejamento.descricao);
  if (nomeTipo) {
    const tipoDescricao = tiposAtividade.find(
      (item) => item.nome.trim().toLowerCase() === nomeTipo.toLowerCase(),
    );
    if (tipoDescricao?.cor) return normalizarCorHex(tipoDescricao.cor);
  }

  return "var(--accent)";
}

function acumularSegmento(
  segmentos: SegmentoBarraDia[],
  cor: string,
  minutos: number,
) {
  if (minutos <= 0) return;
  const corNormalizada = normalizarCorHex(cor);
  const existente = segmentos.find((item) => item.cor === corNormalizada);
  if (existente) {
    existente.minutos += minutos;
    return;
  }
  segmentos.push({ cor: corNormalizada, minutos });
}

function calcularSegmentosPercentuais(
  segmentos: SegmentoBarraDia[],
  capacidadeTotal: number,
): SegmentoBarraDia[] {
  if (capacidadeTotal <= 0 || segmentos.length === 0) return [];
  return segmentos
    .filter((segmento) => segmento.minutos > 0)
    .map((segmento) => ({
      ...segmento,
      percentual: Math.min(100, (segmento.minutos / capacidadeTotal) * 100),
    }));
}

function converterQuantidadeParaMinutos(
  unidadeTempo: "HORAS" | "MINUTOS",
  quantidade: number,
): number {
  return unidadeTempo === "HORAS" ? quantidade * 60 : quantidade;
}

function obterDescricaoOrigemTipo(tipo: TipoAtividade): string {
  if (tipo.origem === "BLOCO") return "Bloco de produção";
  if (tipo.grupo === "INDISPONIBILIDADE") return "Indisponibilidade";
  if (tipo.grupo === "AJUSTE") return "Ajuste administrativo";
  return "Tipo configurado";
}

export default function AgendaPrevista() {
  const queryClient = useQueryClient();
  const { ehAdmin, usuario } = useAuth();
  const calendar = useCalendarNavigation({ initialView: "month" });

  const [selectedUsuarioIds, setSelectedUsuarioIds] = useState<number[]>([]);
  const [usuariosOpen, setUsuariosOpen] = useState(false);
  const [planejamentoOpen, setPlanejamentoOpen] = useState(false);
  const [consolidacaoOpen, setConsolidacaoOpen] = useState(false);
  const [filtroUsuarios, setFiltroUsuarios] = useState("");
  const [diaDetalheSelecionado, setDiaDetalheSelecionado] =
    useState<Date | null>(null);
  const [form, setForm] = useState<FormularioPlanejamento>(ESTADO_INICIAL_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [planejamentoEmEdicao, setPlanejamentoEmEdicao] =
    useState<PlanejamentoEdicaoState | null>(null);
  const [edicaoMinutos, setEdicaoMinutos] = useState("");
  const [edicaoDescricao, setEdicaoDescricao] = useState("");
  const [edicaoErrors, setEdicaoErrors] = useState<Record<string, string>>({});
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const { data: usuarios = [], isLoading: loadingUsuarios } = useQuery({
    queryKey: ["usuarios"],
    queryFn: getUsuarios,
    enabled: ehAdmin,
    staleTime: 60_000,
  });

  const { data: tiposAtividadeResposta, isLoading: loadingTipos } = useQuery({
    queryKey: ["tipos-atividade"],
    queryFn: getTiposAtividade,
    staleTime: 60_000,
  });

  const { data: configTeto } = useQuery({
    queryKey: ["config-teto"],
    queryFn: getConfigTeto,
    staleTime: 60_000,
  });

  const { data: feriadosData } = useQuery({
    queryKey: ["feriados"],
    queryFn: getFeriados,
    staleTime: 300_000,
  });

  const tiposAtividade: TipoAtividade[] = useMemo(() => {
    if (Array.isArray(tiposAtividadeResposta))
      return tiposAtividadeResposta as TipoAtividade[];
    if (
      tiposAtividadeResposta &&
      Array.isArray(
        (tiposAtividadeResposta as { tipos?: TipoAtividade[] }).tipos,
      )
    ) {
      return (tiposAtividadeResposta as { tipos: TipoAtividade[] }).tipos;
    }
    return [];
  }, [tiposAtividadeResposta]);

  const usuariosSelecionados = useMemo(
    () => usuarios.filter((item) => selectedUsuarioIds.includes(item.id)),
    [usuarios, selectedUsuarioIds],
  );

  const usuariosFiltrados = useMemo(() => {
    const termo = filtroUsuarios.trim().toLowerCase();
    if (!termo) return usuarios;
    return usuarios.filter((item) => {
      const nomeCurto = obterNomeUsuario(item).toLowerCase();
      const nomeCompleto = item.nome.toLowerCase();
      return nomeCurto.includes(termo) || nomeCompleto.includes(termo);
    });
  }, [filtroUsuarios, usuarios]);

  const usuarioIdPrincipal = useMemo(() => {
    if (!ehAdmin) return usuario?.usuario_id;
    if (selectedUsuarioIds.length > 0) return selectedUsuarioIds[0];
    return usuario?.usuario_id;
  }, [ehAdmin, selectedUsuarioIds, usuario?.usuario_id]);

  const usuarioPrincipal = useMemo(
    () => usuarios.find((item) => item.id === usuarioIdPrincipal),
    [usuarios, usuarioIdPrincipal],
  );

  const { agenda, capacidade, getDiaData, isLoading, isError, invalidate } =
    useAgendaData({
      usuarioId: usuarioIdPrincipal,
      isAdmin: ehAdmin,
      dataInicio: calendar.formatForApi(calendar.dateRange.start),
      dataFim: calendar.formatForApi(calendar.dateRange.end),
      enabled: !!usuarioIdPrincipal,
    });

  const idsUsuariosPainel = useMemo(() => {
    if (ehAdmin) {
      if (selectedUsuarioIds.length > 0) return selectedUsuarioIds;
      return usuarioIdPrincipal ? [usuarioIdPrincipal] : [];
    }
    return usuario?.usuario_id ? [usuario.usuario_id] : [];
  }, [ehAdmin, selectedUsuarioIds, usuarioIdPrincipal, usuario?.usuario_id]);

  const agendasMultiplosUsuariosQuery = useQuery({
    queryKey: [
      "agenda-prevista-multiusuario",
      idsUsuariosPainel,
      calendar.dateRange.start.toISOString(),
      calendar.dateRange.end.toISOString(),
      ehAdmin,
    ],
    queryFn: async (): Promise<AgendaCompleta[]> => {
      if (!idsUsuariosPainel.length) return [];
      if (!ehAdmin) return agenda ? [agenda] : [];
      const resultados = await Promise.allSettled(
        idsUsuariosPainel.map((usuarioId) =>
          getAgendaUsuario(
            usuarioId,
            calendar.formatForApi(calendar.dateRange.start),
            calendar.formatForApi(calendar.dateRange.end),
          ),
        ),
      );
      return resultados
        .filter(
          (resultado): resultado is PromiseFulfilledResult<AgendaCompleta> =>
            resultado.status === "fulfilled",
        )
        .map((resultado) => resultado.value);
    },
    enabled: idsUsuariosPainel.length > 0 && (!!agenda || ehAdmin),
    staleTime: 30_000,
  });

  const resumoPeriodo = capacidade?.resumo;
  const capacidadePadraoMinutos = configTeto?.teto_normal_min ?? 360;
  const diasSelecionados = calendar.selectedDates.length;

  const feriadosDatas = useMemo(
    () => feriadosData?.feriados.map((f) => f.data) ?? [],
    [feriadosData],
  );

  const diasComPlanejamento = useMemo(() => {
    const set = new Set<string>();
    if (agenda?.dias) {
      for (const d of agenda.dias) {
        if (d.planejamento.length > 0) set.add(d.data);
      }
    }
    return set;
  }, [agenda]);

  const intervaloSelecionado = useMemo(() => {
    if (calendar.selectedRange) return calendar.selectedRange;
    if (calendar.selectedDates.length === 1) {
      return {
        start: calendar.selectedDates[0],
        end: calendar.selectedDates[0],
      };
    }
    return null;
  }, [calendar.selectedDates, calendar.selectedRange]);

  const intervaloSelecionadoLabel = useMemo(() => {
    if (!intervaloSelecionado) return "Nenhum dia selecionado";
    const inicio = format(intervaloSelecionado.start, "dd/MM/yyyy");
    const fim = format(intervaloSelecionado.end, "dd/MM/yyyy");
    return inicio === fim ? inicio : `${inicio} até ${fim}`;
  }, [intervaloSelecionado]);

  const quantidadeDiasResumo = useMemo(() => {
    if (!intervaloSelecionado) return "0 dia";
    if (diasSelecionados === 1) return "1 dia";
    return `${diasSelecionados} dias`;
  }, [diasSelecionados, intervaloSelecionado]);

  const podeCriarPlanejamento =
    ehAdmin && selectedUsuarioIds.length > 0 && diasSelecionados >= 1;
  const podeConsolidar =
    ehAdmin && !!intervaloSelecionado && diasSelecionados >= 1;

  useEffect(() => {
    if (!ehAdmin) return;
    function handleClickFora(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setUsuariosOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, [ehAdmin]);

  function alternarUsuario(usuarioId: number) {
    setSelectedUsuarioIds((atual) => {
      if (atual.includes(usuarioId))
        return atual.filter((id) => id !== usuarioId);
      return [...atual, usuarioId].sort((a, b) => a - b);
    });
  }

  function limparSelecaoUsuarios() {
    setSelectedUsuarioIds([]);
  }

  function abrirPlanejamento() {
    setErrors({});
    setPlanejamentoOpen(true);
  }

  function resumoUsuariosSelecionados(): string {
    if (!selectedUsuarioIds.length) return "Selecione um ou mais usuários";
    if (usuariosSelecionados.length <= 2)
      return usuariosSelecionados.map(obterNomeUsuario).join(", ");
    return `${usuariosSelecionados.length} usuários selecionados`;
  }

  const mapaUsuariosPorId = useMemo(() => {
    const mapa = new Map<number, string>();
    for (const item of usuarios) {
      mapa.set(item.id, obterNomeUsuario(item));
    }
    if (usuario?.usuario_id) {
      mapa.set(
        usuario.usuario_id,
        usuario.nome_guerra || usuario.nome || "Usuário atual",
      );
    }
    return mapa;
  }, [usuarios, usuario]);

  const agendaDetalheUsuarios = useMemo(() => {
    if (ehAdmin) return agendasMultiplosUsuariosQuery.data ?? [];
    return agenda ? [agenda] : [];
  }, [agenda, agendasMultiplosUsuariosQuery.data, ehAdmin]);

  const detalhesPorDia = useMemo(() => {
    const mapa = new Map<string, UsuarioResumoDia[]>();
    const datasVisiveis = calendar.calendarDays.map((item) =>
      format(item.date, "yyyy-MM-dd"),
    );

    for (const data of datasVisiveis) {
      mapa.set(
        data,
        idsUsuariosPainel.map((usuarioId) =>
          criarResumoUsuarioDia(
            usuarioId,
            mapaUsuariosPorId.get(usuarioId) ?? `Usuário ${usuarioId}`,
            capacidadePadraoMinutos,
          ),
        ),
      );
    }

    for (const agendaUsuario of agendaDetalheUsuarios) {
      const nomeUsuario =
        mapaUsuariosPorId.get(agendaUsuario.usuario_id) ??
        `Usuário ${agendaUsuario.usuario_id}`;
      for (const dia of agendaUsuario.dias) {
        const listaDia = mapa.get(dia.data) ?? [];
        let resumoUsuario = listaDia.find(
          (item) => item.usuarioId === agendaUsuario.usuario_id,
        );
        if (!resumoUsuario) {
          resumoUsuario = criarResumoUsuarioDia(
            agendaUsuario.usuario_id,
            nomeUsuario,
            dia.teto_normal_min || capacidadePadraoMinutos,
          );
          listaDia.push(resumoUsuario);
        }

        resumoUsuario.capacidadeMaxima =
          dia.teto_normal_min || capacidadePadraoMinutos;

        for (const planejamento of dia.planejamento) {
          const corPlanejamento = obterCorPlanejamento(
            planejamento,
            tiposAtividade,
          );

          if (planejamento.minutos_planejados_normais > 0) {
            resumoUsuario.minutosNormaisPlanejados +=
              planejamento.minutos_planejados_normais;
            resumoUsuario.atividades.push({
              planejamentoId: planejamento.id,
              usuarioId: agendaUsuario.usuario_id,
              data: dia.data,
              descricao:
                planejamento.descricao?.trim() || "Planejamento administrativo",
              minutos: planejamento.minutos_planejados_normais,
              faixa: "NORMAL",
              cor: corPlanejamento,
            });
            acumularSegmento(
              resumoUsuario.segmentos,
              corPlanejamento,
              planejamento.minutos_planejados_normais,
            );
          }
          if (planejamento.minutos_planejados_extras > 0) {
            resumoUsuario.minutosExtrasPlanejados +=
              planejamento.minutos_planejados_extras;
            resumoUsuario.atividades.push({
              planejamentoId: planejamento.id,
              usuarioId: agendaUsuario.usuario_id,
              data: dia.data,
              descricao:
                planejamento.descricao?.trim() || "Planejamento administrativo",
              minutos: planejamento.minutos_planejados_extras,
              faixa: "EXTRA",
              cor: corPlanejamento,
            });
            acumularSegmento(
              resumoUsuario.segmentos,
              corPlanejamento,
              planejamento.minutos_planejados_extras,
            );
          }
        }

        resumoUsuario.minutosPlanejados =
          resumoUsuario.minutosNormaisPlanejados +
          resumoUsuario.minutosExtrasPlanejados;
        mapa.set(
          dia.data,
          [...listaDia].sort((a, b) => a.nome.localeCompare(b.nome)),
        );
      }
    }

    return mapa;
  }, [
    agendaDetalheUsuarios,
    calendar.calendarDays,
    capacidadePadraoMinutos,
    idsUsuariosPainel,
    mapaUsuariosPorId,
    tiposAtividade,
  ]);

  function obterResumoDiaUsuario(
    usuarioId: number,
    data: string,
  ): UsuarioResumoDia | undefined {
    return (detalhesPorDia.get(data) ?? []).find(
      (item) => item.usuarioId === usuarioId,
    );
  }

  const criarPlanejamentoMutation = useMutation({
    mutationFn: async () => {
      const novosErros: Record<string, string> = {};
      const quantidade = Number(form.quantidade);
      const minutosCalculados = converterQuantidadeParaMinutos(
        form.unidadeTempo,
        quantidade,
      );

      if (!form.tipoAtividadeId)
        novosErros.tipoAtividadeId = "Selecione um tipo de atividade.";
      if (!form.tipoHorario)
        novosErros.tipoHorario = "Selecione o tipo de horário.";
      if (!Number.isFinite(quantidade) || quantidade <= 0)
        novosErros.quantidade = "Informe uma quantidade válida.";
      if (calendar.selectedDates.length === 0)
        novosErros.periodo = "Selecione pelo menos um dia.";
      if (selectedUsuarioIds.length === 0)
        novosErros.usuarios = "Selecione ao menos um usuário.";

      if (
        form.tipoHorario === "NORMAL" &&
        Number.isFinite(minutosCalculados) &&
        minutosCalculados > 0
      ) {
        for (const usuarioId of selectedUsuarioIds) {
          const nomeUsuario =
            mapaUsuariosPorId.get(usuarioId) ?? `Usuário ${usuarioId}`;
          for (const dataSelecionada of calendar.selectedDates) {
            const dataChave = format(dataSelecionada, "yyyy-MM-dd");
            const resumoDia = obterResumoDiaUsuario(usuarioId, dataChave);
            const capacidadeDia =
              resumoDia?.capacidadeMaxima ?? capacidadePadraoMinutos;
            const normalJaPlanejado = resumoDia?.minutosNormaisPlanejados ?? 0;
            if (normalJaPlanejado + minutosCalculados > capacidadeDia) {
              novosErros.quantidade = `O usuário ${nomeUsuario} ultrapassa ${formatarHorasMinutos(capacidadeDia)} em ${format(dataSelecionada, "dd/MM/yyyy")}. O sistema só permite até 6h em horário normal.`;
              break;
            }
          }
          if (novosErros.quantidade) break;
        }
      }

      setErrors(novosErros);
      if (Object.keys(novosErros).length > 0) {
        throw new Error("Existem campos obrigatórios ou limites inválidos.");
      }

      const dias = calendar.selectedDates.map((data) =>
        format(data, "yyyy-MM-dd"),
      );
      const tipoSelecionado = tiposAtividade.find(
        (item) => item.id === Number(form.tipoAtividadeId),
      );
      const blocoSelecionadoId =
        tipoSelecionado?.origem === "BLOCO"
          ? (tipoSelecionado.bloco_id ?? null)
          : null;
      const descricaoComTipo =
        tipoSelecionado?.origem === "BLOCO"
          ? form.descricao.trim()
          : [
              tipoSelecionado?.nome ? `[${tipoSelecionado.nome}]` : "",
              form.descricao.trim(),
            ]
              .filter(Boolean)
              .join(" ");

      await criarPlanejamentoLote({
        usuario_ids: selectedUsuarioIds,
        datas: dias,
        bloco_id: blocoSelecionadoId,
        minutos_planejados_normais:
          form.tipoHorario === "NORMAL" ? minutosCalculados : 0,
        minutos_planejados_extras:
          form.tipoHorario === "EXTRA" ? minutosCalculados : 0,
        descricao: descricaoComTipo || undefined,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agenda"] });
      await queryClient.invalidateQueries({ queryKey: ["capacidade"] });
      await queryClient.invalidateQueries({
        queryKey: ["agenda-prevista-multiusuario"],
      });
      invalidate();
      setPlanejamentoOpen(false);
      setForm(ESTADO_INICIAL_FORM);
      setErrors({});
    },
    onError: (error) => {
      setErrors((atual) => ({
        ...atual,
        submit:
          error instanceof Error
            ? error.message
            : "Não foi possível criar o planejamento.",
      }));
    },
  });

  const consolidacaoCsvMutation = useMutation({
    mutationFn: async () => {
      if (!intervaloSelecionado)
        throw new Error("Selecione um período para consolidar.");
      return consolidarPeriodo({
        data_inicio: format(intervaloSelecionado.start, "yyyy-MM-dd"),
        data_fim: format(intervaloSelecionado.end, "yyyy-MM-dd"),
        usuarios_ids:
          selectedUsuarioIds.length > 0 ? selectedUsuarioIds : undefined,
        ignorar_pendencias: false,
      });
    },
    onSuccess: (resultado) => {
      if (!resultado.pendencias.length) {
        setConsolidacaoOpen(true);
        return;
      }

      const linhas = [
        ["usuario", "dia", "horas_faltantes"].join(","),
        ...resultado.pendencias.map((pendencia) =>
          [
            JSON.stringify(
              pendencia.usuario_nome ?? `Usuário ${pendencia.usuario_id}`,
            ),
            pendencia.data,
            JSON.stringify(pendencia.motivo),
          ].join(","),
        ),
      ];

      const blob = new Blob([linhas.join("\n")], {
        type: "text/csv;charset=utf-8;",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `pendencias-consolidacao-${format(new Date(), "yyyyMMdd-HHmmss")}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      setConsolidacaoOpen(true);
    },
  });

  const quantidadeMinutos = Number(form.quantidade || 0);
  const cargaPlanejadaLabel = useMemo(() => {
    if (!quantidadeMinutos || quantidadeMinutos < 1) return "Não definida";
    return formatarHorasMinutos(
      converterQuantidadeParaMinutos(form.unidadeTempo, quantidadeMinutos),
    );
  }, [form.unidadeTempo, quantidadeMinutos]);

  const dataDetalheSelecionadoChave = diaDetalheSelecionado
    ? format(diaDetalheSelecionado, "yyyy-MM-dd")
    : null;
  const detalhesDiaSelecionado = dataDetalheSelecionadoChave
    ? (detalhesPorDia.get(dataDetalheSelecionadoChave) ?? [])
    : [];

  const capacidadeVisualPorDia = useMemo(() => {
    const mapa = new Map<
      string,
      {
        totalMinutos: number;
        totalExtraMinutos: number;
        segmentos: SegmentoBarraDia[];
      }
    >();

    for (const [data, usuariosDia] of detalhesPorDia.entries()) {
      const capacidadeTotal = usuariosDia.reduce(
        (soma, item) => soma + item.capacidadeMaxima,
        0,
      );
      const minutosTotais = usuariosDia.reduce(
        (soma, item) => soma + item.minutosPlanejados,
        0,
      );
      const minutosExtrasTotais = usuariosDia.reduce(
        (soma, item) => soma + item.minutosExtrasPlanejados,
        0,
      );
      const segmentosAgrupados: SegmentoBarraDia[] = [];

      for (const usuarioDia of usuariosDia) {
        for (const segmento of usuarioDia.segmentos) {
          acumularSegmento(segmentosAgrupados, segmento.cor, segmento.minutos);
        }
      }

      mapa.set(data, {
        totalMinutos: minutosTotais,
        totalExtraMinutos: minutosExtrasTotais,
        segmentos: calcularSegmentosPercentuais(
          segmentosAgrupados,
          capacidadeTotal,
        ),
      });
    }

    return mapa;
  }, [detalhesPorDia]);

  const conteudoTooltipPorDia = useMemo(
    () => ({
      get: (date: Date) =>
        (detalhesPorDia.get(format(date, "yyyy-MM-dd")) ?? []).map((item) => ({
          usuarioId: item.usuarioId,
          nome: item.nome,
          minutosPlanejados: item.minutosPlanejados,
          capacidadeMaxima: item.capacidadeMaxima,
          segmentos: calcularSegmentosPercentuais(
            item.segmentos,
            item.capacidadeMaxima,
          ),
        })),
    }),
    [detalhesPorDia],
  );

  const tiposAtividadeOrdenados = useMemo(
    () => [...tiposAtividade].sort((a, b) => a.nome.localeCompare(b.nome)),
    [tiposAtividade],
  );

  const tiposAtividadePorGrupo = useMemo(() => {
    return {
      blocos: tiposAtividadeOrdenados.filter((tipo) => tipo.origem === "BLOCO"),
      tipos: tiposAtividadeOrdenados.filter((tipo) => tipo.origem !== "BLOCO"),
    };
  }, [tiposAtividadeOrdenados]);

  function abrirEdicaoAtividade(
    atividade: AtividadeDetalheDia,
    detalheUsuario: UsuarioResumoDia,
  ) {
    setEdicaoErrors({});
    setPlanejamentoEmEdicao({
      planejamentoId: atividade.planejamentoId,
      usuarioId: atividade.usuarioId,
      usuarioNome: detalheUsuario.nome,
      data: atividade.data,
      faixa: atividade.faixa,
      minutos: atividade.minutos,
      descricao: atividade.descricao,
      capacidadeMaxima: detalheUsuario.capacidadeMaxima,
      totalNormalDia: detalheUsuario.minutosNormaisPlanejados,
    });
    setEdicaoMinutos(String(atividade.minutos));
    setEdicaoDescricao(atividade.descricao);
  }

  const editarPlanejamentoMutation = useMutation({
    mutationFn: async () => {
      if (!planejamentoEmEdicao)
        throw new Error("Nenhum planejamento selecionado.");
      const novosErros: Record<string, string> = {};
      const minutos = Number(edicaoMinutos);

      if (!Number.isFinite(minutos) || minutos <= 0) {
        novosErros.minutos = "Informe uma quantidade válida de minutos.";
      }

      if (
        planejamentoEmEdicao.faixa === "NORMAL" &&
        Number.isFinite(minutos) &&
        minutos > 0
      ) {
        const capacidadePermitida = planejamentoEmEdicao.capacidadeMaxima;
        const totalSemItemAtual =
          planejamentoEmEdicao.totalNormalDia - planejamentoEmEdicao.minutos;
        if (totalSemItemAtual + minutos > capacidadePermitida) {
          novosErros.minutos = `Este ajuste ultrapassa ${formatarHorasMinutos(capacidadePermitida)} em horário normal. Reduza a atividade ou use hora extra em um novo lançamento.`;
        }
      }

      setEdicaoErrors(novosErros);
      if (Object.keys(novosErros).length > 0) {
        throw new Error("Existem erros no planejamento selecionado.");
      }

      return editarPlanejamento(planejamentoEmEdicao.planejamentoId, {
        minutos_planejados_normais:
          planejamentoEmEdicao.faixa === "NORMAL" ? minutos : undefined,
        minutos_planejados_extras:
          planejamentoEmEdicao.faixa === "EXTRA" ? minutos : undefined,
        descricao: edicaoDescricao.trim() || undefined,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agenda"] });
      await queryClient.invalidateQueries({ queryKey: ["capacidade"] });
      await queryClient.invalidateQueries({
        queryKey: ["agenda-prevista-multiusuario"],
      });
      invalidate();
      setPlanejamentoEmEdicao(null);
    },
    onError: (error) => {
      setEdicaoErrors((atual) => ({
        ...atual,
        submit:
          error instanceof Error
            ? error.message
            : "Não foi possível editar o planejamento.",
      }));
    },
  });

  const removerPlanejamentoMutation = useMutation({
    mutationFn: async () => {
      if (!planejamentoEmEdicao)
        throw new Error("Nenhum planejamento selecionado.");
      return removerPlanejamento(planejamentoEmEdicao.planejamentoId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agenda"] });
      await queryClient.invalidateQueries({ queryKey: ["capacidade"] });
      await queryClient.invalidateQueries({
        queryKey: ["agenda-prevista-multiusuario"],
      });
      invalidate();
      setPlanejamentoEmEdicao(null);
    },
    onError: (error) => {
      setEdicaoErrors((atual) => ({
        ...atual,
        submit:
          error instanceof Error
            ? error.message
            : "Não foi possível remover o planejamento.",
      }));
    },
  });

  const removerPlanejamentoLoteMutation = useMutation({
    mutationFn: async () => {
      if (selectedUsuarioIds.length === 0)
        throw new Error("Selecione ao menos um usuário.");
      if (calendar.selectedDates.length === 0)
        throw new Error("Selecione ao menos uma data.");
      return removerPlanejamentoLote({
        usuario_ids: selectedUsuarioIds,
        datas: calendar.selectedDates.map((data) => format(data, "yyyy-MM-dd")),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agenda"] });
      await queryClient.invalidateQueries({ queryKey: ["capacidade"] });
      await queryClient.invalidateQueries({
        queryKey: ["agenda-prevista-multiusuario"],
      });
      invalidate();
    },
    onError: (error) => {
      setErrors((atual) => ({
        ...atual,
        submit:
          error instanceof Error
            ? error.message
            : "Não foi possível remover os planejamentos selecionados.",
      }));
    },
  });

  return (
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h2 className={styles.sidebarTitle}>Agenda prevista</h2>
          <p className={styles.sidebarSubtitle}>
            Planejamento administrativo com leitura clara, filtros compactos e
            calendário sempre visível.
          </p>
        </div>

        {ehAdmin ? (
          <div className={styles.userSelector} ref={dropdownRef}>
            <div className={styles.sectionHeaderCompact}>
              <span className={styles.selectorLabel}>Usuários</span>
              {selectedUsuarioIds.length > 0 && (
                <button
                  type="button"
                  className={styles.clearLink}
                  onClick={limparSelecaoUsuarios}
                >
                  Limpar
                </button>
              )}
            </div>

            <button
              type="button"
              className={styles.userDropdownTrigger}
              onClick={() => setUsuariosOpen((atual) => !atual)}
              aria-expanded={usuariosOpen}
            >
              <div className={styles.userDropdownTriggerText}>
                <span className={styles.userDropdownTitle}>
                  {resumoUsuariosSelecionados()}
                </span>
                <span className={styles.userDropdownHint}>
                  Selecione por checkbox dentro do dropdown
                </span>
              </div>
              <span className={styles.userDropdownMeta}>
                {selectedUsuarioIds.length}
              </span>
            </button>

            {usuariosOpen && (
              <div className={styles.userDropdownMenu}>
                <Input
                  className={styles.userSearchInput}
                  placeholder="Buscar usuário"
                  value={filtroUsuarios}
                  onChange={(evento) => setFiltroUsuarios(evento.target.value)}
                />
                <div className={styles.userDropdownList}>
                  {loadingUsuarios ? (
                    <div className={styles.userDropdownLoading}>
                      Carregando usuários...
                    </div>
                  ) : usuariosFiltrados.length === 0 ? (
                    <div className={styles.userDropdownLoading}>
                      Nenhum usuário encontrado.
                    </div>
                  ) : (
                    usuariosFiltrados.map((item) => {
                      const nomeCurto = obterNomeUsuario(item);
                      const nomeCompleto = item.nome.trim();
                      const selecionado = selectedUsuarioIds.includes(item.id);
                      return (
                        <label
                          key={item.id}
                          className={`${styles.userOption} ${selecionado ? styles.userOptionSelected : ""}`}
                        >
                          <input
                            type="checkbox"
                            checked={selecionado}
                            onChange={() => alternarUsuario(item.id)}
                          />
                          <div className={styles.userOptionTextWrap}>
                            <span className={styles.userOptionText}>
                              {nomeCurto}
                            </span>
                            {nomeCompleto &&
                              nomeCompleto.toLowerCase() !==
                                nomeCurto.toLowerCase() && (
                                <span className={styles.userOptionSubtext}>
                                  {nomeCompleto}
                                </span>
                              )}
                          </div>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {usuariosSelecionados.length > 0 && (
              <div className={styles.selectedUsersPreview}>
                {usuariosSelecionados.map((item) => (
                  <span key={item.id} className={styles.userChip}>
                    {obterNomeUsuario(item)}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className={styles.userViewer}>
            <span className={styles.selectorLabel}>Usuário</span>
            <div className={styles.userViewerCard}>
              {usuario?.nome_guerra || usuario?.nome || "Usuário atual"}
            </div>
          </div>
        )}

        <div className={styles.summaryCards}>
          {isLoading ? (
            <>
              <Skeleton height={92} />
              <Skeleton height={92} />
              <Skeleton height={92} />
              <Skeleton height={92} />
            </>
          ) : (
            <>
              <Card padding="sm">
                <StatCard
                  label="Previsto normal"
                  value={resumoPeriodo?.minutos_previstos_normais ?? 0}
                  suffix="min"
                  variant="default"
                  size="sm"
                />
              </Card>
              <Card padding="sm">
                <StatCard
                  label="Realizado em bloco"
                  value={resumoPeriodo?.minutos_realizados_bloco_normais ?? 0}
                  suffix="min"
                  variant="accent"
                  size="sm"
                />
              </Card>
              <Card padding="sm">
                <StatCard
                  label="Horas extras"
                  value={resumoPeriodo?.minutos_extras_totais ?? 0}
                  suffix="min"
                  variant="warning"
                  size="sm"
                />
              </Card>
              <Card padding="sm">
                <StatCard
                  label="Capacidade diária"
                  value={formatarHorasMinutos(capacidadePadraoMinutos)}
                  variant="default"
                  size="sm"
                />
              </Card>
            </>
          )}
        </div>

        <div className={styles.legend}>
          <div className={styles.legendHeader}>
            <div>
              <h4 className={styles.legendTitle}>Contexto exibido</h4>
              <p className={styles.legendSubtitle}>
                A agenda combina capacidade do dia com a paleta real das
                atividades configuradas pelo administrador.
              </p>
            </div>
            <span className={styles.legendBadge}>
              {tiposAtividade.length} atividades
            </span>
          </div>

          <div className={styles.activityPaletteSection}>
            <div className={styles.activityPaletteHeader}>
              <span className={styles.activityPaletteTitle}>
                Cores das atividades
              </span>
              <span className={styles.activityPaletteMeta}>
                Legenda operacional
              </span>
            </div>

            {loadingTipos ? (
              <div className={styles.activityPaletteEmpty}>
                Carregando atividades configuradas...
              </div>
            ) : tiposAtividade.length === 0 ? (
              <div className={styles.activityPaletteEmpty}>
                Nenhuma atividade configurada encontrada.
              </div>
            ) : (
              <>
                {tiposAtividadePorGrupo.blocos.length > 0 && (
                  <div className={styles.activityPaletteGroup}>
                    <div className={styles.activityPaletteGroupTitle}>
                      Blocos de produção
                    </div>
                    <div className={styles.activityPaletteGrid}>
                      {tiposAtividadePorGrupo.blocos.map((tipo) => (
                        <article
                          key={tipo.id}
                          className={styles.activityPaletteCard}
                        >
                          <span
                            className={styles.activityPaletteSwatch}
                            style={{ background: normalizarCorHex(tipo.cor) }}
                          />
                          <div className={styles.activityPaletteContent}>
                            <span className={styles.activityPaletteName}>
                              {tipo.nome}
                            </span>
                            <span className={styles.activityPaletteDescription}>
                              {obterDescricaoOrigemTipo(tipo)}
                            </span>
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                )}

                {tiposAtividadePorGrupo.tipos.length > 0 && (
                  <div className={styles.activityPaletteGroup}>
                    <div className={styles.activityPaletteGroupTitle}>
                      Demais atividades selecionáveis
                    </div>
                    <div className={styles.activityPaletteGrid}>
                      {tiposAtividadePorGrupo.tipos.map((tipo) => (
                        <article
                          key={tipo.id}
                          className={styles.activityPaletteCard}
                        >
                          <span
                            className={styles.activityPaletteSwatch}
                            style={{ background: normalizarCorHex(tipo.cor) }}
                          />
                          <div className={styles.activityPaletteContent}>
                            <span className={styles.activityPaletteName}>
                              {tipo.nome}
                            </span>
                            <span className={styles.activityPaletteDescription}>
                              {obterDescricaoOrigemTipo(tipo)}
                            </span>
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {ehAdmin && usuarioPrincipal && (
            <p className={styles.renderHint}>
              Passe o mouse sobre um dia para ver a carga de cada usuário
              selecionado. Ao clicar, a lateral mostra os lançamentos acumulados
              do dia e as ações só aparecem quando você abre uma atividade
              específica.
            </p>
          )}
        </div>
      </aside>

      <main className={styles.main}>
        <div className={styles.topActionsBar}>
          <div>
            <h3 className={styles.topActionsTitle}>Planejamento do período</h3>
            <p className={styles.topActionsSubtitle}>
              Novos lançamentos são somados ao que já existe. Em horário normal,
              o sistema limita a carga diária a 6 horas por usuário.
            </p>
          </div>
          {ehAdmin && (
            <div className={styles.topActionsButtons}>
              <Button
                variant="secondary"
                onClick={() => {
                  setConsolidacaoOpen(true);
                  void consolidacaoCsvMutation
                    .mutateAsync()
                    .catch(() => undefined);
                }}
                disabled={!podeConsolidar}
              >
                Consolidar período
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  void removerPlanejamentoLoteMutation
                    .mutateAsync()
                    .catch(() => undefined);
                }}
                disabled={
                  !(
                    ehAdmin &&
                    selectedUsuarioIds.length > 0 &&
                    calendar.selectedDates.length > 0
                  )
                }
                loading={removerPlanejamentoLoteMutation.isPending}
              >
                Remover selecionados
              </Button>
              <Button
                variant="primary"
                onClick={abrirPlanejamento}
                disabled={!podeCriarPlanejamento}
              >
                Criar planejamento
              </Button>
            </div>
          )}
        </div>

        <div className={styles.selectionSummary}>
          <div className={styles.selectionPill}>
            <strong>Período</strong>
            <span>{intervaloSelecionadoLabel}</span>
          </div>
          <div className={styles.selectionPill}>
            <strong>Dias</strong>
            <span>{quantidadeDiasResumo}</span>
          </div>
          {ehAdmin && (
            <div className={styles.selectionPill}>
              <strong>Usuários</strong>
              <span>{selectedUsuarioIds.length || "0"}</span>
            </div>
          )}
        </div>

        <CalendarHeader
          periodLabel={calendar.periodLabel}
          view={calendar.view}
          onViewChange={calendar.setView}
          onPrev={calendar.goToPrev}
          onNext={calendar.goToNext}
          onToday={calendar.goToToday}
          loading={isLoading}
        />

        {/* Barra de seleção rápida */}
        <div className={styles.quickSelectBar}>
          <button
            type="button"
            className={styles.quickSelectBtn}
            onClick={() => calendar.selectDiasUteisDoMes(feriadosDatas)}
            title="Selecionar todos os dias úteis do mês"
          >
            Mês inteiro
          </button>
          {calendar.selectedDates.length > 0 && (
            <>
              <span className={styles.quickSelectCount}>
                {calendar.selectedDates.length} dia{calendar.selectedDates.length !== 1 ? "s" : ""} selecionado{calendar.selectedDates.length !== 1 ? "s" : ""}
              </span>
              <button
                type="button"
                className={`${styles.quickSelectBtn} ${styles.quickSelectClear}`}
                onClick={calendar.clearSelection}
              >
                Limpar
              </button>
            </>
          )}
        </div>

        <div className={styles.calendarWorkspace}>
          <div className={styles.calendarContainer}>
            {isError ? (
              <div className={styles.errorState}>
                <p>Erro ao carregar dados da agenda.</p>
              </div>
            ) : (
              <CalendarGrid
                days={calendar.calendarDays}
                weekDays={calendar.weekDays}
                view={calendar.view}
                getDiaData={getDiaData}
                getHoverUsuarios={(date) =>
                  (conteudoTooltipPorDia.get(date) ?? []).map((u) => ({
                    ...u,
                    segmentos: u.segmentos?.map((s) => ({
                      ...s,
                      percentual: s.percentual ?? 0,
                    })),
                  }))
                }
                getCapacityDisplay={(date) => {
                  const d = capacidadeVisualPorDia.get(format(date, "yyyy-MM-dd"));
                  if (!d) return null;
                  return {
                    ...d,
                    segmentos: d.segmentos.map((s) => ({
                      ...s,
                      percentual: s.percentual ?? 0,
                    })),
                  };
                }}
                selectedDates={calendar.selectedDates}
                onSelectDate={calendar.selectDate}
                onSelectRange={(start, end) =>
                  calendar.selectRangeDiasUteis(start, end, feriadosDatas)
                }
                onDayClick={(date) => {
                  calendar.selectDate(date);
                  setDiaDetalheSelecionado(date);
                }}
                feriados={feriadosDatas}
                isAdmin={ehAdmin}
                loading={isLoading || agendasMultiplosUsuariosQuery.isLoading}
                exibirIndicadorOcioso={
                  !ehAdmin || selectedUsuarioIds.length > 0
                }
              />
            )}
          </div>

          <aside className={styles.dayDetailsPanel}>
            <div className={styles.dayDetailsHeader}>
              <span className={styles.selectorLabel}>Detalhe do dia</span>
              <h4 className={styles.dayDetailsTitle}>
                {diaDetalheSelecionado
                  ? format(diaDetalheSelecionado, "dd/MM/yyyy")
                  : "Selecione um dia"}
              </h4>
              <p className={styles.dayDetailsSubtitle}>
                {diaDetalheSelecionado
                  ? "Resumo compacto dos usuários e atividades do dia."
                  : "Clique em uma célula da agenda para abrir o detalhamento lateral."}
              </p>
            </div>

            {diaDetalheSelecionado ? (
              <div className={styles.dayDetailsContent}>
                {detalhesDiaSelecionado.length > 0 ? (
                  detalhesDiaSelecionado.map((detalheUsuario) => {
                    const percentual =
                      detalheUsuario.capacidadeMaxima > 0
                        ? Math.min(
                            100,
                            (detalheUsuario.minutosPlanejados /
                              detalheUsuario.capacidadeMaxima) *
                              100,
                          )
                        : 0;
                    return (
                      <section
                        key={`${detalheUsuario.usuarioId}-${dataDetalheSelecionadoChave}`}
                        className={styles.dayUserCard}
                      >
                        <div className={styles.dayUserHeader}>
                          <div>
                            <h5 className={styles.dayUserName}>
                              {detalheUsuario.nome}
                            </h5>
                            <p className={styles.dayUserMeta}>
                              {percentual}% da capacidade ocupada · {formatarHorasMinutos(
                                detalheUsuario.capacidadeMaxima,
                              )} disponíveis
                            </p>
                          </div>
                          <span className={styles.dayUserTotal}>
                            {formatarHorasMinutos(
                              detalheUsuario.minutosPlanejados,
                            )}
                          </span>
                        </div>

                        <div className={styles.dayUserBarTrack}>
                          {calcularSegmentosPercentuais(
                            detalheUsuario.segmentos,
                            detalheUsuario.capacidadeMaxima,
                          ).map((segmento, index) => (
                            <div
                              key={`${detalheUsuario.usuarioId}-${index}-${segmento.cor}`}
                              className={styles.dayUserBarFill}
                              style={{
                                width: `${segmento.percentual ?? 0}%`,
                                background: segmento.cor,
                              }}
                            />
                          ))}
                          {percentual === 0 && (
                            <div
                              className={styles.dayUserBarFill}
                              style={{ width: "0%" }}
                            />
                          )}
                        </div>

                        <div className={styles.dayUserMetricsRow}>
                          <span className={styles.dayMetricPill}>
                            Normal:{" "}
                            {formatarHorasMinutos(
                              detalheUsuario.minutosNormaisPlanejados,
                            )}
                          </span>
                          <span className={styles.dayMetricPill}>
                            Extra:{" "}
                            {formatarHorasMinutos(
                              detalheUsuario.minutosExtrasPlanejados,
                            )}
                          </span>
                        </div>

                        <div className={styles.dayActivitiesList}>
                          {detalheUsuario.atividades.length > 0 ? (
                            detalheUsuario.atividades.map((atividade) => (
                              <article
                                key={`${atividade.planejamentoId}-${atividade.faixa}`}
                                className={`${styles.dayActivityItem} ${ehAdmin ? styles.dayActivityItemInteractive : ""}`}
                                onClick={
                                  ehAdmin
                                    ? () =>
                                        abrirEdicaoAtividade(
                                          atividade,
                                          detalheUsuario,
                                        )
                                    : undefined
                                }
                              >
                                <div className={styles.dayActivityInfo}>
                                  <div className={styles.dayActivityTitle}>
                                    <span
                                      className={styles.dayActivityColorDot}
                                      style={{ background: atividade.cor }}
                                    />
                                    <span className={styles.dayActivityTitleText}>
                                      {atividade.descricao}
                                    </span>
                                  </div>
                                  <div className={styles.dayActivityMeta}>
                                    {atividade.faixa === "NORMAL"
                                      ? "Normal"
                                      : "Hora extra"}{" "}
                                    · {formatarHorasMinutos(atividade.minutos)}
                                  </div>
                                </div>
                                {ehAdmin && (
                                  <span className={styles.dayActivityAction}>
                                    Editar
                                  </span>
                                )}
                              </article>
                            ))
                          ) : (
                            <div className={styles.dayEmptyState}>
                              Nenhuma atividade planejada.
                            </div>
                          )}
                        </div>
                      </section>
                    );
                  })
                ) : (
                  <div className={styles.dayDetailsEmpty}>
                    Nenhum dado encontrado para o dia selecionado.
                  </div>
                )}
              </div>
            ) : (
              <div className={styles.dayDetailsEmpty}>
                Nenhum dia selecionado ainda.
              </div>
            )}
          </aside>
        </div>
      </main>

      <Modal
        open={planejamentoOpen}
        onClose={() => setPlanejamentoOpen(false)}
        title="Criar planejamento"
        size="xl"
      >
        <form
          className={styles.planejamentoForm}
          onSubmit={(evento) => {
            evento.preventDefault();
            criarPlanejamentoMutation.mutate();
          }}
        >
          <section className={styles.modalSection}>
            <div className={styles.modalSectionHeader}>
              <h4 className={styles.modalSectionTitle}>
                Configuração da atividade
              </h4>
              <p className={styles.modalSectionSubtitle}>
                Defina tipo, faixa de horário e quantidade de tempo com
                alinhamento consistente.
              </p>
            </div>

            <div className={styles.formGrid}>
              <div className={styles.formField}>
                <label className={styles.formLabel}>Tipo de atividade</label>
                <Select
                  value={form.tipoAtividadeId}
                  onChange={(valor) =>
                    setForm((atual) => ({ ...atual, tipoAtividadeId: valor }))
                  }
                  options={tiposAtividade.map((tipo) => ({
                    value: String(tipo.id),
                    label: tipo.nome,
                  }))}
                  placeholder={loadingTipos ? "Carregando..." : "Selecione"}
                />
                {errors.tipoAtividadeId && (
                  <span className={styles.formError}>
                    {errors.tipoAtividadeId}
                  </span>
                )}
              </div>

              <div className={styles.formField}>
                <label className={styles.formLabel}>Tipo de horário</label>
                <Select
                  value={form.tipoHorario}
                  onChange={(valor) =>
                    setForm((atual) => ({
                      ...atual,
                      tipoHorario: valor as "NORMAL" | "EXTRA",
                    }))
                  }
                  options={[
                    { value: "NORMAL", label: "Normal" },
                    { value: "EXTRA", label: "Hora extra" },
                  ]}
                />
                {errors.tipoHorario && (
                  <span className={styles.formError}>{errors.tipoHorario}</span>
                )}
              </div>

              <div className={styles.formField}>
                <label className={styles.formLabel}>Unidade do tempo</label>
                <Select
                  value={form.unidadeTempo}
                  onChange={(valor) =>
                    setForm((atual) => ({
                      ...atual,
                      unidadeTempo: valor as "HORAS" | "MINUTOS",
                    }))
                  }
                  options={[
                    { value: "HORAS", label: "Horas" },
                    { value: "MINUTOS", label: "Minutos" },
                  ]}
                />
              </div>

              <div className={styles.formField}>
                <Input
                  label="Quantidade"
                  type="number"
                  min="1"
                  step="1"
                  value={form.quantidade}
                  onChange={(evento) =>
                    setForm((atual) => ({
                      ...atual,
                      quantidade: evento.target.value,
                    }))
                  }
                  error={errors.quantidade}
                />
              </div>
            </div>
          </section>

          <section className={styles.modalSection}>
            <div className={styles.modalSectionHeader}>
              <h4 className={styles.modalSectionTitle}>Descrição</h4>
              <p className={styles.modalSectionSubtitle}>
                Use este campo para dar contexto ao planejamento e facilitar a
                leitura futura.
              </p>
            </div>
            <Textarea
              label="Descrição opcional"
              rows={5}
              value={form.descricao}
              onChange={(evento) =>
                setForm((atual) => ({
                  ...atual,
                  descricao: evento.target.value,
                }))
              }
              placeholder="Ex.: apoio ao processamento, afastamento, treinamento interno, atividade administrativa"
            />
          </section>
          <section className={styles.modalSection}>
            <div className={styles.modalSectionHeader}>
              <h4 className={styles.modalSectionTitle}>Resumo do lançamento</h4>
              <p className={styles.modalSectionSubtitle}>
                Cada novo lançamento será somado ao que já existe no dia.
                Horário normal respeita o teto diário de 6 horas.
              </p>
            </div>

            <div className={styles.infoGrid}>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>Período selecionado</span>
                <strong>{intervaloSelecionadoLabel}</strong>
                <span className={styles.infoDetail}>
                  Seleção atual do calendário
                </span>
              </div>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>Dias</span>
                <strong>{quantidadeDiasResumo}</strong>
                <span className={styles.infoDetail}>
                  Aceita lançamento em apenas um dia
                </span>
              </div>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>Usuários</span>
                <strong>{selectedUsuarioIds.length}</strong>
                <span className={styles.infoDetail}>
                  Aplicação simultânea para todos os selecionados
                </span>
              </div>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>Carga por dia</span>
                <strong>{cargaPlanejadaLabel}</strong>
                <span className={styles.infoDetail}>
                  Capacidade padrão:{" "}
                  {formatarHorasMinutos(capacidadePadraoMinutos)}
                </span>
              </div>
            </div>

            <div className={styles.chipsWrap}>
              {usuariosSelecionados.length > 0 ? (
                usuariosSelecionados.map((item) => (
                  <span key={item.id} className={styles.userChip}>
                    {obterNomeUsuario(item)}
                  </span>
                ))
              ) : (
                <span className={styles.emptyHint}>
                  Nenhum usuário selecionado.
                </span>
              )}
            </div>
          </section>

          {(errors.submit || errors.usuarios || errors.periodo) && (
            <div className={styles.submitError}>
              {errors.submit || errors.usuarios || errors.periodo}
            </div>
          )}

          <Modal.Footer>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setPlanejamentoOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={criarPlanejamentoMutation.isPending}
            >
              Criar lançamento
            </Button>
          </Modal.Footer>
        </form>
      </Modal>

      <Modal
        open={!!planejamentoEmEdicao}
        onClose={() => setPlanejamentoEmEdicao(null)}
        title="Gerenciar atividade planejada"
        size="md"
      >
        {planejamentoEmEdicao && (
          <form
            className={styles.activityManageForm}
            onSubmit={(evento) => {
              evento.preventDefault();
              editarPlanejamentoMutation.mutate();
            }}
          >
            <div className={styles.activityManageSummary}>
              <div className={styles.activityManageCard}>
                <span className={styles.infoLabel}>Usuário</span>
                <strong>{planejamentoEmEdicao.usuarioNome}</strong>
              </div>
              <div className={styles.activityManageCard}>
                <span className={styles.infoLabel}>Data</span>
                <strong>
                  {format(
                    new Date(`${planejamentoEmEdicao.data}T00:00:00`),
                    "dd/MM/yyyy",
                  )}
                </strong>
              </div>
              <div className={styles.activityManageCard}>
                <span className={styles.infoLabel}>Faixa</span>
                <strong>
                  {planejamentoEmEdicao.faixa === "NORMAL"
                    ? "Normal"
                    : "Hora extra"}
                </strong>
              </div>
              <div className={styles.activityManageCard}>
                <span className={styles.infoLabel}>Teto normal</span>
                <strong>
                  {formatarHorasMinutos(planejamentoEmEdicao.capacidadeMaxima)}
                </strong>
              </div>
            </div>

            <div className={styles.formField}>
              <Input
                label="Minutos planejados"
                type="number"
                min="1"
                step="5"
                value={edicaoMinutos}
                onChange={(evento) => setEdicaoMinutos(evento.target.value)}
                error={edicaoErrors.minutos}
              />
              <p className={styles.inlineHint}>
                Ao editar ou remover, o backend deve versionar o registro antigo
                como inativo e manter o histórico.
              </p>
            </div>

            <div className={styles.formField}>
              <Textarea
                label="Descrição"
                rows={4}
                value={edicaoDescricao}
                onChange={(evento) => setEdicaoDescricao(evento.target.value)}
              />
            </div>

            {edicaoErrors.submit && (
              <div className={styles.submitError}>{edicaoErrors.submit}</div>
            )}

            <Modal.Footer>
              <Button
                type="button"
                variant="danger"
                onClick={() => removerPlanejamentoMutation.mutate()}
                loading={removerPlanejamentoMutation.isPending}
              >
                Remover
              </Button>
              <div className={styles.modalSpacer} />
              <Button
                type="button"
                variant="ghost"
                onClick={() => setPlanejamentoEmEdicao(null)}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={editarPlanejamentoMutation.isPending}
              >
                Salvar edição
              </Button>
            </Modal.Footer>
          </form>
        )}
      </Modal>

      <ConsolidacaoModal
        open={consolidacaoOpen}
        onClose={() => setConsolidacaoOpen(false)}
        dateRange={intervaloSelecionado}
        usuarioIds={selectedUsuarioIds}
      />
    </div>
  );
}
