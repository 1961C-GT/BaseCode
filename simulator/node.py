import math

class Node:

    def getDist(self, nodeB):
        distm = math.sqrt(math.pow((nodeB.x - self.x),2) + math.pow((nodeB.y - self.y),2))
        return math.floor(distm * 1000)

    def outOfRange(self, nodeB):
        distm = math.sqrt(math.pow((nodeB.x - self.x),2) + math.pow((nodeB.y - self.y),2))
        return (distm > self.range)

    def __init__(self, id, x, y, range):
        self.range = range
        self.x = x
        self.y = y
        self.id = id

        self.vx = 0
        self.vy = 0
        self.cycle = 0
        self.heading = 0

    def setvx(self, vx):
        self.vx = vx

    def setvy(self, vy):
        self.vy = vy

    def step(self, ts):
        self.x += self.vx * ts
        self.y += self.vy * ts
        # if (self.vx is not 0 or self.vy is not 0):
        self.heading = math.degrees(math.atan2(self.vx,self.vy))

        self.cycle += 1
