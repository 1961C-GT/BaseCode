from node import Node
from task import Task
import math
import json

def stepNodes(nodeList, ts):
    for node in nodeList:
        node.step(ts)

def dumpRanges(f, nodeList, cycle):
    for nodeA in nodeList:
        for nodeB in nodeList:
            if (nodeA == nodeB or nodeA.outOfRange(nodeB)):
                continue
            f.write("Range Packet | Cycle:"
                + str(cycle) + ",	From:"
                + str(nodeA.id) + ",	To:" + str(nodeB.id) + ",	Seq:0,	Hops:2,	Range:" + str(nodeA.getDist(nodeB)) + "\n")

def dumpStatus(f, nodeList, cycle):
    for nodeA in nodeList:
        f.write("Stats Packet | Cycle:"
            + str(cycle) + ",	From:"
            + str(nodeA.id) + ",		Seq:0,	Hops:2,	Bat:4.95,	Temp:49.22,	Heading:" + str(nodeA.heading) + "\n")

def applyTasks(taskList, cycle):
    for task in taskList:
        if task.poll(cycle):
            taskList.remove(task)

if __name__ == "__main__":
    cycle = 0
    nodeList = []
    taskList = []
    numCycles = 0

    # Trail Name (input and output file names)
    trialName = "test1"

    #### Build node and task lists from json
    with open("tests/" + trialName + ".json") as json_file:
        data = json.load(json_file)
        for n in data['nodeList']:
            nodeList.append(Node(n['id'], n['x'], n['y'], n['range']))
        for t in data['taskList']:
            taskList.append(Task(nodeList[t['nodeIdx']], t['vx'], t['vy'], t['cycle']))

        numCycles = data['length']

    #### Main Loop
    with open("tests/" + trialName + ".log","w+") as f:
        while cycle <= numCycles:
            dumpStatus(f, nodeList, cycle)
            applyTasks(taskList, cycle)
            stepNodes(nodeList, 1)
            dumpRanges(f, nodeList, cycle);
            cycle += 1

        # Close the file
        f.close()
