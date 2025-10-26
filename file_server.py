import socket
import threading
import logging
import os

# --- Configuration ---
HOST = '0.0.0.0'  # Listen on all available interfaces
PORT = 50000      # Port for the file server
CHAT_FILE = "chat_log.txt"
LOG_FILE = "file_server.log"
# --- End Configuration ---

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# A lock to protect file access, preventing a 'view'
# from reading a partially written 'post'.
file_lock = threading.Lock()

def handle_client(conn, addr):
    """Handles a single client connection."""
    client_ip, client_port = addr
    logging.info(f"Accepted connection from {client_ip}:{client_port}")
    
    try:
        data = conn.recv(4096)
        if not data:
            logging.warning(f"No data received from {client_ip}:{client_port}")
            return

        command_full = data.decode().strip()
        command, *payload = command_full.split(' ', 1)
        
        if command == "VIEW":
            logging.info(f"Processing 'VIEW' from {client_ip}:{client_port}")
            with file_lock:
                if not os.path.exists(CHAT_FILE):
                    conn.sendall(b"[Chat room is empty]")
                else:
                    with open(CHAT_FILE, "r") as f:
                        content = f.read()
                        conn.sendall(content.encode() if content else b"[No messages yet]")
            logging.info(f"Sent chat log to {client_ip}:{client_port}")

        elif command == "POST":
            if not payload:
                logging.warning(f"Received 'POST' with no payload from {client_ip}:{client_port}")
                conn.sendall(b"ERROR: No message provided")
                return
                
            message_to_post = payload[0]
            logging.info(f"Processing 'POST' from {client_ip}:{client_port}: {message_to_post[:30]}...")
            
            with file_lock:
                with open(CHAT_FILE, "a") as f:
                    f.write(message_to_post + "\n")
            
            conn.sendall(b"OK: Message posted")
            logging.info(f"Appended message for {client_ip}:{client_port}")

        else:
            logging.warning(f"Unknown command '{command}' from {client_ip}:{client_port}")
            conn.sendall(b"ERROR: Unknown command")

    except Exception as e:
        logging.error(f"Error handling client {client_ip}:{client_port}: {e}")
    finally:
        conn.close()
        logging.info(f"Closed connection from {client_ip}:{client_port}")

def main():
    """Main server loop."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        logging.info(f"File server listening on {HOST}:{PORT}")
        logging.info(f"Storing chat logs in {CHAT_FILE}")

        while True:
            conn, addr = server_socket.accept()
            # Start a new thread for each client
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.name = f"Client-{addr[0]}:{addr[1]}"
            thread.start()

    except KeyboardInterrupt:
        logging.info("Server shutting down.")
    except Exception as e:
        logging.error(f"Server socket error: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()