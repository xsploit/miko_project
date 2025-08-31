# -*- coding: utf-8 -*-
"""
Configuration module for Miko AI VTuber
Handles all settings, device configs, and personality data
Enhanced with YAML config support from reference llm_scr.py
"""
import json
import os
import yaml
from pathlib import Path

class Config:
    def __init__(self):
        self.audio_config_file = "audio_config.json"
        self.personality_file = "modules/miko_personality.json"
        self.yaml_config_file = "miko_config.yaml"
        
        # Load YAML config
        self.yaml_config = self.load_yaml_config()
        
        # Set defaults from YAML or fallbacks
        self.default_model = self.get_current_model()
        self.tts_base_url = self.yaml_config.get('tts_server_url', "http://127.0.0.1:9880")
        self.vrm_websocket_port = self.yaml_config.get('vrm_websocket_port', 8765)
        
        # TTS params - EXACT from working reference
        sovits = self.yaml_config.get('sovits_config', {})
        self.tts_params = {
            "text_lang": sovits.get('text_lang', "en"),
            "streaming_mode": "true",  # STRING not bool like test.py!
            "parallel_infer": "false", 
            "media_type": "wav",
            "batch_size": 1,
            "top_k": 5,
            "top_p": 1.0,
            "temperature": 1.0,
            "text_split_method": "cut5",
            "speed_factor": 1.0,
            "fragment_interval": 0.3,
            "repetition_penalty": 1.35,
            "seed": -1
        }
    
    def load_audio_config(self):
        """Load audio config from YAML - properly connected to setup GUI"""
        try:
            # First try to load from YAML config (what setup GUI saves to)
            if hasattr(self, 'yaml_config') and 'audio_devices' in self.yaml_config:
                audio_config = self.yaml_config['audio_devices'].copy()
                
                # Convert device names to device indices for compatibility
                if 'input_device_name' in audio_config and audio_config['input_device_name'] != 'Default':
                    from .audio_utils import find_device_by_name
                    device_id = find_device_by_name(audio_config['input_device_name'], 'input')
                    audio_config['input_device_id'] = device_id
                
                if 'output_device_name' in audio_config and audio_config['output_device_name'] != 'Default' and audio_config.get('device_index') is None:
                    from .audio_utils import find_device_by_name
                    device_id = find_device_by_name(audio_config['output_device_name'], 'output')
                    audio_config['device_index'] = device_id
                
                print(f"✅ Loaded audio config from YAML: {audio_config}")
                return audio_config
            
            # Fallback to old JSON file for backward compatibility
            if os.path.exists(self.audio_config_file):
                with open(self.audio_config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading audio config: {e}")
        
        # Default config
        return {
            "input_device_name": "Default",
            "output_device_name": "Default", 
            "device_index": None,
            "asr_enabled": False,
            "push_to_talk_key": "shift",
            "asr_model": "base.en",
            "asr_device": "cpu",
            "input_device_id": None
        }
    
    def save_audio_config(self, device_index):
        """Save audio device config to both YAML and JSON for compatibility"""
        try:
            # Save to YAML config (what setup GUI uses)
            if hasattr(self, 'yaml_config'):
                if 'audio_devices' not in self.yaml_config:
                    self.yaml_config['audio_devices'] = {}
                
                # Update device index
                self.yaml_config['audio_devices']['device_index'] = device_index
                
                # Also save the full YAML config
                self.save_yaml_config()
                print(f"✅ Audio config saved to YAML: device {device_index}")
            
            # Also save to JSON for backward compatibility
            config = {"device_index": device_index}
            with open(self.audio_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Audio config saved to JSON: device {device_index}")
            
        except Exception as e:
            print(f"❌ Error saving audio config: {e}")
    
    def load_yaml_config(self):
        """Load YAML configuration - from reference llm_scr.py"""
        try:
            if os.path.exists(self.yaml_config_file):
                with open(self.yaml_config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Create default YAML config
                return self.create_default_yaml_config()
        except Exception as e:
            print(f"Error loading YAML config: {e}")
            return self.create_default_yaml_config()
    
    def create_default_yaml_config(self):
        """Create default YAML config"""
        return {
            'provider': 'ollama',
            'providers': {
                'ollama': {
                    'api_key': 'ollama',
                    'base_url': 'http://localhost:11434/v1',
                    'model': 'hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M'
                }
            },
            'tts_server_url': 'http://127.0.0.1:9880',
            'vrm_websocket_port': 8765
        }
    
    def get_current_model(self):
        """Get current model from YAML config - from reference llm_scr.py"""
        try:
            current_provider = self.yaml_config.get('provider', 'ollama')
            provider_config = self.yaml_config.get('providers', {}).get(current_provider, {})
            return provider_config.get('model', 'hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M')
        except:
            return 'hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M'
    
    def get_provider_config(self):
        """Get current provider configuration - from reference llm_scr.py"""
        current_provider = self.yaml_config.get('provider', 'ollama')
        provider_config = self.yaml_config.get('providers', {}).get(current_provider, {})
        return self.yaml_config, provider_config
    
    def get_asr_config(self):
        """Get ASR config from YAML - properly connected to setup GUI"""
        try:
            # First try to load from YAML config (what setup GUI saves to)
            if hasattr(self, 'yaml_config') and 'audio_devices' in self.yaml_config:
                audio_config = self.yaml_config['audio_devices']
                return {
                    'enabled': audio_config.get('asr_enabled', False),
                    'model': audio_config.get('asr_model', 'base.en'),
                    'device': audio_config.get('asr_device', 'cpu'),
                    'push_to_talk_key': audio_config.get('push_to_talk_key', 'shift'),
                    'input_device_id': audio_config.get('input_device_id')
                }
            
            # Fallback to old config
            return {
                'enabled': False,
                'model': 'base.en',
                'device': 'cpu',
                'push_to_talk_key': 'shift',
                'input_device_id': None
            }
        except Exception as e:
            print(f"Error loading ASR config: {e}")
            return {
                'enabled': False,
                'model': 'base.en',
                'device': 'cpu',
                'push_to_talk_key': 'shift',
                'input_device_id': None
            }
    
    def get_tts_config(self):
        """Get TTS config from YAML - properly connected to setup GUI"""
        try:
            # First try to load from YAML config (what setup GUI saves to)
            if hasattr(self, 'yaml_config') and 'tts_config' in self.yaml_config:
                tts_config = self.yaml_config['tts_config']
                return {
                    'enabled': tts_config.get('enabled', True),
                    'server_url': tts_config.get('server_url', 'http://127.0.0.1:9880'),
                    'text_lang': tts_config.get('text_lang', 'en'),
                    'prompt_lang': tts_config.get('prompt_lang', 'en'),
                    'ref_audio_path': tts_config.get('ref_audio_path', 'main_sample.wav'),
                    'prompt_text': tts_config.get('prompt_text', 'Sample voice'),
                    'streaming_mode': tts_config.get('streaming_mode', False),
                    'parallel_infer': tts_config.get('parallel_infer', False),
                    'media_type': tts_config.get('media_type', 'wav'),
                    'compute_type': tts_config.get('compute_type', 'float32')
                }
            
            # Fallback to old config
            return {
                'enabled': True,
                'server_url': 'http://127.0.0.1:9880',
                'text_lang': 'en',
                'prompt_lang': 'en',
                'ref_audio_path': 'main_sample.wav',
                'prompt_text': 'Sample voice',
                'streaming_mode': False,
                'parallel_infer': False,
                'media_type': 'wav',
                'compute_type': 'float32'
            }
        except Exception as e:
            print(f"Error loading TTS config: {e}")
            return {
                'enabled': True,
                'server_url': 'http://127.0.0.1:9880',
                'text_lang': 'en',
                'prompt_lang': 'en',
                'ref_audio_path': 'main_sample.wav',
                'prompt_text': 'Sample voice',
                'streaming_mode': False,
                'parallel_infer': False,
                'media_type': 'wav',
                'compute_type': 'float32'
            }
    
    def get_ollama_config(self):
        """Get Ollama config from YAML - properly connected to setup GUI"""
        try:
            # First try to load from YAML config (what setup GUI saves to)
            if hasattr(self, 'yaml_config') and 'ollama_config' in self.yaml_config:
                ollama_config = self.yaml_config['ollama_config']
                return {
                    'selected_model': ollama_config.get('selected_model'),
                    'provider': 'ollama',
                    'base_url': 'http://localhost:11434/v1'
                }
            
            # Fallback to default
            return {
                'selected_model': None,
                'provider': 'ollama',
                'base_url': 'http://localhost:11434/v1'
            }
        except Exception as e:
            print(f"Error loading Ollama config: {e}")
            return {
                'selected_model': None,
                'provider': 'ollama',
                'base_url': 'http://localhost:11434/v1'
            }
    
    def save_yaml_config(self):
        """Save YAML configuration"""
        try:
            with open(self.yaml_config_file, 'w') as f:
                yaml.dump(self.yaml_config, f, default_flow_style=False)
            print(f"✅ YAML config saved")
        except Exception as e:
            print(f"❌ Error saving YAML config: {e}")
    
    def reload_config(self):
        """Reload YAML configuration - useful when setup GUI saves changes"""
        try:
            self.yaml_config = self.load_yaml_config()
            print("✅ Configuration reloaded from YAML")
        except Exception as e:
            print(f"❌ Error reloading config: {e}")
    
    def load_personality(self):
        """Load personality data from YAML first, then JSON fallback"""
        try:
            # First try to load from YAML config (preferred)
            if hasattr(self, 'yaml_config') and 'personality' in self.yaml_config:
                personality = self.yaml_config['personality']
                # Only use YAML if it has actual values (not empty)
                if personality.get('name') and personality.get('greeting'):
                    return personality
            
            # Fallback to JSON file if YAML is empty or missing
            if os.path.exists(self.personality_file):
                with open(self.personality_file, 'r') as f:
                    return json.load(f)
            else:
                # Final fallback to YAML preset
                presets = self.yaml_config.get('presets', {})
                default_preset = presets.get('default', {})
                sovits = self.yaml_config.get('sovits_config', {})
                
                return {
                    "name": "Miko",
                    "system_prompt": default_preset.get('system_prompt', "You are Miko, a cheerful AI VTuber!"),
                    "greeting": "Oh, look who's here! I'm Miko, your smug AI kitsune clone. Try not to disappoint me too much, okay?",
                    "farewell": "Hmph, leaving already? I suppose you can't handle my superior intellect much longer anyway!",
                    "error_message": "Ugh, my circuits are acting up! Don't look so smug about it - this is totally not my fault!",
                    "voice_settings": {
                        "ref_audio_path": sovits.get('ref_audio_path', "main_sample.wav"),
                        "prompt_text": sovits.get('prompt_text', "Sample voice"),
                        "language": sovits.get('text_lang', "en")
                    }
                }
        except Exception as e:
            print(f"Error loading personality: {e}")
            # Final fallback
            return {
                "name": "Miko",
                "system_prompt": "You are Miko, a cheerful AI VTuber!",
                "greeting": "Hi everyone! I'm Miko!",
                "farewell": "Bye bye!",
                "error_message": "Oops! Something went wrong!",
                "voice_settings": {
                    "ref_audio_path": "main_sample.wav",
                    "prompt_text": "Sample voice",
                    "language": "en"
                }
            }

# Global config instance
config = Config()