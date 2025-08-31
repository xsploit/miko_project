#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR (Automatic Speech Recognition) Module for Miko AI VTuber
Provides push-to-talk voice input functionality
"""

import os
import sounddevice as sd
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel
import keyboard
import threading
import time
import asyncio
from pathlib import Path
from typing import Optional, Callable


class ASRManager:
    """Manages ASR functionality for voice input"""
    
    def __init__(self, config, on_transcription: Optional[Callable[[str], None]] = None):
        self.config = config
        self.on_transcription = on_transcription
        self.is_enabled = False
        self.is_recording = False
        self.recording_thread = None
        self.model = None
        self.hotkey = "shift"
        self.model_name = "base.en"
        self.device = "cpu"
        self.input_device_id = None
        
        # Load ASR settings from config
        self.load_asr_config()
        
        # Initialize Whisper model if enabled
        if self.is_enabled:
            self.initialize_model()
    
    def load_asr_config(self):
        """Load ASR configuration from YAML config (what setup GUI saves to)"""
        try:
            # Use the new config method that loads from YAML
            asr_config = self.config.get_asr_config()
            self.is_enabled = asr_config.get("enabled", False)
            self.hotkey = asr_config.get("push_to_talk_key", "shift")
            self.model_name = asr_config.get("model", "base.en")
            self.device = asr_config.get("device", "cpu")
            self.input_device_id = asr_config.get("input_device_id")
            
            print(f"✅ Loaded ASR config: enabled={self.is_enabled}, hotkey={self.hotkey}, model={self.model_name}, device={self.device}")
            
        except Exception as e:
            print(f"⚠️ Failed to load ASR config: {e}")
            self.is_enabled = False
    
    def initialize_model(self):
        """Initialize the Whisper model"""
        try:
            print(f"🧠 Initializing ASR model: {self.model_name} on {self.device}")
            self.model = WhisperModel(self.model_name, device=self.device, compute_type="float32")
            print("✅ ASR model initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize ASR model: {e}")
            self.is_enabled = False
    
    def start_listening(self):
        """Start listening for hotkey presses to begin recording"""
        if not self.is_enabled or self.is_recording:
            return
        
        print(f"🎤 ASR listening for hotkey: {self.hotkey}")
        self.is_recording = True
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._recording_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
    
    def stop_listening(self):
        """Stop listening for hotkey presses"""
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=1)
        print("🎤 ASR listening stopped")
    
    def _recording_loop(self):
        """Main recording loop - waits for hotkey and records"""
        while self.is_recording:
            try:
                # Wait for hotkey press
                keyboard.wait(self.hotkey)
                
                if not self.is_recording:
                    break
                
                print(f"🔴 Recording started (hold {self.hotkey} to speak)...")
                
                # Record audio while hotkey is held
                audio_data = self._record_while_hotkey_held()
                
                if audio_data is not None and len(audio_data) > 0:
                    # Transcribe the audio
                    transcription = self._transcribe_audio(audio_data)
                    
                    if transcription and self.on_transcription:
                        # Call the callback with the transcription
                        try:
                            if asyncio.iscoroutinefunction(self.on_transcription):
                                # If it's an async function, we can't call it from sync context
                                # Just log the transcription for now
                                print(f"🎤 ASR transcription: '{transcription}' (async callback not supported in sync context)")
                            else:
                                # If it's a sync function, call it directly
                                self.on_transcription(transcription)
                        except Exception as e:
                            print(f"❌ Error calling transcription callback: {e}")
                
                # Small delay to prevent rapid re-triggering
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ ASR recording error: {e}")
                time.sleep(0.5)
    
    def _record_while_hotkey_held(self) -> Optional[np.ndarray]:
        """Record audio while the hotkey is held down"""
        try:
            samplerate = 44100
            chunk_duration = 0.1  # 100ms chunks
            chunk_samples = int(chunk_duration * samplerate)
            recording_data = []
            
            # Record in chunks while hotkey is held
            while keyboard.is_pressed(self.hotkey) and self.is_recording:
                chunk = sd.rec(chunk_samples, samplerate=samplerate, channels=1,
                             dtype='float32', device=self.input_device_id, blocking=True)
                recording_data.extend(chunk.flatten())
                
                # Limit recording duration to prevent very long recordings
                if len(recording_data) > samplerate * 30:  # 30 seconds max
                    break
            
            if not recording_data:
                return None
            
            # Convert to numpy array
            audio_data = np.array(recording_data, dtype='float32')
            
            # Check audio level
            max_level = float(np.max(np.abs(audio_data)))
            if max_level < 0.001:
                print("⚠️ Audio level too low - no speech detected")
                return None
            
            duration = len(audio_data) / samplerate
            if duration < 0.5:
                print("⚠️ Recording too short - try holding hotkey longer")
                return None
            
            print(f"⏹️ Recording complete: {duration:.2f}s, Level: {max_level:.4f}")
            return audio_data
            
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def _transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe audio data using Whisper"""
        try:
            if not self.model:
                print("❌ ASR model not initialized")
                return None
            
            # Save temporary audio file
            temp_file = "temp_asr_recording.wav"
            sf.write(temp_file, audio_data, 44100)
            
            print("🎯 Transcribing audio...")
            
            # Transcribe
            segments, _ = self.model.transcribe(temp_file)
            transcription = " ".join([segment.text for segment in segments])
            
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass
            
            if transcription.strip():
                print(f"✅ Transcription: '{transcription}'")
                return transcription.strip()
            else:
                print("⚠️ No transcription generated")
                return None
                
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
    
    def update_config(self):
        """Reload ASR configuration and reinitialize if needed"""
        old_enabled = self.is_enabled
        self.load_asr_config()
        
        # Reinitialize model if settings changed
        if self.is_enabled and (not self.model or old_enabled != self.is_enabled):
            self.initialize_model()
        
        # Update hotkey if changed
        if self.is_enabled:
            print(f"🎤 ASR updated - Hotkey: {self.hotkey}, Model: {self.model_name}")
    
    def get_status(self) -> dict:
        """Get current ASR status"""
        return {
            "enabled": self.is_enabled,
            "recording": self.is_recording,
            "hotkey": self.hotkey,
            "model": self.model_name,
            "device": self.device,
            "model_loaded": self.model is not None
        }


# Convenience function for testing ASR
def test_asr_recording(config, hotkey="shift", duration=5):
    """Test ASR recording functionality"""
    print(f"🎤 Testing ASR recording (hold {hotkey} for {duration}s)...")
    
    try:
        # Initialize ASR manager
        asr = ASRManager(config)
        asr.hotkey = hotkey
        
        # Simple recording test
        samplerate = 44100
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate,
                          channels=1, dtype='float32', blocking=True)
        
        # Check audio level
        max_level = float(np.max(np.abs(recording)))
        print(f"📊 Test recording: {duration}s, Level: {max_level:.4f}")
        
        if max_level < 0.001:
            print("⚠️ Very low audio level - check microphone!")
            return False
        
        print("✅ ASR test recording successful!")
        return True
        
    except Exception as e:
        print(f"❌ ASR test failed: {e}")
        return False