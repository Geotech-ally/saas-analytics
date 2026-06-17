"""
Analytics endpoints — all require a valid Django-issued JWT.
"""
import asyncio
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from core.auth import get_current_user, require_org_member, verify_service_key
from schemas.analytics import (
    AnalyticsResponse,
    AnomalyReport,
    ColumnStats,
    InsightsResponse,
    KPISummary,
    ProcessingRequest,
    ProcessingResponse,
    TokenClaims,
    TrendAnalysis,
)
from services.analytics_service import (
    compute_kpis,
    detect_anomalies,
    detect_trends,
    generate_insights,
)
from services.data_loader import load_dataset

router = APIRouter(prefix="/api/v1", tags=["Analytics"])


@router.post("/datasets/{dataset_id}/process", response_model=ProcessingResponse)
async def trigger_processing(
    dataset_id: UUID,
    x_service_key: str = Header(..., alias="X-Service-Key"),
    claims: TokenClaims = Depends(require_org_member),
):
    """Internal endpoint called by Django when a new dataset is uploaded."""
    verify_service_key(x_service_key)
    # In production: push to Celery/RQ worker; here we return immediately
    return ProcessingResponse(
        dataset_id=dataset_id,
        status="queued",
        message="Dataset queued for processing.",
    )


@router.get("/analytics/{dataset_id}", response_model=AnalyticsResponse)
async def get_analytics(
    dataset_id: UUID,
    claims: TokenClaims = Depends(require_org_member),
):
    """Full analytics report for a dataset."""
    try:
        df = await asyncio.to_thread(load_dataset, str(dataset_id), claims.org_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {exc}")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        raise HTTPException(status_code=422, detail="No numeric columns found for analysis.")

    primary_col = numeric_cols[0]
    values: List[float] = df[primary_col].dropna().tolist()

    kpi = compute_kpis(values, dataset_id)
    trends = detect_trends(values, dataset_id)
    anomalies = detect_anomalies(values, dataset_id)

    col_stats: List[ColumnStats] = []
    for col in df.columns:
        s = df[col]
        numeric_stats = None
        if s.dtype.kind in "fiu":
            numeric_stats = {
                "mean": round(s.mean(), 4),
                "std": round(s.std(), 4),
                "min": round(s.min(), 4),
                "max": round(s.max(), 4),
            }
        col_stats.append(ColumnStats(
            name=col,
            dtype=str(s.dtype),
            non_null_count=int(s.notna().sum()),
            null_count=int(s.isna().sum()),
            unique_count=int(s.nunique()),
            numeric_stats=numeric_stats,
        ))

    return AnalyticsResponse(
        dataset_id=dataset_id,
        org_id=claims.org_id,
        kpi=kpi,
        trends=trends,
        anomalies=anomalies,
        column_stats=col_stats,
        computed_at=datetime.utcnow(),
    )


@router.get("/analytics/{dataset_id}/insights", response_model=InsightsResponse)
async def get_insights(
    dataset_id: UUID,
    claims: TokenClaims = Depends(require_org_member),
):
    """Natural-language insights derived from analytics."""
    try:
        df = await asyncio.to_thread(load_dataset, str(dataset_id), claims.org_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        raise HTTPException(status_code=422, detail="No numeric columns found.")

    values = df[numeric_cols[0]].dropna().tolist()
    kpi = compute_kpis(values, dataset_id)
    trends = detect_trends(values, dataset_id)
    anomalies = detect_anomalies(values, dataset_id)
    insight_items = generate_insights(kpi, trends, anomalies)

    return InsightsResponse(
        dataset_id=dataset_id,
        insights=insight_items,
        generated_at=datetime.utcnow(),
    )


@router.get("/analytics/{dataset_id}/kpi", response_model=KPISummary)
async def get_kpi(
    dataset_id: UUID,
    claims: TokenClaims = Depends(require_org_member),
):
    """Lightweight KPI endpoint for dashboard widgets."""
    try:
        df = await asyncio.to_thread(load_dataset, str(dataset_id), claims.org_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        raise HTTPException(status_code=422, detail="No numeric columns found.")

    values = df[numeric_cols[0]].dropna().tolist()
    return compute_kpis(values, dataset_id)
