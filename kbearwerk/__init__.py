"""KBEARWERK - Office automation desktop app for a structural engineering office.

The package is split into three layers:

* ``kbearwerk.services`` - the "engine": plain-Python helpers for files, Excel,
  Outlook, document generation and secret storage. These have **no** GUI
  dependencies so they can be unit-tested on any machine.
* ``kbearwerk.panels`` - one screen ("panel") per part of the job. Each panel is
  a CustomTkinter frame that drives the services.
* ``kbearwerk.app`` - the main window that ties the panels together with a
  left-hand navigation sidebar.

Nothing in ``kbearwerk.services`` imports ``tkinter``/``customtkinter``; keep it
that way so the engine stays testable without a display.
"""

from .version import __version__

__all__ = ["__version__"]
