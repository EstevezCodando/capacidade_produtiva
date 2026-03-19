// ============================================================
// AgendaRealizada — Lançamentos realizados pelo operador/admin
// Padrão baseado em AgendaPrevista. Persiste em agenda_lancamento.
// ============================================================
import {
    consolidarPeriodo,
    criarLancamento,
    criarLancamentoAdmin,
    editarLancamento,
    editarLancamentoAdmin,
    getConfigTeto,
    getTiposAtividade,
    getUsuarios,
    removerLancamento,
    removerLancamentoAdmin,
} from "@/api/agenda";
import ConsolidacaoModal from "@/components/agenda/ConsolidacaoModal";
import CalendarGrid from "@/components/calendar/CalendarGrid";
import CalendarHeader from "@/components/calendar/CalendarHeader";
import {
    Button,
    Card,
    CapacityBar,
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
    ApontamentoResumo,
    CodigoAtividade,
    FaixaMinuto,
    TipoAtividade,
    UsuarioResumo,
} from "@/types/agenda";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, isAfter, startOfDay } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import styles from "./AgendaPage.module.css";

// ── Interfaces locais ──────────────────────────────────────

interface FormularioLancamento {
    tipoAtividadeId: string;
    faixa: FaixaMinuto;
    unidadeTempo: "HORAS" | "MINUTOS";
    quantidade: string;
    descricao: string;
}

interface SegmentoBarraDia {
    cor: string;
    minutos: number;
    percentual?: number;
}

interface LancamentoDetalheDia {
    lancamentoId: number;
    data: string;
    tipoAtividadeNome: string;
    tipoAtividadeCodigo: CodigoAtividade;
    blocoNome: string | null;
    faixa: FaixaMinuto;
    minutos: number;
    cor: string;
}

interface ResumoDiaRealizado {
    totalNormalMin: number;
    totalExtraMin: number;
    tetoNormalMin: number;
    lancamentos: LancamentoDetalheDia[];
    segmentos: SegmentoBarraDia[];
}

interface LancamentoEdicaoState {
    lancamentoId: number;
    data: string;
    tipoAtividadeNome: string;
    faixa: FaixaMinuto;
    minutos: number;
    descricao: string;
    tetoNormalMin: number;
    totalNormalDia: number;
}

// ── Estado inicial do formulário ───────────────────────────

const ESTADO_INICIAL_FORM: FormularioLancamento = {
    tipoAtividadeId: "",
    faixa: "NORMAL",
    unidadeTempo: "HORAS",
    quantidade: "1",
    descricao: "",
};

// ── Funções auxiliares ─────────────────────────────────────

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

function normalizarCorHex(cor?: string | null): string {
    const valor = (cor ?? "").trim().toUpperCase();
    if (/^#[0-9A-F]{6}$/.test(valor)) return valor;
    return "var(--accent)";
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

function obterCorLancamento(lancamento: ApontamentoResumo): string {
    return normalizarCorHex(lancamento.tipo_atividade_cor);
}

function obterNomeLancamento(lancamento: ApontamentoResumo): string {
    return lancamento.tipo_atividade_nome;
}

function acumularSegmento(
    segmentos: SegmentoBarraDia[],
    cor: string,
    minutos: number,
) {
    if (minutos <= 0) return;
    const corNorm = normalizarCorHex(cor);
    const existente = segmentos.find((s) => s.cor === corNorm);
    if (existente) {
        existente.minutos += minutos;
        return;
    }
    segmentos.push({ cor: corNorm, minutos });
}

function calcularSegmentosPercentuais(
    segmentos: SegmentoBarraDia[],
    capacidadeTotal: number,
): SegmentoBarraDia[] {
    if (capacidadeTotal <= 0 || segmentos.length === 0) return [];
    return segmentos
        .filter((s) => s.minutos > 0)
        .map((s) => ({
            ...s,
            percentual: Math.min(100, (s.minutos / capacidadeTotal) * 100),
        }));
}

// ── Componente principal ───────────────────────────────────

export default function AgendaRealizada() {
    const queryClient = useQueryClient();
    const { ehAdmin, usuario } = useAuth();
    const calendar = useCalendarNavigation({ initialView: "month" });

    // Suporte a ?usuario_id=X na URL (usado pela tela de consolidação para navegar direto ao usuário)
    const [searchParams, setSearchParams] = useSearchParams();
    const urlUsuarioId = searchParams.get("usuario_id")
        ? Number(searchParams.get("usuario_id"))
        : undefined;

    const [selectedUsuarioId, setSelectedUsuarioId] = useState<
        number | undefined
    >(urlUsuarioId);

    // Limpa o param da URL após leitura inicial, para não prender o estado
    useMemo(() => {
        if (urlUsuarioId && searchParams.has("usuario_id")) {
            setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.delete("usuario_id");
                return next;
            }, { replace: true });
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    const [lancamentoOpen, setLancamentoOpen] = useState(false);
    const [consolidacaoOpen, setConsolidacaoOpen] = useState(false);
    const [diaDetalheSelecionado, setDiaDetalheSelecionado] =
        useState<Date | null>(null);
    const [form, setForm] =
        useState<FormularioLancamento>(ESTADO_INICIAL_FORM);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [lancamentoEmEdicao, setLancamentoEmEdicao] =
        useState<LancamentoEdicaoState | null>(null);
    const [edicaoMinutos, setEdicaoMinutos] = useState("");
    const [edicaoDescricao, setEdicaoDescricao] = useState("");
    const [edicaoErrors, setEdicaoErrors] = useState<Record<string, string>>(
        {},
    );

    // ── Queries ──────────────────────────────────────────────

    const { data: usuarios = [], isLoading: loadingUsuarios } = useQuery({
        queryKey: ["usuarios"],
        queryFn: getUsuarios,
        enabled: ehAdmin,
        staleTime: 60_000,
    });

    const { data: tiposAtividadeResposta, isLoading: loadingTipos } = useQuery(
        {
            queryKey: ["tipos-atividade"],
            queryFn: getTiposAtividade,
            staleTime: 60_000,
        },
    );

    const { data: configTeto } = useQuery({
        queryKey: ["config-teto"],
        queryFn: getConfigTeto,
        staleTime: 60_000,
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

    // Usuário cujo dado será carregado
    const usuarioIdParaCarregar = useMemo(() => {
        if (ehAdmin && selectedUsuarioId) return selectedUsuarioId;
        return usuario?.usuario_id;
    }, [ehAdmin, selectedUsuarioId, usuario?.usuario_id]);

    const usuarioSelecionado = useMemo(
        () => usuarios.find((u) => u.id === usuarioIdParaCarregar),
        [usuarios, usuarioIdParaCarregar],
    );

    const { agenda, capacidade, getDiaData, isLoading, isError, invalidate } =
        useAgendaData({
            usuarioId: usuarioIdParaCarregar,
            isAdmin: ehAdmin,
            dataInicio: calendar.formatForApi(calendar.dateRange.start),
            dataFim: calendar.formatForApi(calendar.dateRange.end),
            enabled: !!usuarioIdParaCarregar,
        });

    const capacidadePadraoMinutos = configTeto?.teto_normal_min ?? 360;
    const resumoPeriodo = capacidade?.resumo;

    // ── Derivações ────────────────────────────────────────────

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

    const diasSelecionados = calendar.selectedDates.length;

    const quantidadeDiasResumo = useMemo(() => {
        if (!intervaloSelecionado) return "0 dia";
        if (diasSelecionados === 1) return "1 dia";
        return `${diasSelecionados} dias`;
    }, [diasSelecionados, intervaloSelecionado]);

    // ── Verificações de permissão de lançamento ───────────────

    const hoje = useMemo(() => startOfDay(new Date()), []);

    function isDiaFuturo(date: Date): boolean {
        return isAfter(startOfDay(date), hoje);
    }

    function isDiaConsolidado(date: Date): boolean {
        return getDiaData(date)?.status === "CONSOLIDADO";
    }

    function podeAdicionarLancamento(date: Date): boolean {
        if (isDiaFuturo(date)) return false;
        if (isDiaConsolidado(date)) return false;
        return true;
    }

    function motivoBloqueioLancamento(date: Date): string | null {
        if (isDiaFuturo(date))
            return "Não é possível lançar atividades em dias futuros.";
        if (isDiaConsolidado(date))
            return "Este dia foi consolidado pelo administrador e não aceita mais lançamentos.";
        return null;
    }

    const podeLancarNoDiaSelecionado = diaDetalheSelecionado
        ? podeAdicionarLancamento(diaDetalheSelecionado)
        : false;

    const podeConsolidar =
        ehAdmin && !!intervaloSelecionado && diasSelecionados >= 1;

    // ── Mapa de lançamentos por dia ───────────────────────────

    const detalhesPorDia = useMemo(() => {
        const mapa = new Map<string, ResumoDiaRealizado>();

        if (!agenda?.dias) return mapa;

        for (const dia of agenda.dias) {
            const lancamentos: LancamentoDetalheDia[] = dia.lancamentos.map(
                (l) => ({
                    lancamentoId: l.id,
                    data: dia.data,
                    tipoAtividadeNome: obterNomeLancamento(l),
                    tipoAtividadeCodigo: l.tipo_atividade,
                    blocoNome: l.bloco_nome ?? null,
                    faixa: l.faixa,
                    minutos: l.minutos,
                    cor: obterCorLancamento(l),
                }),
            );

            const segmentos: SegmentoBarraDia[] = [];
            let totalNormalMin = 0;
            let totalExtraMin = 0;

            for (const l of lancamentos) {
                acumularSegmento(segmentos, l.cor, l.minutos);
                if (l.faixa === "NORMAL") totalNormalMin += l.minutos;
                else totalExtraMin += l.minutos;
            }

            mapa.set(dia.data, {
                totalNormalMin,
                totalExtraMin,
                tetoNormalMin: dia.teto_normal_min || capacidadePadraoMinutos,
                lancamentos,
                segmentos,
            });
        }

        return mapa;
    }, [agenda, capacidadePadraoMinutos]);

    const capacidadeVisualPorDia = useMemo(() => {
        const mapa = new Map<
            string,
            {
                totalMinutos: number;
                totalExtraMinutos: number;
                segmentos: SegmentoBarraDia[];
            }
        >();

        for (const [data, resumo] of detalhesPorDia.entries()) {
            mapa.set(data, {
                totalMinutos: resumo.totalNormalMin,
                totalExtraMinutos: resumo.totalExtraMin,
                segmentos: calcularSegmentosPercentuais(
                    resumo.segmentos,
                    resumo.tetoNormalMin,
                ),
            });
        }

        return mapa;
    }, [detalhesPorDia]);

    const dataDetalheSelecionadoChave = diaDetalheSelecionado
        ? format(diaDetalheSelecionado, "yyyy-MM-dd")
        : null;

    const resumoDiaSelecionado = dataDetalheSelecionadoChave
        ? (detalhesPorDia.get(dataDetalheSelecionadoChave) ?? null)
        : null;

    const diaDadoSelecionado = diaDetalheSelecionado
        ? getDiaData(diaDetalheSelecionado)
        : null;

    // ── Tipos de atividade agrupados ──────────────────────────

    const tiposAtividadeOrdenados = useMemo(
        () => [...tiposAtividade].sort((a, b) => a.nome.localeCompare(b.nome)),
        [tiposAtividade],
    );

    const tiposAtividadePorGrupo = useMemo(
        () => ({
            blocos: tiposAtividadeOrdenados.filter(
                (t) => t.origem === "BLOCO",
            ),
            tipos: tiposAtividadeOrdenados.filter(
                (t) => t.origem !== "BLOCO",
            ),
        }),
        [tiposAtividadeOrdenados],
    );

    // ── Mutations ─────────────────────────────────────────────

    const criarLancamentoMutation = useMutation({
        mutationFn: async () => {
            const novosErros: Record<string, string> = {};
            const quantidade = Number(form.quantidade);
            const minutosCalculados = converterQuantidadeParaMinutos(
                form.unidadeTempo,
                quantidade,
            );

            if (!form.tipoAtividadeId)
                novosErros.tipoAtividadeId =
                    "Selecione um tipo de atividade.";
            if (!Number.isFinite(quantidade) || quantidade <= 0)
                novosErros.quantidade = "Informe uma quantidade válida.";
            if (!diaDetalheSelecionado)
                novosErros.data = "Nenhuma data selecionada.";

            setErrors(novosErros);
            if (Object.keys(novosErros).length > 0) {
                throw new Error("Existem campos obrigatórios inválidos.");
            }

            const tipoSelecionado = tiposAtividade.find(
                (t) => t.id === Number(form.tipoAtividadeId),
            );
            if (!tipoSelecionado) {
                setErrors({ tipoAtividadeId: "Tipo de atividade não encontrado. Recarregue a página." });
                throw new Error("Tipo de atividade não encontrado.");
            }
            const blocoId =
                tipoSelecionado.origem === "BLOCO"
                    ? (tipoSelecionado.bloco_id ?? null)
                    : null;
            if (tipoSelecionado.origem === "BLOCO" && blocoId === null) {
                setErrors({ tipoAtividadeId: "Bloco não configurado para este tipo de atividade." });
                throw new Error("bloco_id ausente para atividade BLOCO.");
            }
            const tipoAtividade = tipoSelecionado.codigo;

            const payload = {
                data: format(diaDetalheSelecionado!, "yyyy-MM-dd"),
                bloco_id: blocoId,
                tipo_atividade: tipoAtividade,
                faixa: form.faixa,
                minutos: minutosCalculados,
                descricao: form.descricao.trim() || undefined,
            };

            if (ehAdmin && usuarioIdParaCarregar) {
                return criarLancamentoAdmin({
                    ...payload,
                    usuario_id: usuarioIdParaCarregar,
                });
            }
            return criarLancamento(payload);
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["agenda"] });
            await queryClient.invalidateQueries({ queryKey: ["capacidade"] });
            invalidate();
            setLancamentoOpen(false);
            setForm(ESTADO_INICIAL_FORM);
            setErrors({});
        },
        onError: (error) => {
            setErrors((prev) => ({
                ...prev,
                submit:
                    error instanceof Error
                        ? error.message
                        : "Não foi possível criar o lançamento.",
            }));
        },
    });

    const editarLancamentoMutation = useMutation({
        mutationFn: async () => {
            if (!lancamentoEmEdicao)
                throw new Error("Nenhum lançamento selecionado.");
            const novosErros: Record<string, string> = {};
            const minutos = Number(edicaoMinutos);

            if (!Number.isFinite(minutos) || minutos <= 0) {
                novosErros.minutos =
                    "Informe uma quantidade válida de minutos.";
            }

            if (
                lancamentoEmEdicao.faixa === "NORMAL" &&
                Number.isFinite(minutos) &&
                minutos > 0
            ) {
                const totalSemItem =
                    lancamentoEmEdicao.totalNormalDia -
                    lancamentoEmEdicao.minutos;
                if (totalSemItem + minutos > lancamentoEmEdicao.tetoNormalMin) {
                    novosErros.minutos = `Este ajuste ultrapassa ${formatarHorasMinutos(lancamentoEmEdicao.tetoNormalMin)} em horário normal.`;
                }
            }

            setEdicaoErrors(novosErros);
            if (Object.keys(novosErros).length > 0) {
                throw new Error("Existem erros no lançamento selecionado.");
            }

            const updateData = {
                minutos,
                descricao: edicaoDescricao.trim() || undefined,
            };

            if (ehAdmin) {
                return editarLancamentoAdmin(
                    lancamentoEmEdicao.lancamentoId,
                    updateData,
                );
            }
            return editarLancamento(lancamentoEmEdicao.lancamentoId, updateData);
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["agenda"] });
            await queryClient.invalidateQueries({ queryKey: ["capacidade"] });
            invalidate();
            setLancamentoEmEdicao(null);
        },
        onError: (error) => {
            setEdicaoErrors((prev) => ({
                ...prev,
                submit:
                    error instanceof Error
                        ? error.message
                        : "Não foi possível editar o lançamento.",
            }));
        },
    });

    const removerLancamentoMutation = useMutation({
        mutationFn: async () => {
            if (!lancamentoEmEdicao)
                throw new Error("Nenhum lançamento selecionado.");
            if (ehAdmin) {
                return removerLancamentoAdmin(lancamentoEmEdicao.lancamentoId);
            }
            return removerLancamento(lancamentoEmEdicao.lancamentoId);
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["agenda"] });
            await queryClient.invalidateQueries({ queryKey: ["capacidade"] });
            invalidate();
            setLancamentoEmEdicao(null);
        },
        onError: (error) => {
            setEdicaoErrors((prev) => ({
                ...prev,
                submit:
                    error instanceof Error
                        ? error.message
                        : "Não foi possível remover o lançamento.",
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
                usuarios_ids: selectedUsuarioId
                    ? [selectedUsuarioId]
                    : undefined,
                ignorar_pendencias: false,
            });
        },
        onSuccess: (resultado) => {
            if (!resultado.pendencias.length) {
                setConsolidacaoOpen(true);
                return;
            }

            const linhas = [
                ["usuario", "dia", "motivo"].join(","),
                ...resultado.pendencias.map((p) =>
                    [
                        JSON.stringify(
                            p.usuario_nome ?? `Usuário ${p.usuario_id}`,
                        ),
                        p.data,
                        JSON.stringify(p.motivo),
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

    // ── Handlers ──────────────────────────────────────────────

    function abrirEdicaoLancamento(
        lancamento: LancamentoDetalheDia,
        resumoDia: ResumoDiaRealizado,
    ) {
        setEdicaoErrors({});
        setLancamentoEmEdicao({
            lancamentoId: lancamento.lancamentoId,
            data: lancamento.data,
            tipoAtividadeNome: lancamento.tipoAtividadeNome,
            faixa: lancamento.faixa,
            minutos: lancamento.minutos,
            descricao: "",
            tetoNormalMin: resumoDia.tetoNormalMin,
            totalNormalDia: resumoDia.totalNormalMin,
        });
        setEdicaoMinutos(String(lancamento.minutos));
        setEdicaoDescricao("");
    }

    function abrirNovoLancamento() {
        setErrors({});
        setForm(ESTADO_INICIAL_FORM);
        setLancamentoOpen(true);
    }

    // ── Valores derivados para o formulário ───────────────────

    const cargaLancamentoLabel = useMemo(() => {
        const qtd = Number(form.quantidade || 0);
        if (!qtd || qtd < 1) return "Não definida";
        return formatarHorasMinutos(
            converterQuantidadeParaMinutos(form.unidadeTempo, qtd),
        );
    }, [form.unidadeTempo, form.quantidade]);

    // ── Sidebar stats ─────────────────────────────────────────

    const totalNormalRealizado =
        (resumoPeriodo?.minutos_realizados_bloco_normais ?? 0) +
        (resumoPeriodo?.minutos_perdidos_externas_normais ?? 0);
    const capacidadeNormalPeriodo =
        resumoPeriodo?.minutos_previstos_normais ?? capacidadePadraoMinutos;

    // ── Render ────────────────────────────────────────────────

    return (
        <div className={styles.page}>
            {/* ══ SIDEBAR ══════════════════════════════════════════ */}
            <aside className={styles.sidebar}>
                <div className={styles.sidebarHeader}>
                    <h2 className={styles.sidebarTitle}>Agenda Realizada</h2>
                    <p className={styles.sidebarSubtitle}>
                        Lançamentos e apontamentos de atividades realizadas.
                        Operadores registram o próprio trabalho; administradores
                        gerenciam qualquer usuário.
                    </p>
                </div>

                {/* Seletor de usuário (admin) ou identificação (operador) */}
                {ehAdmin ? (
                    <div className={styles.userSelector}>
                        <span className={styles.selectorLabel}>Usuário</span>
                        {loadingUsuarios ? (
                            <Skeleton height={40} />
                        ) : (
                            <Select
                                value={selectedUsuarioId?.toString() ?? ""}
                                onChange={(v) =>
                                    setSelectedUsuarioId(
                                        v ? parseInt(v, 10) : undefined,
                                    )
                                }
                                options={[
                                    {
                                        value: "",
                                        label: "Selecione um usuário…",
                                    },
                                    ...usuarios.map((u) => ({
                                        value: u.id.toString(),
                                        label: obterNomeUsuario(u),
                                    })),
                                ]}
                            />
                        )}
                        {usuarioSelecionado && (
                            <div className={styles.selectedUsersPreview}>
                                <span className={styles.userChip}>
                                    {obterNomeUsuario(usuarioSelecionado)}
                                </span>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className={styles.userViewer}>
                        <span className={styles.selectorLabel}>Usuário</span>
                        <div className={styles.userViewerCard}>
                            {usuario?.nome_guerra ||
                                usuario?.nome ||
                                "Usuário atual"}
                        </div>
                    </div>
                )}

                {/* Barra de utilização e estatísticas */}
                <div className={styles.summaryCards}>
                    {isLoading ? (
                        <>
                            <Skeleton height={60} />
                            <Skeleton height={92} />
                            <Skeleton height={92} />
                            <Skeleton height={92} />
                            <Skeleton height={92} />
                            <Skeleton height={92} />
                        </>
                    ) : (
                        <>
                            <CapacityBar
                                normalValue={totalNormalRealizado}
                                normalMax={capacidadeNormalPeriodo}
                                extraValue={
                                    resumoPeriodo?.minutos_extras_totais ?? 0
                                }
                                extraMax={configTeto?.teto_extra_min ?? 240}
                                size="lg"
                            />
                            <Card padding="sm">
                                <StatCard
                                    label="Realizado em bloco"
                                    value={
                                        resumoPeriodo?.minutos_realizados_bloco_normais ??
                                        0
                                    }
                                    suffix="min"
                                    variant="accent"
                                    size="sm"
                                />
                            </Card>
                            <Card padding="sm">
                                <StatCard
                                    label="Atividades externas"
                                    value={
                                        resumoPeriodo?.minutos_perdidos_externas_normais ??
                                        0
                                    }
                                    suffix="min"
                                    variant="default"
                                    size="sm"
                                />
                            </Card>
                            <Card padding="sm">
                                <StatCard
                                    label="Hora extra"
                                    value={
                                        resumoPeriodo?.minutos_extras_totais ??
                                        0
                                    }
                                    suffix="min"
                                    variant="warning"
                                    size="sm"
                                />
                            </Card>
                            <Card padding="sm">
                                <StatCard
                                    label="Não alocados"
                                    value={
                                        resumoPeriodo?.minutos_nao_alocados ?? 0
                                    }
                                    suffix="min"
                                    variant="default"
                                    size="sm"
                                />
                            </Card>
                            <Card padding="sm">
                                <StatCard
                                    label="Ociosos"
                                    value={
                                        resumoPeriodo?.minutos_ociosos ?? 0
                                    }
                                    suffix="min"
                                    variant={
                                        (resumoPeriodo?.minutos_ociosos ?? 0) >
                                        0
                                            ? "error"
                                            : "default"
                                    }
                                    size="sm"
                                />
                            </Card>
                        </>
                    )}
                </div>

                {/* Legenda com paleta de atividades */}
                <div className={styles.legend}>
                    <div className={styles.legendHeader}>
                        <div>
                            <h4 className={styles.legendTitle}>
                                Cores das atividades
                            </h4>
                            <p className={styles.legendSubtitle}>
                                Paleta operacional configurada pelo administrador
                                para identificação visual dos lançamentos.
                            </p>
                        </div>
                        <span className={styles.legendBadge}>
                            {tiposAtividade.length} atividades
                        </span>
                    </div>

                    <div className={styles.legendItems}>
                        <div className={styles.legendItem}>
                            <span
                                className={`${styles.legendColor} ${styles.legendColorConsolidado}`}
                            />
                            <span>Dia consolidado</span>
                        </div>
                        <div className={styles.legendItem}>
                            <span
                                className={`${styles.legendColor} ${styles.legendColorFeriado}`}
                            />
                            <span>Feriado</span>
                        </div>
                        <div className={styles.legendItem}>
                            <span
                                className={`${styles.legendColor} ${styles.legendColorIndisponivel}`}
                            />
                            <span>Indisponível</span>
                        </div>
                    </div>

                    <div className={styles.activityPaletteSection}>
                        <div className={styles.activityPaletteHeader}>
                            <span className={styles.activityPaletteTitle}>
                                Blocos e tipos
                            </span>
                            <span className={styles.activityPaletteMeta}>
                                Legenda operacional
                            </span>
                        </div>

                        {loadingTipos ? (
                            <div className={styles.activityPaletteEmpty}>
                                Carregando atividades configuradas…
                            </div>
                        ) : tiposAtividade.length === 0 ? (
                            <div className={styles.activityPaletteEmpty}>
                                Nenhuma atividade configurada encontrada.
                            </div>
                        ) : (
                            <>
                                {tiposAtividadePorGrupo.blocos.length > 0 && (
                                    <div
                                        className={
                                            styles.activityPaletteGroup
                                        }
                                    >
                                        <div
                                            className={
                                                styles.activityPaletteGroupTitle
                                            }
                                        >
                                            Blocos de produção
                                        </div>
                                        <div
                                            className={
                                                styles.activityPaletteGrid
                                            }
                                        >
                                            {tiposAtividadePorGrupo.blocos.map(
                                                (tipo) => (
                                                    <article
                                                        key={tipo.id}
                                                        className={
                                                            styles.activityPaletteCard
                                                        }
                                                    >
                                                        <span
                                                            className={
                                                                styles.activityPaletteSwatch
                                                            }
                                                            style={{
                                                                background:
                                                                    normalizarCorHex(
                                                                        tipo.cor,
                                                                    ),
                                                            }}
                                                        />
                                                        <div
                                                            className={
                                                                styles.activityPaletteContent
                                                            }
                                                        >
                                                            <span
                                                                className={
                                                                    styles.activityPaletteName
                                                                }
                                                            >
                                                                {tipo.nome}
                                                            </span>
                                                            <span
                                                                className={
                                                                    styles.activityPaletteDescription
                                                                }
                                                            >
                                                                {obterDescricaoOrigemTipo(
                                                                    tipo,
                                                                )}
                                                            </span>
                                                        </div>
                                                    </article>
                                                ),
                                            )}
                                        </div>
                                    </div>
                                )}

                                {tiposAtividadePorGrupo.tipos.length > 0 && (
                                    <div
                                        className={
                                            styles.activityPaletteGroup
                                        }
                                    >
                                        <div
                                            className={
                                                styles.activityPaletteGroupTitle
                                            }
                                        >
                                            Demais atividades
                                        </div>
                                        <div
                                            className={
                                                styles.activityPaletteGrid
                                            }
                                        >
                                            {tiposAtividadePorGrupo.tipos.map(
                                                (tipo) => (
                                                    <article
                                                        key={tipo.id}
                                                        className={
                                                            styles.activityPaletteCard
                                                        }
                                                    >
                                                        <span
                                                            className={
                                                                styles.activityPaletteSwatch
                                                            }
                                                            style={{
                                                                background:
                                                                    normalizarCorHex(
                                                                        tipo.cor,
                                                                    ),
                                                            }}
                                                        />
                                                        <div
                                                            className={
                                                                styles.activityPaletteContent
                                                            }
                                                        >
                                                            <span
                                                                className={
                                                                    styles.activityPaletteName
                                                                }
                                                            >
                                                                {tipo.nome}
                                                            </span>
                                                            <span
                                                                className={
                                                                    styles.activityPaletteDescription
                                                                }
                                                            >
                                                                {obterDescricaoOrigemTipo(
                                                                    tipo,
                                                                )}
                                                            </span>
                                                        </div>
                                                    </article>
                                                ),
                                            )}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </aside>

            {/* ══ MAIN ════════════════════════════════════════════ */}
            <main className={styles.main}>
                {/* Barra de ações superior */}
                <div className={styles.topActionsBar}>
                    <div>
                        <h3 className={styles.topActionsTitle}>
                            Lançamentos do período
                        </h3>
                        <p className={styles.topActionsSubtitle}>
                            Registre as atividades realizadas. Não é permitido
                            lançar em dias futuros ou em dias já consolidados
                            pelo administrador.
                        </p>
                    </div>
                    <div className={styles.topActionsButtons}>
                        {ehAdmin && (
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
                        )}
                        <Button
                            variant="primary"
                            onClick={abrirNovoLancamento}
                            disabled={
                                !diaDetalheSelecionado ||
                                !podeLancarNoDiaSelecionado ||
                                (ehAdmin && !usuarioIdParaCarregar)
                            }
                        >
                            Novo lançamento
                        </Button>
                    </div>
                </div>

                {/* Resumo de seleção */}
                <div className={styles.selectionSummary}>
                    <div className={styles.selectionPill}>
                        <strong>Período</strong>
                        <span>{intervaloSelecionadoLabel}</span>
                    </div>
                    <div className={styles.selectionPill}>
                        <strong>Dias</strong>
                        <span>{quantidadeDiasResumo}</span>
                    </div>
                    {diaDetalheSelecionado && (
                        <div className={styles.selectionPill}>
                            <strong>Status</strong>
                            <span>
                                {isDiaFuturo(diaDetalheSelecionado)
                                    ? "Dia futuro"
                                    : isDiaConsolidado(diaDetalheSelecionado)
                                      ? "Consolidado"
                                      : diaDadoSelecionado?.eh_feriado
                                        ? "Feriado"
                                        : diaDadoSelecionado?.eh_indisponivel
                                          ? "Indisponível"
                                          : "Aberto"}
                            </span>
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
                                getCapacityDisplay={(date) =>
                                    capacidadeVisualPorDia.get(
                                        format(date, "yyyy-MM-dd"),
                                    ) ?? null
                                }
                                getOciosoDisplay={(date) => {
                                    if (isDiaFuturo(date)) return { ativo: false, minutos: 0 };
                                    const diaData = getDiaData(date);
                                    if (!diaData || !diaData.eh_dia_util || diaData.eh_feriado || diaData.eh_indisponivel) return null;
                                    const ociosos = Math.max(0, diaData.teto_normal_min - diaData.apontado_normal_min);
                                    return { ativo: ociosos > 0, minutos: ociosos };
                                }}
                                selectedDates={calendar.selectedDates}
                                onSelectDate={calendar.selectDate}
                                onSelectRange={calendar.selectRange}
                                onDayClick={(date) => {
                                    calendar.selectDate(date);
                                    setDiaDetalheSelecionado(date);
                                }}
                                isAdmin={ehAdmin}
                                loading={isLoading}
                                exibirIndicadorOcioso={true}
                            />
                        )}
                    </div>

                    {/* Painel lateral de detalhes do dia */}
                    <aside className={styles.dayDetailsPanel}>
                        <div className={styles.dayDetailsHeader}>
                            <span className={styles.selectorLabel}>
                                Detalhe do dia
                            </span>
                            <h4 className={styles.dayDetailsTitle}>
                                {diaDetalheSelecionado
                                    ? format(
                                          diaDetalheSelecionado,
                                          "dd/MM/yyyy",
                                      )
                                    : "Selecione um dia"}
                            </h4>
                            <p className={styles.dayDetailsSubtitle}>
                                {diaDetalheSelecionado
                                    ? "Lançamentos registrados no dia selecionado."
                                    : "Clique em uma célula para ver os lançamentos do dia."}
                            </p>
                        </div>

                        {diaDetalheSelecionado ? (
                            <div className={styles.dayDetailsContent}>
                                {/* Aviso de bloqueio */}
                                {motivoBloqueioLancamento(
                                    diaDetalheSelecionado,
                                ) && (
                                    <div
                                        className={styles.dayDetailsEmpty}
                                        style={{
                                            borderColor:
                                                "rgba(255,180,0,0.25)",
                                            background: "rgba(80,50,0,0.22)",
                                            color: "#ffd88a",
                                        }}
                                    >
                                        {motivoBloqueioLancamento(
                                            diaDetalheSelecionado,
                                        )}
                                    </div>
                                )}

                                {/* Resumo do dia */}
                                {resumoDiaSelecionado ? (
                                    <section className={styles.dayUserCard}>
                                        <div className={styles.dayUserHeader}>
                                            <div>
                                                <h5
                                                    className={
                                                        styles.dayUserName
                                                    }
                                                >
                                                    {usuarioSelecionado
                                                        ? obterNomeUsuario(
                                                              usuarioSelecionado,
                                                          )
                                                        : usuario?.nome_guerra ||
                                                          usuario?.nome ||
                                                          "Usuário atual"}
                                                </h5>
                                                <p
                                                    className={
                                                        styles.dayUserMeta
                                                    }
                                                >
                                                    {resumoDiaSelecionado.tetoNormalMin >
                                                    0
                                                        ? `${Math.round((resumoDiaSelecionado.totalNormalMin / resumoDiaSelecionado.tetoNormalMin) * 100)}% ocupado`
                                                        : "Capacidade não definida"}{" "}
                                                    ·{" "}
                                                    {formatarHorasMinutos(
                                                        resumoDiaSelecionado.tetoNormalMin,
                                                    )}{" "}
                                                    teto normal
                                                </p>
                                            </div>
                                            <span
                                                className={styles.dayUserTotal}
                                            >
                                                {formatarHorasMinutos(
                                                    resumoDiaSelecionado.totalNormalMin +
                                                        resumoDiaSelecionado.totalExtraMin,
                                                )}
                                            </span>
                                        </div>

                                        <div
                                            className={styles.dayUserBarTrack}
                                        >
                                            {calcularSegmentosPercentuais(
                                                resumoDiaSelecionado.segmentos,
                                                resumoDiaSelecionado.tetoNormalMin,
                                            ).map((seg, i) => (
                                                <div
                                                    key={`seg-${i}-${seg.cor}`}
                                                    className={
                                                        styles.dayUserBarFill
                                                    }
                                                    style={{
                                                        width: `${seg.percentual ?? 0}%`,
                                                        background: seg.cor,
                                                    }}
                                                />
                                            ))}
                                        </div>

                                        <div
                                            className={
                                                styles.dayUserMetricsRow
                                            }
                                        >
                                            <span
                                                className={
                                                    styles.dayMetricPill
                                                }
                                            >
                                                Normal:{" "}
                                                {formatarHorasMinutos(
                                                    resumoDiaSelecionado.totalNormalMin,
                                                )}
                                            </span>
                                            <span
                                                className={
                                                    styles.dayMetricPill
                                                }
                                            >
                                                Extra:{" "}
                                                {formatarHorasMinutos(
                                                    resumoDiaSelecionado.totalExtraMin,
                                                )}
                                            </span>
                                        </div>

                                        {/* Lista de lançamentos */}
                                        <div
                                            className={
                                                styles.dayActivitiesList
                                            }
                                        >
                                            {resumoDiaSelecionado.lancamentos
                                                .length > 0 ? (
                                                resumoDiaSelecionado.lancamentos.map(
                                                    (lancamento) => {
                                                        const diaAberto =
                                                            podeAdicionarLancamento(
                                                                diaDetalheSelecionado,
                                                            );
                                                        return (
                                                            <article
                                                                key={
                                                                    lancamento.lancamentoId
                                                                }
                                                                className={`${styles.dayActivityItem} ${diaAberto ? styles.dayActivityItemInteractive : ""}`}
                                                                onClick={
                                                                    diaAberto
                                                                        ? () =>
                                                                              abrirEdicaoLancamento(
                                                                                  lancamento,
                                                                                  resumoDiaSelecionado,
                                                                              )
                                                                        : undefined
                                                                }
                                                            >
                                                                <div
                                                                    className={
                                                                        styles.dayActivityInfo
                                                                    }
                                                                >
                                                                    <div
                                                                        className={
                                                                            styles.dayActivityTitle
                                                                        }
                                                                    >
                                                                        <span
                                                                            className={
                                                                                styles.dayActivityColorDot
                                                                            }
                                                                            style={{
                                                                                background:
                                                                                    lancamento.cor,
                                                                            }}
                                                                        />
                                                                        <span
                                                                            className={
                                                                                styles.dayActivityTitleText
                                                                            }
                                                                        >
                                                                            {
                                                                                lancamento.tipoAtividadeNome
                                                                            }
                                                                        </span>
                                                                    </div>
                                                                    <div
                                                                        className={
                                                                            styles.dayActivityMeta
                                                                        }
                                                                    >
                                                                        {lancamento.faixa ===
                                                                        "NORMAL"
                                                                            ? "Normal"
                                                                            : "Hora extra"}{" "}
                                                                        ·{" "}
                                                                        {formatarHorasMinutos(
                                                                            lancamento.minutos,
                                                                        )}
                                                                    </div>
                                                                </div>
                                                                {diaAberto && (
                                                                    <span
                                                                        className={
                                                                            styles.dayActivityMetaHint
                                                                        }
                                                                    >
                                                                        Editar
                                                                    </span>
                                                                )}
                                                            </article>
                                                        );
                                                    },
                                                )
                                            ) : (
                                                <div
                                                    className={
                                                        styles.dayEmptyState
                                                    }
                                                >
                                                    Nenhum lançamento neste dia.
                                                </div>
                                            )}
                                        </div>

                                        {/* Botão de novo lançamento no painel */}
                                        {podeAdicionarLancamento(
                                            diaDetalheSelecionado,
                                        ) && (
                                            <Button
                                                variant="primary"
                                                size="sm"
                                                onClick={abrirNovoLancamento}
                                                disabled={
                                                    ehAdmin &&
                                                    !usuarioIdParaCarregar
                                                }
                                            >
                                                + Novo lançamento
                                            </Button>
                                        )}
                                    </section>
                                ) : (
                                    <div className={styles.dayDetailsEmpty}>
                                        {diaDadoSelecionado?.eh_feriado
                                            ? "Feriado — nenhum lançamento aplicável."
                                            : diaDadoSelecionado?.eh_indisponivel
                                              ? "Dia marcado como indisponível."
                                              : !diaDadoSelecionado
                                                ? "Dados do dia não disponíveis. Selecione um período com dados carregados."
                                                : "Nenhum lançamento neste dia."}

                                        {podeAdicionarLancamento(
                                            diaDetalheSelecionado,
                                        ) &&
                                            !diaDadoSelecionado?.eh_feriado &&
                                            !diaDadoSelecionado?.eh_indisponivel && (
                                                <Button
                                                    variant="primary"
                                                    size="sm"
                                                    onClick={abrirNovoLancamento}
                                                    disabled={
                                                        ehAdmin &&
                                                        !usuarioIdParaCarregar
                                                    }
                                                    style={{
                                                        marginTop: "12px",
                                                    }}
                                                >
                                                    + Novo lançamento
                                                </Button>
                                            )}
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

            {/* ══ MODAL: NOVO LANÇAMENTO ═══════════════════════════ */}
            <Modal
                open={lancamentoOpen}
                onClose={() => setLancamentoOpen(false)}
                title="Novo lançamento"
                size="xl"
            >
                <form
                    className={styles.planejamentoForm}
                    onSubmit={(e) => {
                        e.preventDefault();
                        criarLancamentoMutation.mutate();
                    }}
                >
                    <section className={styles.modalSection}>
                        <div className={styles.modalSectionHeader}>
                            <h4 className={styles.modalSectionTitle}>
                                Atividade realizada
                            </h4>
                            <p className={styles.modalSectionSubtitle}>
                                Selecione o tipo de atividade, a faixa de
                                horário e informe o tempo dedicado.
                            </p>
                        </div>

                        <div className={styles.formGrid}>
                            <div className={styles.formField}>
                                <label className={styles.formLabel}>
                                    Tipo de atividade
                                </label>
                                <Select
                                    value={form.tipoAtividadeId}
                                    onChange={(v) =>
                                        setForm((prev) => ({
                                            ...prev,
                                            tipoAtividadeId: v,
                                        }))
                                    }
                                    options={tiposAtividade.map((t) => ({
                                        value: String(t.id),
                                        label: t.nome,
                                    }))}
                                    placeholder={
                                        loadingTipos
                                            ? "Carregando…"
                                            : "Selecione"
                                    }
                                />
                                {errors.tipoAtividadeId && (
                                    <span className={styles.formError}>
                                        {errors.tipoAtividadeId}
                                    </span>
                                )}
                            </div>

                            <div className={styles.formField}>
                                <label className={styles.formLabel}>
                                    Faixa de horário
                                </label>
                                <Select
                                    value={form.faixa}
                                    onChange={(v) =>
                                        setForm((prev) => ({
                                            ...prev,
                                            faixa: v as FaixaMinuto,
                                        }))
                                    }
                                    options={[
                                        { value: "NORMAL", label: "Normal" },
                                        {
                                            value: "EXTRA",
                                            label: "Hora extra",
                                        },
                                    ]}
                                />
                            </div>

                            <div className={styles.formField}>
                                <label className={styles.formLabel}>
                                    Unidade de tempo
                                </label>
                                <Select
                                    value={form.unidadeTempo}
                                    onChange={(v) =>
                                        setForm((prev) => ({
                                            ...prev,
                                            unidadeTempo: v as
                                                | "HORAS"
                                                | "MINUTOS",
                                        }))
                                    }
                                    options={[
                                        { value: "HORAS", label: "Horas" },
                                        {
                                            value: "MINUTOS",
                                            label: "Minutos",
                                        },
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
                                    onChange={(e) =>
                                        setForm((prev) => ({
                                            ...prev,
                                            quantidade: e.target.value,
                                        }))
                                    }
                                    error={errors.quantidade}
                                />
                            </div>
                        </div>
                    </section>

                    <section className={styles.modalSection}>
                        <div className={styles.modalSectionHeader}>
                            <h4 className={styles.modalSectionTitle}>
                                Descrição
                            </h4>
                            <p className={styles.modalSectionSubtitle}>
                                Contexto opcional para facilitar a identificação
                                futura do lançamento.
                            </p>
                        </div>
                        <Textarea
                            label="Descrição opcional"
                            rows={4}
                            value={form.descricao}
                            onChange={(e) =>
                                setForm((prev) => ({
                                    ...prev,
                                    descricao: e.target.value,
                                }))
                            }
                            placeholder="Ex.: reunião de alinhamento, apoio ao bloco X, atividade administrativa…"
                        />
                    </section>

                    <section className={styles.modalSection}>
                        <div className={styles.modalSectionHeader}>
                            <h4 className={styles.modalSectionTitle}>
                                Resumo do lançamento
                            </h4>
                            <p className={styles.modalSectionSubtitle}>
                                Confirme os dados antes de registrar.
                            </p>
                        </div>

                        <div className={styles.infoGrid}>
                            <div className={styles.infoCard}>
                                <span className={styles.infoLabel}>Data</span>
                                <strong>
                                    {diaDetalheSelecionado
                                        ? format(
                                              diaDetalheSelecionado,
                                              "EEEE, d 'de' MMMM 'de' yyyy",
                                              { locale: ptBR },
                                          )
                                        : "—"}
                                </strong>
                            </div>
                            <div className={styles.infoCard}>
                                <span className={styles.infoLabel}>
                                    Carga registrada
                                </span>
                                <strong>{cargaLancamentoLabel}</strong>
                                <span className={styles.infoDetail}>
                                    Teto normal:{" "}
                                    {formatarHorasMinutos(
                                        capacidadePadraoMinutos,
                                    )}
                                </span>
                            </div>
                            <div className={styles.infoCard}>
                                <span className={styles.infoLabel}>Faixa</span>
                                <strong>
                                    {form.faixa === "NORMAL"
                                        ? "Normal"
                                        : "Hora extra"}
                                </strong>
                            </div>
                            <div className={styles.infoCard}>
                                <span className={styles.infoLabel}>
                                    Usuário
                                </span>
                                <strong>
                                    {usuarioSelecionado
                                        ? obterNomeUsuario(usuarioSelecionado)
                                        : usuario?.nome_guerra ||
                                          usuario?.nome ||
                                          "Usuário atual"}
                                </strong>
                            </div>
                        </div>
                    </section>

                    {errors.submit && (
                        <div className={styles.submitError}>
                            {errors.submit}
                        </div>
                    )}

                    <Modal.Footer>
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => setLancamentoOpen(false)}
                        >
                            Cancelar
                        </Button>
                        <Button
                            type="submit"
                            variant="primary"
                            loading={criarLancamentoMutation.isPending}
                        >
                            Registrar lançamento
                        </Button>
                    </Modal.Footer>
                </form>
            </Modal>

            {/* ══ MODAL: EDITAR / REMOVER LANÇAMENTO ══════════════ */}
            <Modal
                open={!!lancamentoEmEdicao}
                onClose={() => setLancamentoEmEdicao(null)}
                title="Gerenciar lançamento"
                size="md"
            >
                {lancamentoEmEdicao && (
                    <form
                        className={styles.activityManageForm}
                        onSubmit={(e) => {
                            e.preventDefault();
                            editarLancamentoMutation.mutate();
                        }}
                    >
                        <div className={styles.activityManageSummary}>
                            <div className={styles.activityManageCard}>
                                <span className={styles.infoLabel}>
                                    Atividade
                                </span>
                                <strong>
                                    {lancamentoEmEdicao.tipoAtividadeNome}
                                </strong>
                            </div>
                            <div className={styles.activityManageCard}>
                                <span className={styles.infoLabel}>Data</span>
                                <strong>
                                    {format(
                                        new Date(
                                            `${lancamentoEmEdicao.data}T00:00:00`,
                                        ),
                                        "dd/MM/yyyy",
                                    )}
                                </strong>
                            </div>
                            <div className={styles.activityManageCard}>
                                <span className={styles.infoLabel}>Faixa</span>
                                <strong>
                                    {lancamentoEmEdicao.faixa === "NORMAL"
                                        ? "Normal"
                                        : "Hora extra"}
                                </strong>
                            </div>
                            <div className={styles.activityManageCard}>
                                <span className={styles.infoLabel}>
                                    Teto normal
                                </span>
                                <strong>
                                    {formatarHorasMinutos(
                                        lancamentoEmEdicao.tetoNormalMin,
                                    )}
                                </strong>
                            </div>
                        </div>

                        <div className={styles.formField}>
                            <Input
                                label="Minutos realizados"
                                type="number"
                                min="1"
                                step="5"
                                value={edicaoMinutos}
                                onChange={(e) =>
                                    setEdicaoMinutos(e.target.value)
                                }
                                error={edicaoErrors.minutos}
                            />
                            <p className={styles.inlineHint}>
                                O sistema mantém histórico ao versionar o
                                registro alterado.
                            </p>
                        </div>

                        <div className={styles.formField}>
                            <Textarea
                                label="Descrição"
                                rows={4}
                                value={edicaoDescricao}
                                onChange={(e) =>
                                    setEdicaoDescricao(e.target.value)
                                }
                                placeholder="Observações sobre o lançamento…"
                            />
                        </div>

                        {edicaoErrors.submit && (
                            <div className={styles.submitError}>
                                {edicaoErrors.submit}
                            </div>
                        )}

                        <Modal.Footer>
                            <Button
                                type="button"
                                variant="danger"
                                onClick={() =>
                                    removerLancamentoMutation.mutate()
                                }
                                loading={removerLancamentoMutation.isPending}
                            >
                                Remover
                            </Button>
                            <div className={styles.modalSpacer} />
                            <Button
                                type="button"
                                variant="ghost"
                                onClick={() => setLancamentoEmEdicao(null)}
                            >
                                Cancelar
                            </Button>
                            <Button
                                type="submit"
                                variant="primary"
                                loading={editarLancamentoMutation.isPending}
                            >
                                Salvar edição
                            </Button>
                        </Modal.Footer>
                    </form>
                )}
            </Modal>

            {/* ══ MODAL: CONSOLIDAÇÃO ══════════════════════════════ */}
            <ConsolidacaoModal
                open={consolidacaoOpen}
                onClose={() => setConsolidacaoOpen(false)}
                dateRange={intervaloSelecionado}
                usuarioIds={selectedUsuarioId ? [selectedUsuarioId] : []}
            />
        </div>
    );
}
