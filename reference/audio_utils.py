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

def validate_device_name(device_name, device_type='input'):
    """Check if a device name is valid and available"""
    if device_name is None or device_name == "Default":
        return True  # Default is always valid
    
    device_id = find_device_by_name(device_name, device_type)
    return device_id is not None

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