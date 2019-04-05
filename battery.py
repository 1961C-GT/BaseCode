import math

bat_step = 0
bat_start_volts = 0
bat_percentage_array = []
bat_imported = False


def import_bat_data(filename):
    global bat_step, bat_start_volts, bat_percentage_array, bat_imported
    bat_percentage_array = []
    with open(filename, 'r') as f:
        for line in f:
            if "=" in line:
                line_arr = (line.rstrip()).split('=')
                if line_arr[0] == 'step':
                    bat_step = float(line_arr[1])
                elif line_arr[0] == 'start':
                    bat_start_volts = float(line_arr[1])
            else:
                bat_percentage_array.append(float(line.rstrip()))
    bat_imported = True


def volts_to_percentage(volts_in):
    if bat_imported is False:
        print('Run \'import_bat_data(filename)\' before running \'volts_to_percentage\'')
        return -1
    index = math.floor((volts_in - bat_start_volts) / bat_step)
    if index < 0:
        return 0.0
    elif index > len(bat_percentage_array):
        return 100.0
    return bat_percentage_array[index]


import_bat_data('./battery.dat')

if __name__ == "__main__":
    print(volts_to_percentage(3.3))  # 0%
    print(volts_to_percentage(4.15))  # 96.6951%
    print(volts_to_percentage(4.2))  # 100%
    print(volts_to_percentage(4.3))  # 100%
    print(volts_to_percentage(3.71))  # 17.3236%
    print(volts_to_percentage(1.0))  # 0%
    print(volts_to_percentage(5.3))  # 100%
