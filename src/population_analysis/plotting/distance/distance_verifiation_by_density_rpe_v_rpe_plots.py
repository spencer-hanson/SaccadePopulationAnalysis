import os.path

import numpy as np
import matplotlib.pyplot as plt
import pickle

from population_analysis.processors.filters import BasicFilter
from population_analysis.quantification import QuanDistribution
from population_analysis.quantification.euclidian import EuclidianQuantification
from population_analysis.sessions.saccadic_modulation import NWBSession

PICKLE_FILENAME_FMT = "quan_dist_rpe_v_rpe_mot_{motdir}.pickle"


def plot_distance_density(data1, name1, data2, name2, quan, shuffle):
    # data1/2 is (units, trials, t)

    if shuffle:
        shuf = np.hstack([data1, data2]).swapaxes(0, 1)
        np.random.shuffle(shuf)
        shuf = shuf.swapaxes(0, 1)
        data1 = shuf[:, :data1.shape[1], :]
        data2 = shuf[:, data1.shape[1]:, :]

    num_t = data1.shape[2]
    dists = []
    for t in range(num_t):
        dists.append(
            quan.calculate(
                data1[:, :, t],
                data2[:, :, t]
            )
        )

    fig, ax = plt.subplots()
    ax.plot(dists)
    plt.show()


def calc_quandist(sess, ufilt, sess_filter, save_filename, base_prop, quan=None, use_cached=False, motions=None):
    motdata = {}  # {1: <arr like (samples10k, 35), -1: ..}
    if quan is None:
        quan = EuclidianQuantification()
    if motions is None:
        motions = [-1, 1]

    for motdir in motions:
        sv_fn = f"{save_filename}-{quan.get_name()}{motdir}.pickle"
        if use_cached and os.path.exists(sv_fn):
            print(f"Using cached quandist result! Loading unit filter and trial filter for mot={motdir}..")
            with open(sv_fn, "rb") as fff:
                motdata[motdir] = pickle.load(fff)
                continue
        trial_filter = sess_filter.append(sess.trial_motion_filter(motdir))
        print("Calculating unit idxs and filter idxs..")
        units = sess.units()[ufilt.idxs()][:, trial_filter.idxs()]
        if base_prop > 1 or base_prop < 0:
            raise ValueError("Cannot split proportion > 1 or < 0!")
        proportion = int(units.shape[1] * base_prop)
        if proportion < 5:
            raise ValueError("Error! Split has less than 5 entries!")

        print("Starting Quantity Distribution calculations..")
        quan_dist = QuanDistribution(
            # units,
            # sess.rp_peri_units()[ufilt.idxs()],
            units[:, :proportion],
            units[:, proportion:],
            quan
        )

        results = quan_dist.calculate()  # (10000, 35) arr of the distances
        motdata[motdir] = results
        print(f"Writing to pickle file '{sv_fn}'")
        fp = open(sv_fn, "wb")
        pickle.dump(results, fp)
        fp.close()
    return motdata


def plot_verif_rpe_v_rpe(sess: NWBSession, ufilt, use_cached=True, suppress_plot=False, quan=None):
    sess_filt = sess.trial_filter_rp_extra()
    rpperi = sess.rp_peri_units().shape[1]
    rpextra = len(sess.trial_filter_rp_extra().idxs())
    prop = rpperi / rpextra

    motdata = calc_quandist(sess, ufilt, sess_filt, "rpe_rpe", prop, quan=quan, use_cached=use_cached)

    if not suppress_plot:
        plt.title("RpExtra v RpExtra distance, 10k bootstrap mean")
        # plt.errorbar(range(35), np.mean(motdata[1], axis=0), label="1", yerr=np.std(motdata[1], axis=0))
        plt.errorbar(range(35), np.mean(motdata[-1], axis=0), label="-1", yerr=np.std(motdata[-1], axis=0), ecolor="oran")
        plt.xlabel("Time (20ms bins)")
        plt.ylabel("Euclidian distance")
        plt.legend()
        plt.show()

    return motdata


def main():
    filename = "new_test"
    # matplotlib.use('Agg')  # Uncomment to suppress matplotlib window opening
    sess = NWBSession("../../../../scripts", filename, "../graphs")
    ufilt = BasicFilter.empty(sess.num_units)

    plot_verif_rpe_v_rpe(sess, ufilt)
    # plot_verif_rpe_v_rpe(sess, False)
    tw = 2


if __name__ == "__main__":
    main()
