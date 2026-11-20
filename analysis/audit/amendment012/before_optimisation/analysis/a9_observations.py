"""Date-only observable records, separate from fitting and latent simulation."""
import numpy as np
import pandas as pd


def observable_spells(completed, active, epoch, horizon):
    """Use the same ceil-to-date observation as A16, never latent event ages."""
    records = []
    for item in [*completed, *active]:
        att = epoch + pd.Timedelta(days=int(np.ceil(item['start'])))
        removed = item.get('risk', 0) != 0
        end = item['end'] if removed else item.get('censor_end', horizon)
        rem = epoch + pd.Timedelta(days=int(np.ceil(end)))
        records.append({'Part #': item['pn'], 'Serial #': item['unit'] + '-' + str(item['renewal']),
                        'Aircraft #': item['aircraft'], 'att': att, 'rem': rem,
                        'event': int(item.get('risk') == 1),
                        'preventive': bool(item.get('risk') == 3),
                        'source': 'in_window_removed' if removed else 'in_window_censored'})
    columns = ['Part #', 'Serial #', 'Aircraft #', 'att', 'rem', 'event', 'preventive', 'source']
    frame = pd.DataFrame(records, columns=columns)
    frame['spell_id'] = ['A9-' + str(i).zfill(8) for i in range(len(frame))]
    return frame
