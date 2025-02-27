import os
import pickle
import time

from population_analysis.consts import NUM_FIRINGRATE_SAMPLES
from population_analysis.plotting.distance.distance_rpp_rpe_errorbars_plots import get_xaxis_vals, confidence_interval
from population_analysis.plotting.distance.distance_verifiation_by_density_rpe_v_rpe_plots import calc_quandist
from population_analysis.quantification.euclidian import EuclidianQuantification
from population_analysis.sessions.saccadic_modulation import NWBSession
from population_analysis.sessions.group import SessionGroup
import matplotlib.pyplot as plt
import numpy as np

DISTANCES_LOCATION = "D:\\PopulationAnalysisDists"


def rnd(x):
    return int(x*1000)


def sess_firingrate(rpp, rpe, ax):
    ax.plot(np.mean(np.mean(rpe, axis=1), axis=0), color="orange", label="RpExtra")
    ax.plot(np.mean(np.mean(rpp, axis=1), axis=0), color="blue", label="RpPeri")
    # fig, ax2 = plt.subplots(nrows=2)
    # [ax2[0].plot(r) for r in np.mean(rpe, axis=1)]
    # [ax2[1].plot(r) for r in np.mean(rpp, axis=1)]
    # fig.show()


def calc_rpextra_error_distribution(sess, use_cached, motdir):
    olddir = os.getcwd()
    os.chdir(DISTANCES_LOCATION)
    quan = EuclidianQuantification()
    tmp_fn = f"debugging_timewindow-{sess.filename_no_ext}.pickle"
    if os.path.exists(tmp_fn):
        with open(tmp_fn, "rb") as f:
            print("LOADING PRECALCULATED RPEXTRA DISTRIBUTION!")
            d = pickle.load(f)
            os.chdir(olddir)
            return d

    ufilt = sess.unit_filter_premade()
    rpperi = sess.rp_peri_units().shape[1]
    rpextra = len(sess.trial_filter_rp_extra().idxs())
    prop = rpperi / rpextra
    prop = prop / 10  # divide by 10 since we have 10 latencies (probe delivery was random, so it's uniformly distrib'd)
    prop = prop / 2  # divide by 2 since we have 2 motion directions

    motions = [motdir]
    quan_dist_motdir_dict = calc_quandist(sess, ufilt, sess.trial_filter_rp_extra(), sess.filename_no_ext, quan=quan, use_cached=use_cached, base_prop=prop, motions=motions)
    data = quan_dist_motdir_dict[motions[0]]
    with open(tmp_fn, "wb") as f:
        pickle.dump(data, f)
    os.chdir(olddir)
    return data


def sess_distance(rpp, rpe, quan, motdir, confidence_val, ax, sess, use_cached):
    rpextra_error_distribution = calc_rpextra_error_distribution(sess, use_cached, motdir)

    distances = []
    means = []
    uppers = []
    lowers = []

    for t in range(NUM_FIRINGRATE_SAMPLES):
        lower, upper = confidence_interval(rpextra_error_distribution[:, t], confidence_val)
        mean = np.mean(rpextra_error_distribution[:, t], axis=0)
        distances.append(quan.calculate(rpp[:, :, t], rpe[:, :, t]))
        means.append(mean)
        uppers.append(upper)
        lowers.append(lower)

    ax.plot(get_xaxis_vals(), distances, color="blue")
    ax.plot(get_xaxis_vals(), means, color="orange")
    ax.plot(get_xaxis_vals(), uppers, color="orange", linestyle="dotted")
    ax.plot(get_xaxis_vals(), lowers, color="orange", linestyle="dotted")


def sess_summary(sess: NWBSession, filename, quan, motdir, confidence_val, use_cached):
    save_fn = f"sess_debug/{filename}.png"
    if os.path.exists(save_fn):
        print(f"Session summary already exists at '{save_fn}' skipping..")
        return

    mmax = 10
    allfig, allax = plt.subplots(ncols=mmax, nrows=2, sharey="row", sharex="row", figsize=(16, 4))
    ufilt = sess.unit_filter_premade()
    # ufilt = BasicFilter.empty(sess.num_units)
    rp_extra = sess.units()[ufilt.idxs()]
    rp_peri = sess.rp_peri_units()[ufilt.idxs()]

    counts = {}
    for i in range(mmax):
        start = (i - (mmax / 2)) / 10
        end = ((i - (mmax / 2)) / 10) + .1

        rpe = rp_extra[:, sess.trial_filter_rp_extra().idxs()]
        rpp = rp_peri[:, sess.trial_filter_rp_peri(start, end).idxs()]
        title = f"{rnd(start)},{rnd(end)}"
        counts[title] = rpp.shape[1]

        allax[0][i].title.set_text(title)
        sess_firingrate(rpp, rpe, allax[0][i])
        sess_distance(rpp, rpe, quan, motdir, confidence_val, allax[1][i], sess, use_cached)

    allax[0][0].set_ylabel("Avg. Firing Rate")
    allax[1][0].set_ylabel("Distance")
    allfig.savefig(save_fn)
    # plt.show()
    tw = 2


def main():
    print("Loading group..")
    # grp = NWBSessionGroup("E:\\PopulationAnalysisNWBs")
    while True:
        # grp = NWBSessionGroup("C:\\Users\\Matrix\\Documents\\GitHub\\SaccadePopulationAnalysis\\scripts\\nwbs")
        grp = SessionGroup("D:\\PopulationAnalysisNWBs")
        if not os.path.exists("sess_debug"):
            os.mkdir("sess_debug")

        quan = EuclidianQuantification()
        motdir = 1
        confidence_val = 0.99
        use_cached = True

        for filename, sess in grp.session_iter():
            sess_summary(sess, filename, quan, motdir, confidence_val, use_cached)

        print("Sleeping 5 minutes before checking new sessions..")
        time.sleep(60*5)


if __name__ == "__main__":
    main()
