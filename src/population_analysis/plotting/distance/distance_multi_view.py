from population_analysis.consts import NUM_FIRINGRATE_SAMPLES
import matplotlib.pyplot as plt

from population_analysis.processors.filters import BasicFilter
from population_analysis.processors.filters.trial_filters.rp_peri import RelativeTrialFilter
from population_analysis.quantification.angle import AngleQuantification
from population_analysis.sessions.saccadic_modulation import NWBSession
from population_analysis.quantification.euclidian import EuclidianQuantification
from population_analysis.quantification.magnitude_difference import MagDiffQuantification


def main():
    # filepath = "../../../../scripts"
    # filename = "new_test"

    month = "06"
    day = 30
    year = 2023
    mouse_name = "mlati9"
    filename = f"{mouse_name}-{year}-{month}-{day}-output"
    filepath = f"../../../../scripts/{filename}"
    filename = f"{filename}.hdf-nwb"

    # sess = NWBSession(filepath, filename, "../graphs")
    sess = NWBSession("C:\\Users\\Matrix\\Documents\\GitHub\\SaccadePopulationAnalysis\\scripts\\generated", "generated.hdf-nwb", "")
    # ufilt = BasicFilter([70, 108], sess.num_units)  # 05-19-2023
    ufilt = sess.unit_filter_premade()

    # day = 15
    # filepath = f"../../../../scripts/05-{day}-2023-output"
    # filename = f"05-{day}-2023-output.hdf-nwb"
    # sess = NWBSession(filepath, filename, "../graphs")
    # ufilt = BasicFilter([189, 244, 365, 373, 375, 380, 381, 382, 386, 344], sess.num_units)  # 05-15-2023

    # filepath = "../../../../scripts/generated"
    # filename = "generated.hdf-nwb"

    # matplotlib.use('Agg')  # Uncomment to suppress matplotlib window opening

    # ufilt = sess.unit_filter_premade()
    # ufilt = BasicFilter.empty(sess.num_units)

    rp_extra = sess.units()[ufilt.idxs()]
    rp_peri = sess.rp_peri_units()[ufilt.idxs()]

    quantification_list = [
        # MagQuoQuantification(),
        # EuclidianQuantification(),
        # MagDiffQuantification(),
        AngleQuantification(),
        EuclidianQuantification()
    ]

    fig, axs = plt.subplots(nrows=len(quantification_list), ncols=2, squeeze=True, sharex=True)  # 2 cols for motion dirs
    # fig.tight_layout()

    for col_idx, motdir in enumerate([-1, 1]):
        rp_e_filter = sess.trial_motion_filter(motdir).append(BasicFilter(sess.probe_trial_idxs, rp_extra.shape[1]))
        rp_p_filter = RelativeTrialFilter(sess.trial_motion_filter(motdir), sess.mixed_trial_idxs)

        rpe = rp_extra[:, rp_e_filter.idxs()]
        rpp = rp_peri[:, rp_p_filter.idxs()]

        for row_idx, quan in enumerate(quantification_list):
            axis = axs[row_idx, col_idx]
            dist_arr = []
            for t in range(NUM_FIRINGRATE_SAMPLES):
                dist_arr.append(quan.calculate(rpp[:, :, t], rpe[:, :, t]))
            axis.plot(dist_arr)
            tw = 2
            if row_idx == 0:
                beginning = "Rpp vs Rpe "
            else:
                beginning = ""

            axis.title.set_text(f"{beginning}{quan.get_name()} mot={motdir}")

            if row_idx == len(quantification_list) - 1:
                axis.set_xlabel("Time (20 ms bins)")

    plt.show()
    tw = 2


if __name__ == "__main__":
    main()

