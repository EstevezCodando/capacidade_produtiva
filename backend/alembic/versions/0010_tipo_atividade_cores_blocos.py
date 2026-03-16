"""Adiciona cores e blocos sincronizados em capacidade.tipo_atividade.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tipo_atividade",
        sa.Column("bloco_id", sa.Integer(), nullable=True),
        schema="capacidade",
    )
    op.add_column(
        "tipo_atividade",
        sa.Column("cor", sa.String(length=7), nullable=False, server_default="#5B8DEE"),
        schema="capacidade",
    )

    op.execute("ALTER TABLE capacidade.tipo_atividade DROP CONSTRAINT IF EXISTS uq_tipo_atividade_codigo")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tipo_atividade_bloco_id ON capacidade.tipo_atividade (bloco_id) WHERE bloco_id IS NOT NULL"
    )

    op.execute(
        """
        UPDATE capacidade.tipo_atividade
        SET nome = CASE codigo::text
            WHEN 'BLOCO' THEN 'Trabalho em Bloco'
            WHEN 'EXTERNA' THEN 'Atividade Externa'
            WHEN 'AJUSTE' THEN 'Atividade Administrativa'
            WHEN 'FERIAS' THEN 'Férias'
            WHEN 'LICENCA' THEN 'Afastamentos Diversos'
            WHEN 'CURSO' THEN 'Curso/Capacitação'
            WHEN 'AFASTAMENTO' THEN 'Atividade Interna'
            ELSE nome
        END,
        cor = CASE codigo::text
            WHEN 'BLOCO' THEN '#5B8DEE'
            WHEN 'EXTERNA' THEN '#14B8A6'
            WHEN 'AJUSTE' THEN '#F59E0B'
            WHEN 'FERIAS' THEN '#8B5CF6'
            WHEN 'LICENCA' THEN '#EF4444'
            WHEN 'CURSO' THEN '#10B981'
            WHEN 'AFASTAMENTO' THEN '#64748B'
            ELSE cor
        END
        WHERE bloco_id IS NULL
        """
    )

    op.execute(
        """
        INSERT INTO capacidade.tipo_atividade (codigo, nome, bloco_id, cor, grupo)
        SELECT 'BLOCO', b.nome, b.id, '#5B8DEE', 'PRODUCAO'
        FROM sap_snapshot.macrocontrole_bloco b
        WHERE NOT EXISTS (
            SELECT 1 FROM capacidade.tipo_atividade ta WHERE ta.bloco_id = b.id
        )
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM capacidade.tipo_atividade WHERE bloco_id IS NOT NULL")
    op.execute("DROP INDEX IF EXISTS capacidade.ux_tipo_atividade_bloco_id")
    op.execute(
        "ALTER TABLE capacidade.tipo_atividade ADD CONSTRAINT uq_tipo_atividade_codigo UNIQUE (codigo)"
    )
    op.drop_column("tipo_atividade", "cor", schema="capacidade")
    op.drop_column("tipo_atividade", "bloco_id", schema="capacidade")
