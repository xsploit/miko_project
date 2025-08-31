import os
import sounddevice as sd
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel
import yaml
from pathlib import Path
import sys
import keyboard
import threading
import time
sys.path.append(str(Path(__file__).parent.parent.parent))
from audio_utils import find_device_by_name, validate_device_name

def get_audio_config():
    """Load audio device configuration"""
    try:
        # Get the project root directory (3 levels up from this file)
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / 'character_config.yaml'
        
        with open(config_path, 'r') as f:
            char_config = yaml.safe_load(f)
        
        audio_config = char_config.get('audio_config', {})
        input_name = audio_config.get('input_device_name', 'Default')
        output_name = audio_config.get('output_device_name', 'Default')
        
        # Convert names to IDs
        input_id = find_device_by_name(input_name, 'input')
        output_id = find_device_by_name(output_name, 'output')
        
        return input_id, output_id, input_name, output_name
    except Exception as e:
        print(f"Error loading audio config: {e}")
        return None, None, "Default", "Default"

def record_and_transcribe(model, output_file="recording.wav", samplerate=44100):
    """
    Push-to-talk recorder: Hold Shift to record, release to stop and transcribe
    """
    
    # Load audio device configuration
    input_device_id, _, input_name, _ = get_audio_config()
    
    # Validate input device
    if input_name != "Default" and not validate_device_name(input_name, 'input'):
        print(f"⚠️  Configured input device '{input_name}' is invalid/disconnected, using default")
        input_device_id = None
    
    # Remove existing file
    if os.path.exists(output_file):
        os.remove(output_file)
    
    print("🎤 Hold SHIFT to record, release to stop...")
    
    # Wait for Shift key press
    keyboard.wait('shift')
    
    print("🔴 Recording... (release SHIFT to stop)")
    
    # Start recording in a separate thread
    recording_data = []
    recording_active = threading.Event()
    recording_active.set()
    
    def record_audio():
        nonlocal recording_data
        try:
            print(f"🎤 Using input device: {input_name} (ID: {input_device_id})")
            
            # Record in chunks to allow real-time stopping
            chunk_duration = 0.1  # 100ms chunks
            chunk_samples = int(chunk_duration * samplerate)
            
            while recording_active.is_set():
                if keyboard.is_pressed('shift'):
                    chunk = sd.rec(chunk_samples, samplerate=samplerate, channels=1, 
                                 dtype='float32', device=input_device_id, blocking=True)
                    recording_data.extend(chunk.flatten())
                else:
                    recording_active.clear()
                    break
                    
        except Exception as e:
            print(f"Recording error with device {input_device_id}: {e}")
            print("Falling back to default input device...")
            
            while recording_active.is_set():
                if keyboard.is_pressed('shift'):
                    chunk = sd.rec(chunk_samples, samplerate=samplerate, channels=1, 
                                 dtype='float32', blocking=True)
                    recording_data.extend(chunk.flatten())
                else:
                    recording_active.clear()
                    break
    
    # Start recording thread
    record_thread = threading.Thread(target=record_audio)
    record_thread.start()
    
    # Wait for Shift key release
    while keyboard.is_pressed('shift'):
        time.sleep(0.01)
    
    # Stop recording
    recording_active.clear()
    record_thread.join()
    
    if not recording_data:
        print("❌ No audio recorded!")
        return ""
    
    # Convert to numpy array
    recording = np.array(recording_data, dtype='float32')
    
    # Check recording levels
    max_level = float(np.max(np.abs(recording)))
    duration = len(recording) / samplerate
    print(f"📊 Recording: {duration:.2f}s, Level: {max_level:.4f} (should be > 0.01)")
    
    if max_level < 0.001:
        print("⚠️  Very low audio level detected. Check microphone settings!")
        return ""
    
    if duration < 0.1:
        print("⚠️  Recording too short, try holding Shift longer")
        return ""
    
    print("⏹️  Saving audio...")
    
    # Write the file
    sf.write(str(output_file), recording, samplerate)
    
    print("🎯 Transcribing...")
    
    # Transcribe
    segments, _ = model.transcribe(str(output_file))
    transcription = " ".join([segment.text for segment in segments])
    
    print(f"Transcription: {transcription}")
    return transcription.strip()


# Example usage
if __name__ == "__main__":
    model = WhisperModel("base.en", device="cpu", compute_type="float32")
    result = record_and_transcribe(model)
    print(f"Got: '{result}'")
    