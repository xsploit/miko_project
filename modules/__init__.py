# -*- coding: utf-8 -*-
"""
Miko AI VTuber modules package
"""
from .config import config
from .audio import AudioPlaybackThread, get_audio_devices, show_audio_device_menu
from .audio_utils import (
    find_device_by_name, validate_device_name, get_device_display_name, 
    get_default_devices, get_device_details, test_input_device, get_device_recommendations
)
from .tts import TTSClient, broadcast_to_vrm, vrm_websocket_handler
from .llm import LLMInterface
from .vtuber import AIVTuber
from .asr import ASRManager, test_asr_recording

__all__ = [
    'config',
    'AudioPlaybackThread', 
    'get_audio_devices', 
    'show_audio_device_menu',
    'find_device_by_name',
    'validate_device_name', 
    'get_device_display_name',
    'get_default_devices',
    'get_device_details',
    'test_input_device',
    'get_device_recommendations',
    'TTSClient', 
    'broadcast_to_vrm', 
    'vrm_websocket_handler',
    'LLMInterface',
    'AIVTuber',
    'ASRManager',
    'test_asr_recording'
]