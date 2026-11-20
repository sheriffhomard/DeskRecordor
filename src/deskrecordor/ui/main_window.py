from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from deskrecordor import __version__
from deskrecordor.config.settings import Settings
from deskrecordor.core.audio import AudioManager
from deskrecordor.core.capture import ScreenCapture
from deskrecordor.core.recorder import Recorder
from deskrecordor.core.state_manager import RecorderState
from deskrecordor.ui.components import TimerLabel, VUMeter
from deskrecordor.utils.file_manager import generate_output_filename
from deskrecordor.utils.logger import get_log_file_path, get_logger

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, GLib, Gtk
except (ImportError, ValueError):  # pragma: no cover - GTK may not be available in CI
    Adw = None
    Gio = None
    GLib = None
    Gtk = None


class MainWindow:
    """GTK application window for DeskRecordor."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()
        self.logger = get_logger()
        self.logger.info("Starting DeskRecordor")
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
        self.output_label: Any | None = None
        self.start_button: Any | None = None
        self.pause_button: Any | None = None
        self.stop_button: Any | None = None
        self.maximize_button: Any | None = None
        self.maximize_image: Any | None = None
        self._help_windows: list[Any] = []
        self._timer_source_id: int | None = None
        self._countdown_source_id: int | None = None
        self._startup_source_id: int | None = None
        self._finalization_source_id: int | None = None
        self._startup_future: Any | None = None
        self._recording_seconds = 0
        self._countdown_remaining = 0
        self._folder_chooser: Any | None = None

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
        self.window.set_default_size(620, 480)
        self.window.connect("close-request", self.on_close_request)
        self.window.connect("notify::maximized", self._on_window_maximized_changed)
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(self._build_titlebar())

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=18,
            margin_bottom=18,
            margin_start=18,
            margin_end=18,
        )

        monitor_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        monitor_label = Gtk.Label(label="Moniteur :")
        self.monitor_combo = Gtk.ComboBoxText()
        self.monitor_combo.set_hexpand(True)
        monitor_tooltip = (
            "Choisissez l’écran à capturer. Sous Wayland, le portail système "
            "vous demandera de confirmer l’écran après le compte à rebours."
        )
        monitor_label.set_tooltip_text(monitor_tooltip)
        self.monitor_combo.set_tooltip_text(monitor_tooltip)
        monitor_group.append(monitor_label)
        monitor_group.append(self.monitor_combo)
        content.append(monitor_group)

        mic_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mic_label = Gtk.Label(label="Microphone :")
        self.microphone_combo = Gtk.ComboBoxText()
        self.microphone_combo.set_hexpand(True)
        microphone_tooltip = "Choisissez la source d’entrée audio à enregistrer."
        mic_label.set_tooltip_text(microphone_tooltip)
        self.microphone_combo.set_tooltip_text(microphone_tooltip)
        mic_group.append(mic_label)
        mic_group.append(self.microphone_combo)
        content.append(mic_group)

        self.vumeter_bar = Gtk.ProgressBar(show_text=True, text="Niveau micro non connecté")
        self.vumeter_bar.set_fraction(0.0)
        self.vumeter_bar.set_tooltip_text(
            "Le vumètre n’est pas encore relié au signal audio réel."
        )
        content.append(self.vumeter_bar)

        output_title = Gtk.Label(label="Dossier de sauvegarde")
        output_title.set_xalign(0)
        output_title.set_tooltip_text("Emplacement où les fichiers vidéo seront enregistrés.")
        content.append(output_title)
        output_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.output_label = Gtk.Label()
        self.output_label.set_xalign(0)
        self.output_label.set_ellipsize(3)
        self.output_label.set_hexpand(True)
        choose_folder_button = Gtk.Button(label="Choisir…")
        choose_folder_button.set_tooltip_text("Choisir le dossier de destination des vidéos.")
        choose_folder_button.connect("clicked", self.on_choose_folder_clicked)
        output_group.append(self.output_label)
        output_group.append(choose_folder_button)
        content.append(output_group)

        self.timer_label = Gtk.Label(label="00:00:00")
        self.timer_label.get_style_context().add_class("title-2")
        self.timer_label.set_tooltip_text("Durée écoulée de la capture en cours.")
        self.status_label = Gtk.Label(label="Prêt")
        self.status_label.set_wrap(True)
        self.status_label.set_xalign(0.5)
        self.status_label.set_tooltip_text("État de la capture et éventuels messages d’erreur.")
        content.append(self.timer_label)
        content.append(self.status_label)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.CENTER)
        self.start_button = Gtk.Button(label="ENREGISTRER")
        self.pause_button = Gtk.Button(label="PAUSE")
        self.stop_button = Gtk.Button(label="ARRÊTER")
        self.start_button.set_tooltip_text("Démarrer la capture après un compte à rebours de 3 secondes.")
        self.pause_button.set_tooltip_text("Mettre la capture en pause.")
        self.stop_button.set_tooltip_text("Arrêter la capture et finaliser le fichier vidéo.")
        self.pause_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        self.start_button.connect("clicked", self.on_start_clicked)
        self.pause_button.connect("clicked", self.on_pause_clicked)
        self.stop_button.connect("clicked", self.on_stop_clicked)
        controls.append(self.start_button)
        controls.append(self.pause_button)
        controls.append(self.stop_button)
        content.append(controls)

        utility_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.CENTER)
        logs_button = Gtk.Button(label="JOURNAL")
        logs_button.set_tooltip_text("Afficher les journaux de diagnostic.")
        logs_button.connect("clicked", self.on_logs_clicked)
        quit_button = Gtk.Button(label="QUITTER / INTERROMPRE")
        quit_button.get_style_context().add_class("destructive-action")
        quit_button.set_tooltip_text(
            "Fermer l’application et interrompre immédiatement la capture en cours."
        )
        quit_button.connect("clicked", self.on_quit_clicked)
        utility_controls.append(logs_button)
        utility_controls.append(quit_button)
        content.append(utility_controls)

        toolbar_view.set_content(content)
        self.window.set_content(toolbar_view)
        self.populate_controls()
        self._update_output_label()
        self.window.present()
        self.logger.info("DeskRecordor window opened")

    def _build_titlebar(self) -> Any:
        header_bar = Adw.HeaderBar()
        header_bar.set_show_start_title_buttons(False)
        header_bar.set_show_end_title_buttons(False)

        title = Gtk.Label(label="DeskRecordor")
        title.add_css_class("title")
        header_bar.set_title_widget(title)

        help_button = Gtk.Button(label="?")
        help_button.add_css_class("flat")
        help_button.set_tooltip_text("Documentation, version et mentions légales.")
        help_button.connect("clicked", self.on_help_clicked)
        header_bar.pack_start(help_button)

        onboarding_button = Gtk.Button(label="Guide")
        onboarding_button.add_css_class("flat")
        onboarding_button.set_tooltip_text("Afficher le guide de prise en main.")
        onboarding_button.connect("clicked", self.onboarding_clicked)
        header_bar.pack_start(onboarding_button)

        close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
        close_button.set_tooltip_text("Fermer l’application et interrompre la capture.")
        close_button.connect("clicked", self.on_quit_clicked)
        header_bar.pack_end(close_button)

        self.maximize_button = Gtk.Button()
        self.maximize_image = Gtk.Image.new_from_icon_name("window-maximize-symbolic")
        self.maximize_button.set_child(self.maximize_image)
        self.maximize_button.set_tooltip_text("Agrandir la fenêtre.")
        self.maximize_button.connect("clicked", self.on_toggle_maximize_clicked)
        header_bar.pack_end(self.maximize_button)

        minimize_button = Gtk.Button.new_from_icon_name("window-minimize-symbolic")
        minimize_button.set_tooltip_text("Réduire la fenêtre.")
        minimize_button.connect("clicked", self.on_minimize_clicked)
        header_bar.pack_end(minimize_button)
        return header_bar

    def on_minimize_clicked(self, _button: Any) -> None:
        if self.window is not None:
            self.window.minimize()

    def on_toggle_maximize_clicked(self, _button: Any) -> None:
        if self.window is None:
            return
        if self.window.is_maximized():
            self.window.unmaximize()
        else:
            self.window.maximize()

    def _on_window_maximized_changed(self, *_args: Any) -> None:
        if self.window is None or self.maximize_button is None or self.maximize_image is None:
            return
        maximized = self.window.is_maximized()
        icon_name = "window-restore-symbolic" if maximized else "window-maximize-symbolic"
        tooltip = "Restaurer la taille précédente." if maximized else "Agrandir la fenêtre."
        self.maximize_image.set_from_icon_name(icon_name)
        self.maximize_button.set_tooltip_text(tooltip)

    def _show_information_window(
        self,
        title: str,
        sections: list[tuple[str, str]],
    ) -> None:
        if Gtk is None or self.window is None:
            return
        info_window = Gtk.Window()
        info_window.set_title(title)
        info_window.set_transient_for(self.window)
        info_window.set_modal(True)
        info_window.set_default_size(560, 540)
        if self.app is not None:
            info_window.set_application(self.app)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            margin_top=20,
            margin_bottom=20,
            margin_start=20,
            margin_end=20,
        )
        for heading_text, body_text in sections:
            heading = Gtk.Label(label=heading_text)
            heading.add_css_class("heading")
            heading.set_xalign(0)
            body = Gtk.Label(label=body_text)
            body.set_wrap(True)
            body.set_xalign(0)
            body.set_selectable(True)
            content.append(heading)
            content.append(body)

        scroll = Gtk.ScrolledWindow()
        scroll.set_child(content)
        info_window.set_child(scroll)
        self._help_windows.append(info_window)
        info_window.connect("close-request", self._on_information_window_closed)
        info_window.present()

    def _on_information_window_closed(self, window: Any) -> bool:
        if window in self._help_windows:
            self._help_windows.remove(window)
        return False

    def on_help_clicked(self, _button: Any) -> None:
        self._show_information_window(
            "Documentation — DeskRecordor",
            [
                ("Version", f"DeskRecordor {__version__}"),
                (
                    "Enregistrer une vidéo",
                    "Choisissez un microphone et le dossier de sauvegarde, puis cliquez "
                    "sur ENREGISTRER. Après le compte à rebours, sélectionnez et autorisez "
                    "le partage de l’écran dans le portail système. Utilisez PAUSE ou "
                    "ARRÊTER pour contrôler et finaliser la capture.",
                ),
                (
                    "Fichiers et diagnostic",
                    "Les vidéos restent dans le dossier choisi. Le bouton JOURNAL affiche "
                    "les informations de diagnostic. QUITTER / INTERROMPRE arrête "
                    "immédiatement la capture ; le fichier partiel peut être inutilisable.",
                ),
                (
                    "Mentions légales",
                    "L’application est fournie « en l’état », sans garantie. Vous êtes "
                    "responsable de son utilisation, des autorisations et consentements "
                    "nécessaires, ainsi que du respect du droit à l’image, du droit d’auteur "
                    "et des règles de protection des données. Le développeur ne peut être "
                    "tenu responsable des usages, pertes ou dommages résultant de son "
                    "utilisation, dans les limites permises par la loi.",
                ),
            ],
        )

    def onboarding_clicked(self, _button: Any) -> None:
        self._show_information_window(
            "Bien démarrer — DeskRecordor",
            [
                (
                    "1. Choisir les sources",
                    "Sélectionnez le microphone à enregistrer. Sous Wayland, le choix "
                    "de l’écran se fait dans la fenêtre de partage système après le "
                    "compte à rebours.",
                ),
                (
                    "2. Choisir où enregistrer",
                    "Le dossier de sauvegarde affiche le prochain nom de fichier. "
                    "Cliquez sur Choisir… pour sélectionner un autre emplacement.",
                ),
                (
                    "3. Démarrer et terminer",
                    "Cliquez sur ENREGISTRER, puis autorisez le partage de l’écran si "
                    "le portail le demande. Le chronomètre commence lorsque la capture "
                    "vidéo est lancée. ARRÊTER finalise le fichier ; QUITTER / INTERROMPRE "
                    "coupe immédiatement la capture et peut laisser un fichier incomplet.",
                ),
                (
                    "Besoin d’aide ?",
                    "Le bouton JOURNAL affiche les diagnostics. Le vumètre audio n’est "
                    "pas encore connecté au signal réel : vérifiez la présence du son "
                    "en lisant la vidéo enregistrée.",
                ),
            ],
        )

    def populate_controls(self) -> None:
        if self.monitor_combo is not None:
            self.monitor_combo.remove_all()
            monitors = ScreenCapture.list_monitors()
            for monitor in monitors:
                self.monitor_combo.append(
                    monitor.monitor_id,
                    f"{monitor.name} ({monitor.resolution})",
                )
            if not self.monitor_combo.set_active_id(self.settings.default_monitor or ""):
                self.monitor_combo.set_active(0)

        if self.microphone_combo is not None:
            self.microphone_combo.remove_all()
            audio_manager = AudioManager(self.settings.default_microphone)
            microphones = audio_manager.list_microphones()
            for mic in microphones:
                self.microphone_combo.append(mic.device_id, mic.label)
            default_microphone = audio_manager.default_microphone()
            if not self.microphone_combo.set_active_id(default_microphone.device_id):
                self.microphone_combo.set_active(0)

    def _update_output_label(self) -> None:
        if self.output_label is None:
            return
        directory = Path(self.settings.output_dir).expanduser()
        filename = generate_output_filename(
            prefix=self.settings.output_prefix,
            extension=f".{self.settings.final_format}",
        )
        self.output_label.set_text(f"{directory}  —  prochain fichier : {filename}")
        self.output_label.set_tooltip_text(str(directory))

    def on_choose_folder_clicked(self, _button: Any) -> None:
        if Gtk is None or self.window is None:
            return
        self._folder_chooser = Gtk.FileChooserNative.new(
            "Choisir le dossier des enregistrements",
            self.window,
            Gtk.FileChooserAction.SELECT_FOLDER,
            "_Choisir",
            "_Annuler",
        )
        current_folder = Path(self.settings.output_dir).expanduser()
        if current_folder.exists():
            self._folder_chooser.set_current_folder(Gio.File.new_for_path(str(current_folder)))
        self._folder_chooser.connect("response", self._on_folder_chosen)
        self._folder_chooser.show()

    def _on_folder_chosen(self, chooser: Any, response: int) -> None:
        if Gtk is None:
            return
        if response != Gtk.ResponseType.ACCEPT:
            chooser.destroy()
            self._folder_chooser = None
            return
        selected = chooser.get_file()
        if selected is None or selected.get_path() is None:
            self._set_status("Impossible de lire le dossier choisi.")
            self.logger.error("Folder chooser returned no local path")
            chooser.destroy()
            self._folder_chooser = None
            return
        self.settings.output_dir = selected.get_path()
        try:
            self.settings.save()
            self._update_output_label()
            self._set_status("Dossier de sauvegarde mis à jour.")
            self.logger.info("Recording output directory set to %s", self.settings.output_dir)
        except OSError:
            self.logger.exception("Could not save output directory setting")
            self._set_status("Impossible d’enregistrer ce dossier. Consultez le journal.")
        chooser.destroy()
        self._folder_chooser = None

    def on_start_clicked(self, _button: Any) -> None:
        try:
            if self.recorder.state in {RecorderState.IDLE, RecorderState.COMPLETED, RecorderState.ERROR}:
                self.recorder.prepare()
            if self.monitor_combo is not None:
                self.settings.default_monitor = self.monitor_combo.get_active_id()
            if self.microphone_combo is not None:
                self.settings.default_microphone = self.microphone_combo.get_active_id()
            self.recorder.audio_manager = AudioManager(self.settings.default_microphone)
            self.settings.save()
            self._countdown_remaining = 3
            self.start_button.set_sensitive(False)
            self.pause_button.set_sensitive(False)
            self.stop_button.set_sensitive(False)
            self._set_status("Démarrage de la capture dans 3…")
            if self.timer_label is not None:
                self.timer_label.set_text("00:00:03")
            self.logger.info("Capture requested; countdown started")
            self._countdown_source_id = GLib.timeout_add_seconds(1, self._countdown_tick)
        except Exception as exc:
            self.logger.exception("Could not prepare recording")
            self._set_status(f"Échec du démarrage : {exc}")
            self.start_button.set_sensitive(True)

    def _countdown_tick(self) -> bool:
        self._countdown_remaining -= 1
        if self._countdown_remaining > 0:
            self._set_status(f"Démarrage de la capture dans {self._countdown_remaining}…")
            if self.timer_label is not None:
                self.timer_label.set_text(f"00:00:0{self._countdown_remaining}")
            return True

        self._countdown_source_id = None
        self._startup_future = self.recorder.start_recording_async(self.settings.output_dir)
        if ScreenCapture.uses_wayland_portal():
            self._set_status("Autorisez le partage d’écran dans la fenêtre du portail…")
        else:
            self._set_status("Démarrage de la capture…")
        self._startup_source_id = GLib.timeout_add(150, self._poll_startup)
        return False

    def _poll_startup(self) -> bool:
        future = self._startup_future
        if future is None or not future.done():
            return True

        self._startup_future = None
        self._startup_source_id = None
        try:
            output_path = future.result()
            self._set_status(f"Enregistrement en cours — {output_path.name}")
            self.logger.info("Recording started: %s", output_path)
            self.pause_button.set_sensitive(True)
            self.stop_button.set_sensitive(True)
            self._recording_seconds = 0
            self._timer_source_id = GLib.timeout_add_seconds(1, self._tick_timer)
        except Exception as exc:
            self.logger.exception("Recording failed to start")
            self._set_status(f"Échec de la capture : {exc}\nConsultez le journal pour les détails.")
            self.start_button.set_sensitive(True)
            if self.timer_label is not None:
                self.timer_label.set_text("00:00:00")
        return False

    def on_pause_clicked(self, _button: Any) -> None:
        try:
            if self.recorder.state == RecorderState.RECORDING:
                self.recorder.pause_recording()
                self._set_status("Enregistrement en pause")
                self.pause_button.set_label("REPRENDRE")
                self.pause_button.set_tooltip_text("Reprendre la capture.")
                self.logger.info("Recording paused")
            elif self.recorder.state == RecorderState.PAUSED:
                self.recorder.resume_recording()
                self._set_status("Enregistrement en cours")
                self.pause_button.set_label("PAUSE")
                self.pause_button.set_tooltip_text("Mettre la capture en pause.")
                self.logger.info("Recording resumed")
        except Exception as exc:
            self.logger.exception("Could not change recording state")
            self._set_status(f"Erreur de capture : {exc}")

    def on_stop_clicked(self, _button: Any) -> None:
        self._remove_source("_timer_source_id")
        try:
            if self.recorder.state in {RecorderState.RECORDING, RecorderState.PAUSED}:
                future = self.recorder.stop_recording()
                self._set_status("Finalisation en cours — vous pouvez consulter le journal ou quitter.")
                self.logger.info("Recording stop requested")
                self.pause_button.set_sensitive(False)
                self.stop_button.set_sensitive(False)
                self._finalization_source_id = GLib.timeout_add(
                    150,
                    self._poll_finalization,
                    future,
                )
        except Exception as exc:
            self.logger.exception("Could not stop recording")
            self._set_status(f"Échec de l’arrêt : {exc}")

    def _poll_finalization(self, future: Any) -> bool:
        if not future.done():
            return True
        self._finalization_source_id = None
        try:
            output_path = future.result()
            if output_path is None:
                detail = self.recorder.state_manager.last_error or "Le fichier vidéo est invalide."
                self._set_status(f"Échec de la finalisation : {detail}")
                self.logger.error("Finalization failed: %s", detail)
            else:
                self._set_status(f"Vidéo enregistrée : {output_path}")
                self.logger.info("Recording available at %s", output_path)
                self._update_output_label()
        except Exception as exc:
            self.logger.exception("Finalization future failed")
            self._set_status(f"Échec de la finalisation : {exc}")
        self.start_button.set_sensitive(True)
        self.pause_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        return False

    def _tick_timer(self) -> bool:
        if not self.recorder.check_capture_health():
            self._timer_source_id = None
            self._set_status("La capture s’est arrêtée. Consultez le journal.")
            self.logger.error("Capture health check failed")
            self.start_button.set_sensitive(True)
            self.pause_button.set_sensitive(False)
            self.stop_button.set_sensitive(False)
            return False

        if self.recorder.state == RecorderState.RECORDING:
            self._recording_seconds += 1
            if self.timer_label is not None:
                hours, remainder = divmod(self._recording_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.timer_label.set_text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return True

    def _set_status(self, message: str) -> None:
        if self.status_label is not None:
            self.status_label.set_text(message)

    def _remove_source(self, attribute: str) -> None:
        source_id = getattr(self, attribute)
        if source_id is not None and GLib is not None:
            GLib.source_remove(source_id)
            setattr(self, attribute, None)

    def on_logs_clicked(self, _button: Any) -> None:
        if Gtk is None or self.window is None:
            return
        log_path = get_log_file_path()
        try:
            log_text = log_path.read_text(encoding="utf-8")
        except OSError as exc:
            log_text = f"Impossible de lire le journal : {exc}"

        log_window = Gtk.Window(title=f"Journal DeskRecordor — {log_path}")
        log_window.set_transient_for(self.window)
        log_window.set_default_size(760, 420)
        text_view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        text_view.get_buffer().set_text(log_text[-30000:])
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(text_view)
        log_window.set_child(scrolled)
        log_window.present()

    def on_quit_clicked(self, _button: Any) -> None:
        self._quit_immediately()

    def on_close_request(self, _window: Any) -> bool:
        self._quit_immediately()
        return True

    def _quit_immediately(self) -> None:
        self.logger.warning("Quit requested; aborting active capture")
        self._remove_source("_countdown_source_id")
        self._remove_source("_startup_source_id")
        self._remove_source("_timer_source_id")
        self._remove_source("_finalization_source_id")
        if self._folder_chooser is not None:
            self._folder_chooser.destroy()
            self._folder_chooser = None
        try:
            self.recorder.abort()
        except Exception:
            self.logger.exception("Error while aborting capture during quit")
        if self.app is not None:
            self.app.quit()

    def run(self) -> int:
        if Gtk is None or Adw is None or not (
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        ):
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
