Here is the updated `README.md` file.

The "Firewall Configuration" section has been modified as you requested to open the ports generally, along with a security warning about this approach.

-----

# 3-Node Distributed Chat Application

This project implements a simple distributed chat room application using a 3-node system. It demonstrates a distributed mutual exclusion (DME) algorithm to ensure that only one user can write to the shared chat log at a time.

  * **Node 1 (Server):** A simple file server that hosts the shared `chat_log.txt` file.
  * **Node 2 (Client):** A user-facing chat application that can `view` or `post` messages.
  * **Node 3 (Client):** Another user-facing chat application.

The client nodes use the **Ricart-Agrawala algorithm** to coordinate write access (`post`) among themselves, ensuring data integrity without a central lock manager.

## Files in this Project

1.  `file_server.py`

      * **Role:** The "Resource Server" (Node 1).
      * **Function:** Listens for `VIEW` and `POST` commands. It reads from or appends to the `chat_log.txt` file. It has no DME logic.

2.  `dme_middleware.py`

      * **Role:** The "Distributed Mutual Exclusion Module."
      * **Function:** This module is imported by `chat_app.py`. It contains the `RicartAgrawalaMutex` class, which handles all the complex DME logic (logical clocks, `REQUEST`/`REPLY` messages, and state management).

3.  `chat_app.py`

      * **Role:** The "Collaboration Application" (Nodes 2 & 3).
      * **Function:** This is the script users run. It provides the text-based UI for `view` and `post` commands. It calls the DME middleware (`request_cs()` and `release_cs()`) before executing a `post` command to ensure exclusive access.

-----

## Setup and Execution on 3 Servers

Follow these steps to deploy the application on three separate servers (e.g., AWS EC2 instances).

### Example Node Configuration

We will assume the following Private IP addresses for this guide. **Replace them with your own IPs. by checking ip addr show command**

  * **Node 1 (Server):** `10.0.1.10`
  * **Node 2 (Client Joel):** `10.0.1.20`
  * **Node 3 (Client Jina):** `10.0.1.30`

### 1\. Firewall Configuration (General Access)

⚠️ **Security Warning:** The following commands will open your ports to the **entire internet (`0.0.0.0/0`)**. This is simple for quick testing but is **NOT secure** for a production environment. Anyone on the internet will be able to send data to your application. For a secure setup, you should restrict access to the specific IPs of your other nodes (as shown in the previous IP-specific example).

#### On Ubuntu (using `ufw`)

Run these commands on each respective node:

  * **On Node 1 (Server):**

    ```bash
    sudo ufw allow 50000/tcp
    ```

  * **On Node 2 (Client Joel):**

    ```bash
    sudo ufw allow 50001/tcp
    ```

  * **On Node 3 (Client Jina):**

    ```bash
    sudo ufw allow 50002/tcp
    ```

  * **After running the command(s) for your node, enable `ufw`:**

    ```bash
    sudo ufw enable
    sudo ufw status
    ```

#### On CentOS (using `firewalld`)

Run these commands on each respective node:

  * **On Node 1 (Server):**
    ```bash
    sudo firewall-cmd --zone=public --add-port=50000/tcp --permanent
    ```
  * **On Node 2 (Client Joel):**
    ```bash
    sudo firewall-cmd --zone=public --add-port=50001/tcp --permanent
    ```
  * **On Node 3 (Client Jina):**
    ```bash
    sudo firewall-cmd --zone=public --add-port=50002/tcp --permanent
    ```
  * **After running the command(s) for your node, reload `firewalld`:**
    ```bash
    sudo firewall-cmd --reload
    sudo firewall-cmd --list-all
    ```

### 2\. Copy Files

  * **Node 1:** Copy `file_server.py`.
  * **Node 2 & 3:** Copy `chat_app.py` and `dme_middleware.py`.

### 3\. Run the Application

SSH into each machine in its own terminal window.

  * **Terminal 1 (On Node 1 - Server):**

    ```bash
    python3 file_server.py
    # Output: File server listening on 0.0.0.0:50000...
    ```

  * **Terminal 2 (On Node 2 - Client Joel):**

    ```bash
    python3 chat_app.py Joel 50001 --server 10.0.1.10:50000 --peer Jina:10.0.1.30:50002
    # Output: Welcome, Joel.
    # Output: Joel_machine>
    ```

  * **Terminal 3 (On Node 3 - Client Jina):**

    ```bash
    python3 chat_app.py Jina 50002 --server 10.0.1.10:50000 --peer Joel:10.0.1.20:50001
    # Output: Welcome, Jina.
    # Output: Jina_machine>
    ```

-----

## How to Test

Your 3-node system is now running\!

1.  **Basic Post/View:**

      * In Joel's terminal, type: `post Hello from Joel!`
      * In Jina's terminal, type: `view`
      * You should see Joel's message.

2.  **Test the DME (Race Condition):**

      * In Joel's terminal, type: `post This is Joel testing the lock!` (Don't press Enter yet).
      * In Jina's terminal, type: `post Jina trying to post at the same time!` (Don't press Enter yet).
      * Try to press **Enter** on both terminals at the exact same time.
      * **Observe:** You will see one user (e.g., Jina) print `Waiting for write access (DME)...` while the other user (Joel) acquires the lock, posts, and releases. As soon as Joel releases, Jina's terminal will automatically acquire the lock and post.

3.  **Check Logs:**

      * On Node 1, you can `cat chat_log.txt` to see the perfectly sequential, uncorrupted messages.
      * On Nodes 2 and 3, you can check `chat_app.log` to see the DME logs, including the crucial `DEFERRING reply to...` message, which is proof the algorithm worked.