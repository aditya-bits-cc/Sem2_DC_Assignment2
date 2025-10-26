# Distributed Chat Application with Ricart-Agrawala Mutual Exclusion

This is a distributed chat application implementing the Ricart-Agrawala algorithm for distributed mutual exclusion. The system consists of multiple nodes that can post messages to a shared chat log while maintaining mutual exclusion for write operations.

## Components

1. **DME Middleware** (`dme_middleware.py`)
   - Implements Ricart-Agrawala distributed mutual exclusion algorithm
   - Handles peer-to-peer communication for mutual exclusion
   - Provides request_cs() and release_cs() APIs

2. **Chat Application** (`chat_app.py`)
   - Client application that users interact with
   - Integrates with DME middleware for write operations
   - Provides view and post functionality

3. **File Server** (`file_server.py`)
   - Central server that manages the shared chat log
   - Handles concurrent read/write requests
   - Maintains persistence of chat messages

## Setup and Running

### Prerequisites
- Python 3.7 or higher
- Network connectivity between nodes
- All nodes should be able to reach each other and the file server

### Running the File Server

1. Start the file server first:
```bash
python file_server.py
```
The server will listen on port 50000 by default.

### Running Chat Nodes

For this example, we'll set up three nodes: node1, node2, and node3. Each node needs:
- A unique node ID
- A unique port for DME communication
- Information about its peers
- File server address

#### Node 1 (Example IP: 192.168.1.101)
```bash
python chat_app.py node1 50001 --server 192.168.1.100:50000 --peer "node2:192.168.1.102:50002" --peer "node3:192.168.1.103:50003"
```

#### Node 2 (Example IP: 192.168.1.102)
```bash
python chat_app.py node2 50002 --server 192.168.1.100:50000 --peer "node1:192.168.1.101:50001" --peer "node3:192.168.1.103:50003"
```

#### Node 3 (Example IP: 192.168.1.103)
```bash
python chat_app.py node3 50003 --server 192.168.1.100:50000 --peer "node1:192.168.1.101:50001" --peer "node2:192.168.1.102:50002"
```

### Local Testing Setup
For testing on a single machine, use localhost (127.0.0.1) and different ports:

```bash
# Terminal 1 - File Server
python file_server.py

# Terminal 2 - Node 1
python chat_app.py node1 50001 --server 127.0.0.1:50000 --peer "node2:127.0.0.1:50002" --peer "node3:127.0.0.1:50003"

# Terminal 3 - Node 2
python chat_app.py node2 50002 --server 127.0.0.1:50000 --peer "node1:127.0.0.1:50001" --peer "node3:127.0.0.1:50003"

# Terminal 4 - Node 3
python chat_app.py node3 50003 --server 127.0.0.1:50000 --peer "node1:127.0.0.1:50001" --peer "node2:127.0.0.1:50002"
```

## Usage

### Available Commands
1. `view` - View the current chat log (non-exclusive operation)
2. `post <message>` - Post a new message (uses mutual exclusion)
3. `exit` - Exit the application

### Test Cases

#### Test Case 1: Basic Functionality
1. Start all nodes
2. From node1: `post "Hello from node1"`
3. From node2: `view` (should see node1's message)
4. From node3: `post "Hello from node3"`
5. From node1: `view` (should see both messages)

Expected Result:
- All messages should appear in order
- Each node should see the same chat log

#### Test Case 2: Concurrent Posts
1. Try to post from multiple nodes simultaneously:
   - Node1: `post "Message 1 from node1"`
   - Node2: `post "Message 2 from node2"` (immediately after node1)
   - Node3: `post "Message 3 from node3"` (immediately after node2)

Expected Result:
- Messages should appear in some sequential order
- No messages should be lost or corrupted
- The 2-second artificial delay helps observe the mutual exclusion

#### Test Case 3: Node Failure Recovery
1. Start all nodes
2. Post some messages from each node
3. Stop node2 (Ctrl+C)
4. Continue posting from node1 and node3
5. Restart node2 with the same configuration

Expected Result:
- System should continue functioning for remaining nodes
- Restarted node should rejoin successfully
- All nodes should maintain consistency

#### Test Case 4: Read During Write
1. From node1: Start posting a long message
2. While node1 is waiting for mutex:
   - From node2: Execute `view` command several times
   - From node3: Try to post another message

Expected Result:
- View commands should work without blocking
- Post commands should be serialized
- No corruption of the chat log

## Logging and Debugging

- Each component maintains its own log file:
  - `chat_app.log` - Chat application logs
  - `file_server.log` - File server logs
  - `chat_log.txt` - The actual chat messages

- Log files contain detailed information about:
  - DME algorithm operation
  - Message exchanges
  - Critical section entry/exit
  - Errors and exceptions

## Implementation Details

### Ricart-Agrawala Algorithm Implementation
- Uses logical clocks for message ordering
- Maintains FIFO message ordering
- Implements proper thread synchronization
- Handles network failures gracefully

### Mutual Exclusion Properties
1. Safety: Only one node can be in the critical section at a time
2. Liveness: Requests for critical section eventually succeed
3. Ordering: Requests are served in the order of their timestamps

## Troubleshooting

1. **Connection Refused Errors**
   - Check if all nodes are running
   - Verify IP addresses and ports
   - Ensure no firewall blocking

2. **Messages Not Appearing**
   - Check file server logs
   - Verify network connectivity
   - Check chat_log.txt permissions

3. **Node Not Responding**
   - Check node's log file
   - Verify peer configuration
   - Restart the node if needed