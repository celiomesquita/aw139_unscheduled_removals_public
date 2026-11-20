"""Fresh evaluation units; no auxiliary state can be passed to this factory."""
from a9_events import UnitState
from a9_warmup import LEVELS, PHASES, parameters


def initial_units(truth, channels, level, phase, replicate, evaluation_end, cell=None):
    beta, eta = parameters(truth, level)
    entries = []
    for channel in channels:
        start = channel['start']
        end = min(channel['end'], evaluation_end)
        if start >= end:
            continue
        p = channel['pn_index']
        ac = int(channel['aircraft'].split('-')[1])
        if phase != 'verification' and cell is None:
            raise ValueError('Pilot/main evaluation seeds require an explicit cell')
        key = (9, PHASES[phase], *((cell,) if cell is not None else ()),
               LEVELS[level], replicate, p, ac, channel['channel'])
        state = UnitState(key, float(beta[p]), float(truth.iloc[p].nu),
                          age=0., renewal=0, time=float(start), birth=float(start))
        entries.append(dict(unit=f'EVAL-{p}-{ac}-{channel["channel"]}',
            cohort='evaluation', pn=channel['pn'], aircraft=channel['aircraft'],
            channel=channel['channel'], pn_index=p, start=start, end=end,
            eta=float(eta[p]), state=state,
            intervals=[(max(a, start), min(b, end)) for a, b in channel['intervals']
                       if max(a, start) < min(b, end)]))
    return entries
