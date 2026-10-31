"""Conservative descriptive response envelopes and exact fixed-total allocation."""
from collections import defaultdict
from fractions import Fraction
from datetime import date, datetime, timedelta
from typing import Literal
from pydantic import BaseModel, Field, StrictInt
from .commerce import SourceModel


class BudgetRequest(SourceModel):
    total_paise: StrictInt | None = Field(default=None, ge=0, le=10**13)
    change_bps: StrictInt = Field(default=1000, ge=0, le=1000)


class ResponseBaseline(BaseModel):
    status: Literal['supported', 'abstain']
    blockers: list[str]
    days: int
    spend_levels: int
    minimum_spend_paise: int | None = None
    maximum_spend_paise: int | None = None
    lower_slope: str | None = None
    upper_slope: str | None = None
    observations: list[dict]


class BudgetRow(BaseModel):
    key: str
    platform: str
    account_id: str
    budget_id: str
    shared: bool
    members: list[str]
    products: list[str]
    current_paise: int
    allocated_paise: int
    minimum_paise: int
    maximum_paise: int
    blockers: list[str]
    response: ResponseBaseline
    state: dict | None = None
    historical_contribution_paise: int | None = None


class BudgetData(BaseModel):
    valid_until: str | None = None
    terms: BudgetRequest
    status: Literal['scenario', 'abstain', 'infeasible']
    total_paise: int
    allocated_total_paise: int
    blockers: list[str]
    rows: list[BudgetRow]
    conservative_delta_paise: str | None
    upper_delta_paise: str | None
    portfolio_contribution_after_ads_paise: None = None
    cohort_context: dict
    basis: str = 'Descriptive spend/contribution association; assumes full budget delivery. Uncalibrated synthetic scenario, not causal response, calibrated LTV, incremental profit or a predictive backtest. Slope ranges are sensitivity, not confidence bounds.'
    approval_required: Literal[True] = True
    publishing_enabled: Literal[False] = False
    mutation_enabled: Literal[False] = False


class BudgetSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'inputs_changed', 'analytics_unavailable']
    pins: dict[str, str] = Field(default_factory=dict)
    input_observations: dict[str, str] = Field(default_factory=dict)
    dependencies_current: bool = False
    queried_at: str | None = None
    data: BudgetData | None = None


def observed_outcome(events, placed, cutoff):
    """All attributed order outcomes, not an LTV multiplier or a reserve estimate."""
    end = placed+timedelta(days=60)
    if end > cutoff: return None
    values = []
    for e in events:
        if datetime.fromisoformat(e['at']) >= end: continue
        correction = e.get('correction_at')
        values.append(None if correction and datetime.fromisoformat(correction) >= end else e['contribution_paise'])
    return None if any(v is None for v in values) else sum(values)


def baseline(observations):
    """Never fit covered-only costs or selectively discard unsuitable supplied days."""
    reasons = []
    days = sorted(date.fromisoformat(o['day']) for o in observations)
    if days and (len(set(days)) != len(days) or days != [days[0]+timedelta(days=i) for i in range(len(days))]):
        reasons.append('noncontiguous or duplicate daily observations')
    groups = defaultdict(list)
    for o in observations:
        if not o['complete']: reasons.append('incomplete daily reporting coverage')
        if not o['mature']: reasons.append('immature 60-day order outcomes')
        if o['orders'] < 20: reasons.append('fewer than twenty orders per day')
        if o['contribution_paise'] is None: reasons.append('missing outcome costs')
        if o['spend_paise'] <= 0: reasons.append('nonpositive observed spend')
        groups[o['spend_paise']].append(o['contribution_paise'])
    if len(groups) < 3: reasons.append('fewer than three spend levels')
    if any(len(rows) < 3 for rows in groups.values()): reasons.append('fewer than three days per spend level')
    result = dict(days=len(observations), spend_levels=len(groups), observations=observations)
    if reasons: return ResponseBaseline(status='abstain', blockers=sorted(set(reasons)), **result)
    levels = sorted(groups)
    slopes = [(Fraction(min(groups[b])-max(groups[a]), b-a),
               Fraction(max(groups[b])-min(groups[a]), b-a)) for a, b in zip(levels, levels[1:])]
    low, high = min(s[0] for s in slopes), max(s[1] for s in slopes)
    if low < 0:
        return ResponseBaseline(status='abstain', blockers=['non-monotone response envelope'], **result)
    return ResponseBaseline(status='supported', blockers=[], minimum_spend_paise=levels[0],
        maximum_spend_paise=levels[-1], lower_slope=str(low), upper_slope=str(high), **result)


def allocate(inputs, terms, cohort_context, blockers=()):
    rows = []
    for r in sorted(inputs, key=lambda r: r['key']):
        response = baseline(r['observations'])
        reasons = list(r['blockers']) + response.blockers
        current = r['current_paise']
        change = current * terms.change_bps // 10000
        lo, hi = current-change, current+change
        if response.status == 'supported':
            lo = max(lo, response.minimum_spend_paise)
            hi = min(hi, response.maximum_spend_paise)
            if not lo <= current <= hi: reasons.append('current budget outside observed spend support')
        if reasons: lo = hi = current
        rows.append(BudgetRow(**{k: r[k] for k in ('key','platform','account_id','budget_id','shared','members','products','current_paise')},
            state=r.get('state'), historical_contribution_paise=r.get('historical_contribution_paise'),
            allocated_paise=current, minimum_paise=lo, maximum_paise=hi,
            blockers=sorted(set(reasons)), response=response))
    total = sum(r.current_paise for r in rows)
    global_reasons = list(blockers)
    infeasible = terms.total_paise is not None and terms.total_paise != total
    if infeasible: global_reasons.append('requested fixed total differs from existing portfolio total')
    terms = terms.model_copy(update={'total_paise': total if terms.total_paise is None else terms.total_paise})
    # All feasible marginal gains are constant within the supported envelope. Each
    # budget can only donate or receive in an optimum: a profitable cycle cannot
    # exist because every lower slope is <= its upper slope.
    eligible = [r for r in rows if not r.blockers]
    candidates = sorted(((Fraction(b.response.lower_slope)-Fraction(a.response.upper_slope), a.key, b.key, a, b)
                         for a in eligible for b in eligible if a.key != b.key), key=lambda v: (-v[0], v[1], v[2]))
    low = high = Fraction()
    if not global_reasons:
        for gain, _, _, donor, recipient in candidates:
            if gain <= 0: continue
            amount = min(donor.allocated_paise-donor.minimum_paise, recipient.maximum_paise-recipient.allocated_paise)
            if amount <= 0: continue
            donor.allocated_paise -= amount
            recipient.allocated_paise += amount
            low += amount*gain
            high += amount*(Fraction(recipient.response.upper_slope)-Fraction(donor.response.lower_slope))
    changed = any(r.allocated_paise != r.current_paise for r in rows)
    if not changed and not global_reasons: global_reasons.append('no supported positive conservative reallocation')
    assert sum(r.allocated_paise for r in rows) == total
    assert all(r.minimum_paise <= r.allocated_paise <= r.maximum_paise for r in rows)
    return BudgetData(terms=terms, status='infeasible' if infeasible else 'scenario' if changed else 'abstain',
        total_paise=total, allocated_total_paise=total, blockers=global_reasons, rows=rows,
        conservative_delta_paise=str(low) if changed else None, upper_delta_paise=str(high) if changed else None,
        cohort_context=cohort_context)
