#!/usr/bin/env python3

from datetime import datetime
import importlib
import serial
import sys
import select
import time
import threading

from algorithms.helpers.node import Node
from backend import Backend
from battery import volts_to_percentage
import config
from meas_history import MeasHistory


########
# Main #
########

class Main:

    def __init__(self, src=None, alg_name='multi_tri', multi_pipe=None, serial_pipe=None, repeat_log=False):

        self.PACKET_PROCESSORS = {"Range Packet": self.process_range, "Stats Packet": self.process_stats}

        # Communication with engineering display
        self.multi_pipe = multi_pipe
        self.kill = False
        self.log_file_name = None
        self.repeat_log = repeat_log

        # Load from file if specified, otherwise serial
        if src:
            self.src_input = src
            self.src = open(src)
            self.log_file = None
            self.playback_pipe = serial_pipe
        else:
            self.repeat_log = False
            try:
                self.src = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD)
                self.log_file_name = "log-{}.log".format(datetime.now().strftime("%Y%m%d-%H%M%S"))
                self.log_file = open(self.log_file_name, 'w')
                # Thread for piping stdin to the serial port (for manually typing commands)
                serial_sender = SerialSender(output_pipe=self.src, multi_pipe=serial_pipe)
                self.playback_pipe = None
                serial_sender.start()
            except serial.serialutil.SerialException as e:
                self.kill = True
                print(e)
                if self.multi_pipe is not None:
                    self.multi_pipe.send({
                        'cmd': 'error',
                        'type': 'no_serial'
                    })
                return

        # Load algorithm
        alg_module = importlib.import_module('algorithms.' + alg_name + '.' + alg_name)
        self.algorithm = getattr(alg_module, alg_name)

        # Connect to backend
        self.backend = Backend(Main.ANCHORED_BASE, Main.CALCULATED_BASE)
        if self.multi_pipe:
            for node_id, node in Main.r_nodes.items():
                node.set_pipe(self.multi_pipe)

        self.name_arr = []
        self.history = {}
        for key, value in Main.r_nodes.items():
            val = int(key)
            for i in range(val + 1, len(Main.r_nodes)):
                self.name_arr.append(f"{val}-{i}")

        for name in self.name_arr:
            if Main.AUTO_SETUP_BASE is True and name == Main.auto_base_meas_key:
                self.history[name] = MeasHistory(name, max_meas=100, min_vals=5)
            else:
                self.history[name] = MeasHistory(name)
        self.node_list = Main.r_nodes

    def run(self):
        if self.kill:
            return
        self.multi_pipe.send("Hey, @realMainThread here. I’m alive.") if self.multi_pipe else None

        # Clear out the backend of stale data
        self.backend.clear_nodes()

        line_ctr = 0
        packet_ctr = 0
        start_time = time.time()

        paused = True
        do = True
        self.pause_time = 0

        while do or self.repeat_log is True:
            self.src.readline()  # discard first (possibly incomplete) line
            for line in self.src:
                if self.playback_pipe is not None:

                    while do or paused is True:
                        do = False
                        msg = None
                        if paused:
                            msg = self.playback_pipe.recv()
                        elif self.playback_pipe.poll():
                            msg = self.playback_pipe.recv()
                        if msg is not None and type(msg) == dict and "cmd" in msg:
                            if msg['cmd'] == "play":
                                paused = False
                            elif msg['cmd'] == "pause":
                                paused = True
                            elif msg['cmd'] == "set_speed" and 'speed' in msg:
                                if float(msg['speed']) == 0:
                                    self.pause_time = 0
                                else:
                                    self.pause_time = 1 / float(msg['speed'])
                    do = True
                try:
                    # Try to decode 'bytes' from serial
                    line = line.decode("utf-8")
                except AttributeError:
                    # Probably already a 'str' from file
                    pass

                # Write log, flush to make sure we got it down
                if self.log_file:
                    self.log_file.write(line)
                    self.log_file.flush()

                tmp = line.strip().split("|")
                line_ctr += 1

                # Make sure we have a valid packet
                if len(tmp) != 2:
                    continue

                # Check packet type
                packet_type = tmp[0].strip()
                if packet_type not in self.PACKET_PROCESSORS.keys():
                    continue
                packet_ctr += 1

                # Clean up packet contents
                packet_contents = tmp[1].strip().split(',')
                for i in range(len(packet_contents)):
                    packet_contents[i] = packet_contents[i].strip().split(":")[1]

                # Pass to packet processor for processing
                self.PACKET_PROCESSORS[packet_type](packet_contents)

            if self.repeat_log:
                self.multi_pipe.send({
                    'cmd':'clear_connection_list',
                    'args': {}
                })
                self.src = open(self.src_input)
            else:
                do = False
            

        print()
        print("Processed {} lines ({} packets) in {} secs".format(line_ctr, packet_ctr, time.time() - start_time))
        print("Total non-base node resolutions: {}".format(Main.resolved_ctr))
        self.multi_pipe.send("@realMainThread signing off. Peace.") if self.multi_pipe else None

    #####################
    # Packet processors #
    #####################

    AUTO_SETUP_BASE = config.AUTO_SETUP_BASE
    MANUAL_BASE_DIST = config.MANUAL_BASE_DIST

    ANCHORED_BASE = None
    CALCULATED_BASE = None

    r_nodes = {}
    for node_id, details in config.NODES.items():
        if 'name' not in details:
            print('INVALID NODE SETUP: All nodes require the "name" attribute in config.py.')
            exit()
            continue
        if 'is_base' in details and details['is_base'] is True:
            r_nodes[node_id] = Node(node_id, details['name'], is_base=True)
            if 'base_type' in details:
                if details['base_type'] == 'anchored':
                    if ANCHORED_BASE is None:
                        ANCHORED_BASE = node_id
                    else:
                        print('INVALID NODE SETUP: Only one node may have the "anchored" attribute.')
                        exit()
                elif details['base_type'] == 'calculated':
                    if CALCULATED_BASE is None:
                        CALCULATED_BASE = node_id
                    else:
                        print('INVALID NODE SETUP: Only one node may have the "calculated" attribute.')
                        exit()
        else:
            r_nodes[node_id] = Node(node_id, details['name'])

    if ANCHORED_BASE is None or CALCULATED_BASE is None:
        print(
            'INVALID NODE SETUP: Two base stations must be specified, and each needs to be "calculated" or "anchored" in type.')
        exit()

    config.ANCHORED_BASE = ANCHORED_BASE
    config.CALCULATED_BASE = CALCULATED_BASE

    r_current_cycle = None
    r_cycle_offset = None
    r_cycle_data = []
    r_cycle_history = []

    auto_base_meas_key = ANCHORED_BASE + "-" + CALCULATED_BASE
    if int(ANCHORED_BASE) > int(CALCULATED_BASE):
        auto_base_meas_key = CALCULATED_BASE + "-" + ANCHORED_BASE

    if AUTO_SETUP_BASE is False:
        r_nodes[CALCULATED_BASE].set_real_x_pos(MANUAL_BASE_DIST)
    else:
        r_nodes[CALCULATED_BASE].force_set_resolved(False)

    resolved_ctr = 0

    def algorithm_callback(self, nodes, _t, _n):
        # self.backend.clear_nodes()
        for node_id, node in nodes.items():
            self.backend.update_node(node)
            if not node.is_base and node.is_resolved():
                Main.resolved_ctr += 1

    @staticmethod
    def get_key_from_nodes(node_id_1, node_id_2):
        n1 = int(node_id_1)
        n2 = int(node_id_2)
        if n1 > n2:
            return str(n2) + "-" + str(n1)
        else:
            return str(n1) + "-" + str(n2)

    def process_range(self, packet):
        p_cycle, p_from, p_to, p_seq, p_hops, p_range = packet
        p_cycle = int(p_cycle)
        p_range = int(p_range)

        # START code to discard initial cycle
        if not Main.r_current_cycle:
            Main.r_current_cycle = p_cycle
        if p_cycle == Main.r_current_cycle:
            return
        if not Main.r_cycle_offset:
            Main.r_current_cycle = 0
            Main.r_cycle_offset = 0
        # END code to discard initial cycle

        if p_cycle != Main.r_current_cycle + Main.r_cycle_offset:

            # Pop old cycle data out of the history, and
            # insert the latest data at the front.
            while len(Main.r_cycle_history) >= config.MAX_HISTORY:
                Main.r_cycle_history.pop()
            Main.r_cycle_history.insert(0, Main.r_cycle_data)

            if self.multi_pipe is None:
                self.algorithm(Main.r_nodes, Main.ANCHORED_BASE, Main.CALCULATED_BASE)._process(self.algorithm_callback)
            else:
                self.multi_pipe.send({"cmd": "frame_start", "args": None})
                self.algorithm(Main.r_nodes, Main.ANCHORED_BASE, Main.CALCULATED_BASE)._process(self.algorithm_callback,
                                                                                                multi_pipe=self.multi_pipe)
                self.multi_pipe.send({"cmd": "frame_end", "args": None})

            # Keep track of cycle count in a way that's not affected by system reboots
            Main.r_current_cycle += 1
            Main.r_cycle_offset = p_cycle - Main.r_current_cycle
            Main.r_cycle_data = []
            for node_id, node in Main.r_nodes.items():
                node.start_new_cycle()
                # node.show()
            for name in self.name_arr:
                # self.history[name].new_cycle()
                meas = self.history[name]
                n1 = meas.get_node_1()
                n2 = meas.get_node_2()
                avg = meas.get_avg()
                std = meas.get_std_deviation()
                meas.new_cycle()
                if avg != 0:
                    Main.r_nodes[n1].add_measurement(Main.r_nodes[n2], avg, std=std)
                    Main.r_nodes[n2].add_measurement(Main.r_nodes[n1], avg, std=std)

                if Main.AUTO_SETUP_BASE and name == Main.auto_base_meas_key and avg != 0:
                    Main.r_nodes[Main.CALCULATED_BASE].set_real_x_pos(avg)

            if self.pause_time > 0:
                time.sleep(self.pause_time)

        key = self.get_key_from_nodes(p_from, p_to)
        if self.multi_pipe is not None:
            self.multi_pipe.send({
                "cmd": "report_communication",
                "args": {
                    "key": key
                }
            })
        self.history[key].add_measurement(p_range)
        Main.r_cycle_data.append([p_from, p_to, p_range, p_hops, p_seq])

    def process_stats(self, packet):
        p_cycle, p_from, p_seq, p_hops, p_batt, p_temp, p_heading = packet
        p_heading = float(p_heading)
        p_temp = float(p_temp)
        p_batt = volts_to_percentage(float(p_batt))
        self.backend.update_node_telemetry(Main.r_nodes[p_from], p_temp, p_batt, p_heading, "TELEMETRY")
        if self.multi_pipe is not None:
            self.multi_pipe.send({
                'cmd': 'status_update',
                'args': {
                    'node_id': p_from,
                    'bat': p_batt,
                    'temp': p_temp,
                    'heading': p_heading
                }
            })


#################
# Serial Sender #
#################
# Allows user input from the main console to be piped directly to the 
# Serial interface.
class SerialSender(threading.Thread):
    def __init__(self, output_pipe, multi_pipe=None):
        super().__init__()
        self.output_pipe = output_pipe
        self.multi_pipe = multi_pipe

    def run(self):
        # Infinite loop (kinda sucks)
        while True:
            # See if we have anything to read in
            try:
                if self.multi_pipe is not None and self.multi_pipe.poll():
                    msg = self.multi_pipe.recv()
                    if type(msg) == dict and "cmd" in msg:
                        if msg['cmd'] == "reset":
                            print("Sending reset to base station")
                            self.output_pipe.write(bytes(f"?R\n", 'utf-8'))
                        elif msg['cmd'] == "sleep":
                            if 'time' in msg:
                                time_val = int(msg['time'])
                                time_val_str = str(time_val)
                                if len(time_val_str) > 5:
                                    print("Sleep value too long!!")
                                    return
                                time_val_str = time_val_str.zfill(5)
                                print("Sending sleep to base station with time of '{}'".format(time_val_str))
                                self.output_pipe.write(bytes(f"?S{time_val_str}\n", 'utf-8'))
                            else:
                                print('ERROR: No sleep time mentioned!')
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    # If we do, then write it directly to the serial interface
                    self.output_pipe.write(bytes(sys.stdin.readline(), 'utf-8'))
                # Sleep for a little so that the infinite loop doesnt kill the CPU
                time.sleep(0.1)
            except ValueError:  # We closed the pipe
                return


def main(arg):
    src = None
    repeat = False
    if len(arg) > 0:
        for a in arg:
            if a == '-l' or a == '-light':
                pass
            elif a == '-r' or a == '-repeat':
                repeat = True
            elif src is None:
                src = a
            else:
                print(f"Unknown command entry: {a}")
                exit(1)
    Main(src, repeat_log=repeat).run()


if __name__ == "__main__":
    main(sys.argv[1:])
