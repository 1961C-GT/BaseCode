#!/usr/bin/env python3

import importlib
import serial
import sys
import time

from algorithms.helpers.node import Node
from battery import volts_to_percentage

import config

# Load algorithm
alg_name = 'multi_tri'
alg_module = importlib.import_module('algorithms.' + alg_name + '.' + alg_name)
algorithm = getattr(alg_module, alg_name)

#####################
# Packet processors #
#####################

r_current_cycle = None
r_cycle_offset = None
r_cycle_data = []
r_cycle_history = []
r_nodes = {
    "0": Node("0", "Base 1", is_base=True, x=0, y=0),
    "1": Node("1", "Base 2", is_base=True, x=47000, y=0),
    "2": Node("2", "Node 1"),
    "3": Node("3", "Node 2"),
    "4": Node("4", "Node 3"),
    "5": Node("5", "Node 4"),
}

resolved_ctr = 0


def algorithm_callback(nodes, _t, _n):
    global resolved_ctr
    for node_id, node in nodes.items():
        if not node.is_base and node.is_resolved():
            resolved_ctr += 1


def process_range(packet):
    p_cycle, p_from, p_to, p_seq, p_hops, p_range = packet
    p_cycle = int(p_cycle)
    p_range = int(p_range)

    # START code to discard initial cycle
    global r_current_cycle, r_cycle_offset, r_cycle_data, r_cycle_history
    if not r_current_cycle:
        r_current_cycle = p_cycle
    if p_cycle == r_current_cycle:
        return
    if not r_cycle_offset:
        r_current_cycle = 0
        r_cycle_offset = 0
    # END code to discard initial cycle

    if p_cycle != r_current_cycle + r_cycle_offset:

        # Pop old cycle data out of the history, and
        # insert the latest data at the front.
        while len(r_cycle_history) >= config.MAX_HISTORY:
            r_cycle_history.pop()
        r_cycle_history.insert(0, r_cycle_data)

        algorithm(r_nodes)._process(algorithm_callback)

        # TODO: push r_cycle_history into algorithm
        # TODO: push algorithm results into UI backend
        # we might want to do this in a separate thread

        # Keep track of cycle count in a way that's not affected by system reboots
        r_current_cycle += 1
        r_cycle_offset = p_cycle - r_current_cycle
        r_cycle_data = []
        for node_id, node in r_nodes.items():
            node.start_new_cycle()

    print("Got range from {} -> {}: {} (cycle {})".format(p_from, p_to, p_range, r_current_cycle))
    r_nodes[p_from].add_measurement(r_nodes[p_to], p_range)
    r_cycle_data.append([p_from, p_to, p_range, p_hops, p_seq])


def process_stats(packet):
    p_cycle, p_from, p_seq, p_hops, p_bat, p_temp, p_heading = packet
    p_bat = volts_to_percentage(float(p_bat))
    print("Got stats from {}: bat={}%, temp={}C, heading={}º (cycle {}, seq {}, {} hops)".format(p_from, p_bat, p_temp,
                                                                                                 p_heading, p_cycle,
                                                                                                 p_seq, p_hops))
    # TODO: push stats directly into UI backend


PACKET_PROCESSORS = {"Range Packet": process_range, "Stats Packet": process_stats}


########
# Main #
########

def main(src):
    line_ctr = 0
    packet_ctr = 0
    start_time = time.time()

    src.readline()  # discard first (possibly incomplete) line
    for line in src:

        try:
            # Try to decode 'bytes' from serial
            line = line.decode("utf-8")
        except AttributeError:
            # Probably already a 'str' from file
            pass

        tmp = line.strip().split("|")
        line_ctr += 1

        # Make sure we have a valid packet
        if len(tmp) != 2:
            continue

        # Check packet type
        packet_type = tmp[0].strip()
        if packet_type not in PACKET_PROCESSORS.keys():
            continue
        packet_ctr += 1

        # Clean up packet contents
        packet_contents = tmp[1].strip().split(',')
        for i in range(len(packet_contents)):
            packet_contents[i] = packet_contents[i].strip().split(":")[1]

        # Pass to packet processor for processing
        PACKET_PROCESSORS[packet_type](packet_contents)

    print()
    print("Processed {} lines ({} packets) in {} secs".format(line_ctr, packet_ctr, time.time() - start_time))
    print("Total non-base node resolutions: {}".format(resolved_ctr))


if __name__ == "__main__":

    # Load from file if specified, otherwise serial
    if len(sys.argv) < 2:
        data_src = serial.Serial(config.PORT, config.BAUD)
    else:
        data_src = open(sys.argv[1])

    main(data_src)
