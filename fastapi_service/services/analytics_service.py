"""
Core analytics engine: KPI calculations, trend detection, anomaly detection.
Designed to be stateless and easily testable.
"""
import math
import statistics
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from schemas.analytics import (
    AnomalyPoint,
    AnomalyReport,
    ColumnStats,
    InsightItem,
    InsightsResponse,
    KPISummary,
    TrendAnalysis,
    TrendPoint,
)


# ---------------------------------------------------------------------------
# KPI Calculations
# ---------------------------------------------------------------------------

def compute_kpis(
    values: List[float],
    dataset_id: UUID,
    previous_values: Optional[List[float]] = None,
) -> KPISummary:
    if not values:
        raise ValueError("No data to compute KPIs.")

    total = sum(values)
    average = statistics.mean(values)
    median = statistics.median(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
    min_val = min(values)
    max_val = max(values)

    growth_rate = None
    if previous_values:
        prev_total = sum(previous_values)
        if prev_total != 0:
            growth_rate = ((total - prev_total) / abs(prev_total)) * 100

    return KPISummary(
        dataset_id=dataset_id,
        total=round(total, 4),
        average=round(average, 4),
        median=round(median, 4),
        std_dev=round(std_dev, 4),
        min_value=round(min_val, 4),
        max_value=round(max_val, 4),
        growth_rate=round(growth_rate, 2) if growth_rate is not None else None,
        computed_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Trend Analysis (linear regression)
# ---------------------------------------------------------------------------

def _linear_regression(y: List[float]) -> Tuple[float, float, float]:
    """Returns (slope, intercept, r_squared)."""
    n = len(y)
    x = list(range(n))
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)

    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)

    if ss_xx == 0:
        return 0.0, mean_y, 0.0

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x

    y_pred = [slope * xi + intercept for xi in x]
    ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y, y_pred))
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    return round(slope, 6), round(intercept, 4), round(r_squared, 4)


def _moving_average(values: List[float], window: int = 3) -> List[Optional[float]]:
    result = []
    for i, _ in enumerate(values):
        if i < window - 1:
            result.append(None)
        else:
            result.append(round(statistics.mean(values[i - window + 1 : i + 1]), 4))
    return result


def detect_trends(values: List[float], dataset_id: UUID, periods: Optional[List[str]] = None) -> TrendAnalysis:
    slope, _, r_squared = _linear_regression(values)
    direction = "flat" if abs(slope) < 0.001 else ("up" if slope > 0 else "down")

    mavg = _moving_average(values)
    labels = periods or [str(i) for i in range(len(values))]

    points = [
        TrendPoint(period=labels[i], value=round(v, 4), moving_avg=mavg[i])
        for i, v in enumerate(values)
    ]

    return TrendAnalysis(
        dataset_id=dataset_id,
        direction=direction,
        slope=slope,
        r_squared=r_squared,
        points=points,
    )


# ---------------------------------------------------------------------------
# Anomaly Detection (Z-score method)
# ---------------------------------------------------------------------------

def detect_anomalies(
    values: List[float],
    dataset_id: UUID,
    threshold_z: float = 2.5,
) -> AnomalyReport:
    if len(values) < 4:
        return AnomalyReport(dataset_id=dataset_id, anomaly_count=0, anomalies=[], threshold_z=threshold_z)

    mean = statistics.mean(values)
    std = statistics.stdev(values)
    anomalies: List[AnomalyPoint] = []

    for i, v in enumerate(values):
        z = abs((v - mean) / std) if std > 0 else 0.0
        if z >= threshold_z:
            severity = "high" if z >= threshold_z * 1.5 else ("medium" if z >= threshold_z * 1.2 else "low")
            anomalies.append(
                AnomalyPoint(
                    index=i,
                    value=round(v, 4),
                    expected=round(mean, 4),
                    z_score=round(z, 3),
                    severity=severity,
                )
            )

    return AnomalyReport(
        dataset_id=dataset_id,
        anomaly_count=len(anomalies),
        anomalies=anomalies,
        threshold_z=threshold_z,
    )


# ---------------------------------------------------------------------------
# Insights Generation
# ---------------------------------------------------------------------------

def generate_insights(
    kpi: KPISummary,
    trends: TrendAnalysis,
    anomalies: AnomalyReport,
) -> List[InsightItem]:
    insights: List[InsightItem] = []

    # KPI insight
    insights.append(InsightItem(
        type="kpi",
        title="Summary Statistics",
        description=(
            f"Total: {kpi.total:,.2f} | Avg: {kpi.average:,.2f} | "
            f"StdDev: {kpi.std_dev:,.2f}"
        ),
        severity="info",
        data={"total": kpi.total, "average": kpi.average},
    ))

    # Growth rate
    if kpi.growth_rate is not None:
        sev = "warning" if abs(kpi.growth_rate) > 20 else "info"
        direction = "increased" if kpi.growth_rate > 0 else "decreased"
        insights.append(InsightItem(
            type="kpi",
            title="Period-over-Period Growth",
            description=f"Values {direction} by {abs(kpi.growth_rate):.1f}% compared to the previous period.",
            severity=sev,
            data={"growth_rate": kpi.growth_rate},
        ))

    # Trend insight
    if trends.r_squared > 0.7:
        insights.append(InsightItem(
            type="trend",
            title=f"Strong {trends.direction.capitalize()} Trend Detected",
            description=(
                f"R²={trends.r_squared:.2f} indicates a {trends.direction} trend "
                f"with slope {trends.slope:+.4f} per period."
            ),
            severity="warning" if trends.direction != "flat" else "info",
            data={"slope": trends.slope, "r_squared": trends.r_squared},
        ))

    # Anomaly insight
    if anomalies.anomaly_count > 0:
        high_count = sum(1 for a in anomalies.anomalies if a.severity == "high")
        sev = "critical" if high_count > 0 else "warning"
        insights.append(InsightItem(
            type="anomaly",
            title=f"{anomalies.anomaly_count} Anomalies Detected",
            description=(
                f"Found {anomalies.anomaly_count} outlier(s) "
                f"({high_count} high-severity) exceeding Z={anomalies.threshold_z}."
            ),
            severity=sev,
            data={"count": anomalies.anomaly_count, "high_severity": high_count},
        ))

    return insights
