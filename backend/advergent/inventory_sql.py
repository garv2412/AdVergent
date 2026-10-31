"""Exasol storage, typed input verification and inventory feature SQL."""
import json
from datetime import datetime, timezone
from .commerce import canonical
from .contracts import AnalyticsUnavailable

FIELDS=('variant_id','available','committed','merchant_reserve','stock_observed_at','eligible_units','in_stock_seconds','merchant_weight')


class InventorySQL:
    def migrate_inventory(self,conn):
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.INV_OBSERVATIONS (DATASET_ID VARCHAR(36),VARIANT_ID VARCHAR(100),AVAILABLE DECIMAL(18,0),COMMITTED DECIMAL(18,0),MERCHANT_RESERVE DECIMAL(18,0),STOCK_OBSERVED_AT VARCHAR(40),ELIGIBLE_UNITS DECIMAL(18,0),IN_STOCK_SECONDS DECIMAL(18,0),MERCHANT_WEIGHT DECIMAL(18,0),PAYLOAD VARCHAR(2000000),PRIMARY KEY(DATASET_ID,VARIANT_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.INV_COMPLETE (DATASET_ID VARCHAR(36),FINANCE_ID VARCHAR(36),CONFIGURATION VARCHAR(2000000),PRIMARY KEY(DATASET_ID) ENABLE)')

    def load_inventory(self,dataset,fid,f):
        fin=self.finance_data(fid)
        with self.connection() as conn:
            cid=conn.execute('SELECT COMMERCE_ID FROM ADVERGENT.FIN_COMPLETE WHERE DATASET_ID={fid}',dict(fid=fid)).fetchval()
        variants=self.commerce_records(cid,'variants',limit=None)
        if {r.variant_id for r in f.observations}!={r.id for r in variants}:raise ValueError('Complete variant inventory observations required')
        if set(f.lead_days)!={r.data['product_id'] for r in variants}:raise ValueError('Complete lead settings required, null for unknown')
        if any(r.variant_id not in {v.id for v in variants} for r in f.receipts):raise ValueError('Unknown receipt variant')
        # Complete pinned financial data has already been validated before publication.
        if not fin['reconciled']:raise ValueError('Finance not reconciled')
        with self.connection() as conn:
            aid=conn.execute('SELECT ADS_ID FROM ADVERGENT.FIN_COMPLETE WHERE DATASET_ID={fid}',dict(fid=fid)).fetchval()
        resources={(r['platform'],r['account_id'],r['id']) for r in self.ad_data(aid)['resources']}
        if any(r.key not in resources for r in f.resource_states):raise ValueError('Unknown resource state')
        with self.connection() as conn:
            if conn.execute('SELECT COUNT(*) FROM ADVERGENT.INV_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchval():return
            for r in f.observations:
                payload=r.model_dump(mode='json')
                params=dict(zip(FIELDS,[payload[k] for k in FIELDS],strict=True),id=dataset,payload=canonical(payload))
                conn.execute('INSERT INTO ADVERGENT.INV_OBSERVATIONS VALUES ({id},'+','.join('{'+k+'}' for k in FIELDS)+',{payload})',params)
            conn.execute('INSERT INTO ADVERGENT.INV_COMPLETE VALUES ({id},{fid},{config})',dict(id=dataset,fid=fid,config=canonical(f.model_dump(mode='json'))))
            conn.commit()

    def inventory_data(self,dataset,at=None,dependencies_current=True,expected_finance=None):
        from .inventory import InventoryFixture,assess,recommendations
        from .attribution import Mapping
        at=at or datetime.now(timezone.utc)
        with self.connection() as conn:
            complete=conn.execute('SELECT FINANCE_ID,CONFIGURATION FROM ADVERGENT.INV_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchone()
            if not complete or (expected_finance is not None and complete[0]!=expected_finance):raise AnalyticsUnavailable('Incomplete inventory or dependency mismatch')
            fid,config=complete;f=InventoryFixture.model_validate_json(config)
            deps=conn.execute('SELECT COMMERCE_ID,ADS_ID,ATTRIBUTION_ID FROM ADVERGENT.FIN_COMPLETE WHERE DATASET_ID={fid}',dict(fid=fid)).fetchone()
            if not deps:raise AnalyticsUnavailable('Missing finance input')
            cid,aid,tid=deps
            source=[]
            for row in conn.execute('SELECT '+','.join(k.upper() for k in FIELDS)+',PAYLOAD FROM ADVERGENT.INV_OBSERVATIONS WHERE DATASET_ID={id} ORDER BY VARIANT_ID',dict(id=dataset)).fetchall():
                payload=json.loads(row[-1])
                if list(row[:-1])!=[payload[k] for k in FIELDS]:raise AnalyticsUnavailable('Inventory typed/source mismatch')
                source.append(payload)
            if sorted(map(canonical,source))!=sorted(canonical(r.model_dump(mode='json')) for r in f.observations):raise AnalyticsUnavailable('Inventory configuration/source mismatch')
            variants=self.commerce_records(cid,'variants',limit=None)
            if {r.id for r in variants}!={r['variant_id'] for r in source}:raise AnalyticsUnavailable('Inventory variant mismatch')
            # Available already excludes commitments. A separate reserve is subtracted once.
            sell='GREATEST(0,i.AVAILABLE-i.MERCHANT_RESERVE)'
            velocity='CASE WHEN i.IN_STOCK_SECONDS>0 THEN i.ELIGIBLE_UNITS*86400.0/i.IN_STOCK_SECONDS ELSE NULL END'
            cover=f'CASE WHEN i.ELIGIBLE_UNITS>0 AND i.IN_STOCK_SECONDS>0 THEN ({sell})*i.IN_STOCK_SECONDS/(i.ELIGIBLE_UNITS*86400.0) ELSE NULL END'
            rows=conn.execute('SELECT i.VARIANT_ID,v.PRODUCT_ID,v."SIZE",'+sell+','+velocity+','+cover+' FROM ADVERGENT.INV_OBSERVATIONS i JOIN ADVERGENT.COMMERCE_VARIANTS v ON v.DATASET_ID={cid} AND v.SOURCE_ID=i.VARIANT_ID WHERE i.DATASET_ID={id} ORDER BY i.VARIANT_ID',dict(id=dataset,cid=cid)).fetchall()
            byid={r['variant_id']:r for r in source}
            features=[dict(**byid[r[0]],product_id=r[1],size=r[2],sellable_units=int(r[3]),daily_velocity=str(r[4]) if r[4] is not None else None,raw_days_of_cover=str(r[5]) if r[5] is not None else None) for r in rows]
            reliable=f'(i.ELIGIBLE_UNITS>={f.min_units} AND i.IN_STOCK_SECONDS>={f.min_exposure_days*86400})'
            all_reliable=f'SUM(CASE WHEN {reliable} THEN 0 ELSE 1 END)=0'
            demand=f'CASE WHEN {all_reliable} THEN SUM({velocity}) ELSE NULL END'
            # Weight by in-stock demand rates; complete explicit merchant weights are the only fallback.
            unavailable=f'CASE WHEN {all_reliable} THEN 10000*SUM(CASE WHEN ({sell})=0 THEN ({velocity}) ELSE 0 END)/SUM({velocity}) WHEN COUNT(i.MERCHANT_WEIGHT)=COUNT(*) AND SUM(i.MERCHANT_WEIGHT)>0 THEN 10000*SUM(CASE WHEN ({sell})=0 THEN i.MERCHANT_WEIGHT ELSE 0 END)/SUM(i.MERCHANT_WEIGHT) ELSE NULL END'
            grouped=conn.execute('SELECT v.PRODUCT_ID,SUM('+sell+'),'+demand+',CASE WHEN '+all_reliable+' THEN SUM('+sell+')/SUM('+velocity+') ELSE NULL END,'+unavailable+' FROM ADVERGENT.INV_OBSERVATIONS i JOIN ADVERGENT.COMMERCE_VARIANTS v ON v.DATASET_ID={cid} AND v.SOURCE_ID=i.VARIANT_ID WHERE i.DATASET_ID={id} GROUP BY v.PRODUCT_ID',dict(id=dataset,cid=cid)).fetchall()
            aggregates={r[0]:dict(sellable_units=int(r[1]),daily_velocity=r[2],days_of_cover=r[3],unavailable_weight_bps=r[4]) for r in grouped}
            products=assess(f,features,at,aggregates)
            finance=self.finance_data(fid,tuple(deps));ads=self.ad_data(aid);attr=self.attribution_data(tid)
            mappings=[Mapping.model_validate_json(canonical(m)) for m in attr['mapping_evidence']]
            proposals=recommendations(f,products,ads['resources'],mappings,finance,at,dependencies_current)
            # An SQL aggregation independently reconciles exact sellable stock.
            total=int(conn.execute('SELECT SUM('+sell+') FROM ADVERGENT.INV_OBSERVATIONS i WHERE i.DATASET_ID={id}',dict(id=dataset)).fetchval())
            if sum(p['sellable_units'] for p in products)!=total:raise AnalyticsUnavailable('Inventory stock reconciliation failed')
            return dict(products=products,recommendations=proposals,sellable_units=total,variants=len(rows),reconciled=True,
                assumptions={k:v for k,v in f.model_dump(mode='json').items() if k not in ('observations','receipts','resource_states')},
                demand_basis='Synthetic warehouse eligible-unit counters over the stated window and observed in-stock seconds; independent inventory evidence, not additional commerce orders or revenue',
                finance_id=fid,evaluated_at=at.isoformat())

    def verify_inventory(self,dataset,f,expected_finance=None):
        with self.connection() as conn:
            actual=conn.execute('SELECT CONFIGURATION FROM ADVERGENT.INV_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchval()
            if actual!=canonical(f.model_dump(mode='json')):raise AnalyticsUnavailable('Inventory full read-back mismatch')
        self.inventory_data(dataset,expected_finance=expected_finance)
