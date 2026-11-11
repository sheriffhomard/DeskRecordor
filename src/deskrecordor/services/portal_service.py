from __future__ import annotations

import os
from typing import Any

try:
    from gi.repository import Gio, GLib
except ImportError:  # pragma: no cover - optional on minimal CI systems
    Gio = None
    GLib = None


class PortalService:
    """Wrap org.freedesktop.portal.ScreenCast and related xdg-desktop-portal APIs."""

    PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
    PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
    SCREENCAST_INTERFACE = "org.freedesktop.portal.ScreenCast"

    @staticmethod
    def is_available() -> bool:
        if not os.environ.get("WAYLAND_DISPLAY"):
            return False
        if Gio is None or GLib is None:
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

    @staticmethod
    def request_screen_capture() -> dict[str, Any]:
        if not PortalService.is_available():
            return {"available": False, "reason": "Wayland desktop portal is unavailable"}

        try:
            proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                None,
                PortalService.PORTAL_BUS_NAME,
                PortalService.PORTAL_OBJECT_PATH,
                PortalService.SCREENCAST_INTERFACE,
                None,
            )
            session = proxy.call_sync(
                "CreateSession",
                GLib.Variant("(a{sv})", [{}]),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            return {"available": True, "session": session}
        except Exception as exc:  # pragma: no cover - depends on the actual Wayland session
            return {"available": False, "reason": str(exc)}

    @staticmethod
    def default_pipewire_source() -> str:
        return os.environ.get("PIPEWIRE_SCREEN_SOURCE") or "default"
