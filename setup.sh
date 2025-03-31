#!/bin/bash

# Filename: setup.sh
# Description: Builds the custom SearXNG image using Podman and starts the container.
# Prerequisites: A Bash environment (like Git Bash or WSL). Podman will be checked for,
#                and an attempt will be made to install it on common Linux distros/macOS if missing.
# Assumes 'Containerfile' and the 'searxng_config/settings.yml' file are present
# in the current directory or its subdirectories as expected by the Containerfile.

IMAGE_NAME="my-searxng-custom"
CONTAINER_NAME="searxng"
HOST_PORT="8080"
CONTAINER_PORT="8080" # SearXNG default internal port

echo "--- Checking Prerequisites ---"
# Check for Podman and attempt installation if missing
if ! command -v podman &> /dev/null; then
    echo "Podman command not found. Attempting installation..."
    INSTALL_CMD=""
    # Check for known package managers
    if command -v apt-get &> /dev/null; then # Linux - Debian/Ubuntu
        echo "Detected apt package manager (Debian/Ubuntu)."
        INSTALL_CMD="sudo apt-get update && sudo apt-get install -y podman"
    elif command -v dnf &> /dev/null; then # Linux - Fedora
        echo "Detected dnf package manager (Fedora)."
        INSTALL_CMD="sudo dnf install -y podman"
    elif command -v brew &> /dev/null; then # macOS
        echo "Detected Homebrew package manager (macOS)."
        INSTALL_CMD="brew install podman"
    elif command -v winget &> /dev/null; then # Windows
        echo "Detected winget package manager (Windows)."
        # Note: winget might require admin privileges depending on system config
        INSTALL_CMD="winget install -e --id RedHat.Podman"
    fi

    if [ -n "$INSTALL_CMD" ]; then
        echo "Running installation command: $INSTALL_CMD"
        echo "You might be prompted for your password (sudo)."
        eval $INSTALL_CMD
        if [ $? -ne 0 ]; then
            echo "Error: Podman installation failed. Please install Podman manually:"
            echo "https://podman.io/docs/installation"
            read -p "Press Enter to exit..."
            exit 1
        else
            echo "Podman installation appears successful."
            # Re-check if command is now available
            if ! command -v podman &> /dev/null; then
                 echo "Error: Podman installed but command still not found in PATH. Please check your PATH configuration."
                 read -p "Press Enter to exit..."
                 exit 1
            fi
        fi
    else
        echo "Error: Could not detect a supported package manager (apt, dnf, brew, winget)."
        echo "Please install Podman manually (https://podman.io/docs/installation) and ensure it's in your PATH."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

# Verify Podman is responsive
echo "Verifying Podman service..."
if ! podman info > /dev/null 2>&1; then
    echo "Warning: Podman command found, but the service is not responsive. Attempting to start..."
    SERVICE_STARTED=false
    # Attempt to start based on OS/environment
    if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
        echo "Attempting to start Podman service using systemctl..."
        systemctl --user start podman.socket
        # Give it a moment
        sleep 3
        if podman info > /dev/null 2>&1; then
            SERVICE_STARTED=true
        else
            # Fallback attempt for some setups
            systemctl --user start podman
            sleep 3
            if podman info > /dev/null 2>&1; then
                 SERVICE_STARTED=true
            fi
        fi
        if $SERVICE_STARTED; then
             echo "Podman service started successfully via systemctl."
        else
             echo "Failed to start Podman service via systemctl."
        fi
    elif [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "win32"* ]]; then
         # Common command for Podman Machine on macOS/Windows
         echo "Attempting to start Podman machine..."
         if podman machine start > /dev/null 2>&1; then
              echo "Podman machine start command issued. Waiting a few seconds..."
              sleep 5 # Give machine time to boot
              if podman info > /dev/null 2>&1; then
                   SERVICE_STARTED=true
                   echo "Podman service appears responsive after machine start."
              else
                   echo "Podman machine started, but service still not responsive."
              fi
         else
              echo "Command 'podman machine start' failed or is not applicable."
         fi
    else
         echo "Could not determine appropriate command to start Podman service for OSTYPE '$OSTYPE'."
    fi

    # Final check after attempting to start
    if ! $SERVICE_STARTED; then
        echo "Error: Failed to automatically start the Podman service."
        echo "Please start the Podman service/daemon manually and re-run the script."
        echo "(e.g., 'systemctl --user start podman.socket', 'podman machine start', or use Podman Desktop)"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi
echo "Podman found and responsive: $(podman --version)"

# Check for Containerfile
if [ ! -f "Containerfile" ]; then
    echo "Error: Containerfile not found in the current directory."
    read -p "Press Enter to exit..."
    exit 1
fi
echo "Containerfile found."

# Check for settings file needed by Containerfile
if [ ! -f "searxng_config/settings.yml" ]; then
    echo "Error: searxng_config/settings.yml not found."
    echo "Please ensure the configured settings.yml exists in the searxng_config subdirectory."
    read -p "Press Enter to exit..."
    exit 1
fi
echo "searxng_config/settings.yml found."


echo "--- Building Custom SearXNG Image ($IMAGE_NAME) ---"
# Build from the current directory where Containerfile is located
podman build -t "$IMAGE_NAME" .
if [ $? -ne 0 ]; then
    echo "Error building custom SearXNG image. Check build logs and file permissions."
    read -p "Press Enter to exit..."
    exit 1
fi
echo "Custom image built successfully."

echo "--- Stopping and Removing Existing '$CONTAINER_NAME' Container (if any) ---"
podman stop "$CONTAINER_NAME" > /dev/null 2>&1
podman rm "$CONTAINER_NAME" > /dev/null 2>&1
echo "Existing container stopped/removed (if present)."

echo "--- Running Custom SearXNG Container ($CONTAINER_NAME) ---"
# Run the container using the custom image, no volume mount needed for settings
podman run -d --name "$CONTAINER_NAME" -p "$HOST_PORT:$CONTAINER_PORT" "localhost/$IMAGE_NAME:latest"
if [ $? -ne 0 ]; then
    echo "Error starting SearXNG container '$CONTAINER_NAME' from image '$IMAGE_NAME'."
    echo "Check Podman logs ('podman logs $CONTAINER_NAME') or port conflicts (port $HOST_PORT)."
    read -p "Press Enter to exit..."
    exit 1
fi
echo "Container '$CONTAINER_NAME' start command issued."
sleep 5 # Give the container a moment to start

echo "--- Verifying Container Status ---"
podman ps --filter name="$CONTAINER_NAME"

echo "---"
echo "Setup complete. SearXNG container '$CONTAINER_NAME' should be running."
echo "It uses the custom image '$IMAGE_NAME' with built-in settings."
echo "Access SearXNG in your browser at: http://localhost:$HOST_PORT/"
echo "The Python agent should now be able to connect."
echo "To stop the container, run: podman stop $CONTAINER_NAME"
echo "To start it again later, run: podman start $CONTAINER_NAME"
echo "---"

# --- Optional: Start Agent ---
echo ""
echo "IMPORTANT: Before starting the agent, ensure your Local LM server"
echo "(e.g., Ollama, LM Studio) is running and accessible at the URL"
# Attempt to extract URL, handle potential errors gracefully
CONFIG_FILE="llm_web_agent/config.py"
LM_URL_LINE=$(grep LOCAL_LM_URL "$CONFIG_FILE" 2>/dev/null)
if [ -n "$LM_URL_LINE" ]; then
    CURRENT_LM_URL=$(echo "$LM_URL_LINE" | cut -d '=' -f2- | xargs)
    echo "specified in '$CONFIG_FILE' (currently: $CURRENT_LM_URL)."
else
    echo "specified in '$CONFIG_FILE'."
fi
echo ""

read -p "Start the Python agent now? [Y/n]: " start_agent
start_agent=${start_agent:-Y} # Default to Yes if Enter is pressed

if [[ "$start_agent" =~ ^[Yy]$ ]]; then
    AGENT_SCRIPT="llm_web_agent/agent.py"
    if [ ! -f "$AGENT_SCRIPT" ]; then
        echo "Error: Agent script not found at '$AGENT_SCRIPT'."
    else
        # Directly attempt to run using 'python' command
        echo "Attempting to start agent using 'python'..."
        echo "(Ensure 'python' is in your PATH and your virtual environment is active if needed)"
        echo "(Press Ctrl+C in the agent window/terminal to stop it)"

        # Run directly in the current terminal.
        # This will block until the agent exits or is stopped (Ctrl+C).
        python "$AGENT_SCRIPT"
        echo "Agent process finished."
    fi
else
    echo "Agent not started. You can run it manually later (e.g., 'python llm_web_agent/agent.py')."
fi

echo ""
# Keep the setup window open until user presses Enter
read -p "Setup script finished. Press Enter to close this window..."