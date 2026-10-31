"""Clearance analytical input joins stay inside the Exasol adapter."""
from .contracts import AnalyticsUnavailable
from .clearance import evaluate


class ClearanceSQL:
    def clearance_data(self, inventory_id, finance_id, commerce_id, request, at, dependencies_current):
        inventory = self.inventory_data(inventory_id, at=at, dependencies_current=dependencies_current,
                                        expected_finance=finance_id)
        with self.connection() as conn:
            cid = conn.execute('SELECT COMMERCE_ID FROM ADVERGENT.FIN_COMPLETE WHERE DATASET_ID={id}', dict(id=finance_id)).fetchval()
            if cid != commerce_id:
                raise AnalyticsUnavailable('Clearance finance commerce mismatch')
        # Validate typed catalog columns against retained source before the analytical join.
        variants = self.commerce_records(commerce_id, 'variants', limit=None)
        with self.connection() as conn:
            rows = conn.execute('''SELECT v.SOURCE_ID,v.PRODUCT_ID,v.PRICE_PAISE,v.UNIT_COST_PAISE,v.COST_STATUS,
                GREATEST(0,i.AVAILABLE-i.MERCHANT_RESERVE)
                FROM ADVERGENT.INV_OBSERVATIONS i JOIN ADVERGENT.COMMERCE_VARIANTS v
                ON v.DATASET_ID={cid} AND v.SOURCE_ID=i.VARIANT_ID
                WHERE i.DATASET_ID={iid} ORDER BY v.SOURCE_ID''', dict(cid=commerce_id, iid=inventory_id)).fetchall()
        features = {v['variant_id']: v for p in inventory['products'] for v in p['variants']}
        if len(rows) != len(variants) or len(rows) != len(features):
            raise AnalyticsUnavailable('Incomplete clearance join')
        inputs = []
        for vid, pid, price, cost, status, stock in rows:
            f = features[vid]
            if int(stock) != f['sellable_units'] or pid != f['product_id']:
                raise AnalyticsUnavailable('Clearance stock reconciliation failed')
            inputs.append(dict(variant_id=vid, product_id=pid, price_paise=int(price),
                unit_cost_paise=int(cost) if cost is not None else None, cost_status=status,
                sellable_units=int(stock), stock_observed_at=f['stock_observed_at'], fresh=f['fresh'],
                demand_status=f['demand_status'], daily_velocity=f['daily_velocity']))
        return evaluate(inputs, request, dependencies_current)
