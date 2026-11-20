"""Freeze the author-authorised MH approximation, before policy simulations."""
import json

import numpy as np
import pandas as pd

from a16_generator import ROOT, sha
from round5_execution import atomic_json, check_historical

PROXIES = ('3G6230A00833', '3G6230A00932', '3G6430A00335')
OUT = ROOT / 'data/derived/a9/resources'


def select_resources(domain, summary, parameters):
    records = []
    for pn in sorted(domain.pn):
        proxy = pn in PROXIES
        cohort = 'all_equal_share' if proxy else 'single_document'
        group = summary[(summary.pn == pn) & (summary.cohort == cohort)]
        row = group[group.aggregation == 'row_sum']
        alternative = group[group.aggregation == 'task_max']
        if len(row) != 1 or len(alternative) != 1:
            raise ValueError('Missing or duplicated resource source: ' + pn)
        row, alternative = row.iloc[0], alternative.iloc[0]
        values = [float(row['median']), float(row.q1), float(row.q3), float(alternative['median'])]
        if (int(row.n_observed) <= 0 or not np.isfinite(values).all() or min(values) <= 0 or
                not values[1] <= values[0] <= values[2]):
            raise ValueError('Unavailable or invalid resource coefficient: ' + pn)
        if (int(row.documents), int(row.n_observed)) != (
                int(alternative.documents), int(alternative.n_observed)):
            raise ValueError('Resource aggregation populations differ: ' + pn)
        if proxy:
            original = summary[(summary.pn == pn) &
                               (summary.cohort == 'single_document') &
                               (summary.aggregation == 'row_sum')]
            if len(original) != 1 or int(original.iloc[0].n_observed) != 0:
                raise ValueError('Proxy exception no longer matches the amendment: ' + pn)
        else:
            configured = parameters[parameters.parametro == 'mh_row_sum_' + pn]
            if len(configured) != 1 or float(configured.iloc[0].valor_central) != values[0]:
                raise ValueError('Historical config disagrees with resource source: ' + pn)
        records.append(dict(pn=pn, cohort=cohort, proxy_authorised=proxy,
                            documents=int(row.documents), n_observed=int(row.n_observed),
                            principal_mh=values[0], lower_mh=values[1], upper_mh=values[2],
                            task_max_mh=values[3]))
    if set(domain.pn).intersection(PROXIES) != set(PROXIES):
        raise ValueError('The three preregistered proxy exceptions must be present')
    return pd.DataFrame(records)


def run():
    frozen = json.loads((ROOT / 'data/derived/a16/flow17/configuration.json').read_text())
    check_historical(frozen['historical'])
    paths = ['analysis/emenda_A16_A9_008.md', 'analysis/a9_resources.py',
             'config/a4_scale_map.csv', 'config/cost_parameters.csv',
             'data/derived/single_removal_mh_summary.csv']
    sources = {p: sha(ROOT / p) for p in paths}
    result = select_resources(pd.read_csv(ROOT / paths[2]), pd.read_csv(ROOT / paths[4]),
                              pd.read_csv(ROOT / paths[3]))
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'preventive_mh.csv'
    content = result.to_csv(index=False)
    if target.exists() and target.read_bytes() != content.encode('utf-8'):
        raise RuntimeError('Frozen A9 resource table differs; preserve and amend')
    target.write_text(content, encoding='utf-8', newline='')
    manifest = dict(sources=sources, resource_sha256=sha(target), pn_count=len(result),
                    authorised_proxy_count=int(result.proxy_authorised.sum()),
                    historical_artifacts_unchanged=True, policy_outcomes_generated=False)
    destination = OUT / 'manifest.json'
    if destination.exists() and json.loads(destination.read_text()) != manifest:
        raise RuntimeError('Frozen A9 resource manifest differs')
    atomic_json(destination, manifest)
    check_historical(frozen['historical'])
    print('A9 resource inputs frozen: 11 P/N, 3 authorised proxies, 4 MH vectors')
    return manifest


if __name__ == '__main__':
    run()
