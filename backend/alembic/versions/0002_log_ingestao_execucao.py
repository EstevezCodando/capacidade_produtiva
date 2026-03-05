"""Cria schema log e tabela log.ingestao_execucao.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS log")

    op.create_table(
        "ingestao_execucao",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'em_andamento'"), nullable=False),
        sa.Column("disparado_por", sa.String(length=255), nullable=False),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("counts", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("mensagem_erro", sa.Text(), nullable=True),
        schema="log",
    )

    op.create_index(
        "ix_log_ingestao_execucao_iniciado_em",
        "ingestao_execucao",
        ["iniciado_em"],
        schema="log",
    )

    op.create_index(
        "ix_log_ingestao_execucao_status",
        "ingestao_execucao",
        ["status"],
        schema="log",
    )


def downgrade() -> None:
    op.drop_index("ix_log_ingestao_execucao_status", table_name="ingestao_execucao", schema="log")
    op.drop_index("ix_log_ingestao_execucao_iniciado_em", table_name="ingestao_execucao", schema="log")
    op.drop_table("ingestao_execucao", schema="log")
    op.execute("DROP SCHEMA IF EXISTS log")
