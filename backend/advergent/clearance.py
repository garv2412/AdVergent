"""Read-only synthetic clearance comparisons. No executor or publishing interface."""
from decimal import Decimal, ROUND_FLOOR
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Terms(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Component(Terms):
    variant_id: str = Field(min_length=1, max_length=100)
    units_per_bundle: int = Field(default=1, ge=1, le=1000)


class ClearanceRequest(Terms):
    components: list[Component] = Field(default_factory=lambda: [Component(variant_id='v6')], min_length=1, max_length=20)
    baseline_bundles: int = Field(default=1, ge=0, le=100000)
    scenario_bundles: int = Field(default=3, ge=0, le=100000)
    markdown_bps: int = Field(default=5000, ge=0, le=10000)
    additional_spend_paise: int = Field(default=0, ge=0, le=1000000000)
    horizon_days: int = Field(default=30, ge=1, le=365)
    assumed_stock_age_days: int = Field(default=120, ge=0, le=3650)
    deadstock_age_days: int = Field(default=90, ge=0, le=3650)
    holding_paise_per_unit_day: int | None = Field(default=5, ge=0, le=100000)
    variable_paise_per_unit: int | None = Field(default=10000, ge=0, le=10000000)
    return_loss_paise_per_unit: int | None = Field(default=1000, ge=0, le=10000000)
    min_contribution_paise: int = Field(default=0, ge=0, le=1000000000)
    min_margin_bps: int = Field(default=1000, ge=0, le=10000)

    @model_validator(mode='after')
    def unique(self):
        if len({c.variant_id for c in self.components}) != len(self.components):
            raise ValueError('Bundle components must have unique variant IDs')
        return self


class Comparison(BaseModel):
    bundles: int
    units: int
    revenue_paise: int
    product_cost_paise: int | None
    variable_cost_paise: int | None
    return_loss_paise: int | None
    holding_cost_paise: int | None
    additional_spend_paise: int
    expected_contribution_paise: int | None
    margin_bps: str | None
    cost_coverage_bps: int
    remaining_units: int
    blockers: list[str]
    limits_pass: bool


class RankedVariant(BaseModel):
    variant_id: str
    product_id: str
    sellable_units: int
    price_paise: int
    unit_cost_paise: int | None
    cost_status: str
    stock_observed_at: str
    fresh: bool
    demand_status: str
    daily_velocity: str | None
    assumed_stock_age_days: int
    excess_units: int | None
    deadstock_candidate: bool | None
    age_excess_score: int | None


class ClearanceData(BaseModel):
    ranking: list[RankedVariant]
    selected: list[RankedVariant]
    baseline: Comparison
    scenario: Comparison
    revenue_delta_paise: int
    contribution_delta_paise: int | None
    evidence_blockers: list[str]
    feasible: bool
    assumptions: ClearanceRequest
    mutation_enabled: Literal[False] = False
    publishing_enabled: Literal[False] = False
    basis: str = ('Uncalibrated synthetic what-if, not a demand forecast or incremental profit. '
        'Baseline: selected bundle mix at full catalog price, explicit assumed sales, zero additional spend. '
        'Scenario: explicit sales assumption independent of markdown/spend; no fitted response. '
        'Catalog COGS are prospective synthetic estimates, never replacements for historical finance costs. '
        'Variable expense and expected return loss are per sold unit, additional spend charged once. '
        'Holding cost applies to all unsold selected stock for the full horizon; assumes sales at horizon start. '
        'Stock age is an assumption for every variant, not warehouse lot-age evidence. '
        'Markdown rounds down per unit to integer paise; excludes tax, assumes full delivery. '
        'Scenarios are alternatives and must not be added together. No discounts, bundles or campaigns are published.')


class ClearanceSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'analytics_unavailable']
    pins: dict[str, str] = Field(default_factory=dict)
    observed_at: str | None = None
    input_observations: dict[str, str] = Field(default_factory=dict)
    queried_at: str | None = None
    dependencies_current: bool = False
    data: ClearanceData | None = None


def evaluate(rows, request: ClearanceRequest, dependencies_current=True):
    ranking = []
    for source in rows:
        r = dict(source)
        rate = Decimal(r['daily_velocity']) if r['daily_velocity'] is not None else None
        # Insufficient/zero exposure never becomes invented zero demand or infinity.
        excess = (max(0, r['sellable_units'] - int((rate * request.horizon_days).to_integral_value(rounding=ROUND_FLOOR)))
                  if r['demand_status'] == 'sufficient' and rate is not None else None)
        r.update(assumed_stock_age_days=request.assumed_stock_age_days, excess_units=excess,
                 deadstock_candidate=(excess > 0 and request.assumed_stock_age_days >= request.deadstock_age_days) if excess is not None else None,
                 age_excess_score=excess * request.assumed_stock_age_days if excess is not None else None)
        ranking.append(RankedVariant(**r))
    ranking.sort(key=lambda r: (r.age_excess_score is None, -(r.age_excess_score or 0), r.variant_id))
    byid = {r.variant_id: r for r in ranking}
    if any(c.variant_id not in byid for c in request.components):
        raise ValueError('Unknown variant in pinned inventory')
    selected = [byid[c.variant_id] for c in request.components]

    def compare(bundles, markdown, spend):
        revenue = units = remaining = known_units = 0
        cogs = 0
        blockers = []
        for c, r in zip(request.components, selected, strict=True):
            quantity = bundles * c.units_per_bundle
            units += quantity
            revenue += quantity * (r.price_paise * (10000 - markdown) // 10000)
            remaining += max(0, r.sellable_units - quantity)
            if quantity > r.sellable_units:
                blockers.append('stock limit: ' + r.variant_id)
            if r.unit_cost_paise is None and quantity:
                cogs = None
            elif r.unit_cost_paise is not None:
                known_units += quantity
                if cogs is not None:
                    cogs += quantity * r.unit_cost_paise
        variable = units * request.variable_paise_per_unit if request.variable_paise_per_unit is not None else (0 if not units else None)
        reserve = units * request.return_loss_paise_per_unit if request.return_loss_paise_per_unit is not None else (0 if not units else None)
        holding = remaining * request.horizon_days * request.holding_paise_per_unit_day if request.holding_paise_per_unit_day is not None else (0 if not remaining else None)
        costs = [cogs, variable, reserve, holding]
        contribution = revenue - sum(costs) - spend if all(v is not None for v in costs) else None
        margin = Decimal(contribution) * 10000 / revenue if contribution is not None and revenue else None
        if contribution is None:
            blockers.append('incomplete cost coverage')
        else:
            if contribution < request.min_contribution_paise:
                blockers.append('contribution floor')
            # Cross multiplication avoids a rounded margin passing the floor.
            if revenue and contribution * 10000 < request.min_margin_bps * revenue:
                blockers.append('margin floor')
        return Comparison(bundles=bundles, units=units, revenue_paise=revenue, product_cost_paise=cogs,
            variable_cost_paise=variable, return_loss_paise=reserve, holding_cost_paise=holding,
            additional_spend_paise=spend, expected_contribution_paise=contribution,
            margin_bps=str(margin) if margin is not None else None,
            cost_coverage_bps=known_units * 10000 // units if units else 10000,
            remaining_units=remaining, blockers=blockers, limits_pass=not blockers)

    baseline = compare(request.baseline_bundles, 0, 0)
    scenario = compare(request.scenario_bundles, request.markdown_bps, request.additional_spend_paise)
    evidence = ([] if dependencies_current else ['pinned dependencies changed'])
    if any(b.startswith('stock limit:') for b in baseline.blockers):
        evidence.append('no-action baseline exceeds available stock')
    if any(not r.fresh for r in selected):
        evidence.append('stale or future selected stock observations')
    if any(r.demand_status != 'sufficient' for r in selected):
        evidence.append('insufficient selected demand evidence')
    return ClearanceData(ranking=ranking, selected=selected, baseline=baseline, scenario=scenario,
        revenue_delta_paise=scenario.revenue_paise - baseline.revenue_paise,
        contribution_delta_paise=(scenario.expected_contribution_paise - baseline.expected_contribution_paise
            if scenario.expected_contribution_paise is not None and baseline.expected_contribution_paise is not None else None),
        evidence_blockers=evidence, feasible=not evidence and scenario.limits_pass,
        assumptions=request)
