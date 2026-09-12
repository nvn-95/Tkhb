import json
import os
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QEasingCurve, QObject, Property, QPropertyAnimation, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "SCREAM VOLUME™"
TAGLINE = "Why use a slider when you have vocal cords?"
SAMPLE_RATE = 44100
RECORD_DURATION_SECONDS = 2.5
WAVEFORM_SAMPLES = 96


@dataclass
class AppSettings:
    selected_microphone: Optional[int] = None
    sensitivity: float = 1.0
    min_output: int = 0
    max_output: int = 100
    calibration_reference: Optional[float] = None


@dataclass
class AudioMeasurement:
    rms: float
    peak: float
    loudness: float
    normalized: float
    raw_percent: int
    output_percent: int


class WaveformWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(150)
        self._values = np.zeros(WAVEFORM_SAMPLES, dtype=float)
        self._phase = 0.0

    def set_level_data(self, level: float, waveform: np.ndarray) -> None:
        waveform = np.asarray(waveform, dtype=float).flatten()
        if waveform.size == 0:
            return
        samples = np.abs(waveform)
        if samples.size < WAVEFORM_SAMPLES:
            pad = np.zeros(WAVEFORM_SAMPLES - samples.size, dtype=float)
            samples = np.concatenate([samples, pad])
        self._values = np.clip(samples[:WAVEFORM_SAMPLES], 0.0, 1.0)
        self._phase = (self._phase + max(0.02, level * 0.08)) % 1.0
        self.update()

    def clear(self) -> None:
        self._values[:] = 0.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#111827"))
        painter.drawRoundedRect(rect, 16, 16)

        bar_count = len(self._values)
        if bar_count == 0:
            return

        bar_width = max(2.0, rect.width() / (bar_count * 1.6))
        spacing = bar_width * 0.6
        x = rect.left() + (rect.width() - (bar_count * bar_width + (bar_count - 1) * spacing)) / 2
        mid_y = rect.center().y()

        for i, value in enumerate(self._values):
            glow = 0.25 + 0.75 * np.sin((i / max(1, bar_count - 1) + self._phase) * np.pi)
            height = max(6.0, value * rect.height() * 0.9)
            top = mid_y - height / 2

            gradient = QLinearGradient(x, top, x, top + height)
            gradient.setColorAt(0.0, QColor(115, 255, 214, int(255 * glow)))
            gradient.setColorAt(1.0, QColor(74, 110, 255, int(220 * glow)))

            painter.setBrush(gradient)
            painter.drawRoundedRect(x, top, bar_width, height, bar_width / 2, bar_width / 2)
            x += bar_width + spacing


class RecorderWorker(QObject):
    level_updated = Signal(float, object)
    progress_updated = Signal(float)
    finished = Signal(object, str)

    def __init__(
        self,
        duration_seconds: float,
        sample_rate: int,
        device_index: Optional[int],
        settings: AppSettings,
    ) -> None:
        super().__init__()
        self.duration_seconds = duration_seconds
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.settings = settings
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        sd = _sounddevice()
        chunks: list[np.ndarray] = []
        start_time = time.monotonic()

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001,ARG001
            if status:
                pass
            data = np.squeeze(np.array(indata, dtype=np.float32))
            if data.size == 0:
                return
            chunks.append(data.copy())
            peak = float(np.max(np.abs(data)))

            if data.size >= WAVEFORM_SAMPLES:
                indices = np.linspace(0, data.size - 1, WAVEFORM_SAMPLES).astype(int)
                waveform = data[indices]
            else:
                waveform = np.pad(data, (0, WAVEFORM_SAMPLES - data.size))

            self.level_updated.emit(peak, waveform)
            elapsed = time.monotonic() - start_time
            progress = min(1.0, elapsed / self.duration_seconds)
            self.progress_updated.emit(progress)
            if elapsed >= self.duration_seconds or self._stop_event.is_set():
                raise sd.CallbackStop()

        try:
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=callback,
                device=self.device_index,
            )
            with stream:
                while stream.active and not self._stop_event.is_set():
                    time.sleep(0.02)

            if not chunks:
                raise RuntimeError("No audio data captured.")

            samples = np.concatenate(chunks)
            measurement = analyze_audio(samples, self.settings)
            self.finished.emit(measurement, "")
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(None, str(exc))


def _settings_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home()
    return base / "scream_volume" / "settings.json"


def load_settings() -> AppSettings:
    path = _settings_path()
    if not path.exists():
        return AppSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return AppSettings()

    settings = AppSettings()
    settings.selected_microphone = data.get("selected_microphone")
    settings.sensitivity = float(data.get("sensitivity", settings.sensitivity))
    settings.min_output = int(data.get("min_output", settings.min_output))
    settings.max_output = int(data.get("max_output", settings.max_output))
    calibration = data.get("calibration_reference")
    settings.calibration_reference = float(calibration) if calibration else None
    return validate_settings(settings)


def validate_settings(settings: AppSettings) -> AppSettings:
    settings.sensitivity = float(np.clip(settings.sensitivity, 0.5, 2.0))
    settings.min_output = int(np.clip(settings.min_output, 0, 100))
    settings.max_output = int(np.clip(settings.max_output, 0, 100))
    if settings.min_output > settings.max_output:
        settings.min_output, settings.max_output = settings.max_output, settings.min_output
    if settings.calibration_reference is not None and settings.calibration_reference <= 0:
        settings.calibration_reference = None
    return settings


def save_settings(settings: AppSettings) -> None:
    settings = validate_settings(settings)
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def _sounddevice():
    try:
        import sounddevice as sd  # noqa: PLC0415
    except OSError as exc:
        raise RuntimeError(
            "Audio backend unavailable. Install PortAudio/sound drivers and try again."
        ) from exc
    return sd


def list_input_devices() -> list[tuple[int, str]]:
    sd = _sounddevice()
    devices = sd.query_devices()
    result: list[tuple[int, str]] = []
    for index, device in enumerate(devices):
        if device.get("max_input_channels", 0) > 0:
            result.append((index, str(device.get("name", f"Microphone {index}"))))
    return result


def get_input_device_info(device_index: Optional[int]) -> dict:
    sd = _sounddevice()
    if device_index is None:
        default_input_index = sd.default.device[0]
        if default_input_index is None or default_input_index < 0:
            raise RuntimeError("No default input device configured.")
        return sd.query_devices(default_input_index, "input")
    return sd.query_devices(device_index, "input")


def analyze_audio(samples: np.ndarray, settings: AppSettings) -> AudioMeasurement:
    samples = np.asarray(samples, dtype=np.float32).flatten()
    if samples.size == 0:
        raise RuntimeError("No audio data captured.")

    rms = float(np.sqrt(np.mean(np.square(samples))))
    peak = float(np.max(np.abs(samples)))

    loudness = max(peak, min(1.0, rms * 1.8))
    reference = settings.calibration_reference if settings.calibration_reference else 1.0
    normalized = (loudness / max(reference, 1e-6)) * settings.sensitivity
    normalized = float(np.clip(normalized, 0.0, 1.0))

    raw_percent = int(round(normalized * 100))
    volume_range = settings.max_output - settings.min_output
    output_percent = settings.min_output + int(round((raw_percent / 100.0) * volume_range))
    output_percent = int(np.clip(output_percent, settings.min_output, settings.max_output))

    return AudioMeasurement(
        rms=rms,
        peak=peak,
        loudness=loudness,
        normalized=normalized,
        raw_percent=raw_percent,
        output_percent=output_percent,
    )


def _get_windows_endpoint_volume():
    if not sys.platform.startswith("win"):
        raise RuntimeError("Windows volume access is only supported on Windows.")

    from pycaw.pycaw import AudioUtilities

    device = AudioUtilities.GetSpeakers()
    endpoint = getattr(device, "EndpointVolume", None)
    if endpoint is not None:
        return endpoint

    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume

    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def get_windows_master_volume() -> int:
    endpoint = _get_windows_endpoint_volume()
    scalar = endpoint.GetMasterVolumeLevelScalar()
    return int(round(float(np.clip(scalar, 0.0, 1.0)) * 100))


def set_windows_master_volume(percent: int) -> None:
    if not (0 <= percent <= 100):
        raise ValueError("Volume percent must be in range 0-100.")

    if not sys.platform.startswith("win"):
        raise RuntimeError("Windows volume control is only supported on Windows.")

    endpoint = _get_windows_endpoint_volume()
    endpoint.SetMasterVolumeLevelScalar(percent / 100.0, None)


def try_get_windows_master_volume() -> Optional[int]:
    try:
        return get_windows_master_volume()
    except Exception:  # noqa: BLE001
        return None


def loudness_feedback(percent: int) -> str:
    if percent < 15:
        return "Was that a whisper or a philosophical thought?"
    if percent < 35:
        return "Respectable effort. Your neighbors are still calm."
    if percent < 60:
        return "Strong lungs detected. The walls are listening."
    if percent < 85:
        return "Excellent scream. Local birds have filed complaints."
    return "Legendary roar. Windows itself is intimidated."


class FadeStackedWidget(QStackedWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._animation: Optional[QPropertyAnimation] = None

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        super().setCurrentIndex(index)
        widget = self.currentWidget()
        if widget is None:
            return
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        self._animation = QPropertyAnimation(effect, b"opacity", self)
        self._animation.setDuration(240)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._animation.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._animation.start()


class GlowButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._glow = 0.0
        self._anim = QPropertyAnimation(self, b"glow", self)
        self._anim.setDuration(900)
        self._anim.setLoopCount(-1)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._glow = 0.0
        self._refresh_style()
        super().leaveEvent(event)

    def get_glow(self) -> float:
        return self._glow

    def set_glow(self, value: float) -> None:
        self._glow = float(value)
        self._refresh_style()

    glow = Property(float, get_glow, set_glow)

    def _refresh_style(self) -> None:
        border_alpha = int(180 + self._glow * 60)
        hover_alpha = int(210 + self._glow * 45)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #3A4FF4;
                color: white;
                border: 1px solid rgba(140,180,255,{border_alpha});
                border-radius: 18px;
                font-size: 20px;
                font-weight: 700;
                padding: 16px 28px;
            }}
            QPushButton:hover {{
                background-color: #4B5CFF;
                border-color: rgba(160,220,255,{hover_alpha});
            }}
            QPushButton:disabled {{
                background-color: #2A3550;
                color: #8892A8;
                border-color: #2F3A50;
            }}
            """
        )


class ScreamVolumeWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(980, 700)
        self.settings_data = load_settings()
        self.last_measurement: Optional[AudioMeasurement] = None
        self.pre_scream_system_volume: Optional[int] = None
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[RecorderWorker] = None
        self.mode = "idle"

        self._build_ui()
        self.apply_theme()
        self.populate_microphones()
        self.refresh_home()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(16)

        self.stack = FadeStackedWidget(self)
        root_layout.addWidget(self.stack)

        self.home_page = self._create_home_page()
        self.screaming_page = self._create_screaming_page()
        self.result_page = self._create_result_page()
        self.calibration_page = self._create_calibration_page()
        self.settings_page = self._create_settings_page()

        for page in [
            self.home_page,
            self.screaming_page,
            self.result_page,
            self.calibration_page,
            self.settings_page,
        ]:
            self.stack.addWidget(page)

    def apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #090B12;
                color: #E9EEFF;
            }
            QLabel#titleLabel {
                font-size: 42px;
                font-weight: 800;
                color: #F7FBFF;
            }
            QLabel#taglineLabel {
                font-size: 16px;
                color: #A3B2D7;
            }
            QLabel#screenTitle {
                font-size: 30px;
                font-weight: 700;
                color: #F4F8FF;
            }
            QLabel#screenSubtitle {
                font-size: 16px;
                color: #9AA8C7;
            }
            QFrame#card {
                background: #111522;
                border: 1px solid #1F2A44;
                border-radius: 18px;
            }
            QPushButton {
                background: #1A2238;
                border: 1px solid #2D3A59;
                border-radius: 14px;
                color: #E7EEFF;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background: #223052;
                border-color: #3A4D76;
            }
            QComboBox, QSpinBox {
                background: #0D1220;
                border: 1px solid #2A3653;
                border-radius: 10px;
                color: #EAF0FF;
                padding: 8px;
                min-height: 24px;
            }
            QSlider::groove:horizontal {
                background: #25314E;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #70FFD7;
                border: none;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QProgressBar {
                border-radius: 9px;
                background: #18233C;
                border: 1px solid #2B3A59;
                text-align: center;
                color: #D8E3FF;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #52F7CB, stop:1 #517BFF);
                border-radius: 8px;
            }
            """
        )

    def _create_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("card")
        return card

    def _create_home_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        subtitle = QLabel(TAGLINE)
        subtitle.setObjectName("taglineLabel")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        status_card = self._create_card()
        status_layout = QGridLayout(status_card)

        self.system_volume_label = QLabel("SYSTEM VOLUME: --%")
        self.system_volume_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #DEEAFF;")
        self.calibration_status_label = QLabel("CALIBRATION: Not calibrated")
        self.calibration_status_label.setStyleSheet("font-size: 15px; color: #93A8D0;")
        self.home_microphone_label = QLabel("MICROPHONE: --")
        self.home_microphone_label.setStyleSheet("font-size: 14px; color: #8D9FBE;")

        status_layout.addWidget(self.system_volume_label, 0, 0)
        status_layout.addWidget(self.calibration_status_label, 1, 0)
        status_layout.addWidget(self.home_microphone_label, 2, 0)

        layout.addWidget(status_card)

        self.set_volume_button = GlowButton("SET VOLUME")
        self.set_volume_button.clicked.connect(self.start_scream_session)
        self.set_volume_button._refresh_style()

        actions = QHBoxLayout()
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.calibration_button = QPushButton("Calibration")
        self.calibration_button.clicked.connect(self.open_calibration)

        actions.addWidget(self.settings_button)
        actions.addWidget(self.calibration_button)
        actions.addStretch(1)

        layout.addWidget(self.set_volume_button)
        layout.addLayout(actions)
        layout.addStretch(1)
        return page

    def _create_screaming_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        icon = QLabel("🎤")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 84px;")

        title = QLabel("SCREAM NOW")
        title.setObjectName("screenTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Give it everything you've got.")
        subtitle.setObjectName("screenSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        self.scream_waveform = WaveformWidget(self)
        self.scream_progress = QProgressBar(self)
        self.scream_progress.setRange(0, 100)
        self.scream_countdown = QLabel("Recording: 2.5s")
        self.scream_countdown.setAlignment(Qt.AlignCenter)
        self.scream_countdown.setStyleSheet("font-size: 14px; color: #9AB2DD;")

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.cancel_recording)

        layout.addStretch(1)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.scream_waveform)
        layout.addWidget(self.scream_progress)
        layout.addWidget(self.scream_countdown)
        layout.addWidget(cancel, alignment=Qt.AlignCenter)
        layout.addStretch(1)
        return page

    def _create_result_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        title = QLabel("VOLUME SET")
        title.setObjectName("screenTitle")
        title.setAlignment(Qt.AlignCenter)

        self.result_percent = QLabel("--%")
        self.result_percent.setAlignment(Qt.AlignCenter)
        self.result_percent.setStyleSheet("font-size: 96px; font-weight: 800; color: #78FFD8;")

        self.result_scream_label = QLabel("YOUR SCREAM: --%")
        self.result_scream_label.setAlignment(Qt.AlignCenter)
        self.result_scream_label.setStyleSheet("font-size: 20px; color: #D3E2FF;")

        self.result_system_label = QLabel("SYSTEM VOLUME: --%")
        self.result_system_label.setAlignment(Qt.AlignCenter)
        self.result_system_label.setStyleSheet("font-size: 18px; color: #AAC0E5;")

        self.feedback_label = QLabel("Ready for glory.")
        self.feedback_label.setAlignment(Qt.AlignCenter)
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setStyleSheet("font-size: 16px; color: #9FB3D9;")

        again = GlowButton("SCREAM AGAIN")
        again.clicked.connect(self.start_scream_session)
        again._refresh_style()

        home = QPushButton("Back to Home")
        home.clicked.connect(self.show_home)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(self.result_percent)
        layout.addWidget(self.result_scream_label)
        layout.addWidget(self.result_system_label)
        layout.addWidget(self.feedback_label)
        layout.addWidget(again)
        layout.addWidget(home, alignment=Qt.AlignCenter)
        layout.addStretch(1)
        return page

    def _create_calibration_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        title = QLabel("CALIBRATION")
        title.setObjectName("screenTitle")

        explanation = QLabel(
            "Your loudest comfortable scream becomes your 100% reference.\n"
            "Future screams are measured against this profile."
        )
        explanation.setObjectName("screenSubtitle")
        explanation.setWordWrap(True)

        self.calibration_waveform = WaveformWidget(self)
        self.calibration_progress = QProgressBar(self)
        self.calibration_progress.setRange(0, 100)
        self.calibration_status = QLabel("Calibration not started.")
        self.calibration_status.setStyleSheet("font-size: 14px; color: #9DB1D7;")

        button_row = QHBoxLayout()
        self.calibration_start_button = GlowButton("CALIBRATE NOW")
        self.calibration_start_button.clicked.connect(self.start_calibration_session)
        self.calibration_start_button._refresh_style()
        back = QPushButton("Back")
        back.clicked.connect(self.show_home)

        button_row.addWidget(self.calibration_start_button)
        button_row.addWidget(back)

        layout.addWidget(title)
        layout.addWidget(explanation)
        layout.addWidget(self.calibration_waveform)
        layout.addWidget(self.calibration_progress)
        layout.addWidget(self.calibration_status)
        layout.addLayout(button_row)
        layout.addStretch(1)
        return page

    def _create_settings_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("SETTINGS")
        title.setObjectName("screenTitle")

        card = self._create_card()
        card_layout = QGridLayout(card)
        card_layout.setHorizontalSpacing(16)
        card_layout.setVerticalSpacing(12)

        mic_label = QLabel("Microphone")
        self.microphone_combo = QComboBox(self)

        sensitivity_label = QLabel("Sensitivity")
        self.sensitivity_slider = QSlider(Qt.Horizontal, self)
        self.sensitivity_slider.setRange(50, 200)
        self.sensitivity_value = QLabel("1.00x")
        self.sensitivity_slider.valueChanged.connect(self._on_sensitivity_changed)

        min_label = QLabel("Minimum output volume")
        self.min_spin = QSpinBox(self)
        self.min_spin.setRange(0, 100)

        max_label = QLabel("Maximum output volume")
        self.max_spin = QSpinBox(self)
        self.max_spin.setRange(0, 100)

        card_layout.addWidget(mic_label, 0, 0)
        card_layout.addWidget(self.microphone_combo, 0, 1, 1, 2)
        card_layout.addWidget(sensitivity_label, 1, 0)
        card_layout.addWidget(self.sensitivity_slider, 1, 1)
        card_layout.addWidget(self.sensitivity_value, 1, 2)
        card_layout.addWidget(min_label, 2, 0)
        card_layout.addWidget(self.min_spin, 2, 1, 1, 2)
        card_layout.addWidget(max_label, 3, 0)
        card_layout.addWidget(self.max_spin, 3, 1, 1, 2)

        actions = QHBoxLayout()
        save = QPushButton("Save Settings")
        save.clicked.connect(self.save_settings_from_ui)
        reset = QPushButton("Reset Settings")
        reset.clicked.connect(self.reset_settings)
        recalibrate = QPushButton("Recalibrate")
        recalibrate.clicked.connect(self.open_calibration)
        back = QPushButton("Back")
        back.clicked.connect(self.show_home)

        actions.addWidget(save)
        actions.addWidget(reset)
        actions.addWidget(recalibrate)
        actions.addWidget(back)

        self.settings_status = QLabel("")
        self.settings_status.setStyleSheet("font-size: 14px; color: #8CA4D1;")

        layout.addWidget(title)
        layout.addWidget(card)
        layout.addLayout(actions)
        layout.addWidget(self.settings_status)
        layout.addStretch(1)
        return page

    def _on_sensitivity_changed(self, value: int) -> None:
        self.sensitivity_value.setText(f"{value/100:.2f}x")

    def populate_microphones(self) -> None:
        self.microphone_combo.clear()
        self.microphone_combo.addItem("Default system microphone", None)
        try:
            for index, name in list_input_devices():
                self.microphone_combo.addItem(name, index)
        except Exception:  # noqa: BLE001
            self.settings_status.setText("Microphone list unavailable.")

        target = self.settings_data.selected_microphone
        for i in range(self.microphone_combo.count()):
            if self.microphone_combo.itemData(i) == target:
                self.microphone_combo.setCurrentIndex(i)
                break

        self.sensitivity_slider.setValue(int(round(self.settings_data.sensitivity * 100)))
        self.min_spin.setValue(self.settings_data.min_output)
        self.max_spin.setValue(self.settings_data.max_output)

    def refresh_home(self) -> None:
        try:
            device = get_input_device_info(self.settings_data.selected_microphone)
            self.home_microphone_label.setText(f"MICROPHONE: {device['name']}")
            self.set_volume_button.setEnabled(True)
        except Exception:  # noqa: BLE001
            self.home_microphone_label.setText("MICROPHONE ERROR: unavailable")
            self.set_volume_button.setEnabled(False)

        if self.settings_data.calibration_reference:
            self.calibration_status_label.setText("CALIBRATION: Ready")
        else:
            self.calibration_status_label.setText("CALIBRATION: Not calibrated")

        current_volume = try_get_windows_master_volume()
        if current_volume is None:
            self.system_volume_label.setText("SYSTEM VOLUME: unavailable")
        else:
            self.system_volume_label.setText(f"SYSTEM VOLUME: {current_volume}%")

    def save_settings_from_ui(self) -> None:
        self.settings_data.selected_microphone = self.microphone_combo.currentData()
        self.settings_data.sensitivity = self.sensitivity_slider.value() / 100.0
        self.settings_data.min_output = self.min_spin.value()
        self.settings_data.max_output = self.max_spin.value()
        validate_settings(self.settings_data)
        self.min_spin.setValue(self.settings_data.min_output)
        self.max_spin.setValue(self.settings_data.max_output)
        save_settings(self.settings_data)
        self.settings_status.setText("Settings saved locally.")
        self.refresh_home()

    def reset_settings(self) -> None:
        self.settings_data = AppSettings()
        save_settings(self.settings_data)
        self.populate_microphones()
        self.settings_status.setText("Settings reset.")
        self.refresh_home()

    def open_settings(self) -> None:
        self.populate_microphones()
        self.settings_status.setText("")
        self.stack.setCurrentWidget(self.settings_page)

    def open_calibration(self) -> None:
        self.calibration_progress.setValue(0)
        self.calibration_status.setText("Calibration not started.")
        self.calibration_waveform.clear()
        self.stack.setCurrentWidget(self.calibration_page)

    def show_home(self) -> None:
        self.refresh_home()
        self.stack.setCurrentWidget(self.home_page)

    def cancel_recording(self) -> None:
        if self.worker:
            self.worker.stop()
        self.show_home()

    def _start_recording(self, mode: str) -> None:
        if self.worker_thread and self.worker_thread.isRunning():
            return

        validate_settings(self.settings_data)
        self.mode = mode
        if mode == "scream":
            self.pre_scream_system_volume = try_get_windows_master_volume()
            self.scream_waveform.clear()
            self.scream_progress.setValue(0)
            self.scream_countdown.setText(f"Recording: {RECORD_DURATION_SECONDS:.1f}s")
            self.stack.setCurrentWidget(self.screaming_page)
        else:
            self.calibration_waveform.clear()
            self.calibration_progress.setValue(0)
            self.calibration_status.setText("Recording calibration scream...")

        self.worker_thread = QThread(self)
        self.worker = RecorderWorker(
            duration_seconds=RECORD_DURATION_SECONDS,
            sample_rate=SAMPLE_RATE,
            device_index=self.settings_data.selected_microphone,
            settings=self.settings_data,
        )

        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.level_updated.connect(self._on_level_update)
        self.worker.progress_updated.connect(self._on_progress_update)
        self.worker.finished.connect(self._on_recording_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def start_scream_session(self) -> None:
        self._start_recording(mode="scream")

    def start_calibration_session(self) -> None:
        self._start_recording(mode="calibration")

    def _on_level_update(self, level: float, waveform: object) -> None:
        values = np.asarray(waveform, dtype=float)
        if self.mode == "scream":
            self.scream_waveform.set_level_data(level, values)
        elif self.mode == "calibration":
            self.calibration_waveform.set_level_data(level, values)

    def _on_progress_update(self, progress: float) -> None:
        value = int(round(progress * 100))
        remaining = max(0.0, RECORD_DURATION_SECONDS * (1.0 - progress))

        if self.mode == "scream":
            self.scream_progress.setValue(value)
            self.scream_countdown.setText(f"Recording: {remaining:.1f}s")
        elif self.mode == "calibration":
            self.calibration_progress.setValue(value)

    def _on_recording_finished(self, measurement: object, error: str) -> None:
        self.worker = None
        self.worker_thread = None

        if error:
            message = "Recording failed. Please try again."
            if self.mode == "calibration":
                self.calibration_status.setText(message)
                self.stack.setCurrentWidget(self.calibration_page)
            else:
                self.stack.setCurrentWidget(self.result_page)
                self.result_percent.setText("--")
                self.result_scream_label.setText("YOUR SCREAM: --")
                self.result_system_label.setText("SYSTEM VOLUME: unchanged")
                self.feedback_label.setText(message)
            return

        assert isinstance(measurement, AudioMeasurement)
        self.last_measurement = measurement

        if self.mode == "calibration":
            reference = max(measurement.loudness, 0.05)
            self.settings_data.calibration_reference = reference
            save_settings(self.settings_data)
            self.calibration_status.setText(
                f"Calibration saved. Reference scream = {int(round(reference * 100))}% baseline."
            )
            self.refresh_home()
            return

        volume_text = "SYSTEM VOLUME: unavailable"
        try:
            set_windows_master_volume(measurement.output_percent)
        except Exception:  # noqa: BLE001
            pass

        current_volume = try_get_windows_master_volume()
        if current_volume is not None:
            volume_text = f"SYSTEM VOLUME: {current_volume}%"

        self.result_percent.setText(f"{measurement.output_percent}%")
        self.result_scream_label.setText(f"YOUR SCREAM: {measurement.raw_percent}%")
        self.result_system_label.setText(volume_text)
        self.feedback_label.setText(loudness_feedback(measurement.raw_percent))
        self.stack.setCurrentWidget(self.result_page)
        self.refresh_home()


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = ScreamVolumeWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
