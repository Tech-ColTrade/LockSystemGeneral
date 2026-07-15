"""Tope GLOBAL de navegadores Selenium simultáneos (para todo el servidor).

Cada navegador headless pesa ~400-700 MB. Si se abren muchos a la vez, Render se
queda sin RAM y mata el proceso (OOM), dejando los jobs a medias. Para evitarlo
se limita cuántas sesiones pueden correr al tiempo, sin importar la empresa:

  - Sincronización MANUAL (un TV):  `SYNC_MAX_MANUAL` navegadores (por defecto 1).
  - Sincronización MASIVA (un lote): `SYNC_MAX_MASIVO` navegadores (por defecto 2).

Son dos cupos independientes: en el peor caso pueden coexistir
`SYNC_MAX_MANUAL + SYNC_MAX_MASIVO` navegadores. Dimensiona la RAM del plan por
esa suma (p.ej. 1 + 2 = 3 navegadores ~= 1.5 GB solo en Chrome).

Un job que no consigue cupo NO falla: su hilo espera (bloquea) hasta que se
libere uno. Mientras tanto el job queda en estado `PENDIENTE` y el frontend lo
ve como "en cola" por polling, igual que siempre.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from django.conf import settings

# BoundedSemaphore: si por un bug se liberara de más, revienta en vez de dejar
# crecer el cupo en silencio (justo lo que no queremos con la RAM).
_sem_manual = threading.BoundedSemaphore(getattr(settings, 'SYNC_MAX_MANUAL', 1))
_sem_masivo = threading.BoundedSemaphore(getattr(settings, 'SYNC_MAX_MASIVO', 2))


@contextmanager
def cupo_navegador(masivo: bool):
    """Reserva un cupo de navegador; BLOQUEA hasta que haya uno libre.

    Úsalo alrededor de toda la vida del navegador (abrir -> usar -> cerrar), para
    que el cupo se libere recién cuando el Chrome ya se cerró de verdad.
    """
    sem = _sem_masivo if masivo else _sem_manual
    sem.acquire()
    try:
        yield
    finally:
        sem.release()
