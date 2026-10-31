"""Verified budget/day and dated outcome joins; vendor SQL stays in the adapter."""
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .attribution import Mapping, resolve_mapping
from .commerce import canonical
from .budget import allocate, observed_outcome
from .contracts import AnalyticsUnavailable

INDIA = ZoneInfo('Asia/Kolkata')


class BudgetSQL:
    def budget_data(self, pins, at, terms, publications, operational):
        ads = self.ad_data(pins['ads'])
        finance = self.finance_data(pins['finance'], tuple(pins[k] for k in ('commerce','ads','attribution')))
        inventory = self.inventory_data(pins['inventory'], at=at, expected_finance=pins['finance'])
        diagnostics = self.diagnostics_data(pins['diagnostics'], at=at, expected_inventory=pins['inventory'])
        attr = self.attribution_data(pins['attribution'])
        mappings = [Mapping.model_validate_json(canonical(m)) for m in attr['mapping_evidence']]
        cutoff = min(at, datetime.fromisoformat(publications['finance']['configuration']['as_of']),
                     *(publications[k]['observed_at'] for k in ('finance','commerce','ads','attribution')))
        cohorts = self.cohort_data(pins, cutoff, publications['finance']['configuration']['period_start'])
        context = dict(history_complete=False, cutoff=cohorts.cutoff,
            basis='Separate descriptive cohort context; never a response multiplier or calibrated LTV',
            windows=[dict(days=days, mature=sum(w.mature for c in cohorts.customers for w in c.windows if w.days==days),
                immature=sum(not w.mature for c in cohorts.customers for w in c.windows if w.days==days),
                missing=sum(w.missing_events>0 for c in cohorts.customers for w in c.windows if w.days==days)) for days in (60,90)])
        # Distinct budget/day spend and unique order/campaign relationships are real SQL joins.
        with self.connection() as c:
            spends = c.execute('''SELECT p.PLATFORM,p.ACCOUNT_ID,r.BUDGET_ID,p.REPORTING_DAY,SUM(p.SPEND_PAISE)
                FROM ADVERGENT.AD_REPORTS p JOIN ADVERGENT.AD_RESOURCES r ON r.DATASET_ID=p.DATASET_ID
                AND r.PLATFORM=p.PLATFORM AND r.ACCOUNT_ID=p.ACCOUNT_ID AND r.RESOURCE_ID=p.RESOURCE_ID
                WHERE p.DATASET_ID={aid} GROUP BY p.PLATFORM,p.ACCOUNT_ID,r.BUDGET_ID,p.REPORTING_DAY''',dict(aid=pins['ads'])).fetchall()
            orders = c.execute('''SELECT o.SOURCE_ID,o.PLACED_AT,a.PLATFORM,a.ACCOUNT_ID,a.CAMPAIGN_ID
                FROM ADVERGENT.COMMERCE_ORDERS o JOIN ADVERGENT.ATTR_ORDERS a ON a.DATASET_ID={tid}
                AND a.ORDER_ID=o.SOURCE_ID WHERE o.DATASET_ID={cid}''',dict(tid=pins['attribution'],cid=pins['commerce'])).fetchall()
            events = c.execute('''SELECT EVENT_ID,NET_SALES_PAISE-NET_PRODUCT_COST_PAISE-VARIABLE_PAISE
                FROM ADVERGENT.FIN_EVENTS WHERE DATASET_ID={fid}''',dict(fid=pins['finance'])).fetchall()
        if sum(int(r[4]) for r in spends) != ads['spend_paise']: raise AnalyticsUnavailable('Budget spend mismatch')
        amounts = {eid: int(value) if value is not None else None for eid,value in events}
        order_lines = defaultdict(list)
        for line in finance['lines']: order_lines[line['order_id']].append(line)
        products = {p['product_id']: p for p in inventory['products']}
        inputs = []
        resources = ads['resources']
        states = publications['inventory']['configuration']['resource_states']
        for b in ads['budgets']:
            identity = (b['platform'],b['account_id'])
            members = [r for r in resources if (r['platform'],r['account_id'])==identity and r['id'] in b['member_ids']]
            scope = [resolve_mapping(mappings, (*identity,r['id']), at) for r in members]
            pids = sorted({p for m in scope for p in m['products']})
            blockers = []
            if not b['budget_control_supported']: blockers.append('budget control unsupported')
            if len(members)!=len(b['member_ids']) or not scope or any(m['status']!='resolved' for m in scope): blockers.append('exact reviewed mapping unavailable for every member')
            related = {r['id']:r for r in resources if (r['platform'],r['account_id'],r['effective_budget_id'])==(*identity,b['id'])}
            for r in list(related.values()):
                while r['parent_id']:
                    r = next(x for x in resources if (x['platform'],x['account_id'],x['id'])==(*identity,r['parent_id']))
                    related[r['id']] = r
            if any(r['status']!='active' for r in related.values()): blockers.append('paused budget member or hierarchy resource')
            for r in related.values():
                actual = operational['resources'].get(canonical([*identity,'status',r['id']]))
                if actual and actual['value']!='active': blockers.append('paused durable simulator resource')
            for pid in pids:
                p = products.get(pid)
                if not p or not p['fresh'] or p['risk']!='clear': blockers.append('inventory '+pid+': '+(p['risk'] if p else 'missing'))
            for member in members:
                ss = [s for s in states if (s['platform'],s['account_id'],s['resource_id'])==(*identity,member['id'])]
                if not ss or any(s['status']!='active' or s['blockers'] or not 0 <= (at-datetime.fromisoformat(s['observed_at'].replace('Z','+00:00'))).total_seconds() <= 900 for s in ss):
                    blockers.append('missing, blocked, paused or stale member state')
                ds = [r for r in diagnostics['recommendations'] if (r['platform'],r['account_id'],r['resource_id'])==(*identity,member['id'])]
                if not ds or any(r['blockers'] for r in ds): blockers.append('destination or catalog blockers')
            for k in ('ads','inventory','diagnostics'):
                if not 0 <= (at-publications[k]['observed_at']).total_seconds() <= 900: blockers.append('stale or future '+k+' source')
            campaigns = {r['campaign_id'] for r in members}
            ambiguous = any(r['effective_budget_id'] not in (None,b['id']) for r in resources
                            if (r['platform'],r['account_id'])==identity and r['campaign_id'] in campaigns)
            if ambiguous: blockers.append('campaign contribution cannot resolve multiple budgets')
            leaves = [r for r in resources if (r['platform'],r['account_id'],r['effective_budget_id'])==(*identity,b['id'])
                and r['kind']==('ad' if r['campaign_type'] in ('meta','search') else 'asset_group' if r['campaign_type']=='pmax' else 'ad_group')]
            observations = []
            for platform, account, bid, day, spend in spends:
                if (platform,account,bid)!=(*identity,b['id']): continue
                start = datetime.fromisoformat(day).replace(tzinfo=INDIA)
                end = start+timedelta(days=1)
                outcome_end = end+timedelta(days=60)
                grains = {(r['resource_id'],datetime.fromisoformat(r['interval_start'])) for r in ads['reports']
                          if (r['platform'],r['account_id'])==identity and r['reporting_day']==day}
                expected = {(r['id'],start+timedelta(minutes=30*i)) for r in leaves for i in range(48)}
                complete = bool(expected) and expected <= grains and end <= cutoff
                selected = [(oid,datetime.fromisoformat(placed)) for oid,placed,p,a,campaign in orders
                    if (p,a)==identity and campaign in campaigns and start <= datetime.fromisoformat(placed) < end]
                values = []
                for oid, placed in selected:
                    order_events = []
                    for line in order_lines[oid]:
                        for event in line['events']:
                            correction = line['evidence']['correction']
                            correction_at = correction['effective_at'] if correction and (event['id'].endswith(':delivery') or ':recovery:' in event['id']) else None
                            order_events.append(dict(at=event['occurred_at'],contribution_paise=amounts[event['id']],correction_at=correction_at))
                    values.append(observed_outcome(order_events,placed,cutoff))
                observations.append(dict(day=day,spend_paise=int(spend),complete=complete,
                    mature=outcome_end<=cutoff,orders=len(selected),
                    contribution_paise=None if outcome_end>cutoff or any(v is None for v in values) else sum(values),
                    estimated_lines=sum(l['cost_status']=='estimated' or l['expense_status']=='estimated' for oid,_ in selected for l in order_lines[oid])))
            vids = {v['variant_id'] for pid in pids if pid in products for v in products[pid]['variants']}
            historical = [l['expected_before_ads_paise'] for l in finance['lines'] if l['evidence']['original_line']['variant_id'] in vids]
            if not historical or any(v is None for v in historical): blockers.append('missing historical product costs or history')
            key = canonical([*identity,'budget',b['id']])
            state = operational['resources'].get(key)
            current = state['value'] if state else b['daily_paise']
            if type(current) is not int or current < 0: raise AnalyticsUnavailable('Invalid budget state')
            inputs.append(dict(key=key,platform=identity[0],account_id=identity[1],budget_id=b['id'],shared=b['shared'],
                members=b['member_ids'],products=pids,current_paise=current,state=state,blockers=blockers,observations=observations,
                historical_contribution_paise=sum(historical) if historical and all(v is not None for v in historical) else None))
        global_blockers = []
        if operational['stopped']: global_blockers.append('kill switch enabled')
        if operational['unresolved']: global_blockers.append('unresolved execution intents')
        data = allocate(inputs, terms, context, global_blockers)
        # Only future boundaries matter: already stale resources are frozen above.
        limits = [publications[k]['observed_at']+timedelta(seconds=900) for k in ('ads','inventory','diagnostics')]
        limits += [datetime.fromisoformat(v['stock_observed_at'])+timedelta(seconds=min(900,inventory['assumptions']['freshness_seconds'])) for p in products.values() for v in p['variants']]
        limits += [t for m in mappings for t in (m.valid_from,m.valid_to)]
        limits += [datetime.fromisoformat(s['observed_at'].replace('Z','+00:00'))+timedelta(seconds=900) for s in states]
        for r in diagnostics['recommendations']:
            for d in r['destinations']:
                for e in d['evidence']:
                    limits.append(datetime.fromisoformat(e['observed_at'].replace('Z','+00:00'))+timedelta(seconds=min(900,diagnostics['assumptions']['freshness_seconds'])))
                    if e.get('offer_expires_at'): limits.append(datetime.fromisoformat(e['offer_expires_at'].replace('Z','+00:00')))
        future = [t for t in limits if t >= at]
        data.valid_until = min(future).isoformat() if future else None
        return data
