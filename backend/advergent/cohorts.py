"""Vendor-neutral exact observed customer cohorts. No advertising actions."""
from collections import defaultdict
from datetime import datetime, timedelta
from fractions import Fraction
from zoneinfo import ZoneInfo
from typing import Literal
from pydantic import BaseModel, Field
from .finance import allocate


class CohortWindow(BaseModel):
    days: int
    end: str
    observed_until: str
    mature: bool
    events: int
    missing_events: int
    estimated_events: int
    excluded_before_acquisition: int
    covered_event_contribution_paise: int
    contribution_before_ads_paise: int | None
    product_contribution_paise: dict[str, int | None]


class CohortCustomer(BaseModel):
    customer_id: str
    first_order_id: str
    first_delivered_at: str
    acquisition_month: str
    acquisition_campaign: list[str | None]
    history_complete: Literal[False] = False
    weights: dict[str, str]
    windows: list[CohortWindow]


class CohortBucket(BaseModel):
    acquisition_month: str
    product_id: str
    days: int
    mature: bool
    customer_weight: str
    customers: int
    missing_customers: int
    known_customer_contribution_paise: int
    contribution_before_ads_paise: int | None


class CohortData(BaseModel):
    cutoff: str
    history_start: str
    history_complete: Literal[False] = False
    basis: str = 'First observed delivered purchase in incomplete available history; realized before ads; not calibrated LTV or incremental profit.'
    customers_without_delivery: int
    zero_value_unassigned: int
    customers: list[CohortCustomer]
    buckets: list[CohortBucket]
    publishing_enabled: Literal[False] = False
    mutation_enabled: Literal[False] = False


class CohortSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'analytics_unavailable', 'inputs_changed']
    pins: dict[str, str] = Field(default_factory=dict)
    input_observations: dict[str, str] = Field(default_factory=dict)
    dependencies_current: bool = False
    queried_at: str | None = None
    data: CohortData | None = None


def evaluate(orders, lines, events, cutoff, history_start):
    """Inputs are verified SQL features; all date comparisons use aware instants."""
    def dt(s): return datetime.fromisoformat(s)
    by_customer = defaultdict(list)
    by_order = defaultdict(list)
    for o in orders: by_customer[o['customer_id']].append(o)
    for line in lines: by_order[line['order_id']].append(line)
    by_customer_event = defaultdict(list)
    for e in events: by_customer_event[e['customer_id']].append(e)
    customers = []
    no_delivery = zero = 0
    groups = defaultdict(list)
    for customer, os in sorted(by_customer.items()):
        delivered = [o for o in os if o['delivered_at'] and dt(o['delivered_at']) <= cutoff]
        if not delivered:
            no_delivery += 1
            continue
        first = min(delivered, key=lambda o: (dt(o['delivered_at']), o['order_id']))
        start = dt(first['delivered_at'])
        weights = defaultdict(int)
        for line in by_order[first['order_id']]: weights[line['product_id']] += line['merchandise_paise']
        weights = {k: v for k, v in weights.items() if v > 0}
        total = sum(weights.values())
        if not total:
            zero += 1
            continue
        fractions = {k: str(Fraction(v, total)) for k, v in sorted(weights.items())}
        assert sum(map(Fraction, fractions.values())) == 1
        month = start.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m')
        windows = []
        for days in (60, 90):
            end = start + timedelta(days=days)
            until = min(cutoff, end)
            selected = [e for e in by_customer_event[customer]
                        if dt(e['at']) < end and dt(e['at']) <= cutoff
                        and (dt(e['at']) >= start or e['order_id'] == first['order_id'])]
            # A later-effective correction cannot be used by an earlier window.
            def value(e):
                if e.get('correction_at'):
                    effective = dt(e['correction_at'])
                    if effective >= end or effective > cutoff: return None
                return e['contribution_paise']
            missing = sum(value(e) is None for e in selected)
            covered = sum(value(e) for e in selected if value(e) is not None)
            contribution = None if missing else covered
            allocation = allocate(contribution, weights)
            if contribution is not None: assert sum(allocation.values()) == contribution
            window = CohortWindow(days=days, end=end.isoformat(), observed_until=until.isoformat(),
                mature=cutoff >= end, events=len(selected), missing_events=missing,
                estimated_events=sum(e['estimated'] for e in selected),
                excluded_before_acquisition=sum(dt(e['at']) < start and e['order_id'] != first['order_id']
                    for e in by_customer_event[customer] if dt(e['at']) <= cutoff),
                covered_event_contribution_paise=covered, contribution_before_ads_paise=contribution,
                product_contribution_paise=allocation)
            windows.append(window)
            for pid, fraction in fractions.items():
                groups[month, pid, days, window.mature].append((Fraction(fraction), allocation[pid]))
        customers.append(CohortCustomer(customer_id=customer, first_order_id=first['order_id'],
            first_delivered_at=start.isoformat(), acquisition_month=month,
            acquisition_campaign=first['campaign'], weights=fractions, windows=windows))
    buckets = []
    for (month, pid, days, mature), rows in sorted(groups.items()):
        missing = sum(v is None for _, v in rows)
        known = sum(v for _, v in rows if v is not None)
        buckets.append(CohortBucket(acquisition_month=month, product_id=pid, days=days, mature=mature,
            customer_weight=str(sum((f for f, _ in rows), Fraction())), customers=len(rows),
            missing_customers=missing, known_customer_contribution_paise=known,
            contribution_before_ads_paise=None if missing else known))
    return CohortData(cutoff=cutoff.isoformat(), history_start=history_start, customers=customers,
                      customers_without_delivery=no_delivery, zero_value_unassigned=zero, buckets=buckets)
