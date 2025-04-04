"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-04-03 17:32:10.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_name', sa.String(), nullable=False),
        sa.Column('account_number', sa.String()),
        sa.Column('bank_name', sa.String(), nullable=False),
        sa.Column('bank_branch', sa.String()),
        sa.Column('ifsc_code', sa.String()),
        sa.Column('tally_ledger_name', sa.String()),
        sa.Column('is_integrated', sa.Boolean(), default=False),
        sa.Column('integration_settings', sa.String()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create statements table
    op.create_table(
        'statements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('bank_name', sa.String(), nullable=False),
        sa.Column('statement_period_start', sa.DateTime()),
        sa.Column('statement_period_end', sa.DateTime()),
        sa.Column('opening_balance', sa.Float()),
        sa.Column('closing_balance', sa.Float()),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_format', sa.Enum('PDF', 'IMAGE', 'CSV', 'EXCEL', name='statement_format'), nullable=False),
        sa.Column('file_size', sa.Integer()),
        sa.Column('processing_status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'VALIDATED', name='processing_status'), nullable=False),
        sa.Column('processing_notes', sa.Text()),
        sa.Column('parser_used', sa.String()),
        sa.Column('extraction_duration', sa.Float()),
        sa.Column('error_message', sa.Text()),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('statement_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('transaction_type', sa.Enum('CREDIT', 'DEBIT', name='transaction_type'), nullable=False),
        sa.Column('balance', sa.Float()),
        sa.Column('reference_number', sa.String()),
        sa.Column('raw_description', sa.String()),
        sa.Column('bank_category', sa.String()),
        sa.Column('normalized_description', sa.String()),
        sa.Column('confidence_score', sa.Float(), default=1.0),
        sa.Column('extraction_method', sa.String()),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSED', 'FAILED', 'VERIFIED', name='transaction_status'), default='PENDING'),
        sa.Column('is_duplicate', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['statement_id'], ['statements.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)
    op.create_index(op.f('ix_statements_account_id'), 'statements', ['account_id'], unique=False)
    op.create_index(op.f('ix_transactions_statement_id'), 'transactions', ['statement_id'], unique=False)
    op.create_index(op.f('ix_transactions_date'), 'transactions', ['date'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_date'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_statement_id'), table_name='transactions')
    op.drop_index(op.f('ix_statements_account_id'), table_name='statements')
    op.drop_index(op.f('ix_accounts_user_id'), table_name='accounts')
    op.drop_table('transactions')
    op.drop_table('statements')
    op.drop_table('accounts')