"""add critic_review per-outlet OpenCritic review fact

Revision ID: f1d3b5a7c9e3
Revises: e9c1b3d5f7a1
Create Date: 2026-09-04

"""
import sqlalchemy as sa
from alembic import op

revision = 'f1d3b5a7c9e3'
down_revision = 'e9c1b3d5f7a1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'critic_review',
        sa.Column('criticreviewid', sa.BigInteger(), nullable=False),
        sa.Column('gameid', sa.BigInteger(), nullable=False),
        sa.Column('opencritic_id', sa.BigInteger(), nullable=False,
                  comment='OpenCritic game id the review was fetched '
                          'under.'),
        sa.Column('review_id', sa.Text(), nullable=False,
                  comment="OpenCritic's own review id, kept as text so "
                          'an id-format change never drops rows.'),
        sa.Column('outlet', sa.Text(), nullable=True,
                  comment='Outlet name as published.'),
        sa.Column('outlet_id', sa.BigInteger(), nullable=True,
                  comment='OpenCritic outlet id; NULL when absent.'),
        sa.Column('author', sa.Text(), nullable=True,
                  comment='Author names joined with ", "; NULL when '
                          'absent.'),
        sa.Column('score', sa.Numeric(), nullable=True,
                  comment='Score on the 0-100 scale; NULL for an '
                          'unscored review.'),
        sa.Column('published_date', sa.Date(), nullable=True,
                  comment='UTC date the review was published; NULL '
                          'when absent.'),
        sa.Column('url', sa.Text(), nullable=True,
                  comment="The review on the outlet's site."),
        sa.Column('fetched_at', sa.DateTime(), nullable=False,
                  comment='Naive UTC; the last sweep that touched the '
                          "row - the lane's rotation watermark (max "
                          'per gameid).'),
        sa.ForeignKeyConstraint(['gameid'], ['games.game.gameid']),
        sa.PrimaryKeyConstraint('criticreviewid'),
        sa.UniqueConstraint('review_id', name='uq_critic_review_id'),
        schema='games',
        comment='Per-outlet OpenCritic reviews per game - the '
                'distribution behind critic_score. Sparse by design: '
                "a title's reviews land when the review call budget "
                'reaches it, newest first and incremental, so absence '
                'means "not fetched yet", never "unreviewed", and a '
                'title past the page cap holds its newest reviews '
                'rather than the whole set. score is NULL for an '
                'unscored review.',
    )
    op.create_index('ix_critic_review_gameid', 'critic_review',
                    ['gameid'], schema='games')
    op.create_index('ix_critic_review_published', 'critic_review',
                    ['published_date'], schema='games')


def downgrade():
    op.drop_index('ix_critic_review_published',
                  table_name='critic_review', schema='games')
    op.drop_index('ix_critic_review_gameid', table_name='critic_review',
                  schema='games')
    op.drop_table('critic_review', schema='games')
