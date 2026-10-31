"""Cohort joins and event arithmetic live only in the Exasol adapter."""
from datetime import datetime
from .cohorts import evaluate
from .contracts import AnalyticsUnavailable


class CohortsSQL:
    def cohort_data(self, pins, cutoff, history_start):
        # Verifies all typed finance events, retained payloads and pinned upstream cores.
        finance = self.finance_data(pins['finance'], tuple(pins[k] for k in ('commerce', 'ads', 'attribution')))
        for kind in ('orders', 'lines', 'variants'):
            self.commerce_records(pins['commerce'], kind, limit=None)
        source = {r['line_id']: r for r in finance['lines']}
        with self.connection() as c:
            rows = c.execute('''SELECT o.CUSTOMER_ID,o.SOURCE_ID,a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID
                FROM ADVERGENT.COMMERCE_ORDERS o JOIN ADVERGENT.ATTR_ORDERS a
                ON a.DATASET_ID={tid} AND a.ORDER_ID=o.SOURCE_ID WHERE o.DATASET_ID={cid}''',
                dict(tid=pins['attribution'], cid=pins['commerce'])).fetchall()
            line_rows = c.execute('''SELECT l.SOURCE_ID,l.ORDER_ID,v.PRODUCT_ID,l.QUANTITY*l.UNIT_PRICE_PAISE-l.DISCOUNT_PAISE
                FROM ADVERGENT.COMMERCE_LINES l JOIN ADVERGENT.COMMERCE_VARIANTS v
                ON v.DATASET_ID=l.DATASET_ID AND v.SOURCE_ID=l.VARIANT_ID WHERE l.DATASET_ID={cid}''',
                dict(cid=pins['commerce'])).fetchall()
            event_rows = c.execute('''SELECT e.EVENT_ID,e.LINE_ID,o.CUSTOMER_ID,e.ORDER_ID,
                e.NET_SALES_PAISE-e.NET_PRODUCT_COST_PAISE-e.VARIABLE_PAISE
                FROM ADVERGENT.FIN_EVENTS e JOIN ADVERGENT.COMMERCE_ORDERS o
                ON o.DATASET_ID={cid} AND o.SOURCE_ID=e.ORDER_ID WHERE e.DATASET_ID={fid}''',
                dict(cid=pins['commerce'], fid=pins['finance'])).fetchall()
        evidence = {r['order_id']: r['evidence']['order'] for r in finance['lines']}
        if len(rows) != len(evidence) or len(line_rows) != len(source):
            raise AnalyticsUnavailable('Incomplete cohort joins')
        orders = [dict(customer_id=r[0], order_id=r[1], campaign=list(r[2:]),
                       delivered_at=evidence[r[1]]['delivered_at']) for r in rows]
        lines = [dict(order_id=r[1], product_id=r[2], merchandise_paise=int(r[3])) for r in line_rows]
        event_source = {e['id']: e for line in finance['lines'] for e in line['events']}
        if len(event_rows) != len(event_source): raise AnalyticsUnavailable('Incomplete cohort events')
        events = []
        for eid, lid, customer, oid, contribution in event_rows:
            line = source[lid]
            correction = line['evidence']['correction']
            # Only delivery COGS and recovery valuations depend on the corrected cost.
            correction_at = correction['effective_at'] if correction and (eid.endswith(':delivery') or ':recovery:' in eid) else None
            events.append(dict(customer_id=customer, order_id=oid, at=event_source[eid]['occurred_at'],
                contribution_paise=int(contribution) if contribution is not None else None,
                correction_at=correction_at, estimated=line['cost_status']=='estimated' or line['expense_status']=='estimated'))
        return evaluate(orders, lines, events, cutoff, history_start)
