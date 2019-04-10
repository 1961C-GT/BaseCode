#!/usr/bin/env python3

import math
import time

import tkinter as tk
from tkinter import font
from tkinter import *
from multiprocessing import Process, Pipe

from main import Main
from backend import Backend


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

        # self.scan_mark(self.scan_x,self.scan_y)

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
        self.canvas_shift((self.width - old_width) / 2, (self.height - old_height) / 2)

    def canvas_shift(self, x, y):
        self.x_offset = self.x_offset - x
        self.y_offset = self.y_offset - y
        self.move_by(x, y)

    def move_by(self, x, y):
        self.x_pos = self.x_pos + x
        self.y_pos = self.y_pos + y
        self.scan_dragto(int(self.x_pos / 10), int(self.y_pos / 10))

    def move_to(self, x, y):
        self.x_pos = x
        self.y_pos = y
        self.scan_dragto(int(self.x_pos / 10), int(self.y_pos / 10))


# Message Structures
# {
#   "cmd": "draw_circle",
#   "args": {
#       "x": 200,
#       "y": 300,
#       "r": 50
#   }
# }
# 
# {
#   "cmd": "frame_start"
#   "args": None
# }
# 
# {
#   "cmd": "clear_screen"
#   "args": None
# }

class EngDisplay:
    def __init__(self, src=None):
        self.backend = Backend()
        self.parent_conn, self.child_conn = Pipe()
        self.data_src = src
        self.main = Main(src, multi_pipe=self.child_conn)
        self.proc = Process(target=self.main.run)
        self.proc.start()
        # self.width = 700
        # self.height = 700
        self.move_amt = 20
        self.m_to_pixel = 1
        self.meas_to_map = 1 / 1000
        self.universal_scale = 2
        self.start_pos = []
        self.measuring = False
        self.cur_line = None
        self.cur_line_txt = None
        self.closed = False

        self.create_eng_display()

    def create_eng_display(self):
        self.window = tk.Tk()
        self.myframe = Frame(self.window)
        self.myframe.pack(fill=BOTH, expand=YES)
        w, h = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.canvas = ResizingCanvas(self.myframe, width=w, height=h, borderwidth=0, bg="#22252b", highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=YES)
        self.zoom(3)
        # root.resizable(width=False, height=False)
        # self.canvas = tk.Canvas(self.window, borderwidth=0,
        # highlightthickness=0, bg="#22252b")
        # self.canvas.grid(column=0, row=0, columnspan=30)
        # self.canvas.create_rectangle(-2500, -300, 3000, 4250, fill="#22242a")
        # Add menu
        self.menu_bar = Menu(self.window)
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Exit", command=self.window.quit, accelerator="Cmd+q")
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.window.config(menu=self.menu_bar)

        # Bind these functions to motion, press, and release
        self.canvas.bind('<Motion>', self.measure)
        self.canvas.bind('<Button-1>', self.start_measure)
        self.canvas.bind('<Button-3>', lambda e: self.zoom(0.9))
        self.canvas.bind('<Button-2>', lambda e: self.zoom(0.9))
        self.window.bind('<Up>', lambda e: self.canvas.move_by(0, self.move_amt))
        self.window.bind('<Down>', lambda e: self.canvas.move_by(0, -self.move_amt))
        self.window.bind('<Left>', lambda e: self.canvas.move_by(self.move_amt, 0))
        self.window.bind('<Right>', lambda e: self.canvas.move_by(-self.move_amt, 0))
        self.canvas.bind('<ButtonRelease-1>', self.stop_measure)

        self.canvas.addtag_all("bg")

        self.window.protocol("WM_DELETE_WINDOW", self.close_callback)

        self.create_circle(100, 100, 100)
        if not self.update_frame():
            return

        self.main_loop()

    def close_callback(self):
        self.window.destroy()
        self.closed = True
        print('Window Closed!')

    def main_loop(self):
        frame_end = False
        receiving = True
        last_update = 0
        while True:
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
                        elif msg['cmd'] == "frame_end":
                            frame_end = True
                            break
                        elif msg['cmd'] == "clear_screen":
                            self.clear_canvas()
                        elif msg['cmd'] == "draw_circle":
                            self.draw_circle(msg['args'])
                        elif msg['cmd'] == "connect_points":
                            self.connect_points(msg['args'])
                        else:
                            print(f"Unknown command: {msg['cmd']}")
                    else:
                        print(msg)
                else:
                    receiving = False
            receiving = True

    # Interactive features

    def update_frame(self):
        try:
            self.window.update_idletasks()
            self.window.update()
        except:
            return False
        return True

    def measure(self, event):
        # Check to see if we are measuring
        (x, y) = self.translate_screen_pos_to_canvas_pos(event.x, event.y)
        if self.measuring:
            # Try to remove the old elements
            try:
                event.widget.delete(self.cur_line)
                event.widget.delete(self.cur_line_txt)
            except:
                pass
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
                (self.start_pos[0] - x) ** 2 + (self.start_pos[1] - y) ** 2) / self.universal_scale / self.m_to_pixel
            # Calculate distance string
            dist = '{:.0f}m'.format(dist_num)
            # Create the text
            self.cur_line_txt = event.widget.create_text(midx, midy, text=dist,
                                                         fill="white", font=font.Font(family='Courier New', size=14),
                                                         justify=tk.LEFT, angle=rotation)
            # Create the line
            self.cur_line = event.widget.create_line(self.start_pos[0], self.start_pos[1], x,
                                                     y, fill="#3c4048", dash=(3, 5), arrow=tk.BOTH)

    def shrink(self, scale, x=None, y=None):
        # objs = self.canvas.find_all()
        # for obj in objs:
        #     if self.canvas.type(obj) == "text" and not 'scale' in self.canvas.gettags(obj):
        #         continue
        #     if x is None or y is None:
        #         x = self.window.winfo_pointerx() - self.window.winfo_rootx()
        #         y = self.window.winfo_pointery() - self.window.winfo_rooty()
        #     (x, y) = self.translate_screen_pos_to_canvas_pos(x,y)
        #     self.canvas.scale(obj, x, y, scale, scale)
        if x is None or y is None:
            x = self.window.winfo_pointerx() - self.window.winfo_rootx()
            y = self.window.winfo_pointery() - self.window.winfo_rooty()
        (x, y) = self.translate_screen_pos_to_canvas_pos(x, y)
        self.canvas.scale("obj", x, y, scale, scale)
        self.universal_scale *= scale

    def translate_screen_pos_to_canvas_pos(self, x, y):
        return x - self.canvas.x_pos, y - self.canvas.y_pos

    def translate_canvas_pos_to_screen_pos(self, x, y):
        return x + self.canvas.x_pos, y + self.canvas.y_pos

    def start_measure(self, event):
        # Save the initial point
        (x, y) = self.translate_screen_pos_to_canvas_pos(event.x, event.y)
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

    @staticmethod
    def get_val_from_args(args, val):
        if val in args:
            return args[val]
        else:
            return None

    def draw_circle(self, args):
        x = self.get_val_from_args(args, "x")
        y = self.get_val_from_args(args, "y")
        r = self.get_val_from_args(args, "r")
        fill = self.get_val_from_args(args, "fill")
        tags = self.get_val_from_args(args, "tags")
        outline = self.get_val_from_args(args, "outline")
        width = self.get_val_from_args(args, "width")
        text = self.get_val_from_args(args, "text")
        if x is None or y is None or r is None:
            print(f"Invalid args input for function 'draw_circle': {args}")
            return
        x = x * self.universal_scale
        y = y * self.universal_scale
        r = r * self.universal_scale
        (x, y) = self.translate_screen_pos_to_canvas_pos(x, y)
        if fill is None:
            fill = ""
        if tags is None:
            tags = []
        if outline is None:
            outline = "white"
        if width is None:
            width = 3
        x = x * self.meas_to_map
        y = y * self.meas_to_map
        r = r * self.meas_to_map
        self.create_circle(x, y, r, extra_tags=tags, fill=fill, width=width, outline=outline)

        if text is not None:
            ypos = y - r - 20
            if ypos < 0:
                ypos = y + r + 20
            self.create_text(x, ypos, text=text)

    def connect_points(self, args):
        pos1 = self.get_val_from_args(args, "pos1")
        pos2 = self.get_val_from_args(args, "pos2")
        dashed = self.get_val_from_args(args, "dashed")
        color = self.get_val_from_args(args, "color")
        text = self.get_val_from_args(args, "text")
        text_size = self.get_val_from_args(args, "text_size")
        text_color = self.get_val_from_args(args, "text_color")
        if pos1 is None or pos2 is None:
            print(f"Invalid args input for function 'connect_points': {args}")
            return
        if dashed is None:
            dashed = True
        if color is None:
            color = "#3c4048"

        pos1_scaled = (pos1[0] * self.meas_to_map * self.universal_scale + self.canvas.x_pos,
                       pos1[1] * self.meas_to_map * self.universal_scale + self.canvas.y_pos)
        pos2_scaled = (pos2[0] * self.meas_to_map * self.universal_scale + self.canvas.x_pos,
                       pos2[1] * self.meas_to_map * self.universal_scale + self.canvas.y_pos)

        self._connect_points(pos1_scaled, pos2_scaled, text=text, text_size=text_size, text_color=text_color,
                             dashed=dashed, color=color)

    def create_circle(self, x, y, r, extra_tags=[], **kwargs):
        (x, y) = self.translate_canvas_pos_to_screen_pos(x, y)
        tags = ["obj"]
        return self.canvas.create_oval(x - r, y - r, x + r, y + r, tags=(tags + extra_tags), **kwargs)

    def create_text(self, x, y, text="", extra_tags=[], **kwargs):
        (x, y) = self.translate_canvas_pos_to_screen_pos(x, y)
        tags = ["obj"]
        self.canvas.create_text(x, y, text=text,
                                fill="white", font=font.Font(family='Courier New', size=14),
                                justify=tk.LEFT, tags=(tags + extra_tags))

    def _connect_points(self, node1_pos, node2_pos, text=None, text_size=None, text_color=None, dashed=True,
                        color="#3c4048"):
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
            if text_size is None:
                text_size = 14
            if text_color is None:
                text_color = "white"
            self.canvas.create_text(midx, midy, text=text,
                                    fill=text_color, font=font.Font(family='Courier New', size=text_size),
                                    justify=tk.LEFT, tags=['scale', 'obj'])  # angle=rotation
        if dashed is True:
            self.canvas.create_line(node1_pos[0], node1_pos[1], node2_pos[0], node2_pos[1], fill=color, dash=(1, 5),
                                    tags="obj")
        else:
            self.canvas.create_line(node1_pos[0], node1_pos[1], node2_pos[0], node2_pos[1], fill=color, tags="obj")


if __name__ == "__main__":
    EngDisplay(sys.argv[1] if len(sys.argv) == 2 else None)
