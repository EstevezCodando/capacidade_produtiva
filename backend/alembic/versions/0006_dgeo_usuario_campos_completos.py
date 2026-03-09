"""Adiciona tipo_turno_id, administrador e uuid a sap_snapshot.dgeo_usuario.

Motivacao:
    A tabela sap_snapshot.dgeo_usuario foi criada originalmente com apenas
    6 campos (id, login, nome, nome_guerra, tipo_posto_grad_id, ativo).
    O schema real de sap.dgeo.usuario contem tambem:
        - tipo_turno_id    (smallint)
        - administrador    (boolean) -- necessario para o middleware JWT
        - uuid             (uuid)    -- identificador unico usado no JWT

    O campo uuid e essencial: o JWT emitido pelo servico de autenticacao
    usa uuid como identificador do usuario (claim "uuid").
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# Variaveis obrigatorias do Alembic — lidas pelo framework para montar o grafo
# de dependencias entre migracoes. Devem ser declaradas no escopo do modulo.
revision: str = "0006"
down_revision: str = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dgeo_usuario",
        sa.Column("tipo_turno_id", sa.SmallInteger(), nullable=True),
        schema="sap_snapshot",
    )
    op.add_column(
        "dgeo_usuario",
        sa.Column("administrador", sa.Boolean(), nullable=True, server_default="false"),
        schema="sap_snapshot",
    )
    op.add_column(
        "dgeo_usuario",
        sa.Column("uuid", sa.UUID(as_uuid=True), nullable=True),
        schema="sap_snapshot",
    )


def downgrade() -> None:
    op.drop_column("dgeo_usuario", "uuid", schema="sap_snapshot")
    op.drop_column("dgeo_usuario", "administrador", schema="sap_snapshot")
    op.drop_column("dgeo_usuario", "tipo_turno_id", schema="sap_snapshot")
