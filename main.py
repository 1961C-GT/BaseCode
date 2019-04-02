import serial
import struct

port = "/dev/tty.usbserial-UUT2"
ser = serial.Serial(port, 921600)


def main():
    print("Looking for end of message...")
    while ser.read(1) != 0x55 and ser.read(1) != 0xAA:
        pass
    print("Found end of message.")

    while True:
        msg_type = ser.read(1)

        if msg_type == 0xA1:
            print("Message type: Distance")
            msg_contents = ser.read(17)
            msg = struct.unpack("IBBdBH", msg_contents)
            print(msg)
            pass
        elif msg_type == 0xA2:
            print("Message type: Telemetry")
            msg_contents = ser.read(10)
            msg = struct.unpack("IBHBH", msg_contents)
            print(msg)
            pass
        elif msg_type == 0xA3:
            print("Message type: Status")
            msg_contents = ser.read(16)
            msg = struct.unpack("IBHHHHBH", msg_contents)
            print(msg)
            pass
        else:
            # Message type: Invalid
            print("Detected invalid message type {}!".format(msg_type.encode('hex')))
            pass
        # TODO PUSH INTO ALGORITHM


if __name__ == "__main__":
    main()