from __future__ import annotations

from deskrecordor.ui.main_window import MainWindow


def main() -> int:
    """Run the desktop application."""
    window = MainWindow()
    return window.run()


if __name__ == "__main__":
    raise SystemExit(main())
