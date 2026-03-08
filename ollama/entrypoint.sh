#!/bin/bash
set -e

# Check if this is setup mode (for pulling models during build)
if [ "$OLLAMA_SETUP_MODE" = "true" ]; then
    echo "=== OLLAMA SETUP MODE ==="
    
    # Start ollama server in the background
    ollama serve &
    OLLAMA_PID=$!
    
    # Wait for ollama to be ready
    echo "Waiting for Ollama to start..."
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    until timeout 1 bash -c "echo > /dev/tcp/127.0.0.1/11434" 2>/dev/null; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "ERROR: Ollama failed to start after ${MAX_RETRIES} seconds"
            kill $OLLAMA_PID 2>/dev/null || true
            exit 1
        fi
        echo "Waiting for Ollama... (${RETRY_COUNT}/${MAX_RETRIES})"
        sleep 1
    done
    
    echo "Ollama is ready!"
    
    # Pull required models
    echo "Pulling models..."
    ollama pull phi4-mini:latest || echo "Failed to pull phi4-mini, continuing..."
    
    echo "Models downloaded successfully!"
    echo "Setup complete. Shutting down..."
    
    # Kill the background ollama server
    pkill ollama
    exit 0
else
    echo "=== STARTING OLLAMA SERVER ==="
    # Normal mode - just start the server
    exec ollama serve
fi
