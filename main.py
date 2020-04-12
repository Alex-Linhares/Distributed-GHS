"""Main file for spawning processes and running experiments"""
import sys
from node import Node
from modules.utils import Edge, EdgeStatus
from multiprocessing import Process, Queue, Value, Array

input_file = sys.argv[1]
output_file = sys.argv[2]
wake_processes = int(sys.argv[3])
debug_level = sys.argv[4]


def spawn_process(node_id, name, msg_q, wake_count, mst):
    """Spawn a new process for node with given name and adjacent edges
    
    Arguments:
        node_id {Integer} -- Node Id
        name {Float} -- Fragment Name, initially zero for all
        msg_q {Multiprocessing Queue} -- Queue for the node
        wake_count {Multiprocessing Value} -- Shared value of wake count
        mst {Multiprocessing Array} -- List of edge indexes
    
    Returns:
        Bool -- Whether the MST was completed or not
    """
    global wake_processes, debug_level, outfile, edges
    node = Node(node_id, edges[node_id], name, msg_q, debug_level)

    # Wake up certain processes.
    # print(wake_count.value)
    with wake_count.get_lock():
        if wake_count.value < wake_processes:
            wake_count.value += 1
            node.wakeup()

    completed = node.start_operation()

    for edge in edges[node_id]:
        if edge.get_status() == EdgeStatus.branch:
            edge_id = edge.get_id()
            # Check and update mst in a critical section
            with mst.get_lock():
                if not mst[edge_id]:
                    outfile.write(str(edge) + '\n')
                    mst[edge_id] = True


# Read from the input file
with open(input_file) as file:
    contents = file.readlines()
contents = [x.strip() for x in contents]

num_nodes = int(contents[0])
raw_edges = []
for line in contents[1:]:
    line = line[1:-1].split(',')
    raw_edges.append(line)

# Attach a queue for each process
queues = []
for _ in range(num_nodes):
    q = Queue()
    queues.append(q)

# Form edges for each node from the given input
outfile = open(output_file, 'w')
edges = []
for _ in range(num_nodes):
    edges.append([])

edge_id = 0
for raw_edge in raw_edges:
    node1 = int(raw_edge[0])
    node2 = int(raw_edge[1])
    # Same edge_id for both edges between node1 and node2
    edge1 = Edge(edge_id, node1, node2, float(raw_edge[2]), queues[node2])
    edge2 = Edge(edge_id, node1, node2, float(raw_edge[2]), queues[node1])
    edges[node1].append(edge1)
    edges[node2].append(edge2)
    edge_id += 1

# Spawn processes for each node
wake_count = Value('i', 0)
mst = Array('b', [False] * (edge_id + 1))
processes = []
for node_id in range(num_nodes):
    p = Process(target=spawn_process,
                args=(node_id, 0, queues[node_id], wake_count, mst))
    processes.append(p)
    p.start()

# Join processes before checking the output
for p in processes:
    p.join()

mst = list(mst)
assert mst.count(1) == num_nodes - 1
print('[SUCCESS]: Completed Execution')
