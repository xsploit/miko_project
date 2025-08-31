#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Miko AI VTuber Quick Configuration Tool
Easy setup for different LLM providers
"""
import yaml
import os
from pathlib import Path

def load_config():
    """Load current config"""
    config_file = "miko_config.yaml"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    return {}

def save_config(config):
    """Save config"""
    with open("miko_config.yaml", 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print("✅ Configuration saved to miko_config.yaml")

def setup_provider():
    """Interactive provider setup"""
    config = load_config()
    
    print("🦊 Miko AI VTuber - Quick Configuration")
    print("\nAvailable LLM Providers:")
    print("1. Ollama (Local - Free)")
    print("2. OpenAI (API Key Required)")
    print("3. OpenRouter (API Key Required - Many Models)")
    print("4. Google Gemini (API Key Required)")
    print("5. Custom Provider")
    
    choice = input("\nSelect provider [1]: ").strip() or "1"
    
    if choice == "1":
        # Ollama setup
        print("\n🔧 Setting up Ollama...")
        port = input("Ollama port [11434]: ").strip() or "11434"
        model = input("Model name [hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M]: ").strip() or "hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M"
        
        config['provider'] = 'ollama'
        if 'providers' not in config:
            config['providers'] = {}
        if 'ollama' not in config['providers']:
            config['providers']['ollama'] = {}
        
        config['providers']['ollama']['base_url'] = f'http://localhost:{port}/v1'
        config['providers']['ollama']['model'] = model
        
        print(f"✅ Configured Ollama on port {port} with model {model}")
        
    elif choice == "2":
        # OpenAI setup
        print("\n🔧 Setting up OpenAI...")
        api_key = input("OpenAI API Key: ").strip()
        base_url = input("Base URL [https://api.openai.com/v1]: ").strip() or "https://api.openai.com/v1"
        model = input("Model [gpt-4o-mini]: ").strip() or "gpt-4o-mini"
        
        config['provider'] = 'openai'
        if 'providers' not in config:
            config['providers'] = {}
        if 'openai' not in config['providers']:
            config['providers']['openai'] = {}
            
        config['providers']['openai']['api_key'] = api_key
        config['providers']['openai']['base_url'] = base_url
        config['providers']['openai']['model'] = model
        
        print(f"✅ Configured OpenAI with {model}")
        
    elif choice == "3":
        # OpenRouter setup
        print("\n🔧 Setting up OpenRouter...")
        api_key = input("OpenRouter API Key: ").strip()
        model = input("Model [meta-llama/llama-3.1-8b-instruct:free]: ").strip() or "meta-llama/llama-3.1-8b-instruct:free"
        
        config['provider'] = 'openrouter'
        if 'providers' not in config:
            config['providers'] = {}
        if 'openrouter' not in config['providers']:
            config['providers']['openrouter'] = {}
            
        config['providers']['openrouter']['api_key'] = api_key
        config['providers']['openrouter']['model'] = model
        
        print(f"✅ Configured OpenRouter with {model}")
        
    elif choice == "4":
        # Gemini setup
        print("\n🔧 Setting up Google Gemini...")
        api_key = input("Google AI Studio API Key: ").strip()
        model = input("Model [gemini-1.5-flash]: ").strip() or "gemini-1.5-flash"
        
        config['provider'] = 'gemini'
        if 'providers' not in config:
            config['providers'] = {}
        if 'gemini' not in config['providers']:
            config['providers']['gemini'] = {}
            
        config['providers']['gemini']['api_key'] = api_key
        config['providers']['gemini']['model'] = model
        
        print(f"✅ Configured Gemini with {model}")
        
    elif choice == "5":
        # Custom setup
        print("\n🔧 Setting up Custom Provider...")
        name = input("Provider name: ").strip().lower()
        api_key = input("API Key: ").strip()
        base_url = input("Base URL: ").strip()
        model = input("Model name: ").strip()
        
        config['provider'] = name
        if 'providers' not in config:
            config['providers'] = {}
        if name not in config['providers']:
            config['providers'][name] = {}
            
        config['providers'][name]['api_key'] = api_key
        config['providers'][name]['base_url'] = base_url
        config['providers'][name]['model'] = model
        
        print(f"✅ Configured {name} provider")
    
    return config

def main():
    print("=" * 50)
    config = setup_provider()
    
    # Ask about TTS
    print(f"\n🔊 TTS Configuration")
    tts_port = input("TTS server port [9880]: ").strip() or "9880"
    config['tts_server_url'] = f'http://127.0.0.1:{tts_port}'
    
    # Ask about VRM
    vrm_port = input("VRM WebSocket port [8765]: ").strip() or "8765"
    config['vrm_websocket_port'] = int(vrm_port)
    
    save_config(config)
    
    print(f"\n🎯 Configuration complete!")
    print(f"📝 Edit miko_config.yaml for advanced settings")
    print(f"🚀 Run: python miko.py")
    print("=" * 50)

if __name__ == "__main__":
    main()