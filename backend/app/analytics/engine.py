"""Analytics engine orchestrating beneficiary concentration and batch fragmentation calculations."""
from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .concentration import (
    classify_beneficiary,
    evaluate_concentration,
    evaluate_dual_track_coverage,
)
from .fragmentation import (
    calculate_gini_coefficient,
    calculate_median,
    evaluate_batch_fragmentation,
)
from .cross_registry import (
    compare_cross_registry_entities,
    compare_projects,
    correlate_registry_projects,
    get_cross_registry_retirement_summary,
    get_cross_registry_retirement_trends,
)
from .models import (
    BatchAnalyticsResult,
    BeneficiaryCategory,
    ConcentrationMetrics,
    CrossRegistryCorrelationsResponse,
    CrossRegistryEntityComparison,
    CrossRegistryProjectComparison,
    CrossRegistryRetirementSummary,
    CrossRegistryTrendsResponse,
    FragmentationMetrics,
    PopulationAnalyticsSummary,
    ProjectProfile,
    TemporalActivityResponse,
    TemporalBurstsResponse,
    TemporalGapsResponse,
    TemporalTrendsResponse,
)
from .temporal import (
    aggregate_retirement_activity,
    analyze_temporal_gaps,
    calculate_temporal_trends,
    detect_temporal_bursts,
)

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "var", "registry_demo.sqlite")
)


class AnalyticsEngine:
    """Orchestration engine for population-level statistical and structural analytics.

    Enforces strict invariants:
    - Analyzes retirement records only (never mixes issuance records into retirement denominators).
    - Preserves registry-specific batch namespaces (batches identified by (registry, batch_id)).
    - Never compares numerical serial ranges across registries.
    """

    @staticmethod
    def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
        """Establish a read-only SQLite connection to the registry database."""
        path = db_path or DEFAULT_DB_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"Registry reference database not found at: {path}")
        # Open in URI read-only mode to prevent unintended database writes
        uri = f"file:{os.path.abspath(path)}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        return con

    @classmethod
    def analyze_concentration_records(
        cls,
        records: Sequence[Dict[str, Any]],
        total_units_override: Optional[float] = None,
    ) -> ConcentrationMetrics:
        """Perform in-memory beneficiary concentration analysis over a sequence of retirement records."""
        # Ensure only retirement records are analyzed if 'kind' field is present
        filtered_records = [
            r for r in records
            if r.get("kind") is None or str(r.get("kind")).strip().lower() == "retirement"
        ]
        return evaluate_concentration(filtered_records, total_units_override=total_units_override)

    @classmethod
    def analyze_batch_records(
        cls,
        records: Sequence[Dict[str, Any]],
        registry: Optional[str] = None,
        batch_id: Optional[str] = None,
        project_id: Optional[str] = None,
        micro_threshold: float = 10.0,
    ) -> FragmentationMetrics:
        """Perform in-memory batch fragmentation and interval analysis."""
        filtered_records = [
            r for r in records
            if r.get("kind") is None or str(r.get("kind")).strip().lower() == "retirement"
        ]
        return evaluate_batch_fragmentation(
            filtered_records,
            registry=registry,
            batch_id=batch_id,
            project_id=project_id,
            micro_threshold=micro_threshold,
        )

    @classmethod
    def analyze_batch(
        cls,
        registry: str,
        batch_id: str,
        db_path: Optional[str] = None,
        con: Optional[sqlite3.Connection] = None,
    ) -> BatchAnalyticsResult:
        """Retrieve and analyze a single batch from the reference SQLite database.

        Preserves registry-specific batch namespace: queries by (registry, batch_id).
        Operates strictly on retirement records (kind = 'retirement').
        """
        own_con = False
        if con is None:
            con = cls.get_connection(db_path)
            own_con = True

        try:
            cur = con.cursor()
            cur.execute(
                """
                SELECT registry, batch_id, project_id, project_name, country, vintage,
                       unit_start, unit_end, quantity, beneficiary, event_date
                FROM records
                WHERE kind = 'retirement'
                  AND UPPER(registry) = UPPER(?)
                  AND batch_id = ?
                ORDER BY unit_start ASC
                """,
                (registry.strip(), batch_id.strip()),
            )
            rows = cur.fetchall()

            if not rows:
                raise ValueError(
                    f"No retirement records found for batch: registry='{registry}', batch_id='{batch_id}'"
                )

            records = [dict(r) for r in rows]
            first_rec = records[0]

            proj_id = first_rec.get("project_id")
            proj_name = first_rec.get("project_name")
            country = first_rec.get("country")
            vintage = first_rec.get("vintage")

            # Compute concentration and fragmentation metrics
            concentration = evaluate_concentration(records)
            fragmentation = evaluate_batch_fragmentation(
                records,
                registry=registry,
                batch_id=batch_id,
                project_id=proj_id,
            )

            total_qty = fragmentation.total_units
            total_events = fragmentation.total_events

            return BatchAnalyticsResult(
                registry=str(first_rec.get("registry") or registry).upper(),
                batch_id=batch_id,
                project_id=str(proj_id) if proj_id else None,
                project_name=str(proj_name) if proj_name else None,
                country=str(country) if country else None,
                vintage=int(vintage) if vintage is not None else None,
                total_quantity=total_qty,
                total_events=total_events,
                concentration=concentration,
                fragmentation=fragmentation,
                computed_at=datetime.now(timezone.utc),
            )
        finally:
            if own_con and con:
                con.close()

    @classmethod
    def analyze_population_summary(
        cls,
        db_path: Optional[str] = None,
        con: Optional[sqlite3.Connection] = None,
    ) -> PopulationAnalyticsSummary:
        """Compute population-wide dual-track concentration and batch fragmentation summaries across reference database.

        Analyzes all 37,335 retirement records without mixing issuance records.
        """
        own_con = False
        if con is None:
            con = cls.get_connection(db_path)
            own_con = True

        try:
            cur = con.cursor()
            cur.execute(
                """
                SELECT registry, batch_id, project_id, unit_start, unit_end, quantity, beneficiary
                FROM records
                WHERE kind = 'retirement'
                """
            )
            rows = cur.fetchall()
            records = [dict(r) for r in rows]

            total_records = len(records)
            coverage = evaluate_dual_track_coverage(records)
            overall_concentration = evaluate_concentration(records)

            # Group by (registry, batch_id) to preserve registry namespaces
            batches: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
            for r in records:
                batches[(str(r["registry"]).upper(), str(r["batch_id"]))].append(r)

            total_batches = len(batches)
            batch_rec_counts: List[float] = []
            batch_quantities: List[float] = []
            batch_ginis: List[float] = []

            single_rec_batches = 0
            multi_rec_batches = 0
            micro_batches = 0
            small_tranche_batches = 0
            overlap_batches = 0

            for (reg, b_id), b_records in batches.items():
                n_b = len(b_records)
                batch_rec_counts.append(float(n_b))
                if n_b == 1:
                    single_rec_batches += 1
                else:
                    multi_rec_batches += 1

                b_quantities = [float(int(r["unit_end"]) - int(r["unit_start"]) + 1) for r in b_records]
                total_b_qty = sum(b_quantities)
                batch_quantities.append(total_b_qty)

                # Batch Gini
                b_gini = calculate_gini_coefficient(b_quantities)
                batch_ginis.append(b_gini)

                # Absolute micro claims (0 < q <= 10.0 t)
                if any(0.0 < q <= 10.0 for q in b_quantities):
                    micro_batches += 1

                # Relative small tranches (0 < q <= 1% of batch)
                tau_rel = total_b_qty * 0.01
                if any(0.0 < q <= tau_rel for q in b_quantities):
                    small_tranche_batches += 1

                # Overlap check
                sorted_ints = sorted([(int(r["unit_start"]), int(r["unit_end"])) for r in b_records])
                curr_max_e = sorted_ints[0][1]
                has_overlap = False
                for i in range(1, len(sorted_ints)):
                    if sorted_ints[i][0] <= curr_max_e:
                        has_overlap = True
                        break
                    if sorted_ints[i][1] > curr_max_e:
                        curr_max_e = sorted_ints[i][1]
                if has_overlap:
                    overlap_batches += 1

            # Portfolio-wide pooled allocations
            pooled_quantities = [float(int(r["unit_end"]) - int(r["unit_start"]) + 1) for r in records]
            pooled_allocation_count = len(pooled_quantities)
            pooled_allocation_quantity = sum(pooled_quantities)
            pooled_allocation_mean_size = (pooled_allocation_quantity / pooled_allocation_count) if pooled_allocation_count > 0 else 0.0
            pooled_allocation_gini = calculate_gini_coefficient(pooled_quantities)

            # Sizing summaries
            sorted_rec_counts = sorted(batch_rec_counts)
            rec_counts_summary = {
                "min": sorted_rec_counts[0] if sorted_rec_counts else 0.0,
                "max": sorted_rec_counts[-1] if sorted_rec_counts else 0.0,
                "mean": (sum(batch_rec_counts) / total_batches) if total_batches > 0 else 0.0,
                "median": calculate_median(sorted_rec_counts),
            }

            sorted_quantities = sorted(batch_quantities)
            quantities_summary = {
                "min": sorted_quantities[0] if sorted_quantities else 0.0,
                "max": sorted_quantities[-1] if sorted_quantities else 0.0,
                "mean": (sum(batch_quantities) / total_batches) if total_batches > 0 else 0.0,
                "median": calculate_median(sorted_quantities),
            }

            sorted_ginis = sorted(batch_ginis)
            gini_summary = {
                "min": sorted_ginis[0] if sorted_ginis else 0.0,
                "max": sorted_ginis[-1] if sorted_ginis else 0.0,
                "mean": (sum(batch_ginis) / total_batches) if total_batches > 0 else 0.0,
                "median": calculate_median(sorted_ginis),
            }

            return PopulationAnalyticsSummary(
                total_retirement_records=total_records,
                total_retirement_quantity=coverage.total_quantity,
                total_batches=total_batches,
                coverage=coverage,
                overall_concentration=overall_concentration,
                batch_record_counts=rec_counts_summary,
                batch_quantities=quantities_summary,
                batch_gini_distribution=gini_summary,
                pooled_allocation_count=pooled_allocation_count,
                pooled_allocation_quantity=pooled_allocation_quantity,
                pooled_allocation_mean_size=pooled_allocation_mean_size,
                pooled_allocation_gini=pooled_allocation_gini,
                batches_with_micro_claims=micro_batches,
                batches_with_small_tranches=small_tranche_batches,
                batches_with_overlaps=overlap_batches,
                single_record_batches=single_rec_batches,
                multi_record_batches=multi_rec_batches,
                computed_at=datetime.now(timezone.utc),
            )
        finally:
            if own_con and con:
                con.close()

    @classmethod
    def query_retirement_records(
        cls,
        registry: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        db_path: Optional[str] = None,
        con: Optional[sqlite3.Connection] = None,
    ) -> List[Dict[str, Any]]:
        """Query retirement records with optional registry, project, and date filters."""
        own_con = False
        if con is None:
            con = cls.get_connection(db_path)
            own_con = True

        try:
            cur = con.cursor()
            sql = """
                SELECT registry, batch_id, project_id, project_name, country, vintage,
                       unit_start, unit_end, quantity, beneficiary, event_date
                FROM records
                WHERE kind = 'retirement'
            """
            params: List[Any] = []

            if registry:
                sql += " AND UPPER(registry) = UPPER(?)"
                params.append(registry.strip())

            if project_id:
                sql += " AND project_id = ?"
                params.append(project_id.strip())

            if start_date:
                s_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date).strip()[:10]
                sql += " AND event_date >= ?"
                params.append(s_str)

            if end_date:
                e_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date).strip()[:10]
                sql += " AND event_date <= ?"
                params.append(e_str)

            sql += " ORDER BY event_date ASC, unit_start ASC"

            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            if own_con and con:
                con.close()

    @classmethod
    def analyze_temporal_activity(
        cls,
        registry: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        period_type: str = "monthly",
        records: Optional[Sequence[Dict[str, Any]]] = None,
        db_path: Optional[str] = None,
        con: Optional[sqlite3.Connection] = None,
    ) -> TemporalActivityResponse:
        """Analyze temporal retirement activity across continuous calendar periods."""
        if records is None:
            records = cls.query_retirement_records(
                registry=registry,
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
                db_path=db_path,
                con=con,
            )
        return aggregate_retirement_activity(
            records=records,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            registry=registry,
            project_id=project_id,
        )

    @classmethod
    def analyze_temporal_trends(
        cls,
        registry: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        period_type: str = "monthly",
        window: int = 4,
        threshold_pct: float = 5.0,
        records: Optional[Sequence[Dict[str, Any]]] = None,
        db_path: Optional[str] = None,
        con: Optional[sqlite3.Connection] = None,
    ) -> TemporalTrendsResponse:
        """Analyze rolling trends and direction across calendar periods."""
        act_resp = cls.analyze_temporal_activity(
            registry=registry,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            records=records,
            db_path=db_path,
            con=con,
        )
        return calculate_temporal_trends(
            activity_periods=act_resp.periods,
            window=window,
            threshold_pct=threshold_pct,
            registry=registry,
            project_id=project_id,
            period_type=period_type,
        )

    @classmethod
    def analyze_temporal_bursts(
        cls,
        registry: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        period_type: str = "monthly",
        baseline_window: int = 12,
        sensitivity: float = 3.0,
        min_history: int = 5,
        min_tonne_threshold: float = 100.0,
        min_record_threshold: int = 2,
        records: Optional[Sequence[Dict[str, Any]]] = None,
        db_path: Optional[str] = None,
        con: Optional[sqlite3.Connection] = None,
    ) -> TemporalBurstsResponse:
        """Detect anomalous temporal bursts using robust leave-one-out historical baseline."""
        act_resp = cls.analyze_temporal_activity(
            registry=registry,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            records=records,
            db_path=db_path,
            con=con,
        )
        return detect_temporal_bursts(
            activity_periods=act_resp.periods,
            baseline_window=baseline_window,
            sensitivity=sensitivity,
            min_history=min_history,
            min_tonne_threshold=min_tonne_threshold,
            min_record_threshold=min_record_threshold,
            registry=registry,
            project_id=project_id,
            period_type=period_type,
        )

    @classmethod
    def analyze_temporal_gaps(
        cls,
        registry: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        period_type: str = "monthly",
        records: Optional[Sequence[Dict[str, Any]]] = None,
        db_path: Optional[str] = None,
        con: Optional[sqlite3.Connection] = None,
    ) -> TemporalGapsResponse:
        """Analyze temporal gaps and inactivity intervals across calendar periods."""
        act_resp = cls.analyze_temporal_activity(
            registry=registry,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            records=records,
            db_path=db_path,
            con=con,
        )
        return analyze_temporal_gaps(
            activity_periods=act_resp.periods,
            period_type=period_type,
            registry=registry,
            project_id=project_id,
        )

    # ==============================================================================
    # PHASE 2C STAGE 3: CROSS-REGISTRY INTELLIGENCE
    # ==============================================================================

    @classmethod
    def compare_projects(
        cls,
        proj_a: Union[ProjectProfile, Dict[str, Any]],
        proj_b: Union[ProjectProfile, Dict[str, Any]],
    ) -> CrossRegistryProjectComparison:
        """Compare two projects across or within registries and produce explainable evidence."""
        return compare_projects(proj_a, proj_b)

    @classmethod
    def correlate_cross_registry_projects(
        cls,
        min_similarity: float = 0.50,
        category_filter: Optional[str] = None,
        country_filter: Optional[str] = None,
        limit: int = 50,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> CrossRegistryCorrelationsResponse:
        """Query all distinct projects in the reference database and evaluate cross-registry correlations."""
        from .cross_registry import correlate_registry_projects
        return correlate_registry_projects(
            min_similarity=min_similarity,
            category_filter=category_filter,
            country_filter=country_filter,
            limit=limit,
            con=con,
            db_path=db_path,
        )

    @classmethod
    def compare_entities(
        cls,
        entity_a: str,
        entity_b: str,
        registry_a: str = "VCS",
        registry_b: str = "GS",
    ) -> CrossRegistryEntityComparison:
        """Compare two entities across registries using the Phase 2A resolution engine."""
        return compare_cross_registry_entities(
            entity_a=entity_a,
            entity_b=entity_b,
            registry_a=registry_a,
            registry_b=registry_b,
        )

    @classmethod
    def get_cross_registry_retirement_summary(
        cls,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> CrossRegistryRetirementSummary:
        """Retrieve comparative retirement summary across VCS and GS."""
        return get_cross_registry_retirement_summary(con=con, db_path=db_path)

    @classmethod
    def get_cross_registry_retirement_trends(
        cls,
        period_type: str = "yearly",
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> CrossRegistryTrendsResponse:
        """Retrieve comparative time series trends across VCS and GS."""
        return get_cross_registry_retirement_trends(period_type=period_type, con=con, db_path=db_path)

    # ==============================================================================
    # PHASE 2C STAGE 4: UNIFIED EXPLAINABLE RISK ASSESSMENT
    # ==============================================================================

    @classmethod
    def assess_risk(
        cls,
        request: Any,
        con: Optional[sqlite3.Connection] = None,
        db_path: Optional[str] = None,
    ) -> Any:
        """Execute unified, explainable risk assessment across Phase 2A, 2B, and 2C subsystems."""
        from .risk_assessment import RiskAssessmentEngine
        return RiskAssessmentEngine.assess(request, con=con, db_path=db_path)

    @classmethod
    def get_assessment_rules_catalog(cls) -> Any:
        """Retrieve the complete catalog of deterministic risk assessment rules."""
        from .risk_assessment import RiskAssessmentEngine
        return RiskAssessmentEngine.get_rules_catalog()

