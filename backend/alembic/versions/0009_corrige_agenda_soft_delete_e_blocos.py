"""Corrige soft delete da agenda e evita quebra após patch anterior.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-11
"""

from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE capacidade.agenda_prevista_admin
        ADD COLUMN IF NOT EXISTS em_uso boolean NOT NULL DEFAULT true
        """
    )
    op.execute(
        """
        ALTER TABLE capacidade.agenda_lancamento
        ADD COLUMN IF NOT EXISTS em_uso boolean NOT NULL DEFAULT true
        """
    )
    op.execute(
        """
        ALTER TABLE capacidade.agenda_prevista_admin
        DROP CONSTRAINT IF EXISTS uq_agenda_prevista_usuario_data_bloco
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_agenda_prevista_em_uso
        ON capacidade.agenda_prevista_admin (em_uso)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_agenda_lancamento_em_uso
        ON capacidade.agenda_lancamento (em_uso)
        """
    )
    

        op.execute(
        """
        ALTER TABLE capacidade.agenda_prevista_admin
        ADD COLUMN IF NOT EXISTS consolidado boolean NOT NULL DEFAULT false
        """
    )
    op.execute(
        """
        ALTER TABLE capacidade.agenda_lancamento
        ADD COLUMN IF NOT EXISTS consolidado boolean NOT NULL DEFAULT false
        """
    )
    op.execute(
        """
        ALTER TABLE capacidade.agenda_prevista_admin
        DROP CONSTRAINT IF EXISTS uq_agenda_prevista_usuario_data_bloco
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_agenda_prevista_consolidado
        ON capacidade.agenda_prevista_admin (consolidado)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_agenda_lancamento_consolidado
        ON capacidade.agenda_lancamento (consolidado)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS capacidade.ix_agenda_lancamento_em_uso")
    op.execute("DROP INDEX IF EXISTS capacidade.ix_agenda_prevista_em_uso")
    op.execute(
        """
        ALTER TABLE capacidade.agenda_prevista_admin
        ADD CONSTRAINT uq_agenda_prevista_usuario_data_bloco
        UNIQUE (usuario_id, data, bloco_id)
        """
    )
    op.execute(
        "ALTER TABLE capacidade.agenda_lancamento DROP COLUMN IF EXISTS em_uso"
    )
    op.execute(
        "ALTER TABLE capacidade.agenda_prevista_admin DROP COLUMN IF EXISTS em_uso"
    )
    

    op.execute("DROP INDEX IF EXISTS capacidade.ix_agenda_lancamento_consolidado")
    op.execute("DROP INDEX IF EXISTS capacidade.ix_agenda_prevista_consolidado")
    op.execute(
        """
        ALTER TABLE capacidade.agenda_prevista_admin
        ADD CONSTRAINT uq_agenda_prevista_usuario_data_bloco
        UNIQUE (usuario_id, data, bloco_id)
        """
    )
    op.execute(
        "ALTER TABLE capacidade.agenda_lancamento DROP COLUMN IF EXISTS consolidado"
    )
    op.execute(
        "ALTER TABLE capacidade.agenda_prevista_admin DROP COLUMN IF EXISTS consolidado"
    )

