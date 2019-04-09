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


########
# Main #
########

class Main:

    def __init__(self, src=None, alg_name='multi_tri', multi_pipe=None):

        self.PACKET_PROCESSORS = {"Range Packet": self.process_range, "Stats Packet": self.process_stats}

        # Communication with engineering display
        self.multi_pipe = multi_pipe

        # Load from file if specified, otherwise serial
        if src:
            self.src = open(src)
            self.log_file = None
        else:
            self.src = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD)
            self.log_file = open("log-{}.log".format(datetime.now().strftime("%Y%m%d-%H%M%S")), 'w')

        # Thread for piping stdin to the serial port (for manually typing commands)
        serial_sender = SerialSender(outputPipe = self.src)
        serial_sender.start()

        # Load algorithm
        alg_module = importlib.import_module('algorithms.' + alg_name + '.' + alg_name)
        self.algorithm = getattr(alg_module, alg_name)

        # Connect to backend
        if not self.multi_pipe:
            self.backend = Backend()
        else:
            for node_id, node in Main.r_nodes.items():
                node.set_pipe(self.multi_pipe)

    def run(self):
        self.multi_pipe.send("Hey, @realMainThread here. I’m alive.") if self.multi_pipe else None
        self.multi_pipe.send("Test!") if self.multi_pipe else None
        cmd_obj = {
            "cmd": "draw_circle",
            "args": {
                "x": 100,
                "y": 100,
                "r": 25
            }
        }
        self.multi_pipe.send(cmd_obj) if self.multi_pipe else None

        # Clear out the backend of stale data
        self.multi_pipe.send({"cmd": "backend_clear_nodes"}) if self.multi_pipe else self.backend.clear_nodes()

        line_ctr = 0
        packet_ctr = 0
        start_time = time.time()

        self.src.readline()  # discard first (possibly incomplete) line
        for line in self.src:
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

        print()
        print("Processed {} lines ({} packets) in {} secs".format(line_ctr, packet_ctr, time.time() - start_time))
        print("Total non-base node resolutions: {}".format(Main.resolved_ctr))
        self.multi_pipe.send("@realMainThread signing off. Peace.") if self.multi_pipe else None

    #####################
    # Packet processors #
    #####################

    r_current_cycle = None
    r_cycle_offset = None
    r_cycle_data = []
    r_cycle_history = []
    r_nodes = {
        "1": Node("1", "Base 2", is_base=True, x=0, y=0),
        "0": Node("0", "Base 1", is_base=True, x=47000, y=0),
        "2": Node("2", "Node 1"),
        "3": Node("3", "Node 2"),
        "4": Node("4", "Node 3"),
        "5": Node("5", "Node 4"),
    }

    resolved_ctr = 0

    def algorithm_callback(self, nodes, _t, _n):
        self.multi_pipe.send({"cmd": "backend_clear_nodes"}) if self.multi_pipe else self.backend.clear_nodes()
        for node_id, node in nodes.items():
            self.multi_pipe.send({"cmd": "backend_update_node", "args": node}) if self.multi_pipe \
                else self.backend.update_node(node)
            if not node.is_base and node.is_resolved():
                Main.resolved_ctr += 1

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
                self.algorithm(Main.r_nodes)._process(self.algorithm_callback)
            else:
                self.multi_pipe.send({"cmd": "frame_start", "args": None})
                self.algorithm(Main.r_nodes)._process(self.algorithm_callback, multi_pipe=self.multi_pipe)
                self.multi_pipe.send({"cmd": "frame_end", "args": None})

            # TODO: push r_cycle_history into algorithm
            # TODO: push algorithm results into UI backend
            # we might want to do this in a separate thread

            # Keep track of cycle count in a way that's not affected by system reboots
            Main.r_current_cycle += 1
            Main.r_cycle_offset = p_cycle - Main.r_current_cycle
            Main.r_cycle_data = []
            for node_id, node in Main.r_nodes.items():
                node.start_new_cycle()
                # node.show()

        # print("Got range from {} -> {}: {} (cycle {})".format(p_from, p_to, p_range, r_current_cycle))
        Main.r_nodes[p_from].add_measurement(Main.r_nodes[p_to], p_range)
        Main.r_cycle_data.append([p_from, p_to, p_range, p_hops, p_seq])

    def process_stats(self, packet):
        p_cycle, p_from, p_seq, p_hops, p_bat, p_temp, p_heading = packet
        p_bat = volts_to_percentage(float(p_bat))
        # print("Got stats from {}: bat={}%, temp={}C, heading={}º (cycle {}, seq {}, {} hops)".format(p_from, p_bat, p_temp,
        #                                                                                              p_heading, p_cycle,
        #                                                                                              p_seq, p_hops))
        # TODO: push stats directly into UI backend

#################
# Serial Sender #
#################
# Allows user input from the main console to be piped directly to the 
# Serial interface.
class SerialSender(threading.Thread):
    def __init__(self, outputPipe):
        super().__init__()
        self.outputPipe = outputPipe

    def run(self):
        # Infinate loop (kinda sucks)
        while (True):
            # See if we have anything to read in
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                # If we do, then write it directly to the serial interface
                self.outputPipe.write(bytes(sys.stdin.readline(), 'utf-8'))
            # Sleep for a little so that the infinate loop doesnt kill the CPU
            time.sleep(0.1)

if __name__ == "__main__":
    Main(sys.argv[1] if len(sys.argv) == 2 else None).run()
