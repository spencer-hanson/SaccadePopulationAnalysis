import numpy as np

from population_analysis.consts import SPIKE_BIN_MS
from population_analysis.processors.experiments.saccadic_modulation import ModulationTrialGroup


class RpPeriCalculator(object):
    def __init__(self, firing_rates, saccade_idxs, mixed_idxs, trialgroup):
        self.fr = firing_rates  # (units, trials, t*3)  [-t, 0, t*2]
        assert firing_rates.shape[-1] % 3 == 0
        self.window_size = int(firing_rates.shape[-1]/3)
        self.sac_idxs = saccade_idxs
        self.mix_idxs = mixed_idxs
        self.trialgroup = trialgroup

    def calculate_static(self):
        # Index is 35:35+35 because the window is |--A35--|--B35--|--C35--|
        # where A is 700ms + 200ms before the probe, B is the 700ms around the probe, centered at 200ms in
        # and C is 700ms + 500ms after the probe

        saccade_unit_trial_waveforms = self.fr[:, self.sac_idxs][:, :, 35:35+35]  # (units, trials, t))

        # average is now (units, t)
        saccade_unit_average_waveforms = np.average(saccade_unit_trial_waveforms, axis=1)  # Average over saccade trials for each unit
        # Get mixed waveform unit-trials
        mixed_unit_trial_waveforms = self.fr[:, self.mix_idxs][:, :, 35:35+35]  # (units, trials, t)

        # Reshape saccade_unit_average_waveforms to (units, 1, t) and broadcast against (units, trials, t)
        # to subtract saccade avg from all units in all trials
        saccade_unit_average_waveforms = saccade_unit_average_waveforms[:, None]
        mixed_peri_waveforms = mixed_unit_trial_waveforms - saccade_unit_average_waveforms

        return mixed_peri_waveforms

    # def calculate_timeshifted_rp_peri(self):
    def calculate(self):
        saccade_unit_trial_waveforms = self.fr[:, self.sac_idxs]  # (units, trials, t))

        # average is now units x t
        saccade_unit_average_waveforms = np.average(saccade_unit_trial_waveforms, axis=1)  # Average over saccade trials for each unit
        all_mixed_peri_waveforms = []  # Will end up being (trials, units, t) will swapaxes to (units, trials, t)

        for tr_idx, tr in enumerate(self.trialgroup.get_trials_by_type("mixed")):
            offset = tr.events["saccade_time"] - tr.events["probe_time"]  # Will be in seconds
            offset = int(round(offset, 3)*1000)  # Round to .000 and turn into ms
            offset = int(round(offset / SPIKE_BIN_MS, 0))  # Figure out how many indexes away the relative saccade is
            offset = int(np.clip(offset, -35, 35))
            offset = (-1*offset)
            sac_wv = saccade_unit_average_waveforms[:, 35 + offset:offset + 35 + 35]  # 35 long waveform snippet
            mixed_peri_wavs = []
            for unit_num in range(self.fr.shape[0]):
                unit_trial_fr = self.fr[unit_num, self.mix_idxs[tr_idx], 35:35 + 35]  # actually is 0-35 but offset for neg
                rpperi = unit_trial_fr - sac_wv[unit_num, :]  # Subtract off each RpPeri for each trial specific to the offset of the saccade from the probe
                mixed_peri_wavs.append(rpperi)

            all_mixed_peri_waveforms.append(mixed_peri_wavs)
        all_mixed_peri_waveforms = np.array(all_mixed_peri_waveforms).swapaxes(0, 1)  # Swap units trials so its (units, trials, t)

        return all_mixed_peri_waveforms
