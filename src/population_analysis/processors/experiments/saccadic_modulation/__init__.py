import os

import numpy as np

from population_analysis.processors.experiments.saccadic_modulation.trials import ModulationTrial, ModulationTrialGroup
import pickle


class SaccadicModulationTrialProcessor(object):
    CACHE_FILENAME = "saccadic-trials.pickle"

    def __init__(self, firing_rate_bins, events_data):
        # events_data should look like this
        # {
        #         "saccade_timestamps": saccade_timestamps,
        #         "saccade_motions": saccade_motions,
        #         "saccade_blocks": saccade_blocks,
        #         "probe_timestamps": probe_timestamps,
        #         "probe_motions": probe_motions,
        #         "probe_blocks": probe_blocks,
        #         "grating_motion_direction": grating_motion_directions,
        #         "grating_windows": grating_windows
        #     }
        self.block_motions = events_data["grating_motion_direction"]
        self.block_windows = events_data["grating_windows"]

        self.firing_rate_bins = firing_rate_bins  # Expects a list of (t + 1,) timestamps for bins for the firing rates
        self.saccade_timings = events_data["saccade_timestamps"]
        self.saccade_motions = events_data["saccade_motions"]
        self.saccade_blocks = events_data["saccade_blocks"]  # blocks into drifting grating
        assert self.saccade_timings.shape[0] == self.saccade_motions.shape[0] == self.saccade_blocks.shape[0]

        self.probe_timings = events_data["probe_timestamps"]
        self.probe_motions = events_data["probe_motions"]
        self.probe_blocks = events_data["probe_blocks"]
        assert self.probe_timings.shape[0] == self.probe_motions.shape[0] == self.probe_blocks.shape[0]

    def _process_timings(self, timings, motions, blocks, label) -> list[ModulationTrial]:
        trs = []
        for idx, timing in enumerate(timings):
            mot = motions[idx]
            block = blocks[idx]

            hist, _ = np.histogram(timing, bins=self.firing_rate_bins)
            where_my_val = np.where(hist)[0]
            if not bool(where_my_val):
                raise ValueError("Not enough recording! TODO fix?")
            else:
                firing_rate_idx = where_my_val[0]  # Index of this event in firing rate idxs
            # TODO? Assuming bins are 20ms and window is (-200ms, 500ms)
            start_idx = firing_rate_idx - 10  # -10idxs = 20ms * -10idxs = -200ms
            end_idx = firing_rate_idx + 25  # 25idx * 20ms = +500ms
            event_idx = firing_rate_idx
            trs.append(ModulationTrial(start_idx, end_idx, event_idx, timing, label, mot, block, {}))
        return trs

    def _demix_trials(self, probe_trials, saccade_trials, add_saccades=False):
        demixed_trials = []

        found_sac = {i: False for i in range(len(saccade_trials))}  # {saccade_trial_idx: True/False} if saccade has been used in mixed
        num_duplicates = 0

        for probe_tr in probe_trials:
            probe_start = probe_tr.start_idx
            probe_end = probe_tr.end_idx
            num_collisions = 0
            mixed_tr = None

            for sac_idx, sac_tr in enumerate(saccade_trials):
                sac_ev = sac_tr.event_idx

                # if abs(sac_ev - probe_tr.event_idx) <= 30: # indexes by bin so x*20ms
                if abs(sac_tr.event_time - probe_tr.event_time) <= .51:
                    num_collisions = num_collisions + 1
                    found_sac[sac_idx] = True
                    mixed_tr = ModulationTrial(
                        probe_start, probe_end, probe_tr.event_idx, probe_tr.event_time, "mixed", probe_tr.motion_direction, probe_tr.block_idx,{
                            "probe_start": probe_start,
                            "probe_event": probe_tr.event_idx,
                            "probe_end": probe_end,
                            "probe_time": probe_tr.event_time,
                            "saccade_start": sac_tr.start_idx,
                            "saccade_event": sac_tr.event_idx,
                            "saccade_end": sac_tr.end_idx,
                            "saccade_time": sac_tr.event_time
                        })
                    if num_collisions >= 1:
                        break

            # end sac trials loop
            if num_collisions == 1:
                demixed_trials.append(mixed_tr)  # Only add if we have one collision
            elif num_collisions == 0:
                demixed_trials.append(probe_tr)  # Only probe, no matches
            else:
                num_duplicates = num_duplicates + 1  # Don't add multiple trial ones

        if add_saccades:
            for idx, sac_was_found in found_sac.items():
                if not sac_was_found:  # If there were no collisions with this saccade, mark it as Rs
                    demixed_trials.append(saccade_trials[idx])

        return demixed_trials

    def _sort_trials(self, trs: list[ModulationTrial]):
        sort = list(sorted(trs, key=lambda x: x.event_time))
        return sort

    def _filter_saccades_by_time(self, saccade_trials: list[ModulationTrial], probe_trials: list[ModulationTrial]):
        sac_probe_latency = 10  # 200ms is the minimum distance between a saccade and probe that can be used as a sacc
        probe_sac_latency = 20  # 400ms min dist backwards from sacc
        # Filter out any saccades that are not within the latencies

        passing_trials = []
        for saccade_trial in saccade_trials:
            sac_passes = True

            for probe_trial in probe_trials:
                diff = saccade_trial.event_idx - probe_trial.event_idx
                if diff < 0: # Saccade is before probe
                    if abs(diff) < sac_probe_latency:  # Saccade is too close to the probe to be included
                        sac_passes = False
                        break
                else:
                    if diff < probe_sac_latency:  # Saccade is after probe
                        sac_passes = False
                        break

            if sac_passes:
                passing_trials.append(saccade_trial)  # Didn't find any probes within the specified range, can add

        return passing_trials

    def calculate(self):
        if os.path.exists(SaccadicModulationTrialProcessor.CACHE_FILENAME):
            print("Precalculated ModulationTrialGroup found, skipping..")
            with open(SaccadicModulationTrialProcessor.CACHE_FILENAME, "rb") as f:
                return pickle.load(f)

        # Will return [{"start": start_idx, "event": event_idx, "stop": stop_idx}, ..]
        # The indexes are the value of the bin that the timestamps fall into, so indexed into the firing rates

        # indexes are into the firing rate
        print("Processing saccade timings..")
        saccade_trials = self._process_timings(self.saccade_timings, self.saccade_motions, self.saccade_blocks, "saccade")

        print("Processing probe timings..")
        probe_trials = self._process_timings(self.probe_timings, self.probe_motions, self.probe_blocks, "probe")

        print("Filtering saccades..")
        filt_sac_trials = self._filter_saccades_by_time([s.copy() for s in saccade_trials], [p.copy() for p in probe_trials])
        print(f"Filter found {len(filt_sac_trials)} saccade trials")
        print("Demixing trials..")
        demixed_trials = self._demix_trials(probe_trials, saccade_trials, add_saccades=False)  # Dont include since we're filtering above
        demixed_names, demixed_counts = np.unique([tr.trial_label for tr in demixed_trials], return_counts=True)
        for i in range(len(demixed_names)):
            print(f"Demixed {demixed_counts[i]} {demixed_names[i]} trials")

        # Sort by event time TODO CHeck demixed only has mixed and probes
        print("Sorting trials by event time..")
        combined = []
        combined.extend(demixed_trials)
        combined.extend(filt_sac_trials)

        all_trials = self._sort_trials(combined)
        group = ModulationTrialGroup(all_trials)

        print("Dumping trialgroup data to cached file..")
        with open(SaccadicModulationTrialProcessor.CACHE_FILENAME, "wb") as f:
            pickle.dump(group, f)

        return group
