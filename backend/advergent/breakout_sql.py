"""Content-addressed synthetic funnel inputs and analytical aggregates in Exasol."""
import hashlib
from datetime import datetime, timedelta
from .breakout import FunnelSource, evaluate
from .commerce import canonical
from .contracts import AnalyticsUnavailable
from .operational import ROOT


class BreakoutSQL:
    def migrate_breakout(self, conn):
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.BR_EVENTS (SOURCE_HASH VARCHAR(64), EVENT_ID VARCHAR(100), PRODUCT_ID VARCHAR(100), KIND VARCHAR(20), EVENT_AT VARCHAR(40), ORDER_ID VARCHAR(100), PRIMARY KEY(SOURCE_HASH,EVENT_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.BR_SOURCES (SOURCE_HASH VARCHAR(64), CONFIGURATION VARCHAR(2000000), PRIMARY KEY(SOURCE_HASH) ENABLE)')

    def breakout_data(self, pins, at, current, source=None):
        source = source or FunnelSource.model_validate_json((ROOT/'fixtures/breakout-v1.json').read_text(encoding='utf-8'))
        payload = canonical(source.model_dump(mode='json'))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        events = source.unique_events()
        # Validate all catalogue and order/product references before storing immutable evidence.
        variants = self.commerce_records(pins['commerce'], 'variants', limit=None)
        products = {r.data['product_id'] for r in variants}
        if any(e.product_id not in products for e in events) or any(c.product_id not in products for c in source.coverage):
            raise AnalyticsUnavailable('Unknown funnel product')
        orders = {r.id: datetime.fromisoformat(r.data['placed_at']) for r in self.commerce_records(pins['commerce'], 'orders', limit=None)}
        self.commerce_records(pins['commerce'], 'lines', limit=None)
        with self.connection() as conn:
            purchased = set(conn.execute('''SELECT DISTINCT l.ORDER_ID,v.PRODUCT_ID FROM ADVERGENT.COMMERCE_LINES l
                JOIN ADVERGENT.COMMERCE_VARIANTS v ON v.DATASET_ID=l.DATASET_ID AND v.SOURCE_ID=l.VARIANT_ID
                WHERE l.DATASET_ID={cid}''', dict(cid=pins['commerce'])).fetchall())
        if any((e.order_id, e.product_id) not in purchased or e.at < orders[e.order_id]
               for e in events if e.kind == 'purchase'):
            raise AnalyticsUnavailable('Unlinked funnel purchase')
        with self.connection() as conn:
            existing = conn.execute('SELECT CONFIGURATION FROM ADVERGENT.BR_SOURCES WHERE SOURCE_HASH={h}', dict(h=digest)).fetchval()
            if existing is None:
                for start in range(0, len(events), 100):
                    values, params = [], {}
                    for i, e in enumerate(events[start:start+100]):
                        row = [digest, e.id, e.product_id, e.kind, e.at.isoformat(), e.order_id]
                        keys = [f'p{i}_{j}' for j in range(6)]
                        params.update(zip(keys, row, strict=True))
                        values.append('('+','.join('{'+k+'}' for k in keys)+')')
                    conn.execute('INSERT INTO ADVERGENT.BR_EVENTS VALUES '+','.join(values), params)
                conn.execute('INSERT INTO ADVERGENT.BR_SOURCES VALUES ({h},{p})', dict(h=digest, p=payload))
                conn.commit()
            elif existing != payload:
                raise AnalyticsUnavailable('Funnel source mismatch')
            actual = conn.execute('SELECT EVENT_ID,PRODUCT_ID,KIND,EVENT_AT,ORDER_ID FROM ADVERGENT.BR_EVENTS WHERE SOURCE_HASH={h}', dict(h=digest)).fetchall()
            expected = [(e.id, e.product_id, e.kind, e.at.isoformat(), e.order_id) for e in events]
            if len(actual) != len(expected) or set(actual) != set(expected):
                raise AnalyticsUnavailable('Funnel typed/source mismatch')
            # Source validators normalize all event and window timestamps to UTC.
            # Bounds use identical timezone-normalized serialization for exact half-open windows.
            counts = {}
            for w, start, end in (('baseline', source.signal_end-timedelta(days=14), source.signal_end-timedelta(days=7)),
                                  ('signal', source.signal_end-timedelta(days=7), source.signal_end),
                                  ('evaluation', source.signal_end, source.signal_end+timedelta(days=7))):
                end = min(end, at, source.observed_at)
                rows = conn.execute('''SELECT PRODUCT_ID,KIND,CASE WHEN KIND='purchase' THEN COUNT(DISTINCT ORDER_ID) ELSE COUNT(*) END FROM ADVERGENT.BR_EVENTS
                    WHERE SOURCE_HASH={h} AND EVENT_AT>={start} AND EVENT_AT<{end}
                    GROUP BY PRODUCT_ID,KIND''', dict(h=digest, start=start.isoformat(), end=end.isoformat())).fetchall()
                counts.update({(pid, w, kind): int(n) for pid, kind, n in rows})
            linked = int(conn.execute('''SELECT COUNT(*) FROM (SELECT DISTINCT ORDER_ID,PRODUCT_ID FROM ADVERGENT.BR_EVENTS
                WHERE SOURCE_HASH={h} AND KIND='purchase' AND EVENT_AT<{cutoff})''',
                dict(h=digest, cutoff=min(at, source.observed_at).isoformat())).fetchval())
        inv = self.inventory_data(pins['inventory'], at=at, dependencies_current=current, expected_finance=pins['finance'])
        fin = self.finance_data(pins['finance'], tuple(pins[k] for k in ('commerce', 'ads', 'attribution')))
        margins = {}
        for pid in products:
            vids = {r.id for r in variants if r.data['product_id'] == pid}
            lines = [r for r in fin['lines'] if r['evidence']['original_line']['variant_id'] in vids]
            sales = sum(r['net_sales_paise'] for r in lines)
            margins[pid] = (sum(r['expected_before_ads_paise'] for r in lines)*10000//sales
                           if sales > 0 and lines and all(r['expected_before_ads_paise'] is not None for r in lines) else None)
        return evaluate(source, counts, inv['products'], margins, at, current, digest, linked)
