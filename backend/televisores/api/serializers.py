from rest_framework import serializers

from televisores.models import (
    BulkSyncItem,
    BulkSyncJob,
    PinCodeUsado,
    SyncJob,
    Televisor,
)


# La MAC y el serial son únicos en todo el sistema, no dentro de la empresa. El
# mensaje de error NO dice de qué empresa es el equipo: eso convertiría el
# formulario en un buscador de datos ajenos. Solo dice que ya está tomado.
YA_REGISTRADO = (
    'Este {campo} ya está registrado en el sistema. Si el equipo es de tu '
    'empresa y no lo ves, contacta al administrador.'
)


class TelevisorSerializer(serializers.ModelSerializer):
    empresa = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Televisor
        fields = [
            'id',
            'empresa',
            'mac_address',
            'serial_number',
            'numero_credito',
            'inhabilitado',
            'eui64',
            'created_at',
        ]
        # El estado y las fechas no se editan desde el CRUD del televisor. La
        # empresa tampoco: la fija la vista con la cuenta que crea el registro.
        read_only_fields = ['id', 'empresa', 'inhabilitado', 'created_at']
        extra_kwargs = {
            'eui64': {'required': False},
        }

    def validate_mac_address(self, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError('La dirección MAC es obligatoria.')
        # Unicidad global (ignorando el propio registro al editar). Ojo: se
        # consulta sobre TODOS los televisores, no sobre los de la empresa, para
        # que la MAC de otra empresa también choque.
        qs = Televisor.objects.filter(mac_address=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(YA_REGISTRADO.format(campo='MAC'))
        return value

    def validate_serial_number(self, value: str) -> str:
        value = (value or '').strip()
        if not value:
            return value
        # `iexact` es más estricto que el índice único de la base de datos (que
        # distingue mayúsculas): así 'abc123' y 'ABC123' tampoco conviven, que es
        # lo que espera quien lee un serial de una etiqueta.
        qs = Televisor.objects.filter(serial_number__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(YA_REGISTRADO.format(campo='serial'))
        return value


class PinCodeUsadoSerializer(serializers.ModelSerializer):
    # El serial vive en el televisor asociado (SET_NULL): si el equipo se borró
    # o el pin no quedó ligado, sale vacío.
    serial_number = serializers.SerializerMethodField()

    class Meta:
        model = PinCodeUsado
        fields = ['id', 'mac_address', 'serial_number', 'passcode', 'pin_code', 'creado']

    def get_serial_number(self, obj) -> str:
        return obj.televisor.serial_number if obj.televisor_id else ''


class SyncJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncJob
        fields = [
            'id',
            'inhabilitar',
            'estado',
            'porcentaje',
            'error',
            'creado',
            'terminado_en',
        ]


class BulkSyncItemSerializer(serializers.ModelSerializer):
    # El serial sale del televisor asociado (la MAC va denormalizada en el item,
    # el serial no). Con esto el resultado de un lote —validación o enrolar
    # estado— identifica cada equipo también por serial, que es como lo conoce la
    # integración. Si el televisor se borró (SET_NULL), sale vacío.
    serial_number = serializers.SerializerMethodField()

    class Meta:
        model = BulkSyncItem
        fields = [
            'id',
            'mac_address',
            'serial_number',
            'inhabilitar',
            'estado',
            'mensaje',
            'remoto_inhabilitado',
            'local_inhabilitado',
            'coincide',
        ]

    def get_serial_number(self, obj) -> str:
        return obj.televisor.serial_number if obj.televisor_id else ''


class BulkSyncJobSerializer(serializers.ModelSerializer):
    porcentaje = serializers.IntegerField(read_only=True)
    finalizado = serializers.BooleanField(read_only=True)
    items = BulkSyncItemSerializer(many=True, read_only=True)

    class Meta:
        model = BulkSyncJob
        fields = [
            'id',
            'modo',
            'estado',
            'total',
            'procesados',
            'ok_count',
            'error_count',
            'porcentaje',
            'finalizado',
            'creados',
            'actualizados',
            'errores_import',
            'items',
            'creado',
            'terminado_en',
        ]
