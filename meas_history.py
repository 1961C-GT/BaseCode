import numpy

class MeasHistory:

    MAX_MEAS = 20
    MIN_DIST = 750    # mm
    MAX_DIST = 500000 # mm

    def __init__(self, key, max_meas=MAX_MEAS, min_vals=5):
        self.key = key
        self.node1, self.node2 = self.key.split('-')
        self.meas_list = []
        self.added_meas = False
        self.volitile_cycle = True
        self.max_meas = max_meas
        self.min_vals = min_vals

    def get_key(self):
        return self.key

    def get_node_1(self):
        return self.node1

    def get_node_2(self):
        return self.node2

    def new_cycle(self):
        # pass
        if self.added_meas is False and self.volitile_cycle:
            self.add_measurement(0, override=True)
        self.added_meas = False
        self.volitile_cycle = not self.volitile_cycle

    def add_measurement(self, dist, override=False):
        if not override and (dist < MeasHistory.MIN_DIST or dist > MeasHistory.MAX_DIST):
            return
        self.added_meas = True
        self.meas_list.append(dist)
        if len(self.meas_list) > self.max_meas:
            self.meas_list.pop(0)

    def get_avg(self):
        sum_val = 0
        counter = 0
        for dist in self.meas_list:
            sum_val += dist
            if dist != 0:
                counter += 1
        if counter < self.min_vals:
            return 0 # TODO: Remove when we do deviation?
        return sum_val / counter

    def get_std_deviation(self):
        return numpy.std(self.meas_list)