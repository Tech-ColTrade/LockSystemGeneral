"""Enrolar Estado: aplicar estados (habilitado/inhabilitado) masivamente.

Los datos pueden llegar de dos formas, pero se procesan igual:
    - Archivo CSV/XLSX  -> procesar_enrolar_estado()  (lo usa el panel)
    - Lista JSON        -> procesar_registros()        (lo usa la integración)

Campos reconocidos (columna del archivo o clave del JSON):
    - mac_address    (obligatoria)
    - estado         (obligatoria: habilitado/inhabilitado, sinónimos o booleano)
    - serial_number  (opcional)

Fija el estado LOCAL de cada televisor (creándolo si no existe) y devuelve la
lista de televisores cuyo estado cambió, para sincronizarlos con el portal.
"""
from __future__ import annotations

from django.db import transaction

from .api.imports import leer_filas
from .models import Televisor

# Sinónimos aceptados en la columna 'estado'.
_INHABILITADO = {
    'inhabilitado', 'inhabilitar', 'inhabilitacion', 'inhabilitación',
    'bloqueado', 'bloqueo', 'bloquear', 'lock', 'locked', 'si', 'sí',
    'true', '1', 'x', 'yes', 'y',
}
_HABILITADO = {
    'habilitado', 'habilitar', 'habilitacion', 'habilitación',
    'desbloqueado', 'desbloqueo', 'desbloquear', 'unlock', 'unlocked',
    'no', 'false', '0', 'n',
}

_COL_MAC = {'mac_address', 'mac', 'mac_address', 'direccion_mac', 'dirección_mac'}
_COL_ESTADO = {'estado', 'status', 'lock', 'lock_status', 'inhabilitado', 'bloqueo'}
_COL_SERIAL = {'serial_number', 'serial', 'sn', 'numero_de_serie', 'número_de_serie'}


def _parse_estado(valor: str):
    """True (inhabilitado), False (habilitado) o None si no se reconoce."""
    t = (valor or '').strip().lower()
    if t in _INHABILITADO:
        return True
    if t in _HABILITADO:
        return False
    return None


def _parse_estado_valor(valor):
    """Como _parse_estado pero admite además un booleano JSON (true = inhabilitar)."""
    if isinstance(valor, bool):
        return valor
    return _parse_estado('' if valor is None else str(valor))


def _mapear_columnas(headers: list[str]) -> dict:
    mapa = {}
    for i, h in enumerate(headers):
        clave = (h or '').strip().lower().replace(' ', '_')
        if clave in _COL_MAC:
            mapa['mac'] = i
        elif clave in _COL_ESTADO:
            mapa['estado'] = i
        elif clave in _COL_SERIAL:
            mapa['serial'] = i
    return mapa


def procesar_enrolar_estado(nombre: str, data: bytes, empresa) -> dict:
    """Aplica los estados del archivo y devuelve el resumen + los TV cambiados.

    Solo toca televisores de `empresa`. Una MAC que ya exista en otra empresa se
    rechaza como error de fila: cambiar el estado de un equipo ajeno lo
    bloquearía/desbloquearía de verdad en el portal, no solo en la app.

    Return: {'creados', 'actualizados', 'errores': [..], 'cambiados': [Televisor,..]}
    """
    filas = leer_filas(nombre, data)
    if not filas:
        return {'creados': 0, 'actualizados': 0, 'errores': ['El archivo está vacío.'], 'cambiados': []}

    mapa = _mapear_columnas(filas[0])
    faltan = [c for c in ('mac', 'estado') if c not in mapa]
    if faltan:
        nombres = {'mac': 'mac_address', 'estado': 'estado'}
        return {
            'creados': 0,
            'actualizados': 0,
            'errores': ['Faltan columnas: ' + ', '.join(nombres[c] for c in faltan)],
            'cambiados': [],
        }

    errores: list[str] = []
    orden: list[str] = []
    deseado: dict[str, dict] = {}

    def celda(fila, i):
        return fila[i].strip() if i is not None and i < len(fila) else ''

    for n, fila in enumerate(filas[1:], start=2):
        mac = celda(fila, mapa['mac']).upper()
        estado = _parse_estado(celda(fila, mapa['estado']))
        serial = celda(fila, mapa.get('serial'))
        if not mac:
            continue
        if estado is None:
            errores.append(f'Fila {n} ({mac}): estado inválido (usa "habilitado" o "inhabilitado").')
            continue
        if mac not in deseado:
            orden.append(mac)
        deseado[mac] = {'mac': mac, 'estado': estado, 'serial': serial or deseado.get(mac, {}).get('serial', '')}

    return _aplicar_estados(orden, deseado, errores, empresa)


def procesar_registros(registros, empresa) -> dict:
    """Igual que procesar_enrolar_estado pero desde una lista JSON (no un archivo).

    `registros` es una lista de objetos con las mismas claves que las columnas del
    Excel: {mac_address, estado, serial_number?}. Es lo que usa un ERP: hace un
    POST con los datos, sin subir ningún archivo.

    Return: {'creados', 'actualizados', 'errores': [..], 'cambiados': [Televisor,..]}
    """
    if not isinstance(registros, list) or not registros:
        return {'creados': 0, 'actualizados': 0,
                'errores': ['Envía "registros" como una lista con al menos un elemento.'],
                'cambiados': []}

    errores: list[str] = []
    orden: list[str] = []
    deseado: dict[str, dict] = {}

    for i, reg in enumerate(registros, start=1):
        if not isinstance(reg, dict):
            errores.append(f'Registro {i}: debe ser un objeto.')
            continue
        mac = str(reg.get('mac_address') or reg.get('mac') or '').strip().upper()
        estado = _parse_estado_valor(reg.get('estado'))
        serial = str(reg.get('serial_number') or reg.get('serial') or '').strip()
        if not mac:
            errores.append(f'Registro {i}: falta "mac_address".')
            continue
        if estado is None:
            errores.append(
                f'Registro {i} ({mac}): "estado" inválido '
                '(usa "habilitado"/"inhabilitado" o true/false).'
            )
            continue
        if mac not in deseado:
            orden.append(mac)
        deseado[mac] = {'mac': mac, 'estado': estado,
                        'serial': serial or deseado.get(mac, {}).get('serial', '')}

    return _aplicar_estados(orden, deseado, errores, empresa)


def procesar_registros_por_serial(registros, empresa) -> dict:
    """Cambio de estado masivo para INTEGRACIÓN: identifica cada televisor por su
    SERIAL, no por MAC.

    A diferencia del camino por MAC, aquí NO se crean televisores: un equipo se
    da de alta con su MAC (ver crear televisor), así que por serial solo se
    ACTUALIZA el estado de equipos que ya existen en la empresa. Un serial que no
    exista se reporta en "errores".

    Return: {'creados', 'actualizados', 'errores': [..], 'cambiados': [Televisor,..]}
    """
    if not isinstance(registros, list) or not registros:
        return {'creados': 0, 'actualizados': 0,
                'errores': ['Envía "registros" como una lista con al menos un elemento.'],
                'cambiados': []}

    errores: list[str] = []
    orden: list[str] = []          # seriales (en mayúsculas) en orden de aparición
    deseado: dict[str, dict] = {}  # serial_upper -> {serial, estado}

    for i, reg in enumerate(registros, start=1):
        if not isinstance(reg, dict):
            errores.append(f'Registro {i}: debe ser un objeto.')
            continue
        serial = str(reg.get('serial_number') or reg.get('serial') or '').strip()
        estado = _parse_estado_valor(reg.get('estado'))
        if not serial:
            errores.append(f'Registro {i}: falta "serial_number".')
            continue
        if estado is None:
            errores.append(
                f'Registro {i} ({serial}): "estado" inválido '
                '(usa "habilitado"/"inhabilitado" o true/false).'
            )
            continue
        clave = serial.upper()
        if clave not in deseado:
            orden.append(clave)
        deseado[clave] = {'serial': serial, 'estado': estado}

    if not orden:
        return {'creados': 0, 'actualizados': 0,
                'errores': errores or ['No hay registros válidos.'], 'cambiados': []}

    # Búsqueda por serial dentro de la empresa, insensible a mayúsculas: se
    # compara Upper(serial) contra los seriales pedidos (que ya vienen en
    # mayúsculas en `orden`). `__in` a secas sería sensible a mayúsculas en
    # Postgres y no encontraría 'SN-1' si el ERP manda 'sn-1'.
    from django.db.models.functions import Upper

    por_serial = {
        tv.serial_number.upper(): tv
        for tv in Televisor.objects.annotate(_su=Upper('serial_number')).filter(
            empresa=empresa, _su__in=orden,
        )
    }

    cambiados: list[Televisor] = []
    actualizar: list[Televisor] = []
    for k in orden:
        d = deseado[k]
        tv = por_serial.get(k)
        if tv is None:
            errores.append(
                f'{d["serial"]}: no existe un televisor con ese serial en tu empresa.'
            )
            continue
        if tv.inhabilitado != d['estado']:
            cambiados.append(tv)
        tv.inhabilitado = d['estado']
        actualizar.append(tv)

    if actualizar:
        with transaction.atomic():
            Televisor.objects.bulk_update(actualizar, ['inhabilitado'], batch_size=500)

    return {
        'creados': 0,
        'actualizados': len(actualizar),
        'errores': errores,
        'cambiados': cambiados,
    }


def _aplicar_estados(orden, deseado, errores, empresa) -> dict:
    """Núcleo común: valida contra la empresa y escribe en la base.

    Recibe los estados ya parseados (venga la data de un archivo o de un JSON):
    `orden` es la lista de MACs en orden de aparición y `deseado[mac]` = {mac,
    estado(bool), serial}. Devuelve el resumen + los televisores cambiados."""
    if not orden:
        return {'creados': 0, 'actualizados': 0,
                'errores': errores or ['No hay registros válidos.'], 'cambiados': []}

    encontrados = {
        tv.mac_address.upper(): tv
        for tv in Televisor.objects.filter(mac_address__in=[deseado[k]['mac'] for k in orden])
    }
    existentes = {
        mac: tv for mac, tv in encontrados.items() if tv.empresa_id == empresa.pk
    }

    # Seriales ya usados por otro equipo: rechazan la fila en vez de reventar el
    # bulk_create contra el índice único.
    seriales_tomados = {
        s.upper(): mac
        for s, mac in Televisor.objects.filter(
            serial_number__in={deseado[k]['serial'] for k in orden} - {''}
        ).values_list('serial_number', 'mac_address')
    }

    cambiados: list[Televisor] = []
    nuevos: list[Televisor] = []
    actualizar: list[Televisor] = []

    for k in orden:
        d = deseado[k]

        if k in encontrados and k not in existentes:
            errores.append(
                f'{d["mac"]}: esta MAC ya está registrada en el sistema y no '
                'pertenece a tu empresa.'
            )
            continue

        if d['serial']:
            dueño = seriales_tomados.get(d['serial'].upper())
            if dueño and dueño.upper() != k:
                errores.append(
                    f'{d["mac"]}: el serial "{d["serial"]}" ya está registrado en '
                    'otro televisor.'
                )
                continue

        tv = existentes.get(k)
        if tv is None:
            tv = Televisor(
                empresa=empresa, mac_address=d['mac'], serial_number=d['serial']
            )
            nuevos.append(tv)
        else:
            if d['serial'] and tv.serial_number != d['serial']:
                tv.serial_number = d['serial']
            actualizar.append(tv)

        if tv.inhabilitado != d['estado']:
            cambiados.append(tv)
        tv.inhabilitado = d['estado']

    # bulk_create/bulk_update no llaman a save(), así que la normalización que
    # hace Televisor.save() se aplica aquí a mano.
    for tv in (*nuevos, *actualizar):
        tv.mac_address = tv.mac_address.strip().upper()
        tv.serial_number = (tv.serial_number or '').strip()

    # Dos escrituras por lotes en vez de un save() por fila: contra una base de
    # datos remota, el round-trip por fila era el cuello de botella.
    with transaction.atomic():
        if nuevos:
            Televisor.objects.bulk_create(nuevos, batch_size=500)
        if actualizar:
            Televisor.objects.bulk_update(
                actualizar, ['serial_number', 'inhabilitado'], batch_size=500
            )

    creados = len(nuevos)
    actualizados = len(actualizar)
    return {
        'creados': creados,
        'actualizados': actualizados,
        'errores': errores,
        'cambiados': cambiados,
    }
