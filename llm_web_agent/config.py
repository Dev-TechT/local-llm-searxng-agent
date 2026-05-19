"""
Configuration settings for the LLM Web Agent.
"""

import os
import sys


def get_env(name, default):
    """Return an environment override, or the default when unset or blank."""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def get_int_env(name, default):
    """Return a positive integer environment override, or fall back clearly."""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    try:
        parsed = int(value)
    except ValueError:
        print(
            f"WARNING: {name} must be a positive integer; using default {default}.",
            file=sys.stderr,
        )
        return default

    if parsed <= 0:
        print(
            f"WARNING: {name} must be a positive integer; using default {default}.",
            file=sys.stderr,
        )
        return default

    return parsed


# LM Studio API Endpoint (OpenAI-compatible)
# Ensure this matches your Local LM server (Ollama, LM Studio, Jan, etc.) configuration.
LOCAL_LM_URL = get_env(
    "LOCAL_LM_URL",
    "http://127.0.0.1:1234/v1/chat/completions",
) # Adjust port if needed (e.g., 11434 for Ollama)

# Specify the model name if required by your Local LM setup and the API endpoint.
# Example: LOCAL_LM_MODEL = "llama3:instruct" # For Ollama
# Example: LOCAL_LM_MODEL = "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF" # For LM Studio
LOCAL_LM_MODEL = get_env("LOCAL_LM_MODEL", None) # Set to None or the actual model identifier string

# Local SearxNG Instance URL
# Make sure your SearxNG instance is running and accessible at this address.
SEARXNG_URL = get_env("SEARXNG_URL", "http://127.0.0.1:8080")

# Keywords to trigger a standard web search (lowercase)
SEARCH_TRIGGER_KEYWORDS = [
    "latest", "current", "today", "recent", "news",
    "price of", "stock", "weather", "who won", "what happened",
    "define", "explain", "summary of", "search for", "find information on",
    "time", "momentan", "momentane"
]

# Keywords to trigger an image search (lowercase)
IMAGE_SEARCH_TRIGGER_KEYWORDS = [
    "image of", "images of", "picture of", "pictures of", "show me image", "show me picture"
]

# Parameters for SearxNG query (base parameters)
# 'categories' will be added dynamically for image searches
SEARXNG_PARAMS = {
    "format": "json",
    "engines": "google,bing,duckduckgo", # Adjust engines as needed
    "safesearch": "0", # 0=off, 1=moderate, 2=strict
    # "language": "en",
}

# How many search results to process and include in the context (text or image URLs)
MAX_SEARCH_RESULTS = get_int_env("MAX_SEARCH_RESULTS", 5) # Increased slightly for images

# Timeout for network requests in seconds
REQUEST_TIMEOUT = get_int_env("REQUEST_TIMEOUT", 15)

# Optional: System prompt to guide the LLM's behavior (for text responses)
SYSTEM_PROMPT = "You are a helpful assistant that can use web search results to answer questions accurately."
