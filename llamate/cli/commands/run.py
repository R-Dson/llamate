"""Run command implementation."""
import sys
import requests
import json

from ...core import config
from ... import constants

from ...core import config

def run_command(args) -> None:
    """Run a model in interactive chat mode."""
    # Resolve alias if exists
    resolved_name = config.resolve_alias(args.model_name)
    model_name = resolved_name or args.model_name
    
    global_config = config.load_global_config()
    
    listen_port = global_config.get("llama_swap_listen_port", constants.LLAMA_SWAP_DEFAULT_PORT)
    api_url = f"http://localhost:{listen_port}/v1/chat/completions"

    messages = []
    print(f"Starting conversation with model: {model_name}")
    print("Type '/bye' or 'exit' to end the conversation.")

    while True:
        try:
            user_message = input(">>> User: ")
            if user_message.lower() in ["/bye", "exit"]:
                print("Ending conversation.")
                break

            messages.append({"role": "user", "content": user_message})

            payload = {
                "model": model_name,
                "messages": messages,
                "stream": True
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer no-key"
            }

            assistant_response_content = ""
            with requests.post(api_url, headers=headers, json=payload, stream=True) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
                print("<<< Assistant: ", end="", flush=True)
                for chunk in response.iter_content(chunk_size=None):
                    if chunk:
                        try:
                            # Decode chunk as string, then parse JSON
                            chunk_str = chunk.decode('utf-8')
                            for line in chunk_str.splitlines():
                                if line.strip().startswith("data:"):
                                    json_data = json.loads(line.strip()[len("data:"):])
                                    if "choices" in json_data and len(json_data["choices"]) > 0:
                                        delta = json_data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            assistant_response_content += content
                                            print(content, end="", flush=True)
                        except json.JSONDecodeError:
                            # Handle cases where a chunk might not be a complete JSON line
                            pass
                print() # Newline after assistant response

            # Always append the assistant's response, even if empty
            messages.append({"role": "assistant", "content": assistant_response_content})

        except requests.exceptions.ConnectionError:
            print(f"Error: Could not connect to the llama-swap server at {api_url}.", file=sys.stderr)
            print("Please ensure 'llamate serve' is running.", file=sys.stderr)
            break
        except requests.exceptions.RequestException as e:
            print(f"Error during API request: {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            break