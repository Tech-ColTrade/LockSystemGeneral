"""Levanta el entorno de desarrollo: backend (Django) y frontend (Vite).

Abre una consola por servicio. Si el puerto de un servicio ya está ocupado se
asume que ese servicio ya está corriendo y no se vuelve a lanzar, para evitar
consolas duplicadas peleando por el mismo puerto.

Uso:
    python a.py
"""

import os
import socket
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ / "backend"
FRONTEND = RAIZ / "frontend"

PUERTO_BACKEND = 8000
PUERTO_FRONTEND = 5173

# El venv no vive dentro del proyecto: la ruta de OneDrive supera el límite de
# 260 caracteres de Windows y pip no puede instalar ahí. Se busca primero uno
# local por si eso llega a cambiar.
CANDIDATOS_VENV = [
    BACKEND / ".venv",
    RAIZ / ".venv",
    Path(os.environ["USERPROFILE"]) / ".venvs" / "locksystem",
]


def puerto_ocupado(puerto: int) -> bool:
    """¿Hay algo escuchando en el puerto?

    Se prueban todas las direcciones de localhost: Vite se ata solo a ::1 (IPv6)
    y Django a 127.0.0.1, así que mirar una sola familia deja escapar la otra.
    """
    try:
        destinos = socket.getaddrinfo("localhost", puerto, type=socket.SOCK_STREAM)
    except socket.gaierror:
        destinos = []

    for familia, tipo, proto, _canon, direccion in destinos:
        s = socket.socket(familia, tipo, proto)
        s.settimeout(0.5)
        try:
            s.connect(direccion)
            return True
        except OSError:
            continue
        finally:
            s.close()
    return False


def buscar_venv() -> Path:
    for venv in CANDIDATOS_VENV:
        if (venv / "Scripts" / "activate.bat").is_file():
            return venv
    rutas = "\n  ".join(str(v) for v in CANDIDATOS_VENV)
    sys.exit(
        f"No se encontró un entorno virtual. Se buscó en:\n  {rutas}\n"
        f"Créalo con: python -m venv <ruta> && <ruta>\\Scripts\\pip install -r "
        f"{BACKEND / 'requirements.txt'}"
    )


def abrir_consola(titulo: str, cwd: Path, comando: str) -> None:
    """Abre una consola nueva que queda viva (cmd /k) ejecutando el comando."""
    subprocess.Popen(
        ["cmd", "/c", "start", titulo, "cmd", "/k", comando],
        cwd=str(cwd),
    )


def main() -> None:
    lanzados = []

    if puerto_ocupado(PUERTO_BACKEND):
        print(f"[backend]  ya corriendo en el puerto {PUERTO_BACKEND}, se omite.")
    else:
        venv = buscar_venv()
        activate = venv / "Scripts" / "activate.bat"
        abrir_consola(
            "backend - django",
            BACKEND,
            f'call "{activate}" && python manage.py runserver',
        )
        lanzados.append(f"backend  -> http://127.0.0.1:{PUERTO_BACKEND} (venv: {venv})")

    if puerto_ocupado(PUERTO_FRONTEND):
        print(f"[frontend] ya corriendo en el puerto {PUERTO_FRONTEND}, se omite.")
    else:
        # Sin node_modules, `npm run dev` falla al instante y la consola quedaría
        # abierta con un error; se instala antes en la misma consola.
        if (FRONTEND / "node_modules").is_dir():
            comando = "npm run dev"
        else:
            print("[frontend] falta node_modules: se ejecutará npm install primero.")
            comando = "npm install && npm run dev"
        abrir_consola("frontend - vite", FRONTEND, comando)
        lanzados.append(f"frontend -> http://127.0.0.1:{PUERTO_FRONTEND}")

    if lanzados:
        print("Consolas abiertas:")
        for linea in lanzados:
            print("  " + linea)
    else:
        print("Todo ya estaba corriendo. No se abrió nada.")


if __name__ == "__main__":
    main()
