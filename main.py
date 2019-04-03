#!/usr/bin/env python3

import serial
import sys
import time

import config

#####################
# Packet processors #
#####################

r_current_cycle = None
r_cycle_offset = None
r_cycle_data = []
r_cycle_history = []


def process_range(packet):
    p_cycle, p_from, p_to, p_seq, p_hops, p_range = packet
    p_cycle = int(p_cycle)

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

        # TODO: push r_cycle_history into algorithm
        # TODO: push algorithm results into UI backend
        # we might want to do this in a separate thread

        # Keep track of cycle count in a way that's not affected by system reboots
        r_current_cycle += 1
        r_cycle_offset = p_cycle - r_current_cycle
        r_cycle_data = []

    r_cycle_data.append([p_from, p_to, p_range, p_hops, p_seq])


def process_stats(packet):
    p_cycle, p_from, p_seq, p_hops, p_bat, p_temp, p_heading = packet
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

    print("Processed {} lines ({} packets) in {} secs".format(line_ctr, packet_ctr, time.time() - start_time))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        src = serial.Serial(config.PORT, config.BAUD)
    else:
        src = open(sys.argv[1])
    main(src)
