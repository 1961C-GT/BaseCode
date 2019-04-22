import math
from node import Node

class Task:

    def __init__(self, node, vx, vy, time):
        self.node = node
        self.vx = vx
        self.vy = vy
        self.time = time

    def poll(self, time):
        if (time >= self.time):
            self.node.setvx(self.vx)
            self.node.setvy(self.vy)
            return True
        else:
            return False
