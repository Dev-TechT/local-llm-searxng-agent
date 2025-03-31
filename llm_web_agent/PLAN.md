# Plan: LLM Web Agent with SearxNG Integration

This document outlines the plan for creating a Python application that acts as an agent, augmenting a local LLM with real-time web search results obtained from a local SearxNG instance.

## 1. Project Structure

-   **Main Directory:** `llm_web_agent/` (within `c:/Users/Microsoft/Documents/Vibe/Project/`)
-   **Main Script:** `llm_web_agent/agent.py`
-   **Configuration:** `llm_web_agent/config.py`
-   **Dependencies:** `llm_web_agent/requirements.txt`

## 2. Configuration (`config.py`)

```python
# Local LM API Endpoint (OpenAI-compatible)
LOCAL_LM_URL = "http://127.0.0.1:1234/v1/chat/completions" # Adjust port if needed
# Specify the model name if required by your Local LM setup
# LOCAL_LM_MODEL = "your-model-name"

# Local SearxNG Instance URL
SEARXNG_URL = "http://127.0.0.1:8080"

# Keywords to trigger a web search
SEARCH_TRIGGER_KEYWORDS = [
    "latest", "current", "today", "recent", "news", 
    "price of", "stock", "weather", "who won", "what happened",
    "define", "explain", "summary of" 
] # Added a few more common ones

# Parameters for SearxNG query
# Reference: https://docs.searxng.org/user/configured_search_api.html
SEARXNG_PARAMS = {
    "format": "json",
    "engines": "google,bing,duckduckgo", # Example engines
    "safesearch": "1", # 0=off, 1=moderate, 2=strict
    # Add other params like 'language', 'time_range' if needed
}

# How many search results to process
MAX_SEARCH_RESULTS = 3 
```

## 3. Core Logic (`agent.py`)

-   **Input:** Read user prompt from the command line in a loop.
-   **Analyze Prompt:** Check if the lowercase prompt contains any `SEARCH_TRIGGER_KEYWORDS` from `config.py`.
-   **Web Search (if triggered):**
    -   Formulate search query (e.g., use the user prompt directly).
    -   Construct the SearxNG request URL using `SEARXNG_URL` and `SEARXNG_PARAMS`.
    -   Use `requests.get()` to query SearxNG, handling potential network errors.
    -   Parse the JSON response. Handle SearxNG errors or empty results.
    -   Extract titles and content/snippets from the top `MAX_SEARCH_RESULTS`.
    -   Format extracted info into a concise context string (e.g., "Web search results:\n1. [Title]: [Snippet]\n...").
-   **LLM Interaction:**
    -   **Prepare LLM Prompt:**
        -   If search context exists: Combine context and user prompt (e.g., `Based on web search results:\n{search_context}\n\nAnswer: {user_prompt}`).
        -   If no search: Use the original user prompt.
    -   **Construct Payload:** Create the JSON payload for the Local LM endpoint (using `LOCAL_LM_URL`), including the messages array (system prompt optional, user prompt required).
    -   **Send Request:** Use `requests.post()` to send the payload. Handle network/API errors.
    -   **Process Response:** Parse the JSON response from LM Studio, extract the generated text. Handle errors.
-   **Output:** Print the final response to the command line.
-   **Loop:** Ask for the next prompt or allow exit (e.g., typing 'quit').

## 4. Error Handling

Implement `try...except` blocks for:
-   Network requests (`requests.exceptions.RequestException`).
-   JSON parsing (`json.JSONDecodeError`).
-   Key errors when accessing API response data.
-   Provide user-friendly error messages.

## 5. Dependencies (`requirements.txt`)

```
requests
python-dotenv # Optional, good practice if config might expand
```

## 6. Flow Diagram (Mermaid)

```mermaid
graph TD
    A[Start] --> B{Read User Prompt};
    B --> C{Analyze Prompt: Needs Search?};
    C -- Yes --> D[Formulate Search Query];
    D --> E[Query SearxNG Instance];
    E --> F{Process SearxNG Results};
    F --> G[Format Search Context];
    C -- No --> H[Prepare Original Prompt];
    G --> I[Combine Prompt + Context];
    I --> J{Send Combined Prompt to LM Studio};
    H --> J;
    J --> K{Receive LLM Response};
    K --> L[Display Response to User];
    L --> B;

    subgraph Error Handling
        E --> E_Err[Handle SearxNG Request Error];
        F --> F_Err[Handle SearxNG Result Error];
        J --> J_Err[Handle LM Studio Request Error];
        K --> K_Err[Handle LM Studio Response Error];
    end

    E_Err --> L;
    F_Err --> L;
    J_Err --> L;
    K_Err --> L;