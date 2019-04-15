#!/usr/bin/env python3

import math
import time
from sys import platform

import tkinter as tk
from tkinter import font
from tkinter import *
from multiprocessing import Process, Pipe
from eng_colors import EngColors

from main import Main
import config


class EngDisplay:
    def __init__(self, src=None, use_light_theme=False):
        # Check if we're on macOS, first.
        if platform != 'darwin':
            print('This display only supports OSX platforms. Run \'main.py\' directly on other platforms.')
            return
        self.colors = EngColors(use_dark=(not use_light_theme))
        self.parent_conn, self.child_conn = Pipe()
        self.parent_conn_serial_out, self.child_conn_serial_out = Pipe()
        self.data_src = src
        self.main = Main(src, multi_pipe=self.child_conn, serial_pipe=self.child_conn_serial_out)
        if src is None:
            self.using_serial = True
        else:
            self.using_serial = False
        self.proc = Process(target=self.main.run)
        self.proc.start()
        # self.width = 700
        # self.height = 700
        self.move_amt = 20
        self.meas_to_map = 1 / 1000
        self.universal_scale = 2
        self.start_pos = []
        self.measuring = False
        self.cur_line = None
        self.cur_line_txt = None
        self.closed = False
        self.popup_active = False
        self.cycle_counter = 0
        self.paused = True
        self.not_cleared = True
        self.tk_version = tk.TclVersion
        self.create_eng_display()

    def create_eng_display(self):
        self.window = tk.Tk()
        img = tk.Image("photo", file="icon.png")
        try:
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            if bundle:
                info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if info and info['CFBundleName'] == 'Python':
                    info['CFBundleName'] = "MNSLAC"
        except:
            print("NOTICE: To allow edits of Mac application names, install 'pyobjc' via 'pip3 install pyobjc'")

        self.window.tk.call('wm', 'iconphoto', self.window._w, img)
        self.myframe = Frame(self.window)
        self.myframe.pack(fill=BOTH, expand=YES)
        w, h = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.canvas = ResizingCanvas(self.myframe, width=w, height=h, borderwidth=0, bg=self.colors.background,
                                     highlightthickness=0)
        self.window.wm_title(f"MNSLAC Engineering Display")
        self.canvas.pack(fill=BOTH, expand=YES)
        self.zoom(3)

        # Add menu
        # self.menu_bar = Menu(self.window)
        # self.file_menu = Menu(self.menu_bar, tearoff=0)
        # self.file_menu.add_command(label="Exit", command=self.window.quit, accelerator="Cmd+q")
        # self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        # self.help_menu = Menu(self.menu_bar, tearoff=0)
        # self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        # self.window.config(menu=self.menu_bar)

        # Bind these functions to motion, press, and release
        self.canvas.bind('<Motion>', self.measure)
        self.canvas.bind('<Button-1>', self.start_measure)
        self.canvas.bind('<Button-3>', lambda e: self.zoom(0.9))
        self.canvas.bind('<Button-2>', lambda e: self.zoom(0.9))
        self.window.bind('<Up>', lambda e: self.canvas.move_by(0, self.move_amt))
        self.window.bind('<Down>', lambda e: self.canvas.move_by(0, -self.move_amt))
        self.window.bind('<Left>', lambda e: self.canvas.move_by(self.move_amt, 0))
        self.window.bind('<Right>', lambda e: self.canvas.move_by(-self.move_amt, 0))
        self.window.bind('<Shift-Up>', lambda e: self.canvas.move_by(0, self.move_amt * 5))
        self.window.bind('<Shift-Down>', lambda e: self.canvas.move_by(0, -self.move_amt * 5))
        self.window.bind('<Shift-Left>', lambda e: self.canvas.move_by(self.move_amt * 5, 0))
        self.window.bind('<Shift-Right>', lambda e: self.canvas.move_by(-self.move_amt * 5, 0))
        self.canvas.bind('<ButtonRelease-1>', self.stop_measure)
        self.window.protocol("WM_DELETE_WINDOW", self.close_callback)
        # self.canvas.addtag_all("bg")

        # Create crosshairs in background
        scale = 25 * 1000  # Distance in mm between crosshairs
        number = 30  # Total number of crosshairs to be drawn
        min_val = -scale * number
        max_val = scale * number
        length = scale * number * self.universal_scale * self.meas_to_map
        for x in range(min_val, max_val, scale):
            x_tmp = x * self.universal_scale * self.meas_to_map + self.canvas.x_pos
            self.canvas.create_line(int(x_tmp), int(length), int(x_tmp), int(-length), fill=self.colors.crosshair,
                                    tags="obj-bg", dash=(3, 10))  # 1D1F25
        for y in range(min_val, max_val, scale):
            y_tmp = y * self.universal_scale * self.meas_to_map + self.canvas.y_pos
            self.canvas.create_line(int(length), int(y_tmp), int(-length), int(y_tmp), fill=self.colors.crosshair,
                                    tags="obj-bg", dash=(3, 10))

        # Create the MNSLAC icon
        mnslac_icon = PhotoImage(file=self.colors.mnslac_logo)
        self.icon = self.canvas.create_image(w - 10, 10, image=mnslac_icon, anchor=NE)

        # Create the hz update text
        self.update_hz = self.canvas.create_text(10, 10, text="0.0 Hz", fill=self.colors.text,
                                                 font=font.Font(family=self.colors.data_font,
                                                                size=self.colors.text_size_large), anchor=tk.NW)

        # Create the no_connection rectangle and text
        self.no_connection_rect = self.canvas.create_rectangle(-300, h / 3 - 50, 300 + w, h / 3 + 50,
                                                               fill=self.colors.background_accent, tag="del")
        self.no_connection = self.canvas.create_text(w / 2, h / 3, text="NO CONNECTION", fill=self.colors.text_warn,
                                                     font=font.Font(family=self.colors.data_font,
                                                                    size=self.colors.text_size_xlarge),
                                                     anchor=tk.CENTER, tag="del")

        # Create the connection details text based on whether or not we are using a serial connection or log file
        if self.using_serial is False:
            self.no_connection_details = self.canvas.create_text(w / 2, h / 3 + 20,
                                                                 text="Begin playback of log file by clicking 'Play'",
                                                                 fill=self.colors.text_details,
                                                                 font=font.Font(family=self.colors.data_font,
                                                                                size=self.colors.text_size_medium),
                                                                 anchor=tk.CENTER, tag="del")
            msg = f"Loaded from '{self.data_src}'"
        else:
            self.no_connection_details = self.canvas.create_text(w / 2, h / 3 + 20,
                                                                 text="Connect NODE and/or ensure proper serial configuration",
                                                                 fill=self.colors.text_details,
                                                                 font=font.Font(family=self.colors.data_font,
                                                                                size=self.colors.text_size_medium),
                                                                 anchor=tk.CENTER, tag="del")
            serial_port = config.SERIAL_PORT
            saving_log = self.main.log_file_name
            if saving_log is None:
                msg = f"Listening to Serial '{serial_port}', no logging'"
            else:
                msg = f"Listening to Serial '{serial_port}', logging to '{saving_log}'"
        self.file_details = self.canvas.create_text(10, h - 10, text=f"{msg}", fill=self.colors.text,
                                                    font=font.Font(family=self.colors.data_font,
                                                                   size=self.colors.text_size_small), anchor=tk.SW)

        # Initialize the main canvas
        if self.main.kill or not self.update_frame():
            print('Error initializing the main canvas')
            return

        # Create the details canvas
        self.dh = 370
        self.dw = 350
        self.details = Canvas(self.window, width=self.dw, height=self.dh, bg=self.colors.background_accent,
                              highlightthickness=0, borderwidth=0)
        self.details.create_rectangle(2, 2, self.dw - 4, self.dh - 4, fill="", outline=self.colors.pinstripe,
                                      dash=(1, 5))
        self.d_title = self.details.create_text(20, 20, text="Node Details:", fill=self.colors.text_details,
                                                font=font.Font(family='Courier New', size=14), anchor=tk.NW)
        # Create the list for node details based on the node_list from main
        self.node_details_list = {}
        self.connection_list = {}
        y_pos = 50
        for node_id, node_obj in self.main.node_list.items():
            if node_obj.is_base:
                continue
            # Create the text objects for later use
            self.node_details_list[node_id] = {
                'txt_id': self.details.create_text(20, y_pos, text=node_obj.name, fill=self.colors.text_details,
                                                   font=font.Font(family='Courier New', size=12), anchor=tk.NW),
                'name': node_obj.name,
                'bat': 0,
                'temp': 0,
                'heading': 0,
                'speed': 0
            }
            y_pos += 20
        # Create the node ranging section
        y_pos += 20
        self.details.create_text(20, y_pos, text="Ranging List", fill=self.colors.text_details,
                                 font=font.Font(family='Courier New', size=14), anchor=tk.NW)
        y_pos += 30
        x_pos = 20
        y_pos_o = y_pos
        rows_per_col = 5
        row_counter = 0
        for name in self.main.name_arr:
            id1, id2 = name.split('-')
            n1 = self.main.node_list[id1].name
            n2 = self.main.node_list[id2].name
            n1 = n1[0] + n1.split()[1]
            n2 = n2[0] + n2.split()[1]
            self.connection_list[name] = {
                "counter": 0,
                "node_obj1": self.main.node_list[id1],
                "node_obj2": self.main.node_list[id2],
                "name": n1 + "↔" + n2,
                "txt_id": self.details.create_text(x_pos, y_pos, text=n1 + "↔" + n2 + ": 0",
                                                   fill=self.colors.text_details,
                                                   font=font.Font(family='Courier New', size=12), anchor=tk.NW)
            }
            y_pos += 20
            row_counter += 1
            if row_counter == rows_per_col:
                row_counter = 0
                x_pos += 100
                y_pos = y_pos_o
        # Skip below the ranging section
        y_pos = y_pos_o + 20 * rows_per_col + 30
        x_pos = 75
        # Create the section containing buttons, based on whether or not the data source is a file or serial connection
        if self.using_serial:
            # The data source is a serial connection, create the sleep and reset buttons
            button2 = Button(self.window, command=lambda: self.popup_msg(type="sleep"), text="Sleep (Seconds)",
                             width=13, anchor=tk.CENTER, highlightbackground=self.colors.background_accent, bd=0,
                             highlightthickness=0, relief=tk.FLAT)
            button2_window = self.details.create_window(x_pos, y_pos, anchor=tk.CENTER, window=button2)
            x_pos += 74
            y_pos -= 15
            self.sleep_time_entry = Entry(self.window, highlightbackground=self.colors.background_accent,
                                          bg=self.colors.entry_background, bd=2)
            e1_window = self.details.create_window(x_pos, y_pos, anchor=tk.NW, window=self.sleep_time_entry)
            y_pos += 44
            x_pos -= 75
            button1 = Button(self.window, command=lambda: self.popup_msg(type="reset"), text="Reset Network", width=13,
                             anchor=tk.CENTER, highlightbackground=self.colors.background_accent, bd=0,
                             highlightthickness=0, relief=tk.FLAT)
            button1_window = self.details.create_window(x_pos, y_pos, anchor=tk.CENTER, window=button1)
        else:
            # The data source is a file, create the play/pause button and playback speed slider
            y_pos += 10
            self.play_pause_button_string = tk.StringVar()
            self.pause_play_button = Button(self.window, command=self.play_pause,
                                            textvariable=self.play_pause_button_string, width=13, anchor=tk.CENTER,
                                            highlightbackground=self.colors.background_accent, bd=0,
                                            highlightthickness=0, relief=tk.FLAT)
            self.play_pause_button_string.set("Play")
            button2_window = self.details.create_window(x_pos, y_pos, anchor=tk.CENTER, window=self.pause_play_button)
            x_pos += 75
            y_pos -= 1
            self.update_hz_limit_scale = Scale(self.window, from_=0, to=1, resolution=0.001,
                                               command=self.update_refresh_hz, orient=HORIZONTAL,
                                               troughcolor=self.colors.slider_trough, borderwidth=0, length=175,
                                               width=15, relief=tk.FLAT, activebackground="#AAA", sliderrelief=tk.FLAT,
                                               showvalue=False, fg="#FFF")
            self.update_hz_limit_scale.set(1)
            w_window = self.details.create_window(x_pos, y_pos, anchor=tk.W, window=self.update_hz_limit_scale)
            self.details.create_text(x_pos, y_pos - 15, text="Slow", fill=self.colors.text_details,
                                     font=font.Font(family='Courier New', size=10), anchor=tk.W)
            self.details.create_text(x_pos + 175, y_pos - 15, text="Fast", fill=self.colors.text_details,
                                     font=font.Font(family='Courier New', size=10), anchor=tk.E)
            self.update_hz_target_text = self.details.create_text(x_pos + 88, y_pos + 18, text="≈60Hz",
                                                                  fill=self.colors.text_details,
                                                                  font=font.Font(family='Courier New', size=10),
                                                                  anchor=tk.CENTER)

        self.canvas.assign_resize_callback(self.resize_event)
        # self.proc.terminate()
        self.main_loop()

    def popup_msg(self, type="reset"):
        if self.popup_active:
            return
        valid = False
        message = ""
        target = None
        if type == "reset":
            valid = True
            message = "Are you sure you want to reset?"
            target = self.reset_network
        elif type == "sleep":
            try:
                self.sleep_time = int(self.sleep_time_entry.get())
                self.sleep_time_entry.config(fg=self.colors.text)
                message = "Sleep for {} seconds OK?".format(int(self.sleep_time))
                target = self.sleep_network
                valid = True
            except:
                self.sleep_time_entry.config(fg=self.colors.text_error)
                print('Invalid value for sleep time: {}'.format(self.sleep_time_entry.get()))
        else:
            print('Unknown pop message type: {}'.format(type))
            return

        if valid:
            ph = 80
            pw = 270
            self.popup = Canvas(self.window, width=pw, height=ph, bg=self.colors.background_dialog,
                                highlightthickness=0, borderwidth=0)
            w, h = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
            self.popup.place(x=w / 2 - pw / 2, y=h / 3 - ph / 2)
            self.popup.create_rectangle(1, 1, pw - 3, ph - 3, fill="", outline="#888", dash=(1, 5))
            self.popup.create_rectangle(0, 0, pw, 20, fill=self.colors.background_accent, outline="")
            self.popup.create_polygon([-1, ph, 4, ph, -1, ph - 5], outline='', fill=self.colors.background, width=0)
            self.popup.create_polygon([pw + 1, ph, pw - 4, ph, pw + 1, ph - 5], outline='', fill=self.colors.background,
                                      width=0)
            self.popup.create_polygon([-1, -1, 4, -1, -1, 5], outline='', fill=self.colors.background, width=0)
            self.popup.create_polygon([pw + 1, -1, pw - 4, -1, pw + 1, 5], outline='', fill=self.colors.background,
                                      width=0)
            self.popup.create_text(pw / 2, 11, text="NOTICE", fill=self.colors.text_notice,
                                   font=font.Font(family='Courier New', size=14), anchor=tk.CENTER)
            self.popup.create_text(pw / 2, 35, text=message, fill=self.colors.text_invert,
                                   font=font.Font(family='Helvetica', size=14), anchor=tk.CENTER)
            yes_button = Button(self.window, command=target, text="Yes", width=13, anchor=tk.CENTER,
                                highlightbackground=self.colors.background_dialog, bd=0, highlightthickness=0,
                                relief=tk.FLAT)
            yes_button_window = self.popup.create_window(70, ph - 20, anchor=tk.CENTER, window=yes_button)
            no_button = Button(self.window, command=self.destroy_popup, text="No", width=13, anchor=tk.CENTER,
                               highlightbackground=self.colors.background_dialog, bd=0, highlightthickness=0,
                               relief=tk.FLAT)
            no_button_window = self.popup.create_window(pw - 70, ph - 20, anchor=tk.CENTER, window=no_button)
            self.popup_active = True
            self.ph = ph
            self.pw = pw

    def destroy_popup(self):
        if self.popup_active:
            self.popup.destroy()
        self.popup_active = False

    def reset_network(self):
        self.destroy_popup()
        self.parent_conn_serial_out.send({
            'cmd': 'reset'
        })

    def sleep_network(self):
        self.destroy_popup()
        self.parent_conn_serial_out.send({
            'cmd': 'sleep',
            'time': self.sleep_time
        })

    def play_pause(self):
        print('Play Pause!')
        if self.using_serial is False:
            self.paused = not self.paused
            if self.paused:
                self.parent_conn_serial_out.send({
                    'cmd': 'pause'
                })
                # self.details.itemconfig(self.pause_play_button, text="Play")
                self.play_pause_button_string.set("Play")
            else:
                self.parent_conn_serial_out.send({
                    'cmd': 'play'
                })
                # self.details.itemconfig(self.pause_play_button, text="Pause")
                self.play_pause_button_string.set("Pause")

    # 0 -> 1
    # 0.5 -> 5
    # 1 -> 60
    def update_refresh_hz(self, value):
        try:
            refresh_hz = float(value)
            if refresh_hz <= 0.5:
                refresh_hz = refresh_hz * 8 + 1
            else:
                refresh_hz = (refresh_hz - 0.5) * 110 + 5
            if refresh_hz == 60:
                refresh_hz = 0  # Sets unlimited hz
                self.details.itemconfig(self.update_hz_target_text, text="∞".format(float(refresh_hz)),
                                        font=font.Font(family=self.colors.data_font, size=22))
            else:
                self.details.itemconfig(self.update_hz_target_text, text="≈{:.2f}Hz".format(float(refresh_hz)),
                                        font=font.Font(family=self.colors.data_font, size=10))
            self.parent_conn_serial_out.send({
                'cmd': 'set_speed',
                'speed': refresh_hz
            })
        except Exception as e:
            pass

    def resize_event(self, event):
        self.details.place(x=event.width - (self.dw + 25), y=event.height - (self.dh + 25))
        if self.popup_active is True:
            self.popup.place(x=event.width / 2 - self.pw / 2, y=event.height / 3 - self.ph / 2)
        coords = self.canvas.coords(self.icon)
        self.canvas.move(self.icon, (event.width - 10) - coords[0], 0)
        coords = self.canvas.coords(self.file_details)
        self.canvas.move(self.file_details, 0, (event.height - 10) - coords[1])

        if self.not_cleared:
            coords = self.canvas.coords(self.no_connection)
            self.canvas.move(self.no_connection, event.width / 2 - coords[0], event.height / 3 - coords[1])
            coords = self.canvas.coords(self.no_connection_details)
            self.canvas.move(self.no_connection_details, event.width / 2 - coords[0], event.height / 3 + 20 - coords[1])
            coords = self.canvas.coords(self.no_connection_details)
            self.canvas.move(self.no_connection_details, event.width / 2 - coords[0], event.height / 3 + 20 - coords[1])
            coords = self.canvas.coords(self.no_connection_rect)
            self.canvas.move(self.no_connection_rect, -300 - coords[0], event.height / 3 - 40 - coords[1])

    def close_callback(self):
        self.window.destroy()
        self.closed = True
        print('Window Closed!')
        self.proc.terminate()

    def main_loop(self):
        frame_end = False
        receiving = True
        last_update = 0
        message_timer = 0
        try:
            while True:
                if time.time() - message_timer > 0.5:
                    message_timer = time.time()
                    self.draw_update_hz(int(self.cycle_counter / 0.5))
                    self.cycle_counter = 0
                if frame_end is True:
                    if not self.update_frame():
                        return
                    last_update = time.time()
                    # self.clear_canvas()
                    frame_end = False
                elif time.time() - last_update > 0.01666666667:
                    if not self.update_frame():
                        return
                    last_update = time.time()
                while receiving is True:
                    if self.parent_conn.poll():
                        msg = self.parent_conn.recv()
                        if type(msg) == dict and "cmd" in msg:
                            if "args" not in msg:
                                continue
                            if msg['cmd'] == "frame_start":
                                frame_end = False
                                self.clear_canvas()
                                self.cycle_counter += 1
                            elif msg['cmd'] == "frame_end":
                                frame_end = True
                                break
                            elif msg['cmd'] == "clear_screen":
                                self.clear_canvas()
                            elif msg['cmd'] == "draw_circle":
                                self.draw_circle(msg['args'])
                            elif msg['cmd'] == "connect_points":
                                self.connect_points(msg['args'])
                            elif msg['cmd'] == "status_update":
                                self.status_update(msg['args'])
                            elif msg['cmd'] == "report_communication":
                                self.report_communication(msg['args'])
                            else:
                                print(f"Unknown command: {msg['cmd']}")
                        else:
                            print(msg)
                    else:
                        receiving = False
                receiving = True
        except tk.TclError:
            print('Close detected. Exit!')
            exit()

    # Interactive features

    def draw_update_hz(self, hz_value):
        txt = "{} Hz".format(hz_value)
        self.canvas.itemconfig(self.update_hz, text=txt)

    def update_frame(self):
        try:
            self.window.update_idletasks()
            self.window.update()
        except:
            return False
        return True

    def measure(self, event):
        # txt = "Coordinates: ({}, {}) meters".format(round(x), round(y))
        # self.details.itemconfig(self.d_mouse, text=txt)
        # Check to see if we are measuring
        if self.measuring:
            # Try to remove the old elements
            try:
                event.widget.delete(self.cur_line)
                event.widget.delete(self.cur_line_txt)
            except:
                pass
            (x, y) = self.translate_screen_pos_to_canvas_pos(event.x, event.y)
            x = x + self.canvas.x_pos
            y = y + self.canvas.y_pos
            # Calculate the rotation between the two points
            rotation = 180 - math.degrees(math.atan2(self.start_pos[1] - y,
                                                     self.start_pos[0] - x))
            # Normalize the rotation
            if 90 < rotation < 270:
                rotation -= 180
            # Convert to radians
            rrotation = math.radians(rotation)
            # Calculate mid point + rotation offset
            midx = (self.start_pos[0] + x) / 2 - math.sin(rrotation) * 10
            midy = (self.start_pos[1] + y) / 2 - math.cos(rrotation) * 10
            # Calculate distance
            dist_num = math.sqrt(
                (self.start_pos[0] - x) ** 2 + (self.start_pos[1] - y) ** 2) / self.universal_scale
            # Calculate distance string
            dist = '{:.0f}m'.format(dist_num)
            # Create the text
            self.cur_line_txt = event.widget.create_text(midx, midy, text=dist,
                                                         fill=self.colors.text,
                                                         font=font.Font(family=self.colors.data_font,
                                                                        size=self.colors.text_size_large),
                                                         justify=tk.LEFT, angle=rotation)
            # Create the line
            self.cur_line = event.widget.create_line(self.start_pos[0], self.start_pos[1], x,
                                                     y, fill=self.colors.main_line, dash=(3, 5), arrow=tk.BOTH)

    def shrink(self, scale, x=None, y=None):
        if x is None or y is None:
            x = self.window.winfo_pointerx() - self.window.winfo_rootx()
            y = self.window.winfo_pointery() - self.window.winfo_rooty()
        # (x, y) = self.translate_screen_pos_to_canvas_pos(0, 0)
        # x = x + self.canvas.x_pos
        # y = y + self.canvas.y_pos
        # print(x, y)
        # x = 0
        # y = 0
        # self.canvas.scale("obj", x, y, scale, scale)
        # self.canvas.scale("obj-bg", x, y, scale, scale)

        old_scale = self.universal_scale
        self.universal_scale *= scale
        self.canvas.scale("obj", self.canvas.x_pos, self.canvas.y_pos, scale, scale)
        self.canvas.scale("obj-bg", self.canvas.x_pos, self.canvas.y_pos, scale, scale)

    def translate_screen_pos_to_canvas_pos(self, x, y):
        return x - self.canvas.x_pos - self.canvas.x_offset, y - self.canvas.y_pos - self.canvas.y_offset

    def translate_canvas_pos_to_screen_pos(self, x, y):
        return x + self.canvas.x_pos + self.canvas.x_offset, y + self.canvas.y_pos + self.canvas.y_offset

    def start_measure(self, event):
        # Save the initial point
        (x, y) = self.translate_screen_pos_to_canvas_pos(event.x, event.y)
        x = x + self.canvas.x_pos
        y = y + self.canvas.y_pos
        self.start_pos = (x, y)
        # Set measuring to True
        self.measuring = True

    def zoom(self, scale, center=False):
        if center is False:
            self.shrink(scale)
        else:
            self.shrink(scale, x=0, y=0)

    def stop_measure(self, event):
        # Include globals
        # Set measuring to False
        self.measuring = False
        now_pos = self.translate_screen_pos_to_canvas_pos(event.x, event.y)
        now_pos = (now_pos[0] + self.canvas.x_pos, now_pos[1] + self.canvas.y_pos)
        if self.start_pos[0] == now_pos[0] and self.start_pos[1] == now_pos[1]:
            self.zoom(1.1)
        # Try to remove the old elements
        try:
            event.widget.delete(self.cur_line)
            event.widget.delete(self.cur_line_txt)
        except:
            pass

    # Helper Functions

    def clear_canvas(self):
        self.canvas.delete("obj")
        self.canvas.delete("del")
        self.not_cleared = False

    @staticmethod
    def get_val_from_args(args, val):
        if val in args:
            return args[val]
        else:
            return None

    def report_communication(self, args):
        key = self.get_val_from_args(args, "key")
        if key is None:
            print(f"Invalid args input for function 'report_communication': {args}")
            return
        if key in self.connection_list:
            self.connection_list[key]['counter'] += 1
            txt = "{}: {:<5}".format(self.connection_list[key]['name'], self.connection_list[key]['counter'])
            self.details.itemconfig(self.connection_list[key]['txt_id'], text=txt)
        else:
            print(f"Nodes '{key}' not in the comm list. Command 'report_communication'.")

    def status_update(self, args):
        node_id = self.get_val_from_args(args, "node_id")
        bat = self.get_val_from_args(args, "bat")
        temp = self.get_val_from_args(args, "temp")
        heading = self.get_val_from_args(args, "heading")

        if node_id is None or bat is None or temp is None:
            print(f"Invalid args input for function 'status_update': {args}")
            return

        if node_id not in self.node_details_list:
            if node_id != '0' and node_id != '1':
                print(f"Node '{node_id}' not in the details list. Command 'status_update'.")
            return

        txt = "{:<7}| BAT {:<4}, TEMP {:<5}, HDG {}".format(self.node_details_list[node_id]['name'],
                                                            str(round(bat)) + "%", str(round(temp)) + "°C",
                                                            str(round(heading)) + "°")
        self.details.itemconfig(self.node_details_list[node_id]['txt_id'], text=txt)

    def draw_circle(self, args):
        x = self.get_val_from_args(args, "x")
        y = self.get_val_from_args(args, "y")
        r = self.get_val_from_args(args, "r")
        fill = self.get_val_from_args(args, "fill")
        tags = self.get_val_from_args(args, "tags")
        outline = self.get_val_from_args(args, "outline")
        width = self.get_val_from_args(args, "width")
        text = self.get_val_from_args(args, "text")
        text_color = self.get_val_from_args(args, "text_color")
        text_size = self.get_val_from_args(args, "text_size")
        text_y_bias = self.get_val_from_args(args, "text_y_bias")
        if x is None or y is None or r is None:
            print(f"Invalid args input for function 'draw_circle': {args}")
            return
        x = x * self.universal_scale
        y = y * self.universal_scale
        r = r * self.universal_scale
        (x, y) = self.translate_screen_pos_to_canvas_pos(x, y)
        if fill is None:
            fill = 'text'
        if tags is None:
            tags = []
        if outline is None:
            outline = 'blank'
        if width is None:
            width = 3
        x = x * self.meas_to_map
        y = y * self.meas_to_map
        r = r * self.meas_to_map
        self.create_circle(x, y, r, extra_tags=tags, fill=fill, width=width, outline=outline)

        if text is not None:
            if text_color is None:
                text_color = "text"
            if text_size is None:
                text_size = "text_size_large"
            if text_y_bias is None:
                ypos = y - r - 20
                if ypos < 0:
                    ypos = y + r + 20
            else:
                ypos = text_y_bias
            self.create_text(x, ypos, text=text, color=text_color, size=text_size)

    def connect_points(self, args):
        pos1 = self.get_val_from_args(args, "pos1")
        pos2 = self.get_val_from_args(args, "pos2")
        dashed = self.get_val_from_args(args, "dashed")
        color = self.get_val_from_args(args, "color")
        text = self.get_val_from_args(args, "text")
        text_size = self.get_val_from_args(args, "text_size")
        text_color = self.get_val_from_args(args, "text_color")
        arrow = self.get_val_from_args(args, "arrow")
        if pos1 is None or pos2 is None:
            print(f"Invalid args input for function 'connect_points': {args}")
            return
        if dashed is None:
            dashed = True

        if arrow is "both":
            arrow = tk.BOTH
        else:
            arrow = None

        pos1_scaled = (pos1[0] * self.meas_to_map * self.universal_scale + self.canvas.x_pos,
                       pos1[1] * self.meas_to_map * self.universal_scale + self.canvas.y_pos)
        pos2_scaled = (pos2[0] * self.meas_to_map * self.universal_scale + self.canvas.x_pos,
                       pos2[1] * self.meas_to_map * self.universal_scale + self.canvas.y_pos)

        self._connect_points(pos1_scaled, pos2_scaled, text=text, text_size=text_size, text_color=text_color,
                             dashed=dashed, color=color, arrow=arrow)

    def create_circle(self, x, y, r, extra_tags=[], fill=None, outline=None, **kwargs):
        fill = self.refrence_color(fill, default=self.colors.text)
        outline = self.refrence_color(outline, default=self.colors.blank)
        (x, y) = self.translate_canvas_pos_to_screen_pos(x, y)
        tags = ["obj"]
        return self.canvas.create_oval(x - r, y - r, x + r, y + r, tags=(tags + extra_tags), fill=fill, outline=outline,
                                       **kwargs)

    def create_text(self, x, y, text="", color=None, size=None, extra_tags=[], **kwargs):
        size = self.refrence_color(size, self.colors.text_size_large)
        color = self.refrence_color(color, default=self.colors.text)
        (x, y) = self.translate_canvas_pos_to_screen_pos(x, y)
        tags = ["obj"]
        self.canvas.create_text(x, y, text=text,
                                fill=color, font=font.Font(family=self.colors.data_font, size=size),
                                justify=tk.LEFT, tags=(tags + extra_tags))

    def _connect_points(self, node1_pos, node2_pos, text=None, text_size=None, text_color=None, dashed=True,
                        color="#3c4048", arrow=None):
        if node2_pos[0] is None or node2_pos[1] is None or node1_pos[0] is None or node1_pos[1] is None:
            return
        if text is not None:
            # Calculate the rotation between the two points
            rotation = 180 - math.degrees(math.atan2(node1_pos[1] - node2_pos[1],
                                                     node1_pos[0] - node2_pos[0]))
            # node1_pos the rotation
            if 90 < rotation < 270:
                rotation -= 180
            # Convert to radians
            rrotation = math.radians(rotation)
            # Calculate mid point + rotation offset
            midx = (node1_pos[0] + node2_pos[0]) / 2 - math.sin(rrotation) * 5
            midy = (node1_pos[1] + node2_pos[1]) / 2 - math.cos(rrotation) * 5
            text_size = self.refrence_color(text_size, self.colors.text_size_large)
            text_color = self.refrence_color(text_color, default=self.colors.text)
            if self.tk_version >= 8.6:
                self.canvas.create_text(midx, midy, text=text,
                                        fill=text_color, font=font.Font(family=self.colors.data_font, size=text_size),
                                        justify=tk.LEFT, tags=['scale', 'obj'], angle=rotation)
            else:
                self.canvas.create_text(midx, midy, text=text,
                                        fill=text_color, font=font.Font(family=self.colors.data_font, size=text_size),
                                        justify=tk.LEFT, tags=['scale', 'obj'])
        color = self.refrence_color(color, default=self.colors.main_line)
        if dashed is True:
            self.canvas.create_line(node1_pos[0], node1_pos[1], node2_pos[0], node2_pos[1],
                                    width=self.colors.line_width, fill=color, dash=self.colors.dash_type, arrow=arrow,
                                    tags="obj")
        else:
            self.canvas.create_line(node1_pos[0], node1_pos[1], node2_pos[0], node2_pos[1],
                                    width=self.colors.line_width, fill=color, arrow=arrow, tags="obj")

    def refrence_color(self, color, default=None):
        if color == default and default is not None:
            return color
        if color is not None and isinstance(color, str) and hasattr(self.colors, color):
            color = getattr(self.colors, color)
        else:
            if default is None:
                color = self.colors.text
            else:
                color = default
        return color


class ResizingCanvas(Canvas):
    def __init__(self, parent, **kwargs):
        Canvas.__init__(self, parent, **kwargs)
        self.bind("<Configure>", self.on_resize)
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()
        self.scan_x = 0
        self.scan_y = 0
        self.x_pos = 0
        self.y_pos = 0
        self.x_offset = 0
        self.y_offset = 0
        self.move_by(self.width / 4, 100)
        self.callback = None
        self.last_resize = None

    def on_resize(self, event):
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width) / self.width
        hscale = float(event.height) / self.height
        old_width = self.width
        old_height = self.height
        self.width = event.width
        self.height = event.height
        # resize the canvas 
        self.scale("bg", 0, 0, wscale, hscale)
        self.canvas_shift(0, 0)
        if self.callback is not None:
            self.callback(event)
        self.last_resize = event

    def assign_resize_callback(self, callback):
        self.callback = callback
        if self.last_resize is not None:
            self.callback(self.last_resize)

    def canvas_shift(self, x, y):
        self.move_by(x, y)

    def move_by(self, x, y):
        self.x_pos = self.x_pos + x
        self.y_pos = self.y_pos + y
        self.move('obj', x, y)
        self.move('obj-bg', x, y)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        first = True
        use_light_theme = False
        src = None
        for arg in sys.argv:
            if first:
                first = False
                continue
            if arg == '-l' or arg == '-light':
                use_light_theme = True
            elif src is None:
                src = arg
            else:
                print(f"Unknown command entry: {arg}")
                exit
        if src is not None:
            EngDisplay(src=src, use_light_theme=use_light_theme)
        else:
            EngDisplay(use_light_theme=use_light_theme)
    else:
        EngDisplay()
