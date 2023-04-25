# CSEE 4119 Programming Assignment 2: Network Protocols Emulation

Done by: Yaochen Shen (ys3593)

Directory:
----
- README.md
- test.txt
- gbnnode.py
- dvnode.py
- cnnode.py

Commands for Running the Program
------

### Go-Back-N (GBN) Protocol:  
__Start the Node:__  
- <self-port>: the port number of the current node. It is between 1024 - 65535.  
- <peer-port>: the port number of the peer node. It is between 1024 - 65535.  
- <window-size>:  the size of window in GBN protocol
- [ -d <value-of-n> | -p <value-of-p> ]: either -d or -p. The square bracket and the vertical line means to choose between the two options.
-d means the GBN node will drop packets (data or ACK) in a deterministic way (for every n packets), and -p means the GBN node will drop packets with a probability of p.
```
python3 gbnnode.py <self-port> <peer-port> <window-size> [ -d <value-of-n> | -p <value-of-p> ]
```

__Send Messages to Peer Node:__
```
send <message>
```

### Distance-Vector Routing Algorithm:
__Start the Node:__  
- <local-port>: the port number of the current node. It is between 1024 - 65535.  
- <neighbor#-port>: the port number of the peer node. It is between 1024 - 65535.  
- <loss-rate-#>: the link distance to the <neighbor#-port>.
It is between 0 - 1 and represents the probability of a packet being dropped on that link.
- [last]: the indication of the last node information of the network. It is an optional arg.
Upon the input of the command with this argument, the routing message exchanges among the nodes should kick in.
```
python3 dvnode.py <local-port> <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... [last]
```
Example:
```
python3 dvnode.py 1111 2222 .1 3333 .5
python3 dvnode.py 2222 1111 .1 3333 .2 4444 .8
python3 dvnode.py 3333 1111 .5 2222 .2 4444 .5
python3 dvnode.py 4444 2222 .8 3333 .5 last
```

### Combination:
__Start the Node:__  
- <local-port>: the port number of the current node. It is between 1024 - 65535.  
- receive: the current node will be the probe receiver for the following neighbors.
- <neighbor#-port>: the port number of the peer node. It is between 1024 - 65535.  
- <loss-rate-#>: the link distance to the <neighbor#-port>.
It is between 0 - 1 and represents the probability of a packet being dropped on that link.
- send: The current node will be the probe sender for the following neighbors.
- [last]: the indication of the last node information of the network. It is an optional arg.
Upon the input of the command with this argument, the routing message exchanges among the nodes should kick in.
```
python3 cnnode.py <local-port> receive <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... <neighborM-port> <loss-rate-M> send <neighbor(M+1)-port> <neighbor(M+2)-port> ... <neighborN-port> [last]
```
Example:
```
python3 cnnode.py receive send 2222 3333 (receiving list is empty)
python3 cnnode.py 2222 receive 1111 .1 send 3333 4444
python3 cnnode.py 3333 receive 1111 .5 2222 .2 send 4444
python3 cnnode.py 4444 receive 2222 .8 3333 .5 send last (sending list is empty)
```

Project Documentation
------
Network Protocols Emulation emulates the operation of a link layer and network layer protocol in a small 
computer network. The program behaves like a single node in the network.
Several instances of nodes will be run at the same time so that they can send packets to each other as if there are links between them. 
Running as an independent node, the program implements a simple version of Go-Back-N Protocol (Link Layer) and 
the Distance-Vector Routing Algorithm (Network Layer), in order to provide reliable transmissions and efficient routing.

### Go-Back-N (GBN) Protocol: GBNNode Class
The GBNNode class is used to implement a simple version of Go-Back-N Protocol. It involves 2 ndoes: 
a sender and a receiver. The sender sends packets to the receiver through the UDP protocol. 
And GBN protocol is implemented on top of UDP on both nodes to guarantee that all packets can be successfully delivered in the correct order to the higher layers. 
To emulate an unreliable channel, the receiver or the sender drops an incoming data packet or an ACK, respectively, with a certain probability.
-  Attributes
    - self.self_port: the port number of the current node
    - self.peer_port: the port number of the peer node
    - self.window_size: the window size of the node
    - self.drop_mode: either -d or -p. d means the GBN node will drop packets (data or ACK) in a deterministic way (for every n packets), and -p means the GBN node will drop packets with a probability of p.
    - self.drop_value: the value associated with self.drop_mode
    - self.buffer: a list of tuples (seq, char). Packets are removed once it receives ack. 
    - self.buffer_queue: a list of tuples (seq, char). It is used to pop into window. 
    - self.window: a list of tuples (seq, char)
    - self.timer: the timer of the GBN protocol
    - self.rcv_base: the sequence number of the packet that the node need to receive currently
    - self.total_no_sender: the total number of acks the sender received
    - self.drop_no_sender: the total number of the dropped acks
    - self.total_no_rcver: the total number of packets the receiver received
    - self.drop_no_rcver: the total number of the dropped packets
   
- Methods
    - drop(self, pkt): determine drop the current packet/ack or not. The argument pkt is a boolean variable.
        pkt is true when we are dropping the pkt and false when we are dropping the ack.
        If the method returns true, it should drop the packet; 
        If the method returns false, it should not drop the packet. 
    - listen(self): listen incoming messages and deal with different headers, including "end", "pkt", and "ack". 
      When the header is "end", it prints out the summary with the loss rate.
      When the header is "pkt", it checks with self.rcv_base to determine whether to send ack back to the sender.
      When the header is "ack", it deals with timer, as well as removes packet in window and buffer according to ack.
      It also determines to send the message with the "end" header to the receiver or not.
    - cmd_process(self): process command input "send". It adds new packets into the buffer and the window, as well as deals with timeout. 
  
- Threads
  - listen thread: thread to listen incoming messages
  - cmd_process thread: thread to process command input "send"
  
### Distance-Vector Routing Algorithm: DVNode Class
The DVNode class is used to implement a simplified version of a routing protocol in a static network. 
It builds its routing table based on the distances to other nodes in the network. 
The class uses the Bellman-Ford algorithm to build and update the routing tables. 
And the UDP protocol is used to exchange the routing table information among the nodes in the network.
-  Attributes
    - self.self_port: the port number of the current node
    - self.dv: a diction whose key is the neighbor port and value is the distance from the current node to the neighbor node. self.dv[self_port] is set to 0.
    - self.hop: a diction whose key is the neighbor port and value is port number of the next hop for each destination
    - self.neighbors: a list of neighbor ports 
    - self.first: a boolean initialized as True. It is used to track whether this node send out self.dv at least once so this attribute would turn to False if this node has already sent out its self.dv to neighbors.

- Methods
    - add(self, neighbor, distance): add neighbor port (key) & distance (value) to self.dv, add neighbor port (key) & None (value) to self.hop, and add neighbor port to self.neighbors. 
      The argument neighbor is the neighbor port and distance is the link distance from the current node to the neighbor node.
    - listen(self): listen incoming distance vectors(dv) from neighbors and decide whether to update self.dv and self.hop or not based on the received dv.
      It also creates new thread to send the updated self.dv to neighbors.
    - send(self): send self.dv to neighbors
    - print(self): print the routing table from self.dv and self.hop
  
- Threads
  - listen thread: thread to listen incoming messages
  - send thread: thread to send self.dv to neighbors

### Combination: CNNNode Class
The CNNNode class implements both GBN and DV protocols. The GBN protocol creates reliable links, 
and the DV algorithm determines the shortest paths over these GBN links. 
The distance of each link in this class is the packet loss rate on that link calculated by the GBN protocol.
-  Attributes
    - ##

- Methods
    - ##
  
- Threads
  - listen thread: thread to listen incoming messages
  - process listen thread: thread to process the message received in the listen(self) method
  - send_probe_thread: thread to send probe to neighbors in self.send_to
  - send_dv_thread: thread to send self.dv to neighbors





