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

        # attributes - from gbn
        # window: key - port, value - list of int (seq)
        self.window = dict()
        self.timer = time.time()
        # the packet current node need to receive
        self.rcv_base = 0
        self.timer = time.time()

        # attributes - new
        # send_to: key - port, value - [no_rcv_ack, no_sent_pkt]
        # send_from: key - port, value - loss_rate
        self.send_to = dict()
        self.send_from = dict()
        self.print_loss_timer = time.time()
        self.update_loss_timer = time.time()
        self.change = False
        self.seq_no = 0

        # open socket & bind the socket with port
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.self_port))

        # multi-threading
        listen_dv_thread = threading.Thread(target=self.listen)
        listen_dv_thread.start()

    def add_send_from(self, neighbor, loss_rate):
        """ add neighbor after receive"""
        self.dv[neighbor] = float(0)
        self.hop[neighbor] = None
        self.neighbors.add(neighbor)
        self.send_from[neighbor] = loss_rate

    def add_send_to(self, neighbor):
        """ add neighbor after send"""
        self.dv[neighbor] = float(0)
        self.hop[neighbor] = None
        self.neighbors.add(neighbor)
        self.send_to[neighbor] = [0, 0]
        self.window[neighbor] = []

    def listen(self):
        """ listen incoming dv: update dv and hop, send the updated to neighbors, send probe packets """
        while True:
            buf, sender_address = self.socket.recvfrom(4096)
            ip, sender_port = sender_address
            sender_port = int(sender_port)
            buf = buf.decode()
            lines = buf.splitlines()
            header = lines[0]

            # start new thread to process listen
            # self.process_listen(header, lines, sender_port)
            process_listen_thread = threading.Thread(target=self.process_listen, args=(header, lines, sender_port,))
            process_listen_thread.start()

    def process_listen(self, header, lines, sender_port):
        if header == 'dv':
            new_dv = json.loads(lines[1])
            print(f"[{time.time()}] Message received at Node {self.self_port} from Node {sender_port}")
            print(f"the receive dv is {new_dv}")

            # update dv and hop
            update = False
            n_dis = self.dv[sender_port]
            # print(f"the old dv in Node {self.self_port} is {self.dv}")
            # print(f"the old hop in Node {self.self_port} is {self.hop}")
            if sender_port in self.send_from:
                self.dv[sender_port] = new_dv[str(self.self_port)]

            for n in new_dv:
                if n != self.self_port:
                    int_n = int(n)
                    if int_n in self.dv:
                        new_dis = float("{:.2f}".format(Decimal(str(new_dv[n])) + Decimal(str(n_dis))))
                        # new_dis = new_dv[n] + n_dis
                        if self.dv[int_n] > new_dis and new_dis != float(0) and new_dv[n] != float(0) and n_dis != float(0):
                            update = True
                            self.dv[int_n] = new_dis
                            self.hop[int_n] = sender_port
                    else:
                        if float("{:.2f}".format(Decimal(str(new_dv[n])) + Decimal(str(n_dis)))) != float(0) and new_dv[n] != float(0) and n_dis != float(0):
                            update = True
                            # self.dv[int_n] = new_dv[n] + n_dis
                            self.dv[int_n] = float("{:.2f}".format(Decimal(str(new_dv[n])) + Decimal(str(n_dis))))
                            self.hop[int_n] = sender_port


            # print the routing table every time after a message is received
            # print(f"the new dv in Node {self.self_port} is {self.dv}")
            # print(f"the new hop in Node {self.self_port} is {self.hop}")
            self.print()

            # send probe packets
            if self.first:
                self.first = False
                # self.send_probe()
                for peer_port in self.send_to:
                    send_probe_thread = threading.Thread(target=self.send_probe, args=(peer_port,))
                    send_probe_thread.start()
                # self.send_dv()
                send_dv_thread = threading.Thread(target=self.send_dv)
                send_dv_thread.start()
                self.print_loss_timer = time.time()
                self.update_loss_timer = time.time()
            # change in dv, then send the updated information to its neighbors
            elif not self.first and update:
                # self.send_dv()
                send_dv_thread = threading.Thread(target=self.send_dv)
                send_dv_thread.start()

        elif header == 'probe':
            if random.random() < self.send_from[sender_port]:
                pass
            else:
                # send ack
                if int(lines[1]) == self.rcv_base:
                    self.rcv_base += 1
                    to_send = "ack" + "\n" + lines[1]
                    self.socket.sendto(to_send.encode(), ('', sender_port))
                else:
                    ack_s = self.rcv_base - 1
                    to_send = "ack" + "\n" + str(ack_s)
                    self.socket.sendto(to_send.encode(), ('', sender_port))

        elif header == 'ack':
            # no_rcv_ack increase by 1
            self.send_to[sender_port][0] += 1

            # process window
            self.timer = time.time()
            for p in range(len(self.window[sender_port])):
                w = self.window[sender_port][p]
                if w == int(lines[1]):
                    self.window[sender_port] = self.window[sender_port][p + 1:]
                    break

            if time.time() - self.print_loss_timer > 1:
                no_rcv_ack = self.send_to[sender_port][0]
                no_sent_pkt = self.send_to[sender_port][1]
                no_drop_pack = no_sent_pkt - no_rcv_ack
                if no_sent_pkt != 0:
                    new_loss_rate = float("{:.2f}".format(no_drop_pack / no_sent_pkt))

                    if self.dv[sender_port] != new_loss_rate and self.hop[sender_port] is None:
                        self.dv[sender_port] = new_loss_rate
                        self.change = True
                    print(
                        f"[{time.time()}] Link to {sender_port}: {no_sent_pkt} packets sent, {no_drop_pack} packets lost, loss rate {new_loss_rate}")
                    self.print_loss_timer = time.time()

            if time.time() - self.update_loss_timer > 5:
                self.update_loss_timer = time.time()
                if self.change:
                    self.change = False
                    self.send_dv()

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

    def send_dv(self):
        """ send dv to neighbors"""
        for n in self.neighbors:
            timestamp = time.time()
            to_send = "dv" + "\n" + json.dumps(self.dv) + "\n" + str(timestamp)
            self.socket.sendto(to_send.encode(), ('', n))
            print(f"[{time.time()}] Message sent from Node {self.self_port} to Node {n}")

    def send_probe(self, peer_port):
        """ send probe with Window size is always 5, Timeout is still 500ms"""
        self.update_loss_timer = time.time()
        self.print_loss_timer = time.time()

        # put and send packet in window
        while True:
            # keep window-size of packets in window & send newly added packets
            while len(self.window[peer_port]) < 5:
                # timer start when first in the window sent
                if len(self.window[peer_port]) == 0:
                    self.timer = time.time()

                self.window[peer_port].append(self.seq_no)

                to_send = "probe" + "\n" + str(self.seq_no)
                self.socket.sendto(to_send.encode(), ('', peer_port))
                self.send_to[peer_port][1] += 1
                # print(f"probe packet{self.seq_no} sent to {peer_port}")
                self.seq_no += 1

            # timeout: resent all packet in window
            if time.time() - self.timer > 0.5:
                seq = self.window[peer_port][0]
                # print(f"[{time.time()}] packet{seq} timeout")
                # timer start after first in the window sent
                self.timer = time.time()
                # print(self.window)
                for w in self.window[peer_port]:
                    seq = w
                    to_send = "probe" + "\n" + str(seq)
                    self.send_to[peer_port][1] += 1
                    self.socket.sendto(to_send.encode(), ('', peer_port))
                    # print(f"[{time.time()}] packet{seq} {char} sent")


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

        node.add_send_from(int(neighbors[2*i]), float(neighbors[2*i + 1]))

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

        node.add_send_to(int(receiver))

    # print the initial routing table
    node.print()
    if start:
        node.send_dv()
