"""Prepara las APIs del experimento (se ejecuta UNA vez, antes del benchmark).

    python benchmark/setup_apis.py

- Descarga el código fuente de VAmPI y de Full Stack FastAPI Template en benchmark/apis/,
  fijado en un commit concreto (reproducibilidad: todos usan exactamente la misma versión).
- Construye sus imágenes Docker.
- Descarga la imagen de Swagger Petstore v3.

Requiere Git y Docker Desktop abiertos. La primera vez tarda varios minutos (sobre todo
la imagen de FastAPI Template, que también compila su frontend).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APIS_DIR = ROOT / "benchmark" / "apis"

REPOS = {
    # nombre carpeta: (URL, commit fijado, fecha del commit)
    "VAmPI": ("https://github.com/erev0s/VAmPI", "f16052dce83f05847133ec98f01c5193a41de7d8", "2026-04-07"),
    "full-stack-fastapi-template": ("https://github.com/fastapi/full-stack-fastapi-template",
                                    "aabb90126964a164e02aff39e7c385bb0598236d", "2026-11-03"),
}
VAMPI_IMAGE = "deltaheal/vampi:f16052d"
PETSTORE_IMAGE = "swaggerapi/petstore3:unstable"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if r.returncode != 0:
        sys.exit(f"\n❌ Falló: {' '.join(cmd)}")


def main() -> int:
    for tool in ("git", "docker"):
        if not shutil.which(tool):
            sys.exit(f"❌ No se encontró '{tool}'. Instálalo (y abre Docker Desktop) antes de continuar.")
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        sys.exit("❌ Docker no está corriendo: abre Docker Desktop y espera a que diga 'Engine running'.")

    APIS_DIR.mkdir(parents=True, exist_ok=True)
    for name, (url, commit, date) in REPOS.items():
        dest = APIS_DIR / name
        if not (dest / ".git").exists():
            run(["git", "clone", url, str(dest)])
        run(["git", "-C", str(dest), "fetch", "--all", "--quiet"])
        run(["git", "-C", str(dest), "checkout", "--quiet", commit])
        print(f"   ✔ {name} fijado en {commit[:10]} ({date})")

    print("\n▶ Imagen de VAmPI")
    run(["docker", "build", "-t", VAMPI_IMAGE, str(APIS_DIR / "VAmPI")])

    print("\n▶ Imágenes de FastAPI Template (puede tardar varios minutos la primera vez)")
    run(["docker", "compose", "-p", "fastapi_bench", "-f", "compose.yml",
         "-f", str(ROOT / "benchmark" / "docker" / "fastapi-template.override.yml"), "build", "backend"],
        cwd=APIS_DIR / "full-stack-fastapi-template")

    print("\n▶ Imagen de Swagger Petstore v3")
    run(["docker", "pull", PETSTORE_IMAGE])

    print("\n✅ APIs listas. Siguiente paso:  python benchmark/run.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
