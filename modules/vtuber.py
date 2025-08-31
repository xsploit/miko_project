# -*- coding: utf-8 -*-
"""
Main VTuber module for Miko AI VTuber
Contains the AIVTuber class with EXACT functionality from working reference
Enhanced with ASR push-to-talk functionality
"""
import queue
import threading
import time
from .config import config
from .tts import TTSClient
from .llm import LLMInterface
from .asr import ASRManager


class AIVTuber:
    def __init__(self, model=None, enable_streaming=False, audio_device_index=None):
        # EXACT COPY from working reference - use audio queue and playback thread
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.tts_client = None
        
        # Get model from YAML config (what setup GUI saves to)
        if model is None:
            ollama_config = config.get_ollama_config()
            model = ollama_config.get('selected_model')
        
        self.llm = LLMInterface(model)
        self.enable_streaming = enable_streaming  # Toggle for streaming vs non-streaming
        
        # Get audio device from YAML config (what setup GUI saves to)
        if audio_device_index is None:
            audio_config = config.load_audio_config()
            audio_device_index = audio_config.get('device_index')
        
        self.audio_device_index = audio_device_index  # Selected audio device
        
        # Load personality and create conversation
        self.personality = config.load_personality()
        self.conversation = [
            {"role": "system", "content": self.personality["system_prompt"]}
        ]
        
        # TTS request queue to serialize requests and avoid conflicts
        self.tts_queue = queue.Queue()
        self.tts_worker_thread = None
        self.tts_worker_running = False
        
        print(f"🎭 VTuber initialized: model={model}, streaming={enable_streaming}, audio_device={audio_device_index}")
        
    def _tts_worker(self):
        """Worker thread that processes TTS requests one at a time - EXACT from working reference"""
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
        """Queue text for TTS - non-blocking - EXACT from working reference"""
        if text.strip():
            print(f"📝 Queuing TTS: '{text[:50]}...'")
            self.tts_queue.put(text)
        else:
            print(f"❌ Skipped empty TTS: '{text}'")
        
    async def start(self):
        """Start the VTuber - EXACT from working reference"""
        print(f"🎤 Starting AI VTuber {self.personality['name']} with VRM support...")
        self.tts_client = TTSClient(self)  # Pass self reference
        await self.tts_client.__aenter__()
        
        # Start TTS worker thread
        self.tts_worker_running = True
        self.tts_worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_worker_thread.start()
        print("🔊 TTS worker thread started")
        
        # Welcome message from personality
        welcome = self.personality["greeting"]
        if not welcome or welcome.strip() == "":
            welcome = "Hello! I'm ready to chat!"
            print(f"⚠️ Using fallback greeting: {welcome}")
        
        print(f"🎭 {self.personality['name']}: {welcome}")
        print("🎙️ Speaking welcome message...")
        self.queue_tts(welcome)
        
    async def stop(self):
        """Stop the VTuber - EXACT from working reference"""
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
        """Handle chat interaction - EXACT from working reference"""
        self.conversation.append({"role": "user", "content": user_input})
        
        print(f"👤 User: {user_input}")
        print(f"🎭 {self.personality['name']}: ", end="", flush=True)
        
        response_text = ""
        sentence_buffer = ""
        
        try:
            if self.enable_streaming:
                # STREAMING MODE - queue sentences as they complete
                print("(streaming mode)")
                for chunk in self.llm.chat_streaming(self.conversation):
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
                response_text = self.llm.chat_complete(self.conversation)
                print(response_text)
                
                # Send complete response to TTS
                self.queue_tts(response_text)
                    
        except Exception as e:
            error_msg = self.personality["error_message"]
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
        
        # Keep conversation manageable - EXACT from working reference
        if len(self.conversation) > 11:
            self.conversation = [self.conversation[0]] + self.conversation[-10:]