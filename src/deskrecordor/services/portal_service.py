from __future__ import annotations

import os
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

try:
    from gi.repository import Gio, GLib
except ImportError:  # pragma: no cover - optional on minimal CI systems
    Gio = None
    GLib = None


@dataclass
class PortalCapture:
    connection: Any
    session_handle: str
    node_id: int
    width: int
    height: int
    pipewire_fd: int


class PortalService:
    """Create and manage an xdg-desktop-portal ScreenCast session."""

    PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
    PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
    SCREENCAST_INTERFACE = "org.freedesktop.portal.ScreenCast"
    REQUEST_INTERFACE = "org.freedesktop.portal.Request"
    SESSION_INTERFACE = "org.freedesktop.portal.Session"

    @staticmethod
    def is_available() -> bool:
        if not os.environ.get("WAYLAND_DISPLAY") or Gio is None or GLib is None:
            return False
        try:
            Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                None,
                PortalService.PORTAL_BUS_NAME,
                PortalService.PORTAL_OBJECT_PATH,
                PortalService.SCREENCAST_INTERFACE,
                None,
            )
            return True
        except Exception:
            return False

    @classmethod
    def _request(
        cls,
        proxy: Any,
        connection: Any,
        context: Any,
        method: str,
        session_handle: str | None,
        options: dict[str, Any],
        cancel_event: threading.Event | None,
    ) -> dict[str, Any]:
        token = secrets.token_hex(8)
        options = dict(options)
        options["handle_token"] = GLib.Variant("s", token)
        responses: dict[str, tuple[int, dict[str, Any]]] = {}

        def on_response(
            _connection: Any,
            _sender: str,
            path: str,
            _interface: str,
            _signal: str,
            parameters: Any,
            _user_data: Any,
        ) -> None:
            responses[path] = parameters.unpack()

        subscription = connection.signal_subscribe(
            cls.PORTAL_BUS_NAME,
            cls.REQUEST_INTERFACE,
            "Response",
            None,
            None,
            Gio.DBusSignalFlags.NONE,
            on_response,
            None,
        )
        if session_handle is None:
            parameters = GLib.Variant("(a{sv})", (options,))
        elif method == "Start":
            parameters = GLib.Variant("(osa{sv})", (session_handle, "", options))
        else:
            parameters = GLib.Variant("(oa{sv})", (session_handle, options))
        try:
            result = proxy.call_sync(
                method,
                parameters,
                Gio.DBusCallFlags.NONE,
                30000,
                None,
            )
            request_path = result.unpack()[0]

            deadline = time.monotonic() + 180
            while request_path not in responses:
                if cancel_event is not None and cancel_event.is_set():
                    cls._close_request(connection, request_path)
                    raise RuntimeError("La demande de capture a été interrompue.")
                if time.monotonic() >= deadline:
                    cls._close_request(connection, request_path)
                    raise TimeoutError("Le portail n’a pas répondu en trois minutes.")
                if not context.iteration(False):
                    if cancel_event is not None:
                        cancel_event.wait(0.05)
                    else:
                        time.sleep(0.05)
        finally:
            connection.signal_unsubscribe(subscription)

        code, results = responses[request_path]
        if code != 0:
            if code == 1:
                raise RuntimeError("La demande de capture a été refusée ou annulée.")
            raise RuntimeError(f"Le portail a échoué (code {code}).")
        return results

    @classmethod
    def _close_request(cls, connection: Any, request_path: str) -> None:
        try:
            connection.call_sync(
                cls.PORTAL_BUS_NAME,
                request_path,
                cls.REQUEST_INTERFACE,
                "Close",
                GLib.Variant("()", ()),
                GLib.VariantType.new("()"),
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
        except Exception:
            logging.getLogger(__name__).exception("Could not close the portal request")

    @staticmethod
    def _close_session(connection: Any, session_handle: str) -> None:
        connection.call_sync(
            PortalService.PORTAL_BUS_NAME,
            session_handle,
            PortalService.SESSION_INTERFACE,
            "Close",
            GLib.Variant("()", ()),
            GLib.VariantType.new("()"),
            Gio.DBusCallFlags.NONE,
            2000,
            None,
        )

    @classmethod
    def start_capture(
        cls,
        cancel_event: threading.Event | None = None,
    ) -> PortalCapture:
        if not cls.is_available():
            raise RuntimeError(
                "Le portail de capture d’écran Wayland est indisponible. "
                "Vérifiez xdg-desktop-portal et le portail de votre environnement."
            )

        context = GLib.MainContext.new()
        context.push_thread_default()
        connection = None
        session_handle = None
        pipewire_fd = -1
        try:
            connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            proxy = Gio.DBusProxy.new_sync(
                connection,
                Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                None,
                cls.PORTAL_BUS_NAME,
                cls.PORTAL_OBJECT_PATH,
                cls.SCREENCAST_INTERFACE,
                None,
            )
            create_results = cls._request(
                proxy,
                connection,
                context,
                "CreateSession",
                None,
                {"session_handle_token": GLib.Variant("s", secrets.token_hex(8))},
                cancel_event,
            )
            session_handle = create_results.get("session_handle")
            if not session_handle:
                raise RuntimeError("Le portail n’a pas créé de session ScreenCast.")

            cls._request(
                proxy,
                connection,
                context,
                "SelectSources",
                session_handle,
                {
                    "types": GLib.Variant("u", 1),
                    "multiple": GLib.Variant("b", False),
                    "cursor_mode": GLib.Variant("u", 2),
                },
                cancel_event,
            )
            start_results = cls._request(
                proxy,
                connection,
                context,
                "Start",
                session_handle,
                {},
                cancel_event,
            )
            streams = start_results.get("streams", [])
            if not streams:
                raise RuntimeError("Aucun écran n’a été sélectionné dans le portail.")
            node_id, properties = streams[0]
            size = properties.get("size") if isinstance(properties, dict) else None
            if not size or len(size) != 2 or min(size) <= 0:
                raise RuntimeError("Le portail n’a pas fourni la résolution de l’écran.")

            fd_result, fd_list = connection.call_with_unix_fd_list_sync(
                cls.PORTAL_BUS_NAME,
                cls.PORTAL_OBJECT_PATH,
                cls.SCREENCAST_INTERFACE,
                "OpenPipeWireRemote",
                GLib.Variant("(oa{sv})", (session_handle, {})),
                GLib.VariantType.new("(h)"),
                Gio.DBusCallFlags.NONE,
                30000,
                None,
                None,
            )
            if fd_list is None:
                raise RuntimeError("Le portail n’a pas ouvert le flux PipeWire.")
            pipewire_fd = fd_list.get(fd_result.unpack()[0])
            if pipewire_fd < 0:
                raise RuntimeError("Le descripteur du flux PipeWire est invalide.")
            return PortalCapture(
                connection=connection,
                session_handle=session_handle,
                node_id=int(node_id),
                width=int(size[0]),
                height=int(size[1]),
                pipewire_fd=pipewire_fd,
            )
        except Exception:
            if pipewire_fd >= 0:
                try:
                    os.close(pipewire_fd)
                except OSError:
                    logging.getLogger(__name__).exception("Could not close the PipeWire FD")
            if connection is not None and session_handle:
                try:
                    cls._close_session(connection, session_handle)
                except Exception:
                    logging.getLogger(__name__).exception("Could not close the portal session")
            raise
        finally:
            context.pop_thread_default()

    @classmethod
    def close_capture(cls, capture: PortalCapture) -> None:
        errors: list[Exception] = []
        if capture.pipewire_fd >= 0:
            try:
                os.close(capture.pipewire_fd)
            except OSError as exc:
                errors.append(exc)
            capture.pipewire_fd = -1
        try:
            cls._close_session(capture.connection, capture.session_handle)
        except Exception as exc:
            errors.append(exc)
        if errors:
            raise RuntimeError("Impossible de fermer proprement la session du portail.") from errors[0]
