import threading
import sys
import time
import datetime
import subprocess

import psutil
import numpy as np
import sounddevice as sd
import speech_recognition as sr

from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QLabel
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import os
import webbrowser
import pyautogui
import requests
import pyttsx3
from PyQt5.QtWidgets import QScrollArea

from google import genai # for gemeni api
import requests
import pyttsx3
from google import genai

import json

MEMORY_FILE = "memory.json"

GEMINI_API_KEY = "..........................PM"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

memory = load_memory()


# jarvis profile

PROFILE_FILE = "jarvis_profile.json"

def load_profile():
    try:
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "assistant_name": "Jarvis",
            "owner_name": "sir",
            "speaking_style": "short, respectful, confident",
            "personality": "futuristic personal AI assistant",
            "reply_rule": "Always reply in one short natural sentence."
        }

profile = load_profile()


def save_profile():
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=4)

# ================= CUSTOM COMMANDS =================

CUSTOM_COMMANDS_FILE = "custom_commands.json"

def load_custom_commands():
    try:
        with open(CUSTOM_COMMANDS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_custom_commands(commands):
    with open(CUSTOM_COMMANDS_FILE, "w") as f:
        json.dump(commands, f, indent=4)

custom_commands = load_custom_commands()

def remember_custom_command(name, actions):
    name = name.lower().strip()

    action_list = []
    
    for action in actions.split(" and "):
        action = action.strip()
        if action:
            action_list.append(action)

    custom_commands[name] = action_list
    save_custom_commands(custom_commands)

    return f"Custom command {name} saved sir"

def run_custom_command(name):
    name = name.lower().strip()

    if name in custom_commands:
        return custom_commands[name]

    return None

# yaha s pehle wala he 

def remember_value(key, value):
    key = key.lower().strip()
    value = value.strip()
    memory[key] = value
    save_memory(memory)
    return f"I will remember that your {key} is {value}"

def recall_value(key):
    key = key.lower().strip()
    if key in memory:
        return f"Your {key} is {memory[key]}"
    return "I don't know that yet sir"

def ask_ollama(prompt):
    try:
        url = "http://localhost:11434/api/generate"

        data = {
            "model": "phi",
            "prompt": (
                f"You are {profile['assistant_name']}, a {profile['personality']}. "
                f"Your owner is {profile['owner_name']}. "
                f"Speaking style: {profile['speaking_style']}. "
                f"Rule: {profile['reply_rule']} "
                f"User said: {prompt}"
            ),
            "stream": False,
            "options": {
                "num_predict": 35,
                "temperature": 0.4
            }
        }

        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        return result.get("response", "Sorry sir, I could not respond.")

    except Exception as e:
        print("Ollama AI Error:", e)
        return None


def ask_gemini(prompt):
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"You are {profile['assistant_name']}, a {profile['personality']}. "
                f"Your owner is {profile['owner_name']}. "
                f"Speaking style: {profile['speaking_style']}. "
                f"Rule: {profile['reply_rule']} "
                f"User said: {prompt}"
            )
        )

        if response.text:
            return response.text.strip()

        return None

    except Exception as e:
        print("Gemini AI Error:", e)
        return None
    

    #gemini ka api yaha se he


def ask_ai(prompt):
    # Brain 1: Gemini main brain
    answer = ask_gemini(prompt)
    if answer:
        return answer

    # Brain 2: Ollama backup brain
    answer = ask_ollama(prompt)
    if answer:
        return answer

    return "Sorry sir, both AI brains are not responding."
    
def smart_open(target):
    target = target.lower().strip()

    # remove extra words
    target = target.replace("the ", "").replace("app", "").strip()

    # memory check
    if target in memory:
        target = memory[target]

    # common apps
    app_commands = {
        "spotify": "spotify:",
        "instagram": "instagram:",
        "chrome": "chrome",
        "notepad": "notepad",
        "calculator": "calc",
        "vs code": "code",
        "vscode": "code"
    }

    try:
        if target in app_commands:
            os.system(f'start "" "{app_commands[target]}"')
            return f"Opening {target} sir"

        os.system(f'start "" "{target}"')
        return f"Opening {target} sir"

    except Exception:
        try:
            webbrowser.open(f"https://www.google.com/search?q={target}")
            return f"Searching {target} sir"
        except:
            return "I could not open that sir"

def smart_close(target):
    target = target.lower().strip()
    target = target.replace("the ", "").replace("app", "").strip()

    app_processes = {
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "vs code": ["Code.exe"],
        "vscode": ["Code.exe"],
        "code": ["Code.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["CalculatorApp.exe", "calc.exe"],
        "spotify": ["Spotify.exe"],
        "instagram": ["Instagram.exe", "ApplicationFrameHost.exe"],
        "whatsapp": ["WhatsApp.exe", "ApplicationFrameHost.exe"]
    }

    if target == "all":
        closed = []
        for app_name, processes in app_processes.items():
            for process in processes:
                os.system(f'taskkill /f /im "{process}" >nul 2>&1')
            closed.append(app_name)

        return "Closing all opened apps sir"

    if target in app_processes:
        for process in app_processes[target]:
            os.system(f'taskkill /f /im "{process}" >nul 2>&1')
        return f"Closing {target} sir"

    return "I don't know how to close that yet sir"


# ===================== AUDIO LEVEL THREAD =====================
class AudioLevelThread(QThread):
    level_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        def callback(indata, frames, time_info, status):
            if not self._running:
                return
            try:
                volume = np.linalg.norm(indata) * 10
                level = min(int(volume), 60)
                self.level_changed.emit(level)
            except Exception:
                self.level_changed.emit(0)

        try:
            with sd.InputStream(callback=callback):
                self.status_changed.emit("AUDIO MONITOR ACTIVE")
                while self._running:
                    self.msleep(50)
        except Exception:
            self.status_changed.emit("MIC LEVEL ERROR")


# ===================== SPEECH THREAD =====================
class SpeechThread(QThread):
    heard_text = pyqtSignal(str)
    command_text = pyqtSignal(str)
    response_text = pyqtSignal(str)
    status_text = pyqtSignal(str)
    wake_detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = True
        self.active_mode = False

    def stop(self):
        self._running = False

    def process_command(self, text: str):
        lower = text.lower().strip()
        self.command_text.emit(lower)

    # EXIT / SLEEP
        if "exit" in lower or "go to sleep" in lower or "stop listening" in lower:
            self.active_mode = False
            self.response_text.emit("Going to sleep sir")
            self.status_text.emit("STATUS : STANDBY")
            return
        

                # ===== CUSTOM COMMAND SAVE =====
        elif lower.startswith("remember command "):

            try:
                text = lower.replace("remember command ", "", 1)

                if " as " not in text:
                    self.response_text.emit(
                        "Please say remember command study mode as open chrome and open youtube"
                    )
                    return

                name, actions = text.split(" as ", 1)

                result = remember_custom_command(name, actions)

                self.response_text.emit(result)

            except Exception as e:
                print(e)
                self.response_text.emit("Error saving custom command sir")

        # ===== RUN CUSTOM COMMAND =====
        elif lower in custom_commands:

            actions = run_custom_command(lower)

            if actions:

                self.response_text.emit(f"Running {lower} sir")

                for action in actions:
                   self.process_command(action)

            else:
               self.response_text.emit("Command not found sir")        
        

    # WEBSITES
        elif "open youtube" in lower:
            import random
            webbrowser.open("https://youtube.com")
            responses = [
                "Opening youtube sir",
                "Launching youtube",
                "youtube is ready",
                "Done, opening youtube now"
            ]

            self.response_text.emit(random.choice(responses))

        elif "open google" in lower:
            import random
            webbrowser.open("https://google.com")
            responses = [
                "Opening google sir",
                "Launching google",
                "google is ready",
                "Done, opening google now"
            ]

            self.response_text.emit(random.choice(responses))

        elif "open whatsapp" in lower:
            import random
            webbrowser.open("https://web.whatsapp.com")
            responses = [
                "Opening whatsapp sir",
                "Launching whatsapp",
                "whatsapp is ready",
                "Done, opening whatsapp now"
            ]

            self.response_text.emit(random.choice(responses))

    # APPS
        elif "open chrome" in lower:
            import random
            os.system("start chrome")

            responses = [
                "Opening Chrome sir",
                "Launching Chrome",
                "Chrome is ready",
                "Done, opening Chrome now"
            ]

            self.response_text.emit(random.choice(responses))

        elif "open notepad" in lower:
            import random
            os.system("start notepad")
            responses = [
                "Opening notepad sir",
                "Launching notepad",
                "notepad is ready",
                "Done, opening notepad now"
            ]

            self.response_text.emit(random.choice(responses))

        elif "open calculator" in lower:
            import random
            os.system("start calc")
            responses = [
                "Opening calculator sir",
                "Launching calculator",
                "calculator is ready",
                "Done, opening calculator now"
            ]

            self.response_text.emit(random.choice(responses))

        elif "open vs code" in lower or "open vscode" in lower:
            import random
            os.system("code")
            responses = [
                "Opening vs code sir",
                "Launching vs code",
                "vs code is ready",
                "Done, opening vs code now"
            ]

            self.response_text.emit(random.choice(responses))

    # FOLDERS
        elif "open downloads" in lower:
            import random
            os.startfile(os.path.join(os.path.expanduser("~"), "Downloads"))
            responses = [
                "Opening downloads sir",
                "Launching downloads",
                "downloads is ready",
                "Done, opening downloads now"
            ]

            self.response_text.emit(random.choice(responses))

        elif "open desktop" in lower:
            import random
            os.startfile(os.path.join(os.path.expanduser("~"), "Desktop"))
            responses = [
                "Opening destop sir",
                "Launching destop",
                "destop is ready",
                "Done, opening destop now"
            ]

            self.response_text.emit(random.choice(responses))

        elif "open " in lower:
            target = lower.split("open ", 1)[1].strip()
            result = smart_open(target)
            self.response_text.emit(result)

    # CLOSE
        elif lower.startswith("close "):
            target = lower.replace("close ", "", 1).strip()
            result = smart_close(target)
            self.response_text.emit(result)
        

    # TIME
        elif "what time is it" in lower or "tell me the time" in lower or "time" == lower:
            now = datetime.datetime.now().strftime("%H:%M")
            self.response_text.emit(f"The time is {now} sir")

    # SCREENSHOT
        elif "screenshot" in lower:
            path = os.path.join(os.path.expanduser("~"), "Desktop", f"screenshot_{int(time.time())}.png")
            img = pyautogui.screenshot()
            img.save(path)
            self.response_text.emit("Screenshot saved on desktop sir")

    # BATTERY
        elif "battery" in lower:
            battery = psutil.sensors_battery()
            percent = battery.percent if battery else "unknown"
            self.response_text.emit(f"Battery is at {percent} percent sir")

    # VOLUME
        elif "volume up" in lower:
            pyautogui.press("volumeup")
            self.response_text.emit("Volume increased sir")

        elif "volume down" in lower:
            pyautogui.press("volumedown")
            self.response_text.emit("Volume decreased sir")

        elif "mute" in lower:
            pyautogui.press("volumemute")
            self.response_text.emit("Volume muted sir")

    # SHUTDOWN
        elif "shutdown" in lower:
            os.system("shutdown /s /t 5")
            self.response_text.emit("Shutting down system sir")

        # ===== MEMORY SAVE =====
        elif lower.startswith("remember that my "):
            try:
                text = lower.replace("remember that my ", "", 1).strip()

                if " is " in text:
                    key, value = text.split(" is ", 1)
                elif " name is " in text:
                    key, value = text.split(" name is ", 1)
                    key = key + " name"
                else:
                    self.response_text.emit("Please say it like remember that my college is XYZ")
                    return

                self.response_text.emit(remember_value(key, value))
            except Exception:
                self.response_text.emit("Sorry sir, I could not save that")

        elif lower.startswith("my ") and " is " in lower:
            try:
                text = lower.replace("my ", "", 1).strip()
                key, value = text.split(" is ", 1)
                self.response_text.emit(remember_value(key, value))
            except Exception:
                self.response_text.emit("Sorry sir, I could not save that")

        elif lower.startswith("what is my "):
            try:
                key = lower.replace("what is my ", "", 1).strip()
                self.response_text.emit(recall_value(key))
            except Exception:
                self.response_text.emit("Error reading memory")

        elif lower.startswith("who is my "):
            try:
                key = lower.replace("who is my ", "", 1).strip()
                self.response_text.emit(recall_value(key))
            except Exception:
                self.response_text.emit("Error reading memory")


        # ===== CHANGE PERSONALITY =====
        elif lower.startswith("set personality to "):

            try:
                new_personality = lower.replace(
                    "set personality to ",
                    "",
                    1
                ).strip()

                profile["personality"] = new_personality

                save_profile()

                self.response_text.emit(
                    f"Personality changed to {new_personality} sir"
                )

            except Exception:
                self.response_text.emit(
                    "Could not change personality sir"
                )


    # AI FALLBACK
        else:
            if len(lower.split()) <= 1:
                self.response_text.emit("Please say a little more clearly sir")
                self.status_text.emit("STATUS : ACTIVATED")
                return

            import time

            self.status_text.emit("STATUS : THINKING")
            time.sleep(0.4)

            answer = ask_ai(lower)

            self.response_text.emit(answer)
            self.status_text.emit("STATUS : ACTIVATED")

    def run(self):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.pause_threshold = 0.8

        try:
            mic = sr.Microphone()
        except Exception:
            self.status_text.emit("STATUS : MICROPHONE ERROR")
            return

        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.6)
        except Exception:
            self.status_text.emit("STATUS : MIC INIT ERROR")
            return

        self.status_text.emit("STATUS : LISTENING")

        while self._running:
            try:
                with mic as source:
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)

                text = recognizer.recognize_google(audio)
                self.heard_text.emit(text)

                lower = text.lower().strip()

                if "hello jarvis" in lower or "wake up jarvis" in lower:
                    self.active_mode = True
                    self.wake_detected.emit()
                    self.status_text.emit("STATUS : ACTIVATED")
                    continue

                if self.active_mode:
                    self.status_text.emit("STATUS : LISTENING")
                    self.process_command(lower)
                else:
                    self.status_text.emit("STATUS : STANDBY")

            except sr.WaitTimeoutError:
                self.status_text.emit("STATUS : LISTENING")
            except sr.UnknownValueError:
                self.status_text.emit("STATUS : LISTENING")
            except sr.RequestError:
                self.status_text.emit("STATUS : SPEECH API ERROR")
                time.sleep(1)
            except Exception:
                self.status_text.emit("STATUS : LISTENING")
                time.sleep(0.2)


# ===================== CENTER CORE =====================
class RotatingCore(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pulse = 0
        self.pulse_dir = 1
        self.voice_level = 0
        self.boost = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_core)
        self.timer.start(40)

    def set_voice_level(self, level: int):
        self.voice_level = level

    def trigger_effect(self):
        self.boost = 35

    def animate_core(self):
        self.pulse += self.pulse_dir
        if self.pulse > 16 or self.pulse < 0:
            self.pulse_dir *= -1

        if self.boost > 0:
            self.boost -= 2

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx = self.width() // 2
        cy = self.height() // 2
        p.translate(cx, cy)

        dynamic = self.pulse + int(self.voice_level * 0.6) + self.boost
        base_size = 180 + dynamic

        # outer clean rings
        for i in range(16):
            alpha = max(20, 190 - i * 10)
            size = base_size + i * 11
            p.setPen(QPen(QColor(0, 255, 255, alpha), 2))
            p.drawEllipse(-size // 2, -size // 2, size, size)

        # voice wave accent
        if self.voice_level > 8:
            for i in range(4):
                wave = 240 + i * 22 + self.voice_level
                alpha = max(20, 120 - i * 20)
                p.setPen(QPen(QColor(140, 255, 255, alpha), 2))
                p.drawEllipse(-wave // 2, -wave // 2, wave, wave)

        # main core
        p.setPen(QPen(QColor(0, 255, 255), 4))
        p.drawEllipse(-95, -95, 190, 190)

        # internal cross
        p.drawLine(0, -60, 0, 60)
        p.drawLine(-60, 0, 60, 0)

        # small inner circle
        p.drawEllipse(-28, -28, 56, 56)


# ===================== LEFT PANEL CIRCLE =====================
class CircleWidget(QWidget):
    def __init__(self, text_func, label="", big=False, parent=None):
        super().__init__(parent)
        self.text_func = text_func
        self.label = label
        self.big = big

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(5, 5, -5, -5)
        p.setPen(QPen(QColor(0, 255, 255), 3))
        p.drawEllipse(rect)

        p.setPen(QColor(0, 255, 255))

        if self.big:
            p.setFont(QFont("Consolas", 18, QFont.Bold))
        else:
            p.setFont(QFont("Consolas", 9, QFont.Bold))

        text = self.text_func()

        if self.label:
            draw_text = f"{self.label}\n{text}"
        else:
            draw_text = text

        p.drawText(self.rect(), Qt.AlignCenter, draw_text)


# ===================== WAVEFORM WIDGET =====================
class WaveformWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0
        self.bars = [8] * 24

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_idle)
        self.timer.start(50)

    def set_level(self, level: int):
        self.level = level

    def animate_idle(self):
        target = max(6, min(50, self.level))
        self.bars.pop(0)
        self.bars.append(target)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), Qt.transparent)

        width = self.width()
        height = self.height()
        bar_count = len(self.bars)
        gap = 4
        bar_w = max(3, (width - gap * (bar_count - 1)) // bar_count)

        x = 0
        center_y = height // 2

        for value in self.bars:
            bar_h = max(8, min(height - 6, value))
            y = center_y - bar_h // 2
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 255, 255, 210))
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)
            x += bar_w + gap

class SideVoiceWave(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0
        self.active = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def trigger(self):
        self.active = True
        self.level = 70

    def animate(self):
        if self.active:
            self.level -= 1
            if self.level <= 0:
                self.active = False
                self.level = 0
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        center = h // 2

        for i in range(24):
            val = self.level + np.random.randint(-8, 9)
            val = max(6, val)

            x = i * (w // 24)
            p.setPen(QPen(QColor(0, 255, 255, 200), 3))
            p.drawLine(x, center - val, x, center + val)


# ===================== MAIN UI =====================
class JarvisUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.is_speaking = False # abhi add kiya he 

        self.setWindowTitle("JARVIS AI")
        self.setGeometry(100, 100, 1450, 820)
        self.setStyleSheet("background-color: black;")

        self.panel_glow = 0
        self.panel_dir = 1
        self.current_heard = "NONE"
        self.current_response = "WAITING"
        self.current_status = "STATUS : LISTENING"
        
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", 185)
        self.tts_engine.setProperty("volume", 1.0)

        # panels + center elements
        self.left_panel = QFrame(self)
        self.right_panel = QFrame(self)
        self.core = RotatingCore(self)

        self.left_wave = SideVoiceWave(self)
        self.right_wave = SideVoiceWave(self)

        self.top_title = QLabel("JARVIS AI", self)
        self.top_title.setStyleSheet("color: cyan;")
        self.top_title.setFont(QFont("Consolas", 24, QFont.Bold))
        self.top_title.setAlignment(Qt.AlignCenter)

        self.speaking_label = QLabel("SPEAKING", self)
        self.speaking_label.setStyleSheet("color: cyan;")
        self.speaking_label.setFont(QFont("Consolas", 11, QFont.Bold))
        self.speaking_label.setAlignment(Qt.AlignCenter)

        self.listening_label = QLabel("LISTENING", self)
        self.listening_label.setStyleSheet("color: cyan;")
        self.listening_label.setFont(QFont("Consolas", 11, QFont.Bold))
        self.listening_label.setAlignment(Qt.AlignCenter)

        self.bottom_center_label = QLabel("J.A.R.V.I.S SYSTEM ACTIVE", self)
        self.bottom_center_label.setStyleSheet("color: cyan;")
        self.bottom_center_label.setFont(QFont("Consolas", 12, QFont.Bold))
        self.bottom_center_label.setAlignment(Qt.AlignCenter)

        # -------- LEFT PANEL --------
        self.left_title = QLabel("SYSTEM", self.left_panel)
        self.left_title.setStyleSheet("color: cyan; border:none;")
        self.left_title.setFont(QFont("Consolas", 17, QFont.Bold))
        self.left_title.setAlignment(Qt.AlignCenter)

        # ===== SPEAKING TEXT (NEW ADD) =====
        self.speaking_text = QLabel("...", self)
        self.speaking_text.setStyleSheet("color: cyan; border:none;")
        self.speaking_text.setFont(QFont("Consolas", 10, QFont.Bold))
        self.speaking_text.setAlignment(Qt.AlignCenter)

        self.date_circle = CircleWidget(
            lambda: datetime.datetime.now().strftime("%d\n%b"),
            big=True,
            parent=self.left_panel
        )

        self.cpu_circle = CircleWidget(
            lambda: f"{int(psutil.cpu_percent())}%",
            label="CPU",
            parent=self.left_panel
        )

        self.ram_circle = CircleWidget(
            lambda: f"{int(psutil.virtual_memory().percent)}%",
            label="RAM",
            parent=self.left_panel
        )

        self.left_box1 = QFrame(self.left_panel)
        self.left_box2 = QFrame(self.left_panel)

        self.left_status_text = QLabel(self.left_box1)
        self.left_status_text.setStyleSheet("color: cyan; border:none;")
        self.left_status_text.setFont(QFont("Consolas", 10))
        self.left_status_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.left_extra_text = QLabel(self.left_box2)
        self.left_extra_text.setStyleSheet("color: cyan; border:none;")
        self.left_extra_text.setFont(QFont("Consolas", 10))
        self.left_extra_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # -------- RIGHT PANEL --------
        self.right_title = QLabel("VOICE COMMAND", self.right_panel)
        self.right_title.setStyleSheet("color: cyan; border:none;")
        self.right_title.setFont(QFont("Consolas", 16, QFont.Bold))
        self.right_title.setAlignment(Qt.AlignCenter)

        self.wake_word_label = QLabel("WAKE WORD", self.right_panel)
        self.wake_word_label.setStyleSheet("color: rgba(0,255,255,180); border:none;")
        self.wake_word_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.wake_word_label.setAlignment(Qt.AlignCenter)

        self.hello_label = QLabel("HELLO JARVIS", self.right_panel)
        self.hello_label.setStyleSheet("color: cyan; border:none;")
        self.hello_label.setFont(QFont("Consolas", 16, QFont.Bold))
        self.hello_label.setAlignment(Qt.AlignCenter)

        self.command_title = QLabel("COMMAND", self.right_panel)
        self.command_title.setStyleSheet("color: rgba(0,255,255,180); border:none;")
        self.command_title.setFont(QFont("Consolas", 9, QFont.Bold))
        self.command_title.setAlignment(Qt.AlignCenter)

        self.command_box = QFrame(self.right_panel)
        self.command_text = QLabel(self.command_box)
        self.command_text.setStyleSheet("color: cyan; border:none;")
        self.command_text.setFont(QFont("Consolas", 10, QFont.Bold))
        self.command_text.setAlignment(Qt.AlignCenter)
        self.command_text.setWordWrap(True)
        self.command_text.setText("NONE")

        self.status_title = QLabel("STATUS", self.right_panel)
        self.status_title.setStyleSheet("color: rgba(0,255,255,180); border:none;")
        self.status_title.setFont(QFont("Consolas", 9, QFont.Bold))
        self.status_title.setAlignment(Qt.AlignCenter)

        self.status_box = QFrame(self.right_panel)
        self.status_text = QLabel(self.status_box)
        self.status_text.setStyleSheet("color: cyan; border:none;")
        self.status_text.setFont(QFont("Consolas", 10, QFont.Bold))
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setText(self.current_status)

        self.wave_widget = WaveformWidget(self)

        self.response_title = QLabel("RESPONSE", self.right_panel)
        self.response_title.setStyleSheet("color: rgba(0,255,255,180); border:none;")
        self.response_title.setFont(QFont("Consolas", 9, QFont.Bold))
        self.response_title.setAlignment(Qt.AlignCenter)

        self.response_box = QFrame(self.right_panel)

        self.scroll_area = QScrollArea(self.response_box)  # yaha se leke
        self.scroll_area.setStyleSheet("border:none;")
        self.scroll_area.setWidgetResizable(True)

        self.response_text = QLabel()
        self.response_text.setStyleSheet("color: cyan; border:none;")
        self.response_text.setFont(QFont("Consolas", 10, QFont.Bold))
        self.response_text.setWordWrap(True)
        self.response_text.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.response_text)  # yaha tk
        # timers
        self.info_timer = QTimer()
        self.info_timer.timeout.connect(self.update_left_info)
        self.info_timer.start(1000)

        self.panel_timer = QTimer()
        self.panel_timer.timeout.connect(self.animate_panels)
        self.panel_timer.start(50)

        # threads
        self.audio_thread = AudioLevelThread()
        self.audio_thread.level_changed.connect(self.on_audio_level)
        self.audio_thread.status_changed.connect(self.on_audio_status)
        self.audio_thread.start()

        self.speech_thread = SpeechThread()
        self.speech_thread.heard_text.connect(self.on_heard_text)
        self.speech_thread.command_text.connect(self.on_command_text)
        self.speech_thread.response_text.connect(self.on_response_text)
        self.speech_thread.status_text.connect(self.on_status_text)
        self.speech_thread.wake_detected.connect(self.on_wake_detected)
        self.speech_thread.start()

    def show_thinking(self):
        self.response_text.setText("Thinking.")
        QTimer.singleShot(300, lambda: self.response_text.setText("Thinking.."))
        QTimer.singleShot(600, lambda: self.response_text.setText("Thinking..."))    

    def speak_async(self, text):
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()

    def speak(self, text):
        try:
            self.is_speaking = True

            self.current_response = text

            QTimer.singleShot(0, lambda: self.response_text.setText(text))
            QTimer.singleShot(0, self.left_wave.trigger)
            QTimer.singleShot(0, self.right_wave.trigger)
            QTimer.singleShot(0, self.core.trigger_effect)

            self.tts_engine.stop()
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()

            self.is_speaking = False

        except Exception as e:
            print("Voice Error:", e)
            self.is_speaking = False

    # ---------- callbacks ----------
    def on_audio_level(self, level):
        self.core.set_voice_level(level)
        self.wave_widget.set_level(level)

    def on_audio_status(self, text):
        pass

    def on_heard_text(self, text):
        self.current_heard = text.upper()
        self.speaking_text.setText(f"USER → {self.current_heard}")

    def on_command_text(self, text):
        self.command_text.setText(text.upper())

# 🔥 IMPORTANT: interrupt speech
        if self.is_speaking:
            self.tts_engine.stop()
            self.is_speaking = False

    def on_response_text(self, text):
        self.current_response = text

        if "opening" in text.lower():
            self.status_text.setText("STATUS : EXECUTING")
        elif "battery" in text.lower():
            self.status_text.setText("STATUS : ANALYZING")
        elif "sorry" in text.lower():
            self.status_text.setText("STATUS : ERROR")
        else:
            self.status_text.setText("STATUS : RESPONDING")

        self.response_text.setText(text)
        self.speak_async(text)

    def on_status_text(self, text):
        self.current_status = text
        self.status_text.setText(text)

    def on_wake_detected(self):
        self.core.trigger_effect()
        self.left_wave.trigger()
        self.right_wave.trigger()

        self.status_text.setText("STATUS : ACTIVATED")

        QTimer.singleShot(200, lambda: self.speak_async("Yes sir"))

    # ---------- left info ----------
    def update_left_info(self):
        now = datetime.datetime.now()

        self.left_status_text.setText(
            f"STATUS : ONLINE\n"
            f"TIME   : {now.strftime('%H:%M:%S')}\n"
            f"DATE   : {now.strftime('%d-%m-%Y')}\n"
            f"MODE   : ACTIVE"
        )

        battery = psutil.sensors_battery()
        bat_percent = f"{battery.percent}%" if battery else "N/A"
        power = "PLUGGED" if battery and battery.power_plugged else "UNPLUGGED"

        self.left_extra_text.setText(
            f"DRIVE  : C:\\\n"
            f"BAT    : {bat_percent}\n"
            f"POWER  : {power}"
        )

    # ---------- panel glow ----------
    def animate_panels(self):
        self.panel_glow += self.panel_dir
        if self.panel_glow > 20 or self.panel_glow < 0:
            self.panel_dir *= -1

        alpha = 150 + self.panel_glow

        panel_style = f"""
        QFrame {{
            border: 2px solid rgba(0,255,255,{alpha});
            border-radius: 14px;
            background-color: rgba(0,0,0,0);
        }}
        """

        inner_style = """
        QFrame {
            border: 1px solid rgba(0,255,255,120);
            border-radius: 10px;
            background-color: rgba(0,0,0,0);
        }
        """

        self.left_panel.setStyleSheet(panel_style)
        self.right_panel.setStyleSheet(panel_style)

        self.left_box1.setStyleSheet(inner_style)
        self.left_box2.setStyleSheet(inner_style)
        self.command_box.setStyleSheet(inner_style)
        self.status_box.setStyleSheet(inner_style)
        self.response_box.setStyleSheet(inner_style)

    # ---------- layout ----------
    def resizeEvent(self, event):
        w = self.width()
        h = self.height()

        panel_w = 290
        panel_h = int(h * 0.78)

        left_x = 35
        right_x = w - panel_w - 35
        panel_y = (h - panel_h) // 2 + 20

        self.left_panel.setGeometry(left_x, panel_y, panel_w, panel_h)
        self.right_panel.setGeometry(right_x, panel_y, panel_w, panel_h)

        # center
        core_size = 430
        core_x = (w - core_size) // 2
        core_y = (h - core_size) // 2 + 5
        self.core.setGeometry(core_x, core_y, core_size, core_size)

        self.top_title.setGeometry((w // 2) - 220, 35, 440, 40)
        # ===== BOTTOM CENTER =====
        self.bottom_center_label.setGeometry((w // 2) - 220, h - 70, 440, 30)

        # ===== SPEAKING SIDE =====
        self.speaking_label.setGeometry(w//2 - 300, h - 120, 120, 25)
        self.speaking_text.setGeometry(w//2 - 300, h - 90, 140, 25)

        # ===== LISTENING SIDE =====
        self.listening_label.setGeometry(w//2 + 180, h - 120, 120, 25)
        self.wave_widget.setGeometry(w//2 + 180, h - 90, 140, 40)

        # left panel internals
        self.left_title.setGeometry(0, 18, panel_w, 28)
        self.date_circle.setGeometry((panel_w - 170) // 2, 60, 170, 170)
        self.cpu_circle.setGeometry(35, 245, 90, 90)
        self.ram_circle.setGeometry(panel_w - 125, 245, 90, 90)

        self.left_box1.setGeometry(22, 360, panel_w - 44, 115)
        self.left_status_text.setGeometry(14, 10, panel_w - 72, 95)

        self.left_box2.setGeometry(22, 495, panel_w - 44, 110)
        self.left_extra_text.setGeometry(14, 10, panel_w - 72, 90)

        # right panel internals
        self.right_title.setGeometry(0, 18, panel_w, 28)
        self.wake_word_label.setGeometry(0, 62, panel_w, 20)
        self.hello_label.setGeometry(0, 85, panel_w, 32)

        self.command_title.setGeometry(0, 130, panel_w, 20)
        self.command_box.setGeometry(22, 154, panel_w - 44, 72)
        self.command_text.setGeometry(12, 8, panel_w - 68, 56)

        self.status_title.setGeometry(0, 238, panel_w, 20)
        self.status_box.setGeometry(22, 262, panel_w - 44, 56)
        self.status_text.setGeometry(8, 8, panel_w - 60, 40)

        # self.wave_widget.setGeometry(26, 334, panel_w - 52, 95) need pe change

        self.response_title.setGeometry(0, 445, panel_w, 20)
        self.response_box.setGeometry(22, 450, panel_w - 44, 160)
        self.scroll_area.setGeometry(10, 10, panel_w - 64, 140)

        self.left_wave.setGeometry(
           core_x - 220,
           core_y + core_size//2 - 60,
           190,
           120
        )

        self.right_wave.setGeometry(
           core_x + core_size + 30,
           core_y + core_size//2 - 60,
           190,
           120
        )

    def closeEvent(self, event):
        try:
            self.audio_thread.stop()
            self.audio_thread.wait(1000)
        except Exception:
            pass

        try:
            self.speech_thread.stop()
            self.speech_thread.wait(1000)
        except Exception:
            pass

        event.accept()


# ===================== RUN =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JarvisUI()
    window.showMaximized()
    sys.exit(app.exec_())
