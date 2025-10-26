import socket
import threading
import logging
import time

# Set up a specific logger for the middleware
log = logging.getLogger("DME_Middleware")

class RicartAgrawalaMutex:
    """
    Implements the Ricart-Agrawala Distributed Mutual Exclusion algorithm.
    This logic runs on the *client nodes*, not the server.
    """
    STATE_RELEASED = "RELEASED"
    STATE_WANTED = "WANTED"
    STATE_HELD = "HELD"

    def __init__(self, node_id, peers, my_dme_port):
        self.node_id = node_id  # e.g., "Joel"
        # peers: dict of {"node_id": ("ip", port)}
        self.peers = peers
        self.my_dme_port = my_dme_port
        
        self.logical_clock = 0
        self.clock_lock = threading.Lock()

        self.our_request = None  # Stores our (timestamp, node_id) when in WANTED or HELD
        self.replies_needed = set()
        self.replies_lock = threading.Lock()
        
        self.deferred_replies = set() # Stores peer_ids whose REQUESTs we've deferred
        self.deferred_lock = threading.Lock()

        self.state = self.STATE_RELEASED
        self.state_lock = threading.Lock()

        log.info(f"[{self.node_id}] Initialized. State: {self.state}, Clock: {self.logical_clock}")
        
        # Start the background thread to listen for DME messages
        self.listener_thread = threading.Thread(target=self._listen_for_peers, daemon=True)
        self.listener_thread.name = f"{self.node_id}-DME-Listener"
        self.listener_thread.start()

    def _listen_for_peers(self):
        """Runs in a background thread, listening for DME messages from peers."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', self.my_dme_port))
        s.listen()
        log.info(f"[{self.node_id}] DME listener started on port {self.my_dme_port}")
        
        while True:
            try:
                conn, addr = s.accept()
                threading.Thread(
                    target=self._handle_dme_message, 
                    args=(conn,), 
                    daemon=True
                ).start()
            except Exception as e:
                log.error(f"[{self.node_id}] Error in DME listener: {e}")

    def _handle_dme_message(self, conn):
        """Processes a single incoming DME message (REQUEST or REPLY)."""
        try:
            data = conn.recv(1024).decode()
            if not data:
                return
            
            msg_type, timestamp_str, sender_id = data.split('|')
            timestamp = int(timestamp_str)

            # 1. Update our logical clock
            with self.clock_lock:
                self.logical_clock = max(self.logical_clock, timestamp) + 1
                log.debug(f"[{self.node_id}] Clock updated to {self.logical_clock} from {msg_type} by {sender_id}")

            # 2. Process the message
            if msg_type == "REQUEST":
                log.info(f"[{self.node_id}] Received REQUEST from {sender_id} (T={timestamp})")
                sender_req = (timestamp, sender_id)
                
                with self.state_lock:
                    my_state = self.state
                    my_req = self.our_request
                
                # Ricart-Agrawala logic:
                # Defer if we are HELD, or if we are WANTED and our request has priority
                if (my_state == self.STATE_HELD or 
                   (my_state == self.STATE_WANTED and my_req < sender_req)):
                    
                    with self.deferred_lock:
                        self.deferred_replies.add(sender_id)
                    log.info(f"[{self.node_id}] DEFERRING reply to {sender_id} (MyState: {my_state}, MyReq: {my_req})")
                else:
                    # Send reply immediately
                    self._send_message(sender_id, "REPLY")

            elif msg_type == "REPLY":
                log.info(f"[{self.node_id}] Received REPLY from {sender_id}")
                with self.replies_lock:
                    if sender_id in self.replies_needed:
                        self.replies_needed.remove(sender_id)
                        log.info(f"[{self.node_id}] Got needed REPLY from {sender_id}. ({len(self.replies_needed)} more needed)")
                    else:
                        log.warning(f"[{self.node_id}] Got unexpected REPLY from {sender_id}")
                        
        except Exception as e:
            log.error(f"[{self.node_id}] Error handling DME message: {e}")
        finally:
            conn.close()

    def _send_message(self, target_node_id, msg_type, timestamp=None):
        """Helper to send a DME message to a specific peer."""
        if target_node_id not in self.peers:
            log.error(f"[{self.node_id}] Unknown peer: {target_node_id}")
            return

        with self.clock_lock:
            # Increment clock for *our* send event
            self.logical_clock += 1
            # Use provided timestamp (for REQUEST) or our new clock (for REPLY)
            msg_timestamp = timestamp if timestamp is not None else self.logical_clock
            
        message = f"{msg_type}|{msg_timestamp}|{self.node_id}"
        host, port = self.peers[target_node_id]
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.sendall(message.encode())
            log.debug(f"[{self.node_id}] Sent {msg_type} to {target_node_id} (T={msg_timestamp})")
        except ConnectionRefusedError:
            log.error(f"[{self.node_id}] Connection refused when sending {msg_type} to {target_node_id} at {host}:{port}")
        except Exception as e:
            log.error(f"[{self.node_id}] Error sending message to {target_node_id}: {e}")

    # --- Public API for the Application ---

    def request_cs(self):
        """
        Called by the application to request entry into the critical section.
        This function BLOCKS until access is granted.
        """
        log.info(f"[{self.node_id}] Application requesting CS...")
        
        with self.state_lock:
            self.state = self.STATE_WANTED
        
        # 1. Create our request
        with self.clock_lock:
            self.logical_clock += 1
            self.our_request = (self.logical_clock, self.node_id)
        
        with self.replies_lock:
            self.replies_needed = set(self.peers.keys())

        log.info(f"[{self.node_id}] State -> {self.state}. Broadcasting REQUEST (T={self.our_request[0]}). Need {len(self.replies_needed)} replies.")

        # 2. Broadcast REQUEST to all peers
        for peer_id in self.peers:
            # Send our specific request timestamp
            self._send_message(peer_id, "REQUEST", timestamp=self.our_request[0])

        # 3. Wait until all replies are received
        while True:
            with self.replies_lock:
                if not self.replies_needed:
                    break  # We got all replies
            time.sleep(0.1) # Poll without busy-waiting

        # 4. Access granted
        with self.state_lock:
            self.state = self.STATE_HELD
        log.info(f"[{self.node_id}] All replies received. State -> {self.state}. Entering CS.")

    def release_cs(self):
        """Called by the application when leaving the critical section."""
        log.info(f"[{self.node_id}] Application releasing CS...")
        
        with self.state_lock:
            self.state = self.STATE_RELEASED
            self.our_request = None
        
        log.info(f"[{self.node_id}] State -> {self.state}. Sending deferred replies...")
        
        # Send replies to all deferred requests
        with self.deferred_lock:
            for peer_id in self.deferred_replies:
                self._send_message(peer_id, "REPLY")
            self.deferred_replies.clear()
            
        log.info(f"[{self.node_id}] CS released.")