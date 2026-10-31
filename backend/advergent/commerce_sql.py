"""Exasol-only commerce storage/query implementation; mixed into the adapter."""
from .commerce import KINDS, canonical
from .contracts import AnalyticsUnavailable, CommerceTotals

# Typed core columns support analytical joins; payload preserves source provenance.
TABLES = {
    'products': [('title', 'VARCHAR(500)'), ('status', 'VARCHAR(20)')],
    'variants': [('product_id', 'VARCHAR(100)'), ('sku', 'VARCHAR(100)'), ('size', 'VARCHAR(30)'), ('color', 'VARCHAR(100)'), ('price_paise', 'DECIMAL(18,0)'), ('unit_cost_paise', 'DECIMAL(18,0)'), ('cost_status', 'VARCHAR(20)')],
    'customers': [('synthetic_key', 'VARCHAR(100)')],
    'orders': [('customer_id', 'VARCHAR(100)'), ('currency', 'VARCHAR(3)'), ('placed_at', 'VARCHAR(40)'), ('payment_method', 'VARCHAR(20)'), ('payment_status', 'VARCHAR(20)'), ('fulfillment_status', 'VARCHAR(20)')],
    'lines': [('order_id', 'VARCHAR(100)'), ('variant_id', 'VARCHAR(100)'), ('quantity', 'DECIMAL(18,0)'), ('unit_price_paise', 'DECIMAL(18,0)'), ('discount_paise', 'DECIMAL(18,0)'), ('tax_paise', 'DECIMAL(18,0)'), ('unit_cost_paise', 'DECIMAL(18,0)'), ('cost_status', 'VARCHAR(20)')],
    'refunds': [('order_id', 'VARCHAR(100)'), ('line_id', 'VARCHAR(100)'), ('quantity', 'DECIMAL(18,0)'), ('merchandise_paise', 'DECIMAL(18,0)'), ('tax_paise', 'DECIMAL(18,0)'), ('refunded_at', 'VARCHAR(40)'), ('recovery', 'VARCHAR(20)')],
    'inventory': [('variant_id', 'VARCHAR(100)'), ('location_id', 'VARCHAR(30)'), ('available', 'DECIMAL(18,0)'), ('committed', 'DECIMAL(18,0)'), ('merchant_reserve', 'DECIMAL(18,0)')],
}


class CommerceSQL:
    def migrate_commerce(self, conn):
        for kind, columns in TABLES.items():
            fields = ','.join(f'"{name.upper()}" {sql_type}' for name, sql_type in columns)
            conn.execute(f'CREATE TABLE IF NOT EXISTS ADVERGENT.COMMERCE_{kind.upper()} (DATASET_ID VARCHAR(36), SOURCE_ID VARCHAR(100), UPDATED_AT VARCHAR(40), PAYLOAD VARCHAR(2000000), {fields}, PRIMARY KEY(DATASET_ID,SOURCE_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.COMMERCE_COMPLETE (DATASET_ID VARCHAR(36), PRIMARY KEY(DATASET_ID) ENABLE)')

    def load_commerce(self, dataset_id, records):
        with self.connection() as conn:
            if conn.execute('SELECT COUNT(*) FROM ADVERGENT.COMMERCE_COMPLETE WHERE DATASET_ID={id}', {'id': dataset_id}).fetchval():
                return
            for kind in KINDS:
                group = [record for record in records if record.kind == kind and not record.deleted]
                columns = [name for name, _ in TABLES[kind]]
                for start in range(0, len(group), 100):
                    batch = group[start:start + 100]
                    values, params = [], {}
                    for index, record in enumerate(batch):
                        row = [dataset_id, record.id, record.updated_at.isoformat(), canonical(record.model_dump(mode='json'))] + [record.data[name] for name in columns]
                        keys = [f'v{index}_{n}' for n in range(len(row))]
                        values.append('(' + ','.join('{' + key + '}' for key in keys) + ')')
                        params.update(zip(keys, row, strict=True))
                    conn.execute(f'INSERT INTO ADVERGENT.COMMERCE_{kind.upper()} VALUES ' + ','.join(values), params)
            conn.execute('INSERT INTO ADVERGENT.COMMERCE_COMPLETE VALUES ({id})', {'id': dataset_id})
            conn.commit()

    def verify_commerce(self, dataset_id, records):
        # Full read-back verifies every field, including explicit null costs and
        # source timestamps, instead of trusting a completion marker or counts.
        expected = {(r.kind, r.id): r for r in records if not r.deleted}
        actual = {}
        for kind in KINDS:
            for record in self.commerce_records(dataset_id, kind, limit=None):
                actual[(kind, record.id)] = record
        if actual != expected:
            raise AnalyticsUnavailable('Commerce read-back mismatch')
        self.commerce_totals(dataset_id)

    def commerce_records(self, dataset_id, kind, limit=50, offset=0):
        from .commerce import Record
        if kind not in KINDS:
            raise ValueError('Unknown commerce collection')
        paging = '' if limit is None else f' LIMIT {int(limit)} OFFSET {int(offset)}'
        with self.connection() as conn:
            fields = ','.join(f'"{name.upper()}"' for name, _ in TABLES[kind])
            rows = conn.execute(f'SELECT PAYLOAD,SOURCE_ID,UPDATED_AT,{fields} FROM ADVERGENT.COMMERCE_{kind.upper()} WHERE DATASET_ID={{id}} ORDER BY SOURCE_ID' + paging, {'id': dataset_id}).fetchall()
            records = []
            for row in rows:
                record = Record.model_validate_json(row[0])
                expected = [record.id, record.updated_at.isoformat()] + [record.data[name] for name, _ in TABLES[kind]]
                if list(row[1:]) != expected:
                    raise AnalyticsUnavailable('Commerce core/source mismatch')
                records.append(record)
            return records

    def commerce_totals(self, dataset_id):
        with self.connection() as conn:
            counts = {}
            for kind in KINDS:
                counts[kind] = int(conn.execute(f'SELECT COUNT(*) FROM ADVERGENT.COMMERCE_{kind.upper()} WHERE DATASET_ID={{id}}', {'id': dataset_id}).fetchval())
            line = conn.execute('''SELECT COALESCE(SUM(QUANTITY),0),COALESCE(SUM(QUANTITY*UNIT_PRICE_PAISE-DISCOUNT_PAISE),0),
                SUM(CASE WHEN UNIT_COST_PAISE IS NULL THEN 1 ELSE 0 END)
                FROM ADVERGENT.COMMERCE_LINES WHERE DATASET_ID={id}''', {'id': dataset_id}).fetchone()
            stock = conn.execute('SELECT COALESCE(SUM(AVAILABLE),0),COALESCE(SUM(CASE WHEN AVAILABLE>MERCHANT_RESERVE THEN AVAILABLE-MERCHANT_RESERVE ELSE 0 END),0) FROM ADVERGENT.COMMERCE_INVENTORY WHERE DATASET_ID={id}', {'id': dataset_id}).fetchone()
            refunded = conn.execute('SELECT COALESCE(SUM(QUANTITY),0),COALESCE(SUM(MERCHANDISE_PAISE),0) FROM ADVERGENT.COMMERCE_REFUNDS WHERE DATASET_ID={id}', {'id': dataset_id}).fetchone()
            # An actual analytical join, with separately preserved fulfillment/payment states.
            delivered = conn.execute("SELECT COUNT(*) FROM ADVERGENT.COMMERCE_LINES l JOIN ADVERGENT.COMMERCE_ORDERS o ON l.DATASET_ID=o.DATASET_ID AND l.ORDER_ID=o.SOURCE_ID WHERE l.DATASET_ID={id} AND o.FULFILLMENT_STATUS='delivered'", {'id': dataset_id}).fetchval()
            return CommerceTotals(**counts, ordered_units=int(line[0]), placed_merchandise_paise=int(line[1]), missing_cost_lines=int(line[2] or 0), available_units=int(stock[0]), sellable_units=int(stock[1]), refunded_units=int(refunded[0]), refund_merchandise_paise=int(refunded[1]), delivered_lines=int(delivered))
