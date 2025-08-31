#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for ASR functionality
"""

import sys
import os
sys.path.append('modules')

from modules.asr import ASRManager, test_asr_recording
from modules.config import config

def main():
    print("🧪 Testing ASR functionality...")
    
    # Test basic recording
    print("\n1. Testing basic recording...")
    success = test_asr_recording(config, "shift", 3)
    if success:
        print("✅ Basic recording test passed!")
    else:
        print("❌ Basic recording test failed!")
    
    # Test ASR manager
    print("\n2. Testing ASR manager...")
    try:
        asr = ASRManager(config)
        print(f"✅ ASR manager created: {asr.get_status()}")
        
        if asr.is_enabled:
            print("🎤 ASR is enabled and ready!")
        else:
            print("⚠️ ASR is disabled - check configuration")
            
    except Exception as e:
        print(f"❌ ASR manager test failed: {e}")
    
    print("\n🧪 ASR testing complete!")

if __name__ == "__main__":
    main()
