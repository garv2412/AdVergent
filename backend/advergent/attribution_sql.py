"""Exasol-only attribution storage, order-line joins and reconciliation."""
import json
from .commerce import canonical
from .contracts import AnalyticsUnavailable


class AttributionSQL:
    def migrate_attribution(self, conn):
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.ATTR_ENTITIES (DATASET_ID VARCHAR(36), KIND VARCHAR(30), ENTITY_ID VARCHAR(300), PAYLOAD VARCHAR(2000000), PRIMARY KEY(DATASET_ID,KIND,ENTITY_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.ATTR_ORDERS (DATASET_ID VARCHAR(36), ORDER_ID VARCHAR(100), PLATFORM VARCHAR(10), ACCOUNT_ID VARCHAR(80), CAMPAIGN_ID VARCHAR(80), PRIMARY KEY(DATASET_ID,ORDER_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.ATTR_COMPLETE (DATASET_ID VARCHAR(36), COMMERCE_ID VARCHAR(36), PRIMARY KEY(DATASET_ID) ENABLE)')

    def load_attribution(self, dataset_id, commerce_id, data):
        with self.connection() as conn:
            if conn.execute('SELECT COUNT(*) FROM ADVERGENT.ATTR_COMPLETE WHERE DATASET_ID={id}', dict(id=dataset_id)).fetchval():
                return
            for kind, rows in data.items():
                for start in range(0, len(rows), 100):
                    params, values = {}, []
                    for index, row in enumerate(rows[start:start + 100]):
                        key = row.get('id', row.get('order_id')) if kind != 'mappings' else ':'.join(row[k] for k in ('platform', 'account_id', 'resource_id'))
                        params.update({f'd{index}': dataset_id, f'k{index}': kind, f'i{index}': key, f'p{index}': canonical(row)})
                        values.append('(' + ','.join('{' + f'{p}{index}' + '}' for p in ('d', 'k', 'i', 'p')) + ')')
                    conn.execute('INSERT INTO ADVERGENT.ATTR_ENTITIES VALUES ' + ','.join(values), params)
            rows = data['assignments']
            for start in range(0, len(rows), 100):
                params, values = {}, []
                for index, row in enumerate(rows[start:start + 100]):
                    vals = [dataset_id] + [row[k] for k in ('order_id', 'platform', 'account_id', 'campaign_id')]
                    keys = [f'v{index}_{j}' for j in range(5)]
                    params.update(zip(keys, vals, strict=True))
                    values.append('(' + ','.join('{' + k + '}' for k in keys) + ')')
                conn.execute('INSERT INTO ADVERGENT.ATTR_ORDERS VALUES ' + ','.join(values), params)
            conn.execute('INSERT INTO ADVERGENT.ATTR_COMPLETE VALUES ({id},{commerce})', dict(id=dataset_id, commerce=commerce_id))
            conn.commit()

    def attribution_data(self, dataset_id):
        with self.connection() as conn:
            commerce = conn.execute('SELECT COMMERCE_ID FROM ADVERGENT.ATTR_COMPLETE WHERE DATASET_ID={id}', dict(id=dataset_id)).fetchval()
            if not commerce:
                raise AnalyticsUnavailable('Incomplete attribution')
            data = {k: [] for k in ('assignments', 'mappings', 'mapping_evidence', 'clicks', 'platform_claims')}
            for kind, payload in conn.execute('SELECT KIND,PAYLOAD FROM ADVERGENT.ATTR_ENTITIES WHERE DATASET_ID={id} ORDER BY KIND,ENTITY_ID', dict(id=dataset_id)).fetchall():
                data[kind].append(json.loads(payload))
            core = conn.execute('SELECT ORDER_ID,PLATFORM,ACCOUNT_ID,CAMPAIGN_ID FROM ADVERGENT.ATTR_ORDERS WHERE DATASET_ID={id}', dict(id=dataset_id)).fetchall()
            expected = {(r['order_id'], r['platform'], r['account_id'], r['campaign_id']) for r in data['assignments']}
            if set(core) != expected or len(core) != len(data['assignments']):
                raise AnalyticsUnavailable('Attribution core mismatch')
            # Each order appears once; each line joins once, including unmatched orders.
            groups = conn.execute('''SELECT a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID,COUNT(DISTINCT a.ORDER_ID),COUNT(l.SOURCE_ID),
                COALESCE(SUM(l.QUANTITY*l.UNIT_PRICE_PAISE-l.DISCOUNT_PAISE),0)
                FROM ADVERGENT.ATTR_ORDERS a LEFT JOIN ADVERGENT.COMMERCE_LINES l
                ON l.DATASET_ID={commerce} AND l.ORDER_ID=a.ORDER_ID
                WHERE a.DATASET_ID={id} GROUP BY a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID
                ORDER BY a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID''', dict(id=dataset_id, commerce=commerce)).fetchall()
            data['groups'] = [dict(platform=r[0], account_id=r[1], campaign_id=r[2], orders=int(r[3]), lines=int(r[4]), placed_merchandise_paise=int(r[5])) for r in groups]
            # Product allocation follows purchased lines, never the advertised product set.
            products = conn.execute('''SELECT a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID,v.PRODUCT_ID,COUNT(*),SUM(l.QUANTITY*l.UNIT_PRICE_PAISE-l.DISCOUNT_PAISE)
                FROM ADVERGENT.ATTR_ORDERS a JOIN ADVERGENT.COMMERCE_LINES l ON l.DATASET_ID={commerce} AND l.ORDER_ID=a.ORDER_ID
                JOIN ADVERGENT.COMMERCE_VARIANTS v ON v.DATASET_ID=l.DATASET_ID AND v.SOURCE_ID=l.VARIANT_ID
                WHERE a.DATASET_ID={id} GROUP BY a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID,v.PRODUCT_ID
                ORDER BY a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID,v.PRODUCT_ID''', dict(id=dataset_id, commerce=commerce)).fetchall()
            data['product_allocations'] = [dict(platform=r[0], account_id=r[1], campaign_id=r[2], product_id=r[3], lines=int(r[4]), placed_merchandise_paise=int(r[5])) for r in products]
            refunds = conn.execute('''SELECT r.SOURCE_ID,r.ORDER_ID,r.REFUNDED_AT,a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID
                FROM ADVERGENT.COMMERCE_REFUNDS r JOIN ADVERGENT.ATTR_ORDERS a ON a.ORDER_ID=r.ORDER_ID AND a.DATASET_ID={id}
                WHERE r.DATASET_ID={commerce} ORDER BY r.SOURCE_ID''', dict(id=dataset_id, commerce=commerce)).fetchall()
            data['refund_links'] = [dict(refund_id=r[0], order_id=r[1], refunded_at=r[2], platform=r[3], account_id=r[4], campaign_id=r[5]) for r in refunds]
            totals = self.commerce_totals(commerce)
            actual = (sum(r['orders'] for r in data['groups']), sum(r['lines'] for r in data['groups']), sum(r['placed_merchandise_paise'] for r in data['groups']))
            if actual != (totals.orders, totals.lines, totals.placed_merchandise_paise):
                raise AnalyticsUnavailable('Order allocation reconciliation failed')
            if (sum(r['lines'] for r in data['product_allocations']), sum(r['placed_merchandise_paise'] for r in data['product_allocations'])) != actual[1:] or len(refunds) != totals.refunds:
                raise AnalyticsUnavailable('Product/refund reconciliation failed')
            data['reconciliation'] = dict(orders=actual[0], lines=actual[1], placed_merchandise_paise=actual[2], refunds=len(refunds))
            return data

    def verify_attribution(self, dataset_id, commerce_id, expected):
        actual = self.attribution_data(dataset_id)
        for kind, rows in expected.items():
            if sorted(map(canonical, actual[kind])) != sorted(map(canonical, rows)):
                raise AnalyticsUnavailable('Attribution full read-back mismatch')
        with self.connection() as conn:
            if conn.execute('SELECT COMMERCE_ID FROM ADVERGENT.ATTR_COMPLETE WHERE DATASET_ID={id}', dict(id=dataset_id)).fetchval() != commerce_id:
                raise AnalyticsUnavailable('Attribution dependency mismatch')
