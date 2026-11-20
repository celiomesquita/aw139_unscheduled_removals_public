"""Stationary renewal generator and the first preregistered T12 gate."""
import argparse
import gzip
import hashlib
import io
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.special import gamma
from scipy.stats import wasserstein_distance

from a15_stability import protected_hashes
from a5_models import Exposure, START, END

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data/derived/a16/generator'
SEED = 20261112
LEVELS = ('calibrated', 'null', 'amplified')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def committed_protocol():
    path = ROOT / 'analysis/preregistro_A16_A9.md'
    revision = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--',
        path.relative_to(ROOT).as_posix()], cwd=ROOT, text=True).strip()
    original = subprocess.check_output(['git', 'show', revision + ':' +
        path.relative_to(ROOT).as_posix()], cwd=ROOT)
    if original.replace(b'\r\n', b'\n') != path.read_bytes().replace(b'\r\n', b'\n'):
        raise ValueError('A16/A9 protocol differs from its committed version')
    return revision, sha(path)


def preserve_mean(beta, eta, target_beta):
    return eta * gamma(1 + 1 / beta) / gamma(1 + 1 / target_beta)


def colour_channels(spells):
    """Assign the lowest free channel; dates and stable row index break ties."""
    records = []
    for (aircraft, pn), group in spells.groupby(['Aircraft #', 'Part #'], sort=True):
        ends = []
        for row in group.sort_values(['att', 'rem', 'real_id'], kind='stable').itertuples(index=False):
            # Column names with punctuation are deliberately not used for identity.
            att, rem, real_id = row.att, row.rem, row.real_id
            free = next((i for i, end in enumerate(ends) if end <= att), len(ends))
            if free == len(ends):
                ends.append(rem)
            else:
                ends[free] = rem
            records.append(dict(aircraft=aircraft, pn=pn, channel=free,
                                real_id=real_id, att=att, rem=rem))
    return pd.DataFrame(records)


def union_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if end < start:
            raise ValueError('Negative observation interval')
        if end == start:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def inverse_clock(curve, target):
    """Invert a piecewise linear, nondecreasing daily clock."""
    j = int(np.searchsorted(curve, target, side='left'))
    if j >= len(curve):
        return np.inf
    if j == 0:
        return 0.
    width = curve[j] - curve[j - 1]
    if width <= 0:
        raise ValueError('Invalid clock inversion on a flat segment')
    return j - 1 + float((target - curve[j - 1]) / width)


def clock_value(curve, t):
    left = min(int(np.floor(t)), len(curve) - 1)
    if left == len(curve) - 1:
        return float(curve[-1])
    return float(curve[left] + (t - left) * (curve[left + 1] - curve[left]))


def renewal_path(curve, start, end, beta, eta, nu, unscheduled_rng, competing_rng):
    """Yield latent spells; risk 1=unscheduled, 2=competing, 0=final censor."""
    if beta <= 0 or eta <= 0 or nu < 0 or not 0 <= start <= end <= len(curve) - 1:
        raise ValueError('Invalid generator parameters')
    now = float(start)
    while now < end:
        base = clock_value(curve, now)
        life = eta * unscheduled_rng.exponential() ** (1 / beta)
        failure = inverse_clock(curve, base + life)
        competing = now + competing_rng.exponential() / nu if nu > 0 else np.inf
        # Competing event has precedence at a numerical tie.
        risk = 2 if competing <= failure else 1
        finish = min(failure, competing, end)
        if finish <= now:
            raise FloatingPointError('A renewal did not advance time')
        if finish >= end:
            finish, risk = float(end), 0
        yield now, finish, risk, clock_value(curve, finish) - base
        now = finish


def load_design():
    domain = pd.read_csv(ROOT / 'config/a4_scale_map.csv').sort_values('pn').reset_index(drop=True)
    effects = pd.read_csv(ROOT / 'data/derived/a4/effects.csv', float_precision='round_trip')
    effects = effects[(effects.variant == 'principal') & (effects.origin == '2025-12-01') &
                      (effects.model == 'w')].set_index('pn')
    fits = pd.read_csv(ROOT / 'data/derived/a4/individual_reference_fits.csv', float_precision='round_trip')
    fits = fits[(fits.variant == 'principal') & (fits.origin == '2025-12-01') & (fits.model == 'w')]
    truth = []
    for row in domain.itertuples():
        effect = effects.loc[row.pn]
        reference = fits[(fits.pn == row.pn) & (fits.scale == row.scale)]
        if len(reference) != 1 or not effect.converged:
            raise ValueError('Unidentified truth or competing rate: ' + row.pn)
        nuisance = reference.iloc[0]
        truth.append(dict(pn=row.pn, family=row.family, scale=row.scale,
            beta=float(effect.beta), eta=float(effect.eta), nu=float(nuisance.competing_rate),
            competing_fallback=bool(nuisance.competing_pooled_fallback)))
    truth = pd.DataFrame(truth)
    exposure = Exposure(pd.read_csv(ROOT / 'data/anonymised/hours_flown.csv'))
    clock = exposure.clocks(END + pd.Timedelta(days=1))
    days = pd.date_range(START, END)
    daily = pd.DataFrame({'date': np.repeat(days.to_numpy(), len(exposure.aircraft)),
                          'aircraft': exposure.aircraft * len(days)})
    for name in ('Hours', 'cycles', 'missing_cycles', 'missing_hours', 'known_hours'):
        daily[name] = clock['daily'][name].loc[days].to_numpy().ravel()
    curves = {ac: clock['cum']['Hours'].loc[days, ac].to_numpy(float) for ac in exposure.aircraft}
    spells = pd.read_csv(ROOT / 'data/derived/spells.csv', parse_dates=['att', 'rem'])
    spells['real_id'] = np.arange(len(spells))
    spells = spells[spells.source.isin(['in_window_removed', 'in_window_censored']) &
                    spells['Part #'].isin(domain.pn)].copy()
    if spells['Aircraft #'].isna().any() or (spells.rem > END).any() or (spells.att < START).any():
        raise ValueError('Invalid primary-cohort bounds')
    markers = colour_channels(spells)
    channels, observed = [], []
    real_ages = {}
    for pn_index, row in enumerate(truth.itertuples()):
        group = spells[spells['Part #'].eq(row.pn)]
        ages = exposure.ages(group, group.rem, clock, row.scale)
        valid = ages > 0
        real_ages[row.pn] = ages[valid & group.event.eq(1).to_numpy()]
        observed.append(dict(pn=row.pn, spells=len(group), positive_spells=int(valid.sum()),
            events=int(group.event.to_numpy()[valid].sum()), exposure=float(ages[valid].sum()),
            zero_age_events=int(group.event.to_numpy()[~valid].sum()),
            censored=int(group.event.eq(0).sum()), scale=row.scale))
        for (aircraft, channel), g in markers[markers.pn.eq(row.pn)].groupby(['aircraft', 'channel'], sort=True):
            curve = curves[aircraft] if row.scale == 'FH' else np.arange(len(days), dtype=float)
            intervals = union_intervals([((r.att - START).days, (r.rem - START).days)
                                         for r in g.itertuples()])
            if not intervals:
                continue
            denominator = sum(clock_value(curve, end) - clock_value(curve, start)
                              for start, end in intervals)
            channels.append(dict(pn_index=pn_index, pn=row.pn, aircraft=aircraft,
                channel=int(channel), intervals=intervals, start=intervals[0][0],
                end=intervals[-1][1], curve=curve, exposure=denominator, installations=len(g)))
    observed = pd.DataFrame(observed)
    reconstructed = pd.DataFrame(channels).groupby('pn').exposure.sum().reindex(observed.pn).to_numpy()
    np.testing.assert_allclose(reconstructed, observed.exposure, rtol=0, atol=1e-8)
    return truth, observed, real_ages, channels, markers, daily


def event_observed(t, intervals):
    # (installation, removal] matches the cumulative clock used for real ages.
    return any(start < t <= end for start, end in intervals)


def run_validation(replicates=1000):
    if replicates != 1000:
        raise ValueError('Preregistered fleet gate requires exactly 1000 replicates per level')
    revision, prereg_hash = committed_protocol()
    before = protected_hashes()
    before['analysis/preregistro_A16_A9.md'] = prereg_hash
    truth, observed, real_ages, channels, markers, daily = load_design()
    OUT.mkdir(parents=True, exist_ok=True)
    truth.to_csv(OUT / 'truth.csv', index=False)
    observed.to_csv(OUT / 'observed_rates.csv', index=False)
    markers.to_csv(OUT / 'installation_markers.csv', index=False)
    daily.to_csv(OUT / 'daily_clocks.csv', index=False)
    structure = pd.DataFrame([{k: v for k, v in channel.items() if k not in ('curve', 'intervals')}
        | {'intervals': json.dumps(channel['intervals'])} for channel in channels])
    structure.to_csv(OUT / 'channels.csv', index=False)
    rows, summary, distributions, ecdf = [], [], [], []
    started = time.perf_counter()
    truth_rows = list(truth.itertuples())
    # gzip header has fixed mtime so complete replays produce identical artifacts.
    with (OUT / 'latent_spells.csv.gz').open('wb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding='utf-8', newline='') as stream:
                stream.write('level,replicate,pn,aircraft,channel,renewal,start,end,risk,age,observed\n')
                for level_index, level in enumerate(LEVELS):
                    beta = truth.beta.to_numpy().copy()
                    if level == 'null':
                        beta[:] = 1.
                    if level == 'amplified':
                        beta = 1 + 1.5 * (beta - 1)
                    eta = preserve_mean(truth.beta.to_numpy(), truth.eta.to_numpy(), beta)
                    age_samples = [[] for _ in truth_rows]
                    counts = np.zeros((replicates, len(truth)), dtype=int)
                    exits = np.zeros_like(counts)
                    censored = np.zeros_like(counts)
                    for replicate in range(replicates):
                        for channel in channels:
                            p = channel['pn_index']
                            key = [SEED, 16, level_index, replicate, p,
                                   int(channel['aircraft'].split('-')[1]), channel['channel']]
                            rng_u = np.random.default_rng(np.random.SeedSequence(key + [1]))
                            rng_c = np.random.default_rng(np.random.SeedSequence(key + [2]))
                            for renewal, (start, end, risk, age) in enumerate(renewal_path(
                                channel['curve'], channel['start'], channel['end'], beta[p], eta[p],
                                truth_rows[p].nu, rng_u, rng_c)):
                                visible = event_observed(end, channel['intervals'])
                                if visible and risk == 1 and age > 0:
                                    counts[replicate, p] += 1
                                    age_samples[p].append(age)
                                if visible and risk == 2:
                                    exits[replicate, p] += 1
                                if risk == 0:
                                    censored[replicate, p] += 1
                                stream.write(f'{level},{replicate},{channel["pn"]},{channel["aircraft"]},'
                                    f'{channel["channel"]},{renewal},{start:.17g},{end:.17g},{risk},'
                                    f'{age:.17g},{int(visible)}\n')
                        if (replicate + 1) % 100 == 0:
                            print(level, replicate + 1, 'of', replicates, flush=True)
                    for p, parameter in enumerate(truth_rows):
                        real = observed[observed.pn.eq(parameter.pn)].iloc[0]
                        rate = counts[:, p] / real.exposure
                        real_rate = real.events / real.exposure
                        alpha = .05 / len(truth)
                        lo, hi = np.quantile(rate, [alpha / 2, 1 - alpha / 2])
                        summary.append(dict(level=level, pn=parameter.pn, beta=beta[p], eta=eta[p],
                            real_rate=real_rate, simulated_rate=float(rate.mean()), predictive_lo=lo,
                            predictive_hi=hi, simulated_real_ratio=rate.mean() / real_rate,
                            predictive_sd=float(rate.std(ddof=1)), mc_se=float(rate.std(ddof=1) / np.sqrt(replicates)),
                            within_interval=bool(lo <= real_rate <= hi),
                            decision_rule=level == 'calibrated'))
                        rows.extend(dict(level=level, replicate=r, pn=parameter.pn, events=int(counts[r, p]),
                            competing=int(exits[r, p]), censored=int(censored[r, p]), exposure=real.exposure,
                            rate=float(rate[r])) for r in range(replicates))
                        simulated = np.sort(np.asarray(age_samples[p]))
                        real_sample = np.sort(real_ages[parameter.pn])
                        probs = np.linspace(0, 1, 201)
                        for source, sample in (('real', real_sample), ('simulated', simulated)):
                            if not len(sample):
                                raise ValueError('Empty age distribution: ' + parameter.pn)
                            quantiles = np.quantile(sample, probs)
                            ecdf.extend(dict(level=level, pn=parameter.pn, source=source,
                                probability=float(q), age=float(a)) for q, a in zip(probs, quantiles))
                        distributions.append(dict(level=level, pn=parameter.pn,
                            n_real=len(real_sample), n_simulated=len(simulated),
                            real_q10=float(np.quantile(real_sample, .1)), real_q50=float(np.median(real_sample)),
                            real_q90=float(np.quantile(real_sample, .9)),
                            simulated_q10=float(np.quantile(simulated, .1)), simulated_q50=float(np.median(simulated)),
                            simulated_q90=float(np.quantile(simulated, .9)),
                            normalized_wasserstein=float(wasserstein_distance(real_sample, simulated) /
                                np.median(real_sample)) if np.median(real_sample) > 0 else np.nan))
    pd.DataFrame(rows).to_csv(OUT / 'replicate_rates.csv', index=False)
    summary = pd.DataFrame(summary)
    summary.to_csv(OUT / 'rate_validation.csv', index=False)
    pd.DataFrame(distributions).to_csv(OUT / 'age_distributions.csv', index=False)
    pd.DataFrame(ecdf).to_csv(OUT / 'age_quantile_grid.csv', index=False)
    # Full real ECDF, paired with complete simulated ages in latent_spells.csv.gz.
    pd.DataFrame([dict(pn=pn, age=float(age)) for pn, ages in real_ages.items() for age in ages]).to_csv(
        OUT / 'real_event_ages.csv', index=False)
    after = protected_hashes()
    after['analysis/preregistro_A16_A9.md'] = sha(ROOT / 'analysis/preregistro_A16_A9.md')
    if before != after:
        raise RuntimeError('Protected files changed')
    gate = summary[summary.level.eq('calibrated')]
    failed = gate.loc[~gate.within_interval, 'pn'].tolist()
    inputs = ['data/anonymised/hours_flown.csv', 'data/derived/spells.csv',
              'config/a4_scale_map.csv', 'data/derived/a4/effects.csv',
              'data/derived/a4/individual_reference_fits.csv', 'data/derived/stoppages.csv',
              'analysis/a16_generator.py', 'analysis/emenda_A16_A9_001.md']
    manifest = dict(protocol_revision=revision, protected=before, seed=SEED,
        levels=LEVELS, replicates_per_level=replicates, fit_executed=False, pilot_executed=False,
        a9_executed=False, gate_passed=not failed, failed_pn=failed,
        inputs={name: sha(ROOT / name) for name in inputs},
        outputs={p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'manifest.json'},
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    # Timing belongs to a separate operational log, not a deterministic scientific artifact.
    print('Elapsed seconds:', round(time.perf_counter() - started, 2), flush=True)
    print(gate.to_string(index=False), flush=True)
    print('GATE PASSED' if not failed else 'STOP: calibrated generator failed: ' + ', '.join(failed), flush=True)
    return not failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate', action='store_true', required=True)
    parser.parse_args()
    raise SystemExit(0 if run_validation() else 2)
