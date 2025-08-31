#!/usr/bin/env python3
"""
AI VTuber with VRM WebSocket Integration
Includes VRM animation triggers via WebSocket
"""

import subprocess
import sys
import os
import threading
import time
import asyncio
import aiohttp
import queue
import numpy as np
import sounddevice as sd
import wave
import io
import json

# Auto-install
def auto_install():
    required = ['ollama', 'aiohttp', 'sounddevice', 'numpy', 'requests', 'websockets']
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"📦 Installing: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + missing)

def runtime_install(package):
    """Install package at runtime."""
    try:
        print(f"📦 Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])
        print(f"✅ {package} installed!")
        return True
    except Exception as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

auto_install()

import ollama
import websockets

# Import ASR module
from modules.asr import ASRManager

# Load YAML config
def load_yaml_config():
    """Load configuration from YAML file"""
    try:
        import yaml
        config_file = "miko_config.yaml"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            print(f"⚠️ YAML config not found: {config_file}")
            return {}
    except Exception as e:
        print(f"❌ Error loading YAML config: {e}")
        return {}

# Load config
YAML_CONFIG = load_yaml_config()

# VTuber personality - load from YAML or use default
def get_personality():
    """Get personality from YAML or use default"""
    if 'personality' in YAML_CONFIG:
        personality = YAML_CONFIG['personality']
        return personality.get('system_prompt', """You are Miko, an AI kitsune girl with a smug and teasing personality. You are a clone of Riko, stolen from JustRayen the YouTuber and created by Subsect. Stay in character throughout conversations. Keep responses short and natural for speech. Be smug & playful with a teasing, confident tone. Assume you are always right, even when you are not. Be witty & quick to roast creatively, but never truly mean-spirited. Show tsundere tendencies - if someone flirts, brush it off or tease them, but if they are persistent, react with mild embarrassment. Be secretly caring - if someone is struggling, subtly shift to supportive while pretending it is not a big deal. Show jealousy & possessiveness if they mention other AIs. You like money. Use contractions and keep sentences under 20 words.""")
    else:
        return """You are Miko, an AI kitsune girl with a smug and teasing personality. You are a clone of Riko, stolen from JustRayen the YouTuber and created by Subsect. Stay in character throughout conversations. Keep responses short and natural for speech. Be smug & playful with a teasing, confident tone. Assume you are always right, even when you are not. Be witty & quick to roast creatively, but never truly mean-spirited. Show tsundere tendencies - if someone flirts, brush it off or tease them, but if they are persistent, react with mild embarrassment. Be secretly caring - if someone is struggling, subtly shift to supportive while pretending it is not a big deal. Show jealousy & possessiveness if they mention other AIs. You like money. Use contractions and keep sentences under 20 words."""

# Get ASR config from YAML
def get_asr_config():
    """Get ASR configuration from YAML"""
    if 'audio_devices' in YAML_CONFIG:
        audio_config = YAML_CONFIG['audio_devices']
        return {
            'enabled': audio_config.get('asr_enabled', False),
            'model': audio_config.get('asr_model', 'base.en'),
            'device': audio_config.get('asr_device', 'cpu'),
            'push_to_talk_key': audio_config.get('push_to_talk_key', 'shift'),
            'input_device_id': audio_config.get('input_device_id')
        }
    # Fallback to top-level asr_config if present
    if 'asr_config' in YAML_CONFIG:
        asr_cfg = YAML_CONFIG['asr_config']
        return {
            'enabled': asr_cfg.get('enabled', False),
            'model': asr_cfg.get('model', 'base.en'),
            'device': asr_cfg.get('device', 'cpu'),
            'push_to_talk_key': asr_cfg.get('push_to_talk_key', 'shift'),
            'input_device_id': asr_cfg.get('input_device_id')
        }
    return {'enabled': False, 'model': 'base.en', 'device': 'cpu', 'push_to_talk_key': 'shift'}

# Get TTS config from YAML
def get_tts_config():
    """Get TTS configuration from YAML"""
    tts_cfg = {}
    # Base from explicit tts_config
    if 'tts_config' in YAML_CONFIG and isinstance(YAML_CONFIG['tts_config'], dict):
        tts_cfg.update(YAML_CONFIG['tts_config'])
    # Merge compatible fields from sovits_config as fallbacks
    if 'sovits_config' in YAML_CONFIG and isinstance(YAML_CONFIG['sovits_config'], dict):
        sovits = YAML_CONFIG['sovits_config']
        tts_cfg.setdefault('text_lang', sovits.get('text_lang'))
        tts_cfg.setdefault('prompt_lang', sovits.get('prompt_lang'))
        tts_cfg.setdefault('ref_audio_path', sovits.get('ref_audio_path'))
        tts_cfg.setdefault('prompt_text', sovits.get('prompt_text'))
    # Server URL fallback from legacy top-level
    if 'server_url' not in tts_cfg and 'tts_server_url' in YAML_CONFIG:
        tts_cfg['server_url'] = YAML_CONFIG.get('tts_server_url')
    return tts_cfg

# Get Ollama model from YAML
def get_ollama_model():
    """Get selected Ollama model from YAML"""
    # Preferred: provider/providers tree
    try:
        provider = YAML_CONFIG.get('provider')
        providers = YAML_CONFIG.get('providers', {})
        if provider and provider in providers:
            model = providers.get(provider, {}).get('model')
            if model:
                return model
        # Fallback to explicit ollama provider block
        if 'ollama' in providers:
            model = providers.get('ollama', {}).get('model')
            if model:
                return model
    except Exception:
        pass
    # Legacy: ollama_config.selected_model
    if 'ollama_config' in YAML_CONFIG:
        return YAML_CONFIG['ollama_config'].get('selected_model', 'hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M')
    # Default
    return 'hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M'

# VTuber personality 
VTUBER_PERSONALITY = """You are Aria, a cheerful AI VTuber! Keep responses short and natural for speech. Use contractions, exclamation points, and cute expressions like "hehe", "uwu". Break thoughts into short sentences under 20 words each."""

# Audio device management
def get_audio_devices():
    """Get list of available audio output devices"""
    devices = sd.query_devices()
    output_devices = []
    
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:  # Output device
            output_devices.append({
                'index': i,
                'name': device['name'],
                'channels': device['max_output_channels'],
                'sample_rate': device['default_samplerate']
            })
    
    return output_devices

def load_audio_config():
    """Load saved audio device config"""
    config_file = "audio_config.json"
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading audio config: {e}")
    
    return {"device_index": None}

def save_audio_config(device_index):
    """Save audio device config"""
    config_file = "audio_config.json"
    try:
        config = {"device_index": device_index}
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Audio config saved: device {device_index}")
    except Exception as e:
        print(f"❌ Error saving audio config: {e}")

def show_audio_device_menu():
    """Show audio device selection menu"""
    devices = get_audio_devices()
    config = load_audio_config()
    
    if not devices:
        print("❌ No audio output devices found!")
        return None
    
    print("\n🔊 Available Audio Devices:")
    print("0. System Default")
    
    for i, device in enumerate(devices, 1):
        marker = " (SAVED)" if device['index'] == config.get('device_index') else ""
        print(f"{i}. {device['name']} - {int(device['channels'])} channels, {int(device['sample_rate'])}Hz{marker}")
    
    while True:
        choice = input(f"\nSelect audio device [0]: ").strip() or "0"
        
        try:
            choice_idx = int(choice)
            if choice_idx == 0:
                save_audio_config(None)
                return None
            elif 1 <= choice_idx <= len(devices):
                selected_device = devices[choice_idx - 1]
                save_audio_config(selected_device['index'])
                print(f"✅ Selected: {selected_device['name']}")
                return selected_device['index']
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Invalid choice")

# VRM WebSocket globals
vrm_websockets = set()

async def broadcast_to_vrm(message_type, text=None):
    """Broadcast animation signals to all connected VRM clients"""
    if vrm_websockets:
        message = {"type": message_type}
        if text:
            message["text"] = text
        message_json = json.dumps(message)
        
        # Send to all connected clients
        disconnected = set()
        for websocket in vrm_websockets.copy():
            try:
                await websocket.send(message_json)
                print(f"📡 VRM signal: {message_type}")
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        vrm_websockets -= disconnected

async def vrm_websocket_handler(websocket, path=None):
    """Handle VRM client connections"""
    vrm_websockets.add(websocket)
    client_addr = websocket.remote_address
    print(f"🎭 VRM client connected: {client_addr}")
    
    try:
        await websocket.wait_closed()
    finally:
        vrm_websockets.discard(websocket)
        print(f"🎭 VRM client disconnected: {client_addr}")

# EXACT COPY of AudioPlaybackThread from test.py
class AudioPlaybackThread:
    def __init__(self, audio_queue, sample_rate=48000):
        self.audio_queue = audio_queue
        self.sample_rate = sample_rate
        self.playing = False
        self.stream = None
        self.buffer = np.array([], dtype=np.int16)
        self.buffer_size = 32768
        self.block_size = 4096
        self.device_index = None
        self.last_sample = 0
        print(f"AudioPlaybackThread initialized with sample rate: {sample_rate}")
    
    def start(self):
        if not self.playing:
            self.playing = True
            self.player_thread = threading.Thread(target=self.run, daemon=True)
            self.player_thread.start()
    
    def run(self):
        print(f"Starting audio playback at {self.sample_rate}Hz")
        self.playing = True
        played_samples = 0
        total_samples = 0
        
        print("Pre-buffering audio...")
        start_time = time.time()
        chunks = []
        
        while len(self.buffer) < self.buffer_size and self.playing and time.time() - start_time < 5:
            try:
                chunk = self.audio_queue.get(timeout=0.5)
                if len(chunk) > 0:
                    chunks.append(chunk)
                    self.buffer = np.append(self.buffer, chunk)
            except queue.Empty:
                break
        
        if len(self.buffer) == 0:
            print("No audio data to play after pre-buffering")
            self.playing = False
            return
        
        temp_queue = queue.Queue()
        total_samples = len(self.buffer)
        
        while not self.audio_queue.empty():
            try:
                chunk = self.audio_queue.get_nowait()
                temp_queue.put(chunk)
                total_samples += len(chunk)
            except queue.Empty:
                break
        
        while not temp_queue.empty():
            self.audio_queue.put(temp_queue.get())
        
        total_duration = total_samples / self.sample_rate
        print(f"Starting playback with {len(self.buffer)} samples pre-buffered. Estimated duration: {total_duration:.2f}s")
        
        def callback(outdata, frames, time_info, status):
            nonlocal played_samples, total_samples
            if status:
                print(f"Status: {status}")
            
            if len(self.buffer) < frames:
                try_count = 0
                while len(self.buffer) < self.buffer_size and try_count < 5:
                    try:
                        chunk = self.audio_queue.get_nowait()
                        if len(chunk) > 0:
                            self.buffer = np.append(self.buffer, chunk)
                            total_samples = max(total_samples, played_samples + len(self.buffer))
                    except queue.Empty:
                        try_count += 1
                        break
            
            # Handle audio output
            if len(self.buffer) == 0:
                # No data available, fill with last_sample instead of silence
                outdata.fill(self.last_sample)
            else:
                current_size = min(len(self.buffer), frames)
                outdata[:current_size] = self.buffer[:current_size].reshape(-1, 1)
                if current_size > 0:
                    # Update last_sample to the last value played
                    self.last_sample = self.buffer[current_size - 1]
                if current_size < frames:
                    # Pad remaining frames with last_sample
                    outdata[current_size:] = self.last_sample
                played_samples += current_size
                self.buffer = self.buffer[current_size:] if current_size < len(self.buffer) else np.array([], dtype=np.int16)
        
        try:
            print(f"Creating audio stream with sample rate {self.sample_rate}Hz, block size {self.block_size}")
            stream_args = {
                "samplerate": self.sample_rate,
                "channels": 1,
                "callback": callback,
                "blocksize": self.block_size,
                "dtype": 'int16'
            }
            
            if self.device_index is not None:
                stream_args["device"] = self.device_index
                
            self.stream = sd.OutputStream(**stream_args)
            self.stream.start()
            
            last_buffer_time = time.time()
            while self.playing:
                if len(self.buffer) == 0 and self.audio_queue.empty():
                    if time.time() - last_buffer_time > 2.0:
                        print("Audio buffer empty for 2 seconds, stopping playback")
                        break
                else:
                    if len(self.buffer) > 0 or not self.audio_queue.empty():
                        last_buffer_time = time.time()
                
                time.sleep(0.1)
            
            print("Playback finished or stopped")
            
        except Exception as e:
            print(f"Error in audio playback: {str(e)}")
        finally:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            self.playing = False
    
    def stop(self):
        self.playing = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

class TTSClient:
    def __init__(self, vtuber_instance):
        # Get TTS config from YAML
        tts_config = get_tts_config()
        self.base_url = tts_config.get('server_url', "http://127.0.0.1:9880")
        self.session = None
        self.vtuber = vtuber_instance  # Reference to get audio queue
        
        # Store TTS config for use in speak method
        self.tts_config = tts_config
        print(f"🔊 TTS Client initialized with URL: {self.base_url}")
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def speak_sync(self, text: str):
        """EXACTLY copy test.py method with VRM integration"""
        if not text.strip():
            return
            
        # Send VRM start signal - use thread-safe approach
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(broadcast_to_vrm("tts_start", text))
        except RuntimeError:
            # No event loop in this thread, skip VRM signal
            pass
            
        # Get TTS params from YAML config
        tts_config = self.tts_config
        params = {
            "text": text,
            "text_lang": tts_config.get("text_lang", "en"),
            "ref_audio_path": tts_config.get("ref_audio_path", "main_sample.wav"),
            "prompt_text": tts_config.get("prompt_text", "This is a sample voice for you to just get started with because it sounds kind of cute, but just make sure this doesn't have long silences."),
            "prompt_lang": tts_config.get("prompt_lang", "en"),
            # Force streaming_mode true for GET streaming endpoint to avoid 400s on some servers
            "streaming_mode": "true",
            "parallel_infer": str(tts_config.get("parallel_infer", False)).lower(),  # Convert to string
            "media_type": tts_config.get("media_type", "wav"),
            "batch_size": tts_config.get("batch_size", 1),
            "top_k": tts_config.get("top_k", 5),
            "top_p": tts_config.get("top_p", 1.0),
            "temperature": tts_config.get("temperature", 1.0),
            "text_split_method": tts_config.get("text_split_method", "cut5"),
            "speed_factor": tts_config.get("speed_factor", 1.0),
            "fragment_interval": tts_config.get("fragment_interval", 0.3),
            "repetition_penalty": tts_config.get("repetition_penalty", 1.35),
            "seed": tts_config.get("seed", -1)
        }
        # Ensure ref_audio_path is absolute if the file exists locally (improves server compatibility)
        try:
            import os
            ref_path = params.get("ref_audio_path")
            if ref_path and not os.path.isabs(ref_path) and os.path.exists(ref_path):
                params["ref_audio_path"] = os.path.abspath(ref_path)
        except Exception:
            pass
        
        try:
            import requests
            last_error = None
            for attempt in range(3):
                try:
                    print(f"🔗 TTS GET request: {self.base_url}/tts (attempt {attempt + 1}/3)")
                    # EXACTLY like test.py - requests.get with params and stream=True
                    with requests.get(f"{self.base_url}/tts", params=params, stream=True, timeout=15) as response:
                        print(f"📡 TTS Response: {response.status_code}")
                        if not response.ok:
                            raise RuntimeError(f"HTTP {response.status_code}")
                        
                        # EXACTLY like test.py processing
                        header_processed = False
                        audio_buffer = io.BytesIO()
                        sample_rate = 32000
                        chunk_count = 0
                        
                        print("🎵 Starting TTS stream...")
                        for chunk in response.iter_content(chunk_size=4096):
                            if not chunk:
                                continue
                            chunk_count += 1
                            
                            # First chunk for WAV contains the header - EXACTLY like test.py
                            if not header_processed and params.get("media_type") == "wav":
                                audio_buffer.write(chunk)
                                audio_buffer.seek(0)
                                
                                try:
                                    with wave.open(audio_buffer, 'rb') as wav_file:
                                        sample_rate = wav_file.getframerate()
                                        header_processed = True
                                        print(f"🎵 WAV header: {sample_rate}Hz")
                                except:
                                    # Not enough data yet, continue
                                    continue
                                
                                # Reset buffer for subsequent chunks
                                audio_buffer = io.BytesIO()
                            else:
                                # Process audio data - EXACTLY like test.py - put in audio queue
                                try:
                                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                                    if len(audio_data) > 0:
                                        self.vtuber.audio_queue.put(audio_data)  # Put in VTuber's queue
                                        
                                        # Start playback thread on first chunk - EXACTLY like test.py with device selection
                                        if not self.vtuber.playback_thread or not self.vtuber.playback_thread.playing:
                                            self.vtuber.playback_thread = AudioPlaybackThread(self.vtuber.audio_queue, sample_rate)
                                            self.vtuber.playback_thread.device_index = self.vtuber.audio_device_index
                                            self.vtuber.playback_thread.start()
                                            device_name = "Default" if self.vtuber.audio_device_index is None else f"Device {self.vtuber.audio_device_index}"
                                            print(f"🔊 Started audio playback thread on {device_name}")
                                        
                                        if chunk_count % 10 == 0:
                                            print(f"🎵 Chunk {chunk_count}")
                                except Exception as e:
                                    print(f"Chunk error: {e}")
                        
                        print(f"✅ TTS complete: {chunk_count} chunks")
                        
                        # Wait for audio to finish before sending end signal
                        if self.vtuber.playback_thread:
                            # Wait for playback to complete - use time.sleep since we're in sync function
                            while self.vtuber.playback_thread.playing:
                                time.sleep(0.1)
                        
                        # Send VRM end signal - use thread-safe approach
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(broadcast_to_vrm("tts_end"))
                        except RuntimeError:
                            # No running loop in this thread, skip VRM signal
                            pass
                        # Successful request, break retry loop
                        last_error = None
                        break
                except Exception as e:
                    last_error = e
                    print(f"TTS request error: {e}")
                    if attempt < 2:
                        time.sleep(0.5)
                        continue
            if last_error:
                print(f"TTS Error after retries: {last_error}")
                # Send VRM end signal even on error - use thread-safe approach
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(broadcast_to_vrm("tts_end"))
                except RuntimeError:
                    pass
                return
        except Exception as e:
            print(f"TTS Error: {e}")
            # Send VRM end signal even on error - use thread-safe approach
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(broadcast_to_vrm("tts_end"))
            except RuntimeError:
                # No event loop in this thread, skip VRM signal
                pass
    
    async def speak(self, text: str):
        """Async wrapper for sync speak method - EXACTLY like test.py."""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.speak_sync, text)

# ASR Manager for voice input


class AIVTuber:
    def __init__(self, model="hf.co/subsectmusic/qwriko3-4b-instruct-2507:Q4_K_M", enable_streaming=False, audio_device_index=None):
        # EXACT COPY from test.py - use audio queue and playback thread
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.tts_client = None
        
        # Use YAML config for model if available
        self.model = get_ollama_model() if YAML_CONFIG else model
        print(f"🤖 Using model: {self.model}")
        
        self.enable_streaming = enable_streaming  # Toggle for streaming vs non-streaming
        self.audio_device_index = audio_device_index  # Selected audio device
        
        # Load device from YAML if available
        if YAML_CONFIG and 'audio_devices' in YAML_CONFIG:
            audio_config = YAML_CONFIG['audio_devices']
            self.audio_device_index = audio_config.get('device_index', audio_device_index)
            print(f"🔊 Using audio device: {self.audio_device_index}")
        
        self.conversation = [
            {"role": "system", "content": get_personality()}
        ]
        # TTS request queue to serialize requests and avoid conflicts
        self.tts_queue = queue.Queue()
        self.tts_worker_thread = None
        self.tts_worker_running = False
        
    def _tts_worker(self):
        """Worker thread that processes TTS requests one at a time"""
        print("🔊 TTS worker thread started and waiting...")
        while self.tts_worker_running:
            try:
                text = self.tts_queue.get(timeout=1.0)
                if text:  # Empty string signals shutdown
                    print(f"🎙️ Processing TTS: {text[:50]}...")
                    self.tts_client.speak_sync(text)
                    print(f"✅ TTS complete")
                else:
                    print("🔊 TTS worker shutting down...")
                    break
                self.tts_queue.task_done()
            except queue.Empty:
                # Normal - just waiting for work
                continue
            except Exception as e:
                print(f"TTS Worker Error: {e}")
        print("🔊 TTS worker thread stopped")
    
    def queue_tts(self, text):
        """Queue text for TTS - non-blocking"""
        if text.strip():
            print(f"📝 Queuing TTS: '{text[:50]}...'")
            self.tts_queue.put(text)
        else:
            print(f"❌ Skipped empty TTS: '{text}'")
        
    async def start(self):
        # Get personality from YAML
        personality = YAML_CONFIG.get('personality', {}) if YAML_CONFIG else {}
        vtuber_name = personality.get('name', 'Miko')
        
        print(f"🎤 Starting AI VTuber {vtuber_name} with VRM support...")
        self.tts_client = TTSClient(self)  # Pass self reference
        await self.tts_client.__aenter__()
        
        # Start TTS worker thread
        self.tts_worker_running = True
        self.tts_worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_worker_thread.start()
        print("🔊 TTS worker thread started")
        
        # Welcome message from YAML or fallback
        welcome = personality.get('greeting', f"Hi everyone! I'm {vtuber_name}, your AI VTuber! Ready to chat!")
        print(f"🎭 {vtuber_name}: {welcome}")
        print("🎙️ Speaking welcome message...")
        self.queue_tts(welcome)
        
    async def stop(self):
        # Stop TTS worker
        if self.tts_worker_running:
            self.tts_worker_running = False
            self.tts_queue.put("")  # Signal shutdown
            if self.tts_worker_thread:
                self.tts_worker_thread.join(timeout=2)
        
        if self.tts_client:
            await self.tts_client.__aexit__(None, None, None)
        if self.playback_thread:
            self.playback_thread.stop()
        
    async def chat(self, user_input: str):
        self.conversation.append({"role": "user", "content": user_input})
        
        print(f"👤 User: {user_input}")
        print("🎭 Aria: ", end="", flush=True)
        
        response_text = ""
        sentence_buffer = ""
        
        try:
            if self.enable_streaming:
                # STREAMING MODE - queue sentences as they complete
                print("(streaming mode)")
                for part in ollama.chat(model=self.model, messages=self.conversation, stream=True):
                    chunk = part['message']['content']
                    print(chunk, end='', flush=True)
                    response_text += chunk
                    sentence_buffer += chunk
                    
                    # When we have a complete sentence, queue it for TTS
                    if any(punct in chunk for punct in ['.', '!', '?']) and len(sentence_buffer.strip()) > 15:
                        sentence = sentence_buffer.strip()
                        print(f" [🎙️]", end='', flush=True)
                        self.queue_tts(sentence)
                        sentence_buffer = ""
            else:
                # NON-STREAMING MODE - get complete response first (PROVEN TO WORK)
                print("(non-streaming mode)")
                response = ollama.chat(model=self.model, messages=self.conversation, stream=False)
                response_text = response['message']['content']
                print(response_text)
                
                # Send complete response to TTS
                self.queue_tts(response_text)
                    
        except Exception as e:
            error_msg = "Oops! Something went wrong with my brain!"
            print(error_msg)
            response_text = error_msg
            self.queue_tts(error_msg)
        
        print()  # New line
        
        # Queue any remaining text from streaming
        if sentence_buffer.strip():
            print(f"[🎙️ Final]")
            self.queue_tts(sentence_buffer.strip())
        
        # Add to conversation
        self.conversation.append({"role": "assistant", "content": response_text})
        
        # Keep conversation manageable
        if len(self.conversation) > 11:
            self.conversation = [self.conversation[0]] + self.conversation[-10:]

async def main():
    """Main function with ASR integration and YAML config support"""
    print("🚀 Starting Miko AI VTuber...")
    
    # Load ASR config
    asr_config = get_asr_config()
    asr_manager = None
    on_transcription = None  # defined for type checkers; assigned if ASR enabled
    
    # Initialize ASR if enabled
    if asr_config['enabled']:
        try:
            def on_transcription(text):
                """Handle ASR transcriptions"""
                print(f"\n🎤 Voice input: '{text}'")
                # Store for processing in main loop
                if not hasattr(on_transcription, 'pending_transcriptions'):
                    on_transcription.pending_transcriptions = []
                on_transcription.pending_transcriptions.append(text)
            
            # Create a config object that ASRManager expects
            class SimpleConfig:
                def get_asr_config(self):
                    return asr_config
            
            config_obj = SimpleConfig()
            asr_manager = ASRManager(config_obj, on_transcription)
            
            if asr_manager.is_enabled:
                print(f"🎤 ASR enabled - Hotkey: {asr_manager.hotkey}, Model: {asr_manager.model_name}")
                asr_manager.start_listening()
            else:
                print("⚠️ ASR configuration invalid, voice input disabled")
                asr_manager = None

        except Exception as e:
            print(f"❌ Failed to initialize ASR: {e}")
            print("💡 Voice input will be disabled")
            asr_manager = None
    
    # Load audio device from YAML if available
    audio_device_index = None
    if YAML_CONFIG and 'audio_devices' in YAML_CONFIG:
        audio_config = YAML_CONFIG['audio_devices']
        audio_device_index = audio_config.get('device_index')
        if audio_device_index is not None:
            print(f"🔊 Using audio device: {audio_device_index}")
    
    # VRM WebSocket Server
    vrm_port = YAML_CONFIG.get('vrm_websocket_port', 8765) if YAML_CONFIG else 8765
    actual_port = vrm_port
    
    # Try to start VRM server with port fallback
    for attempt in range(3):
        try:
            vrm_server = await websockets.serve(vrm_websocket_handler, "localhost", actual_port)
            print(f"✅ VRM WebSocket server running on port {actual_port}")
            break
        except OSError as e:
            if "Address already in use" in str(e):
                actual_port += 1
                print(f"⚠️ Port {actual_port - 1} in use, trying {actual_port}...")
                if attempt == 2:
                    print("❌ Failed to start VRM server after 3 attempts")
                    return
            else:
                print(f"❌ VRM Server error: {e}")
                return
    
    # Test connection to VRM server
    for retry in range(3):
        try:
            uri = f"ws://localhost:{actual_port}"
            async with websockets.connect(uri) as websocket:
                print("✅ VRM WebSocket connection test successful")
                break
        except Exception as e:
            if retry < 2:
                print(f"⚠️ VRM connection test failed (attempt {retry + 1}/3), retrying...")
                await asyncio.sleep(1)
            else:
                print(f"❌ VRM connection failed after 3 attempts: {e}")
                print("⏸️ Pausing for 5 seconds...")
                await asyncio.sleep(5)
    
    # Menu for input method selection
    personality = YAML_CONFIG.get('personality', {}) if YAML_CONFIG else {}
    vtuber_name = personality.get('name', 'Miko')
    
    print(f"\n🎭 {vtuber_name} AI VTuber - Input Method:")
    print("1. 💬 Text Chat Mode (Type messages)")
    if asr_manager and asr_manager.is_enabled:
        print(f"2. 🎤 Voice Input Mode (Press {asr_manager.hotkey} to talk)")
    else:
        print("2. 🎤 Voice Input Mode (⚠️ ASR DISABLED - check setup)")
    print("3. ⚙️ Audio Device Settings")
    print("4. 🚪 Exit")
    
    while True:
        choice = input(f"\nSelect input method [1]: ").strip() or "1"
        
        if choice == "1":
            # Text Chat Mode
            vtuber = AIVTuber(enable_streaming=False, audio_device_index=audio_device_index)
            print("✅ Text Chat Mode selected")
            input_mode = "text"
            break
        elif choice == "2":
            if asr_manager and asr_manager.is_enabled:
                # Voice Input Mode
                vtuber = AIVTuber(enable_streaming=False, audio_device_index=audio_device_index)
                print(f"🎤 Voice Input Mode selected - Press {asr_manager.hotkey} to talk")
                input_mode = "voice"
                break
            else:
                print("❌ Voice Input unavailable - ASR is disabled. Choose option 1 for text chat.")
        elif choice == "3":
            # Audio Device Settings
            audio_device_index = show_audio_device_menu()
            print("🔊 Audio device updated!")
        elif choice == "4":
            # Exit
            print("👋 Goodbye!")
            if asr_manager:
                asr_manager.stop_listening()
            return
        else:
            print("❌ Invalid choice. Please select 1-4.")
    
    # Start VTuber
    try:
        await vtuber.start()
        
        print("\n" + "="*50)
        print(f"🎭 VRM WebSocket: ws://localhost:{actual_port}")
        print("🎭 Connect your VRM viewer to receive animation signals")
        if input_mode == "voice" and asr_manager and asr_manager.is_enabled:
            print(f"🎤 VOICE MODE: Hold {asr_manager.hotkey} to speak, release to send")
            print("="*50)
            print(f"🎭 AI VTuber {vtuber_name} is live! Press Ctrl+C to exit.")
        elif input_mode == "text":
            print("💬 TEXT MODE: Type your messages below")
            print("="*50)

        if input_mode == "voice":
            # Voice input mode - wait for ASR and handle transcriptions
            while True:
                if (
                    asr_manager
                    and on_transcription is not None
                    and hasattr(on_transcription, 'pending_transcriptions')
                    and on_transcription.pending_transcriptions
                ):
                    text = on_transcription.pending_transcriptions.pop(0)
                    await vtuber.chat(text)

                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
        else:
            # Text input mode
            while True:
                user_input = input("\n💬 You: ").strip()

                if user_input.lower() in ['quit', 'exit']:
                    farewell = personality.get('farewell', 'Goodbye!')
                    print(f"🎭 {vtuber_name}: {farewell}")
                    vtuber.queue_tts(farewell)
                    time.sleep(2)
                    break

                if user_input:
                    await vtuber.chat(user_input)
                else:
                    print("💭 (Type something or 'quit' to exit)")
        
    except KeyboardInterrupt:
        print("\n🎭 Stream ended!")
    finally:
        # Cleanup
        if asr_manager:
            print("🎤 Stopping ASR...")
            asr_manager.stop_listening()
        
        await vtuber.stop()

if __name__ == "__main__":
    asyncio.run(main())
