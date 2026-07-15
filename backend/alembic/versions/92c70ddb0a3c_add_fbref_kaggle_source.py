"""add fbref_kaggle source

Revision ID: 92c70ddb0a3c
Revises: e14967f8d44c
Create Date: 2026-07-15 15:10:33.479807
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '92c70ddb0a3c'
down_revision: Union[str, None] = 'e14967f8d44c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW = "('fbref', 'fbref_kaggle', 'understat', 'transfermarkt', 'clubelo', 'statsbomb')"
OLD = "('fbref', 'understat', 'transfermarkt', 'clubelo', 'statsbomb')"


def _set(constraint, table, values):
    op.drop_constraint(constraint, table, type_="check")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {constraint} CHECK (source IN {values})")


def upgrade() -> None:
    _set("ck_pss_source", "player_season_stats", NEW)
    _set("ck_xref_source", "entity_xref", NEW)


def downgrade() -> None:
    _set("ck_pss_source", "player_season_stats", OLD)
    _set("ck_xref_source", "entity_xref", OLD)
