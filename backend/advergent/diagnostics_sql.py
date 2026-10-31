"""Exasol-only diagnostic storage, verification and analytical joins."""
import json
from datetime import datetime,timezone
from .commerce import canonical
from .contracts import AnalyticsUnavailable

CHECK_FIELDS=('id','platform','account_id','resource_id','variant_id','url','observed_at','outcome','redirect_to','page_variant_id','page_price_paise','advertised_price_paise','currency','offer_expires_at','page_text')
WINDOW_FIELDS=('id','platform','account_id','resource_id','creative_id','start','end','audience','placement','objective','impressions','clicks')


class DiagnosticsSQL:
    def migrate_diagnostics(self,conn):
        for table,fields in (('DIAG_CHECKS',CHECK_FIELDS),('DIAG_WINDOWS',WINDOW_FIELDS)):
            columns=','.join('"'+k.upper()+'" '+('DECIMAL(18,0)' if k in ('page_price_paise','advertised_price_paise','impressions','clicks') else 'VARCHAR(2000)') for k in fields)
            conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.'+table+' (DATASET_ID VARCHAR(36),'+columns+',PAYLOAD VARCHAR(2000000),PRIMARY KEY(DATASET_ID,"ID") ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.DIAG_COMPLETE (DATASET_ID VARCHAR(36),INVENTORY_ID VARCHAR(36),CONFIGURATION VARCHAR(2000000),PRIMARY KEY(DATASET_ID) ENABLE)')

    def load_diagnostics(self,dataset,iid,f):
        with self.connection() as conn:
            if conn.execute('SELECT COUNT(*) FROM ADVERGENT.DIAG_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchval():return
            for table,fields,rows in (('DIAG_CHECKS',CHECK_FIELDS,f.checks),('DIAG_WINDOWS',WINDOW_FIELDS,f.windows)):
                for row in rows:
                    payload=row.model_dump(mode='json')
                    conn.execute('INSERT INTO ADVERGENT.'+table+' VALUES ({dataset},'+','.join('{'+k+'}' for k in fields)+',{payload})',dict(dataset=dataset,payload=canonical(payload),**payload))
            conn.execute('INSERT INTO ADVERGENT.DIAG_COMPLETE VALUES ({id},{iid},{config})',dict(id=dataset,iid=iid,config=canonical(f.model_dump(mode='json'))));conn.commit()

    def diagnostics_data(self,dataset,at=None,dependencies_current=True,expected_inventory=None):
        from .diagnostics import DiagnosticsFixture,evaluate
        from .attribution import Mapping
        at=at or datetime.now(timezone.utc)
        with self.connection() as conn:
            marker=conn.execute('SELECT INVENTORY_ID,CONFIGURATION FROM ADVERGENT.DIAG_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchone()
            if not marker or (expected_inventory is not None and marker[0]!=expected_inventory):raise AnalyticsUnavailable('Diagnostic input mismatch')
            iid,config=marker;f=DiagnosticsFixture.model_validate_json(config)
            for table,fields,expected in (('DIAG_CHECKS',CHECK_FIELDS,f.checks),('DIAG_WINDOWS',WINDOW_FIELDS,f.windows)):
                source=[]
                for row in conn.execute('SELECT '+','.join('"'+k.upper()+'"' for k in fields)+',PAYLOAD FROM ADVERGENT.'+table+' WHERE DATASET_ID={id}',dict(id=dataset)).fetchall():
                    payload=json.loads(row[-1])
                    if list(row[:-1])!=[None if payload[k]=='' else payload[k] for k in fields]:raise AnalyticsUnavailable('Diagnostic typed/source mismatch')
                    source.append(payload)
                if sorted(map(canonical,source))!=sorted(canonical(r.model_dump(mode='json')) for r in expected):raise AnalyticsUnavailable('Diagnostic source/configuration mismatch')
            fid=conn.execute('SELECT FINANCE_ID FROM ADVERGENT.INV_COMPLETE WHERE DATASET_ID={id}',dict(id=iid)).fetchval()
            deps=conn.execute('SELECT COMMERCE_ID,ADS_ID,ATTRIBUTION_ID FROM ADVERGENT.FIN_COMPLETE WHERE DATASET_ID={id}',dict(id=fid)).fetchone()
            if not deps:raise AnalyticsUnavailable('Missing diagnostic dependencies')
            cid,aid,tid=deps
            variants={r.id:r.data for r in self.commerce_records(cid,'variants',limit=None)}
            products={r.id:r.data for r in self.commerce_records(cid,'products',limit=None)}
            ads=self.ad_data(aid);keys={(r['platform'],r['account_id'],r['id']) for r in ads['resources']}
            if any(r.key not in keys for r in f.checks+f.windows) or any(r.variant_id not in variants for r in f.checks):raise AnalyticsUnavailable('Unknown diagnostic resource or variant')
            # Actual typed analytical join: exact selected variant, never product min-price.
            prices=conn.execute('SELECT c."ID",v.SOURCE_ID,v.PRICE_PAISE,c.PAGE_PRICE_PAISE,c.ADVERTISED_PRICE_PAISE FROM ADVERGENT.DIAG_CHECKS c JOIN ADVERGENT.COMMERCE_VARIANTS v ON v.DATASET_ID={cid} AND v.SOURCE_ID=c.VARIANT_ID WHERE c.DATASET_ID={id}',dict(cid=cid,id=dataset)).fetchall()
            if len(prices)!=len(f.checks):raise AnalyticsUnavailable('Diagnostic variant reconciliation failed')
            ctr=conn.execute('SELECT "ID",CASE WHEN IMPRESSIONS>0 THEN CLICKS*1.0/IMPRESSIONS ELSE NULL END FROM ADVERGENT.DIAG_WINDOWS WHERE DATASET_ID={id}',dict(id=dataset)).fetchall()
            inventory=self.inventory_data(iid,at=at,dependencies_current=dependencies_current,expected_finance=fid)
            mappings=[Mapping.model_validate_json(canonical(m)) for m in self.attribution_data(tid)['mapping_evidence']]
            data=evaluate(f,variants,products,ads['resources'],mappings,inventory,at,dependencies_current)
            data['variant_price_evidence']=[dict(check_id=r[0],variant_id=r[1],catalog_price_paise=int(r[2]),page_price_paise=int(r[3]) if r[3] is not None else None,advertised_price_paise=int(r[4]) if r[4] is not None else None) for r in prices]
            data['ctr_evidence']=[dict(window_id=r[0],ctr=str(r[1]) if r[1] is not None else None) for r in ctr]
            return data

    def verify_diagnostics(self,dataset,f,expected_inventory=None):
        with self.connection() as conn:
            if conn.execute('SELECT CONFIGURATION FROM ADVERGENT.DIAG_COMPLETE WHERE DATASET_ID={id}',dict(id=dataset)).fetchval()!=canonical(f.model_dump(mode='json')):raise AnalyticsUnavailable('Diagnostic read-back mismatch')
        self.diagnostics_data(dataset,expected_inventory=expected_inventory)
