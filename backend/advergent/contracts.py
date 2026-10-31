from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID
from pydantic import BaseModel, Field


class GoldenMetric(BaseModel):
    line_count: int
    net_sales_paise: int
    product_cost_paise: int
    variable_cost_paise: int
    ad_spend_paise: int
    contribution_before_ads_paise: int
    contribution_after_ads_paise: int


class Snapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'analytics_unavailable']
    source: Literal['synthetic / real Exasol'] = 'synthetic / real Exasol'
    currency: Literal['INR'] = 'INR'
    dataset_id: UUID | None = None
    refresh_job_id: UUID | None = None
    dataset_version: str | None = None
    fixture_hash: str | None = None
    published_at: datetime | None = None
    queried_at: datetime | None = None
    latest_refresh_status: str | None = None
    metric: GoldenMetric | None = None


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class CommerceTotals(BaseModel):
    products: int
    variants: int
    customers: int
    orders: int
    lines: int
    refunds: int
    inventory: int
    ordered_units: int
    placed_merchandise_paise: int
    missing_cost_lines: int
    available_units: int
    sellable_units: int
    refunded_units: int
    refund_merchandise_paise: int
    delivered_lines: int


class CommerceSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'analytics_unavailable']
    source: Literal['synthetic Shopify-shaped / real Exasol'] = 'synthetic Shopify-shaped / real Exasol'
    dataset_id: UUID | None = None
    dataset_version: str | None = None
    fixture_hash: str | None = None
    observed_at: datetime | None = None
    scenario_clock: datetime | None = None
    published_at: datetime | None = None
    queried_at: datetime | None = None
    freshness: Literal['fresh', 'stale', 'unknown'] = 'unknown'
    age_seconds: int | None = None
    freshness_limit_seconds: int = 900
    latest_import_status: str | None = None
    next_page: int | None = None
    repair_count: int | None = None
    totals: CommerceTotals | None = None


class AnalyticsUnavailable(Exception):
    pass


# Source types are application contracts, independent of the analytics vendor.
from .ads import Account, Budget, Resource


class AdResource(Resource):
    campaign_id: str
    effective_budget_id: str | None
    budget_owner_id: str | None
    shared_budget: bool
    budget_members: list[str]
    affected_budget_ids: list[str]
    status_control_supported: bool
    budget_control_supported: bool
    product_control_supported: bool
    mutation_enabled: bool
    capability_evidence: str
    unsupported_reason: str


class AdReport(BaseModel):
    key: str
    platform: Literal['meta', 'google']
    account_id: str
    resource_id: str
    interval_start: datetime
    reporting_day: str
    source_day: str
    revision: int
    reported_at: datetime
    currency: Literal['INR']
    spend_paise: int


class AdBudget(Budget):
    budget_control_supported: bool
    mutation_enabled: bool
    approval_required: bool
    capability_evidence: str
    member_ids: list[str]


class AdGroup(BaseModel):
    platform: Literal['meta', 'google']
    account_id: str
    reporting_day: str
    campaign_id: str
    budget_id: str
    report_count: int
    spend_paise: int


class AdData(BaseModel):
    accounts: list[Account]
    budgets: list[AdBudget]
    resources: list[AdResource]
    reports: list[AdReport]
    groups: list[AdGroup]
    report_count: int
    spend_paise: int


class AdSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'analytics_unavailable']
    source: Literal['synthetic Meta/Google / real Exasol'] = 'synthetic Meta/Google / real Exasol'
    currency: Literal['INR'] = 'INR'
    reporting_timezone: Literal['Asia/Kolkata'] = 'Asia/Kolkata'
    dataset_id: UUID | None = None
    dataset_version: str | None = None
    fixture_hash: str | None = None
    observed_at: datetime | None = None
    scenario_clock: datetime | None = None
    published_at: datetime | None = None
    queried_at: datetime | None = None
    freshness: Literal['fresh', 'stale', 'unknown'] = 'unknown'
    age_seconds: int | None = None
    freshness_limit_seconds: int = 900
    latest_import_status: str | None = None
    data: AdData | None = None


class Analytics(Protocol):
    def probe(self) -> None: ...
    def load(self, dataset_id: str, fixture: dict) -> None: ...
    def metric(self, dataset_id: str) -> GoldenMetric: ...


from .attribution import Mapping, Click, Claim


class MappingDecision(BaseModel):
    platform: str
    account_id: str
    resource_id: str
    status: Literal['resolved', 'ambiguous', 'unmapped']
    products: list[str]
    evidence_ids: list[str]
    override: bool
    product_control_supported: bool


class Assignment(BaseModel):
    order_id: str
    platform: str | None
    account_id: str | None
    campaign_id: str | None
    reason: Literal['paid_click', 'ambiguous_click', 'no_eligible_click']
    click_ids: list[str]


class AllocationGroup(BaseModel):
    platform: str | None
    account_id: str | None
    campaign_id: str | None
    orders: int
    lines: int
    placed_merchandise_paise: int


class ProductAllocation(BaseModel):
    platform: str | None
    account_id: str | None
    campaign_id: str | None
    product_id: str
    lines: int
    placed_merchandise_paise: int


class RefundLink(BaseModel):
    refund_id: str
    order_id: str
    refunded_at: datetime
    platform: str | None
    account_id: str | None
    campaign_id: str | None


class Reconciliation(BaseModel):
    orders: int
    lines: int
    placed_merchandise_paise: int
    refunds: int


class AttributionData(BaseModel):
    mappings: list[MappingDecision]
    mapping_evidence: list[Mapping]
    assignments: list[Assignment]
    clicks: list[Click]
    platform_claims: list[Claim]
    groups: list[AllocationGroup]
    product_allocations: list[ProductAllocation]
    refund_links: list[RefundLink]
    reconciliation: Reconciliation


class AttributionSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'analytics_unavailable']
    model: Literal['last-paid-click-7d-no-view-v1'] = 'last-paid-click-7d-no-view-v1'
    source: str = 'synthetic first-party evidence / real Exasol'
    dataset_id: UUID | None = None
    commerce_id: UUID | None = None
    ads_id: UUID | None = None
    dataset_version: str | None = None
    fixture_hash: str | None = None
    observed_at: datetime | None = None
    mapping_as_of: datetime | None = None
    published_at: datetime | None = None
    queried_at: datetime | None = None
    latest_import_status: str | None = None
    dependencies_current: bool | None = None
    freshness: Literal['fresh', 'stale', 'unknown'] = 'unknown'
    age_seconds: int | None = None
    data: AttributionData | None = None


class FinanceTotals(BaseModel):
    net_product_cost_paise: int | None
    variable_paise: int | None
    lines: int
    orders: int
    placed_paise: int
    delivered_paise: int
    refunded_paise: int
    net_sales_paise: int
    cash_paise: int
    unsettled_cod_paise: int
    missing_lines: int
    estimated_lines: int
    cost_coverage_bps: int
    covered_contribution_paise: int
    expected_missing_lines: int
    covered_expected_paise: int
    exposed_units: int
    reserve_missing_lines: int
    reserve_paise: int | None
    spend_paise: int
    contribution_before_ads_paise: int | None
    contribution_after_ads_paise: int | None
    expected_before_ads_paise: int | None
    expected_after_ads_paise: int | None
    poas: str | None
    mer: str | None


class FinanceAllocation(BaseModel):
    platform: str | None
    account_id: str | None
    campaign_id: str | None
    totals: FinanceTotals


class FinanceLine(BaseModel):
    events: list[dict]
    line_id: str
    order_id: str
    placed_paise: int
    delivered_paise: int
    refunded_paise: int
    shipping_paise: int
    sold_cost_paise: int | None
    recovered_paise: int | None
    failed_loss_paise: int | None
    variable_paise: int | None
    reserve_paise: int | None
    cash_paise: int
    unsettled_cod_paise: int
    cost_status: str
    expense_status: str
    exposed_units: int
    evidence: dict
    platform: str | None
    account_id: str | None
    campaign_id: str | None
    net_sales_paise: int
    net_product_cost_paise: int | None
    contribution_before_ads_paise: int | None
    expected_before_ads_paise: int | None


class FinanceDay(BaseModel):
    day: str
    events: int
    net_sales_paise: int
    cash_paise: int
    missing_events: int
    covered_contribution_paise: int
    contribution_before_ads_paise: int | None


class FinanceData(BaseModel):
    reserve_evidence: dict[str, int]
    transaction_days: list[FinanceDay]
    acquisition_days: list[FinanceDay]
    totals: FinanceTotals
    allocations: list[FinanceAllocation]
    lines: list[FinanceLine]
    refund_count: int
    reconciled: bool


class FinanceSnapshot(BaseModel):
    status: Literal['available','not_loaded','analytics_unavailable']
    source: str = 'synthetic finance ledger / real Exasol'
    currency: Literal['INR'] = 'INR'
    recognition: str = 'delivery-based; management contribution, not statutory net profit'
    input_observations: dict[str, datetime] | None = None
    dataset_id: UUID | None = None
    commerce_id: UUID | None = None
    ads_id: UUID | None = None
    attribution_id: UUID | None = None
    dataset_version: str | None = None
    fixture_hash: str | None = None
    observed_at: datetime | None = None
    published_at: datetime | None = None
    queried_at: datetime | None = None
    period_start: datetime | None = None
    as_of: datetime | None = None
    reserve_assumptions: dict | None = None
    latest_import_status: str | None = None
    dependencies_current: bool | None = None
    freshness: Literal['fresh','stale','unknown'] = 'unknown'
    age_seconds: int | None = None
    data: FinanceData | None = None


class InventoryProduct(BaseModel):
    suggested_action: str
    approval_required: bool
    affected_scope: list[str]
    product_id: str
    sellable_units: int
    daily_velocity: str | None
    days_of_cover: str | None
    lead_days: int | None
    lead_source: str
    warning: bool
    stockout: bool
    unavailable_weight_bps: str | None
    weight_source: str
    pause_eligible: bool
    throttle_eligible: bool
    recovery_stock_eligible: bool
    risk: str
    uncertain: bool
    fresh: bool
    variants: list[dict]


class InventoryImpact(BaseModel):
    delivered_sample_units: int
    daily_contribution_context_paise: str | None
    scenario_assumption: str
    basis: str
    lines: int
    missing_lines: int
    expected_contribution_paise: int | None
    covered_subtotal_paise: int


class InventoryRecommendation(BaseModel):
    platform: str
    account_id: str
    resource_id: str
    campaign_id: str
    affected_products: list[str]
    mapping: MappingDecision
    action: str
    eligibility: str
    blockers: list[str]
    approval_required: bool
    mutation_enabled: bool
    capability_evidence: str
    budget_id: str | None
    budget_members: list[str]
    state: dict | None
    impact: InventoryImpact
    evidence_products: list[str]


class InventoryData(BaseModel):
    products: list[InventoryProduct]
    recommendations: list[InventoryRecommendation]
    sellable_units: int
    variants: int
    reconciled: bool
    assumptions: dict
    demand_basis: str
    finance_id: UUID
    evaluated_at: datetime


class InventorySnapshot(BaseModel):
    status: Literal['available','not_loaded','analytics_unavailable']
    source: str = 'synthetic warehouse observations / real Exasol; approval-required advisory only'
    dataset_id: UUID | None = None
    finance_id: UUID | None = None
    commerce_id: UUID | None = None
    ads_id: UUID | None = None
    attribution_id: UUID | None = None
    dataset_version: str | None = None
    fixture_hash: str | None = None
    observed_at: datetime | None = None
    published_at: datetime | None = None
    queried_at: datetime | None = None
    latest_import_status: str | None = None
    dependencies_current: bool | None = None
    freshness: Literal['fresh','stale','unknown'] = 'unknown'
    age_seconds: int | None = None
    data: InventoryData | None = None


class DiagnosticsData(BaseModel):
    recommendations: list[dict]
    assumptions: dict
    evaluated_at: datetime
    basis: str
    variant_price_evidence: list[dict]
    ctr_evidence: list[dict]


class DiagnosticsSnapshot(InventorySnapshot):
    source: str = 'synthetic diagnostics / real Exasol; advisory and approval-required'
    inventory_id: UUID | None = None
    data: DiagnosticsData | None = None
