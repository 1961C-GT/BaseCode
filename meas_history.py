class MeasHistory:

    MAX_MEAS = 20
    MIN_DIST = 500    # mm
    MAX_DIST = 1000000 # mm

    def __init__(self, key):
        self.key = key
        self.node1, self.node2 = self.key.split('-')
        self.meas_list = []
        self.added_meas = False

    def get_key(self):
        return self.key

    def get_node_1(self):
        return self.node1

    def get_node_2(self):
        return self.node2

    def new_cycle(self):
        if self.added_meas is False:
            self.add_measurement(0, override=True)
        self.added_meas = False

    def add_measurement(self, dist, override=False):
        if not override and (dist < MeasHistory.MIN_DIST or dist > MeasHistory.MAX_DIST):
            return
        self.added_meas = True
        self.meas_list.append(dist)
        if len(self.meas_list) > MeasHistory.MAX_MEAS:
            self.meas_list.pop(0)

    def get_avg(self):
        sum_val = 0
        counter = 0
        for dist in self.meas_list:
            sum_val += dist
            if dist != 0:
                counter += 1
        if counter < 5:
            return 0 # TODO: Remove when we do deviation?
        return sum_val / counter

    def get_std_deviatoin(self):
        return 0