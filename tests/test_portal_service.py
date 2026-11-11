from deskrecordor.core.capture import ScreenCapture
from deskrecordor.services.portal_service import PortalService


def test_wayland_default_monitor(monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monitors = ScreenCapture.list_monitors()
    assert monitors[0].monitor_id.startswith("wayland")
    assert monitors[0].primary is True


def test_portal_service_detects_non_wayland(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert PortalService.is_available() is False
    assert PortalService.default_pipewire_source() == "default"
