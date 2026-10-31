"""Exasol-only line economics, exact assignment joins and reconciliation."""
import json
from decimal import Decimal, localcontext
from .commerce import canonical
from .contracts import AnalyticsUnavailable

FIELDS=('line_id','order_id','placed_paise','delivered_paise','refunded_paise','shipping_paise','sold_cost_paise','recovered_paise','failed_loss_paise','variable_paise','reserve_paise','cash_paise','unsettled_cod_paise','cost_status','expense_status','exposed_units')
MONEY=FIELDS[2:13]


def ratio(numerator,spend):
    if numerator is None or spend==0: return None
    with localcontext() as ctx:
        ctx.prec=28
        return str(Decimal(numerator)/Decimal(spend))


class FinanceSQL:
    def migrate_finance(self,conn):
        columns='LINE_ID VARCHAR(100),ORDER_ID VARCHAR(100),'+','.join(k.upper()+' DECIMAL(18,0)' for k in MONEY)+',COST_STATUS VARCHAR(20),EXPENSE_STATUS VARCHAR(20),EXPOSED_UNITS DECIMAL(18,0)'
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.FIN_LINES (DATASET_ID VARCHAR(36),'+columns+',PAYLOAD VARCHAR(2000000),PRIMARY KEY(DATASET_ID,LINE_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.FIN_EVENTS (DATASET_ID VARCHAR(36),EVENT_ID VARCHAR(250),LINE_ID VARCHAR(100),ORDER_ID VARCHAR(100),TRANSACTION_DAY VARCHAR(10),ACQUISITION_DAY VARCHAR(10),NET_SALES_PAISE DECIMAL(18,0),NET_PRODUCT_COST_PAISE DECIMAL(18,0),VARIABLE_PAISE DECIMAL(18,0),CASH_PAISE DECIMAL(18,0),PRIMARY KEY(DATASET_ID,EVENT_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.FIN_COMPLETE (DATASET_ID VARCHAR(36),COMMERCE_ID VARCHAR(36),ADS_ID VARCHAR(36),ATTRIBUTION_ID VARCHAR(36),PRIMARY KEY(DATASET_ID) ENABLE)')

    def load_finance(self,dataset,cid,aid,tid,rows):
        with self.connection() as conn:
            if conn.execute('SELECT COUNT(*) FROM ADVERGENT.FIN_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchval(): return
            for start in range(0,len(rows),100):
                params,values={},[]
                for i,r in enumerate(rows[start:start+100]):
                    vals=[dataset]+[r[k] for k in FIELDS]+[canonical(r)]
                    keys=[f'v{i}_{j}' for j in range(len(vals))]
                    params.update(zip(keys,vals,strict=True))
                    values.append('('+','.join('{'+k+'}' for k in keys)+')')
                conn.execute('INSERT INTO ADVERGENT.FIN_LINES VALUES '+','.join(values),params)
            events=[e for r in rows for e in r['events']]
            for start in range(0,len(events),100):
                params,values={},[]
                for i,e in enumerate(events[start:start+100]):
                    vals=[dataset]+[e[k] for k in ('id','line_id','order_id','transaction_day','acquisition_day','net_sales_paise','net_product_cost_paise','variable_paise','cash_paise')]
                    keys=[f'e{i}_{j}' for j in range(len(vals))]
                    params.update(zip(keys,vals,strict=True))
                    values.append('('+','.join('{'+k+'}' for k in keys)+')')
                conn.execute('INSERT INTO ADVERGENT.FIN_EVENTS VALUES '+','.join(values),params)
            conn.execute('INSERT INTO ADVERGENT.FIN_COMPLETE VALUES ({id},{cid},{aid},{tid})',dict(id=dataset,cid=cid,aid=aid,tid=tid))
            conn.commit()

    def finance_data(self,dataset,expected_dependencies=None):
        with self.connection() as conn:
            deps=conn.execute('SELECT COMMERCE_ID,ADS_ID,ATTRIBUTION_ID FROM ADVERGENT.FIN_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchone()
            if not deps: raise AnalyticsUnavailable('Incomplete finance')
            if expected_dependencies is not None and tuple(deps)!=tuple(expected_dependencies): raise AnalyticsUnavailable('Finance dependency mismatch')
            cid,aid,tid=deps
            if conn.execute('SELECT COMMERCE_ID FROM ADVERGENT.ATTR_COMPLETE WHERE DATASET_ID={tid}',dict(tid=tid)).fetchval()!=cid: raise AnalyticsUnavailable('Finance attribution input mismatch')
            # Validate both pinned upstream cores before interpreting analytical joins.
            attr=self.attribution_data(tid)
            ads=self.ad_data(aid)
            source=[]
            columns=','.join(k.upper() for k in FIELDS)
            for row in conn.execute('SELECT '+columns+',PAYLOAD FROM ADVERGENT.FIN_LINES WHERE DATASET_ID={id} ORDER BY LINE_ID',dict(id=dataset)).fetchall():
                payload=json.loads(row[-1])
                if list(row[:-1]) != [payload[k] for k in FIELDS]: raise AnalyticsUnavailable('Finance core/source mismatch')
                source.append(payload)
            # SQL computes actual net sales, net product cost and contribution.
            net='f.DELIVERED_PAISE-f.REFUNDED_PAISE+f.SHIPPING_PAISE'
            cost='f.SOLD_COST_PAISE-f.RECOVERED_PAISE+f.FAILED_LOSS_PAISE'
            cb=f'({net})-({cost})-f.VARIABLE_PAISE'
            rows=conn.execute('SELECT f.LINE_ID,a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID,'+net+','+cost+','+cb+','+cb+'-f.RESERVE_PAISE FROM ADVERGENT.FIN_LINES f JOIN ADVERGENT.ATTR_ORDERS a ON a.DATASET_ID={tid} AND a.ORDER_ID=f.ORDER_ID WHERE f.DATASET_ID={id} ORDER BY f.LINE_ID',dict(tid=tid,id=dataset)).fetchall()
            if len(rows)!=len(source) or len(source)!=attr['reconciliation']['lines']: raise AnalyticsUnavailable('Finance assignment mismatch')
            for r,line in zip(rows,source,strict=True):
                if r[0]!=line['line_id']: raise AnalyticsUnavailable('Finance line mismatch')
                line.update(platform=r[1],account_id=r[2],campaign_id=r[3],net_sales_paise=int(r[4]),net_product_cost_paise=int(r[5]) if r[5] is not None else None,
                    contribution_before_ads_paise=int(r[6]) if r[6] is not None else None,expected_before_ads_paise=int(r[7]) if r[7] is not None else None)
            # Aggregate nullable costs explicitly; SUM alone would hide unknown costs.
            query=f"""SELECT COUNT(*),COUNT(DISTINCT f.ORDER_ID),SUM(f.PLACED_PAISE),SUM({net}),SUM(f.CASH_PAISE),SUM(f.UNSETTLED_COD_PAISE),
                SUM(CASE WHEN ({cb}) IS NULL THEN 1 ELSE 0 END),SUM(CASE WHEN f.COST_STATUS='estimated' OR f.EXPENSE_STATUS='estimated' THEN 1 ELSE 0 END),
                COALESCE(SUM({cb}),0),SUM(CASE WHEN ({cb})-f.RESERVE_PAISE IS NULL THEN 1 ELSE 0 END),COALESCE(SUM(({cb})-f.RESERVE_PAISE),0),
                SUM(f.REFUNDED_PAISE),SUM(f.DELIVERED_PAISE),SUM(f.EXPOSED_UNITS),SUM(CASE WHEN f.RESERVE_PAISE IS NULL THEN 1 ELSE 0 END),COALESCE(SUM(f.RESERVE_PAISE),0),SUM({cost}),SUM(CASE WHEN ({cost}) IS NULL THEN 1 ELSE 0 END),SUM(f.VARIABLE_PAISE),SUM(CASE WHEN f.VARIABLE_PAISE IS NULL THEN 1 ELSE 0 END)
                FROM ADVERGENT.FIN_LINES f WHERE f.DATASET_ID={{id}}"""
            def metrics(r,spend):
                r=[int(v or 0) for v in r]
                before=None if r[6] else r[8]
                expected=None if r[9] else r[10]
                return dict(net_product_cost_paise=None if r[17] else r[16],variable_paise=None if r[19] else r[18],lines=r[0],orders=r[1],placed_paise=r[2],net_sales_paise=r[3],cash_paise=r[4],unsettled_cod_paise=r[5],
                    missing_lines=r[6],estimated_lines=r[7],covered_contribution_paise=r[8],expected_missing_lines=r[9],covered_expected_paise=r[10],
                    refunded_paise=r[11],delivered_paise=r[12],exposed_units=r[13],reserve_missing_lines=r[14],reserve_paise=None if r[14] else r[15],
                    spend_paise=spend,contribution_before_ads_paise=before,contribution_after_ads_paise=before-spend if before is not None else None,
                    expected_before_ads_paise=expected,expected_after_ads_paise=expected-spend if expected is not None else None,
                    poas=ratio(before,spend),mer=ratio(r[3],spend),cost_coverage_bps=(r[0]-r[6])*10000//r[0] if r[0] else 10000)
            total=metrics(conn.execute(query,dict(id=dataset)).fetchone(),ads['spend_paise'])
            grouped=conn.execute(query.replace('SELECT COUNT(*)','SELECT a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID,COUNT(*)').replace('FROM ADVERGENT.FIN_LINES f WHERE', 'FROM ADVERGENT.FIN_LINES f JOIN ADVERGENT.ATTR_ORDERS a ON a.ORDER_ID=f.ORDER_ID AND a.DATASET_ID={tid} WHERE')+' GROUP BY a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID',dict(id=dataset,tid=tid)).fetchall()
            spend={}
            for g in ads['groups']:
                key=(g['platform'],g['account_id'],g['campaign_id'])
                spend[key]=spend.get(key,0)+g['spend_paise']
            buckets={tuple(r[:3]):metrics(r[3:],spend.get(tuple(r[:3]),0)) for r in grouped}
            # Preserve campaigns with spend and no assigned order, too.
            for key,amount in spend.items():
                if key not in buckets: buckets[key]=metrics([0]*20,amount)
            allocations=[dict(platform=k[0],account_id=k[1],campaign_id=k[2],totals=v) for k,v in sorted(buckets.items(),key=lambda item:str(item[0]))]
            for field in ('lines','orders','placed_paise','net_sales_paise','cash_paise','unsettled_cod_paise','missing_lines','covered_contribution_paise','covered_expected_paise','spend_paise','refunded_paise','delivered_paise','exposed_units'):
                if sum(g['totals'][field] for g in allocations)!=total[field]: raise AnalyticsUnavailable('Finance allocation reconciliation failed')
            if total['orders']!=attr['reconciliation']['orders'] or total['placed_paise']!=attr['reconciliation']['placed_merchandise_paise']:
                raise AnalyticsUnavailable('Finance source reconciliation failed')
            actual_keys={(r['line_id'],r['order_id']) for r in source}
            source_keys={(r.id,r.data['order_id']) for r in self.commerce_records(cid,'lines',limit=None)}
            if actual_keys != source_keys: raise AnalyticsUnavailable('Finance commerce lines mismatch')
            event_fields=('id','line_id','order_id','transaction_day','acquisition_day','net_sales_paise','net_product_cost_paise','variable_paise','cash_paise')
            event_core=conn.execute('SELECT EVENT_ID,LINE_ID,ORDER_ID,TRANSACTION_DAY,ACQUISITION_DAY,NET_SALES_PAISE,NET_PRODUCT_COST_PAISE,VARIABLE_PAISE,CASH_PAISE FROM ADVERGENT.FIN_EVENTS WHERE DATASET_ID={id}',dict(id=dataset)).fetchall()
            expected_events=[tuple(e[k] for k in event_fields) for r in source for e in r['events']]
            if set(event_core)!=set(expected_events) or len(event_core)!=len(expected_events): raise AnalyticsUnavailable('Finance event core mismatch')
            dates={}
            for label,column in (('transaction_days','TRANSACTION_DAY'),('acquisition_days','ACQUISITION_DAY')):
                event_rows=conn.execute('SELECT '+column+',COUNT(*),SUM(NET_SALES_PAISE),SUM(CASH_PAISE),SUM(CASE WHEN NET_PRODUCT_COST_PAISE IS NULL OR VARIABLE_PAISE IS NULL THEN 1 ELSE 0 END),COALESCE(SUM(NET_SALES_PAISE-NET_PRODUCT_COST_PAISE-VARIABLE_PAISE),0) FROM ADVERGENT.FIN_EVENTS WHERE DATASET_ID={id} GROUP BY '+column+' ORDER BY '+column,dict(id=dataset)).fetchall()
                dates[label]=[dict(day=r[0],events=int(r[1]),net_sales_paise=int(r[2]),cash_paise=int(r[3]),missing_events=int(r[4]),covered_contribution_paise=int(r[5]),contribution_before_ads_paise=None if r[4] else int(r[5])) for r in event_rows]
                if sum(r['net_sales_paise'] for r in dates[label])!=total['net_sales_paise'] or sum(r['cash_paise'] for r in dates[label])!=total['cash_paise']: raise AnalyticsUnavailable('Finance event reconciliation failed')
                if not total['missing_lines'] and sum(r['covered_contribution_paise'] for r in dates[label])!=total['covered_contribution_paise']: raise AnalyticsUnavailable('Finance complete-event reconciliation failed')
            sample=conn.execute("SELECT COUNT(DISTINCT l.ORDER_ID),SUM(l.QUANTITY) FROM ADVERGENT.COMMERCE_LINES l JOIN ADVERGENT.COMMERCE_ORDERS o ON o.DATASET_ID=l.DATASET_ID AND o.SOURCE_ID=l.ORDER_ID WHERE l.DATASET_ID={cid} AND o.FULFILLMENT_STATUS='delivered'",dict(cid=cid)).fetchone()
            returned=int(conn.execute("SELECT COALESCE(SUM(r.QUANTITY),0) FROM ADVERGENT.COMMERCE_REFUNDS r JOIN ADVERGENT.COMMERCE_ORDERS o ON o.DATASET_ID=r.DATASET_ID AND o.SOURCE_ID=r.ORDER_ID WHERE r.DATASET_ID={cid} AND o.FULFILLMENT_STATUS='delivered'",dict(cid=cid)).fetchval())
            reserve_evidence=dict(delivered_orders=int(sample[0]),delivered_units=int(sample[1]),returned_units=returned,exposed_units=total['exposed_units'],mature_remaining_units=int(sample[1])-returned-total['exposed_units'],calibration_sample_size=0)
            return dict(totals=total,allocations=allocations,lines=source,refund_count=len(attr['refund_links']),reconciled=True,reserve_evidence=reserve_evidence,**dates)

    def verify_finance(self,dataset,expected):
        actual=self.finance_data(dataset)['lines']
        keys=set(expected[0]) if expected else set()
        if sorted(canonical({k:r[k] for k in keys}) for r in actual)!=sorted(map(canonical,expected)):
            raise AnalyticsUnavailable('Finance full read-back mismatch')
