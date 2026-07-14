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

from empresas.models import Empresa
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
