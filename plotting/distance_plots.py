import os
import time

import numpy as np
from pynwb import NWBHDF5IO

from population_analysis.consts import NUM_FIRINGRATE_SAMPLES
from population_analysis.population.plots.pca_meta import run_pca
from population_analysis.quantification.euclidian import EuclidianQuantification
import matplotlib.pyplot as plt


def _calc_dists(data_dict, shuffled=False):
    # Calculate the mean euclidian distance between datasets, pairwise
    # if shuffled=True, then randomize the points between the two datasets before calculating mean
    # data_dict is {"Rp(Extra)": <rp data>, ..}
    # returns like {"Rp(Extra)-Rp(Peri)": [dist_t_0, dist_t_1, ..], ..}
    euclid_dist = EuclidianQuantification("Pairwise")

    def dist_func(name, data, name1, data1):
        dist_data = []
        dist_name = f"{name}-{name1}"
        if shuffled:
            shuf = np.hstack([data, data1]).swapaxes(0, 1)
            np.random.shuffle(shuf)
            shuf = shuf.swapaxes(0, 1)
            data = shuf[:, :data.shape[1], :]
            data1 = shuf[:, data.shape[1]:, :]

        for t in range(NUM_FIRINGRATE_SAMPLES):
            dist_data.append(euclid_dist.calculate(
                data[:, :, t].swapaxes(0, 1),
                data1[:, :, t].swapaxes(0, 1)
            ))
        return dist_name, dist_data
    result = _pairwise_iter(data_dict, dist_func)
    return result


def _pairwise_iter(data_dict, func):
    # func is f(name, data, name2, data2) -> result: Any
    results = []
    data_pairs = list(data_dict.items())
    for i in range(len(data_pairs)):
        name, data = data_pairs.pop()
        for name1, data1 in data_pairs:
            if name == name1:
                continue
            results.append(func(name, data, name1, data1))
    return results


def pairwise_mean_distances(data_dict):
    # Distance between the means of each data type (probe, saccade, mixed, etc..) over time
    dists = _calc_dists(data_dict)
    shuffled_dists = [_calc_dists(data_dict, shuffled=True) for _ in range(10)]
    # dist data - dists[0][1]
    # [s[0][1] for s in shuffled_dists]
    for idx in range(len(dists)):
        pair_name, vals = dists[idx]

        for shuf_data in shuffled_dists:
            _, shuf_vals = shuf_data[idx]
            plt.plot(range(NUM_FIRINGRATE_SAMPLES), shuf_vals, color="orange")
        plt.plot(range(NUM_FIRINGRATE_SAMPLES), vals, color="blue")

        plt.title(pair_name)
        plt.show()


def pairwise_mean_distances_single_plot(data_dict):
    # Distance between the means of each data type (probe, saccade, mixed, etc..) over time
    dists = _calc_dists(data_dict)

    for idx in range(len(dists)):
        pair_name, vals = dists[idx]
        plt.plot(range(NUM_FIRINGRATE_SAMPLES), vals)

    plt.show()


def pairwise_scaled_mean_distances(data_dict):
    # iterate over a space of scales to determine distance between means
    scale_range = np.linspace(-2, 2)

    def wrapper(timepoint):
        def iter_func(name1, data1, name2, data2):
            data1_mean = np.mean(data1, axis=1)[:, timepoint]  # (units, t) avg trials out
            data2_mean = np.mean(data2, axis=1)[:, timepoint]

            data1_mean = scale_range[:, None] * np.broadcast_to(data1_mean, (len(scale_range), *data1_mean.shape))
            data2_mean = np.broadcast_to(data2_mean, (len(scale_range), *data2_mean.shape))

            euclid_dist = EuclidianQuantification("Scaled")
            dists = [euclid_dist.calculate([data1_mean[i, :]], [data2_mean[i, :]]) for i in range(len(scale_range))]
            return f"{name1}-{name2}", dists

        return iter_func

    all_results = [_pairwise_iter(data_dict, wrapper(i)) for i in range(NUM_FIRINGRATE_SAMPLES)]

    for pair_idx in range(len(all_results[0])):
        count = 0
        name = None
        fig = plt.figure()
        three_d = False
        if three_d:
            ax = fig.add_subplot(projection='3d')
        else:
            ax = fig.add_subplot()

        for result in all_results:
            k, v = result[pair_idx]
            name = k
            args = [scale_range[range(len(v))], v]
            if three_d:
                args.append(count)

            ax.plot(*args, color=plt.get_cmap("hsv")(count))
            count = count + 1
            # plt.show()
            # ax = plt.figure().add_subplot()
            # time.sleep(1)
        plt.title(name)
        plt.show()

    # y = np.array(all_data[0][0])[:, 36]
    # plt.figure()
    # plt.plot(range(len(y)), y)
    # plt.show()
    tw = 2


def mean_pca_response(data_dict):
    # all_values = np.hstack(list(data_dict.values()))
    # all_values = all_values.swapaxes(0,2).reshape((-1, all_values.shape[0]))
    # pca, data = run_pca(all_values, components=2)
    count = 0
    for name, val in data_dict.items():
        avg = np.mean(val, axis=1)
        avg = np.mean(avg, axis=0)
        plt.plot(range(len(avg)), avg, color=plt.get_cmap("Set1")(count))
        # for unit in avg:
        #     plt.plot(range(len(unit)), unit, color=plt.get_cmap("Set1")(count))
        count = count + 1
    plt.show()
    tw = 2
    pass


def main():
    filename = "2023-05-15_mlati7_output"
    filepath = "../scripts/" + filename + ".nwb"
    filename_prefix = f"../graphs/{filename}"
    if not os.path.exists(filename_prefix):
        os.makedirs(filename_prefix)

    nwbio = NWBHDF5IO(filepath)
    nwb = nwbio.read()

    probe_trial_idxs = nwb.processing["behavior"]["unit-trial-probe"].data[:]
    saccade_trial_idxs = nwb.processing["behavior"]["unit-trial-saccade"].data[:]
    mixed_trial_idxs = nwb.processing["behavior"]["unit-trial-mixed"].data[:]

    # Filter out mixed trials that saccades are more than 20ms away from the probe
    mixed_rel_timestamps = nwb.processing["behavior"]["mixed-trial-saccade-relative-timestamps"].data[:]
    mixed_filtered_idxs = np.abs(mixed_rel_timestamps) <= 0.02  # 20 ms
    mixed_trial_idxs = mixed_trial_idxs[mixed_filtered_idxs]

    # (units, trials, t)
    probe_units = nwb.units["trial_response_firing_rates"].data[:, probe_trial_idxs]
    saccade_units = nwb.units["trial_response_firing_rates"].data[:, saccade_trial_idxs]
    mixed_units = nwb.units["trial_response_firing_rates"].data[:, mixed_trial_idxs]
    rp_peri_units = nwb.units["r_p_peri_trials"].data[:]
    tw = 2
    # probe_units = probe_units.swapaxes(0, 1)
    # np.random.shuffle(probe_units)
    # probe_units = probe_units.swapaxes(0, 1)

    split_data = rp_peri_units
    num_split = int(split_data.shape[1] * .1)

    data_dict = {
            # "Rp(Extra)": probe_units[:, :num_split, :],  # (units, trials, t)
            # "Rp(Extra)2": probe_units[:, num_split:, :],

            # "Rp(Extra)": probe_units,  # (units, trials, t)
            # "Rs": saccade_units,
            # "Rmixed": mixed_units,
            # "Rp(Peri)": rp_peri_units
        }
    idxs = []
    for i in range(1, 9):
        start_idx = (i - 1) * num_split
        end_idx = i * num_split
        idxs.append((start_idx, end_idx))
        data_dict[f"Rp(Extra){i}"] = split_data[:, start_idx:end_idx]

    mean_pca_response(data_dict)
    # pairwise_mean_distances_single_plot(data_dict)
    # pairwise_mean_distances(data_dict)
    # pairwise_scaled_mean_distances(data_dict)


if __name__ == "__main__":
    main()