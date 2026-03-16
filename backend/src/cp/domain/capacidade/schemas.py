"""Schemas Pydantic do domínio de Capacidade.

Define os contratos de entrada e saída para a API de agenda e capacidade.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cp.domain.capacidade.enums import (
    CodigoAtividade,
    FaixaMinuto,
    GrupoAtividade,
    StatusDia,
    TipoIndisponibilidade,
    TipoPendencia,
)

# ──────────────────────────────────────────────────────────────────────────────
# Schemas Base
# ──────────────────────────────────────────────────────────────────────────────


class BaseSchema(BaseModel):
    """Schema base com configurações comuns."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ──────────────────────────────────────────────────────────────────────────────
# Tipo de Atividade
# ──────────────────────────────────────────────────────────────────────────────


class TipoAtividadeResponse(BaseSchema):
    """Resposta com dados de tipo de atividade."""

    id: int
    codigo: CodigoAtividade
    nome: str
    grupo: GrupoAtividade
    bloco_id: int | None = None
    cor: str


# ──────────────────────────────────────────────────────────────────────────────
# Parâmetro de Capacidade
# ──────────────────────────────────────────────────────────────────────────────


class ParametroCapacidadeInput(BaseModel):
    """Entrada para criação/atualização de parâmetro de capacidade."""

    minutos_dia_util_default: int = Field(..., gt=0, description="Minutos de capacidade normal por dia útil")
    minutos_extra_maximo_default: int = Field(..., ge=0, description="Máximo de minutos extras permitidos")
    data_inicio_vigencia: date = Field(..., description="Data de início da vigência")
    data_fim_vigencia: date | None = Field(None, description="Data de fim da vigência (null = indefinido)")

    @model_validator(mode="after")
    def validar_vigencia(self) -> "ParametroCapacidadeInput":
        if self.data_fim_vigencia and self.data_fim_vigencia < self.data_inicio_vigencia:
            raise ValueError("data_fim_vigencia deve ser >= data_inicio_vigencia")
        return self


class ParametroCapacidadeResponse(BaseSchema):
    """Resposta com dados de parâmetro de capacidade."""

    id: int
    minutos_dia_util_default: int
    minutos_extra_maximo_default: int
    data_inicio_vigencia: date
    data_fim_vigencia: date | None
    criado_por: int
    criado_em: datetime


class ConfigTetoResponse(BaseModel):
    """Configuração atual do teto diário."""

    teto_normal_min: int
    teto_extra_min: int
    vigencia_inicio: date
    vigencia_fim: date | None
    configurado_em: datetime | None
    configurado_por: int | None


# ──────────────────────────────────────────────────────────────────────────────
# Capacidade Diária
# ──────────────────────────────────────────────────────────────────────────────


class CapacidadeDiaResponse(BaseSchema):
    """Resposta com dados de capacidade diária."""

    id: int
    usuario_id: int
    data: date
    minutos_capacidade_normal_prevista: int
    minutos_capacidade_extra_permitida: int
    eh_dia_util: bool
    eh_feriado: bool
    eh_indisponivel: bool
    tipo_indisponibilidade: TipoIndisponibilidade | None
    status_dia: StatusDia
    atualizado_em: datetime


# ──────────────────────────────────────────────────────────────────────────────
# Agenda Prevista (Planejamento)
# ──────────────────────────────────────────────────────────────────────────────


class PlanejamentoInput(BaseModel):
    """Entrada para criação de planejamento."""

    usuario_id: int = Field(..., description="ID do usuário")
    data: date = Field(..., description="Data do planejamento")
    bloco_id: int | None = Field(None, description="ID do bloco (null para atividade sem bloco)")
    minutos_planejados_normais: int = Field(..., ge=0, description="Minutos normais planejados")
    minutos_planejados_extras: int = Field(0, ge=0, description="Minutos extras planejados")
    descricao: str | None = Field(None, max_length=500, description="Descrição do planejamento")


class PlanejamentoUpdateInput(BaseModel):
    """Entrada para atualização de planejamento."""

    minutos_planejados_normais: int | None = Field(None, ge=0, description="Minutos normais planejados")
    minutos_planejados_extras: int | None = Field(None, ge=0, description="Minutos extras planejados")
    descricao: str | None = Field(None, max_length=500, description="Descrição do planejamento")




class PlanejamentoLoteInput(BaseModel):
    """Entrada para criação em lote de planejamentos."""

    usuario_ids: list[int] = Field(..., min_length=1, description="IDs dos usuários")
    datas: list[date] = Field(..., min_length=1, description="Datas selecionadas")
    bloco_id: int | None = Field(None, description="ID do bloco quando aplicável")
    minutos_planejados_normais: int = Field(0, ge=0, description="Minutos normais planejados")
    minutos_planejados_extras: int = Field(0, ge=0, description="Minutos extras planejados")
    descricao: str | None = Field(None, max_length=500, description="Descrição do planejamento")


class PlanejamentoRemocaoLoteInput(BaseModel):
    """Entrada para remoção em lote de planejamentos ativos."""

    usuario_ids: list[int] = Field(..., min_length=1, description="IDs dos usuários")
    datas: list[date] = Field(..., min_length=1, description="Datas selecionadas")


class PlanejamentoResponse(BaseSchema):
    """Resposta com dados de planejamento."""

    id: int
    usuario_id: int
    data: date
    bloco_id: int | None
    minutos_planejados_normais: int
    minutos_planejados_extras: int
    descricao: str | None
    criado_por: int
    criado_em: datetime
    atualizado_em: datetime


# ──────────────────────────────────────────────────────────────────────────────
# Agenda de Lançamentos
# ──────────────────────────────────────────────────────────────────────────────


class LancamentoInput(BaseModel):
    """Entrada para criação de lançamento (operador)."""

    data: date = Field(..., description="Data do lançamento")
    bloco_id: int | None = Field(None, description="ID do bloco (obrigatório para BLOCO)")
    tipo_atividade: CodigoAtividade = Field(..., description="Código do tipo de atividade")
    faixa: FaixaMinuto = Field(..., description="Faixa do minuto (NORMAL ou EXTRA)")
    minutos: int = Field(..., gt=0, description="Quantidade de minutos")
    descricao: str | None = Field(None, max_length=500, description="Descrição do lançamento")

    @model_validator(mode="after")
    def validar_bloco_obrigatorio(self) -> "LancamentoInput":
        if self.tipo_atividade == CodigoAtividade.BLOCO and self.bloco_id is None:
            raise ValueError("bloco_id é obrigatório para atividade do tipo BLOCO")
        return self


class LancamentoAdminInput(LancamentoInput):
    """Entrada para criação de lançamento (admin)."""

    usuario_id: int = Field(..., description="ID do usuário alvo do lançamento")


class LancamentoUpdateInput(BaseModel):
    """Entrada para atualização de lançamento."""

    minutos: int | None = Field(None, gt=0, description="Quantidade de minutos")
    descricao: str | None = Field(None, max_length=500, description="Descrição do lançamento")


class LancamentoResponse(BaseSchema):
    """Resposta com dados de lançamento."""

    id: int
    usuario_id: int
    data_lancamento: date
    bloco_id: int | None
    tipo_atividade_id: int
    tipo_atividade_codigo: CodigoAtividade
    tipo_atividade_nome: str
    tipo_atividade_cor: str
    faixa_minuto: FaixaMinuto
    minutos: int
    descricao: str | None
    criado_por: int
    atualizado_por: int | None
    criado_em: datetime
    atualizado_em: datetime
    alertas: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Visualização de Agenda (composta)
# ──────────────────────────────────────────────────────────────────────────────


class ApontamentoResumo(BaseModel):
    """Resumo de um apontamento para visualização."""

    id: int
    data: date
    bloco_id: int | None
    bloco_nome: str | None = None
    tipo_atividade_id: int
    tipo_atividade: CodigoAtividade
    tipo_atividade_nome: str
    tipo_atividade_cor: str
    minutos: int
    faixa: FaixaMinuto


class DiaDaAgendaCompleto(BaseModel):
    """Visão completa de um dia da agenda."""

    data: date
    status: StatusDia
    eh_dia_util: bool
    eh_feriado: bool
    eh_indisponivel: bool
    tipo_indisponibilidade: TipoIndisponibilidade | None = None
    teto_normal_min: int
    teto_extra_min: int
    apontado_normal_min: int
    apontado_extra_min: int
    minutos_ociosos: int
    planejamento: list[PlanejamentoResponse] = Field(default_factory=list)
    lancamentos: list[ApontamentoResumo] = Field(default_factory=list)


class AgendaCompletaResponse(BaseModel):
    """Resposta com agenda completa de um usuário."""

    usuario_id: int
    data_inicio: date
    data_fim: date
    dias: list[DiaDaAgendaCompleto]


# ──────────────────────────────────────────────────────────────────────────────
# Feriados
# ──────────────────────────────────────────────────────────────────────────────


class FeriadoInput(BaseModel):
    """Entrada para cadastro de feriado."""

    data: date = Field(..., description="Data do feriado")
    descricao: str = Field(..., min_length=1, max_length=255, description="Descrição do feriado")


class FeriadoResponse(BaseSchema):
    """Resposta com dados de feriado."""

    id: int
    data: date
    descricao: str
    criado_por: int
    criado_em: datetime


class FeriadosListResponse(BaseModel):
    """Lista de feriados."""

    feriados: list[FeriadoResponse]


# ──────────────────────────────────────────────────────────────────────────────
# Indisponibilidade
# ──────────────────────────────────────────────────────────────────────────────


class IndisponibilidadeInput(BaseModel):
    """Entrada para cadastro de indisponibilidade."""

    usuario_id: int = Field(..., description="ID do usuário")
    tipo: TipoIndisponibilidade = Field(..., description="Tipo de indisponibilidade")
    data_inicio: date = Field(..., description="Data de início")
    data_fim: date = Field(..., description="Data de fim")
    descricao: str | None = Field(None, max_length=500, description="Descrição")

    @model_validator(mode="after")
    def validar_periodo(self) -> "IndisponibilidadeInput":
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim deve ser >= data_inicio")
        return self


class IndisponibilidadeResponse(BaseSchema):
    """Resposta com dados de indisponibilidade."""

    id: int
    usuario_id: int
    tipo_atividade_id: int
    tipo: TipoIndisponibilidade
    data_inicio: date
    data_fim: date
    descricao: str | None
    criado_por: int
    criado_em: datetime


class IndisponibilidadesListResponse(BaseModel):
    """Lista de indisponibilidades de um usuário."""

    usuario_id: int
    indisponibilidades: list[IndisponibilidadeResponse]


# ──────────────────────────────────────────────────────────────────────────────
# Consolidação
# ──────────────────────────────────────────────────────────────────────────────


class ConsolidacaoInput(BaseModel):
    """Entrada para consolidação de período."""

    data_inicio: date = Field(..., description="Data de início do período")
    data_fim: date = Field(..., description="Data de fim do período")

    @model_validator(mode="after")
    def validar_periodo(self) -> "ConsolidacaoInput":
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim deve ser >= data_inicio")
        return self


class PendenciaResponse(BaseModel):
    """Pendência impeditiva de consolidação."""

    usuario_id: int
    usuario_nome: str | None = None
    data: date
    tipo: TipoPendencia
    motivo: str


class ConsolidacaoResponse(BaseModel):
    """Resultado de consolidação."""

    consolidado: bool
    pendencias: list[PendenciaResponse] = Field(default_factory=list)
    mensagem: str


class StatusDiasResponse(BaseModel):
    """Status dos dias em um período."""

    dias: list[dict[str, str | date | int]]


# ──────────────────────────────────────────────────────────────────────────────
# Consultas Analíticas
# ──────────────────────────────────────────────────────────────────────────────


class ResumoCapacidadePeriodo(BaseModel):
    """Resumo analítico de capacidade por período."""

    usuario_id: int
    data_inicio: date
    data_fim: date
    bloco_id: int | None = None

    # Minutos previstos
    minutos_previstos_normais: int = 0

    # Minutos realizados (faixa normal)
    minutos_realizados_bloco_normais: int = 0
    minutos_perdidos_externas_normais: int = 0

    # Não alocados (indisponibilidades)
    minutos_nao_alocados: int = 0

    # Ociosos (previsto - realizado)
    minutos_ociosos: int = 0

    # Hora extra
    minutos_extras_bloco: int = 0
    minutos_extras_externas: int = 0
    minutos_extras_totais: int = 0


class CapacidadePeriodoResponse(BaseModel):
    """Resposta de consulta de capacidade por período."""

    resumo: ResumoCapacidadePeriodo
    detalhes_por_dia: list[DiaDaAgendaCompleto] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Exportação
# ──────────────────────────────────────────────────────────────────────────────


class ExportacaoRequest(BaseModel):
    """Requisição de exportação de dados."""

    data_inicio: date
    data_fim: date
    usuario_id: int | None = None
    bloco_id: int | None = None
    formato: Literal["csv", "json"] = "json"


# ──────────────────────────────────────────────────────────────────────────────
# Respostas Genéricas
# ──────────────────────────────────────────────────────────────────────────────


class RemovidoResponse(BaseModel):
    """Confirmação de remoção."""

    removido: bool
    mensagem: str = ""


class CriadoResponse(BaseModel):
    """Confirmação de criação."""

    id: int
    mensagem: str = ""
