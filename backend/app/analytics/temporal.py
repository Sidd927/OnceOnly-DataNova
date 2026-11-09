"""Retirement velocity, vintage dormancy, and liquidation burst analytics."""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .fragmentation import calculate_median
from .models import (
    AggregationPeriod,
    BurstType,
    GapClassification,
    TEMPORAL_DISCLAIMER,
    TemporalActivityResponse,
    TemporalBurstPeriod,
    TemporalBurstsResponse,
    TemporalGapItem,
    TemporalGapsResponse,
    TemporalMetrics,
    TemporalPeriodActivity,
    TemporalTrendPeriod,
    TemporalTrendsResponse,
    TrendDirection,
    VelocityTier,
)


def parse_date(val: Any) -> Optional[date]:
    """Safely parse date from date, datetime, or ISO string."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in ("null", "none", ""):
            return None
        # ISO string YYYY-MM-DD
        try:
            return date.fromisoformat(val[:10])
        except (ValueError, TypeError):
            pass
        # Common alternative format YYYY/MM/DD
        try:
            parts = val.replace("/", "-").split("-")
            if len(parts) >= 3 and len(parts[0]) == 4:
                return date(int(parts[0]), int(parts[1]), int(parts[2][:2]))
        except (ValueError, TypeError):
            pass
    return None


def calculate_inclusive_span(dates: Sequence[date]) -> int:
    """Compute inclusive calendar days between earliest and latest dates.

    Single calendar day returns 1.
    Empty sequence returns 0.
    """
    if not dates:
        return 0
    s_dates = sorted(dates)
    return max(1, (s_dates[-1] - s_dates[0]).days + 1)


def calculate_vintage_lags(
    event_dates: Sequence[date],
    vintage_year: int,
) -> Tuple[Optional[float], Optional[float], Optional[int], Optional[int]]:
    """Compute days elapsed from Jan 1 of vintage year to retirement dates.

    Returns
    -------
    (mean_lag, median_lag, min_lag, max_lag)
    """
    if not event_dates or vintage_year is None or vintage_year <= 1990:
        return None, None, None, None

    base_date = date(vintage_year, 1, 1)
    lags = sorted([(d - base_date).days for d in event_dates])
    if not lags:
        return None, None, None, None

    n = len(lags)
    mean_lag = sum(lags) / n
    mid = n // 2
    median_lag = float(lags[mid]) if n % 2 == 1 else (lags[mid - 1] + lags[mid]) / 2.0
    return mean_lag, median_lag, lags[0], lags[-1]


def detect_liquidation_burst(
    span_days: int,
    total_volume: float,
    event_count: int,
    peak_daily_volume: float,
) -> bool:
    """Detect anomalous burst liquidation behavior.

    True if:
    1. Acute window (<= 7 days) with high volume (>= 1,000 t) and multiple tranches (>= 3).
    2. Single-day concentration accounts for >= 70% of total volume (when >= 1,000 t).
    """
    if total_volume < 1000.0:
        return False
    if span_days <= 7 and event_count >= 3:
        return True
    if total_volume > 0 and (peak_daily_volume / total_volume) >= 0.70:
        return True
    return False


def calculate_quarterly_clustering(
    dated_volumes: Sequence[Tuple[date, float]],
    total_volume: float,
) -> Tuple[float, Optional[str]]:
    """Compute maximum share of volume concentrated in a single calendar quarter."""
    if not dated_volumes or total_volume <= 0:
        return 0.0, None

    quarter_map: Dict[str, float] = defaultdict(float)
    for d, qty in dated_volumes:
        q_label = f"{d.year}-Q{(d.month - 1) // 3 + 1}"
        quarter_map[q_label] += qty

    if not quarter_map:
        return 0.0, None

    dominant_q, dominant_vol = max(quarter_map.items(), key=lambda x: x[1])
    share = max(0.0, min(1.0, dominant_vol / total_volume))
    return share, dominant_q


def classify_velocity_tier(
    span_days: int,
    velocity: float,
    burst_flag: bool,
    mean_lag_days: Optional[float],
) -> str:
    """Classify temporal liquidation velocity tier."""
    if span_days <= 0 or velocity <= 0.0:
        return VelocityTier.INSUFFICIENT_TEMPORAL_DATA.value
    if burst_flag:
        return VelocityTier.RAPID_BURST.value
    if mean_lag_days is not None and mean_lag_days >= 1095.0 and velocity >= 1000.0:
        return VelocityTier.DORMANT_LIQUIDATION.value
    if velocity >= 5000.0:
        return VelocityTier.ACCELERATED.value
    return VelocityTier.NORMAL.value


def evaluate_temporal(
    events: Sequence[Dict[str, Any]],
    vintage_year: Optional[int] = None,
) -> TemporalMetrics:
    """Evaluate comprehensive temporal retirement metrics.

    Parameters
    ----------
    events : Sequence[Dict[str, Any]]
        Event dicts containing 'event_date'/'retirement_date' and 'quantity'.
    vintage_year : Optional[int]
        Batch vintage year if available.

    Returns
    -------
    TemporalMetrics
        Immutable container with velocity, vintage lag, burst flags, and clustering.
    """
    dated_events: List[Tuple[date, float]] = []
    daily_volume: Dict[date, float] = defaultdict(float)
    total_volume = 0.0

    for ev in events:
        qty = float(ev.get("quantity") or 0.0)
        if qty <= 0:
            continue
        total_volume += qty

        d_raw = ev.get("event_date") or ev.get("retirement_date") or ev.get("date")
        d_parsed = parse_date(d_raw)
        if d_parsed:
            dated_events.append((d_parsed, qty))
            daily_volume[d_parsed] += qty

    if not dated_events:
        return TemporalMetrics(
            first_event_date=None,
            last_event_date=None,
            timespan_days=0,
            total_volume=total_volume,
            burn_rate_tonnes_per_day=0.0,
            peak_daily_volume=0.0,
            peak_event_date=None,
            vintage_year=vintage_year,
            mean_vintage_lag_days=None,
            median_vintage_lag_days=None,
            min_vintage_lag_days=None,
            max_vintage_lag_days=None,
            liquidation_burst_flag=False,
            fiscal_quarter_clustering_share=0.0,
            dominant_quarter=None,
            velocity_tier=VelocityTier.INSUFFICIENT_TEMPORAL_DATA.value,
        )

    all_dates = [d for d, _ in dated_events]
    s_dates = sorted(all_dates)
    first_date = s_dates[0]
    last_date = s_dates[-1]
    span_days = max(1, (last_date - first_date).days + 1)
    velocity = total_volume / span_days

    # Peak day
    peak_date, peak_vol = max(daily_volume.items(), key=lambda x: x[1])

    # Vintage lag
    mean_lag, med_lag, min_lag, max_lag = (
        calculate_vintage_lags(all_dates, vintage_year)
        if vintage_year
        else (None, None, None, None)
    )

    # Burst flag
    burst_flag = detect_liquidation_burst(span_days, total_volume, len(dated_events), peak_vol)

    # Quarterly clustering
    q_share, dom_q = calculate_quarterly_clustering(dated_events, total_volume)

    # Velocity tier
    tier = classify_velocity_tier(span_days, velocity, burst_flag, mean_lag)

    return TemporalMetrics(
        first_event_date=first_date,
        last_event_date=last_date,
        timespan_days=span_days,
        total_volume=total_volume,
        burn_rate_tonnes_per_day=velocity,
        peak_daily_volume=peak_vol,
        peak_event_date=peak_date,
        vintage_year=vintage_year,
        mean_vintage_lag_days=mean_lag,
        median_vintage_lag_days=med_lag,
        min_vintage_lag_days=min_lag,
        max_vintage_lag_days=max_lag,
        liquidation_burst_flag=burst_flag,
        fiscal_quarter_clustering_share=q_share,
        dominant_quarter=dom_q,
        velocity_tier=tier,
    )


# ==============================================================================
# PHASE 2C STAGE 2: TEMPORAL RETIREMENT INTELLIGENCE
# ==============================================================================


def calculate_dispersion_mad(
    values: Sequence[float],
    floor: float = 1.0,
) -> Tuple[float, float, float, str]:
    """Compute median, scaled Median Absolute Deviation (MAD), and robust dispersion.

    Parameters
    ----------
    values : Sequence[float]
        Numerical observations.
    floor : float
        Minimum positive floor (retained for backward compatibility).

    Returns
    -------
    Tuple[float, float, float, str]
        (median, scaled_mad, effective_dispersion, dispersion_method)
        where dispersion_method is 'MAD' if scaled_mad > 0.0, else 'ZERO_MAD_FLOOR'.
    """
    if not values:
        return 0.0, 0.0, 0.0, "ZERO_MAD_FLOOR"

    med = calculate_median(values)
    deviations = [abs(float(v) - med) for v in values]
    raw_mad = calculate_median(deviations)
    # Standard normal consistency scale factor: 1.4826022185...
    scaled_mad = 1.4826 * raw_mad

    if scaled_mad > 0.0:
        dispersion = scaled_mad
        method = "MAD"
    else:
        # Zero-MAD floor: do NOT fall back to sample standard deviation s (which
        # reintroduces extreme outlier vulnerability with 0% breakdown point).
        # Set robust dispersion to 0.0 and allow the caller to apply the domain minimum floor.
        dispersion = 0.0
        method = "ZERO_MAD_FLOOR"

    return med, scaled_mad, dispersion, method


def generate_calendar_periods(
    start_date: date,
    end_date: date,
    period_type: str = "monthly",
) -> List[Tuple[date, date, str]]:
    """Generate continuous, gap-free calendar periods between start and end dates inclusive.

    Parameters
    ----------
    start_date : date
        Earliest date in calendar range.
    end_date : date
        Latest date in calendar range.
    period_type : str
        Granularity: 'daily', 'weekly', or 'monthly'.

    Returns
    -------
    List[Tuple[date, date, str]]
        Ordered list of (period_start, period_end, period_label).
    """
    if start_date > end_date:
        return []

    p_type = period_type.strip().lower()
    periods: List[Tuple[date, date, str]] = []

    if p_type == AggregationPeriod.DAILY.value:
        curr = start_date
        while curr <= end_date:
            periods.append((curr, curr, curr.isoformat()))
            curr += timedelta(days=1)

    elif p_type == AggregationPeriod.WEEKLY.value:
        # Align to Monday of start_date's ISO week
        curr_monday = start_date - timedelta(days=start_date.weekday())
        while curr_monday <= end_date:
            curr_sunday = curr_monday + timedelta(days=6)
            iso = curr_monday.isocalendar()
            label = f"{iso.year}-W{iso.week:02d}"
            periods.append((curr_monday, curr_sunday, label))
            curr_monday += timedelta(days=7)

    elif p_type == AggregationPeriod.MONTHLY.value:
        y, m = start_date.year, start_date.month
        while (y, m) <= (end_date.year, end_date.month):
            p_start = date(y, m, 1)
            last_day = calendar.monthrange(y, m)[1]
            p_end = date(y, m, last_day)
            label = f"{y:04d}-{m:02d}"
            periods.append((p_start, p_end, label))
            m += 1
            if m > 12:
                m = 1
                y += 1
    else:
        raise ValueError(
            f"Unsupported period_type: '{period_type}'. Must be 'daily', 'weekly', or 'monthly'."
        )

    return periods


def aggregate_retirement_activity(
    records: Sequence[Dict[str, Any]],
    period_type: str = "monthly",
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    registry: Optional[str] = None,
    project_id: Optional[str] = None,
) -> TemporalActivityResponse:
    """Aggregate retirement events into continuous calendar periods.

    Parameters
    ----------
    records : Sequence[Dict[str, Any]]
        Retirement event dictionaries containing 'event_date' and 'quantity'.
    period_type : str
        Granularity: 'daily', 'weekly', or 'monthly'.
    start_date : Optional[Union[date, str]]
        Optional bounding start date.
    end_date : Optional[Union[date, str]]
        Optional bounding end date.
    registry : Optional[str]
        Registry filter metadata.
    project_id : Optional[str]
        Project identifier filter metadata.

    Returns
    -------
    TemporalActivityResponse
        Continuous time series activity metrics with coverage disclosures.
    """
    parsed_start = parse_date(start_date) if start_date else None
    parsed_end = parse_date(end_date) if end_date else None

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise ValueError(
            f"start_date ({parsed_start.isoformat()}) cannot be after end_date ({parsed_end.isoformat()})"
        )

    p_type = period_type.strip().lower()
    if p_type not in (
        AggregationPeriod.DAILY.value,
        AggregationPeriod.WEEKLY.value,
        AggregationPeriod.MONTHLY.value,
    ):
        raise ValueError(
            f"Unsupported period_type: '{period_type}'. Must be 'daily', 'weekly', or 'monthly'."
        )

    # Accumulate valid dated retirement records
    dated_events: List[Tuple[date, float]] = []
    bucket_counts: Dict[str, int] = defaultdict(int)
    bucket_tonnes: Dict[str, float] = defaultdict(float)

    total_records = 0
    total_tonnes = 0.0

    for r in records:
        k = r.get("kind")
        if k is not None and str(k).strip().lower() != "retirement":
            continue

        qty = float(r.get("quantity") or 0.0)
        raw_d = r.get("event_date") or r.get("retirement_date") or r.get("date")
        d_parsed = parse_date(raw_d)

        if d_parsed is not None:
            if parsed_start and d_parsed < parsed_start:
                continue
            if parsed_end and d_parsed > parsed_end:
                continue

            dated_events.append((d_parsed, qty))
            total_records += 1
            total_tonnes += qty

            # Determine bucket label
            if p_type == AggregationPeriod.DAILY.value:
                lbl = d_parsed.isoformat()
            elif p_type == AggregationPeriod.WEEKLY.value:
                iso = d_parsed.isocalendar()
                lbl = f"{iso.year}-W{iso.week:02d}"
            else:  # monthly
                lbl = f"{d_parsed.year:04d}-{d_parsed.month:02d}"

            bucket_counts[lbl] += 1
            bucket_tonnes[lbl] += qty

    if not dated_events:
        effective_start = parsed_start
        effective_end = parsed_end
        if effective_start and effective_end:
            cal_periods = generate_calendar_periods(effective_start, effective_end, period_type=p_type)
            period_acts = [
                TemporalPeriodActivity(
                    period_start=p_start,
                    period_end=p_end,
                    period_label=p_label,
                    record_count=0,
                    total_tonnes=0.0,
                    average_tonnes_per_record=0.0,
                    records_with_usable_dates=0,
                    records_with_missing_or_invalid_dates=0,
                    usable_date_quantity=0.0,
                    excluded_date_quantity=0.0,
                )
                for p_start, p_end, p_label in cal_periods
            ]
            return TemporalActivityResponse(
                registry=registry,
                project_id=project_id,
                period_type=p_type,
                total_periods=len(period_acts),
                total_records=0,
                total_tonnes=0.0,
                active_periods_count=0,
                zero_activity_periods_count=len(period_acts),
                earliest_date_observed=None,
                latest_date_observed=None,
                periods=period_acts,
            )

        return TemporalActivityResponse(
            registry=registry,
            project_id=project_id,
            period_type=p_type,
            total_periods=0,
            total_records=0,
            total_tonnes=0.0,
            active_periods_count=0,
            zero_activity_periods_count=0,
            earliest_date_observed=None,
            latest_date_observed=None,
            periods=[],
        )

    all_observed_dates = [d for d, _ in dated_events]
    earliest_observed = min(all_observed_dates)
    latest_observed = max(all_observed_dates)

    eff_start = parsed_start if parsed_start is not None else earliest_observed
    eff_end = parsed_end if parsed_end is not None else latest_observed

    calendar_sequence = generate_calendar_periods(eff_start, eff_end, period_type=p_type)

    period_activities: List[TemporalPeriodActivity] = []
    active_count = 0
    zero_count = 0

    for p_start, p_end, p_label in calendar_sequence:
        cnt = bucket_counts.get(p_label, 0)
        ton = bucket_tonnes.get(p_label, 0.0)
        avg = (ton / float(cnt)) if cnt > 0 else 0.0

        if cnt > 0:
            active_count += 1
        else:
            zero_count += 1

        period_activities.append(
            TemporalPeriodActivity(
                period_start=p_start,
                period_end=p_end,
                period_label=p_label,
                record_count=cnt,
                total_tonnes=ton,
                average_tonnes_per_record=avg,
                records_with_usable_dates=cnt,
                records_with_missing_or_invalid_dates=0,
                usable_date_quantity=ton,
                excluded_date_quantity=0.0,
            )
        )

    return TemporalActivityResponse(
        registry=registry,
        project_id=project_id,
        period_type=p_type,
        total_periods=len(period_activities),
        total_records=total_records,
        total_tonnes=total_tonnes,
        active_periods_count=active_count,
        zero_activity_periods_count=zero_count,
        earliest_date_observed=earliest_observed,
        latest_date_observed=latest_observed,
        periods=period_activities,
    )


def calculate_temporal_trends(
    activity_periods: Sequence[TemporalPeriodActivity],
    window: int = 4,
    threshold_pct: float = 5.0,
    registry: Optional[str] = None,
    project_id: Optional[str] = None,
    period_type: str = "monthly",
) -> TemporalTrendsResponse:
    """Compute rolling averages and classify temporal trends across periods.

    Parameters
    ----------
    activity_periods : Sequence[TemporalPeriodActivity]
        Chronologically ordered activity periods.
    window : int
        Number of completed prior historical periods in rolling average (W >= 1).
    threshold_pct : float
        Percentage threshold above which trend is increasing and below which decreasing.
    registry : Optional[str]
        Registry filter metadata.
    project_id : Optional[str]
        Project identifier filter metadata.
    period_type : str
        Granularity identifier.

    Returns
    -------
    TemporalTrendsResponse
        Rolling trend series with coverage and direction classifications.
    """
    if window < 1:
        raise ValueError(f"Rolling window must be >= 1, received {window}")
    if threshold_pct < 0.0:
        raise ValueError(f"threshold_pct must be >= 0.0, received {threshold_pct}")

    trends: List[TemporalTrendPeriod] = []
    n = len(activity_periods)

    for t, p in enumerate(activity_periods):
        has_sufficient = t >= window
        if has_sufficient:
            prior_slice = activity_periods[t - window : t]
            roll_rec = sum(x.record_count for x in prior_slice) / float(window)
            roll_ton = sum(x.total_tonnes for x in prior_slice) / float(window)
            status = "COMPLETE_WINDOW"
        else:
            roll_rec = None
            roll_ton = None
            status = "INSUFFICIENT_HISTORY"

        if t == 0:
            rec_change = None
            ton_change = None
            rec_pct_change = None
            ton_pct_change = None
            direction = TrendDirection.STABLE.value
        else:
            prev = activity_periods[t - 1]
            rec_change = p.record_count - prev.record_count
            ton_change = p.total_tonnes - prev.total_tonnes

            if prev.record_count == 0:
                rec_pct_change = 100.0 if p.record_count > 0 else 0.0
            else:
                rec_pct_change = ((p.record_count - prev.record_count) / float(prev.record_count)) * 100.0

            if prev.total_tonnes == 0.0:
                ton_pct_change = 100.0 if p.total_tonnes > 0.0 else 0.0
            else:
                ton_pct_change = ((p.total_tonnes - prev.total_tonnes) / float(prev.total_tonnes)) * 100.0

            # Trend direction: compare against rolling average when baseline is complete,
            # otherwise compare against prior period
            if has_sufficient and roll_ton is not None and roll_ton > 0.0:
                rel_pct = ((p.total_tonnes - roll_ton) / roll_ton) * 100.0
                if rel_pct > threshold_pct:
                    direction = TrendDirection.INCREASING.value
                elif rel_pct < -threshold_pct:
                    direction = TrendDirection.DECREASING.value
                else:
                    direction = TrendDirection.STABLE.value
            elif has_sufficient and roll_ton == 0.0:
                if p.total_tonnes > 0.0:
                    direction = TrendDirection.INCREASING.value
                else:
                    direction = TrendDirection.STABLE.value
            else:
                # Insufficient history: compare against prior period
                if ton_pct_change is not None:
                    if ton_pct_change > threshold_pct:
                        direction = TrendDirection.INCREASING.value
                    elif ton_pct_change < -threshold_pct:
                        direction = TrendDirection.DECREASING.value
                    else:
                        direction = TrendDirection.STABLE.value
                else:
                    direction = TrendDirection.STABLE.value

        trends.append(
            TemporalTrendPeriod(
                period_start=p.period_start,
                period_end=p.period_end,
                period_label=p.period_label,
                record_count=p.record_count,
                total_tonnes=p.total_tonnes,
                average_tonnes_per_record=p.average_tonnes_per_record,
                rolling_average_records=roll_rec,
                rolling_average_tonnes=roll_ton,
                record_count_change=rec_change,
                tonne_quantity_change=ton_change,
                record_count_pct_change=rec_pct_change,
                tonne_quantity_pct_change=ton_pct_change,
                direction=direction,
                has_sufficient_history=has_sufficient,
                data_coverage_status=status,
            )
        )

    sufficient_count = sum(1 for tr in trends if tr.has_sufficient_history)
    insufficient_count = n - sufficient_count

    return TemporalTrendsResponse(
        registry=registry,
        project_id=project_id,
        period_type=period_type,
        rolling_window=window,
        direction_threshold_pct=threshold_pct,
        total_periods=n,
        sufficient_history_periods=sufficient_count,
        insufficient_history_periods=insufficient_count,
        trends=trends,
    )


def detect_temporal_bursts(
    activity_periods: Sequence[TemporalPeriodActivity],
    baseline_window: int = 12,
    sensitivity: float = 3.0,
    min_history: int = 5,
    min_tonne_threshold: float = 100.0,
    min_record_threshold: int = 2,
    registry: Optional[str] = None,
    project_id: Optional[str] = None,
    period_type: str = "monthly",
) -> TemporalBurstsResponse:
    """Detect anomalous transaction volume or frequency bursts using a robust leave-one-out baseline.

    Parameters
    ----------
    activity_periods : Sequence[TemporalPeriodActivity]
        Chronologically ordered activity periods.
    baseline_window : int
        Lookback window size in prior periods (evaluated period t strictly excluded).
    sensitivity : float
        Multiplier k applied to MAD dispersion.
    min_history : int
        Minimum number of prior periods required for baseline calculation.
    min_tonne_threshold : float
        Absolute volume floor required to trigger a tonne burst.
    min_record_threshold : int
        Absolute record count floor required to trigger a record burst.
    registry : Optional[str]
        Registry filter metadata.
    project_id : Optional[str]
        Project identifier filter metadata.
    period_type : str
        Granularity identifier.

    Returns
    -------
    TemporalBurstsResponse
        Explainable burst detection results for each period.
    """
    if baseline_window < 1:
        raise ValueError(f"baseline_window must be >= 1, received {baseline_window}")
    if sensitivity < 0.5:
        raise ValueError(f"sensitivity must be >= 0.5, received {sensitivity}")
    if min_history < 1:
        raise ValueError(f"min_history must be >= 1, received {min_history}")

    bursts: List[TemporalBurstPeriod] = []
    burst_count = 0

    for t, p in enumerate(activity_periods):
        # Leave-one-out historical baseline: lookback window strictly ends at t - 1
        baseline_slice = activity_periods[max(0, t - baseline_window) : t]
        hist_len = len(baseline_slice)

        if hist_len < min_history:
            has_sufficient = False
            bursts.append(
                TemporalBurstPeriod(
                    period_start=p.period_start,
                    period_end=p.period_end,
                    period_label=p.period_label,
                    observed_records=p.record_count,
                    baseline_median_records=0.0,
                    baseline_mad_records=0.0,
                    record_burst_threshold=0.0,
                    record_burst_flag=False,
                    record_dispersion_method="INSUFFICIENT_HISTORY",
                    observed_tonnes=p.total_tonnes,
                    baseline_median_tonnes=0.0,
                    baseline_mad_tonnes=0.0,
                    tonne_burst_threshold=0.0,
                    tonne_burst_flag=False,
                    tonne_dispersion_method="INSUFFICIENT_HISTORY",
                    burst_type=BurstType.NONE.value,
                    is_burst=False,
                    has_sufficient_history=False,
                    explanation=f"Insufficient historical baseline ({hist_len} < {min_history} periods).",
                )
            )
            continue

        has_sufficient = True
        rec_vals = [float(x.record_count) for x in baseline_slice]
        ton_vals = [float(x.total_tonnes) for x in baseline_slice]

        med_rec, mad_rec, disp_rec, meth_rec = calculate_dispersion_mad(rec_vals, floor=1.0)
        med_ton, mad_ton, disp_ton, meth_ton = calculate_dispersion_mad(ton_vals, floor=10.0)

        rec_threshold = max(float(min_record_threshold), med_rec + sensitivity * disp_rec)
        ton_threshold = max(float(min_tonne_threshold), med_ton + sensitivity * disp_ton)

        # In Zero-MAD regimes (where variability has collapsed), require strictly > threshold
        # to prevent ordinary constant continuations from triggering false positive bursts.
        rec_flag = bool(
            (p.record_count > rec_threshold if meth_rec == "ZERO_MAD_FLOOR" else p.record_count >= rec_threshold)
            and p.record_count >= min_record_threshold
        )
        ton_flag = bool(
            (p.total_tonnes > ton_threshold if meth_ton == "ZERO_MAD_FLOOR" else p.total_tonnes >= ton_threshold)
            and p.total_tonnes >= min_tonne_threshold
        )

        if ton_flag and rec_flag:
            b_type = BurstType.BOTH.value
            is_b = True
            explanation = (
                f"Anomalous surge in both volume ({p.total_tonnes:,.1f} t vs threshold {ton_threshold:,.1f} t, "
                f"baseline median {med_ton:,.1f} t) and transaction frequency ({p.record_count} records vs "
                f"threshold {rec_threshold:,.1f}, baseline median {med_rec:,.1f})."
            )
        elif ton_flag:
            b_type = BurstType.TONNES.value
            is_b = True
            explanation = (
                f"Anomalous volume surge ({p.total_tonnes:,.1f} t vs threshold {ton_threshold:,.1f} t, "
                f"baseline median {med_ton:,.1f} t; record count {p.record_count} within normal bounds)."
            )
        elif rec_flag:
            b_type = BurstType.RECORDS.value
            is_b = True
            explanation = (
                f"Anomalous transaction frequency ({p.record_count} records vs threshold {rec_threshold:,.1f}, "
                f"baseline median {med_rec:,.1f}; volume {p.total_tonnes:,.1f} t within normal bounds)."
            )
        else:
            b_type = BurstType.NONE.value
            is_b = False
            explanation = "Observed volume and transaction frequency within normal statistical bounds."

        if is_b:
            burst_count += 1

        bursts.append(
            TemporalBurstPeriod(
                period_start=p.period_start,
                period_end=p.period_end,
                period_label=p.period_label,
                observed_records=p.record_count,
                baseline_median_records=med_rec,
                baseline_mad_records=mad_rec,
                record_burst_threshold=rec_threshold,
                record_burst_flag=rec_flag,
                record_dispersion_method=meth_rec,
                observed_tonnes=p.total_tonnes,
                baseline_median_tonnes=med_ton,
                baseline_mad_tonnes=mad_ton,
                tonne_burst_threshold=ton_threshold,
                tonne_burst_flag=ton_flag,
                tonne_dispersion_method=meth_ton,
                burst_type=b_type,
                is_burst=is_b,
                has_sufficient_history=True,
                explanation=explanation,
            )
        )

    return TemporalBurstsResponse(
        registry=registry,
        project_id=project_id,
        period_type=period_type,
        sensitivity=sensitivity,
        baseline_window=baseline_window,
        total_periods_evaluated=len(bursts),
        burst_periods_count=burst_count,
        bursts=bursts,
    )


def analyze_temporal_gaps(
    activity_periods: Sequence[TemporalPeriodActivity],
    period_type: str = "monthly",
    registry: Optional[str] = None,
    project_id: Optional[str] = None,
) -> TemporalGapsResponse:
    """Analyze contiguous periods of zero retirement activity.

    Parameters
    ----------
    activity_periods : Sequence[TemporalPeriodActivity]
        Chronologically ordered activity periods.
    period_type : str
        Granularity identifier.
    registry : Optional[str]
        Registry filter metadata.
    project_id : Optional[str]
        Project identifier filter metadata.

    Returns
    -------
    TemporalGapsResponse
        Identified inactivity intervals and coverage classifications.
    """
    gaps: List[TemporalGapItem] = []
    n = len(activity_periods)
    i = 0

    while i < n:
        if activity_periods[i].record_count == 0:
            j = i
            while j + 1 < n and activity_periods[j + 1].record_count == 0:
                j += 1

            gap_start = activity_periods[i].period_start
            gap_end = activity_periods[j].period_end
            duration_days = (gap_end - gap_start).days + 1
            duration_periods = j - i + 1

            prev_act = activity_periods[i - 1].to_dict() if i > 0 else None
            next_act = activity_periods[j + 1].to_dict() if j + 1 < n else None

            # Classification
            if i == 0 or j == n - 1:
                classification = GapClassification.DATASET_BOUNDARY.value
            elif duration_periods >= 3:
                classification = GapClassification.SUSTAINED_ZERO_ACTIVITY_INTERVAL.value
            else:
                classification = GapClassification.INTERMITTENT_ZERO_ACTIVITY_INTERVAL.value

            gaps.append(
                TemporalGapItem(
                    gap_start=gap_start,
                    gap_end=gap_end,
                    gap_duration_days=duration_days,
                    gap_duration_periods=duration_periods,
                    previous_activity_period=prev_act,
                    next_activity_period=next_act,
                    gap_classification=classification,
                )
            )
            i = j + 1
        else:
            i += 1

    max_dur = max((g.gap_duration_days for g in gaps), default=0)
    mean_dur = (sum(g.gap_duration_days for g in gaps) / float(len(gaps))) if gaps else 0.0

    return TemporalGapsResponse(
        registry=registry,
        project_id=project_id,
        period_type=period_type,
        total_gaps_count=len(gaps),
        max_gap_duration_days=max_dur,
        mean_gap_duration_days=mean_dur,
        gaps=gaps,
    )
