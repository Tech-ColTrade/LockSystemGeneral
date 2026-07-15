from rest_framework import serializers

from empresas.models import ApiKey, Empresa


class EmpresaSerializer(serializers.ModelSerializer):
    """Empresa + cuántos usuarios y televisores tiene (los anota la vista)."""

    usuarios = serializers.IntegerField(source='usuarios_count', read_only=True)
    televisores = serializers.IntegerField(source='televisores_count', read_only=True)

    class Meta:
        model = Empresa
        fields = ['id', 'nombre', 'nit', 'activa', 'creado', 'usuarios', 'televisores']
        read_only_fields = ['id', 'creado']

    def validate_nombre(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('El nombre es obligatorio.')
        qs = Empresa.objects.filter(nombre__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe una empresa con este nombre.')
        return value


class EmpresaBreveSerializer(serializers.ModelSerializer):
    """Empresa tal como se anida en el perfil del usuario."""

    class Meta:
        model = Empresa
        fields = ['id', 'nombre']
        read_only_fields = fields


class ApiKeySerializer(serializers.ModelSerializer):
    """API-key SIN el secreto: es lo que se lista. La clave en claro solo se ve
    una vez, en la respuesta de creación (ver ApiKeyCreadaSerializer)."""

    class Meta:
        model = ApiKey
        fields = [
            'id', 'nombre', 'prefijo', 'activa',
            'ips_permitidas', 'expira',
            'creada', 'ultimo_uso',
        ]
        read_only_fields = fields


class ApiKeyCreadaSerializer(serializers.Serializer):
    """Respuesta de creación: incluye la clave en claro UNA sola vez."""

    id = serializers.UUIDField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    prefijo = serializers.CharField(read_only=True)
    clave = serializers.CharField(read_only=True)
