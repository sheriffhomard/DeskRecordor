from __future__ import annotations

from __future__ import annotations

import os
from typing import Any

from deskrecordor.config.settings import Settings
from deskrecordor.core.audio import AudioManager
from deskrecordor.core.capture import ScreenCapture
from deskrecordor.core.recorder import Recorder
from deskrecordor.core.state_manager import RecorderState
from deskrecordor.ui.components import TimerLabel, VUMeter

try:
    from gi.repository import Adw, GLib, Gtk
except ImportError:  # pragma: no cover - GTK may not be available in CI
    Adw = None
    GLib = None
    Gtk = None


class MainWindow:
    """GTK application window for DeskRecordor."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()
        self.recorder = Recorder(self.settings)
        self.vumeter = VUMeter()
        self.timer = TimerLabel()
        self.app: Any | None = None
        self.window: Any | None = None
        self.monitor_combo: Any | None = None
        self.microphone_combo: Any | None = None
        self.timer_label: Any | None = None
        self.vumeter_bar: Any | None = None
        self.status_label: Any | None = None
        self.start_button: Any | None = None
        self.pause_button: Any | None = None
        self.stop_button: Any | None = None
        self._timer_source_id: int | None = None
        self._recording_seconds = 0

    def _build_ui(self) -> None:
        if Gtk is None or Adw is None:
            return

        self.app = Adw.Application(application_id="org.deskrecordor.app")
        self.app.connect("activate", self._on_activate)

    def _on_activate(self, app: Any) -> None:
        if Gtk is None or Adw is None:
            return

        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("DeskRecordor — Enregistreur d'écran et de voix")
        self.window.set_default_size(420, 350)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=18, margin_bottom=18, margin_start=18, margin_end=18)

        title = Gtk.Label(label="DeskRecordor")
        title.get_style_context().add_class("title-1")
        content.append(title)

        monitor_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        monitor_label = Gtk.Label(label="Moniteur :")
        self.monitor_combo = Gtk.ComboBoxText()
        monitor_group.append(monitor_label)
        monitor_group.append(self.monitor_combo)
        content.append(monitor_group)

        mic_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mic_label = Gtk.Label(label="Microphone :")
        self.microphone_combo = Gtk.ComboBoxText()
        mic_group.append(mic_label)
        mic_group.append(self.microphone_combo)
        content.append(mic_group)

        self.vumeter_bar = Gtk.ProgressBar(show_text=True, text="Microphone")
        self.vumeter_bar.set_fraction(0.0)
        content.append(self.vumeter_bar)

        self.timer_label = Gtk.Label(label="00:00:00")
        self.status_label = Gtk.Label(label="Prêt")
        content.append(self.timer_label)
        content.append(self.status_label)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.CENTER)
        self.start_button = Gtk.Button(label="ENREGISTRER")
        self.pause_button = Gtk.Button(label="PAUSE")
        self.stop_button = Gtk.Button(label="ARRÊTER")
        self.pause_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        self.start_button.connect("clicked", self.on_start_clicked)
        self.pause_button.connect("clicked", self.on_pause_clicked)
        self.stop_button.connect("clicked", self.on_stop_clicked)
        controls.append(self.start_button)
        controls.append(self.pause_button)
        controls.append(self.stop_button)
        content.append(controls)

        self.window.set_content(content)
        self.populate_controls()
        self.window.present()

    def populate_controls(self) -> None:
        if self.monitor_combo is not None:
            self.monitor_combo.remove_all()
            for monitor in ScreenCapture.list_monitors():
                self.monitor_combo.append_text(f"{monitor.name} ({monitor.resolution})")
            self.monitor_combo.set_active(0)

        if self.microphone_combo is not None:
            self.microphone_combo.remove_all()
            for mic in AudioManager().list_microphones():
                self.microphone_combo.append_text(mic.label)
            self.microphone_combo.set_active(0)

    def on_start_clicked(self, _button: Any) -> None:
        try:
            self.recorder.prepare()
            if self.monitor_combo is not None and self.monitor_combo.get_active_text():
                self.settings.default_monitor = self.monitor_combo.get_active_text().split(" (", 1)[0]
            if self.microphone_combo is not None and self.microphone_combo.get_active_text():
                self.settings.default_microphone = self.microphone_combo.get_active_text().split(" (", 1)[0]
            self.recorder.audio_manager = AudioManager(self.settings.default_microphone)
            self.recorder.start_recording(self.settings.output_dir)
            self.status_label.set_text("Enregistrement en cours")
            self.pause_button.set_sensitive(True)
            self.stop_button.set_sensitive(True)
            self._recording_seconds = 0
            self._timer_source_id = GLib.timeout_add(1000, self._tick_timer)
        except Exception as exc:  # pragma: no cover - UI path may vary per desktop
            if self.status_label is not None:
                self.status_label.set_text(str(exc))

    def on_pause_clicked(self, _button: Any) -> None:
        if self.recorder.state == RecorderState.RECORDING:
            self.recorder.pause_recording()
            self.status_label.set_text("Enregistrement en pause")
            self.pause_button.set_label("REPRENDRE")
        elif self.recorder.state == RecorderState.PAUSED:
            self.recorder.resume_recording()
            self.status_label.set_text("Enregistrement en cours")
            self.pause_button.set_label("PAUSE")

    def on_stop_clicked(self, _button: Any) -> None:
        if self._timer_source_id is not None:
            GLib.source_remove(self._timer_source_id)
            self._timer_source_id = None
        if self.recorder.state in {RecorderState.RECORDING, RecorderState.PAUSED}:
            self.recorder.stop_recording()
        self.status_label.set_text("Finalisation…")
        self.pause_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)

    def _tick_timer(self) -> bool:
        self._recording_seconds += 1
        if self.timer_label is not None:
            hours, remainder = divmod(self._recording_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.set_text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return True

    def run(self) -> int:
        if Gtk is None or Adw is None or not os.environ.get("DISPLAY"):
            return 0
        self._build_ui()
        if self.app is not None:
            return self.app.run()
        return 0

    def start_recording(self):
        return self.recorder.start_recording(self.settings.output_dir)

    def pause_recording(self):
        if self.recorder.state == RecorderState.RECORDING:
            return self.recorder.pause_recording()
        return self.recorder.state

    def resume_recording(self):
        if self.recorder.state == RecorderState.PAUSED:
            return self.recorder.resume_recording()
        return self.recorder.state

    def stop_recording(self):
        if self.recorder.state in {RecorderState.RECORDING, RecorderState.PAUSED}:
            return self.recorder.stop_recording()
        return None
