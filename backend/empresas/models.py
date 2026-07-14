"""La empresa (tenant) es el eje del aislamiento de datos.

Cada usuario pertenece a una empresa y solo ve lo de la suya; los televisores y
todos sus registros llevan la empresa dueña. La única excepción es el
superusuario, que no tiene empresa y ve el sistema completo.

El aislamiento se aplica en `empresas/scoping.py`, no aquí.
"""
from __future__ import annotations

import uuid

from django.db import models


class Empresa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField('nombre', max_length=150, unique=True)
    nit = models.CharField('NIT', max_length=30, blank=True, default='')

    activa = models.BooleanField(
        'activa',
        default=True,
        help_text='Si se desactiva, sus usuarios no podrán iniciar sesión.',
    )

    creado = models.DateTimeField('fecha de registro', auto_now_add=True)

    class Meta:
        verbose_name = 'empresa'
        verbose_name_plural = 'empresas'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip()
        if self.nit:
            self.nit = self.nit.strip()
        super().save(*args, **kwargs)
