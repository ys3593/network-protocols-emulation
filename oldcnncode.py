import random
from decimal import *
import json
import math
import sys
import threading
import time
from socket import *


class CNNNode:
    def __init__(self, self_port):
        # attributes - from dv
        self.self_port = self_port
        self.dv = dict()
        self.dv[self_port] = float(0)
        self.hop = dict()
        self.neighbors = set()
        self.first = True

        # attributes - new
        self.send_to = []
        self.rcv_from = []
        self.display_loss_timer = time.time()
        self.update_timer = time.time()
        self.sent_count = dict()
        self.lost_count = dict()
        self.total_no_rcver = 0
        self.drop_no_rcver = 0
        self.change = False

        # attributes - from gbn
        self.window_size = 5
        # buffer: a list of tuples (seq, char) -> packets removed once receiving ack
        # buffer_queue: a list of tuples (seq, char) -> pop into window
        self.buffer = []
        self.buffer_queue = []
        # window: a list of tuples (seq, char)
        self.window = []

        # open socket & bind the socket with port
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.self_port))

        # multi-threading
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()
        send_thread = threading.Thread(target=self.send)
        send_thread.start()
        send_probe_thread = threading.Thread(target=self.send_probe)
        send_probe_thread.start()

    def add_sender(self, neighbor, distance):
        """ add port(key), distance(value) to dv
        add port(key), hop(value) to hop
        add neighbor to neighbors
        """
        self.dv[neighbor] = distance
        self.hop[neighbor] = None
        self.neighbors.add(neighbor)
        self.rcv_from.append(neighbor)

    def add_receiver(self, r):
        """ add receiver(key), loss rate(value) to send_to """
        self.dv[r] = 0
        self.hop[r] = None
        self.neighbors.add(r)
        self.send_to.append(r)

    def listen(self):
        """ listen incoming dv, update dv and hop, send the updated to neighbors, send probe packets"""
        while True:
            buf, sender_address = self.socket.recvfrom(4096)
            ip, sender_port = sender_address
            sender_port = int(sender_port)
            buf = buf.decode()
            lines = buf.splitlines()
            header = lines[0]

            if header == 'dv':
                new_dv = json.loads(lines[1])
                print(f"[{time.time()}] Message received at Node {self.self_port} from Node {sender_port}")

                # update dv and hop
                update = False
                n_dis = self.dv[sender_port]
                for n in new_dv:
                    int_n = int(n)
                    if int_n in self.dv:
                        new_dis = float(Decimal(str(new_dv[n])) + Decimal(str(n_dis)))
                        if self.dv[int_n] > new_dis:
                            update = True
                            self.dv[int_n] = new_dis
                            self.hop[int_n] = sender_port
                    else:
                        update = True
                        self.dv[int_n] = float(Decimal(str(new_dv[n])) + Decimal(str(n_dis)))
                        self.hop[int_n] = sender_port

                # print the routing table every time after a message is received
                self.print()

                # change in dv, then send the updated information to its neighbors
                if update:
                    self.send()

                # send probe packets
                if self.first:
                    self.first = False
                    self.send_probe()
                    self.send()

            elif header == 'ack':
                # calculate new loss rate and update to dv
                self.sent_count[sender_port] = int(lines[1])
                self.lost_count[sender_port] = int(lines[2])
                if self.dv[sender_port] != round(int(lines[2])/int(lines[1]), 2):
                    self.change = True
                    self.dv[sender_port] = round(int(lines[2])/int(lines[1]), 2)

                # display the loss rate for each link every 1 second
                if time.time() - self.display_loss_timer > 1:
                    self.display_loss_timer = time.time()
                    for r in self.send_to:
                        print(f"[{time.time()}] Link to {r}: {self.sent_count[r]} packets sent, {self.lost_count[r]} packets lost, loss rate {self.dv[r]}")

                # if changes and every 5 seconds, updates of distance vectors
                if (time.time() - self.update_timer > 5) and self.change:
                    self.update_timer = time.time()
                    self.change = False
                    self.send()

            elif header == 'pkt':
                self.total_no_rcver += 1
                # drop
                if random.random() < self.dv[sender_port]:
                    self.drop_no_rcver += 1
                    print(f"[{time.time()}] packet{lines[1]} {lines[2]} discarded")
                else:
                    # send ack with sent_count(self.total_no_rcver) and lost_count(self.drop_no_rcver)
                    to_send = "ack" + "\n" + str(self.total_no_rcver) + "\n" + str(self.drop_no_rcver)
                    self.socket.sendto(to_send.encode(), ('', sender_port))

    def send_probe(self):
        self.update_timer = time.time()
        self.display_loss_timer = time.time()
        cur = time.time()
        while time.time() - cur < 1:
            for r in self.send_to:
                to_send = "pkt" + "\n"
                self.socket.sendto(to_send.encode(), ('', r))

    def send(self):
        """ send dv to neighbors"""
        for n in self.neighbors:
            timestamp = time.time()
            to_send = "dv" + "\n" + json.dumps(self.dv) + "\n" + str(timestamp)
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
                    print(f"- ({dis}) -> Node {n} ; Next hop -> Node {hop}")
                else:
                    print(f"- ({dis}) -> Node {n}")


if __name__ == '__main__':
    # input: python3 cnnode.py <local-port> receive <neighbor1-port> <loss-rate-1> ... <neighborM-port> <loss-rate-M> send <neighbor(M+1)-port> <neighbor(M+2)-port> ... <neighborN-port> [last]
    start = False
    if sys.argv[-1] == 'last':
        start = True

    try:
        port = int(sys.argv[1])
        # 1024 - 65535 are available
        if port < 1024 or port > 65535:
            sys.exit("Local port should be between 1024 - 65535.")
    except:
        sys.exit("Local port should be int.")

    # create new node
    self_port = int(sys.argv[1])
    node = CNNNode(self_port)

    idx_receive = sys.argv.index('receive')
    idx_send = sys.argv.index('send')
    if (idx_send - idx_receive) % 2 == 0:
        sys.exit("Please pass the right command to initiate the process.")

    neighbors = sys.argv[(idx_receive + 1):idx_send]
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

        node.add_sender(int(neighbors[2*i]), float(neighbors[2*i + 1]))

    if start:
        receivers = sys.argv[(idx_send + 1):-1]
    else:
        receivers = sys.argv[(idx_send + 1):]
    for receiver in receivers:
        try:
            port = int(receiver)
            # 1024 - 65535 are available
            if port < 1024 or port > 65535:
                sys.exit("Receiver port should be between 1024 - 65535.")
        except:
            sys.exit("Receiver port should be int.")

        node.add_receiver(int(receiver))

    # print the initial routing table
    node.print()
    if start:
        node.send()
