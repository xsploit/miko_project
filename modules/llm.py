# -*- coding: utf-8 -*-
"""
LLM interface module for Miko AI VTuber
Provides multi-provider LLM via OpenAI-compatible API (OpenAI, OpenRouter, Gemini proxy, Ollama),
with provider params loaded from miko_config.yaml.
"""
import ollama
import os
import yaml
from openai import OpenAI


class LLMInterface:
    def __init__(self, model=None, yaml_path: str = "miko_config.yaml"):
        self.yaml_path = yaml_path
        self.yaml_config = self._load_yaml()
        
        # Determine default model
        if model is None:
            self.model = self._get_default_model()
        else:
            self.model = model
        
        print(f"🤖 LLM initialized with model: {self.model}")

    def _load_yaml(self):
        try:
            if os.path.exists(self.yaml_path):
                with open(self.yaml_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️ Failed to load YAML config: {e}")
        return {}

    def _get_default_model(self) -> str:
        try:
            provider = self.yaml_config.get('provider')
            providers = self.yaml_config.get('providers', {})
            if provider and provider in providers:
                model = providers.get(provider, {}).get('model')
                if model:
                    return model
            if 'ollama' in providers and providers['ollama'].get('model'):
                return providers['ollama']['model']
        except Exception:
            pass
        return 'hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M'
        
    def chat_streaming(self, conversation):
        """Streaming chat with Ollama - EXACT from working reference"""
        try:
            for part in ollama.chat(model=self.model, messages=conversation, stream=True):
                chunk = part['message']['content']
                yield chunk
        except Exception as e:
            print(f"LLM Streaming Error: {e}")
            yield "Sorry! Something went wrong with my brain!"
    
    def chat_complete(self, conversation):
        """Complete chat response - EXACT from working reference"""
        try:
            response = ollama.chat(model=self.model, messages=conversation, stream=False)
            return response['message']['content']
        except Exception as e:
            print(f"LLM Error: {e}")
            return "Oops! Something went wrong with my brain!"
    
    def chat_openai_compatible(self, conversation, streaming=False, provider=None):
        """
        OpenAI-compatible chat with provider-specific optimizations
        Supports all providers: OpenAI, Ollama, OpenRouter, Gemini, Custom
        """
        try:
            # Get provider config from YAML
            yaml_config = self.yaml_config or {}
            current_provider = provider or yaml_config.get('provider', 'ollama')
            provider_config = yaml_config.get('providers', {}).get(current_provider, {})
            
            # Create OpenAI-compatible client with provider settings
            client = OpenAI(
                api_key=provider_config.get('api_key', 'default'),
                base_url=provider_config.get('base_url', 'http://localhost:11434/v1')
            )
            
            # Convert conversation format if needed
            openai_messages = []
            for msg in conversation:
                if isinstance(msg.get('content'), list):
                    # Handle complex message format from reference
                    content = msg['content'][0]['text'] if msg['content'] else ""
                else:
                    content = msg.get('content', "")
                
                openai_messages.append({
                    'role': msg['role'],
                    'content': content
                })
            
            if streaming:
                return self._chat_openai_stream(client, openai_messages, provider_config)
            else:
                # Get provider-specific parameters
                params = provider_config.get('params', {})
                model = provider_config.get('model', self.model)
                
                # Base parameters for all providers
                base_params = {
                    'model': model,
                    'messages': openai_messages,
                    'temperature': params.get('temperature', 0.7),
                    'max_tokens': params.get('max_tokens', 2048),
                    'stream': False
                }
                
                # Add provider-specific parameters
                current_provider = current_provider
                
                if current_provider == 'ollama':
                    # Ollama-specific optimizations (env vars can still override)
                    extra_body = {}
                    ollama_params = {
                        'num_predict': 'OLLAMA_NUM_PREDICT',
                        'num_ctx': 'OLLAMA_NUM_CTX', 
                        'repeat_penalty': 'OLLAMA_REPEAT_PENALTY',
                        'repeat_last_n': 'OLLAMA_REPEAT_LAST_N',
                        'num_thread': 'OLLAMA_NUM_THREAD',
                        'num_gpu': 'OLLAMA_NUM_GPU',
                        'batch_size': 'OLLAMA_BATCH_SIZE',
                        'ubatch_size': 'OLLAMA_UBATCH_SIZE',
                        'n_keep': 'OLLAMA_N_KEEP'
                    }
                    
                    # Add numeric params
                    for param, env_var in ollama_params.items():
                        yaml_value = params.get(param)
                        if yaml_value is not None:
                            extra_body[param] = int(os.getenv(env_var, str(yaml_value)))
                    
                    # Add boolean params
                    bool_params = {
                        'low_vram': 'OLLAMA_LOW_VRAM',
                        'f16_kv': 'OLLAMA_F16_KV', 
                        'use_mlock': 'OLLAMA_USE_MLOCK',
                        'use_mmap': 'OLLAMA_USE_MMAP',
                        'offload_kqv': 'OLLAMA_OFFLOAD_KQV',
                        'flash_attn': 'OLLAMA_FLASH_ATTN',
                        'numa': 'OLLAMA_NUMA'
                    }
                    
                    for param, env_var in bool_params.items():
                        yaml_value = params.get(param)
                        if yaml_value is not None:
                            env_value = os.getenv(env_var, str(yaml_value)).lower()
                            extra_body[param] = env_value == "true"
                    
                    # Add string params
                    string_params = ['cache_type_k', 'cache_type_v']
                    for param in string_params:
                        yaml_value = params.get(param)
                        if yaml_value is not None:
                            env_var = f"OLLAMA_{param.upper()}"
                            extra_body[param] = os.getenv(env_var, yaml_value)
                    
                    if extra_body:
                        base_params['extra_body'] = extra_body
                        
                elif current_provider in ['openai', 'openrouter']:
                    # OpenAI/OpenRouter specific params
                    if 'top_p' in params:
                        base_params['top_p'] = params['top_p']
                    if 'frequency_penalty' in params:
                        base_params['frequency_penalty'] = params['frequency_penalty']
                    if 'presence_penalty' in params:
                        base_params['presence_penalty'] = params['presence_penalty']
                        
                elif current_provider == 'gemini':
                    # Gemini-specific params
                    if 'top_p' in params:
                        base_params['top_p'] = params['top_p']
                    if 'top_k' in params:
                        base_params['extra_body'] = {'top_k': params['top_k']}
                
                # Make the API call
                response = client.chat.completions.create(**base_params)
                
                return response.choices[0].message.content
                
        except Exception as e:
            print(f"LLM Error: {e}")
            return "Oops! Something went wrong with my brain!"
    
    def _chat_openai_stream(self, client, messages, provider_config):
        """Streaming version with provider-specific optimizations"""
        try:
            params = provider_config.get('params', {})
            model = provider_config.get('model', self.model)
            
            stream_params = {
                'model': model,
                'messages': messages,
                'stream': True,
                'temperature': params.get('temperature', 0.7),
                'max_tokens': params.get('max_tokens', 2048)
            }
            
            # Add provider-specific streaming params if needed
            if 'top_p' in params:
                stream_params['top_p'] = params['top_p']
            
            stream = client.chat.completions.create(**stream_params)
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"LLM Streaming Error: {e}")
            personality = self.config.load_personality()
            yield personality.get("error_message", "Sorry! Something went wrong with my brain!")
    
    @staticmethod
    def check_ollama():
        """Check if Ollama is running - EXACT from working reference"""
        try:
            models = ollama.list()
            print("✅ Ollama working")
            return True
        except Exception as e:
            print(f"❌ Ollama not working! Error: {e}")
            print("Make sure ollama serve is running")
            return False