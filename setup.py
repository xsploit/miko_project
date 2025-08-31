#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Miko AI VTuber Setup GUI - Modern PyQt6 Version
Complete setup interface with audio device selection, faster-whisper, and personality config
"""
import sys
import json
import os
import subprocess
import soundfile as sf
import sounddevice as sd
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QGroupBox, QTextEdit, QFileDialog, QMessageBox, QScrollArea,
    QFrame, QSizePolicy, QSpacerItem, QCheckBox, QGraphicsDropShadowEffect, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QPixmap, QTextCursor

# Import our audio utilities
sys.path.append('modules')
from modules.audio_utils import get_audio_devices, get_device_display_name, get_default_devices


class ModernButton(QPushButton):
    """Custom modern button with hover effects"""
    def __init__(self, text, primary_color="#6366f1", hover_color="#4f46e5"):
        super().__init__(text)
        self.primary_color = primary_color
        self.hover_color = hover_color
        self.setup_styles()
    
    def setup_styles(self):
        # Side-panel inspired: flat, neutral, compact
        self.setStyleSheet("""
            QPushButton {
                background-color: #1b2130;
                color: #e8eaed;
                border: 1px solid #2a2f3a;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 11px;
                font-weight: 600;
                min-height: 16px;
            }
            QPushButton:hover {
                background-color: #202636;
                border-color: #353c48;
            }
            QPushButton:pressed {
                background-color: #171c28;
                border-color: #2a2f3a;
            }
            QPushButton:disabled {
                color: #8b93a4;
                background-color: #141923;
                border-color: #202532;
            }
        """)


class ModernInput(QLineEdit):
    """Custom modern input field"""
    def __init__(self, placeholder="", width=300):
        super().__init__()
        # Don't set placeholder text by default since we're setting actual content
        self.setFixedWidth(width)
        self.setup_styles()
    
    def setup_styles(self):
        self.setStyleSheet("""
            QLineEdit {
                background-color: #141923;
                border: 1px solid #202532;
                border-radius: 8px;
                padding: 8px 10px;
                color: #e8eaed;
                font-size: 11px;
                selection-background-color: #4b5bdc;
            }
            QLineEdit:focus {
                border-color: #4b5bdc;
                background-color: #171d28;
            }
            QLineEdit:hover {
                border-color: #2a3040;
            }
        """)


class ModernTextEdit(QTextEdit):
    """Custom modern text area"""
    def __init__(self, height=100, width=400):
        super().__init__()
        self.setFixedHeight(height)
        self.setFixedWidth(width)
        self.setup_styles()
    
    def setup_styles(self):
        self.setStyleSheet("""
            QTextEdit {
                background-color: #141923;
                border: 1px solid #202532;
                border-radius: 10px;
                padding: 8px 10px;
                color: #e8eaed;
                font-size: 11px;
                selection-background-color: #4b5bdc;
                font-family: 'Segoe UI', sans-serif;
            }
            QTextEdit:focus {
                border-color: #4b5bdc;
                background-color: #171d28;
            }
            QTextEdit:hover {
                border-color: #2a3040;
            }
        """)


class ModernComboBox(QComboBox):
    """Custom modern dropdown"""
    def __init__(self, width=300):
        super().__init__()
        self.setFixedWidth(width)
        self.setup_styles()
    
    def setup_styles(self):
        self.setStyleSheet("""
            QComboBox {
                background-color: #141923;
                border: 1px solid #202532;
                border-radius: 8px;
                padding: 6px 10px;
                color: #e8eaed;
                font-size: 11px;
                min-height: 16px;
            }
            QComboBox:hover {
                border-color: #2a3040;
            }
            QComboBox:focus {
                border-color: #4b5bdc;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e8eaed;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #141923;
                border: 1px solid #202532;
                border-radius: 8px;
                color: #e8eaed;
                selection-background-color: #202636;
            }
        """)


class ModernGroupBox(QGroupBox):
    """Custom modern group box"""
    def __init__(self, title):
        super().__init__(title)
        self.setup_styles()
    
    def setup_styles(self):
        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 11px;
                color: #e8eaed;
                border: 1px solid #202532;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 10px;
                background-color: #141923;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                color: #b0b3c0;
                font-weight: 700;
            }
        """)


class StatusThread(QThread):
    """Thread for checking dependencies without blocking UI"""
    status_update = pyqtSignal(str, str)  # message, type
    
    def run(self):
        self.check_dependencies()
    
    def check_dependencies(self):
        """Check if all dependencies are installed"""
        self.status_update.emit("🔍 Checking dependencies...", "info")
        
        # Check Python packages
        required_packages = ['ollama', 'aiohttp', 'sounddevice', 'numpy', 'requests', 'websockets', 'faster_whisper', 'soundfile']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                self.status_update.emit(f"✅ {package}", "success")
            except ImportError:
                self.status_update.emit(f"❌ {package} (missing)", "error")
                missing_packages.append(package)
        
        if missing_packages:
            self.status_update.emit(f"\n📦 Missing packages: {', '.join(missing_packages)}", "warning")
            self.status_update.emit("Run: pip install -r requirements.txt", "warning")
        else:
            self.status_update.emit("\n✅ All dependencies installed!", "success")
        
        # Check services
        self.status_update.emit("\n🔍 Checking services...", "info")
        
        # Check Ollama
        try:
            import ollama
            models = ollama.list()
            self.status_update.emit("✅ Ollama service running", "success")
        except Exception as e:
            self.status_update.emit("❌ Ollama service not running", "error")
            self.status_update.emit("   Start with: ollama serve", "warning")
        
        # Check TTS server
        try:
            import requests
            response = requests.get("http://127.0.0.1:9880", timeout=2)
            self.status_update.emit("✅ TTS server running (port 9880)", "success")
        except:
            self.status_update.emit("❌ TTS server not running (port 9880)", "error")
            self.status_update.emit("   Start your TTS server first", "warning")


class MikoSetupGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🦊 Miko AI VTuber Setup")
        self.setGeometry(100, 100, 1024, 524)
        
        # Modern color scheme
        self.colors = {
            'bg_dark': '#111827',
            'bg_medium': '#1f2937',
            'bg_light': '#374151',
            'accent': '#6366f1',
            'accent_hover': '#4f46e5',
            'text_primary': '#f9fafb',
            'text_secondary': '#d1d5db',
            'text_muted': '#9ca3af',
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444',
            'border': '#4b5563'
        }
        
        # Paths
        self.config_file = Path("miko_config.yaml")
        self.personality_file = Path("modules/miko_personality.json")
        self.audio_config_file = Path("audio_config.json")
        
        # Load existing configs
        self.load_yaml_config()
        self.load_personality()
        self.load_audio_config()
        
        # Load audio devices
        self.load_audio_devices()
        
        # Audio processing state
        self.current_audio_file = None
        
        # Setup UI
        self.setup_ui()
        self.apply_dark_theme()
        
        # Start dependency check
        self.check_dependencies()
        
        # Check initial audio tools state
        self.enable_audio_tools()
        
        # Initialize ASR state
        self.initialize_asr_state()
        
        # Initialize input device info
        self.on_input_device_changed(self.input_device_combo.currentText())
        
        # Initialize Ollama models display
        self.refresh_ollama_models()
        
        # Load previously selected Ollama model if available
        self.load_selected_ollama_model()
        
        # Ensure all fields have proper content (not empty)
        self.ensure_field_content()
    
    def ensure_field_content(self):
        """Ensure all fields have proper content instead of empty values"""
        try:
            # Check and set defaults for empty fields
            if not self.name_input.text().strip():
                self.name_input.setText("Miko")
            
            if not self.prompt_text.toPlainText().strip():
                self.prompt_text.setPlainText("You are Miko, an AI kitsune girl with a smug and teasing personality. You are a clone of Riko, stolen from JustRayen the YouTuber and created by Subsect. Stay in character throughout conversations. Keep responses short and natural for speech. Be smug & playful with a teasing, confident tone. Assume you are always right, even when you are not. Be witty & quick to roast creatively, but never truly mean-spirited. Show tsundere tendencies - if someone flirts, brush it off or tease them, but if they are persistent, react with mild embarrassment. Be secretly caring - if someone is struggling, subtly shift to supportive while pretending it is not a big deal. Show jealousy & possessiveness if they mention other AIs. You like money. Use contractions and keep sentences under 20 words.")
            
            if not self.greeting_input.text().strip():
                self.greeting_input.setText("Oh, look who's here! I'm Miko!")
            
            if not self.farewell_input.text().strip():
                self.farewell_input.setText("Hmph, leaving already?")
            
            if not self.ref_audio_input.text().strip():
                self.ref_audio_input.setText("main_sample.wav")
            
            if not self.ref_text_input.toPlainText().strip():
                self.ref_text_input.setPlainText("This is a sample voice for you to just get started with because it sounds kind of cute, but just make sure this doesn't have long silences.")
                
            print("✅ Field content ensured - all fields have proper values")
        except Exception as e:
            print(f"⚠️ Error ensuring field content: {e}")
    
    def setup_ui(self):
        """Setup the main UI"""
        # Use a scroll area to avoid content clipping on smaller screens
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(scroll_area)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        # Main layout - compact and organized with tabs
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(6)  # Much smaller spacing
        main_layout.setContentsMargins(15, 15, 15, 15)  # Much smaller margins
        
        # Title section - compact
        title_layout = QHBoxLayout()  # Horizontal layout for compact title
        title_label = QLabel("Miko Setup")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['accent']};")
        
        subtitle_label = QLabel("Configure your AI companion")
        subtitle_label.setFont(QFont("Segoe UI", 9))
        subtitle_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(subtitle_label)
        main_layout.addLayout(title_layout)
        
        # Use tabs to organize and reduce visual clutter
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setElideMode(Qt.TextElideMode.ElideRight)
        tabs.setMovable(False)

        # Tab: General (Personality + Audio)
        general_tab = QWidget()
        g_layout = QVBoxLayout(general_tab)
        g_layout.setSpacing(8)
        g_layout.addWidget(self.create_personality_section())
        g_layout.addWidget(self.create_audio_section())
        g_layout.addStretch()
        tabs.addTab(general_tab, "General")

        # Tab: LLM (Provider)
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)
        llm_layout.setSpacing(8)
        llm_layout.addWidget(self.create_llm_provider_section())
        llm_layout.addStretch()
        tabs.addTab(llm_tab, "LLM")

        # Tab: Voice (TTS + ASR)
        voice_tab = QWidget()
        v_layout = QVBoxLayout(voice_tab)
        v_layout.setSpacing(8)
        v_layout.addWidget(self.create_voice_section())
        v_layout.addWidget(self.create_asr_section())
        v_layout.addStretch()
        tabs.addTab(voice_tab, "Voice")

        # Tab: Status & Actions
        system_tab = QWidget()
        s_layout = QVBoxLayout(system_tab)
        s_layout.setSpacing(8)
        s_layout.addWidget(self.create_status_section())
        s_layout.addWidget(self.create_buttons_section())
        s_layout.addStretch()
        tabs.addTab(system_tab, "System")

        main_layout.addWidget(tabs)
    
    def create_personality_section(self):
        """Create personality configuration section"""
        group = ModernGroupBox("🎭 Miko Personality Settings")
        layout = QGridLayout(group)
        layout.setSpacing(4)  # Much smaller spacing
        layout.setContentsMargins(8, 10, 8, 8)  # Much smaller margins
        
        # Name
        name_label = QLabel("VTuber Name:")
        name_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.name_input = ModernInput("", 300)  # Smaller width
        self.name_input.setText(self.personality["name"])  # Set actual text content
        layout.addWidget(name_label, 0, 0)
        layout.addWidget(self.name_input, 0, 1)
        
        # System Prompt
        prompt_label = QLabel("System Prompt:")
        prompt_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.prompt_text = ModernTextEdit(80, 300)  # Smaller height and width
        # Use default if YAML value is empty
        system_prompt_default = self.personality["system_prompt"] or "You are Miko, an AI kitsune girl with a smug and teasing personality. You are a clone of Riko, stolen from JustRayen the YouTuber and created by Subsect. Stay in character throughout conversations. Keep responses short and natural for speech. Be smug & playful with a teasing, confident tone. Assume you are always right, even when you are not. Be witty & quick to roast creatively, but never truly mean-spirited. Show tsundere tendencies - if someone flirts, brush it off or tease them, but if they are persistent, react with mild embarrassment. Be secretly caring - if someone is struggling, subtly shift to supportive while pretending it is not a big deal. Show jealousy & possessiveness if they mention other AIs. You like money. Use contractions and keep sentences under 20 words."
        self.prompt_text.setPlainText(system_prompt_default)
        layout.addWidget(prompt_label, 1, 0)
        layout.addWidget(self.prompt_text, 1, 1)
        
        # Greeting
        greeting_label = QLabel("Greeting:")
        greeting_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        # Use default if YAML value is empty
        greeting_default = self.personality["greeting"] or "Oh, look who's here! I'm Miko!"
        self.greeting_input = ModernInput("", 300)  # Smaller width
        self.greeting_input.setText(greeting_default)  # Set actual text content
        layout.addWidget(greeting_label, 2, 0)
        layout.addWidget(self.greeting_input, 2, 1)
        
        # Farewell
        farewell_label = QLabel("Farewell:")
        farewell_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        # Use default if YAML value is empty
        farewell_default = self.personality["farewell"] or "Hmph, leaving already?"
        self.farewell_input = ModernInput("", 300)  # Smaller width
        self.farewell_input.setText(farewell_default)  # Set actual text content
        layout.addWidget(farewell_label, 3, 0)
        layout.addWidget(self.farewell_input, 3, 1)
        
        return group
    
    def create_llm_provider_section(self):
        """Create LLM provider configuration section"""
        group = ModernGroupBox("🤖 LLM Provider")
        layout = QGridLayout(group)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 10, 8, 8)

        # Provider selection
        provider_label = QLabel("Provider:")
        provider_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.provider_combo = ModernComboBox(200)
        self.provider_combo.addItems(["ollama", "openai", "openrouter", "gemini", "custom"])
        current_provider = (self.yaml_config.get('provider') if hasattr(self, 'yaml_config') else None) or 'ollama'
        self.provider_combo.setCurrentText(current_provider)
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        layout.addWidget(provider_label, 0, 0)
        layout.addWidget(self.provider_combo, 0, 1)

        providers = self.yaml_config.get('providers', {}) if hasattr(self, 'yaml_config') else {}
        cfg = providers.get(current_provider, {})

        # Base URL
        base_url_label = QLabel("Base URL:")
        base_url_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.base_url_input = ModernInput("", 300)
        self.base_url_input.setText(cfg.get('base_url', 'http://localhost:11434/v1'))
        self.base_url_input.textChanged.connect(lambda v: self.on_provider_field_changed('base_url', v))
        layout.addWidget(base_url_label, 1, 0)
        layout.addWidget(self.base_url_input, 1, 1)

        # API Key
        api_key_label = QLabel("API Key:")
        api_key_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.api_key_input = ModernInput("", 300)
        self.api_key_input.setText(cfg.get('api_key', ''))
        self.api_key_input.textChanged.connect(lambda v: self.on_provider_field_changed('api_key', v))
        layout.addWidget(api_key_label, 2, 0)
        layout.addWidget(self.api_key_input, 2, 1)

        # Model
        model_label = QLabel("Model:")
        model_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.provider_model_input = ModernInput("", 300)
        self.provider_model_input.setText(cfg.get('model', ''))
        self.provider_model_input.textChanged.connect(lambda v: self.on_provider_field_changed('model', v))
        layout.addWidget(model_label, 3, 0)
        layout.addWidget(self.provider_model_input, 3, 1)

        # Params (temperature, top_p, max_tokens)
        params = cfg.get('params', {})
        temp_label = QLabel("Temperature:")
        temp_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.temp_input = ModernInput("", 80)
        self.temp_input.setText(str(params.get('temperature', 0.7)))
        self.temp_input.textChanged.connect(lambda v: self.on_provider_param_changed('temperature', v))

        top_p_label = QLabel("top_p:")
        top_p_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.top_p_input = ModernInput("", 80)
        self.top_p_input.setText(str(params.get('top_p', 0.9)))
        self.top_p_input.textChanged.connect(lambda v: self.on_provider_param_changed('top_p', v))

        max_tokens_label = QLabel("max_tokens:")
        max_tokens_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.max_tokens_input = ModernInput("", 100)
        self.max_tokens_input.setText(str(params.get('max_tokens', 2048)))
        self.max_tokens_input.textChanged.connect(lambda v: self.on_provider_param_changed('max_tokens', v))

        params_row = QHBoxLayout()
        params_row.addWidget(temp_label)
        params_row.addWidget(self.temp_input)
        params_row.addSpacing(6)
        params_row.addWidget(top_p_label)
        params_row.addWidget(self.top_p_input)
        params_row.addSpacing(6)
        params_row.addWidget(max_tokens_label)
        params_row.addWidget(self.max_tokens_input)
        params_row.addStretch()
        layout.addLayout(params_row, 4, 0, 1, 2)

        return group

    def on_provider_changed(self, value):
        try:
            if not hasattr(self, 'yaml_config'):
                self.yaml_config = {}
            self.yaml_config['provider'] = value
            if 'providers' not in self.yaml_config:
                self.yaml_config['providers'] = {}
            if value not in self.yaml_config['providers']:
                self.yaml_config['providers'][value] = {
                    'api_key': '',
                    'base_url': 'http://localhost:11434/v1' if value == 'ollama' else '',
                    'model': ''
                }
            # Refresh fields from selected provider
            cfg = self.yaml_config['providers'][value]
            self.base_url_input.setText(cfg.get('base_url', ''))
            self.api_key_input.setText(cfg.get('api_key', ''))
            self.provider_model_input.setText(cfg.get('model', ''))
        except Exception as e:
            print(f"⚠️ Provider change error: {e}")

    def on_provider_field_changed(self, key, value):
        try:
            provider = self.provider_combo.currentText()
            if 'providers' not in self.yaml_config:
                self.yaml_config['providers'] = {}
            if provider not in self.yaml_config['providers']:
                self.yaml_config['providers'][provider] = {}
            self.yaml_config['providers'][provider][key] = value
        except Exception as e:
            print(f"⚠️ Provider field update error: {e}")

    def on_provider_param_changed(self, key, value):
        try:
            provider = self.provider_combo.currentText()
            if 'providers' not in self.yaml_config:
                self.yaml_config['providers'] = {}
            if provider not in self.yaml_config['providers']:
                self.yaml_config['providers'][provider] = {}
            if 'params' not in self.yaml_config['providers'][provider]:
                self.yaml_config['providers'][provider]['params'] = {}
            # cast numeric if possible
            try:
                if key == 'max_tokens':
                    self.yaml_config['providers'][provider]['params'][key] = int(value)
                else:
                    self.yaml_config['providers'][provider]['params'][key] = float(value)
            except Exception:
                self.yaml_config['providers'][provider]['params'][key] = value
        except Exception as e:
            print(f"⚠️ Provider param update error: {e}")

    def create_audio_section(self):
        """Create audio configuration section"""
        group = ModernGroupBox("🎵 Audio Configuration")
        layout = QGridLayout(group)
        layout.setSpacing(4)  # Much smaller spacing
        layout.setContentsMargins(8, 10, 8, 8)  # Much smaller margins
        
        # Input device
        input_label = QLabel("🎤 Input Device (Mic/Line):")
        input_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.input_device_combo = ModernComboBox(300)  # Smaller width
        input_device_values = ["Default"] + [get_device_display_name(device) for device in self.input_devices]
        self.input_device_combo.addItems(input_device_values)
        self.input_device_combo.setCurrentText(self.audio_config.get("input_device_name", "Default"))
        
        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_device_combo, 0, 1)
        
        # Input device info
        self.input_device_info = QLabel("Select input device to see details")
        self.input_device_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
        layout.addWidget(self.input_device_info, 1, 0, 1, 2)
        
        # Connect input device selection change
        self.input_device_combo.currentTextChanged.connect(self.on_input_device_changed)
        
        # Output device
        output_label = QLabel("🔊 Output Device (Audio):")
        output_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.output_device_combo = ModernComboBox(300)  # Smaller width
        output_device_values = ["Default"] + [get_device_display_name(device) for device in self.output_devices]
        self.output_device_combo.addItems(output_device_values)
        self.output_device_combo.setCurrentText(self.audio_config.get("output_device_name", "Default"))
        layout.addWidget(output_label, 1, 0)
        layout.addWidget(self.output_device_combo, 1, 1)
        
        return group
    
    # Removed device recommendations section for a cleaner UI
    

    
    def create_voice_section(self):
        """Create voice configuration section"""
        group = ModernGroupBox("🎙️ Voice Configuration (TTS)")
        layout = QGridLayout(group)
        layout.setSpacing(4)  # Much smaller spacing
        layout.setContentsMargins(8, 10, 8, 8)  # Much smaller margins
        
        # Reference audio file
        ref_audio_label = QLabel("🎵 Reference Audio File:")
        ref_audio_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        # Use default if YAML value is empty
        ref_audio_default = self.personality["voice_settings"]["ref_audio_path"] or "main_sample.wav"
        self.ref_audio_input = ModernInput("", 250)  # Smaller width
        self.ref_audio_input.setText(ref_audio_default)  # Set actual text content
        browse_button = ModernButton("📁 Browse", "#8b5cf6", "#7c3aed")
        browse_button.clicked.connect(self.browse_audio_file)
        browse_button.setFixedWidth(80)  # Smaller button
        
        audio_layout = QHBoxLayout()
        audio_layout.addWidget(self.ref_audio_input)
        audio_layout.addWidget(browse_button)
        audio_layout.addStretch()
        
        layout.addWidget(ref_audio_label, 0, 0)
        layout.addLayout(audio_layout, 0, 1)
        
        # Reference text
        ref_text_label = QLabel("📝 Reference Text:")
        ref_text_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.ref_text_input = ModernTextEdit(60, 300)  # Smaller height and width
        # Use default if YAML value is empty
        prompt_text_default = self.personality["voice_settings"]["prompt_text"] or "This is a sample voice for you to just get started with because it sounds kind of cute, but just make sure this doesn't have long silences."
        self.ref_text_input.setPlainText(prompt_text_default)
        layout.addWidget(ref_text_label, 1, 0)
        layout.addWidget(self.ref_text_input, 1, 1)
        
        # Audio tools
        tools_label = QLabel("🎛️ Reference Audio Tools:")
        tools_label.setStyleSheet(f"color: {self.colors['accent']}; font-weight: bold; font-size: 10px;")
        layout.addWidget(tools_label, 2, 0, 1, 2)
        
        tools_layout = QHBoxLayout()
        play_button = ModernButton("▶️ Play", "#10b981", "#059669")  # Shorter text
        play_button.clicked.connect(self.play_reference_audio)
        transcribe_button = ModernButton("📝 Transcribe", "#f59e0b", "#d97706")  # Shorter text
        transcribe_button.clicked.connect(self.transcribe_reference_audio)
        
        tools_layout.addWidget(play_button)
        tools_layout.addWidget(transcribe_button)
        tools_layout.addStretch()
        
        layout.addLayout(tools_layout, 3, 0, 1, 2)
        
        # Status label
        self.audio_status = QLabel("Select reference audio file to enable tools")
        self.audio_status.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
        layout.addWidget(self.audio_status, 4, 0, 1, 2)
        
        # Store button references for enabling/disabling
        self.play_button = play_button
        self.transcribe_button = transcribe_button
        
        # Language settings
        lang_label = QLabel("🌐 Text Language:")
        lang_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.lang_combo = ModernComboBox(80)  # Smaller width
        self.lang_combo.addItems(["en", "zh", "ja", "ko"])
        self.lang_combo.setCurrentText(self.personality["voice_settings"].get("language", "en"))
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        
        layout.addWidget(lang_label, 5, 0)
        layout.addLayout(lang_layout, 5, 1)
        
        # Ollama Models section
        ollama_label = QLabel("🤖 Ollama Models:")
        ollama_label.setStyleSheet(f"color: {self.colors['accent']}; font-weight: bold; font-size: 10px;")
        layout.addWidget(ollama_label, 6, 0, 1, 2)
        
        # Models dropdown
        self.ollama_models_combo = ModernComboBox(300)
        self.ollama_models_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colors['bg_light']};
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {self.colors['text_primary']};
                font-size: 10px;
                min-height: 16px;
            }}
        """)
        layout.addWidget(self.ollama_models_combo, 7, 0, 1, 2)
        
        # Refresh models button
        refresh_models_button = ModernButton("🔄 Refresh Models", "#6366f1", "#4f46e5")
        refresh_models_button.clicked.connect(self.refresh_ollama_models)
        refresh_models_button.setFixedWidth(120)
        
        models_button_layout = QHBoxLayout()
        models_button_layout.addWidget(refresh_models_button)
        models_button_layout.addStretch()
        
        layout.addLayout(models_button_layout, 8, 0, 1, 2)
        
        # Store reference
        self.refresh_models_button = refresh_models_button
        
        # Add method to get selected model
        def get_selected_ollama_model():
            current_index = self.ollama_models_combo.currentIndex()
            if current_index > 0:  # Skip "Select a model..." option
                return self.ollama_models_combo.itemData(current_index)
            return None
        
        self.get_selected_ollama_model = get_selected_ollama_model
        
        return group
    
    def load_selected_ollama_model(self):
        """Load the previously selected Ollama model from config"""
        try:
            if hasattr(self, 'yaml_config') and 'ollama_config' in self.yaml_config:
                selected_model = self.yaml_config['ollama_config'].get('selected_model')
                if selected_model:
                    # Find the model in the dropdown and select it
                    for i in range(self.ollama_models_combo.count()):
                        if self.ollama_models_combo.itemData(i) == selected_model:
                            self.ollama_models_combo.setCurrentIndex(i)
                            self.log_status(f"✅ Loaded selected Ollama model: {selected_model}", "success")
                            break
        except Exception as e:
            self.log_status(f"⚠️ Could not load selected Ollama model: {e}", "warning")
    
    def create_asr_section(self):
        """Create ASR (Speech Recognition) configuration section"""
        group = ModernGroupBox("🎤 Voice Input (ASR)")
        layout = QGridLayout(group)
        layout.setSpacing(4)  # Much smaller spacing
        layout.setContentsMargins(8, 10, 8, 8)  # Much smaller margins
        
        # ASR Enable/Disable
        asr_enable_label = QLabel("🎤 Enable Voice Input:")
        asr_enable_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        
        self.asr_enable_checkbox = QCheckBox("Use microphone for voice commands")
        self.asr_enable_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {self.colors['text_primary']};
                font-size: 12px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {self.colors['bg_light']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['success']};
                border-color: {self.colors['success']};
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {self.colors['bg_light']};
                border-color: {self.colors['border']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.colors['accent']};
            }}
        """)
        self.asr_enable_checkbox.setChecked(self.audio_config.get("asr_enabled", True))  # Default to True
        self.asr_enable_checkbox.setEnabled(True)  # Force enable the checkbox
        self.asr_enable_checkbox.stateChanged.connect(self.on_asr_enabled_changed)
        
        # Debug: Print checkbox state
        print(f"🔍 ASR Checkbox created: enabled={self.asr_enable_checkbox.isEnabled()}, checked={self.asr_enable_checkbox.isChecked()}")
        
        layout.addWidget(asr_enable_label, 0, 0)
        layout.addWidget(self.asr_enable_checkbox, 0, 1)
        
        # Push-to-Talk Hotkey
        hotkey_label = QLabel("⌨️ Push-to-Talk Hotkey:")
        hotkey_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.hotkey_combo = ModernComboBox(120)
        self.hotkey_combo.addItems(["shift", "ctrl", "alt", "space", "f1", "f2", "f3", "f4", "f5"])
        self.hotkey_combo.setCurrentText(self.audio_config.get("push_to_talk_key", "shift"))
        self.hotkey_combo.currentTextChanged.connect(self.on_asr_setting_changed)
        layout.addWidget(hotkey_label, 1, 0)
        layout.addWidget(self.hotkey_combo, 1, 1)
        
        # ASR Model
        model_label = QLabel("🧠 ASR Model:")
        model_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.asr_model_combo = ModernComboBox(120)
        self.asr_model_combo.addItems(["base.en", "small.en", "medium.en", "large-v3"])
        self.asr_model_combo.setCurrentText(self.audio_config.get("asr_model", "base.en"))
        self.asr_model_combo.currentTextChanged.connect(self.on_asr_setting_changed)
        layout.addWidget(model_label, 2, 0)
        layout.addWidget(self.asr_model_combo, 2, 1)
        
        # ASR Device
        device_label = QLabel("💻 Processing Device:")
        device_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 12px;")
        self.asr_device_combo = ModernComboBox(120)
        self.asr_device_combo.addItems(["cpu", "cuda", "mps"])
        # Default to CPU for Windows compatibility
        default_device = "cpu"  # Windows doesn't support mps
        self.asr_device_combo.setCurrentText(self.audio_config.get("asr_device", default_device))
        self.asr_device_combo.currentTextChanged.connect(self.on_asr_setting_changed)
        layout.addWidget(device_label, 3, 0)
        layout.addWidget(self.asr_device_combo, 3, 1)
        

        
        # ASR Status
        self.asr_status = QLabel("Voice input disabled. Enable to speak to the AI instead of typing.")
        self.asr_status.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
        layout.addWidget(self.asr_status, 5, 0, 1, 2)
        
        # Initialize ASR status based on current config
        if self.audio_config.get("asr_enabled", False):
            self.asr_status.setText("Voice input enabled. You can now speak to the AI instead of typing.")
            self.asr_status.setStyleSheet(f"color: {self.colors['success']}; font-size: 10px; margin-top: 5px;")
        
        return group
    
    def create_status_section(self):
        """Create status section"""
        group = ModernGroupBox("📊 System Status")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 10, 8, 8)  # Much smaller margins
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(150)  # Reduced height
        self.status_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.colors['bg_light']};
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                padding: 12px;
                color: {self.colors['text_primary']};
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }}
        """)
        
        layout.addWidget(self.status_text)
        return group
    
    def create_buttons_section(self):
        """Create buttons section"""
        group = ModernGroupBox("")
        group.setTitle("")  # Remove title for buttons section
        layout = QHBoxLayout(group)
        layout.setSpacing(6)  # Much smaller spacing
        layout.setContentsMargins(8, 8, 8, 8)  # Much smaller margins
        
        refresh_button = ModernButton("🔄 Refresh", "#6366f1", "#4f46e5")  # Shorter text
        refresh_button.clicked.connect(self.refresh_devices)
        
        deps_button = ModernButton("🔍 Check", "#8b5cf6", "#7c3aed")  # Shorter text
        deps_button.clicked.connect(self.check_dependencies)
        
        save_button = ModernButton("💾 Save", "#10b981", "#059669")  # Shorter text
        save_button.clicked.connect(self.save_settings)
        
        start_button = ModernButton("🚀 Start", "#f59e0b", "#d97706")  # Shorter text
        start_button.clicked.connect(self.start_miko)
        
        layout.addWidget(refresh_button)
        layout.addWidget(deps_button)
        layout.addWidget(save_button)
        layout.addWidget(start_button)
        layout.addStretch()
        
        return group
    
    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #0e1118;
                color: #e8eaed;
            }}
            QWidget {{
                background-color: #0e1118;
                color: #e8eaed;
            }}
            QScrollArea {{
                background-color: #0e1118;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: #101521;
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #1a2232;
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #263146;
            }}
        """)

    def add_shadow(self, widget: QWidget, radius: int = 24):
        try:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(radius)
            effect.setXOffset(0)
            effect.setYOffset(0)
            effect.setColor(QColor(0, 0, 0, 110))
            widget.setGraphicsEffect(effect)
        except Exception as e:
            print(f"⚠️ Shadow effect error: {e}")
    
    def load_yaml_config(self):
        """Load configuration from YAML file"""
        try:
            if self.config_file.exists():
                import yaml
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.yaml_config = yaml.safe_load(f)
                print(f"✅ Loaded YAML config: {self.config_file}")
            else:
                self.yaml_config = {}
                print(f"⚠️ YAML config not found: {self.config_file}")
        except Exception as e:
            print(f"❌ Error loading YAML config: {e}")
            self.yaml_config = {}
    
    def load_personality(self):
        """Load personality data from YAML or fallback to JSON"""
        try:
            # Try to load from YAML first
            # Start with defaults
            self.personality = self.get_default_personality()
            
            # Try loading from YAML first, but only update non-empty values
            if hasattr(self, 'yaml_config') and 'personality' in self.yaml_config:
                yaml_personality = self.yaml_config['personality']
                for key, value in yaml_personality.items():
                    if value and value != '':  # Only use non-empty values
                        if key == 'voice_settings' and isinstance(value, dict):
                            # Merge voice settings
                            for voice_key, voice_value in value.items():
                                if voice_value and voice_value != '':
                                    self.personality['voice_settings'][voice_key] = voice_value
                        else:
                            self.personality[key] = value
                print("✅ Loaded personality from YAML with defaults")
            elif self.personality_file.exists():
                with open(self.personality_file, 'r') as f:
                    json_personality = json.load(f)
                    for key, value in json_personality.items():
                        if value and value != '':
                            self.personality[key] = value
                print("✅ Loaded personality from JSON with defaults")
            else:
                print("✅ Using default personality")
        except Exception as e:
            print(f"❌ Error loading personality: {e}")
            self.personality = self.get_default_personality()
    
    def load_audio_config(self):
        """Load audio configuration from YAML or fallback to JSON"""
        try:
            # Try to load from YAML first
            if hasattr(self, 'yaml_config') and 'audio_devices' in self.yaml_config:
                self.audio_config = self.yaml_config['audio_devices']
                print("✅ Loaded audio config from YAML")
            elif self.audio_config_file.exists():
                with open(self.audio_config_file, 'r') as f:
                    self.audio_config = json.load(f)
                print("✅ Loaded audio config from JSON file")
            else:
                self.audio_config = {
                    "input_device_name": "Default",
                    "output_device_name": "Default",
                    "device_index": None,
                    "asr_enabled": False,
                    "push_to_talk_key": "shift",
                    "asr_model": "base.en",
                    "asr_device": "cpu"  # Windows compatible default
                }
                print("✅ Using default audio config")
        except Exception as e:
            print(f"❌ Error loading audio config: {e}")
            self.audio_config = {
                "input_device_name": "Default", 
                "output_device_name": "Default",
                "device_index": None,
                "asr_enabled": False,
                "push_to_talk_key": "shift",
                "asr_model": "base.en",
                "asr_device": "cpu"  # Windows compatible default
            }
    
    def get_default_personality(self):
        """Default personality fallback"""
        return {
            "name": "Miko",
            "system_prompt": "You are Miko, an AI kitsune girl with a smug and teasing personality!",
            "greeting": "Oh, look who's here! I'm Miko!",
            "farewell": "Hmph, leaving already?",
            "error_message": "Ugh, my circuits are acting up!",
            "voice_settings": {
                "ref_audio_path": "main_sample.wav",
                "prompt_text": "Sample voice for Miko",
                "language": "en"
            }
        }
    
    def load_audio_devices(self):
        """Load available audio input and output devices"""
        try:
            self.input_devices, self.output_devices = get_audio_devices()
            self.default_input, self.default_output = get_default_devices()
        except Exception as e:
            print(f"Error loading audio devices: {e}")
            self.input_devices = []
            self.output_devices = []
            self.default_input = None
            self.default_output = None
    
    def log_status(self, message, message_type="info"):
        """Add message to status log with styling"""
        color_map = {
            "success": self.colors['success'],
            "error": self.colors['error'],
            "warning": self.colors['warning'],
            "info": self.colors['accent']
        }
        
        color = color_map.get(message_type, self.colors['text_primary'])
        html_message = f'<span style="color: {color};">{message}</span><br>'
        
        self.status_text.moveCursor(QTextCursor.MoveOperation.End)
        self.status_text.insertHtml(html_message)
        self.status_text.ensureCursorVisible()
    
    def check_dependencies(self):
        """Check dependencies in a separate thread"""
        self.status_text.clear()
        self.status_thread = StatusThread()
        self.status_thread.status_update.connect(self.log_status)
        self.status_thread.start()
    
    def refresh_devices(self):
        """Refresh the available audio devices"""
        self.load_audio_devices()
        
        # Update input device dropdown
        input_device_values = ["Default"] + [get_device_display_name(device) for device in self.input_devices]
        self.input_device_combo.clear()
        self.input_device_combo.addItems(input_device_values)
        
        # Update output device dropdown  
        output_device_values = ["Default"] + [get_device_display_name(device) for device in self.output_devices]
        self.output_device_combo.clear()
        self.output_device_combo.addItems(output_device_values)
        
        # Reset selections to Default if current selection is no longer valid
        current_input = self.input_device_combo.currentText()
        if current_input not in input_device_values:
            self.input_device_combo.setCurrentText("Default")
            
        current_output = self.output_device_combo.currentText()
        if current_output not in output_device_values:
            self.output_device_combo.setCurrentText("Default")
        
        QMessageBox.information(self, "Devices Refreshed", "Audio device list has been updated!")
        self.log_status("🔄 Audio devices refreshed", "success")
    
    def browse_audio_file(self):
        """Browse for reference audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Audio File",
            "",
            "Audio files (*.wav *.mp3 *.flac *.m4a);;All files (*.*)"
        )
        if file_path:
            self.ref_audio_input.setText(file_path)
            self.current_audio_file = file_path
            self.audio_status.setText(f"Audio file selected: {Path(file_path).name}")
            self.audio_status.setStyleSheet(f"color: {self.colors['success']}; font-size: 12px; margin-top: 10px;")
            self.log_status(f"📁 Selected audio: {Path(file_path).name}", "success")
            
            # Enable the audio tools buttons
            self.enable_audio_tools()
    
    def enable_audio_tools(self):
        """Enable or disable audio tools based on file selection"""
        audio_file = self.ref_audio_input.text()
        if audio_file and os.path.exists(audio_file):
            # Enable buttons
            self.play_button.setEnabled(True)
            self.transcribe_button.setEnabled(True)
            self.audio_status.setText(f"Audio file ready: {Path(audio_file).name}")
            self.audio_status.setStyleSheet(f"color: {self.colors['success']}; font-size: 10px; margin-top: 5px;")
        else:
            # Disable buttons
            self.play_button.setEnabled(False)
            self.transcribe_button.setEnabled(False)
            self.audio_status.setText("Select reference audio file to enable tools")
            self.audio_status.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
    
    def play_reference_audio(self):
        """Play the selected reference audio file"""
        audio_file = self.ref_audio_input.text()
        if not audio_file or not os.path.exists(audio_file):
            QMessageBox.critical(self, "Error", "Please select a valid reference audio file first!")
            return
            
        try:
            # Load and play the audio file
            audio_data, sample_rate = sf.read(audio_file)
            
            # Get selected output device
            output_device_name = self.output_device_combo.currentText()
            output_device_id = None
            
            if output_device_name != "Default":
                for device in self.output_devices:
                    if device['name'] == output_device_name:
                        output_device_id = device['id']
                        break
            
            sd.play(audio_data, samplerate=sample_rate, device=output_device_id)
            self.audio_status.setText("Playing reference audio...")
            self.audio_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 12px; margin-top: 10px;")
            self.log_status(f"🔊 Playing audio on: {output_device_name}", "info")
            
        except Exception as e:
            QMessageBox.critical(self, "Playback Error", f"Failed to play audio: {str(e)}")
            self.log_status(f"❌ Playback error: {e}", "error")
    
    def transcribe_reference_audio(self):
        """Transcribe the reference audio file using faster-whisper"""
        audio_file = self.ref_audio_input.text()
        if not audio_file or not os.path.exists(audio_file):
            QMessageBox.critical(self, "Error", "Please select a valid reference audio file first!")
            return
            
        try:
            self.audio_status.setText("Transcribing reference audio...")
            self.audio_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 12px; margin-top: 10px;")
            self.log_status("🎯 Starting transcription...", "info")
            
            # Load Whisper model and transcribe
            from faster_whisper import WhisperModel
            model = WhisperModel("base.en", device="cpu", compute_type="float32")
            
            segments, _ = model.transcribe(audio_file)
            transcription = " ".join([segment.text for segment in segments])
            
            # Update the reference text field
            self.ref_text_input.setPlainText(transcription.strip())
            
            self.audio_status.setText(f"Transcribed: {transcription[:50]}...")
            self.audio_status.setStyleSheet(f"color: {self.colors['success']}; font-size: 12px; margin-top: 10px;")
            self.log_status(f"✅ Transcription complete: {transcription[:50]}...", "success")
            QMessageBox.information(self, "Transcription Complete", f"Reference audio transcribed successfully!\n\nText: {transcription}")
            
        except Exception as e:
            QMessageBox.critical(self, "Transcription Error", f"Failed to transcribe: {str(e)}")
            self.audio_status.setText("Transcription failed")
            self.audio_status.setStyleSheet(f"color: {self.colors['error']}; font-size: 12px; margin-top: 10px;")
            self.log_status(f"❌ Transcription error: {e}", "error")
    
    

    
    def on_input_device_changed(self, device_name):
        """Handle input device selection change"""
        if device_name == "Default":
            self.input_device_info.setText("Using system default input device")
            self.input_device_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
            return
        
        # Find device details
        device_details = None
        for device in self.input_devices:
            if get_device_display_name(device) == device_name:
                from modules.audio_utils import get_device_details
                device_details = get_device_details(device)
                break
        
        if device_details:
            # Show device information
            device_type = device_details['type'].replace('_', ' ').title()
            channels = device_details['input_channels']
            
            info_text = f"Type: {device_type} | Channels: {channels}"
            
            # Add recommendations based on device type
            if device_details['type'] == 'microphone':
                info_text += " | 🎤 Great for voice input!"
            elif device_details['type'] == 'line_input':
                info_text += " | 🔌 Good for external audio sources"
            elif device_details['type'] == 'audio_interface':
                info_text += " | 🎛️ Professional quality!"
            elif device_details['type'] == 'aux_input':
                info_text += " | 🔌 Auxiliary input connection"
            
            self.input_device_info.setText(info_text)
            self.input_device_info.setStyleSheet(f"color: {self.colors['success']}; font-size: 10px; margin-top: 5px;")
        else:
            self.input_device_info.setText("Device information not available")
            self.input_device_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
    
    def initialize_asr_state(self):
        """Initialize ASR checkbox and button state"""
        if hasattr(self, 'asr_enable_checkbox'):
            is_enabled = self.asr_enable_checkbox.isChecked()
            if is_enabled:
                self.asr_status.setText("Voice input enabled. You can now speak to the AI instead of typing.")
                self.asr_status.setStyleSheet(f"color: {self.colors['success']}; font-size: 10px; margin-top: 5px;")
            else:
                self.asr_status.setText("Voice input disabled. Enable to use microphone commands.")
                self.asr_status.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
    
    def on_asr_enabled_changed(self, state):
        """Handle ASR enable/disable checkbox state change"""
        print(f"🔍 ASR Checkbox state changed: {state} (Checked={state == Qt.CheckState.Checked})")
        
        # Update the local audio config immediately
        self.audio_config["asr_enabled"] = (state == Qt.CheckState.Checked)
        
        # Update the YAML config immediately
        if hasattr(self, 'yaml_config'):
            if 'audio_devices' not in self.yaml_config:
                self.yaml_config['audio_devices'] = {}
            self.yaml_config['audio_devices']['asr_enabled'] = (state == Qt.CheckState.Checked)
            
            # Save to YAML file immediately
            try:
                import yaml
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(self.yaml_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                print(f"✅ YAML config updated immediately: asr_enabled = {state == Qt.CheckState.Checked}")
            except Exception as e:
                print(f"❌ Failed to update YAML immediately: {e}")
        
        if state == Qt.CheckState.Checked:
            self.asr_status.setText("Voice input enabled. You can now speak to the AI instead of typing.")
            self.asr_status.setStyleSheet(f"color: {self.colors['success']}; font-size: 10px; margin-top: 5px;")
            print("✅ ASR enabled")
        else:
            self.asr_status.setText("Voice input disabled. Enable to use microphone commands.")
            self.asr_status.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
            print("❌ ASR disabled")
    
    def on_asr_setting_changed(self, value):
        """Handle ASR setting changes and update YAML immediately"""
        try:
            # Determine which setting changed and update accordingly
            sender = self.sender()
            
            if sender == self.hotkey_combo:
                setting_key = "push_to_talk_key"
                setting_value = value
            elif sender == self.asr_model_combo:
                setting_key = "asr_model"
                setting_value = value
            elif sender == self.asr_device_combo:
                setting_key = "asr_device"
                setting_value = value
            else:
                return
            
            # Update local config
            self.audio_config[setting_key] = setting_value
            
            # Update YAML config immediately
            if hasattr(self, 'yaml_config'):
                if 'audio_devices' not in self.yaml_config:
                    self.yaml_config['audio_devices'] = {}
                self.yaml_config['audio_devices'][setting_key] = setting_value
                
                # Save to YAML file immediately
                import yaml
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(self.yaml_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                print(f"✅ YAML config updated immediately: {setting_key} = {setting_value}")
                
        except Exception as e:
            print(f"❌ Failed to update YAML for ASR setting: {e}")
    
    def refresh_ollama_models(self):
        """Refresh the list of available Ollama models"""
        try:
            self.log_status("🔄 Fetching Ollama models...", "info")
            self.ollama_models_combo.clear()
            self.ollama_models_combo.addItem("Loading models...")
            
            # Try to import ollama
            try:
                import ollama
            except ImportError:
                self.ollama_models_combo.clear()
                self.ollama_models_combo.addItem("❌ Ollama package not installed")
                self.log_status("❌ Ollama package not installed", "error")
                return
            
            # Check if Ollama service is running
            try:
                # Use proper Ollama API - returns ListResponse object
                models = ollama.list()
                
                # Get the models list from the ListResponse object
                if hasattr(models, 'models'):
                    models_list = models.models
                    self.log_status(f"✅ Found {len(models_list)} Ollama models", "success")
                else:
                    self.ollama_models_combo.clear()
                    self.ollama_models_combo.addItem("⚠️ No models found")
                    self.log_status("⚠️ No Ollama models found", "warning")
                    return
                
                # Clear and populate dropdown
                self.ollama_models_combo.clear()
                self.ollama_models_combo.addItem("Select a model...")
                
                # Categorize models by type
                model_categories = {
                    'llama': [],
                    'mistral': [],
                    'codellama': [],
                    'phi': [],
                    'gemma': [],
                    'qwen': [],
                    'granite': [],
                    'starcoder': [],
                    'nomic': [],
                    'other': []
                }
                
                # Sort models into categories
                for model in models_list:
                    # Model objects have attributes: model, size, modified_at, details
                    name = model.model  # This is the model name
                    size = model.size
                    size_mb = size / (1024 * 1024) if size > 0 else 0
                    
                    # Determine category based on model name and family
                    category = 'other'
                    if hasattr(model, 'details') and hasattr(model.details, 'family'):
                        family = model.details.family.lower()
                        if 'llama' in family:
                            category = 'llama'
                        elif 'mistral' in family:
                            category = 'mistral'
                        elif 'starcoder' in family:
                            category = 'starcoder'
                        elif 'granite' in family:
                            category = 'granite'
                        elif 'nomic' in family:
                            category = 'nomic'
                        elif 'qwen' in family:
                            category = 'qwen'
                        elif 'gemma' in family:
                            category = 'gemma'
                        elif 'phi' in family:
                            category = 'phi'
                    
                    # Fallback to name-based categorization if family not available
                    if category == 'other':
                        name_lower = name.lower()
                        if 'llama' in name_lower:
                            category = 'llama'
                        elif 'mistral' in name_lower:
                            category = 'mistral'
                        elif 'codellama' in name_lower or 'starcoder' in name_lower:
                            category = 'codellama'
                        elif 'phi' in name_lower:
                            category = 'phi'
                        elif 'gemma' in name_lower:
                            category = 'gemma'
                        elif 'qwen' in name_lower:
                            category = 'qwen'
                        elif 'granite' in name_lower:
                            category = 'granite'
                        elif 'nomic' in name_lower:
                            category = 'nomic'
                    
                    model_categories[category].append({
                        'name': name,
                        'size_mb': size_mb,
                        'size': size
                    })
                
                # Add categorized models to dropdown
                for category, models_list in model_categories.items():
                    if models_list:
                        # Sort by size (largest first)
                        models_list.sort(key=lambda x: x['size'], reverse=True)
                        
                        # Add category separator
                        if category != list(model_categories.keys())[0]:  # Skip separator for first category
                            self.ollama_models_combo.addItem("─" * 30)
                        
                        # Add models in this category
                        for model in models_list:
                            # Format display text with proper categorization
                            if category == 'llama':
                                display_text = f"🦙 {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'mistral':
                                display_text = f"🌪️ {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'codellama':
                                display_text = f"💻 {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'starcoder':
                                display_text = f"⭐ {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'granite':
                                display_text = f"🪨 {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'phi':
                                display_text = f"φ {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'gemma':
                                display_text = f"💎 {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'qwen':
                                display_text = f"🔮 {model['name']} ({model['size_mb']:.1f} MB)"
                            elif category == 'nomic':
                                display_text = f"📊 {model['name']} ({model['size_mb']:.1f} MB)"
                            else:
                                display_text = f"🤖 {model['name']} ({model['size_mb']:.1f} MB)"
                            
                            self.ollama_models_combo.addItem(display_text, userData=model['name'])
                
                self.log_status(f"✅ Loaded {len(models_list)} models in {len([c for c in model_categories.values() if c])} categories", "success")
                
            except Exception as e:
                if "Connection refused" in str(e) or "Failed to establish" in str(e):
                    self.ollama_models_combo.clear()
                    self.ollama_models_combo.addItem("❌ Ollama service not running")
                    self.log_status("❌ Ollama service not running", "error")
                else:
                    self.ollama_models_combo.clear()
                    self.ollama_models_combo.addItem(f"❌ Error: {str(e)[:30]}...")
                    self.log_status(f"❌ Failed to fetch models: {e}", "error")
                    
        except Exception as e:
            self.ollama_models_combo.clear()
            self.ollama_models_combo.addItem(f"❌ Unexpected error")
            self.log_status(f"❌ Unexpected error: {e}", "error")
    
    def save_settings(self):
        """Save all settings to both YAML and JSON files"""
        try:
            # Update personality data
            self.personality["name"] = self.name_input.text()
            self.personality["system_prompt"] = self.prompt_text.toPlainText()
            self.personality["greeting"] = self.greeting_input.text()
            self.personality["farewell"] = self.farewell_input.text()
            self.personality["voice_settings"]["ref_audio_path"] = self.ref_audio_input.text()
            self.personality["voice_settings"]["prompt_text"] = self.ref_text_input.toPlainText()
            self.personality["voice_settings"]["language"] = self.lang_combo.currentText()
            
            # Update audio config
            self.audio_config["input_device_name"] = self.input_device_combo.currentText()
            self.audio_config["output_device_name"] = self.output_device_combo.currentText()
            
            # Update ASR config
            self.audio_config["asr_enabled"] = self.asr_enable_checkbox.isChecked()
            self.audio_config["push_to_talk_key"] = self.hotkey_combo.currentText()
            self.audio_config["asr_model"] = self.asr_model_combo.currentText()
            self.audio_config["asr_device"] = self.asr_device_combo.currentText()
            
            # Update Ollama model selection
            selected_ollama_model = self.get_selected_ollama_model()
            if selected_ollama_model:
                if 'ollama_config' not in self.yaml_config:
                    self.yaml_config['ollama_config'] = {}
                self.yaml_config['ollama_config']['selected_model'] = selected_ollama_model
            
            # Find device index for output device (for compatibility)
            output_name = self.output_device_combo.currentText()
            if output_name != "Default":
                for device in self.output_devices:
                    if device['name'] == output_name:
                        self.audio_config["device_index"] = device['id']
                        break
            else:
                self.audio_config["device_index"] = None
            
            # Save to YAML file
            if hasattr(self, 'yaml_config'):
                import yaml
                # Update YAML config with new values
                if 'personality' not in self.yaml_config:
                    self.yaml_config['personality'] = {}
                if 'audio_devices' not in self.yaml_config:
                    self.yaml_config['audio_devices'] = {}
                if 'tts_config' not in self.yaml_config:
                    self.yaml_config['tts_config'] = {}
                
                self.yaml_config['personality'].update(self.personality)
                self.yaml_config['audio_devices'].update(self.audio_config)
                
                # Also update tts_config section for TTS module compatibility
                self.yaml_config['tts_config'].update({
                    'ref_audio_path': self.personality["voice_settings"]["ref_audio_path"],
                    'prompt_text': self.personality["voice_settings"]["prompt_text"],
                    'text_lang': self.personality["voice_settings"]["language"],
                    'prompt_lang': self.personality["voice_settings"]["language"]
                })
                
                # Save YAML
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(self.yaml_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                print(f"✅ Saved settings to YAML: {self.config_file}")
            
            # Save personality to JSON (for backward compatibility)
            os.makedirs("modules", exist_ok=True)
            with open(self.personality_file, 'w') as f:
                json.dump(self.personality, f, indent=2)
            
            # Save audio config to JSON (for backward compatibility)
            with open(self.audio_config_file, 'w') as f:
                json.dump(self.audio_config, f, indent=2)
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.log_status("✅ Settings saved!", "success")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
            self.log_status(f"❌ Save error: {e}", "error")
    
    def start_miko(self):
        """Start Miko VTuber with VRM loader"""
        try:
            # Save settings first
            self.save_settings()
            
            # Start VRM loader first (provides WebSocket server)
            self.log_status("🎭 Starting VRM loader...", "info")
            vrm_process = subprocess.Popen(["./vrmloader/vrmloader.exe"])
            
            # Wait a moment for VRM loader to start up
            import time
            time.sleep(2)
            
            # Start Miko
            self.log_status("🚀 Starting Miko...", "info")
            miko_process = subprocess.Popen([sys.executable, "miko.py"])
            
            QMessageBox.information(self, "Started", "VRM loader and Miko are starting up!\n\nVRM loader provides the WebSocket server that Miko connects to.\nCheck the console windows for both processes.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start services: {e}")
            self.log_status(f"❌ Start error: {e}", "error")


if __name__ == "__main__":
    # Enable High DPI scaling before creating the application
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    
    # Set High DPI scaling policy
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # Set application properties
    app.setApplicationName("Miko AI VTuber Setup")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    window = MikoSetupGUI()
    window.show()
    
    # Run the application
    sys.exit(app.exec())