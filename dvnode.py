from decimal import *
import json
import math
import sys
import threading
import time
from socket import *


class DVNode:
    def __init__(self, self_port):
        # attributes
        self.self_port = self_port
        self.dv = dict()
        self.dv[self_port] = 0
        self.hop = dict()
        self.neighbors = []
        self.first = True

        # open socket & bind the socket with port
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.self_port))

        # multi-threading
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()

    def add(self, neighbor, distance):
        """ add port(key), distance(value) to dv
        add port(key), hop(value) to hop
        add neighbor to neighbors
        """
        self.dv[neighbor] = distance
        self.hop[neighbor] = None
        self.neighbors.append(neighbor)

    def listen(self):
        """ listen incoming dv, update dv and hop, send the updated to neighbors"""
        while True:
            buf, sender_address = self.socket.recvfrom(4096)
            ip, sender_port = sender_address
            sender_port = int(sender_port)
            buf = buf.decode()
            lines = buf.splitlines()
            new_dv = json.loads(lines[1])
            print(f"[{time.time()}] Message received at Node {self.self_port} from Node {sender_port}")
            # print(f"the dv from Node {sender_port} is {new_dv}")

            # update dv and hop
            update = False
            n_dis = self.dv[sender_port]
            # print(f"the old dv in Node {self.self_port} is {self.dv}")
            # print(f"the old hop in Node {self.self_port} is {self.hop}")
            for n in new_dv:
                if n != self.self_port:
                    int_n = int(n)
                    if int_n in self.dv:
                        new_dis = float(Decimal(str(new_dv[n])) + Decimal(str(n_dis)))
                        # new_dis = new_dv[n] + n_dis
                        if self.dv[int_n] > new_dis:
                            update = True
                            self.dv[int_n] = new_dis
                            self.hop[int_n] = sender_port
                    else:
                        update = True
                        # self.dv[int_n] = new_dv[n] + n_dis
                        self.dv[int_n] = float(Decimal(str(new_dv[n])) + Decimal(str(n_dis)))
                        self.hop[int_n] = sender_port

            # print the routing table every time after a message is received
            # print(f"the new dv in Node {self.self_port} is {self.dv}")
            # print(f"the new hop in Node {self.self_port} is {self.hop}")
            self.print()

            # change in dv, then send the updated information to its neighbors
            if update or self.first:
                self.first = False
                send_thread = threading.Thread(target=self.send)
                send_thread.start()

    def send(self):
        """ send dv to neighbors"""
        for n in self.neighbors:
            timestamp = time.time()
            to_send = "header" + "\n" + json.dumps(self.dv) + "\n" + str(timestamp)
            self.socket.sendto(to_send.encode(), ('', n))
            print(f"[{time.time()}] Message sent from Node {self.self_port} to Node {n}")

    def print(self):
        """ print the routing table from dv and hop"""
        print(f"[{time.time()}] Node {self.self_port} Routing Table")
        for n in self.dv:
            if n != self_port:
                dis = self.dv[n]
                hop = self.hop[n]
                if hop:
                    while self.hop[hop]:
                        hop = self.hop[hop]
                    print(f"- ({dis}) -> Node {n} ; Next hop -> Node {hop}")
                else:
                    print(f"- ({dis}) -> Node {n}")


if __name__ == '__main__':
    # input: python3 dvnode.py <local-port> <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... [last]
    if len(sys.argv) < 4 or len(sys.argv) > 35:
        sys.exit("Please pass the right command to initiate the process.")

    start = False
    if len(sys.argv) % 2 == 1:
        if sys.argv[-1] == 'last':
            start = True
        else:
            sys.exit("Please pass the right command to initiate the process.")

    try:
        port = int(sys.argv[1])
        # 1024 - 65535 are available
        if port < 1024 or port > 65535:
            sys.exit("Local port should be between 1024 - 65535.")
    except:
        sys.exit("Local port should be int.")

    # create new node
    self_port = int(sys.argv[1])
    node = DVNode(self_port)

    # add neighbors and link distances
    neighbors = sys.argv[2:]
    for i in range(math.floor(len(neighbors)/2)):
        try:
            port = int(neighbors[2*i])
            # 1024 - 65535 are available
            if port < 1024 or port > 65535:
                sys.exit("Neighbor port should be between 1024 - 65535.")
        except:
            sys.exit("Neighbor port should be int.")

        try:
            rate = float(neighbors[2*i + 1])
            if rate < 0 or rate > 1:
                sys.exit("Link distance should be between 0 - 1.")
        except:
            sys.exit("Link distance should be float.")

        node.add(int(neighbors[2*i]), float(neighbors[2*i + 1]))

    # print the initial routing table
    node.print()
    if start:
        node.send()







