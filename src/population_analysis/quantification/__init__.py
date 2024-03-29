import math
import time
from multiprocessing import Pool

import numpy as np
import random

import pendulum


class Quantification(object):
    def __init__(self, name):
        self.name = name

    def calculate(self, class_1_data, class_2_data):
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
    NUM_SAMPLES = 10000

    def __init__(self, class_1_data, class_2_data, quan: Quantification):
        self.quan: Quantification = quan
        self.class_1_data = class_1_data
        self.class_2_data = class_2_data
        self._progress = 0

    def original(self):
        return self.quan.calculate(self.class_1_data, self.class_2_data)

    def get_name(self):
        return self.quan.get_name()

    def _calculate(self, num_samples):
        if isinstance(num_samples, tuple):
            num_samples, display = num_samples
        else:
            display = False

        all_values = np.vstack([self.class_1_data, self.class_2_data])
        values_len = len(all_values)
        half = int(values_len / 2)
        quan_values = []

        if display:
            print("Calculating quantification 10k times -", end="")

        one_tenth = int(num_samples / 10)
        start = pendulum.now()
        for progress in range(num_samples):  # Calculate quan 10k times

            if display and progress % one_tenth == 0:
                print(f" {round(progress / num_samples, 2)*100}%", end="")

                # end = pendulum.now()
                # print(start.diff(end).in_seconds())
                # start = pendulum.now()

            np.random.shuffle(all_values)
            new_class_1 = all_values[:half]
            new_class_2 = all_values[half:]
            val = self.quan.calculate(new_class_1, new_class_2)
            quan_values.append(val)

        return quan_values

    def _calc_sample_args(self, num_pools):
        val = math.floor(QuanDistribution.NUM_SAMPLES / num_pools)
        remainder = QuanDistribution.NUM_SAMPLES % num_pools

        nums = [val] * num_pools
        nums[-1] = (nums[-1] + remainder, True)
        return nums

    def calculate(self):
        num_pools = 4
        print(f"Setting up {num_pools} pools for multiprocessing..")
        with Pool(num_pools + 1) as p:
            results = p.map(self._calculate, [*self._calc_sample_args(num_pools)])
            print("\nDone")
            dists = []
            for r in results:
                dists.extend(r)

            return dists
