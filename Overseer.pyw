"""Double-click to open the Overseer window (Windows runs .pyw files without a console).

It is also the entry point the release build turns into Overseer.exe.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from overseer import gui  # noqa: E402

raise SystemExit(gui.main())
