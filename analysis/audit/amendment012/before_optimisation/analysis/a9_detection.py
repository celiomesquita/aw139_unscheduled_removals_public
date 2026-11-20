"""Observable-only drift alarms and a declared empirical-Bayes Wald approximation."""
import numpy as np

from a4_models import likelihood


def log_eta_intervals(records, effects, families, hyper):
    """Joint mean/effect information, conditional on the fitted variance components."""
    pns = sorted(effects)
    if not pns:
        return {}
    theta = np.array([[np.log(effects[p]['beta']), np.log(effects[p]['eta'])] for p in pns])
    times = np.concatenate([records[p]['t'] for p in pns])
    events = np.concatenate([records[p]['d'] for p in pns])
    pid = np.concatenate([np.full(len(records[p]['t']), i) for i, p in enumerate(pns)])
    _, _, blocks = likelihood(theta, times, events, pid, len(pns))
    labels = ['mean_beta'] + ['mean_eta_' + f for f in sorted(set(families[p] for p in pns))]
    random = {}
    for p in pns:
        for k, std in enumerate((hyper['tau_beta'], hyper['tau_eta_' + families[p]])):
            if std > 0:
                random[p, k] = len(labels)
                labels.append(f'effect_{p}_{k}')
    information = np.zeros((len(labels), len(labels)))
    designs = {}
    for i, p in enumerate(pns):
        design = np.zeros((2, len(labels)))
        for k, std in enumerate((hyper['tau_beta'], hyper['tau_eta_' + families[p]])):
            mean = 0 if k == 0 else labels.index('mean_eta_' + families[p])
            index = random.get((p, k), mean)
            design[k, index] = 1
            if std > 0:
                contrast = np.zeros(len(labels))
                contrast[index], contrast[mean] = 1., -1.
                information += np.outer(contrast, contrast) / std ** 2
        information += design.T @ blocks[i] @ design
        designs[p] = design
    values = np.linalg.eigvalsh(information)
    if not np.isfinite(values).all() or values.min() <= np.finfo(float).eps * max(1., values.max()) * len(labels):
        return {p: dict(log_eta_se=None, log_eta_lo=None, log_eta_hi=None,
                        wald_reason='nonpositive_joint_information') for p in pns}
    covariance = np.linalg.inv(information)
    result = {}
    for i, p in enumerate(pns):
        variance = float(designs[p][1] @ covariance @ designs[p][1])
        se = np.sqrt(variance)
        result[p] = dict(log_eta_se=float(se), log_eta_lo=float(theta[i, 1] - 1.95996398454 * se),
                         log_eta_hi=float(theta[i, 1] + 1.95996398454 * se),
                         wald_reason='joint_means_effects_plugin_variances')
    return result


class DriftDetector:
    """No scenario, imposed-change date, latent state or true parameter is accepted."""
    def __init__(self, initial_parameters, rotor_pns, initial_utilisation):
        self.initial = initial_parameters
        self.rotor = tuple(sorted(rotor_pns))
        self.initial_utilisation = initial_utilisation.copy()
        self.parameter_first, self.exposure_first, self.streak = {}, {}, {}
        self.rows = []

    def observe(self, month, parameters, utilisation):
        for pn in self.rotor:
            initial = self.initial[pn].get('log_eta_lo')
            current = parameters[pn].get('log_eta_hi')
            assessable = initial is not None and current is not None
            alarm = bool(assessable and current < initial)
            if alarm:
                self.parameter_first.setdefault(pn, month)
            self.rows.append(dict(month=month, kind='parameter', key=pn,
                                  assessable=assessable, alarm=alarm))
        for aircraft in sorted(self.initial_utilisation):
            initial = self.initial_utilisation[aircraft]
            current = utilisation.get(aircraft)
            assessable = initial is not None and initial > 0 and current is not None
            elevated = bool(assessable and current >= 1.15 * initial)
            self.streak[aircraft] = self.streak.get(aircraft, 0) + 1 if elevated else 0
            alarm = self.streak[aircraft] >= 2
            if alarm:
                self.exposure_first.setdefault(aircraft, month)
            self.rows.append(dict(month=month, kind='utilisation', key=aircraft,
                                  assessable=assessable, alarm=alarm))
