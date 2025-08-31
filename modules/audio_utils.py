# -*- coding: utf-8 -*-
"""
Audio utilities for Miko AI VTuber - EXACT from reference audio_utils.py
"""
import sounddevice as sd

def get_audio_devices():
    """Get all available audio input and output devices"""
    devices = sd.query_devices()
    
    input_devices = []
    output_devices = []
    
    for i, device in enumerate(devices):
        device_info = {
            'id': i,
            'name': device['name'],
            'hostapi': device['hostapi'],
            'max_input_channels': device['max_input_channels'],
            'max_output_channels': device['max_output_channels']
        }
        
        # Input devices (microphones)
        if device['max_input_channels'] > 0:
            input_devices.append(device_info)
        
        # Output devices (speakers/headphones)
        if device['max_output_channels'] > 0:
            output_devices.append(device_info)
    
    return input_devices, output_devices

def get_device_display_name(device_info):
    """Get a friendly display name for a device"""
    return device_info['name']

def list_audio_devices():
    """Print all available audio devices for debugging"""
    devices = sd.query_devices()
    print("\n=== Available Audio Devices ===")
    for i, device in enumerate(devices):
        device_type = []
        if device['max_input_channels'] > 0:
            device_type.append("INPUT")
        if device['max_output_channels'] > 0:
            device_type.append("OUTPUT")
        
        print(f"ID {i}: {device['name']} ({', '.join(device_type)})")
        print(f"     Channels: In={device['max_input_channels']}, Out={device['max_output_channels']}")
    
    try:
        default_device = sd.query_devices(kind='input')
        print(f"\nDefault Input: {default_device['name']} (ID: {sd.default.device[0] if isinstance(sd.default.device, tuple) else sd.default.device})")
    except:
        print("\nCould not determine default input device")
    print("==================================\n")

def get_default_devices():
    """Get default input and output device IDs"""
    try:
        default_input = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
        default_output = sd.default.device[1] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
    except:
        default_input = None
        default_output = None
    
    return default_input, default_output

def find_device_by_name(device_name, device_type='input'):
    """Find device ID by name. Returns None if not found."""
    if device_name is None or device_name == "Default":
        return None
    
    try:
        input_devices, output_devices = get_audio_devices()
        devices_to_search = input_devices if device_type == 'input' else output_devices
        
        for device in devices_to_search:
            if device['name'] == device_name:
                return device['id']
        
        return None  # Device not found
    except:
        return None

def get_device_name_by_id(device_id, device_type='input'):
    """Get device name by ID. Returns None if not found."""
    if device_id is None:
        return "Default"
    
    try:
        devices = sd.query_devices()
        if device_id < len(devices) and device_id >= 0:
            return devices[device_id]['name']
        return None
    except:
        return None

def get_device_details(device_info):
    """Get detailed information about a device"""
    details = {
        'id': device_info['id'],
        'name': device_info['name'],
        'display_name': get_device_display_name(device_info),
        'input_channels': device_info['max_input_channels'],
        'output_channels': device_info['max_output_channels'],
        'type': 'unknown'
    }
    
    # Determine device type
    if device_info['max_input_channels'] > 0:
        if 'mic' in device_info['name'].lower() or 'microphone' in device_info['name'].lower():
            details['type'] = 'microphone'
        elif 'line' in device_info['name'].lower() or 'cable' in device_info['name'].lower():
            details['type'] = 'line_input'
        elif 'aux' in device_info['name'].lower():
            details['type'] = 'aux_input'
        elif 'interface' in device_info['name'].lower():
            details['type'] = 'audio_interface'
        else:
            details['type'] = 'input_device'
    
    if device_info['max_output_channels'] > 0:
        if 'speaker' in device_info['name'].lower():
            details['type'] = 'speaker'
        elif 'headphone' in device_info['name'].lower():
            details['type'] = 'headphone'
        elif 'monitor' in device_info['name'].lower():
            details['type'] = 'monitor'
        else:
            details['type'] = 'output_device'
    
    return details

def validate_device_name(device_name, device_type='input'):
    """Check if a device name is valid and available"""
    if device_name is None or device_name == "Default":
        return True  # Default is always valid
    
    device_id = find_device_by_name(device_name, device_type)
    return device_id is not None

def test_input_device(device_name, duration=3):
    """Test an input device to check if it's working and has audio"""
    if device_name == "Default":
        device_id = None
    else:
        device_id = find_device_by_name(device_name, 'input')
        if device_id is None:
            return False, "Device not found"
    
    try:
        import numpy as np
        
        # Record a short test sample
        samplerate = 44100
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate,
                          channels=1, dtype='float32', device=device_id, blocking=True)
        
        # Check audio level
        max_level = float(np.max(np.abs(recording)))
        
        if max_level < 0.001:
            return False, f"Very low audio level ({max_level:.6f}) - check device connection and volume"
        elif max_level < 0.01:
            return False, f"Low audio level ({max_level:.6f}) - device may be too quiet"
        else:
            return True, f"Device working - audio level: {max_level:.4f}"
            
    except Exception as e:
        return False, f"Device test failed: {str(e)}"

def get_device_recommendations():
    """Get recommendations for audio device selection"""
    input_devices, output_devices = get_audio_devices()
    
    recommendations = {
        'input': [],
        'output': []
    }
    
    # Input device recommendations
    for device in input_devices:
        details = get_device_details(device)
        if details['type'] == 'microphone':
            recommendations['input'].append({
                'device': device,
                'priority': 'high',
                'reason': 'Dedicated microphone - best for voice input'
            })
        elif details['type'] == 'line_input':
            recommendations['input'].append({
                'device': device,
                'priority': 'medium',
                'reason': 'Line input - good for external audio sources'
            })
        elif details['type'] == 'audio_interface':
            recommendations['input'].append({
                'device': device,
                'priority': 'high',
                'reason': 'Professional audio interface - excellent quality'
            })
        else:
            recommendations['input'].append({
                'device': device,
                'priority': 'low',
                'reason': 'Generic input device'
            })
    
    # Sort by priority
    recommendations['input'].sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['priority']])
    
    return recommendations

if __name__ == "__main__":
    print("Available audio devices:")
    input_devices, output_devices = get_audio_devices()
    
    print("\nInput devices (microphones):")
    for device in input_devices:
        print(f"  {get_device_display_name(device)}")
    
    print("\nOutput devices (speakers/headphones):")
    for device in output_devices:
        print(f"  {get_device_display_name(device)}")
    
    default_in, default_out = get_default_devices()
    print(f"\nDefault input: {default_in}, Default output: {default_out}")