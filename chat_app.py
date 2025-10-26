import argparse
import logging
import socket
import sys
import time
from datetime import datetime
from dme_middleware import RicartAgrawalaMutex

# --- Configuration ---
# This will be filled by argparse
SERVER_CONFIG = {}
PEER_CONFIG = {}
MY_NODE_ID = ""
MY_DME_PORT = 0
LOG_FILE = "chat_app.log"
# --- End Configuration ---

# Set up logging for the application and the middleware
# This will capture logs from BOTH modules into one file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] (%(name)s) %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout) # Also print logs to console
    ]
)
# Set the root logger
log = logging.getLogger("ChatApp")
# Optionally set middleware logger to a different level
# logging.getLogger("DME_Middleware").setLevel(logging.INFO)


def talk_to_server(request):
    """A simple helper to send a command to the file server and get a response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0) # 5 second timeout
            s.connect((SERVER_CONFIG['host'], SERVER_CONFIG['port']))
            s.sendall(request.encode())
            
            response = s.recv(4096) # Receive up to 4KB
            return response.decode()
            
    except socket.timeout:
        log.error("Connection to file server timed out.")
        return "ERROR: Server timed out"
    except ConnectionRefusedError:
        log.error(f"Connection refused by file server at {SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
        return "ERROR: Server connection refused"
    except Exception as e:
        log.error(f"Error talking to server: {e}")
        return f"ERROR: {e}"

def handle_view():
    """Handles the 'view' command. This is non-exclusive."""
    log.info("User issued 'view' command.")
    print("\nFetching chat log from server...")
    
    content = talk_to_server("VIEW")
    
    print("\n--- Chat Log ---")
    print(content)
    print("----------------\n")

def handle_post(text, dme_mutex):
    """
    Handles the 'post' command. This is EXCLUSIVE.
    It uses the DME mutex to acquire the lock before posting.
    """
    log.info(f"User issued 'post' command: {text[:30]}...")
    print("Waiting for write access (DME)...")
    
    # 1. Request Critical Section (BLOCKS)
    start_wait = time.time()
    dme_mutex.request_cs()
    wait_time = time.time() - start_wait
    
    # --- CRITICAL SECTION START ---
    log.info(f"APP: Acquired lock in {wait_time:.2f}s. Entering Critical Section.")
    print(f"Acquired lock. Posting to server...")
    
    # 2. Format message with *local* timestamp
    timestamp = datetime.now().strftime("%d %b %I:%M%p")
    formatted_message = f"{timestamp} {MY_NODE_ID}: {text}"
    
    # 3. Perform the protected action (talk to server)
    response = talk_to_server(f"POST {formatted_message}")
    print(f"Server response: {response}")
    
    # Simulate some work to make conflicts more likely during testing
    print("Holding lock for 2 seconds to simulate work...")
    time.sleep(2) 
    
    log.info("APP: Work complete. Releasing Critical Section.")
    
    # 4. Release Critical Section
    dme_mutex.release_cs()
    # --- CRITICAL SECTION END ---
    
    print("Post complete. Lock released.\n")

def main():
    """Parses args, starts the DME, and runs the main command loop."""
    parser = argparse.ArgumentParser(description="Distributed Chat Room Client")
    parser.add_argument("node_id", help="This node's unique ID (e.g., 'Joel')")
    parser.add_argument("dme_port", type=int, help="Local port for DME peer communication")
    parser.add_argument("--server", required=True, help="File server's IP and port (e.g., '1.2.3.4:50000')")
    parser.add_argument("--peer", action="append", help="A peer's ID, IP, and port (e.g., 'Jina:5.6.7.8:50001')")
    
    args = parser.parse_args()

    # Populate global configs from args
    global MY_NODE_ID, MY_DME_PORT, SERVER_CONFIG, PEER_CONFIG
    MY_NODE_ID = args.node_id
    MY_DME_PORT = args.dme_port

    try:
        s_host, s_port = args.server.split(':')
        SERVER_CONFIG = {'host': s_host, 'port': int(s_port)}
        
        if args.peer:
            for p in args.peer:
                p_id, p_host, p_port = p.split(':')
                PEER_CONFIG[p_id] = (p_host, int(p_port))
    except Exception as e:
        print(f"Error parsing arguments: {e}")
        parser.print_help()
        sys.exit(1)

    # Setup complete. Log our configuration.
    log.info(f"--- Starting Chat App for {MY_NODE_ID} ---")
    log.info(f"DME listener will run on port {MY_DME_PORT}")
    log.info(f"File Server: {SERVER_CONFIG}")
    log.info(f"Peers: {PEER_CONFIG}")
    if not PEER_CONFIG:
        log.warning("No peers specified. DME will be trivial (lock acquired instantly).")

    # 1. Initialize the DME Middleware
    # This will start its background listener thread
    dme_mutex = RicartAgrawalaMutex(MY_NODE_ID, PEER_CONFIG, MY_DME_PORT)

    print(f"\nWelcome, {MY_NODE_ID}.")
    print("Your commands are: 'view', 'post <message>', or 'exit'.")
    print(f"All logs (including DME) are in: {LOG_FILE}\n")

    # 2. Run the main user input loop
    while True:
        try:
            cmd_line = input(f"{MY_NODE_ID}_machine> ").strip()
            if not cmd_line:
                continue

            cmd, *text_parts = cmd_line.split(' ', 1)
            text = text_parts[0] if text_parts else ""

            if cmd == "view":
                handle_view()
            elif cmd == "post":
                if not text:
                    print("Usage: post <your message here>")
                else:
                    handle_post(text, dme_mutex)
            elif cmd == "exit":
                log.info("User exiting. Shutting down.")
                print("Goodbye!")
                sys.exit(0)
            else:
                print(f"Unknown command: '{cmd}'")

        except KeyboardInterrupt:
            log.info("User pressed Ctrl-C. Shutting down.")
            print("\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            log.error(f"An error occurred in the main loop: {e}")
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()