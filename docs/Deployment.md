# Deployment Guide: HopeKCC on Google Cloud Platform VM

This guide provides detailed instructions for deploying HopeKCC on a Google Cloud Platform (GCP) Compute Engine VM, including SSH access and command execution, drawing from your Continuous Deployment (CD) workflow for best practices.

## 1. VM Configuration & Setup

### 1.1 Choose a VM Configuration
A Linux VM is recommended (e.g., Ubuntu 22.04 LTS). Ensure it has sufficient resources to handle PDF generation and concurrent WebSockets. For moderate use, a machine with at least **2 CPU cores** and **4 GB RAM** is recommended.

### 1.2 System Setup
Install Python 3.10+, PostgreSQL client libraries, and Git on the VM.
*   **Python 3.10+:**
    ```bash
    sudo apt update
    sudo apt install python3.10 python3.10-venv -y
    sudo apt install python3-pip -y
    ```
*   **PostgreSQL Client Libraries:**
    ```bash
    sudo apt install libpq-dev -y
    ```
*   **Git:**
    ```bash
    sudo apt install git -y
    ```

### 1.3 Environment & Secrets
Set up environment variables on the VM, particularly `DATABASE_URL` (pointing to your Cloud SQL or external Postgres instance) and `FIREBASE_JSON`.
*   **`.env` file:** Create a `.env` file in the root of your application directory (e.g., `/home/server/summer-intern-2025/server/.env`) on the VM:
    ```
    DATABASE_URL="postgresql://user:password@host:port/database"
    FIREBASE_JSON='{"type": "service_account", ...}'
    PERL5LIB = path to perl5
    # Other environment variables as needed
    ```
*   **Google Secret Manager:** For sensitive values, consider using Google Secret Manager and fetching them at runtime or injecting them into your environment variables.

## 2. SSH Access and Initial Deployment

### 2.1 Accessing the VM via SSH
You will need the IP address of your GCP VM, your username, and an SSH key.
*   **From your local machine:**
    ```bash
    ssh -i /path/to/your/private_key username@YOUR_VM_EXTERNAL_IP
    ```
    *Replace `/path/to/your/private_key` with the path to your SSH private key file, `username` with your VM user (often `ubuntu` or `your-gcp-username`), and `YOUR_VM_EXTERNAL_IP` with the public IP address of your VM.*

### 2.2 Initial Repository Clone
Once SSHed into the VM, navigate to the desired directory (e.g., `/home/server/`) and clone your repository.

```bash
# Example: Navigate to /home/server/
cd /home/server/

# Clone the repository
git clone https://github.com/hopekcc/summer-intern-2025.git

# Navigate into the server directory of your cloned repository
cd summer-intern-2025/server
```

### 2.3 Running the Setup Script (Initial Installation)
Your project might have a `setup.sh` script for initial installation. If so, execute it:

```bash
# Assuming setup.sh is in the server directory
./setup.sh
```
*Edit `setup.sh` if needed to skip certain steps or to integrate with your specific environment.*

### 2.4 Manual Setup (Alternative to `setup.sh`)
If you prefer manual setup or need to debug, follow these steps within your `server` directory:

1.  **Create and activate a Python virtual environment:**
    ```bash
    python3.10 -m venv .venvServer
    source .venvServer/bin/activate
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Initialize the database and song data:** (Refer to your project's specific commands for this, e.g., running Alembic migrations or custom data seeding scripts).
    ```bash
    # Example:
    python retrieve_songs.py
    ```

## 3. Running the Server

### 3.1 Running Uvicorn Manually (for testing/development)
```bash
source .venvServer/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080
```
*The WebSocket server runs as part of the application startup (on port 8766 by default). Ensure that port is open or forwarded if clients will connect directly, or consider reverse proxying WebSocket connections as well.*



## 4. Continuous Deployment (CD) for Updates

Leverage your GitHub Actions CD workflow to automate updates. The workflow uses `appleboy/ssh-action` to connect to the VM and execute commands within a `tmux` session.

### 4.1 GitHub Secrets
Ensure the following secrets are configured in your GitHub repository (`Settings > Secrets and variables > Actions`):
*   `VM_ACTIONS_IP`: The external IP address of your GCP VM.
*   `VM_ACTIONS_USERNAME`: The username for SSH access on the VM.
*   `VM_ACTIONS_PRIVATE_KEY`: The SSH private key corresponding to the public key authorized on your VM.

### 4.2 CD Workflow Explanation
When changes are pushed to the `main` branch within the `server/` directory, the following steps will be executed on your VM:

1.  **SSH Connection:** Connects to the VM using the provided secrets.
2.  **`cd ..`:** Navigates up one directory from the default home directory of the SSH user.
3.  **`tmux new-session -d -s server_pull -c /home/server/summer-intern-2025/server || true`:**
    *   Starts a new detached `tmux` session named `server_pull` if it doesn't already exist.
    *   The `-c /home/server/summer-intern-2025/server` ensures the session starts directly in your application's `server` directory.
    *   `|| true` prevents the workflow from failing if the session already exists.
4.  **`tmux send-keys -t server_pull 'git pull origin main' C-m`:**
    *   Sends the `git pull origin main` command to the `server_pull` tmux session, followed by `C-m` (Enter) to execute it. This fetches the latest code.
5.  **`tmux send-keys -t server_pull 'source .venvServer/bin/activate' C-m`:**
    *   Activates the Python virtual environment within the tmux session.
6.  **`tmux send-keys -t server_pull 'pip install -r requirements.txt' C-m`:**
    *   Installs any new or updated Python dependencies.


## 5. Monitoring and Verification

After deployment, monitor the logs to ensure everything starts correctly.
*   **Application Logs:** The app logs to console and also to `logs/` files if configured.
    *   If using `systemd`: `sudo journalctl -u hope-kcc -f`
    *   If running directly in `tmux`: Attach to the `tmux` session: `tmux attach -t server_pull`
*   **Test `/health/db` Endpoint:**
    Verify database connectivity from the VM by accessing your health endpoint.
    ```bash
    curl http://127.0.0.1:8080/health/db
    ```
    Expected output might be `{"status": "Database connected"}` or similar.

---
Here's a diagram illustrating the deployment architecture: 
