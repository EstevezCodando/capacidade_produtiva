"""Sincroniza blocos do macrocontrole em capacidade.tipo_atividade.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-15

Objetivo:
  - Popular capacidade.tipo_atividade com os blocos vindos de
    sap_snapshot.macrocontrole_bloco.
  - Manter sincronismo idempotente entre snapshot SAP e tipos de produção.
  - Não recriar estrutura já definida na migration base.
"""

from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Garante que tipos estáticos estejam com a nomenclatura final correta.
    op.execute(
        """
        UPDATE capacidade.tipo_atividade
        SET nome = CASE codigo::text
            WHEN 'BLOCO'       THEN 'Trabalho em Bloco'
            WHEN 'EXTERNA'     THEN 'Produção Diversos'
            WHEN 'AJUSTE'      THEN 'Atividade Administrativa'
            WHEN 'FERIAS'      THEN 'Férias'
            WHEN 'LICENCA'     THEN 'Dispensa Médica'
            WHEN 'CURSO'       THEN 'Curso/Capacitação'
            WHEN 'AFASTAMENTO' THEN 'Dispensa como recompensa'
            WHEN 'CAMPO'       THEN 'Trabalho de Campo'
            WHEN 'MILITAR'     THEN 'Atividade Militar'
            ELSE nome
        END,
        cor = CASE codigo::text
            WHEN 'BLOCO'       THEN '#5B8DEE'
            WHEN 'EXTERNA'     THEN '#14B8A6'
            WHEN 'AJUSTE'      THEN '#F59E0B'
            WHEN 'FERIAS'      THEN '#8B5CF6'
            WHEN 'LICENCA'     THEN '#EF4444'
            WHEN 'CURSO'       THEN '#10B981'
            WHEN 'AFASTAMENTO' THEN '#64748B'
            WHEN 'CAMPO'       THEN '#14B8A6'
            WHEN 'MILITAR'     THEN '#94A3B8'
            ELSE cor
        END
        WHERE bloco_id IS NULL
        """
    )

    # Insere blocos que ainda não existirem.
    op.execute(
        """
        INSERT INTO capacidade.tipo_atividade (codigo, nome, bloco_id, cor, grupo)
        SELECT
            'BLOCO',
            b.nome,
            b.id,
            '#5B8DEE',
            'PRODUCAO'
        FROM sap_snapshot.macrocontrole_bloco b
        WHERE NOT EXISTS (
            SELECT 1
            FROM capacidade.tipo_atividade ta
            WHERE ta.bloco_id = b.id
        )
        """
    )

    # Atualiza nome/cor/grupo dos blocos já existentes, garantindo sincronismo.
    op.execute(
        """
        UPDATE capacidade.tipo_atividade ta
        SET
            nome = b.nome,
            cor = '#5B8DEE',
            grupo = 'PRODUCAO'::capacidade.grupo_atividade
        FROM sap_snapshot.macrocontrole_bloco b
        WHERE ta.bloco_id = b.id
          AND ta.codigo = 'BLOCO'::capacidade.codigo_atividade
        """
    )

    # Remove tipos de bloco que não existem mais no snapshot.
    # Isso mantém capacidade.tipo_atividade aderente às possibilidades
    # correntes de produção vindas do SAP.
    op.execute(
        """
        DELETE FROM capacidade.tipo_atividade ta
        WHERE ta.bloco_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM sap_snapshot.macrocontrole_bloco b
              WHERE b.id = ta.bloco_id
          )
        """
    )


def downgrade() -> None:
    # Remove apenas os tipos derivados de bloco sincronizados do SAP.
    op.execute(
        """
        DELETE FROM capacidade.tipo_atividade
        WHERE bloco_id IS NOT NULL
        """
    )

    # Reforça os nomes/cor padrão dos tipos estáticos.
    op.execute(
        """
        UPDATE capacidade.tipo_atividade
        SET nome = CASE codigo::text
            WHEN 'BLOCO'       THEN 'Trabalho em Bloco'
            WHEN 'EXTERNA'     THEN 'Produção Diversos'
            WHEN 'AJUSTE'      THEN 'Atividade Administrativa'
            WHEN 'FERIAS'      THEN 'Férias'
            WHEN 'LICENCA'     THEN 'Dispensa Médica'
            WHEN 'CURSO'       THEN 'Curso/Capacitação'
            WHEN 'AFASTAMENTO' THEN 'Dispensa como recompensa'
            WHEN 'CAMPO'       THEN 'Trabalho de Campo'
            WHEN 'MILITAR'     THEN 'Atividade Militar'
            ELSE nome
        END,
        cor = CASE codigo::text
            WHEN 'BLOCO'       THEN '#5B8DEE'
            WHEN 'EXTERNA'     THEN '#14B8A6'
            WHEN 'AJUSTE'      THEN '#F59E0B'
            WHEN 'FERIAS'      THEN '#8B5CF6'
            WHEN 'LICENCA'     THEN '#EF4444'
            WHEN 'CURSO'       THEN '#10B981'
            WHEN 'AFASTAMENTO' THEN '#64748B'
            WHEN 'CAMPO'       THEN '#14B8A6'
            WHEN 'MILITAR'     THEN '#94A3B8'
            ELSE cor
        END
        WHERE bloco_id IS NULL
        """
    )