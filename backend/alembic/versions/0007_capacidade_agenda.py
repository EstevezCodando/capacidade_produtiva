"""Cria schema capacidade e tabelas de agenda, lançamentos e auditoria.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-10
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # Criar schema
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS capacidade")

    # ─────────────────────────────────────────────────────────────────────────
    # Criar tipos ENUM já no estado final
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE capacidade.codigo_atividade AS ENUM (
            'BLOCO',
            'EXTERNA',
            'AJUSTE',
            'FERIAS',
            'LICENCA',
            'CURSO',
            'AFASTAMENTO',
            'CAMPO',
            'MILITAR'
        )
    """)

    op.execute("""
        CREATE TYPE capacidade.grupo_atividade AS ENUM (
            'PRODUCAO', 'INDISPONIBILIDADE', 'AJUSTE'
        )
    """)

    op.execute("""
        CREATE TYPE capacidade.faixa_minuto_enum AS ENUM ('NORMAL', 'EXTRA')
    """)

    op.execute("""
        CREATE TYPE capacidade.status_dia_enum AS ENUM ('ABERTO', 'CONSOLIDADO')
    """)

    op.execute("""
        CREATE TYPE capacidade.tipo_indisponibilidade_enum AS ENUM (
            'FERIAS', 'LICENCA', 'CURSO', 'AFASTAMENTO'
        )
    """)

    op.execute("""
        CREATE TYPE capacidade.acao_auditoria_enum AS ENUM (
            'CREATE', 'UPDATE', 'DELETE', 'CONSOLIDATE'
        )
    """)

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: tipo_atividade
    # Observação:
    #   - tipos estáticos usam bloco_id IS NULL
    #   - tipos sincronizados de macrocontrole_bloco usam bloco_id IS NOT NULL
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "tipo_atividade",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "codigo",
            postgresql.ENUM(
                "BLOCO",
                "EXTERNA",
                "AJUSTE",
                "FERIAS",
                "LICENCA",
                "CURSO",
                "AFASTAMENTO",
                "CAMPO",
                "MILITAR",
                name="codigo_atividade",
                schema="capacidade",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column(
            "grupo",
            postgresql.ENUM(
                "PRODUCAO",
                "INDISPONIBILIDADE",
                "AJUSTE",
                name="grupo_atividade",
                schema="capacidade",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("bloco_id", sa.Integer(), nullable=True),
        sa.Column("cor", sa.String(length=7), nullable=False, server_default="#5B8DEE"),
        schema="capacidade",
    )

    op.execute("""
        CREATE UNIQUE INDEX ux_tipo_atividade_codigo_sem_bloco
        ON capacidade.tipo_atividade (codigo)
        WHERE bloco_id IS NULL
    """)

    op.execute("""
        CREATE UNIQUE INDEX ux_tipo_atividade_bloco_id
        ON capacidade.tipo_atividade (bloco_id)
        WHERE bloco_id IS NOT NULL
    """)

    op.execute("""
        INSERT INTO capacidade.tipo_atividade (codigo, nome, grupo, bloco_id, cor) VALUES
        ('BLOCO', 'Trabalho em Bloco', 'PRODUCAO', NULL, '#5B8DEE'),
        ('EXTERNA', 'Produção Diversos', 'PRODUCAO', NULL, '#14B8A6'),
        ('AJUSTE', 'Atividade Administrativa', 'AJUSTE', NULL, '#F59E0B'),
        ('FERIAS', 'Férias', 'INDISPONIBILIDADE', NULL, '#8B5CF6'),
        ('LICENCA', 'Dispensa Médica', 'INDISPONIBILIDADE', NULL, '#EF4444'),
        ('CURSO', 'Curso/Capacitação', 'INDISPONIBILIDADE', NULL, '#10B981'),
        ('AFASTAMENTO', 'Dispensa como recompensa', 'INDISPONIBILIDADE', NULL, '#64748B'),
        ('CAMPO', 'Trabalho de Campo', 'PRODUCAO', NULL, '#14B8A6'),
        ('MILITAR', 'Atividade Militar', 'AJUSTE', NULL, '#94A3B8')
    """)

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: parametro_capacidade
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "parametro_capacidade",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("minutos_dia_util_default", sa.Integer(), nullable=False, server_default="360"),
        sa.Column("minutos_extra_maximo_default", sa.Integer(), nullable=False, server_default="240"),
        sa.Column("data_inicio_vigencia", sa.Date(), nullable=False),
        sa.Column("data_fim_vigencia", sa.Date(), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("minutos_dia_util_default > 0", name="ck_minutos_dia_util_positivo"),
        sa.CheckConstraint("minutos_extra_maximo_default >= 0", name="ck_minutos_extra_nao_negativo"),
        sa.CheckConstraint(
            "data_fim_vigencia IS NULL OR data_fim_vigencia >= data_inicio_vigencia",
            name="ck_vigencia_valida",
        ),
        schema="capacidade",
    )

    op.create_index(
        "ix_parametro_capacidade_vigencia",
        "parametro_capacidade",
        ["data_inicio_vigencia", "data_fim_vigencia"],
        schema="capacidade",
    )

    op.execute("""
        INSERT INTO capacidade.parametro_capacidade
        (minutos_dia_util_default, minutos_extra_maximo_default, data_inicio_vigencia, criado_por)
        VALUES (360, 240, '2026-01-01', 1)
    """)

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: feriado
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "feriado",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("criado_por", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("data", name="uq_feriado_data"),
        schema="capacidade",
    )

    op.create_index("ix_feriado_data", "feriado", ["data"], schema="capacidade")

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: indisponibilidade_usuario
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "indisponibilidade_usuario",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo_atividade_id",
            sa.Integer(),
            sa.ForeignKey("capacidade.tipo_atividade.id"),
            nullable=False,
        ),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("data_fim >= data_inicio", name="ck_indisponibilidade_periodo_valido"),
        schema="capacidade",
    )

    op.create_index(
        "ix_indisponibilidade_usuario_id",
        "indisponibilidade_usuario",
        ["usuario_id"],
        schema="capacidade",
    )

    op.create_index(
        "ix_indisponibilidade_periodo",
        "indisponibilidade_usuario",
        ["data_inicio", "data_fim"],
        schema="capacidade",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: capacidade_dia
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "capacidade_dia",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("minutos_capacidade_normal_prevista", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minutos_capacidade_extra_permitida", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eh_dia_util", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("eh_feriado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("eh_indisponivel", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "tipo_indisponibilidade",
            postgresql.ENUM(
                "FERIAS",
                "LICENCA",
                "CURSO",
                "AFASTAMENTO",
                name="tipo_indisponibilidade_enum",
                schema="capacidade",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "status_dia",
            postgresql.ENUM(
                "ABERTO",
                "CONSOLIDADO",
                name="status_dia_enum",
                schema="capacidade",
                create_type=False,
            ),
            nullable=False,
            server_default="ABERTO",
        ),
        sa.Column(
            "origem_parametro_capacidade",
            sa.Integer(),
            sa.ForeignKey("capacidade.parametro_capacidade.id"),
            nullable=True,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("usuario_id", "data", name="uq_capacidade_dia_usuario_data"),
        sa.CheckConstraint("minutos_capacidade_normal_prevista >= 0", name="ck_capacidade_normal_nao_negativa"),
        sa.CheckConstraint("minutos_capacidade_extra_permitida >= 0", name="ck_capacidade_extra_nao_negativa"),
        schema="capacidade",
    )

    op.create_index(
        "ix_capacidade_dia_usuario_data",
        "capacidade_dia",
        ["usuario_id", "data"],
        schema="capacidade",
    )

    op.create_index(
        "ix_capacidade_dia_data",
        "capacidade_dia",
        ["data"],
        schema="capacidade",
    )

    op.create_index(
        "ix_capacidade_dia_status",
        "capacidade_dia",
        ["status_dia"],
        schema="capacidade",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: agenda_prevista_admin
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "agenda_prevista_admin",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("bloco_id", sa.Integer(), nullable=True),
        sa.Column("minutos_planejados_normais", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minutos_planejados_extras", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("usuario_id", "data", "bloco_id", name="uq_agenda_prevista_usuario_data_bloco"),
        sa.CheckConstraint("minutos_planejados_normais >= 0", name="ck_minutos_planejados_normais_nao_negativo"),
        sa.CheckConstraint("minutos_planejados_extras >= 0", name="ck_minutos_planejados_extras_nao_negativo"),
        schema="capacidade",
    )

    op.create_index(
        "ix_agenda_prevista_usuario_data",
        "agenda_prevista_admin",
        ["usuario_id", "data"],
        schema="capacidade",
    )

    op.create_index(
        "ix_agenda_prevista_data",
        "agenda_prevista_admin",
        ["data"],
        schema="capacidade",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: agenda_lancamento
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "agenda_lancamento",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("data_lancamento", sa.Date(), nullable=False),
        sa.Column("bloco_id", sa.Integer(), nullable=True),
        sa.Column(
            "tipo_atividade_id",
            sa.Integer(),
            sa.ForeignKey("capacidade.tipo_atividade.id"),
            nullable=False,
        ),
        sa.Column(
            "faixa_minuto",
            postgresql.ENUM(
                "NORMAL",
                "EXTRA",
                name="faixa_minuto_enum",
                schema="capacidade",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("minutos", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=False),
        sa.Column("atualizado_por", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("minutos > 0", name="ck_minutos_positivo"),
        schema="capacidade",
    )

    op.create_index(
        "ix_agenda_lancamento_usuario_data",
        "agenda_lancamento",
        ["usuario_id", "data_lancamento"],
        schema="capacidade",
    )

    op.create_index(
        "ix_agenda_lancamento_data",
        "agenda_lancamento",
        ["data_lancamento"],
        schema="capacidade",
    )

    op.create_index(
        "ix_agenda_lancamento_bloco",
        "agenda_lancamento",
        ["bloco_id"],
        schema="capacidade",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Tabela: audit_log
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entidade", sa.String(100), nullable=False),
        sa.Column("entidade_id", sa.Integer(), nullable=False),
        sa.Column(
            "acao",
            postgresql.ENUM(
                "CREATE",
                "UPDATE",
                "DELETE",
                "CONSOLIDATE",
                name="acao_auditoria_enum",
                schema="capacidade",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("antes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("depois_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("usuario_executor", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="capacidade",
    )

    op.create_index(
        "ix_audit_log_entidade",
        "audit_log",
        ["entidade", "entidade_id"],
        schema="capacidade",
    )

    op.create_index(
        "ix_audit_log_timestamp",
        "audit_log",
        ["timestamp"],
        schema="capacidade",
    )

    op.create_index(
        "ix_audit_log_usuario",
        "audit_log",
        ["usuario_executor"],
        schema="capacidade",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Trigger para atualizar atualizado_em automaticamente
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION capacidade.atualizar_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.atualizado_em = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_capacidade_dia_atualizado_em
        BEFORE UPDATE ON capacidade.capacidade_dia
        FOR EACH ROW EXECUTE FUNCTION capacidade.atualizar_timestamp();
    """)

    op.execute("""
        CREATE TRIGGER trigger_agenda_prevista_atualizado_em
        BEFORE UPDATE ON capacidade.agenda_prevista_admin
        FOR EACH ROW EXECUTE FUNCTION capacidade.atualizar_timestamp();
    """)

    op.execute("""
        CREATE TRIGGER trigger_agenda_lancamento_atualizado_em
        BEFORE UPDATE ON capacidade.agenda_lancamento
        FOR EACH ROW EXECUTE FUNCTION capacidade.atualizar_timestamp();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_agenda_lancamento_atualizado_em ON capacidade.agenda_lancamento")
    op.execute("DROP TRIGGER IF EXISTS trigger_agenda_prevista_atualizado_em ON capacidade.agenda_prevista_admin")
    op.execute("DROP TRIGGER IF EXISTS trigger_capacidade_dia_atualizado_em ON capacidade.capacidade_dia")
    op.execute("DROP FUNCTION IF EXISTS capacidade.atualizar_timestamp()")

    op.drop_table("audit_log", schema="capacidade")
    op.drop_table("agenda_lancamento", schema="capacidade")
    op.drop_table("agenda_prevista_admin", schema="capacidade")
    op.drop_table("capacidade_dia", schema="capacidade")
    op.drop_table("indisponibilidade_usuario", schema="capacidade")
    op.drop_table("feriado", schema="capacidade")
    op.drop_table("parametro_capacidade", schema="capacidade")
    op.drop_table("tipo_atividade", schema="capacidade")

    op.execute("DROP TYPE IF EXISTS capacidade.acao_auditoria_enum")
    op.execute("DROP TYPE IF EXISTS capacidade.tipo_indisponibilidade_enum")
    op.execute("DROP TYPE IF EXISTS capacidade.status_dia_enum")
    op.execute("DROP TYPE IF EXISTS capacidade.faixa_minuto_enum")
    op.execute("DROP TYPE IF EXISTS capacidade.grupo_atividade")
    op.execute("DROP TYPE IF EXISTS capacidade.codigo_atividade")

    op.execute("DROP SCHEMA IF EXISTS capacidade CASCADE")