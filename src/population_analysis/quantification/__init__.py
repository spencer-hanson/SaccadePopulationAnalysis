import math
import time
from multiprocessing import Pool

import numpy as np
import random

import pendulum


class Quantification(object):
    def __init__(self, name):
        self.name = name

    def calculate(self, class_1_data, class_2_data) -> float:
        # expects shape to be (units, trials) pass in each time sep
        raise NotImplemented

    def get_name(self):
        return self.name


class TestQuantification(Quantification):
    DATA = [[1, 2, 3], [3, 4, 5], [5, 6, 7]], [[1, 2, 3], [3, 4, 5], [5, 6, 7]]

    def __init__(self):
        super().__init__("Test")
        
    def calculate(self, class_1_data, class_2_data):
        return np.random.normal()


class SlowQuantification(Quantification):
    def __init__(self):
        super().__init__("Slow")
        self.quan = TestQuantification()

    def calculate(self, class_1_data, class_2_data):
        time.sleep(1 / QuanDistribution.NUM_SAMPLES)
        return self.quan.calculate(class_1_data, class_2_data)


class QuanDistribution(object):
    """
    Calculate the distribution of a given quantification, samples 10,000 times and creates a prob dist
    """

    NUM_SAMPLES = 10000
    # NUM_SAMPLES = 7  # TODO Fix me

    def __init__(self, class_1_data, class_2_data, quan: Quantification):
        # Expects data in (units, trials, t)
        self.quan: Quantification = quan
        self.class_1_data = class_1_data
        self.class_2_data = class_2_data
        assert len(self.class_1_data.shape) == 3  # Make sure input is (units, trials, t)
        assert len(self.class_2_data.shape) == 3
        self._progress = 0

    def get_name(self):
        return self.quan.get_name()

    def _calculate(self, num_samples):
        if isinstance(num_samples, tuple):
            num_samples, display = num_samples
        else:
            display = False

        all_values0 = np.copy(np.concatenate([self.class_1_data, self.class_2_data], axis=1))
        part = self.class_1_data.shape[1]  # part is the 'half' or section to cut the data on
        quan_values = []

        if display:
            print("Calculating quantification 10k times -", end="")

        one_tenth = int(num_samples / 10)
        one_tenth = one_tenth if one_tenth != 0 else 1



        # start = pendulum.now()
        for progress in range(num_samples):  # Calculate quan 10k times

            if display and progress % one_tenth == 0:
                print(f" {round(progress / num_samples, 2)*100}%", end="")

                # end = pendulum.now()
                # print(start.diff(end).in_seconds())
                # start = pendulum.now()

            shuf = list(range(all_values0.shape[1]))
            random.shuffle(shuf)

            new_class_1 = all_values0[:, shuf][:, :part]
            new_class_2 = all_values0[:, shuf][:, part:]
            timepoints = []
            for t in range(all_values0.shape[2]):  # Calculate at each timepoint
                timepoints.append(self.quan.calculate(new_class_1[:, :, t], new_class_2[:, :, t]))
            quan_values.append(timepoints)

        return quan_values

    def _calc_sample_args(self, num_pools):
        val = math.floor(QuanDistribution.NUM_SAMPLES / num_pools)
        remainder = QuanDistribution.NUM_SAMPLES % num_pools

        nums = [val] * num_pools
        nums[-1] = (nums[-1] + remainder, True)
        return nums

    def calculate(self):
        num_pools = 4
        calc_args = self._calc_sample_args(num_pools)

        # Uncomment me for a single-threaded version for debugging
        # vals = []
        # for arg in calc_args:
        #     vals.extend(self._calculate(arg))
        # vals = np.array(vals)
        # return vals

        print(f"Setting up {num_pools} pools for multiprocessing..")
        with Pool(num_pools + 1) as p:
            results = p.map(self._calculate, calc_args)
            print("\nDone")
            dists = []
            for r in results:
                dists.extend(r)

            return np.array(dists)
