import pytest

from deskrecordor.core.capture import ScreenCapture
from deskrecordor.services import portal_service
from deskrecordor.services.portal_service import PortalService


def test_wayland_default_monitor(monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monitors = ScreenCapture.list_monitors()
    assert monitors[0].monitor_id == "wayland-portal"
    assert "portail" in monitors[0].resolution
    assert monitors[0].primary is True


def test_portal_service_detects_non_wayland(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert PortalService.is_available() is False
    assert ScreenCapture.uses_wayland_portal() is False


@pytest.mark.skipif(portal_service.Gio is None, reason="PyGObject is not installed")
def test_portal_methods_use_screen_cast_dbus_signatures():
    class FakeConnection:
        def signal_subscribe(
            self,
            _sender,
            _interface,
            _member,
            _path,
            _arg0,
            _flags,
            callback,
            _user_data,
        ):
            self.callback = callback
            return 1

        def signal_unsubscribe(self, _subscription):
            return None

    class FakeProxy:
        def __init__(self, connection):
            self.connection = connection
            self.signatures = []

        def call_sync(self, method, parameters, *_args):
            self.signatures.append((method, parameters.get_type_string()))
            request_path = f"/request/{method}"
            response = portal_service.GLib.Variant("(ua{sv})", (0, {}))
            self.connection.callback(
                self.connection,
                PortalService.PORTAL_BUS_NAME,
                request_path,
                PortalService.REQUEST_INTERFACE,
                "Response",
                response,
                None,
            )
            return portal_service.GLib.Variant("(o)", (request_path,))

    class ImmediateContext:
        @staticmethod
        def iteration(_may_block):
            return False

    connection = FakeConnection()
    proxy = FakeProxy(connection)
    for method, session_handle in (
        ("CreateSession", None),
        ("SelectSources", "/session/test"),
        ("Start", "/session/test"),
    ):
        assert PortalService._request(
            proxy,
            connection,
            ImmediateContext(),
            method,
            session_handle,
            {},
            None,
        ) == {}

    assert proxy.signatures == [
        ("CreateSession", "(a{sv})"),
        ("SelectSources", "(oa{sv})"),
        ("Start", "(osa{sv})"),
    ]
