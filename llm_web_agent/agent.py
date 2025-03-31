import requests
import json
from urllib.parse import urlencode, quote_plus, urljoin
import sys
import os
import re
import time
import threading

# Attempt to import configuration, handle potential import error
try:
    import config
except ImportError:
    print("ERROR: config.py not found. Please ensure it exists in the same directory.")
    sys.exit(1)

# --- Helper Function Enums/Constants ---
class SearchType:
    NONE = 0
    TEXT = 1
    IMAGE = 2

# --- Helper Functions ---

def get_search_type(prompt: str) -> SearchType:
    """Checks if the prompt contains trigger keywords for text or image search."""
    if not prompt:
        return SearchType.NONE
    prompt_lower = prompt.lower()
    # Check for image keywords first
    for keyword in config.IMAGE_SEARCH_TRIGGER_KEYWORDS:
        if keyword in prompt_lower:
            # print(f"--- Image search keyword '{keyword}' found. ---") # Hide log
            return SearchType.IMAGE
    # Then check for standard text search keywords
    for keyword in config.SEARCH_TRIGGER_KEYWORDS:
        if keyword in prompt_lower:
            # print(f"--- Text search keyword '{keyword}' found. ---") # Hide log
            return SearchType.TEXT
    return SearchType.NONE

def perform_searxng_search(query: str, search_type: SearchType) -> tuple[str | None, list[str] | None]:
    """
    Queries the SearxNG instance.
    Returns (text_context, image_urls)
    """
    # print(f"--- Searching SearxNG ({'Image' if search_type == SearchType.IMAGE else 'Text'}) for: {query} ---") # Hide log
    text_context = None
    image_urls = None

    try:
        base_url = config.SEARXNG_URL
        if not base_url.endswith('/'):
            base_url += '/'

        search_path = "search"
        query_params = {"q": query, **config.SEARXNG_PARAMS}

        # Add category for image search
        if search_type == SearchType.IMAGE:
            query_params["categories"] = "images"

        encoded_params = urlencode(query_params)
        search_url = urljoin(base_url, search_path) + "?" + encoded_params
        # print(f"--- Querying URL: {search_url} ---") # Hide log

        response = requests.get(search_url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        results = response.json()

        if "results" in results and results["results"]:
            if search_type == SearchType.IMAGE:
                image_urls = []
                # print("--- Image search successful. Found results. ---") # Hide log
                for i, result in enumerate(results["results"][:config.MAX_SEARCH_RESULTS]):
                    img_src = result.get("img_src")
                    if img_src:
                        # Try to construct absolute URL if relative
                        if img_src.startswith('/'):
                            img_src = urljoin(config.SEARXNG_URL, img_src) # Use base URL of SearxNG if needed, though often external
                        image_urls.append(img_src)
            else: # Text search
                text_context = "Web search results:\n"
                # print("--- Text search successful. Found results. ---") # Hide log
                for i, result in enumerate(results["results"][:config.MAX_SEARCH_RESULTS]):
                    title = result.get("title", "No Title")
                    content = result.get("content", result.get("snippet", "No Content"))
                    url = result.get("url", "No URL")
                    content_cleaned = ' '.join(content.split()) if content else "N/A"
                    text_context += f"{i+1}. Title: {title}\n   Content: {content_cleaned}\n   URL: {url}\n"
                text_context = text_context.strip()
        else:
            print("--- SearxNG returned no results or unexpected format. ---")
            print(f"SearxNG Response: {results}")

    except requests.exceptions.Timeout:
        print(f"ERROR: Request to SearxNG timed out ({config.REQUEST_TIMEOUT}s).")
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 403:
             print(f"ERROR: SearxNG returned 403 Forbidden. Check SearxNG's settings.yml for API restrictions.")
             print(f"Attempted URL: {search_url}")
        else:
            print(f"ERROR: Could not connect to or query SearxNG at {config.SEARXNG_URL}. Error: {e}")
    except json.JSONDecodeError:
        print("ERROR: Failed to decode JSON response from SearxNG.")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during SearxNG search: {e}")

    return text_context, image_urls


def remove_think_tags(text: str) -> str:
    """Removes <think>...</think> blocks from text."""
    if not text:
        return ""
    # Make regex case-insensitive and allow whitespace in tags
    return re.sub(r'<think\s*>.*?</think\s*>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
def query_local_lm(prompt: str, search_context: str | None, history: list[dict]) -> str | None:
    """Sends the prompt (potentially with search context and history) to the Local LM."""
    final_prompt = prompt
    if search_context:
        # Integrate search context into the *current* user message, not replacing it entirely
        final_prompt = f"Based on the following web search results:\n{search_context}\n\nUser question: {prompt}"

    headers = {"Content-Type": "application/json"}
    # Construct messages: System Prompt -> History -> Current User Prompt
    messages = []
    if config.SYSTEM_PROMPT:
        messages.append({"role": "system", "content": config.SYSTEM_PROMPT})
    messages.extend(history) # Add previous turns
    messages.append({"role": "user", "content": final_prompt}) # Add current turn

    # Corrected payload definition
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000, # Adjust as needed
        "stream": False
    }
    # Conditionally add model if specified in config
    if config.LOCAL_LM_MODEL:
        payload["model"] = config.LOCAL_LM_MODEL

    local_lm_timeout = 300 # Consider making this configurable
    try:
        response = requests.post(
            config.LOCAL_LM_URL,
            headers=headers,
            json=payload,
            timeout=local_lm_timeout
        )
        response.raise_for_status()
        result = response.json()

        if "choices" in result and result["choices"]:
            message = result["choices"][0].get("message")
            if message and "content" in message:
                raw_content = message["content"].strip()
                cleaned_content = remove_think_tags(raw_content)
                return cleaned_content
            else:
                 print("ERROR: Unexpected response structure from LM Studio (missing message content).")
                 print(f"LM Studio Raw Response: {result}")
                 return None
        else:
            print("ERROR: Unexpected response structure from LM Studio (missing choices).")
            print(f"LM Studio Raw Response: {result}")
            return None

    except requests.exceptions.Timeout:
        print(f"\nERROR: Request to Local LM timed out ({local_lm_timeout}s).")
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Could not connect to Local LM at {config.LOCAL_LM_URL}. Error: {e}")
    except json.JSONDecodeError:
        print("\nERROR: Failed to decode JSON response from LM Studio.")
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred during LM Studio query: {e}")

    return None

# --- Waiting Animation ---
def animate_waiting(stop_event):
    """Displays a simple waiting animation."""
    animation = ["   ", ".  ", ".. ", "..."]
    idx = 0
    while not stop_event.is_set():
        print(f"\rWaiting for LLM {animation[idx % len(animation)]}", end="")
        idx += 1
        time.sleep(0.3)
    print("\r" + " " * 30 + "\r", end="")


# --- Main Application Logic ---

def main():
    """Main loop to get user input and process it."""
    print("LLM Web Agent Initialized. Type 'quit' or 'exit' to end.")
    print("-" * 30)

    conversation_history = [] # Initialize conversation history

    while True:
        try:
            user_prompt = input("You: ")
            if user_prompt.lower() in ["quit", "exit"]:
                break
            if not user_prompt:
                continue

            search_type = get_search_type(user_prompt)
            text_search_context = None
            image_urls = None
            llm_response = None

            if search_type != SearchType.NONE:
                text_search_context, image_urls = perform_searxng_search(user_prompt, search_type)

            if search_type == SearchType.IMAGE:
                if image_urls:
                    print("\nFound Image URLs:")
                    print("-" * 15)
                    for url in image_urls:
                        print(url)
                    print("-" * 15 + "\n")
                else:
                    print("\nNo images found for your query.\n")
                # Skip LLM for image searches
                continue # Go to next prompt

            # --- Process Text Search or No Search ---
            stop_indicator = threading.Event()
            indicator_thread = threading.Thread(target=animate_waiting, args=(stop_indicator,))
            # print("--- Querying LM Studio... ---") # Hide log
            indicator_thread.start()

            try:
                # Pass text context (if any) and history to LLM
                llm_response = query_local_lm(user_prompt, text_search_context, conversation_history)
            finally:
                stop_indicator.set()
                indicator_thread.join()

            print("\nLLM Response:")
            print("-" * 15)
            if llm_response:
                print(llm_response)
                # Add the current exchange to history
                conversation_history.append({"role": "user", "content": user_prompt})
                conversation_history.append({"role": "assistant", "content": llm_response})
            else:
                print("Failed to get a response or process the request.")
            print("-" * 15 + "\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
             print("\nExiting...")
             break

if __name__ == "__main__":
    if not config.LOCAL_LM_URL or not config.SEARXNG_URL:
        print("ERROR: LOCAL_LM_URL or SEARXNG_URL is not set in config.py.")
        sys.exit(1)
    main()