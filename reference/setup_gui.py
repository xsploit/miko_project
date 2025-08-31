import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yaml
from pathlib import Path
import json
import os
import soundfile as sf
import sounddevice as sd
from audio_utils import get_audio_devices, get_device_display_name, get_default_devices

class ProviderSetupGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Riko Chat - Complete Setup")
        self.root.geometry("800x800")
        
        # Get config path
        self.config_path = Path(__file__).parent.parent / 'character_config.yaml'
        
        # Load existing config
        self.load_config()
        
        # Load audio devices
        self.load_audio_devices()
        
        # Audio processing state
        self.current_audio_file = None
        
        # Create GUI
        self.create_widgets()
        
    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except:
            # Default config if file doesn't exist
            self.config = {
                'provider': 'ollama',
                'providers': {
                    'openai': {'api_key': '', 'base_url': 'https://api.openai.com/v1', 'model': 'gpt-4o-mini'},
                    'openrouter': {'api_key': '', 'base_url': 'https://openrouter.ai/api/v1', 'model': 'meta-llama/llama-3.1-8b-instruct:free'},
                    'ollama': {'api_key': 'ollama', 'base_url': 'http://localhost:11434/v1', 'model': 'llama3.2'},
                    'gemini': {'api_key': '', 'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai', 'model': 'gemini-1.5-flash'}
                },
                'history_file': 'chat_history.json',
                'tts_enabled': False,
                'audio_config': {
                    'input_device_name': 'Default',
                    'output_device_name': 'Default'
                },
                'presets': {
                    'default': {
                        'system_prompt': 'You are a helpful assistant named Riko.\nYou speak like a snarky anime girl.\nAlways refer to the user as "senpai".'
                    }
                },
                'sovits_ping_config': {
                    'text_lang': 'en',
                    'prompt_lang': 'en',
                    'ref_audio_path': 'character_files/main_sample.wav',
                    'prompt_text': 'This is a sample voice for you to just get started with because it sounds kind of cute but just make sure this doesn\'t have long silences.'
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
    
    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="Riko Chat Configuration", font=("Arial", 18, "bold"))
        title_label.pack(pady=10)
        
        # Provider selection
        provider_frame = ttk.LabelFrame(self.root, text="LLM Provider")
        provider_frame.pack(pady=10, padx=20, fill="x")
        
        ttk.Label(provider_frame, text="Select Provider:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.provider_var = tk.StringVar(value=self.config.get('provider', 'ollama'))
        provider_combo = ttk.Combobox(provider_frame, textvariable=self.provider_var, 
                                     values=['openai', 'openrouter', 'ollama', 'gemini'],
                                     state="readonly", width=47)
        provider_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        provider_combo.bind('<<ComboboxSelected>>', self.on_provider_change)
        
        provider_frame.columnconfigure(1, weight=1)
        
        # Configuration frame
        self.config_frame = ttk.LabelFrame(self.root, text="Provider Configuration")
        self.config_frame.pack(pady=10, padx=20, fill="x")
        
        # API Key
        ttk.Label(self.config_frame, text="API Key:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(self.config_frame, textvariable=self.api_key_var, show="*", width=50)
        self.api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Base URL
        ttk.Label(self.config_frame, text="Base URL:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.base_url_var = tk.StringVar()
        self.base_url_entry = ttk.Entry(self.config_frame, textvariable=self.base_url_var, width=50)
        self.base_url_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Model
        ttk.Label(self.config_frame, text="Model:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.model_var = tk.StringVar()
        self.model_entry = ttk.Entry(self.config_frame, textvariable=self.model_var, width=50)
        self.model_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # TTS Enable/Disable
        ttk.Label(self.config_frame, text="Enable TTS:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.tts_enabled_var = tk.BooleanVar()
        self.tts_checkbox = ttk.Checkbutton(self.config_frame, variable=self.tts_enabled_var)
        self.tts_checkbox.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        self.config_frame.columnconfigure(1, weight=1)
        
        # Audio Configuration Frame
        self.audio_frame = ttk.LabelFrame(self.root, text="Audio Configuration")
        self.audio_frame.pack(pady=10, padx=20, fill="x")
        
        # Input device (microphone)
        ttk.Label(self.audio_frame, text="Input Device (Mic):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.input_device_var = tk.StringVar()
        input_device_values = ["Default"] + [get_device_display_name(device) for device in self.input_devices]
        self.input_device_combo = ttk.Combobox(self.audio_frame, textvariable=self.input_device_var, 
                                              values=input_device_values, state="readonly", width=47)
        self.input_device_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Output device (speakers/headphones)
        ttk.Label(self.audio_frame, text="Output Device (Audio):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.output_device_var = tk.StringVar()
        output_device_values = ["Default"] + [get_device_display_name(device) for device in self.output_devices]
        self.output_device_combo = ttk.Combobox(self.audio_frame, textvariable=self.output_device_var,
                                               values=output_device_values, state="readonly", width=47)
        self.output_device_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.audio_frame.columnconfigure(1, weight=1)
        
        # GPT-SoVITS Configuration Frame
        self.sovits_frame = ttk.LabelFrame(self.root, text="GPT-SoVITS Voice Configuration")
        self.sovits_frame.pack(pady=10, padx=20, fill="x")
        
        # Reference audio file path
        ttk.Label(self.sovits_frame, text="Reference Audio File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ref_audio_var = tk.StringVar()
        self.ref_audio_entry = ttk.Entry(self.sovits_frame, textvariable=self.ref_audio_var, width=40)
        self.ref_audio_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.sovits_frame, text="Browse", command=self.browse_audio_file).grid(row=0, column=2, padx=5, pady=5)
        
        # Reference text for the audio
        ttk.Label(self.sovits_frame, text="Reference Text:").grid(row=1, column=0, sticky="nw", padx=5, pady=5)
        self.ref_text_var = tk.StringVar()
        self.ref_text_entry = tk.Text(self.sovits_frame, height=3, width=40)
        self.ref_text_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Audio analysis section
        audio_tools_frame = ttk.Frame(self.sovits_frame)
        audio_tools_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=10)
        
        ttk.Label(audio_tools_frame, text="Reference Audio Tools:").pack(anchor="w")
        
        # Audio tools
        tools_frame = ttk.Frame(audio_tools_frame)
        tools_frame.pack(fill="x", pady=5)
        
        self.play_ref_button = ttk.Button(tools_frame, text="▶️ Play Reference", command=self.play_reference_audio)
        self.play_ref_button.pack(side="left", padx=5)
        
        self.transcribe_ref_button = ttk.Button(tools_frame, text="📝 Auto-Transcribe Reference", command=self.transcribe_reference_audio)
        self.transcribe_ref_button.pack(side="left", padx=5)
        
        # Status label
        self.audio_status = tk.Label(audio_tools_frame, text="Select reference audio file to enable tools", fg="gray")
        self.audio_status.pack(anchor="w", pady=5)
        
        # Language settings
        lang_frame = ttk.Frame(self.sovits_frame)
        lang_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        ttk.Label(lang_frame, text="Text Language:").pack(side="left")
        self.text_lang_var = tk.StringVar(value="en")
        text_lang_combo = ttk.Combobox(lang_frame, textvariable=self.text_lang_var, 
                                      values=["en", "zh", "ja", "ko"], state="readonly", width=5)
        text_lang_combo.pack(side="left", padx=5)
        
        ttk.Label(lang_frame, text="Prompt Language:").pack(side="left", padx=(20,0))
        self.prompt_lang_var = tk.StringVar(value="en")
        prompt_lang_combo = ttk.Combobox(lang_frame, textvariable=self.prompt_lang_var, 
                                        values=["en", "zh", "ja", "ko"], state="readonly", width=5)
        prompt_lang_combo.pack(side="left", padx=5)
        
        self.sovits_frame.columnconfigure(1, weight=1)
        
        # Info text
        info_frame = ttk.LabelFrame(self.root, text="Setup Instructions")
        info_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.info_text = tk.Text(info_frame, height=6, wrap=tk.WORD)
        self.info_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Refresh Devices", command=self.refresh_devices).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Test Connection", command=self.test_connection).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Save & Start Chat", command=self.save_and_start).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.root.quit).pack(side="left", padx=5)
        
        # Load current provider data
        self.on_provider_change()
    
    def on_provider_change(self, event=None):
        provider = self.provider_var.get()
        provider_config = self.config['providers'].get(provider, {})
        
        self.api_key_var.set(provider_config.get('api_key', ''))
        self.base_url_var.set(provider_config.get('base_url', ''))
        self.model_var.set(provider_config.get('model', ''))
        self.tts_enabled_var.set(self.config.get('tts_enabled', False))
        
        # Load audio device settings
        audio_config = self.config.get('audio_config', {})
        input_name = audio_config.get('input_device_name', 'Default')
        output_name = audio_config.get('output_device_name', 'Default')
        
        self.input_device_var.set(input_name)
        self.output_device_var.set(output_name)
        
        # Load GPT-SoVITS settings
        sovits_config = self.config.get('sovits_ping_config', {})
        self.ref_audio_var.set(sovits_config.get('ref_audio_path', ''))
        
        # Load reference text
        ref_text = sovits_config.get('prompt_text', '')
        self.ref_text_entry.delete("1.0", tk.END)
        self.ref_text_entry.insert("1.0", ref_text)
        
        # Load language settings
        self.text_lang_var.set(sovits_config.get('text_lang', 'en'))
        self.prompt_lang_var.set(sovits_config.get('prompt_lang', 'en'))
        
        # Update info text
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", self.get_provider_info())
    
    def get_provider_info(self):
        provider = self.provider_var.get()
        info = {
            'openai': "OpenAI API - Get your API key from https://platform.openai.com/api-keys\nModels: gpt-4o, gpt-4o-mini, gpt-3.5-turbo\n\nSetup: Enter your OpenAI API key above.",
            'openrouter': "OpenRouter - Get your API key from https://openrouter.ai/keys\nAccess to 100+ models including free options.\n\nSetup: Create account and get API key from OpenRouter.",
            'ollama': "Ollama (Local) - Make sure Ollama is running locally on port 11434\nNo API key needed. Download models with: ollama pull llama3.2\n\nSetup: Install Ollama and pull a model, then start it.",
            'gemini': "Google Gemini - Get your API key from https://aistudio.google.com/app/apikey\nModels: gemini-1.5-pro, gemini-1.5-flash\n\nSetup: Create Google AI Studio account and generate API key."
        }
        return info.get(provider, "Select a provider to see setup instructions.")
    
    def test_connection(self):
        # Save current settings temporarily for testing
        provider = self.provider_var.get()
        test_config = {
            'api_key': self.api_key_var.get(),
            'base_url': self.base_url_var.get(),
            'model': self.model_var.get()
        }
        
        # Test connection
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=test_config['api_key'],
                base_url=test_config['base_url']
            )
            
            response = client.chat.completions.create(
                model=test_config['model'],
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            
            messagebox.showinfo("Success", f"Connection successful!\nResponse: {response.choices[0].message.content}")
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Error: {str(e)}")
    
    def save_and_start(self):
        # Update config
        provider = self.provider_var.get()
        self.config['provider'] = provider
        self.config['providers'][provider]['api_key'] = self.api_key_var.get()
        self.config['providers'][provider]['base_url'] = self.base_url_var.get()
        self.config['providers'][provider]['model'] = self.model_var.get()
        self.config['tts_enabled'] = self.tts_enabled_var.get()
        
        # Save audio device settings (using names now)
        input_device_selection = self.input_device_var.get()
        output_device_selection = self.output_device_var.get()
        
        # Update config with device names
        if 'audio_config' not in self.config:
            self.config['audio_config'] = {}
        
        self.config['audio_config']['input_device_name'] = input_device_selection
        self.config['audio_config']['output_device_name'] = output_device_selection
        
        # Save GPT-SoVITS settings
        if 'sovits_ping_config' not in self.config:
            self.config['sovits_ping_config'] = {}
        
        self.config['sovits_ping_config']['ref_audio_path'] = self.ref_audio_var.get()
        self.config['sovits_ping_config']['prompt_text'] = self.ref_text_entry.get("1.0", tk.END).strip()
        self.config['sovits_ping_config']['text_lang'] = self.text_lang_var.get()
        self.config['sovits_ping_config']['prompt_lang'] = self.prompt_lang_var.get()
        
        # Validate required fields
        if not self.api_key_var.get() and provider != 'ollama':
            messagebox.showerror("Error", "API Key is required for this provider!")
            return
        
        # Save config
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            
            messagebox.showinfo("Success", "Configuration saved! Starting chat...")
            self.root.quit()
            
            # Start main chat
            import sys
            import subprocess
            subprocess.Popen([sys.executable, "main_chat.py"], cwd=self.config_path.parent / "server")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
    
    def refresh_devices(self):
        """Refresh the available audio devices"""
        self.load_audio_devices()
        
        # Update input device dropdown
        input_device_values = ["Default"] + [get_device_display_name(device) for device in self.input_devices]
        self.input_device_combo['values'] = input_device_values
        
        # Update output device dropdown  
        output_device_values = ["Default"] + [get_device_display_name(device) for device in self.output_devices]
        self.output_device_combo['values'] = output_device_values
        
        # Reset selections to Default if current selection is no longer valid
        current_input = self.input_device_var.get()
        if current_input not in input_device_values:
            self.input_device_var.set("Default")
            
        current_output = self.output_device_var.get()
        if current_output not in output_device_values:
            self.output_device_var.set("Default")
        
        messagebox.showinfo("Devices Refreshed", "Audio device list has been updated!")
    
    def browse_audio_file(self):
        """Browse for reference audio file"""
        file_path = filedialog.askopenfilename(
            title="Select Reference Audio File",
            filetypes=[("Audio files", "*.wav *.mp3 *.flac *.m4a"), ("All files", "*.*")]
        )
        if file_path:
            self.ref_audio_var.set(file_path)
            self.current_audio_file = file_path
            self.audio_status.config(text=f"Audio file selected: {Path(file_path).name}", fg="green")
    
    def play_reference_audio(self):
        """Play the selected reference audio file"""
        audio_file = self.ref_audio_var.get()
        if not audio_file or not os.path.exists(audio_file):
            messagebox.showerror("Error", "Please select a valid reference audio file first!")
            return
            
        try:
            # Load and play the audio file
            audio_data, sample_rate = sf.read(audio_file)
            
            # Get selected output device
            output_device_name = self.output_device_var.get()
            output_device_id = None
            
            if output_device_name != "Default":
                for device in self.output_devices:
                    if device['name'] == output_device_name:
                        output_device_id = device['id']
                        break
            
            sd.play(audio_data, samplerate=sample_rate, device=output_device_id)
            self.audio_status.config(text="Playing reference audio...", fg="blue")
            
        except Exception as e:
            messagebox.showerror("Playback Error", f"Failed to play audio: {str(e)}")
    
    def transcribe_reference_audio(self):
        """Transcribe the reference audio file using Whisper"""
        audio_file = self.ref_audio_var.get()
        if not audio_file or not os.path.exists(audio_file):
            messagebox.showerror("Error", "Please select a valid reference audio file first!")
            return
            
        try:
            self.audio_status.config(text="Transcribing reference audio...", fg="blue")
            self.root.update()
            
            # Load Whisper model and transcribe
            from faster_whisper import WhisperModel
            model = WhisperModel("base.en", device="cpu", compute_type="float32")
            
            segments, _ = model.transcribe(audio_file)
            transcription = " ".join([segment.text for segment in segments])
            
            # Update the reference text field
            self.ref_text_entry.delete("1.0", tk.END)
            self.ref_text_entry.insert("1.0", transcription.strip())
            
            self.audio_status.config(text=f"Transcribed: {transcription[:50]}...", fg="green")
            messagebox.showinfo("Transcription Complete", f"Reference audio transcribed successfully!\n\nText: {transcription}")
            
        except Exception as e:
            messagebox.showerror("Transcription Error", f"Failed to transcribe: {str(e)}")
            self.audio_status.config(text="Transcription failed", fg="red")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ProviderSetupGUI()
    app.run()