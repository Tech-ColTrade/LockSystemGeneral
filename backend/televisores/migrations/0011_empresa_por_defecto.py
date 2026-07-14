"""Backfill del multi-tenant: todo lo que ya existía pasa a una empresa.

Antes de esto no había empresas: había un único conjunto de televisores,
usuarios y registros. Se crea la empresa por defecto (configurable con
EMPRESA_POR_DEFECTO) y se le asigna todo, de modo que nadie pierde acceso a
nada. Los superusuarios se quedan SIN empresa: son el administrador general y
ven todas.
"""
from __future__ import annotations

import os

from django.db import migrations

NOMBRE_POR_DEFECTO = os.getenv('EMPRESA_POR_DEFECTO', 'Colombian Trade Company S.A.S.')


def crear_y_asignar(apps, schema_editor):
    Empresa = apps.get_model('empresas', 'Empresa')
    User = apps.get_model('users', 'User')
    Televisor = apps.get_model('televisores', 'Televisor')
    SyncJob = apps.get_model('televisores', 'SyncJob')
    BulkSyncJob = apps.get_model('televisores', 'BulkSyncJob')
    PinCodeUsado = apps.get_model('televisores', 'PinCodeUsado')

    # Si no hay absolutamente nada que migrar, no se crea una empresa vacía.
    hay_datos = (
        Televisor.objects.exists()
        or User.objects.filter(is_superuser=False).exists()
    )
    if not hay_datos:
        return

    empresa, _ = Empresa.objects.get_or_create(nombre=NOMBRE_POR_DEFECTO)

    Televisor.objects.filter(empresa__isnull=True).update(empresa=empresa)
    SyncJob.objects.filter(empresa__isnull=True).update(empresa=empresa)
    BulkSyncJob.objects.filter(empresa__isnull=True).update(empresa=empresa)
    PinCodeUsado.objects.filter(empresa__isnull=True).update(empresa=empresa)
    User.objects.filter(empresa__isnull=True, is_superuser=False).update(empresa=empresa)


def revertir(apps, schema_editor):
    """Deshace la asignación (la empresa se queda: borrarla es decisión manual)."""
    for modelo in ('Televisor', 'SyncJob', 'BulkSyncJob', 'PinCodeUsado'):
        apps.get_model('televisores', modelo).objects.update(empresa=None)
    apps.get_model('users', 'User').objects.update(empresa=None)


def verificar_seriales_unicos(apps, schema_editor):
    """Aborta si hay seriales repetidos: el índice único no podría crearse.

    Se comprueba aquí y no en el `AddConstraint` para poder decir CUÁLES están
    repetidos; el error de Postgres solo menciona el primero que encuentra.
    """
    Televisor = apps.get_model('televisores', 'Televisor')
    from django.db.models import Count

    repetidos = list(
        Televisor.objects.exclude(serial_number='')
        .values('serial_number')
        .annotate(n=Count('id'))
        .filter(n__gt=1)
        .values_list('serial_number', flat=True)[:20]
    )
    if repetidos:
        raise RuntimeError(
            'No se puede exigir un serial único: estos seriales están repetidos '
            'en la base de datos. Corrígelos (o déjalos vacíos) y vuelve a '
            'migrar: ' + ', '.join(repetidos)
        )


class Migration(migrations.Migration):
    dependencies = [
        ('televisores', '0010_bulksyncjob_empresa_pincodeusado_empresa_and_more'),
        ('empresas', '0001_initial'),
        ('users', '0005_user_empresa'),
    ]

    operations = [
        migrations.RunPython(crear_y_asignar, revertir),
        migrations.RunPython(verificar_seriales_unicos, migrations.RunPython.noop),
    ]
