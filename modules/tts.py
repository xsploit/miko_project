# -*- coding: utf-8 -*-
"""
TTS client module with VRM WebSocket integration for Miko AI VTuber
EXACT functionality from working reference
"""
import asyncio
import aiohttp
import time
import queue
import threading
import numpy as np
import wave
import io
import json
import websockets
import requests
from .audio import AudioPlaybackThread

# VRM WebSocket globals - EXACT from working reference
vrm_websockets = set()

async def broadcast_to_vrm(message_type, text=None):
    """Broadcast animation signals to all connected VRM clients - EXACT from working reference"""
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

async def vrm_websocket_handler(websocket, path):
    """Handle VRM client connections - EXACT from working reference"""
    vrm_websockets.add(websocket)
    client_addr = websocket.remote_address
    print(f"🎭 VRM client connected: {client_addr}")
    
    try:
        await websocket.wait_closed()
    finally:
        vrm_websockets.discard(websocket)
        print(f"🎭 VRM client disconnected: {client_addr}")


class TTSClient:
    def __init__(self, vtuber_instance):
        self.base_url = "http://127.0.0.1:9880"  # EXACT from working reference
        self.session = None
        self.vtuber = vtuber_instance  # Reference to get audio queue
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def speak_sync(self, text: str):
        """EXACTLY copy working reference method with VRM integration"""
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
        
        # EXACT params from working reference
        params = {
            "text": text,
            "text_lang": "en",
            "ref_audio_path": "main_sample.wav",
            "prompt_text": "This is a sample voice for you to just get started with because it sounds kind of cute, but just make sure this doesn't have long silences.",
            "prompt_lang": "en",
            "streaming_mode": "true",  # STRING not bool like working reference!
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
        
        try:
            print(f"🔗 TTS GET request: {self.base_url}/tts")
            
            # EXACTLY like working reference - requests.get with params and stream=True
            with requests.get(f"{self.base_url}/tts", params=params, stream=True) as response:
                print(f"📡 TTS Response: {response.status_code}")
                if not response.ok:
                    print(f"TTS Error: {response.status_code}")
                    # Send VRM end signal even on error
                    asyncio.create_task(broadcast_to_vrm("tts_end"))
                    return
                
                # EXACTLY like working reference processing
                header_processed = False
                audio_buffer = io.BytesIO()
                sample_rate = 32000
                chunk_count = 0
                
                print("🎵 Starting TTS stream...")
                for chunk in response.iter_content(chunk_size=4096):
                    if not chunk:
                        continue
                    chunk_count += 1
                    
                    # First chunk for WAV contains the header - EXACTLY like working reference
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
                        # Process audio data - EXACTLY like working reference - put in audio queue
                        try:
                            audio_data = np.frombuffer(chunk, dtype=np.int16)
                            if len(audio_data) > 0:
                                self.vtuber.audio_queue.put(audio_data)  # Put in VTuber's queue
                                
                                # Start playback thread on first chunk - EXACTLY like working reference with device selection
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
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(broadcast_to_vrm("tts_end"))
                except RuntimeError:
                    # No event loop in this thread, skip VRM signal
                    pass
                
        except Exception as e:
            print(f"TTS Error: {e}")
            # Send VRM end signal even on error - use thread-safe approach
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(broadcast_to_vrm("tts_end"))
            except RuntimeError:
                # No event loop in this thread, skip VRM signal
                pass
    
    async def speak(self, text: str):
        """Async wrapper for sync speak method - EXACTLY like working reference."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.speak_sync, text)