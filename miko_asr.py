#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Miko AI VTuber with ASR Push-to-Talk Mode
Enhanced version with speech recognition input
"""
import asyncio
import sys
import os

# Import our modular components
from modules import (
    config, 
    AIVTuber, 
    LLMInterface, 
    ASRManager,
    show_audio_device_menu, 
    get_audio_devices,
    vrm_websocket_handler
)

# Auto-install
def auto_install():
    import subprocess
    required = ['ollama', 'aiohttp', 'sounddevice', 'numpy', 'requests', 'websockets', 'faster_whisper', 'soundfile', 'keyboard']
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"📦 Installing: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + missing)

auto_install()

import websockets
import aiohttp


async def main():
    """Main function with ASR support"""
    print("🔍 Checking services...")
    
    # Check Ollama
    if not LLMInterface.check_ollama():
        return
    
    # Check TTS server
    try:
        async with aiohttp.ClientSession() as session:
            test_data = {
                "text": "test",
                "text_lang": "en",
                "ref_audio_path": "main_sample.wav",
                "prompt_text": "test",
                "prompt_lang": "en",
                "streaming_mode": False,
                "parallel_infer": False,
                "media_type": "wav"
            }
            async with session.post(f"{config.tts_base_url}/tts", json=test_data) as response:
                if response.status == 200:
                    print("✅ TTS server working")
                else:
                    print(f"❌ TTS server error: {response.status}")
                    return
    except Exception as e:
        print(f"❌ TTS server not working! Error: {e}")
        print("Start TTS server on port 9880")
        return
    
    # Start VRM WebSocket server
    print(f"🎭 Starting VRM WebSocket server on port {config.vrm_websocket_port}...")
    vrm_server = await websockets.serve(vrm_websocket_handler, "localhost", config.vrm_websocket_port)
    print("✅ VRM WebSocket server started")
    
    # Load saved audio device
    audio_config = config.load_audio_config()
    saved_device = audio_config.get('device_index')
    
    # Menu for VTuber options with ASR
    personality = config.load_personality()
    print(f"\n🦊 {personality['name']} AI VTuber with ASR Menu:")
    print("1. Text Chat Mode (keyboard input)")
    print("2. ASR Push-to-Talk Mode (hold SHIFT to speak)")
    print("3. Mixed Mode (both text and voice)")
    print("4. Choose Audio Device")
    print("5. Exit")
    
    audio_device = saved_device
    if saved_device is not None:
        devices = get_audio_devices()
        device_name = "Unknown Device"
        for dev in devices:
            if dev['index'] == saved_device:
                device_name = dev['name']
                break
        print(f"🔊 Current device: {device_name}")
    else:
        print("🔊 Current device: System Default")
    
    while True:
        choice = input("\nChoice [1]: ").strip() or "1"
        
        if choice == "1":
            vtuber = AIVTuber(enable_streaming=False, audio_device_index=audio_device)
            mode = "text"
            print("✅ Text chat mode selected")
            break
        elif choice == "2":
            vtuber = AIVTuber(enable_streaming=False, audio_device_index=audio_device)
            mode = "asr"
            print("🎤 ASR push-to-talk mode selected")
            break
        elif choice == "3":
            vtuber = AIVTuber(enable_streaming=False, audio_device_index=audio_device)
            mode = "mixed"
            print("🎤📝 Mixed mode selected (type or hold SHIFT to speak)")
            break
        elif choice == "4":
            audio_device = show_audio_device_menu()
            print("🔊 Device updated! Select mode to continue.")
        elif choice == "5":
            print("👋 Goodbye!")
            return
        else:
            print("❌ Invalid choice")
    
    try:
        await vtuber.start()
        
        print("\n" + "="*60)
        print(f"🦊 AI VTuber {personality['name']} is live!")
        print(f"🎭 VRM WebSocket: ws://localhost:{config.vrm_websocket_port}")
        
        if mode == "text":
            print("💬 Text Mode: Type messages and press Enter")
            print("💬 Type 'quit' to exit")
        elif mode == "asr":
            print("🎤 ASR Mode: Hold SHIFT to record, release to transcribe & respond")
            print("🎤 Press Ctrl+C to exit")
        elif mode == "mixed":
            print("🎤 Mixed Mode: Type messages OR hold SHIFT to speak")
            print("💬 Type 'quit' to exit")
        
        print("="*60)
        
        if mode == "asr":
            # ASR-only mode
            asr = ASRManager()
            
            def on_transcription(text):
                print(f"\n👤 You (voice): {text}")
                # Handle transcription in async context
                asyncio.create_task(vtuber.chat(text))
            
            # This will block, so run in a separate thread
            import threading
            asr_thread = threading.Thread(target=lambda: asr.start_listening(on_transcription), daemon=True)
            asr_thread.start()
            
            # Keep main thread alive
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                asr.stop_listening()
                
        elif mode == "mixed":
            # Mixed mode - both text and ASR
            asr = ASRManager()
            asr.initialize_model()
            
            print("\n🎤 ASR initialized. You can now type or hold SHIFT to speak...")
            
            # Background ASR listener
            def asr_listener():
                while True:
                    try:
                        from modules.asr import record_and_transcribe
                        transcription = record_and_transcribe(asr.model)
                        if transcription:
                            print(f"\n👤 You (voice): {transcription}")
                            asyncio.run_coroutine_threadsafe(vtuber.chat(transcription), asyncio.get_event_loop())
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        print(f"ASR Error: {e}")
            
            asr_thread = threading.Thread(target=asr_listener, daemon=True)
            asr_thread.start()
            
            # Text input loop
            while True:
                try:
                    user_input = input("\n💬 You (text): ").strip()
                    
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    
                    if user_input:
                        await vtuber.chat(user_input)
                except KeyboardInterrupt:
                    break
        
        else:
            # Text-only mode (original)
            while True:
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    farewell = personality["farewell"]
                    print(f"🦊 {personality['name']}: {farewell}")
                    vtuber.queue_tts(farewell)
                    await asyncio.sleep(2)
                    break
                
                if user_input:
                    await vtuber.chat(user_input)
        
    except KeyboardInterrupt:
        print("\n🎭 Stream ended!")
    finally:
        await vtuber.stop()


if __name__ == "__main__":
    asyncio.run(main())