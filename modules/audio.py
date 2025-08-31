# -*- coding: utf-8 -*-
"""
Audio system module for Miko AI VTuber
Contains device management and the EXACT AudioPlaybackThread from working reference
"""
import threading
import time
import queue
import numpy as np
import sounddevice as sd


def get_audio_devices():
    """Get list of available audio output devices - EXACT from working reference"""
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


def show_audio_device_menu():
    """Show audio device selection menu - EXACT from working reference"""
    from .config import config
    devices = get_audio_devices()
    audio_config = config.load_audio_config()
    
    if not devices:
        print("❌ No audio output devices found!")
        return None
    
    print("\n🔊 Available Audio Devices:")
    print("0. System Default")
    
    for i, device in enumerate(devices, 1):
        marker = " (SAVED)" if device['index'] == audio_config.get('device_index') else ""
        print(f"{i}. {device['name']} - {int(device['channels'])} channels, {int(device['sample_rate'])}Hz{marker}")
    
    while True:
        choice = input(f"\nSelect audio device [0]: ").strip() or "0"
        
        try:
            choice_idx = int(choice)
            if choice_idx == 0:
                config.save_audio_config(None)
                return None
            elif 1 <= choice_idx <= len(devices):
                selected_device = devices[choice_idx - 1]
                config.save_audio_config(selected_device['index'])
                print(f"✅ Selected: {selected_device['name']}")
                return selected_device['index']
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Invalid choice")


# EXACT COPY of AudioPlaybackThread from working reference
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