import numpy as np

from population_analysis.processors.nwb import NWBSession
from population_analysis.processors.nwb import UnitNormalizer
from population_analysis.processors.nwb import UnitPreferredDirection
from population_analysis.processors.experiments.saccadic_modulation.raw import RawSessionProcessor


def main():
    raw_sess = RawSessionProcessor("output.hdf", "mlati7")
    sess = NWBSession("../scripts", "2023-05-15_mlati7_output", "../graphs", use_normalized_units=False)

    trial_event_idxs = sess.nwb.processing["behavior"]["trial_event_idxs"].data[:]  # trial_event in idxs
    trial_duration_idxs = sess.nwb.processing["behavior"]["trial_durations_idxs"].data[:]  # [trial_start, trial_stop] in idxs
    trial_event_duration_idxs = []
    for ev_idx in range(len(trial_event_idxs)):
        trial_event_duration_idxs.append(
            [trial_duration_idxs[ev_idx][0], trial_event_idxs[ev_idx], trial_duration_idxs[ev_idx][1]]  # start, event, stop
        )

    trial_event_duration_idxs = np.array(trial_event_duration_idxs) + raw_sess._raw_spike_idx_offset  # Add offset for truncated experiment fix

    cluster_unit_labels = sess.nwb.processing["behavior"]["unit-labels"].data[:]
    ufilt = sess.unit_filter_qm().append(
        sess.unit_filter_probe_zeta().append(
            sess.unit_filter_custom(5, .2, 1, 1, .9, .4)
        )
    )
    cluster_unit_labels = cluster_unit_labels[ufilt.idxs()]

    pref_dir = UnitPreferredDirection(sess.units()[ufilt.idxs()], sess.trial_motion_directions()).calculate()

    norm = UnitNormalizer(
        raw_sess._raw_spike_clusters,
        raw_sess._raw_spike_timestamps,
        trial_event_duration_idxs,
        cluster_unit_labels,  # want the cluster specific unit numbers to iterate over
        sess.trial_motion_directions(),
        pref_dir
    ).normalize()
    tw = 2


if __name__ == "__main__":
    main()
