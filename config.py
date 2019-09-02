######################
# Serial port config #
######################

SERIAL_PORT = "/dev/tty.usbserial-UUT2"
SERIAL_BAUD = 256000  # 921600

####################
# Algorithm config #
####################

MAX_HISTORY = 20  # How many historical cycles to feed to algorithm

##################
# Backend config #
##################

ENABLE_BACKEND = True
BACKEND_URL = "https://web.mnslac.xtriage.com/graphql"

###############
# Site config #
###############

AUTO_SETUP_BASE = True
MANUAL_BASE_DIST = 47000  # Units in mm. Only used if AUTO_SETUP_BASE is False

NODES = {
    "0": {"name": "Base 1", "is_base": True, "base_type": "anchored"},
    "1": {"name": "Base 2", "is_base": True, "base_type": "calculated"},
    "2": {"name": "Yassine 0"},  # N1
    "3": {"name": "Sai 0"},  # N2
    "4": {"name": "Node 3"},  # N3
    "5": {"name": "Norris 0"}   # N4
}

ANCHORED_BASE_GPS = 34.21797, -83.95238
CALCULATED_BASE_GPS = 34.21763, -83.95173
