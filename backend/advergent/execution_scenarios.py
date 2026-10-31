"""Trusted synthetic acceptance sources; no approvals or platform mutations.

Every invocation gets isolated synthetic advertising IDs. Caller restores default
publications; durable action history is retained, including failed attempts.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from .operational import ROOT
from .ads import import_ads
from .attribution import import_attribution
from .finance import import_finance
from .inventory import import_inventory
from .diagnostics import import_diagnostics
from .diagnostics_fixture import build_fixture


def restore(store, analytics):
    for importer in (import_ads, import_attribution, import_finance, import_inventory, import_diagnostics):
        importer(store, analytics)


def prepare(store, analytics, mode='pause', tag=None):
    tag = tag or uuid4().hex[:12]
    stamp = datetime.now(timezone.utc).isoformat()
    ads = json.loads((ROOT / 'fixtures/ads-corrected-v1.json').read_text())
    names = {r['id']: r['id'] + '-' + tag for r in ads['resources'] + ads['budgets']}
    def rename(value):
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return names.get(value, value) if isinstance(value, str) else value
    ads = rename(ads)
    ads.update(version='execution-ads-' + tag, observed_at=stamp, scenario_clock=stamp)
    attr = rename(json.loads((ROOT / 'fixtures/attribution-v1.json').read_text()))
    attr.update(version='execution-attribution-' + tag, observed_at=stamp)
    template = attr['mappings'][0]
    for r in ('m-set', 'm-cbo'):
        attr['mappings'].append(dict(template, id='execution-' + r, resource_id=names[r], products=['p0']))
    inv = rename(json.loads((ROOT / 'fixtures/inventory-v1.json').read_text()))
    inv.update(version='execution-inventory-' + tag + '-' + mode, observed_at=stamp)
    for r in inv['observations']:
        r['stock_observed_at'] = stamp
        if int(r['variant_id'][1:]) < 6:
            r.update(available=0 if mode == 'pause' else 4 if mode == 'throttle' else 100, eligible_units=28)
    for r in inv['resource_states']:
        r['observed_at'] = stamp
    diag = rename(build_fixture())
    delta = datetime.fromisoformat(stamp) - datetime.fromisoformat(diag['observed_at'])
    healthy = next(c for c in diag['checks'] if c['id'] == 'healthy-1')
    diag['checks'] = [dict(healthy, id='execution-' + r, resource_id=names[r]) for r in ('m-ad', 'm-set', 'm-cbo')]
    diag.update(version='execution-diagnostics-' + tag + '-' + mode, observed_at=stamp)
    for c in diag['checks']:
        c['observed_at'] = (datetime.fromisoformat(c['observed_at'].replace('Z', '+00:00')) + delta).isoformat()
    for w in diag['windows']:
        for k in ('start', 'end'):
            w[k] = (datetime.fromisoformat(w[k].replace('Z', '+00:00')) + delta).isoformat()
    with TemporaryDirectory() as directory:
        for f, importer in ((ads, import_ads), (attr, import_attribution),
                            (inv, import_inventory), (diag, import_diagnostics)):
            path = Path(directory) / 'source.json'
            path.write_text(json.dumps(f), encoding='utf-8')
            if importer == import_inventory:
                import_finance(store, analytics)
            importer(store, analytics, path)
    return names
