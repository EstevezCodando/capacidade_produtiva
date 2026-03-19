"""Enumerações do domínio de Capacidade.

Define os tipos e estados utilizados no módulo de Agenda e Capacidade.
"""

from __future__ import annotations

from enum import Enum


class FaixaMinuto(str, Enum):
    """Classificação do minuto quanto ao limite diário.

    NORMAL: dentro da capacidade diária regular
    EXTRA: acima da capacidade diária (hora extra)
    """

    NORMAL = "NORMAL"
    EXTRA = "EXTRA"


class GrupoAtividade(str, Enum):
    """Agrupamento de tipos de atividade.

    PRODUCAO: atividades relacionadas a blocos produtivos
    INDISPONIBILIDADE: ausências programadas (férias, licença, etc.)
    AJUSTE: correções e ajustes administrativos
    """

    PRODUCAO = "PRODUCAO"
    INDISPONIBILIDADE = "INDISPONIBILIDADE"
    AJUSTE = "AJUSTE"


class CodigoAtividade(str, Enum):
    """Códigos de atividade disponíveis no sistema.

    BLOCO: tempo dedicado a bloco produtivo (um por bloco SAP)
    EXTERNA: produção diversa
    AJUSTE: atividade administrativa
    FERIAS: férias do colaborador
    LICENCA: dispensa médica
    CURSO: capacitação ou treinamento
    AFASTAMENTO: dispensa como recompensa
    CAMPO: trabalho de campo
    MILITAR: atividade militar
    """

    BLOCO = "BLOCO"
    EXTERNA = "EXTERNA"
    AJUSTE = "AJUSTE"
    FERIAS = "FERIAS"
    LICENCA = "LICENCA"
    CURSO = "CURSO"
    AFASTAMENTO = "AFASTAMENTO"
    CAMPO = "CAMPO"
    MILITAR = "MILITAR"


class StatusDia(str, Enum):
    """Status de consolidação do dia.

    ABERTO: dia permite edições conforme perfil
    CONSOLIDADO: dia fechado, alteração requer permissão admin e auditoria
    """

    ABERTO = "ABERTO"
    CONSOLIDADO = "CONSOLIDADO"


class TipoIndisponibilidade(str, Enum):
    """Tipos de indisponibilidade do usuário.

    Mapeamento direto para CodigoAtividade de indisponibilidade.
    """

    FERIAS = "FERIAS"
    LICENCA = "LICENCA"
    CURSO = "CURSO"
    AFASTAMENTO = "AFASTAMENTO"


class AcaoAuditoria(str, Enum):
    """Ações auditadas no sistema.

    CREATE: criação de registro
    UPDATE: atualização de registro
    DELETE: exclusão de registro
    CONSOLIDATE: consolidação de período
    """

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CONSOLIDATE = "CONSOLIDATE"
    DECONSOLIDATE = "DECONSOLIDATE"


class TipoPendencia(str, Enum):
    """Tipos de pendência para consolidação.

    SEM_LANCAMENTO: dia útil sem nenhum lançamento
    LANCAMENTO_INCOMPLETO: soma de minutos abaixo do esperado
    INDISPONIBILIDADE_NAO_TRATADA: indisponibilidade sem registro adequado
    INCONSISTENCIA_CALENDARIO: problema com calendário (feriado x dia útil)
    """

    SEM_LANCAMENTO = "SEM_LANCAMENTO"
    LANCAMENTO_INCOMPLETO = "LANCAMENTO_INCOMPLETO"
    INDISPONIBILIDADE_NAO_TRATADA = "INDISPONIBILIDADE_NAO_TRATADA"
    INCONSISTENCIA_CALENDARIO = "INCONSISTENCIA_CALENDARIO"
