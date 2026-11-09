"""Progreso en consola: muestra cada etapa mientras ocurre y el tiempo de espera de la IA.

Se escribe en stderr para no mezclarse con la salida de datos (reporte o JSON en stdout).
Está desactivado por defecto; la CLI lo activa (`--quiet` lo desactiva).

- En una terminal interactiva, la espera se muestra en una sola línea que se actualiza cada segundo.
- Sin terminal (por ejemplo, en GitHub Actions), se imprime una línea cada 30 segundos.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

MAX_LINE = 160


class Progress:
    def __init__(self) -> None:
        self.enabled = False
        self._lock = threading.Lock()
        self._live_line = ""  # línea temporal de espera visible en la terminal

    @staticmethod
    def _is_tty() -> bool:
        try:
            return sys.stderr.isatty()
        except (AttributeError, ValueError):
            return False

    def _clear_live_line(self) -> None:
        """Borra la línea temporal de espera (llamar con el lock tomado)."""
        if self._live_line:
            sys.stderr.write("\r" + " " * len(self._live_line) + "\r")
            self._live_line = ""

    def message(self, text: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._clear_live_line()
            print(text, file=sys.stderr, flush=True)

    def step(self, title: str, detail: str = "") -> None:
        """Etapa completada (se usa como eco de la bitácora de pasos)."""
        text = f"  • {title}" + (f": {detail}" if detail else "")
        if len(text) > MAX_LINE:
            text = text[:MAX_LINE - 1] + "…"
        self.message(text)

    @contextmanager
    def waiting(self, text: str) -> Iterator[None]:
        """Indica una espera larga (llamada a la IA, ejecución de pruebas) con el tiempo transcurrido."""
        if not self.enabled:
            yield
            return
        tty = self._is_tty()
        interval = 1.0 if tty else 30.0
        stop = threading.Event()
        t0 = time.monotonic()

        def show(elapsed: int) -> None:
            line = f"  ⏳ {text}…" + (f" {elapsed} s" if tty or elapsed else "")
            with self._lock:
                if tty:
                    sys.stderr.write("\r" + line)
                    sys.stderr.flush()
                    self._live_line = line
                else:
                    print(line, file=sys.stderr, flush=True)

        def tick() -> None:
            while not stop.wait(interval):
                show(int(time.monotonic() - t0))

        show(0)
        worker = threading.Thread(target=tick, daemon=True)
        worker.start()
        try:
            yield
        finally:
            stop.set()
            worker.join()
            with self._lock:
                self._clear_live_line()


progress = Progress()
