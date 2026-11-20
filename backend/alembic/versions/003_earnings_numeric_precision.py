"""Earnings numeric precision and flexible statement dates

Revision ID: 003_earnings_numeric_precision
Revises: 002_rls_policies
Create Date: 2026-11-20 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003_earnings_numeric_precision'
down_revision = '002_rls_policies'
branch_labels = None
depends_on = None

NUMERIC_COLUMNS = [
    'base_earnings',
    'order_payments',
    'incentives',
    'bonuses',
    'deductions',
    'penalties',
    'taxes',
    'net_amount',
]

def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Statement period start/end in earning_entries -> nullable=True
    if is_postgres:
        op.alter_column(
            'earning_entries',
            'statement_period_start',
            existing_type=sa.DateTime(),
            nullable=True,
        )
        op.alter_column(
            'earning_entries',
            'statement_period_end',
            existing_type=sa.DateTime(),
            nullable=True,
        )
        
        # 2. Monetary columns in earning_entries -> Numeric(10, 2)
        for col in NUMERIC_COLUMNS:
            op.alter_column(
                'earning_entries',
                col,
                existing_type=sa.Float(),
                type_=sa.Numeric(10, 2),
                postgresql_using=f"{col}::numeric(10,2)",
                server_default='0.00',
                nullable=False,
            )

        # 3. Monetary column in evidence_reports -> Numeric(10, 2)
        op.alter_column(
            'evidence_reports',
            'net_earnings_recorded',
            existing_type=sa.Float(),
            type_=sa.Numeric(10, 2),
            postgresql_using="net_earnings_recorded::numeric(10,2)",
            server_default='0.00',
            nullable=False,
        )
    else:
        with op.batch_alter_table('earning_entries') as batch_op:
            batch_op.alter_column(
                'statement_period_start',
                existing_type=sa.DateTime(),
                nullable=True,
            )
            batch_op.alter_column(
                'statement_period_end',
                existing_type=sa.DateTime(),
                nullable=True,
            )
            for col in NUMERIC_COLUMNS:
                batch_op.alter_column(
                    col,
                    existing_type=sa.Float(),
                    type_=sa.Numeric(10, 2),
                    server_default='0.00',
                    nullable=False,
                )
        with op.batch_alter_table('evidence_reports') as batch_op:
            batch_op.alter_column(
                'net_earnings_recorded',
                existing_type=sa.Float(),
                type_=sa.Numeric(10, 2),
                server_default='0.00',
                nullable=False,
            )

def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.alter_column(
            'evidence_reports',
            'net_earnings_recorded',
            existing_type=sa.Numeric(10, 2),
            type_=sa.Float(),
            postgresql_using="net_earnings_recorded::float",
            server_default='0.0',
            nullable=False,
        )
        for col in NUMERIC_COLUMNS:
            op.alter_column(
                'earning_entries',
                col,
                existing_type=sa.Numeric(10, 2),
                type_=sa.Float(),
                postgresql_using=f"{col}::float",
                server_default='0.0',
                nullable=False,
            )
        op.alter_column(
            'earning_entries',
            'statement_period_start',
            existing_type=sa.DateTime(),
            nullable=False,
        )
        op.alter_column(
            'earning_entries',
            'statement_period_end',
            existing_type=sa.DateTime(),
            nullable=False,
        )
    else:
        with op.batch_alter_table('evidence_reports') as batch_op:
            batch_op.alter_column(
                'net_earnings_recorded',
                existing_type=sa.Numeric(10, 2),
                type_=sa.Float(),
                server_default='0.0',
                nullable=False,
            )
        with op.batch_alter_table('earning_entries') as batch_op:
            for col in NUMERIC_COLUMNS:
                batch_op.alter_column(
                    col,
                    existing_type=sa.Numeric(10, 2),
                    type_=sa.Float(),
                    server_default='0.0',
                    nullable=False,
                )
            batch_op.alter_column(
                'statement_period_start',
                existing_type=sa.DateTime(),
                nullable=False,
            )
            batch_op.alter_column(
                'statement_period_end',
                existing_type=sa.DateTime(),
                nullable=False,
            )
