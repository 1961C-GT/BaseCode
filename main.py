#!/usr/bin/env python3

import serial
import sys

import config


#####################
# Packet processors #
#####################

def process_range(packet):
    print("Got Range packet: {}".format(packet))
    pass


def process_stats(packet):
    print("Got Stats packet: {}".format(packet))
    pass


PACKET_PROCESSORS = {"Range Packet": process_range, "Stats Packet": process_stats}


########
# Main #
########

def main(src):
    src.readline()  # discard first (possibly incomplete) line
    for line in src:
        tmp = line.strip().split("|")

        # Make sure we have a valid packet
        if len(tmp) != 2:
            continue

        # Check packet type
        packet_type = tmp[0].strip()
        if packet_type not in PACKET_PROCESSORS.keys():
            continue

        # Clean up packet contents
        packet_contents = tmp[1].strip().split(',')
        for i in range(len(packet_contents)):
            packet_contents[i] = packet_contents[i].strip()

        # Pass to packet processor for processing
        PACKET_PROCESSORS[packet_type](packet_contents)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        src = serial.Serial(config.PORT, config.BAUD)
    else:
        src = open(sys.argv[1])
    main(src)
