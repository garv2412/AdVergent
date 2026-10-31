"""Synthetic event identity, time-separated breakout policy; no action interface."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class FunnelEvent(Strict):
    id: str = Field(min_length=1, max_length=100)
    product_id: str = Field(min_length=1, max_length=100)
    kind: Literal['view', 'cart', 'impression', 'click', 'purchase']
    at: datetime
    order_id: str | None = None

    @model_validator(mode='after')
    def valid(self):
        if self.at.tzinfo is None or (self.kind == 'purchase') != (self.order_id is not None):
            raise ValueError('Aware timestamps and purchase order reference required')
        self.at = self.at.astimezone(timezone.utc)
        return self


class Coverage(Strict):
    product_id: str
    window: Literal['baseline', 'signal', 'evaluation']
    tracked_days: int = Field(ge=0, le=7, strict=True)
    ad_series: str = Field(min_length=1, max_length=100)


class FunnelSource(Strict):
    version: str
    observed_at: datetime
    signal_end: datetime
    events: list[FunnelEvent] = Field(max_length=50000)
    coverage: list[Coverage]

    @model_validator(mode='after')
    def valid(self):
        if self.observed_at.tzinfo is None or self.signal_end.tzinfo is None:
            raise ValueError('Aware source timestamps required')
        if self.signal_end > self.observed_at or any(e.at > self.observed_at for e in self.events):
            raise ValueError('Unobserved future evidence')
        self.observed_at = self.observed_at.astimezone(timezone.utc)
        self.signal_end = self.signal_end.astimezone(timezone.utc)
        seen = {}
        for e in self.events:
            if e.id in seen and seen[e.id] != e:
                raise ValueError('Conflicting event identity')
            seen[e.id] = e
        keys = [(c.product_id, c.window) for c in self.coverage]
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate coverage')
        return self

    def unique_events(self):
        return list({e.id: e for e in self.events}.values())


class BreakoutRow(BaseModel):
    product_id: str
    counts: dict[str, dict[str, int]]
    tracked_days: dict[str, int]
    view_growth_bps: int | None
    cart_rate_bps: int | None
    ctr_bps: int | None
    historical_margin_bps: int | None
    inventory_risk: str
    blockers: list[str]
    score: int | None
    rank: int | None = None
    evaluation: str


class BreakoutData(BaseModel):
    ranking: list[BreakoutRow]
    source_hash: str
    source_version: str
    source_observed_at: str
    signal_end: str
    evaluation_end: str
    raw_events: int
    unique_events: int
    duplicate_events: int
    linked_purchase_pairs: int
    added_revenue_paise: Literal[0] = 0
    mutation_enabled: Literal[False] = False
    publishing_enabled: Literal[False] = False
    basis: str = ('Uncalibrated descriptive synthetic ranking, no confidence probability or budget forecast. '
        '100 views and 20 carts in each signal window; 1000 impressions and 20 clicks per window, '
        'seven tracked days and identical ad series required. Score = capped positive view growth bps '
        '+ cart rate bps + CTR bps + nonnegative historical expected contribution margin bps. '
        'Historical finance costs/reserves remain unchanged; missing costs abstain. Inventory must be clear/fresh. '
        'Later seven-day evaluation never enters the score; sustained means views do not decline and carts meet 20. '
        'Events are observations, not additional orders/revenue. Purchase pairs reference existing purchased products only. '
        'Coverage means supplied synthetic tracking days, not merchant completeness or statistical significance.')


class BreakoutSnapshot(BaseModel):
    status: Literal['available', 'not_loaded', 'analytics_unavailable']
    pins: dict[str, str] = Field(default_factory=dict)
    input_observations: dict[str, str] = Field(default_factory=dict)
    dependencies_current: bool = False
    queried_at: str | None = None
    data: BreakoutData | None = None


def evaluate(source, counts, inventory, margins, at, current, digest, linked_pairs):
    coverage = {(c.product_id, c.window): c for c in source.coverage}
    rows = []
    for p in inventory:
        pid = p['product_id']
        windows = {w: {k: counts.get((pid, w, k), 0) for k in ('view', 'cart', 'impression', 'click', 'purchase')}
                   for w in ('baseline', 'signal', 'evaluation')}
        days = {w: coverage[(pid, w)].tracked_days if (pid, w) in coverage else 0 for w in windows}
        b, s, ev = (windows[w] for w in windows)
        blockers = []
        if not current: blockers.append('pinned dependencies changed')
        if not 0 <= (at-source.observed_at).total_seconds() <= 900: blockers.append('stale or future funnel source')
        if not 0 <= (at-source.signal_end).total_seconds() <= 900: blockers.append('historical or unclosed signal window')
        if any(days[w] != 7 for w in ('baseline', 'signal')): blockers.append('incomplete tracking coverage')
        if any(r['view'] < 100 or r['cart'] < 20 for r in (b, s)): blockers.append('sparse funnel evidence')
        if any(r['impression'] < 1000 or r['click'] < 20 for r in (b, s)): blockers.append('sparse ad evidence')
        series = [coverage.get((pid, w)) for w in ('baseline', 'signal')]
        if any(c is None for c in series) or series[0].ad_series != series[1].ad_series:
            blockers.append('incomparable ad series')
        if any(r['cart'] > r['view'] or r['click'] > r['impression'] for r in (b, s)):
            blockers.append('inconsistent funnel counters')
        growth = (s['view']-b['view'])*10000//b['view'] if b['view'] else None
        cart = s['cart']*10000//s['view'] if s['view'] else None
        ctr = s['click']*10000//s['impression'] if s['impression'] else None
        margin = margins.get(pid)
        if margin is None: blockers.append('unknown historical contribution margin')
        elif margin < 0: blockers.append('negative historical contribution margin')
        if p['risk'] != 'clear' or not p['fresh']: blockers.append('inventory not ready: '+p['risk'])
        if growth is None or growth <= 0: blockers.append('no positive view growth')
        # The holdout is descriptive and independent of current ranking eligibility.
        evaluation_end = source.signal_end+timedelta(days=7)
        evaluation = 'pending'
        if evaluation_end <= min(at, source.observed_at):
            weak_signal = any(b in blockers for b in ('incomplete tracking coverage', 'sparse funnel evidence',
                'sparse ad evidence', 'incomparable ad series', 'inconsistent funnel counters', 'no positive view growth'))
            evaluation = ('insufficient' if weak_signal or days['evaluation'] != 7 or ev['view'] < 100 or ev['cart'] < 20 or ev['cart'] > ev['view']
                          else 'sustained' if ev['view'] >= s['view'] else 'not sustained')
        score = min(10000, max(0, growth))+cart+ctr+margin if not blockers else None
        rows.append(BreakoutRow(product_id=pid, counts=windows, tracked_days=days, view_growth_bps=growth,
            cart_rate_bps=cart, ctr_bps=ctr, historical_margin_bps=margin, inventory_risk=p['risk'],
            blockers=blockers, score=score, evaluation=evaluation))
    rows.sort(key=lambda r: (r.score is None, -(r.score or 0), r.product_id))
    for i, r in enumerate([r for r in rows if r.score is not None], 1): r.rank = i
    return BreakoutData(ranking=rows, source_hash=digest, source_version=source.version,
        source_observed_at=source.observed_at.isoformat(), signal_end=source.signal_end.isoformat(),
        evaluation_end=(source.signal_end+timedelta(days=7)).isoformat(), raw_events=len(source.events),
        unique_events=len(source.unique_events()), duplicate_events=len(source.events)-len(source.unique_events()),
        linked_purchase_pairs=linked_pairs)
