from datetime import date

from pydantic import BaseModel, Field


class FilingTrendPoint(BaseModel):
    date: date
    count: int


class AnalyticsSummaryResponse(BaseModel):
    """
    Response schema for GET /analytics/summary. Deliberately the same
    shape regardless of the caller's role, only which complaints get
    counted changes (see get_analytics_summary), so the frontend's 3
    analytics pages (citizen/staff/admin) can all consume this without
    a separate schema each.
    """

    total: int

    status_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of visible complaints per status value, statuses with zero omitted.",
    )

    category_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of visible complaints per category value, categories with zero omitted.",
    )

    filing_trend: list[FilingTrendPoint] = Field(
        default_factory=list,
        description="One entry per day for the last 14 days (oldest first), zero-filled for days with no filings.",
    )
