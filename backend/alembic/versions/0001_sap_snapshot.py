"""Cria schema sap_snapshot com todas as tabelas espelho do SAP.

Revision ID: 0001
Revises: -
Create Date: 2025-01-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS sap_snapshot")

    # ------------------------------------------------------------------
    # Domínios
    # ------------------------------------------------------------------
    op.create_table(
        "dominio_status",
        sa.Column("code", sa.SmallInteger(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        schema="sap_snapshot",
    )
    op.create_table(
        "dominio_tipo_situacao",
        sa.Column("code", sa.SmallInteger(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=True),
        schema="sap_snapshot",
    )
    op.create_table(
        "dominio_tipo_etapa",
        sa.Column("code", sa.SmallInteger(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        schema="sap_snapshot",
    )
    op.create_table(
        "dominio_tipo_fase",
        sa.Column("code", sa.SmallInteger(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cor", sa.String(255), nullable=False),
        schema="sap_snapshot",
    )

    # ------------------------------------------------------------------
    # Usuários
    # ------------------------------------------------------------------
    op.create_table(
        "dgeo_usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(255), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("nome_guerra", sa.String(255), nullable=False),
        sa.Column("tipo_posto_grad_id", sa.SmallInteger(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        schema="sap_snapshot",
    )

    # ------------------------------------------------------------------
    # Hierarquia produtiva (ordem de dependência)
    # ------------------------------------------------------------------
    op.create_table(
        "macrocontrole_linha_producao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("nome_abrev", sa.String(255), nullable=False),
        schema="sap_snapshot",
    )
    op.create_table(
        "macrocontrole_fase",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo_fase_id", sa.SmallInteger(), nullable=False),
        sa.Column("linha_producao_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_table(
        "macrocontrole_subfase",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("fase_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_subfase_fase_id", "macrocontrole_subfase", ["fase_id"], schema="sap_snapshot"
    )
    op.create_table(
        "macrocontrole_projeto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("nome_abrev", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("status_id", sa.SmallInteger(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_table(
        "macrocontrole_lote",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("nome_abrev", sa.String(255), nullable=False),
        sa.Column("denominador_escala", sa.Integer(), nullable=False),
        sa.Column("linha_producao_id", sa.Integer(), nullable=False),
        sa.Column("projeto_id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("status_id", sa.SmallInteger(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_lote_projeto_id", "macrocontrole_lote", ["projeto_id"], schema="sap_snapshot"
    )
    op.create_table(
        "macrocontrole_bloco",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("prioridade", sa.Integer(), nullable=False),
        sa.Column("status_id", sa.SmallInteger(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_bloco_lote_id", "macrocontrole_bloco", ["lote_id"], schema="sap_snapshot"
    )
    op.create_table(
        "macrocontrole_etapa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo_etapa_id", sa.SmallInteger(), nullable=False),
        sa.Column("subfase_id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_etapa_subfase_id", "macrocontrole_etapa", ["subfase_id"], schema="sap_snapshot"
    )
    op.create_index(
        "ix_snap_etapa_lote_id", "macrocontrole_etapa", ["lote_id"], schema="sap_snapshot"
    )
    op.create_table(
        "macrocontrole_unidade_trabalho",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=True),
        sa.Column("epsg", sa.String(5), nullable=False),
        sa.Column("dado_producao_id", sa.Integer(), nullable=False),
        sa.Column("subfase_id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("bloco_id", sa.Integer(), nullable=False),
        sa.Column("disponivel", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dificuldade", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "tempo_estimado_minutos", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("prioridade", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_ut_subfase_id",
        "macrocontrole_unidade_trabalho",
        ["subfase_id"],
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_ut_bloco_id",
        "macrocontrole_unidade_trabalho",
        ["bloco_id"],
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_ut_lote_id",
        "macrocontrole_unidade_trabalho",
        ["lote_id"],
        schema="sap_snapshot",
    )

    # ------------------------------------------------------------------
    # Fatos — atividade (janela 180 dias)
    # ------------------------------------------------------------------
    op.create_table(
        "macrocontrole_atividade",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etapa_id", sa.Integer(), nullable=False),
        sa.Column("unidade_trabalho_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("tipo_situacao_id", sa.SmallInteger(), nullable=False),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_atv_etapa_id", "macrocontrole_atividade", ["etapa_id"], schema="sap_snapshot"
    )
    op.create_index(
        "ix_snap_atv_ut_id",
        "macrocontrole_atividade",
        ["unidade_trabalho_id"],
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_atv_usuario_id",
        "macrocontrole_atividade",
        ["usuario_id"],
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_atv_data_fim", "macrocontrole_atividade", ["data_fim"], schema="sap_snapshot"
    )

    # ------------------------------------------------------------------
    # Perfis de produção
    # ------------------------------------------------------------------
    op.create_table(
        "macrocontrole_perfil_producao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        schema="sap_snapshot",
    )
    op.create_table(
        "macrocontrole_perfil_producao_etapa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("perfil_producao_id", sa.Integer(), nullable=False),
        sa.Column("subfase_id", sa.Integer(), nullable=False),
        sa.Column("tipo_etapa_id", sa.SmallInteger(), nullable=False),
        sa.Column("prioridade", sa.Integer(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_ppe_perfil_id",
        "macrocontrole_perfil_producao_etapa",
        ["perfil_producao_id"],
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_ppe_subfase_id",
        "macrocontrole_perfil_producao_etapa",
        ["subfase_id"],
        schema="sap_snapshot",
    )
    op.create_table(
        "macrocontrole_perfil_producao_operador",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("perfil_producao_id", sa.Integer(), nullable=False),
        schema="sap_snapshot",
    )
    op.create_index(
        "ix_snap_ppo_usuario_id",
        "macrocontrole_perfil_producao_operador",
        ["usuario_id"],
        schema="sap_snapshot",
    )


def downgrade() -> None:
    for idx, tbl in [
        ("ix_snap_ppo_usuario_id", "macrocontrole_perfil_producao_operador"),
        ("ix_snap_ppe_subfase_id", "macrocontrole_perfil_producao_etapa"),
        ("ix_snap_ppe_perfil_id", "macrocontrole_perfil_producao_etapa"),
        ("ix_snap_atv_data_fim", "macrocontrole_atividade"),
        ("ix_snap_atv_usuario_id", "macrocontrole_atividade"),
        ("ix_snap_atv_ut_id", "macrocontrole_atividade"),
        ("ix_snap_atv_etapa_id", "macrocontrole_atividade"),
        ("ix_snap_ut_lote_id", "macrocontrole_unidade_trabalho"),
        ("ix_snap_ut_bloco_id", "macrocontrole_unidade_trabalho"),
        ("ix_snap_ut_subfase_id", "macrocontrole_unidade_trabalho"),
        ("ix_snap_etapa_lote_id", "macrocontrole_etapa"),
        ("ix_snap_etapa_subfase_id", "macrocontrole_etapa"),
        ("ix_snap_bloco_lote_id", "macrocontrole_bloco"),
        ("ix_snap_lote_projeto_id", "macrocontrole_lote"),
        ("ix_snap_subfase_fase_id", "macrocontrole_subfase"),
    ]:
        op.drop_index(idx, table_name=tbl, schema="sap_snapshot")

    for tbl in [
        "macrocontrole_perfil_producao_operador",
        "macrocontrole_perfil_producao_etapa",
        "macrocontrole_perfil_producao",
        "macrocontrole_atividade",
        "macrocontrole_unidade_trabalho",
        "macrocontrole_etapa",
        "macrocontrole_bloco",
        "macrocontrole_lote",
        "macrocontrole_projeto",
        "macrocontrole_subfase",
        "macrocontrole_fase",
        "macrocontrole_linha_producao",
        "dgeo_usuario",
        "dominio_tipo_fase",
        "dominio_tipo_etapa",
        "dominio_tipo_situacao",
        "dominio_status",
    ]:
        op.drop_table(tbl, schema="sap_snapshot")

    op.execute("DROP SCHEMA IF EXISTS sap_snapshot")
