"""Aislamiento entre empresas (multi-tenant).

Estos tests son la red de seguridad del modelo: cada uno describe una fuga que
sería un incidente real si volviera a abrirse. Van todos contra la API, no
contra los modelos, porque el aislamiento tiene que sostenerse en la frontera
por la que entra un atacante.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import ApiKey, Empresa
from televisores.models import PinCodeUsado, Televisor

User = get_user_model()
CLAVE = 'ClaveSegura123'


class BaseTenancyTests(APITestCase):
    """Dos empresas, un usuario y un televisor en cada una."""

    def setUp(self):
        cache.clear()

        self.google = Empresa.objects.create(nombre='Google')
        self.acme = Empresa.objects.create(nombre='Acme')

        self.user_google = User.objects.create_user(
            email='ana@google.com', password=CLAVE, role='admin', empresa=self.google,
        )
        self.user_acme = User.objects.create_user(
            email='beto@acme.com', password=CLAVE, role='admin', empresa=self.acme,
        )
        self.superadmin = User.objects.create_superuser(
            email='root@sistema.com', password=CLAVE,
        )

        self.tv_google = Televisor.objects.create(
            empresa=self.google, mac_address='AA:AA:AA:AA:AA:AA', serial_number='SN-GOOGLE',
        )
        self.tv_acme = Televisor.objects.create(
            empresa=self.acme, mac_address='BB:BB:BB:BB:BB:BB', serial_number='SN-ACME',
        )


class ListadoYDetalleTests(BaseTenancyTests):
    def test_solo_ve_los_televisores_de_su_empresa(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.get(reverse('televisor-list'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        macs = [tv['mac_address'] for tv in resp.data['results']]
        self.assertEqual(macs, ['AA:AA:AA:AA:AA:AA'])

    def test_televisor_ajeno_da_404_y_no_403(self):
        # 404 y no 403: un 403 confirmaría que ese id existe, que ya es información.
        self.client.force_authenticate(self.user_google)
        resp = self.client.get(reverse('televisor-detail', args=[self.tv_acme.pk]))

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_puede_editar_televisor_ajeno(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.patch(
            reverse('televisor-detail', args=[self.tv_acme.pk]),
            {'numero_credito': '999'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.tv_acme.refresh_from_db()
        self.assertEqual(self.tv_acme.numero_credito, '')

    def test_no_puede_borrar_televisor_ajeno(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.delete(reverse('televisor-detail', args=[self.tv_acme.pk]))

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Televisor.objects.filter(pk=self.tv_acme.pk).exists())

    def test_superadmin_ve_todas_las_empresas(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.get(reverse('televisor-list'))

        self.assertEqual(resp.data['count'], 2)


class CreacionTests(BaseTenancyTests):
    def test_el_televisor_creado_queda_en_la_empresa_del_usuario(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.post(
            reverse('televisor-list'),
            {'mac_address': 'CC:CC:CC:CC:CC:CC', 'serial_number': 'SN-NUEVO'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        tv = Televisor.objects.get(mac_address='CC:CC:CC:CC:CC:CC')
        self.assertEqual(tv.empresa, self.google)

    def test_no_puede_crear_en_otra_empresa_mandando_empresa_en_el_cuerpo(self):
        # La empresa sale del token, nunca del cuerpo: si se aceptara, bastaría
        # con mandar el id de otra empresa para escribir en sus datos.
        self.client.force_authenticate(self.user_google)
        resp = self.client.post(
            reverse('televisor-list'),
            {
                'mac_address': 'CC:CC:CC:CC:CC:CC',
                'empresa': str(self.acme.pk),
            },
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        tv = Televisor.objects.get(mac_address='CC:CC:CC:CC:CC:CC')
        self.assertEqual(tv.empresa, self.google)

    def test_mac_de_otra_empresa_se_rechaza(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.post(
            reverse('televisor-list'),
            {'mac_address': 'BB:BB:BB:BB:BB:BB'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Televisor.objects.filter(mac_address='BB:BB:BB:BB:BB:BB').count(), 1)

    def test_el_error_de_mac_no_revela_la_empresa_dueña(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.post(
            reverse('televisor-list'),
            {'mac_address': 'BB:BB:BB:BB:BB:BB'},
            format='json',
        )

        self.assertNotIn('Acme', str(resp.data))

    def test_serial_de_otra_empresa_se_rechaza(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.post(
            reverse('televisor-list'),
            {'mac_address': 'CC:CC:CC:CC:CC:CC', 'serial_number': 'SN-ACME'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Televisor.objects.filter(mac_address='CC:CC:CC:CC:CC:CC').exists())

    def test_serial_repetido_ignora_mayusculas(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.post(
            reverse('televisor-list'),
            {'mac_address': 'CC:CC:CC:CC:CC:CC', 'serial_number': 'sn-acme'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_varios_televisores_pueden_quedarse_sin_serial(self):
        # El índice único del serial es condicional: el serial vacío no choca.
        self.client.force_authenticate(self.user_google)
        for mac in ('DD:DD:DD:DD:DD:DD', 'EE:EE:EE:EE:EE:EE'):
            resp = self.client.post(
                reverse('televisor-list'), {'mac_address': mac}, format='json'
            )
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class RegistrosTests(BaseTenancyTests):
    """Los registros derivados (pines, sincronizaciones) tampoco cruzan."""

    def setUp(self):
        super().setUp()
        PinCodeUsado.objects.create(
            empresa=self.acme,
            televisor=self.tv_acme,
            mac_address=self.tv_acme.mac_address,
            passcode='1111',
            pin_code='SECRETO-ACME',
        )

    def test_no_ve_los_pines_de_otra_empresa(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.get(reverse('pincodes'))

        self.assertEqual(resp.data['count'], 0)
        self.assertNotIn('SECRETO-ACME', str(resp.data))

    def test_el_pin_sobrevive_al_televisor_sin_cambiar_de_empresa(self):
        # `televisor` es SET_NULL: al borrar el equipo el pin queda huérfano. Es
        # justo por esto que PinCodeUsado lleva su propia empresa.
        self.tv_acme.delete()

        self.client.force_authenticate(self.user_google)
        resp = self.client.get(reverse('pincodes'))

        self.assertEqual(resp.data['count'], 0)
        self.assertNotIn('SECRETO-ACME', str(resp.data))

    def test_el_dueño_si_ve_su_pin(self):
        self.client.force_authenticate(self.user_acme)
        resp = self.client.get(reverse('pincodes'))

        self.assertEqual(resp.data['count'], 1)


class UsuariosTests(BaseTenancyTests):
    def test_admin_solo_ve_los_usuarios_de_su_empresa(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.get(reverse('users:usuarios'))

        correos = [u['email'] for u in resp.data['results']]
        self.assertEqual(correos, ['ana@google.com'])

    def test_admin_no_puede_editar_usuario_de_otra_empresa(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.patch(
            reverse('users:usuario-detalle', args=[self.user_acme.pk]),
            {'is_active': False},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.user_acme.refresh_from_db()
        self.assertTrue(self.user_acme.is_active)

    def test_el_superadmin_cambia_de_empresa_a_un_usuario(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.patch(
            reverse('users:usuario-detalle', args=[self.user_acme.pk]),
            {'empresa': str(self.google.pk)},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user_acme.refresh_from_db()
        self.assertEqual(self.user_acme.empresa, self.google)

    def test_un_admin_de_empresa_no_puede_mover_usuarios_de_empresa(self):
        # Ni siquiera a los suyos: moverse a sí mismo a otra empresa sería la
        # forma más directa de leer los datos del vecino.
        otro = User.objects.create_user(
            email='otro@google.com', password=CLAVE, empresa=self.google,
        )
        self.client.force_authenticate(self.user_google)
        resp = self.client.patch(
            reverse('users:usuario-detalle', args=[otro.pk]),
            {'empresa': str(self.acme.pk)},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        otro.refresh_from_db()
        self.assertEqual(otro.empresa, self.google)

    def test_el_usuario_creado_hereda_la_empresa_del_admin(self):
        self.client.force_authenticate(self.user_google)
        resp = self.client.post(
            reverse('users:usuarios'),
            {'email': 'nuevo@google.com', 'password': CLAVE, 'empresa': str(self.acme.pk)},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(email='nuevo@google.com').empresa, self.google)


class EmpresasApiTests(BaseTenancyTests):
    def test_solo_el_superadmin_gestiona_empresas(self):
        self.client.force_authenticate(self.user_google)  # admin, pero de empresa
        self.assertEqual(
            self.client.get(reverse('empresa-list')).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_el_superadmin_crea_empresas(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.post(
            reverse('empresa-list'), {'nombre': 'Nueva SAS'}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Empresa.objects.filter(nombre='Nueva SAS').exists())

    def test_no_borra_una_empresa_con_datos(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.delete(reverse('empresa-detail', args=[self.google.pk]))

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Empresa.objects.filter(pk=self.google.pk).exists())


class SuperAdminSoloLecturaTests(BaseTenancyTests):
    """El administrador general es un auditor: ve y exporta todo, pero no altera
    los datos de los televisores ni entrega pines."""

    def test_ve_los_televisores_de_todas_las_empresas(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.get(reverse('televisor-list'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 2)

    def test_puede_exportar(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.get(
            reverse('televisor-exportar-sincronizaciones')
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_no_puede_crear_televisor(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.post(
            reverse('televisor-list'),
            {'mac_address': 'FF:FF:FF:FF:FF:FF', 'empresa': str(self.google.pk)},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Televisor.objects.filter(mac_address='FF:FF:FF:FF:FF:FF').exists())

    def test_no_puede_cambiar_el_estado_de_un_televisor(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.post(
            reverse('televisor-estado', args=[self.tv_google.pk]),
            {'inhabilitar': True},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.tv_google.refresh_from_db()
        self.assertFalse(self.tv_google.inhabilitado)

    def test_no_puede_editar_ni_borrar(self):
        self.client.force_authenticate(self.superadmin)
        editar = self.client.patch(
            reverse('televisor-detail', args=[self.tv_google.pk]),
            {'numero_credito': '123'},
            format='json',
        )
        borrar = self.client.delete(
            reverse('televisor-detail', args=[self.tv_google.pk])
        )

        self.assertEqual(editar.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(borrar.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Televisor.objects.filter(pk=self.tv_google.pk).exists())

    def test_no_puede_entregar_un_pincode(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.post(
            reverse('televisor-pincode-usar', args=[self.tv_google.pk]),
            {'passcode': '0323'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_un_operador_de_empresa_si_puede_operar(self):
        # La restricción es SOLO para el admin general: el operador de empresa
        # conserva la escritura sobre lo suyo.
        operador = User.objects.create_user(
            email='op@google.com', password=CLAVE, role='operador', empresa=self.google,
        )
        self.client.force_authenticate(operador)
        resp = self.client.post(
            reverse('televisor-list'),
            {'mac_address': 'CC:CC:CC:CC:CC:CC'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class IntegracionApiKeyTests(BaseTenancyTests):
    """API de integración: por serial, con API-key, acotada a su empresa."""

    def setUp(self):
        super().setUp()
        self.api_key_google, self.clave_google = ApiKey.generar(
            empresa=self.google, nombre='ERP Google',
        )

    def _auth(self, clave):
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {clave}')

    def _url(self, serial, sufijo=''):
        return f'/api/integracion/televisores/{serial}/{sufijo}'

    def test_resuelve_el_televisor_por_serial(self):
        self._auth(self.clave_google)
        resp = self.client.get(self._url('SN-GOOGLE', ''))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['mac_address'], 'AA:AA:AA:AA:AA:AA')

    def test_solo_ve_los_televisores_de_su_empresa(self):
        self._auth(self.clave_google)
        listado = self.client.get('/api/integracion/televisores/')
        # El serial de Acme existe, pero para esta API-key no.
        ajeno = self.client.get(self._url('SN-ACME', ''))

        self.assertEqual(listado.data['count'], 1)
        self.assertEqual(ajeno.status_code, status.HTTP_404_NOT_FOUND)

    def test_sin_api_key_no_entra(self):
        resp = self.client.get(self._url('SN-GOOGLE', ''))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_key_invalida_no_entra(self):
        self._auth('deadbeef.claveinventada')
        resp = self.client.get(self._url('SN-GOOGLE', ''))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_key_revocada_no_entra(self):
        self.api_key_google.activa = False
        self.api_key_google.save(update_fields=['activa'])
        self._auth(self.clave_google)
        resp = self.client.get(self._url('SN-GOOGLE', ''))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_entra_si_la_empresa_esta_desactivada(self):
        self.google.activa = False
        self.google.save(update_fields=['activa'])
        self._auth(self.clave_google)
        resp = self.client.get(self._url('SN-GOOGLE', ''))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_puede_cambiar_estado_por_serial(self):
        # El integrador SÍ opera sobre sus televisores. Cambiar estado guarda el
        # estado local y lanza el job (la sincronización con el portal se prueba
        # aparte); acá basta con que se acepte y persista el estado local.
        self._auth(self.clave_google)
        resp = self.client.post(
            self._url('SN-GOOGLE', 'estado/'), {'inhabilitar': True}, format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.tv_google.refresh_from_db()
        self.assertTrue(self.tv_google.inhabilitado)

    def test_la_accion_por_api_key_no_rompe_la_auditoria(self):
        # El usuario sintético NO puede guardarse como FK: el job queda con
        # usuario vacío, no revienta.
        self._auth(self.clave_google)
        self.client.post(
            self._url('SN-GOOGLE', 'estado/'), {'inhabilitar': True}, format='json',
        )
        job = self.tv_google.sync_jobs.first()
        self.assertIsNotNone(job)
        self.assertIsNone(job.usuario)
        self.assertEqual(job.empresa, self.google)

    def test_el_panel_sigue_por_id_no_por_serial(self):
        # La API del panel no cambió: sigue resolviendo por PK (con JWT).
        self.client.force_authenticate(self.user_google)
        por_id = self.client.get(reverse('televisor-detail', args=[self.tv_google.pk]))
        self.assertEqual(por_id.status_code, status.HTTP_200_OK)


class ApiKeyEndurecimientoTests(BaseTenancyTests):
    """Controles opcionales: lista blanca de IPs y caducidad. Apagados por
    defecto (no cambian el uso documentado); enforced solo si se configuran."""

    def _get(self, clave, **extra):
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {clave}')
        return self.client.get('/api/integracion/televisores/', **extra)

    def test_sin_restricciones_funciona_desde_cualquier_ip(self):
        _, clave = ApiKey.generar(empresa=self.google, nombre='abierta')
        resp = self._get(clave, REMOTE_ADDR='200.1.2.3')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_ip_en_la_lista_blanca_entra(self):
        _, clave = ApiKey.generar(
            empresa=self.google, nombre='fija', ips_permitidas='190.0.0.5',
        )
        resp = self._get(clave, REMOTE_ADDR='190.0.0.5')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_ip_fuera_de_la_lista_blanca_no_entra(self):
        _, clave = ApiKey.generar(
            empresa=self.google, nombre='fija', ips_permitidas='190.0.0.5',
        )
        resp = self._get(clave, REMOTE_ADDR='190.0.0.9')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rango_cidr_en_la_lista_blanca(self):
        _, clave = ApiKey.generar(
            empresa=self.google, nombre='rango', ips_permitidas='10.0.0.0/24',
        )
        dentro = self._get(clave, REMOTE_ADDR='10.0.0.77')
        fuera = self._get(clave, REMOTE_ADDR='10.0.1.1')
        self.assertEqual(dentro.status_code, status.HTTP_200_OK)
        self.assertEqual(fuera.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_xff_falsificado_no_burla_la_lista_blanca(self):
        # El cliente manda un X-Forwarded-For inventado con la IP permitida; la
        # IP real (la última, que pondría el proxy) es la que manda.
        _, clave = ApiKey.generar(
            empresa=self.google, nombre='fija', ips_permitidas='190.0.0.5',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {clave}')
        resp = self.client.get(
            '/api/integracion/televisores/',
            HTTP_X_FORWARDED_FOR='190.0.0.5, 8.8.8.8',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_clave_expirada_no_entra(self):
        from datetime import timedelta

        from django.utils import timezone

        api_key, clave = ApiKey.generar(empresa=self.google, nombre='temporal')
        api_key.expira = timezone.now() - timedelta(minutes=1)
        api_key.save(update_fields=['expira'])
        resp = self._get(clave, REMOTE_ADDR='1.2.3.4')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_clave_con_caducidad_futura_funciona(self):
        from datetime import timedelta

        from django.utils import timezone

        api_key, clave = ApiKey.generar(empresa=self.google, nombre='vigente')
        api_key.expira = timezone.now() + timedelta(days=30)
        api_key.save(update_fields=['expira'])
        resp = self._get(clave, REMOTE_ADDR='1.2.3.4')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class EnrolarEstadoJsonTests(BaseTenancyTests):
    """Cambio de estado masivo por JSON (lo que manda un ERP): identifica cada
    televisor por su SERIAL, sin subir archivo."""

    def setUp(self):
        super().setUp()
        self.api_key, self.clave = ApiKey.generar(empresa=self.google, nombre='ERP')
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.clave}')

    def _post(self, registros):
        return self.client.post(
            '/api/integracion/televisores/enrolar-estado/',
            {'registros': registros},
            format='json',
        )

    def test_aplica_estados_por_serial(self):
        resp = self._post([{'serial_number': 'SN-GOOGLE', 'estado': 'inhabilitado'}])
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(resp.data['cambios'], 1)
        self.tv_google.refresh_from_db()
        self.assertTrue(self.tv_google.inhabilitado)

    def test_acepta_booleano_en_estado(self):
        resp = self._post([{'serial_number': 'SN-GOOGLE', 'estado': True}])
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.tv_google.refresh_from_db()
        self.assertTrue(self.tv_google.inhabilitado)

    def test_serial_con_distinta_capitalizacion_funciona(self):
        resp = self._post([{'serial_number': 'sn-google', 'estado': 'inhabilitado'}])
        self.assertEqual(resp.data['cambios'], 1)

    def test_serial_inexistente_da_error_y_no_crea(self):
        antes = Televisor.objects.count()
        resp = self._post([{'serial_number': 'NO-EXISTE', 'estado': 'habilitado'}])
        self.assertEqual(resp.data['cambios'], 0)
        self.assertEqual(resp.data['creados'], 0)
        self.assertTrue(resp.data['errores'])
        self.assertEqual(Televisor.objects.count(), antes)

    def test_serial_de_otra_empresa_no_se_toca(self):
        # SN-ACME existe, pero no en la empresa de esta API-key: no se encuentra.
        resp = self._post([{'serial_number': 'SN-ACME', 'estado': 'inhabilitado'}])
        self.assertEqual(resp.data['cambios'], 0)
        self.assertTrue(resp.data['errores'])
        self.tv_acme.refresh_from_db()
        self.assertFalse(self.tv_acme.inhabilitado)

    def test_estado_invalido_da_error_de_registro(self):
        resp = self._post([{'serial_number': 'SN-GOOGLE', 'estado': 'xyz'}])
        self.assertEqual(resp.data['cambios'], 0)
        self.assertTrue(any('estado' in e.lower() for e in resp.data['errores']))

    def test_body_sin_registros_da_400(self):
        resp = self.client.post(
            '/api/integracion/televisores/enrolar-estado/', {}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ValidacionMasivaIntegracionTests(BaseTenancyTests):
    """La validación masiva por API-key: valida SOLO los TV de la empresa y el
    resultado identifica cada equipo por serial (además de por MAC)."""

    def setUp(self):
        super().setUp()
        _, self.clave = ApiKey.generar(empresa=self.google, nombre='ERP')
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.clave}')

    def test_lanza_validacion_y_acota_a_la_empresa(self):
        resp = self.client.post('/api/integracion/televisores/validar-masivo/')
        # Google tiene 1 televisor; el de Acme no entra en el total.
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(resp.data['total'], 1)

    def test_el_item_del_resultado_incluye_el_serial(self):
        from televisores.models import BulkSyncItem, BulkSyncJob

        # Se crea el job + item directamente y se consulta el estado por la API,
        # sin correr el hilo/portal (eso es integración externa).
        job = BulkSyncJob.objects.create(
            empresa=self.google, modo=BulkSyncJob.VALIDACION, total=1,
        )
        BulkSyncItem.objects.create(
            job=job, televisor=self.tv_google,
            mac_address=self.tv_google.mac_address, inhabilitar=False,
        )
        resp = self.client.get(
            f'/api/integracion/televisores/validar-masivo/{job.pk}/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['items'][0]['serial_number'], 'SN-GOOGLE')


class ApiKeyGestionTests(BaseTenancyTests):
    """Gestión de API-keys: solo el administrador general, y la clave se ve una vez."""

    def test_superadmin_crea_una_api_key_y_ve_la_clave_una_vez(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.post(
            f'/api/empresas/{self.google.pk}/api-keys/',
            {'nombre': 'ERP Google'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('clave', resp.data)  # la clave en claro, solo aquí
        self.assertTrue(resp.data['clave'].startswith(resp.data['prefijo'] + '.'))

        # Al listar ya no aparece la clave, solo el prefijo.
        listado = self.client.get(f'/api/empresas/{self.google.pk}/api-keys/')
        self.assertEqual(len(listado.data), 1)
        self.assertNotIn('clave', listado.data[0])

    def test_un_admin_de_empresa_no_gestiona_api_keys(self):
        self.client.force_authenticate(self.user_google)  # admin, pero de empresa
        resp = self.client.get(f'/api/empresas/{self.google.pk}/api-keys/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_revocar_deja_la_clave_inservible(self):
        api_key, clave = ApiKey.generar(empresa=self.google, nombre='temporal')

        self.client.force_authenticate(self.superadmin)
        rev = self.client.post(
            f'/api/empresas/{self.google.pk}/api-keys/{api_key.pk}/revocar/'
        )
        self.assertEqual(rev.status_code, status.HTTP_200_OK)

        # Ya no autentica. Se quita la sesión forzada del superadmin para que la
        # petición dependa solo de la API-key (force_authenticate la pisaría).
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {clave}')
        resp = self.client.get('/api/integracion/televisores/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class EmpresaDesactivadaTests(BaseTenancyTests):
    def test_no_puede_iniciar_sesion(self):
        self.google.activa = False
        self.google.save()

        resp = self.client.post(
            reverse('users:token_obtain_pair'),
            {'email': 'ana@google.com', 'password': CLAVE},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_los_tokens_ya_emitidos_dejan_de_servir(self):
        # Desactivar la empresa tiene que cortar el acceso YA, no cuando expire
        # el token que el usuario tenga en la mano.
        login = self.client.post(
            reverse('users:token_obtain_pair'),
            {'email': 'ana@google.com', 'password': CLAVE},
            format='json',
        )
        access = login.data['access']

        self.google.activa = False
        self.google.save()

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(
            self.client.get(reverse('users:me')).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
