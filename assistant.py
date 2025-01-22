import sys
import os
import shutil
import codecs
import speech_recognition as sr
import pyttsx3
import subprocess
from datetime import datetime
import random
import requests
import asyncio
from typing import Optional
from fuzzywuzzy import fuzz
import pyautogui
import time
import win32clipboard
from win32con import CF_UNICODETEXT

class AIAssistant:
    def __init__(self, window):
        self.window = window
        self.api_key = "your_api_key"  # Replace with your Hugging Face API key
        self.weather_api_key = "your_weather_api_key"  # Replace with your OpenWeather API key

        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[2].id)  # Adjust voice as needed
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)

        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.scrcpy_process = None
        self.is_phone_displayed = False
        
        
        self.current_notepad = None
        self.is_dictating = False
        self.max_save_attempts = 3
        pyautogui.PAUSE = 0.1  # Make PyAutoGUI faster

    def speak(self, text):
        """Convert text to speech"""
        self.window.set_assistant_state("speaking", text)
        print(f"Assistant: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
        self.window.set_assistant_state("normal", "Ready")

    async def listen_command(self):
        """Listen for voice commands"""
        with sr.Microphone() as source:
            self.window.set_assistant_state("listening", "Listening...")
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
            
            try:
                self.window.set_assistant_state("thinking", "Processing...")
                command = self.recognizer.recognize_google(audio)
                print(f"Command recognized: {command}")
                return command.lower()
            except sr.UnknownValueError:
                print("Could not understand audio")
                self.speak("Sorry, I didn't catch that")
                return None
            except Exception as e:
                print(f"Error: {e}")
                return None
    async def write_to_notepad(self, text):
        """Write the dictated text to Notepad using the clipboard for speed."""
        try:
            # Set up the clipboard with the text
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()

            # Paste the text (much faster than typing)
            pyautogui.hotkey('ctrl', 'v')

            self.speak("Text written. Continue or say 'save file'.")
        except Exception as e:
            print(f"Error writing to Notepad: {e}")
            self.speak("Sorry, I couldn't write the text.")      

    async def execute_command_async(self, command):
        """Execute voice commands"""
        if not command:
            return

        print(f"Executing: {command}")
        self.window.set_assistant_state("thinking", "Processing...")

        try:
            if 'open notepad' in command:
                await self.start_notepad_dictation()

            elif self.is_dictating and any(word in command for word in ['save', 'save file', 'save it']):
                await self.save_notepad_file()

            elif self.is_dictating:
                await asyncio.sleep(0.2)  # Ensure Notepad is ready
                if 'space' in command:
                    await self.write_to_notepad(' ')
                elif 'comma' in command:
                    await self.write_to_notepad(', ')
                elif 'point' in command or 'period' in command:
                    await self.write_to_notepad('.')
                elif 'new line' in command:
                    await self.write_to_notepad('\n')
                elif 'go back' in command:
                    pyautogui.hotkey('ctrl', 'z')
                elif 'go next' in command:
                    pyautogui.hotkey('ctrl', 'y')
                elif 'clear this line' in command:
                    # Move to the beginning of the line, select to the end, and delete
                    pyautogui.hotkey('home')  # Move to the beginning of the line
                    pyautogui.hotkey('shift', 'end')  # Highlight the entire line
                    pyautogui.press('backspace')  # Delete the selected text
                elif 'clear all' in command:
                    pyautogui.hotkey('ctrl', 'a')  # Select all
                    pyautogui.press('backspace')  # Delete all
                else:
                    await self.write_to_notepad(command)
            
                
            elif "search for" in command:
                search_query = command.replace("search for", "").strip()
                if search_query:
                    print(f"Searching for: {search_query}")
                    self.speak(f"Searching for {search_query}.")
                    # Open the default browser and perform the search
                    subprocess.run(["start", f"https://www.google.com/search?q={search_query}"], shell=True)
                else:
                    self.speak("Please specify what you'd like me to search for.")

            # Handle basic commands
            elif 'what time is it' in command:
                current_time = datetime.now().strftime("%H:%M")
                self.speak(f"It's {current_time}")

            elif 'what is the date' in command:
                current_date = datetime.now().strftime("%B %d, %Y")
                self.speak(f"Today is {current_date}")

            elif 'tell me a joke' in command:
                self.tell_joke()

            elif 'what\'s the weather' in command:
                await self.get_weather_async()

            # Handle AI queries
            elif any(keyword in command for keyword in ['explain', 'what is', 'who is', 'tell me about']):
                await self.process_ai_query(command)

            # Handle phone display commands
            elif 'display my phone' in command:
                await self.display_phone()

            elif 'stop display' in command:
                self.stop_display()

            else:
                self.speak("Sorry, I don't understand that command")

        except Exception as e:
            print(f"Command execution error: {e}")
            self.speak("Sorry, there was an error executing that command")
    
    
    async def start_notepad_dictation(self):
        """Start notepad and prepare for dictation"""
        try:
            self.current_notepad = subprocess.Popen(['notepad.exe'])
            time.sleep(1)  # Wait for Notepad to open
            self.is_dictating = True
            self.speak("Notepad is open. What would you like me to write?")
        except Exception as e:
            print(f"Error opening Notepad: {e}")
            self.speak("Sorry, I couldn't open Notepad")

    

    async def save_notepad_file(self):
        """Save the notepad file with retry logic"""
        attempts = 0
        while attempts < self.max_save_attempts:
            try:
                self.speak("Please say the filename you want to use")
                filename = await self.listen_command()
                
                if not filename:
                    attempts += 1
                    if attempts < self.max_save_attempts:
                        self.speak("I didn't catch that. Please try again.")
                        continue
                    else:
                        self.speak("I'm having trouble understanding the filename. Let's use a default name.")
                        filename = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Clean the filename of any invalid characters
                filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_'))
                
                # Press Ctrl+S to open save dialog
                pyautogui.hotkey('ctrl', 's')
                time.sleep(1)
                
                # Type the filename
                pyautogui.write(f"{filename}.txt")
                time.sleep(1)
                
                # Press Enter to save
                pyautogui.press('enter')
                time.sleep(1)
                
                self.is_dictating = False
                self.current_notepad = None
                self.speak(f"File saved as {filename}.txt")
                return
                
            except Exception as e:
                print(f"Error saving file (attempt {attempts + 1}): {e}")
                attempts += 1
                if attempts < self.max_save_attempts:
                    self.speak("Sorry, there was an error saving. Let's try again.")
                else:
                    self.speak("I'm having trouble saving the file. Please try manually saving it.")

    async def open_application(self, app_name):
        """Open an application by name"""
        print(f"Requested to open: {app_name}")

        # Common aliases
        aliases = {
            'code blocks': 'codeblocks',
            'postman': 'postman.exe',
        }
        app_name = aliases.get(app_name, app_name)

        # Check if app exists in system PATH
        if shutil.which(app_name):
            print(f"Found {app_name} in system PATH. Launching...")
            subprocess.Popen([app_name])
            self.speak(f"Opening {app_name}.")
            return

        # Search in common directories with fuzzy matching
        common_dirs = [
            r"C:\\Program Files",
            r"C:\\Program Files (x86)",
            r"C:\\Users\\%USERNAME%\\AppData\\Local\\Programs",
        ]
        best_match = None
        highest_score = 0

        for directory in common_dirs:
            for root, _, files in os.walk(os.path.expandvars(directory)):
                for file in files:
                    if file.endswith('.exe'):
                        score = fuzz.ratio(app_name, file.lower())
                        if app_name in file.lower():  # Prioritize substring matches
                            score += 20
                        if score > highest_score:
                            best_match = os.path.join(root, file)
                            highest_score = score

        if best_match and highest_score > 75:
            print(f"Launching best match: {best_match}")
            subprocess.Popen(best_match)
            self.speak(f"Opening {os.path.basename(best_match)}.")
        else:
            self.speak(f"Sorry, I couldn't find an application named {app_name}.")

    async def get_weather_async(self):
        """Get current weather information"""
        try:
            # Default coordinates for demo (replace with actual coordinates)
            lat, lon = "30.239660", "-9.526830"
            url = f'http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.weather_api_key}'

            response = await asyncio.to_thread(requests.get, url)
            data = response.json()

            if response.status_code == 200:
                temp = data['main']['temp'] - 273.15  # Convert Kelvin to Celsius
                weather = data['weather'][0]['description']
                self.speak(f"Current temperature is {temp:.1f}°C with {weather}")
            else:
                self.speak("Sorry, I couldn't fetch the weather information")

        except Exception as e:
            print(f"Weather error: {e}")
            self.speak("Sorry, there was an error getting the weather")

    async def process_ai_query(self, query):
        """Process AI queries using Hugging Face API"""
        try:
            formatted_query = f"Q: {query}\nA: Give a brief, factual answer in one sentence:"

            api_url = "https://api-inference.huggingface.co/models/google/flan-t5-base"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "inputs": formatted_query,
                "parameters": {"max_length": 50, "temperature": 0.7}
            }

            response = await asyncio.to_thread(
                requests.post, api_url, headers=headers, json=payload
            )

            if response.status_code == 200:
                answer = response.json()[0]["generated_text"].strip()
                self.speak(answer)
            else:
                self.speak("Sorry, I couldn't process your request")

        except Exception as e:
            print(f"AI query error: {e}")
            self.speak("Sorry, an error occurred")

    def tell_joke(self):
        """Tell a random joke"""
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the math book look sad? Because it had too many problems!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why don't skeletons fight each other? They don't have the guts!",
            "What did the grape say when it got stepped on? Nothing, it just let out a little wine!"
        ]
        joke = random.choice(jokes)
        self.speak(joke)

    async def display_phone(self):
        """Start displaying the phone screen using scrcpy"""
        if self.is_phone_displayed:
            self.speak("Your phone screen is already being displayed.")
            return

        try:
            print("Starting phone display using scrcpy...")
            # Use shell=True for Windows and store the process
            self.scrcpy_process = subprocess.Popen(
                r"C:\Users\dell\Desktop\Assitant\Display_Phone\scrcpy.exe",
                shell=True)
            self.speak("Displaying your phone screen.")
            self.is_phone_displayed = True
        except Exception as e:
            print(f"Error starting scrcpy: {e}")
            self.speak("Failed to display your phone screen.")

    def stop_display(self):
        """Stop displaying the phone screen"""
        try:
            if self.is_phone_displayed and self.scrcpy_process:
                # On Windows, we need to use taskkill to forcefully terminate scrcpy
                subprocess.run(['taskkill', '/F', '/IM', 'scrcpy.exe'], 
                             shell=True, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
                self.scrcpy_process = None
                self.is_phone_displayed = False
                self.speak("Stopped displaying phone screen.")
            else:
                self.speak("Phone screen is not being displayed.")
        except Exception as e:
            print(f"Error stopping display: {e}")
            self.speak("Error occurred while trying to stop the display.")

if __name__ == "__main__":
    # This section would be handled by your GUI framework
    class DummyWindow:
        def set_assistant_state(self, state, message):
            print(f"State: {state}, Message: {message}")

    assistant = AIAssistant(DummyWindow())

    async def main():
        while True:
            command = await assistant.listen_command()
            if command:
                await assistant.execute_command_async(command)

    asyncio.run(main())
    