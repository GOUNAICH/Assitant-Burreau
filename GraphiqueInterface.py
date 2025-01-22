import sys
import os
import speech_recognition as sr
import pyttsx3
import subprocess
from datetime import datetime
import random
import requests
import asyncio
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
import qasync
from typing import Optional


class EyeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.eye_state = "normal"
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink)
        self.blink_timer.start(4000)
        self.is_blinking = False
        self.blink_counter = 0
        self.pupil_offset_x = 0
        self.pupil_offset_y = 0
        self.mouth_state = "normal"  # New variable for mouth expression

    def blink(self):
        self.is_blinking = True
        self.blink_counter = 0
        self.update()
        QTimer.singleShot(150, self.unblink)
        
    def unblink(self):
        self.is_blinking = False
        self.update()
    
    def set_state(self, state: str, mouth_state: Optional[str] = None):
        self.eye_state = state
        if mouth_state:
            self.mouth_state = mouth_state  # Update mouth state
        self.update()
    
    def move_pupils(self, x: int, y: int):
        self.pupil_offset_x = x
        self.pupil_offset_y = y
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        eye_color = QColor("#00CED1")  # Eye color
        pupil_color = QColor("#000000")  # Pupil color
        mouth_color = QColor("#000000")  # Mouth color

        width = self.width()
        height = self.height()
        eye_width = 80
        eye_height = 10 if self.is_blinking else 50
        gap = 40
        
        left_eye_x = (width - (2 * eye_width + gap)) // 2
        left_eye_y = height // 2 - eye_height // 2
        right_eye_x = left_eye_x + eye_width + gap
        right_eye_y = left_eye_y

        # Draw Eyes
        painter.setBrush(QBrush(eye_color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawEllipse(left_eye_x, left_eye_y, eye_width, eye_height)
        painter.drawEllipse(right_eye_x, right_eye_y, eye_width, eye_height)

        if not self.is_blinking:
            painter.setBrush(QBrush(pupil_color))
            pupil_size = 20
            
            if self.eye_state == "thinking":
                pupil_offset_y = -10
                pupil_offset_x = self.pupil_offset_x
            elif self.eye_state == "listening":
                pupil_offset_y = 0
                pupil_offset_x = self.pupil_offset_x * 2
            elif self.eye_state == "speaking":
                pupil_offset_y = 5
                pupil_offset_x = self.pupil_offset_x
            else:  # normal
                pupil_offset_y = self.pupil_offset_y
                pupil_offset_x = self.pupil_offset_x
            
            left_pupil_x = left_eye_x + (eye_width - pupil_size) // 2 + pupil_offset_x
            left_pupil_y = left_eye_y + (eye_height - pupil_size) // 2 + pupil_offset_y
            painter.drawEllipse(left_pupil_x, left_pupil_y, pupil_size, pupil_size)
            
            right_pupil_x = right_eye_x + (eye_width - pupil_size) // 2 + pupil_offset_x
            right_pupil_y = right_eye_y + (eye_height - pupil_size) // 2 + pupil_offset_y
            painter.drawEllipse(right_pupil_x, right_pupil_y, pupil_size, pupil_size)

        # Draw Mouth (based on state)
        mouth_width = 60
        mouth_height = 10
        mouth_x = (width - mouth_width) // 2
        mouth_y = height // 2 + 50

        if self.mouth_state == "happy":
            painter.setBrush(QBrush(mouth_color))
            painter.drawArc(mouth_x, mouth_y, mouth_width, mouth_height, 0, 180 * 16)
        elif self.mouth_state == "sad":
            painter.setBrush(QBrush(mouth_color))
            painter.drawArc(mouth_x, mouth_y, mouth_width, mouth_height, 180 * 16, -180 * 16)
        else:  # neutral
            painter.setBrush(QBrush(mouth_color))
            painter.drawRect(mouth_x, mouth_y, mouth_width, mouth_height)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Assistant - Abdo")
        self.setMinimumSize(600, 400)

        # Dark theme settings
        self.setStyleSheet("background-color: #121212; color: white;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.eye_widget = EyeWidget()
        layout.addWidget(self.eye_widget)
        
        self.status_label = QLabel("AI Assistant Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.random_eye_movement)
        self.animation_timer.start(2000)

        self.move_timer = QTimer(self)  # Timer for moving the assistant
        self.move_timer.timeout.connect(self.move_assistant)
        self.move_timer.start(2000)
        
    def random_eye_movement(self):
        from random import randint
        x_offset = randint(-10, 10)
        y_offset = randint(-5, 5)
        self.eye_widget.move_pupils(x_offset, y_offset)
    
    def move_assistant(self):
        if self.eye_widget.eye_state != "listening":  # Move when not listening
            x = random.randint(0, self.width() - self.eye_widget.width())
            y = random.randint(0, self.height() - self.eye_widget.height())
            self.eye_widget.move(x, y)
    
    def set_assistant_state(self, state: str, mouth_state: Optional[str] = None, message: Optional[str] = None):
        self.eye_widget.set_state(state, mouth_state)
        if message:
            self.status_label.setText(message)