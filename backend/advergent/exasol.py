"""All vendor-specific SQL, transactions and connection options stay here."""
from contextlib import contextmanager, suppress
import pyexasol
from .contracts import AnalyticsUnavailable, GoldenMetric
from .commerce_sql import CommerceSQL
from .ads_sql import AdsSQL
from .attribution_sql import AttributionSQL
from .finance_sql import FinanceSQL
from .inventory_sql import InventorySQL
from .diagnostics_sql import DiagnosticsSQL
from .clearance_sql import ClearanceSQL
from .breakout_sql import BreakoutSQL
from .cohorts_sql import CohortsSQL
from .budget_sql import BudgetSQL


class ExasolAnalytics(CommerceSQL, AdsSQL, AttributionSQL, FinanceSQL, InventorySQL, DiagnosticsSQL, ClearanceSQL, BreakoutSQL, CohortsSQL, BudgetSQL):
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def connection(self):
        conn = None
        try:
            if 'nocertcheck' in self.settings.exasol_dsn.lower():
                raise ValueError('Certificate verification cannot be disabled')
            conn = pyexasol.connect(
                dsn=self.settings.exasol_dsn, user=self.settings.exasol_user,
                password=self.settings.exasol_password, encryption=True,
                connection_timeout=5,
                socket_timeout=15, query_timeout=15, autocommit=False,
            )
            yield conn
        except Exception:
            # Never expose driver errors: they may contain DSNs or credentials.
            raise AnalyticsUnavailable('Exasol operation failed') from None
        finally:
            if conn:
                with suppress(Exception):
                    conn.close()

    def probe(self):
        with self.connection() as conn:
            if conn.execute('SELECT 1').fetchval() != 1:
                raise AnalyticsUnavailable('Exasol probe returned an unexpected value')

    def migrate(self):
        with self.connection() as conn:
            conn.execute('CREATE SCHEMA IF NOT EXISTS ADVERGENT')
            conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.FOUNDATION_LINES (DATASET_ID VARCHAR(36), LINE_ID VARCHAR(80), NET_SALES DECIMAL(18,0), PRODUCT_COST DECIMAL(18,0), VARIABLE_COST DECIMAL(18,0), PRIMARY KEY (DATASET_ID, LINE_ID) ENABLE)')
            conn.execute('CREATE TABLE IF NOT EXISTS ADVERGENT.FOUNDATION_SPEND (DATASET_ID VARCHAR(36), SPEND_ID VARCHAR(80), AMOUNT DECIMAL(18,0), PRIMARY KEY (DATASET_ID, SPEND_ID) ENABLE)')
            self.migrate_commerce(conn)
            self.migrate_ads(conn)
            self.migrate_attribution(conn)
            self.migrate_finance(conn)
            self.migrate_inventory(conn)
            self.migrate_diagnostics(conn)
            self.migrate_breakout(conn)
            conn.commit()

    def load(self, dataset_id: str, fixture: dict):
        with self.connection() as conn:
            # Dataset identifiers are UUIDs generated internally, still bound safely.
            existing = conn.execute('SELECT COUNT(*) FROM ADVERGENT.FOUNDATION_LINES WHERE DATASET_ID={id}', {'id': dataset_id}).fetchval()
            if int(existing):
                return
            for line in fixture['lines']:
                conn.execute('INSERT INTO ADVERGENT.FOUNDATION_LINES VALUES ({dataset}, {id}, {sales}, {cost}, {variable})', dict(dataset=dataset_id, id=line['id'], sales=line['net_sales_paise'], cost=line['product_cost_paise'], variable=line['variable_cost_paise']))
            for spend in fixture['spend']:
                conn.execute('INSERT INTO ADVERGENT.FOUNDATION_SPEND VALUES ({dataset}, {id}, {amount})', dict(dataset=dataset_id, id=spend['id'], amount=spend['spend_paise']))
            conn.commit()

    def metric(self, dataset_id: str) -> GoldenMetric:
        with self.connection() as conn:
            row = conn.execute('''WITH totals AS (
                SELECT COUNT(*) AS LINE_COUNT, COALESCE(SUM(NET_SALES),0) AS SALES,
                COALESCE(SUM(PRODUCT_COST),0) AS COST, COALESCE(SUM(VARIABLE_COST),0) AS VARIABLE_TOTAL,
                (SELECT COALESCE(SUM(AMOUNT),0) FROM ADVERGENT.FOUNDATION_SPEND WHERE DATASET_ID={id}) AS SPEND
                FROM ADVERGENT.FOUNDATION_LINES WHERE DATASET_ID={id})
                SELECT LINE_COUNT, SALES, COST, VARIABLE_TOTAL, SPEND,
                SALES-COST-VARIABLE_TOTAL, SALES-COST-VARIABLE_TOTAL-SPEND FROM totals''', {'id': dataset_id}).fetchone()
            values = map(int, row)
            return GoldenMetric(**dict(zip(GoldenMetric.model_fields, values, strict=True)))
