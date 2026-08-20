from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, UUID4


class TokenClaims(BaseModel):
    sub: str
    email: str
    role: str
    org_id: Optional[str] = None
    exp: int
    token_type: str = "access"


class MetricResult(BaseModel):
    name: str
    value: float
    unit: Optional[str] = None
    change_pct: Optional[float] = Field(None, description="% change vs previous period")


class KPISummary(BaseModel):
    dataset_id: UUID4
    total: float
    average: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    growth_rate: Optional[float] = Field(None, description="Period-over-period growth %")
    computed_at: datetime


class TrendPoint(BaseModel):
    period: str
    value: float
    moving_avg: Optional[float] = None


class TrendAnalysis(BaseModel):
    dataset_id: UUID4
    direction: str  # "up", "down", "flat"
    slope: float
    r_squared: float
    points: List[TrendPoint]


class AnomalyPoint(BaseModel):
    index: int
    value: float
    expected: float
    z_score: float
    severity: str  # "low", "medium", "high"


class AnomalyReport(BaseModel):
    dataset_id: UUID4
    anomaly_count: int
    anomalies: List[AnomalyPoint]
    threshold_z: float = 2.5


class ColumnStats(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    numeric_stats: Optional[Dict[str, float]] = None


class InsightItem(BaseModel):
    type: str  # "kpi", "trend", "anomaly", "correlation"
    title: str
    description: str
    severity: str = "info"  # "info", "warning", "critical"
    data: Optional[Dict[str, Any]] = None


class AnalyticsResponse(BaseModel):
    dataset_id: UUID4
    org_id: str
    kpi: KPISummary
    trends: TrendAnalysis
    anomalies: AnomalyReport
    column_stats: List[ColumnStats]
    computed_at: datetime


class InsightsResponse(BaseModel):
    dataset_id: UUID4
    insights: List[InsightItem]
    generated_at: datetime


class ProcessingRequest(BaseModel):
    dataset_id: UUID4


class ProcessingResponse(BaseModel):
    dataset_id: UUID4
    status: str
    message: str
