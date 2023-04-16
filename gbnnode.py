import os
import random
import sys
import threading
import time
from socket import *


class GBNNode:
    def __init__(self, self_port, peer_port, window_size, drop_mode, drop_value):
        # attributes
        self.self_port = self_port
        self.peer_port = peer_port
        self.window_size = window_size
        self.drop_mode = drop_mode
        self.drop_value = drop_value
        # buffer: a list of tuples (seq, char) -> packets removed once receiving ack
        # buffer_queue: a list of tuples (seq, char) -> pop into window
        self.buffer = []
        self.buffer_queue = []
        # window: a list of tuples (seq, char)
        self.window = []
        self.timer = time.time()
        # the packet current node need to receive
        self.rcv_base = 0
        self.total_no_sender = 0
        self.drop_no_sender = 0
        self.total_no_rcver = 0
        self.drop_no_rcver = 0

        # open socket & bind the socket with port
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.self_port))

        # multi-threading
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()
        cmd_thread = threading.Thread(target=self.cmd_process)
        cmd_thread.start()

    def drop(self, pkt):
        """determine drop the current packet/ack or not:
        if true, drop; if false, not drop"""
        if self.drop_mode == '-d':
            if pkt:
                return self.total_no_rcver % self.drop_value == 0
            else:
                return self.total_no_sender % self.drop_value == 0
        else:
            return random.random() < self.drop_value

    def listen(self):
        """receiver - receive "pkt": check and send ack
        receiver - receive "end": reset rev_base, total_no_rcver, drop_no_rcver to 0, print summary
        sender - receive "ack": remove packet in window, remove packet in buffer
        """
        while True:
            buf, sender_address = self.socket.recvfrom(4096)
            buf = buf.decode()
            lines = buf.splitlines()
            header = lines[0]

            if header == "end":
                # summary
                loss_rate = self.drop_no_rcver / self.total_no_rcver * 100
                print(f"[Summary] {self.drop_no_rcver}/{self.total_no_rcver} packets discarded, loss rate = {loss_rate}%")
                self.rcv_base = 0
                self.total_no_rcver = 0
                self.drop_no_rcver = 0
            if header == "pkt":
                self.total_no_rcver += 1
                # drop
                if self.drop(True):
                # if False:
                    self.drop_no_rcver += 1
                    print(f"[{time.time()}] packet{lines[1]} {lines[2]} discarded")
                else:
                    # check with rcv_base and send ack
                    # print(f"the current packet is {int(lines[1])}")
                    # print(f"the current rcv_base is {self.rcv_base}")
                    if int(lines[1]) == self.rcv_base:
                        self.rcv_base += 1
                        print(f"[{time.time()}] packet{lines[1]} {lines[2]} received")
                        to_send = "ack" + "\n" + lines[1] + "\n" + lines[3]
                        self.socket.sendto(to_send.encode(), ('', self.peer_port))

                        if self.rcv_base == int(lines[3]):
                            print(f"[{time.time()}] ACK{lines[1]} sent")
                        else:
                            print(f"[{time.time()}] ACK{lines[1]} sent, expecting packet{self.rcv_base}")
                    else:
                        print(f"[{time.time()}] packet{lines[1]} {lines[2]} received")
                        ack_s = self.rcv_base - 1
                        to_send = "ack" + "\n" + str(ack_s) + "\n" + lines[3]
                        self.socket.sendto(to_send.encode(), ('', self.peer_port))

                        if self.rcv_base == int(lines[3]):
                            print(f"[{time.time()}] ACK{self.rcv_base - 1} sent")
                        else:
                            print(f"[{time.time()}] ACK{self.rcv_base - 1} sent, expecting packet{self.rcv_base}")

            if header == "ack":
                self.total_no_sender += 1
                # drop
                if self.drop(False):
                # if False:
                    self.drop_no_sender += 1
                    print(f"[{time.time()}] ACK{lines[1]} discarded")
                else:
                    # timer stops when ACK for first in window received
                    # remove packet in window & buffer according to ack
                    self.timer = time.time()
                    for i in range(len(self.window)):
                        w = self.window[i]
                        seq, char = w
                        if seq == int(lines[1]):
                            self.window = self.window[i + 1:]
                            break
                    for i in range(len(self.buffer)):
                        b = self.buffer[i]
                        seq, char = b
                        if seq == int(lines[1]):
                            self.buffer = self.buffer[i + 1:]
                            break

                    if int(lines[1]) + 1 == int(lines[2]):
                        to_send = "end" + "\n"
                        self.socket.sendto(to_send.encode(), ('', self.peer_port))
                        print(f"[{time.time()}] ACK{lines[1]} received")
                        # summary
                        loss_rate = self.drop_no_sender / self.total_no_sender * 100
                        print(
                            f"[Summary] {self.drop_no_sender}/{self.total_no_sender} packets discarded, loss rate = {loss_rate}%")
                    else:
                        print(f"[{time.time()}] ACK{lines[1]} received, window moves to {int(lines[1]) + 1}")

                    # print(f"the current window is {self.window}")
                    # print(f"the current buffer is {self.buffer}")

    def cmd_process(self):
        """sender: send pkt: add new pkt into window, deal with timeout"""
        while True:
            # time.sleep(0.5)
            try:
                cmd = input("node> ")
            except KeyboardInterrupt:
                os._exit(1)
            cmd = cmd.split()

            if cmd[0] == "send":
                if len(cmd) < 2:
                    print("Invalid command")
                else:
                    # reset drop_no_sender and total_no_sender to 0
                    self.drop_no_sender = 0
                    self.total_no_sender = 0
                    # packet: header(seq #) + 1 char
                    message = " ".join(cmd[1:])

                    # put all packets to buffer and buffer_queue
                    for seq, char in enumerate(message):
                        self.buffer.append((seq, char))
                        self.buffer_queue.append((seq, char))

                    # put and send packet in window
                    while len(self.window) > 0 or len(self.buffer) > 0:
                        # keep window-size of packets in window & send newly added packets
                        while len(self.window) < self.window_size and len(self.buffer_queue) > 0:
                            # timer start when first in the window sent
                            if len(self.window) == 0:
                                self.timer = time.time()

                            seq, char = self.buffer_queue.pop(0)
                            self.window.append((seq, char))
                            to_send = "pkt" + "\n" + str(seq) + "\n" + char + "\n" + str(len(message))
                            self.socket.sendto(to_send.encode(), ('', self.peer_port))
                            print(f"[{time.time()}] packet{seq} {char} sent")

                        # timeout: resent all packet in window
                        if time.time() - self.timer > 0.5:
                            seq = self.window[0][0]
                            print(f"[{time.time()}] packet{seq} timeout")
                            # timer start after first in the window sent
                            self.timer = time.time()
                            # print(self.window)
                            for w in self.window:
                                seq, char = w
                                to_send = "pkt" + "\n" + str(seq) + "\n" + char + "\n" + str(len(message))
                                self.socket.sendto(to_send.encode(), ('', self.peer_port))
                                print(f"[{time.time()}] packet{seq} {char} sent")
            else:
                print("Invalid command")


if __name__ == '__main__':
    # deal with input: python3 gbnnode.py <self-port> <peer-port> <window-size> [ -d <value-of-n> | -p <value-of-p>]
    if len(sys.argv) != 6:
        sys.exit("Please pass the right command to initiate the process.")

    try:
        port = int(sys.argv[1])
        # 1024 - 65535 are available
        if port < 1024 or port > 65535:
            sys.exit("Self port should be between 1024 - 65535.")
    except:
        sys.exit("Self port should be int.")

    try:
        port = int(sys.argv[2])
        # 1024 - 65535 are available
        if port < 1024 or port > 65535:
            sys.exit("Peer port should be between 1024 - 65535.")
    except:
        sys.exit("Peer port should be int.")

    try:
        window = int(sys.argv[3])
    except:
        sys.exit("Window size should be int.")

    self_port = int(sys.argv[1])
    peer_port = int(sys.argv[2])
    window = int(sys.argv[3])
    drop_mode = sys.argv[4]
    drop_value = sys.argv[5]

    if drop_mode == '-d':
        try:
            drop_value = int(sys.argv[5])
        except:
            sys.exit("The value of n should be int.")
    elif drop_mode == '-p':
        try:
            drop_value = float(sys.argv[5])
            if drop_value < 0 or drop_value > 1:
                sys.exit("The value of p should be between 0 - 1.")
        except:
            sys.exit("The value of p should be float.")
    else:
        sys.exit("Please specify either -d or -p.")

    # create new node
    node = GBNNode(self_port, peer_port, window, drop_mode, drop_value)


