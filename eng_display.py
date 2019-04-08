#!/usr/bin/env python3

import math

import tkinter as tk
from tkinter import font
from tkinter import *
from canvasvg import *
from multiprocessing import Process, Pipe

from main import Main


class EngDisplay:
    def __init__(self, src=None):
        self.parent_conn, self.child_conn = Pipe()
        self.data_src = src
        self.main = Main(src, multi_pipe=self.child_conn)
        self.proc = Process(target=self.main.run)
        self.proc.start()
        self.width = 700
        self.height = 700
        self.move_amt = 20
        self.universal_scale = 1
        self.start_pos = []
        self.measuring = False
        self.cur_line = None
        self.cur_line_txt = None

        self.create_eng_display()

    def create_eng_display(self):
        self.window = tk.Tk()
        # root.resizable(width=False, height=False)
        self.canvas = tk.Canvas(self.window, width=self.width, height=self.height, borderwidth=0,
                                highlightthickness=0, bg="#22252b")
        self.canvas.grid(column=0, row=0, columnspan=30)
        self.canvas.create_rectangle(-2500, -300, 3000, 4250, fill="#22242a")
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
        self.window.bind('<Up>', lambda e: self.move(0, self.move_amt))
        self.window.bind('<Down>', lambda e: self.move(0, -self.move_amt))
        self.window.bind('<Left>', lambda e: self.move(self.move_amt, 0))
        self.window.bind('<Right>', lambda e: self.move(-self.move_amt, 0))
        self.canvas.bind('<ButtonRelease-1>', self.stop_measure)

        self.main_loop()

    def main_loop(self):
        while True:
            try:
                self.window.update_idletasks()
                self.window.update()
            except:
                return
            if self.parent_conn.poll():
                msg = self.parent_conn.recv()
                print(msg)

    # Interactive features

    def measure(self, event):
        # Check to see if we are measuring
        if self.measuring:
            # Try to remove the old elements
            try:
                event.widget.delete(self.cur_line)
                event.widget.delete(self.cur_line_txt)
            except:
                pass
            # Calculate the rotation between the two points
            rotation = 180 - math.degrees(math.atan2(self.start_pos[1] - event.y,
                                                     self.start_pos[0] - event.x))
            # Normalize the rotation
            if 90 < rotation < 270:
                rotation -= 180
            # Convert to radians
            rrotation = math.radians(rotation)
            # Calculate mid point + rotation offset
            midx = (self.start_pos[0] + event.x) / 2 - math.sin(rrotation) * 10
            midy = (self.start_pos[1] + event.y) / 2 - math.cos(rrotation) * 10
            # Calculate distance
            dist_num = math.sqrt(
                (self.start_pos[0] - event.x) ** 2 + (self.start_pos[1] - event.y) ** 2) / self.universal_scale
            # Calculate distance string
            dist = '{:.0f}ft'.format(dist_num)
            # Create the text
            self.cur_line_txt = event.widget.create_text(midx, midy, text=dist,
                                                         fill="white", font=font.Font(family='Courier New', size=14),
                                                         justify=tk.LEFT, angle=rotation)
            # Create the line
            self.cur_line = event.widget.create_line(self.start_pos[0], self.start_pos[1], event.x,
                                                     event.y, fill="#3c4048", dash=(3, 5), arrow=tk.BOTH)

    def shrink(self, scale, x=None, y=None):
        objs = self.canvas.find_all()
        for obj in objs:
            if self.canvas.type(obj) == "text" and not 'scale' in self.canvas.gettags(obj):
                continue
            if x is None or y is None:
                x = self.window.winfo_pointerx() - self.window.winfo_rootx()
                y = self.window.winfo_pointery() - self.window.winfo_rooty()
            self.canvas.scale(obj, x, y, scale, scale)
        self.universal_scale *= scale

    def move(self, x, y):
        objs = self.canvas.find_all()
        for obj in objs:
            if self.canvas.type(obj) == "text" and not 'scale' in self.canvas.gettags(obj):
                continue
            self.canvas.move(obj, x, y)

    def start_measure(self, event):
        # Save the initial point
        self.start_pos = (event.x, event.y)
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
        now_pos = (event.x, event.y)
        if self.start_pos[0] == now_pos[0] and self.start_pos[1] == now_pos[1]:
            self.zoom(1.1)
        # Try to remove the old elements
        try:
            event.widget.delete(self.cur_line)
            event.widget.delete(self.cur_line_txt)
        except:
            pass

    # Helper Functions

    def create_circle(self, x, y, r, **kwargs):
        return self.canvas.create_oval(x - r, y - r, x + r, y + r, **kwargs)


if __name__ == "__main__":
    EngDisplay(sys.argv[1] if len(sys.argv) == 2 else None)
