"""Ajusta nomes de tipos_atividade e adiciona CAMPO e MILITAR.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-17

Mudanças:
  - Renomeia tipos existentes conforme nova nomenclatura operacional
  - Adiciona valores CAMPO e MILITAR ao enum capacidade.codigo_atividade
  - Insere registros para Trabalho de Campo e Atividade Militar
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Adiciona novos valores ao enum PostgreSQL ──────────────────────────
    # ALTER TYPE não pode rodar dentro de uma transação em algumas versões do PG.
    # Executamos fora do bloco de transação padrão do Alembic.
    op.execute("ALTER TYPE capacidade.codigo_atividade ADD VALUE IF NOT EXISTS 'CAMPO'")
    op.execute("ALTER TYPE capacidade.codigo_atividade ADD VALUE IF NOT EXISTS 'MILITAR'")

    # ── 2. Renomeia tipos de atividade existentes ─────────────────────────────
    op.execute(
        """
        UPDATE capacidade.tipo_atividade
        SET nome = CASE codigo::text
            WHEN 'EXTERNA'     THEN 'Produção Diversos'
            WHEN 'LICENCA'     THEN 'Dispensa Médica'
            WHEN 'AFASTAMENTO' THEN 'Dispensa como recompensa'
            WHEN 'AJUSTE'      THEN 'Atividade Administrativa'
            ELSE nome
        END
        WHERE codigo::text IN ('EXTERNA', 'LICENCA', 'AFASTAMENTO', 'AJUSTE')
          AND bloco_id IS NULL
        """
    )

    # ── 3. Insere novos tipos (caso ainda não existam) ────────────────────────
    op.execute(
        """
        INSERT INTO capacidade.tipo_atividade (codigo, nome, grupo, cor)
        VALUES ('CAMPO', 'Trabalho de Campo', 'PRODUCAO', '#14B8A6')
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO capacidade.tipo_atividade (codigo, nome, grupo, cor)
        VALUES ('MILITAR', 'Atividade Militar', 'AJUSTE', '#94A3B8')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    # ── Remove registros inseridos ────────────────────────────────────────────
    op.execute(
        "DELETE FROM capacidade.tipo_atividade WHERE codigo::text IN ('CAMPO', 'MILITAR')"
    )

    # ── Reverte renomeações ───────────────────────────────────────────────────
    op.execute(
        """
        UPDATE capacidade.tipo_atividade
        SET nome = CASE codigo::text
            WHEN 'EXTERNA'     THEN 'Atividade Externa'
            WHEN 'LICENCA'     THEN 'Afastamentos Diversos'
            WHEN 'AFASTAMENTO' THEN 'Atividade Interna'
            WHEN 'AJUSTE'      THEN 'Atividade Administrativa'
            ELSE nome
        END
        WHERE codigo::text IN ('EXTERNA', 'LICENCA', 'AFASTAMENTO', 'AJUSTE')
          AND bloco_id IS NULL
        """
    )

    # Nota: valores de enum PostgreSQL não podem ser removidos via ALTER TYPE DROP VALUE.
    # Os valores 'CAMPO' e 'MILITAR' permanecem no enum após o downgrade.
