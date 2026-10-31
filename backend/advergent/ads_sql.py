"""Exasol ad schema, immutable loading, full read-back and analytical joins."""
import json
from .ads import hierarchy, budget_capabilities
from .commerce import canonical
from .contracts import AnalyticsUnavailable


class AdsSQL:
    def migrate_ads(self, conn):
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.AD_ENTITIES (DATASET_ID VARCHAR(36), ENTITY_KIND VARCHAR(20), ENTITY_KEY VARCHAR(250), PAYLOAD VARCHAR(2000000), PRIMARY KEY(DATASET_ID,ENTITY_KIND,ENTITY_KEY) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.AD_RESOURCES (DATASET_ID VARCHAR(36), PLATFORM VARCHAR(10), ACCOUNT_ID VARCHAR(80), RESOURCE_ID VARCHAR(80), CAMPAIGN_ID VARCHAR(80), BUDGET_ID VARCHAR(80), PRIMARY KEY(DATASET_ID,PLATFORM,ACCOUNT_ID,RESOURCE_ID) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.AD_REPORTS (DATASET_ID VARCHAR(36), REPORT_KEY VARCHAR(300), PLATFORM VARCHAR(10), ACCOUNT_ID VARCHAR(80), RESOURCE_ID VARCHAR(80), REPORTING_DAY VARCHAR(10), SPEND_PAISE DECIMAL(18,0), PAYLOAD VARCHAR(2000000), PRIMARY KEY(DATASET_ID,REPORT_KEY) ENABLE)')
        conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.AD_COMPLETE (DATASET_ID VARCHAR(36), PRIMARY KEY(DATASET_ID) ENABLE)')

    def load_ads(self, dataset_id, fixture, reports):
        with self.connection() as conn:
            if conn.execute('SELECT COUNT(*) FROM ADVERGENT.AD_COMPLETE WHERE DATASET_ID={id}', {'id': dataset_id}).fetchval():
                return
            entities = dict(accounts=[a.model_dump() for a in fixture.accounts], budgets=budget_capabilities(fixture), resources=hierarchy(fixture))
            for kind, rows in entities.items():
                for row in rows:
                    key = row['platform'] + ':' + row.get('account_id', '') + ':' + row['id']
                    conn.execute('INSERT INTO ADVERGENT.AD_ENTITIES VALUES ({id},{kind},{key},{payload})', dict(id=dataset_id, kind=kind, key=key, payload=canonical(row)))
            for row in entities['resources']:
                conn.execute('INSERT INTO ADVERGENT.AD_RESOURCES VALUES ({id},{platform},{account},{resource},{campaign},{budget})', dict(id=dataset_id, platform=row['platform'], account=row['account_id'], resource=row['id'], campaign=row['campaign_id'], budget=row['effective_budget_id']))
            for report in reports:
                row = report.normalized()
                conn.execute('INSERT INTO ADVERGENT.AD_REPORTS VALUES ({id},{key},{platform},{account},{resource},{day},{spend},{payload})', dict(id=dataset_id, key=row['key'], platform=row['platform'], account=row['account_id'], resource=row['resource_id'], day=row['reporting_day'], spend=row['spend_paise'], payload=canonical(row)))
            conn.execute('INSERT INTO ADVERGENT.AD_COMPLETE VALUES ({id})', {'id': dataset_id})
            conn.commit()

    def ad_data(self, dataset_id):
        with self.connection() as conn:
            if not conn.execute('SELECT COUNT(*) FROM ADVERGENT.AD_COMPLETE WHERE DATASET_ID={id}', {'id': dataset_id}).fetchval():
                raise AnalyticsUnavailable('Incomplete ad dataset')
            entities = {'accounts': [], 'resources': [], 'budgets': []}
            for kind, payload in conn.execute('SELECT ENTITY_KIND,PAYLOAD FROM ADVERGENT.AD_ENTITIES WHERE DATASET_ID={id} ORDER BY ENTITY_KEY', {'id': dataset_id}).fetchall():
                entities[kind].append(json.loads(payload))
            reports = []
            for row in conn.execute('SELECT PAYLOAD,REPORT_KEY,PLATFORM,ACCOUNT_ID,RESOURCE_ID,REPORTING_DAY,SPEND_PAISE FROM ADVERGENT.AD_REPORTS WHERE DATASET_ID={id} ORDER BY REPORT_KEY', {'id': dataset_id}).fetchall():
                report = json.loads(row[0])
                if list(row[1:]) != [report[k] for k in ('key', 'platform', 'account_id', 'resource_id', 'reporting_day', 'spend_paise')]:
                    raise AnalyticsUnavailable('Ad report core/source mismatch')
                reports.append(report)
            core = conn.execute('SELECT PLATFORM,ACCOUNT_ID,RESOURCE_ID,CAMPAIGN_ID,BUDGET_ID FROM ADVERGENT.AD_RESOURCES WHERE DATASET_ID={id}', {'id': dataset_id}).fetchall()
            expected = {(r['platform'], r['account_id'], r['id'], r['campaign_id'], r['effective_budget_id']) for r in entities['resources']}
            if set(core) != expected:
                raise AnalyticsUnavailable('Ad hierarchy core/source mismatch')
            rows = conn.execute('''SELECT p.PLATFORM,p.ACCOUNT_ID,p.REPORTING_DAY,r.CAMPAIGN_ID,r.BUDGET_ID,COUNT(*),SUM(p.SPEND_PAISE)
                FROM ADVERGENT.AD_REPORTS p JOIN ADVERGENT.AD_RESOURCES r
                ON p.DATASET_ID=r.DATASET_ID AND p.PLATFORM=r.PLATFORM AND p.ACCOUNT_ID=r.ACCOUNT_ID AND p.RESOURCE_ID=r.RESOURCE_ID
                WHERE p.DATASET_ID={id} GROUP BY p.PLATFORM,p.ACCOUNT_ID,p.REPORTING_DAY,r.CAMPAIGN_ID,r.BUDGET_ID
                ORDER BY p.REPORTING_DAY,p.PLATFORM,r.CAMPAIGN_ID''', {'id': dataset_id}).fetchall()
            groups = [dict(platform=r[0], account_id=r[1], reporting_day=r[2], campaign_id=r[3], budget_id=r[4], report_count=int(r[5]), spend_paise=int(r[6])) for r in rows]
            total = conn.execute('SELECT COUNT(*),COALESCE(SUM(SPEND_PAISE),0) FROM ADVERGENT.AD_REPORTS WHERE DATASET_ID={id}', {'id': dataset_id}).fetchone()
            if sum(g['report_count'] for g in groups) != int(total[0]) or sum(g['spend_paise'] for g in groups) != int(total[1]):
                raise AnalyticsUnavailable('Ad hierarchy aggregation mismatch')
            return dict(**entities, reports=reports, groups=groups, report_count=int(total[0]), spend_paise=int(total[1]))

    def verify_ads(self, dataset_id, fixture, reports):
        actual = self.ad_data(dataset_id)
        expected = dict(accounts=[a.model_dump() for a in fixture.accounts], resources=hierarchy(fixture), budgets=budget_capabilities(fixture), reports=[r.normalized() for r in reports])
        for kind, rows in expected.items():
            if sorted(map(canonical, rows)) != sorted(map(canonical, actual[kind])):
                raise AnalyticsUnavailable('Ad full read-back mismatch')
        if actual['spend_paise'] != sum(r.paise for r in reports) or actual['report_count'] != len(reports):
            raise AnalyticsUnavailable('Ad spend reconciliation failed')
