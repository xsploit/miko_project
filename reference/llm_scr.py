# OpenAI tool calling with history 
### Uses a sample function
import yaml
import gradio as gr
import json
import os
from pathlib import Path
from openai import OpenAI

# Get the project root directory (3 levels up from this file)
project_root = Path(__file__).parent.parent.parent.parent
config_path = project_root / 'character_config.yaml'

def load_config():
    """Load config fresh each time"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_provider_config():
    """Get current provider configuration"""
    char_config = load_config()
    current_provider = char_config['provider']
    provider_config = char_config['providers'][current_provider]
    return char_config, provider_config

# For backward compatibility - export current config (but this loads fresh each call)
char_config, provider_config = get_provider_config()

# Constants
HISTORY_FILE = project_root / char_config['history_file']
MODEL = provider_config['model']
SYSTEM_PROMPT =  [
        {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": char_config['presets']['default']['system_prompt']  
                }
            ]
        }
    ]

# Load/save chat history
def load_history():
    char_config, _ = get_provider_config()
    HISTORY_FILE = project_root / char_config['history_file']
    SYSTEM_PROMPT = [{"role": "system", "content": [{"type": "input_text", "text": char_config['presets']['default']['system_prompt']}]}]
    
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return SYSTEM_PROMPT

def save_history(history):
    char_config, _ = get_provider_config()
    HISTORY_FILE = project_root / char_config['history_file']
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)



def get_riko_response_no_tool(messages, client, model):

    # Convert to OpenAI-compatible format
    openai_messages = []
    for msg in messages:
        if msg['role'] == 'system':
            openai_messages.append({
                'role': 'system',
                'content': msg['content'][0]['text']
            })
        elif msg['role'] == 'user':
            openai_messages.append({
                'role': 'user', 
                'content': msg['content'][0]['text']
            })
        elif msg['role'] == 'assistant':
            openai_messages.append({
                'role': 'assistant',
                'content': msg['content'][0]['text']
            })
    
    # Call OpenAI-compatible API with Ollama optimizations
    response = client.chat.completions.create(
        model=model,
        messages=openai_messages,
        temperature=0.7,
        top_p=0.9,
        max_tokens=2048,
        stream=False,
        # Ollama performance optimizations with environment variable support
        extra_body={
            "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "2048")),
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "32768")),
            "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1")),
            "repeat_last_n": int(os.getenv("OLLAMA_REPEAT_LAST_N", "64")),
            "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "-1")),  # Use all available threads
            "num_gpu": int(os.getenv("OLLAMA_NUM_GPU", "-1")),     # Use all available GPU layers
            "low_vram": os.getenv("OLLAMA_LOW_VRAM", "false").lower() == "true",
            "f16_kv": os.getenv("OLLAMA_F16_KV", "true").lower() == "true",
            "use_mlock": os.getenv("OLLAMA_USE_MLOCK", "true").lower() == "true",
            "use_mmap": os.getenv("OLLAMA_USE_MMAP", "true").lower() == "true",
            # KV cache optimizations
            "cache_type_k": os.getenv("OLLAMA_CACHE_TYPE_K", "f16"),
            "cache_type_v": os.getenv("OLLAMA_CACHE_TYPE_V", "f16"), 
            "offload_kqv": os.getenv("OLLAMA_OFFLOAD_KQV", "true").lower() == "true",
            "flash_attn": os.getenv("OLLAMA_FLASH_ATTN", "true").lower() == "true",
            # Additional performance optimizations
            "numa": os.getenv("OLLAMA_NUMA", "true").lower() == "true",
            "batch_size": int(os.getenv("OLLAMA_BATCH_SIZE", "512")),
            "ubatch_size": int(os.getenv("OLLAMA_UBATCH_SIZE", "512")),
            "n_keep": int(os.getenv("OLLAMA_N_KEEP", "-1")),
            "logits_all": os.getenv("OLLAMA_LOGITS_ALL", "false").lower() == "true",
            "embedding": os.getenv("OLLAMA_EMBEDDING", "false").lower() == "true",
            "penalize_nl": os.getenv("OLLAMA_PENALIZE_NL", "false").lower() == "true"
        }
    )

    return response


def llm_response(user_input, streaming=False):
    # Load fresh config each time
    char_config, provider_config = get_provider_config()
    
    # Create client with fresh config
    client = OpenAI(
        api_key=provider_config['api_key'],
        base_url=provider_config['base_url']
    )

    messages = load_history()
    
    # Debug: Print current history length
    print(f"📚 Current history length: {len(messages)} messages")
    
    # Limit history to prevent context overflow and repetition
    MAX_HISTORY = 20  # Keep last 20 messages (10 exchanges)
    if len(messages) > MAX_HISTORY:
        # Keep system prompt and last MAX_HISTORY-1 messages
        system_msg = messages[0] if messages and messages[0].get('role') == 'system' else None
        recent_messages = messages[-(MAX_HISTORY-1):] if system_msg else messages[-MAX_HISTORY:]
        
        if system_msg:
            messages = [system_msg] + recent_messages
        else:
            messages = recent_messages
        
        print(f"🔄 Trimmed history to {len(messages)} messages")

    # Append user message to memory
    messages.append({
        "role": "user",
        "content": [
            {"type": "input_text", "text": user_input}
        ]
    })

    # Debug: Print the last few messages being sent
    print(f"🤖 Sending {len(messages)} messages to LLM")
    
    try:
        if streaming:
            # Return streaming generator
            return llm_response_stream(messages, client, provider_config['model'])
        else:
            riko_test_response = get_riko_response_no_tool(messages, client, provider_config['model'])
            response_text = riko_test_response.choices[0].message.content
            
            # Debug: Print response length
            print(f"📝 Generated response: {len(response_text)} characters")
            
            # just append assistant message to regular response. 
            messages.append({
            "role": "assistant",
            "content": [
                {"type": "output_text", "text": response_text}
            ]
            })

            save_history(messages)
            return response_text
        
    except Exception as e:
        print(f"❌ LLM Generation Error: {e}")
        return "Sorry senpai, I'm having trouble thinking right now. Maybe try asking something else?"

def llm_response_stream(messages, client, model):
    """Generator for streaming LLM response"""
    try:
        # Convert message format for OpenAI API
        openai_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                openai_messages.append({
                    "role": "system", 
                    "content": msg['content'][0]['text']
                })
            elif msg['role'] == 'user':
                openai_messages.append({
                    "role": "user",
                    "content": msg['content'][0]['text']
                })
            elif msg['role'] == 'assistant':
                openai_messages.append({
                    "role": "assistant",
                    "content": msg['content'][0]['text']
                })
        
        # Create streaming response
        stream = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            stream=True,
            temperature=0.7,
            max_tokens=2048
        )
        
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content
        
        # Save complete response to history
        messages.append({
            "role": "assistant",
            "content": [
                {"type": "output_text", "text": full_response}
            ]
        })
        save_history(messages)
        
    except Exception as e:
        print(f"❌ LLM Streaming Error: {e}")
        yield "Sorry senpai, I'm having trouble thinking right now. Maybe try asking something else?"


if __name__ == "__main__":
    print('running main')