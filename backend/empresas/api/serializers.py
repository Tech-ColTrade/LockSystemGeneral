from rest_framework import serializers

from empresas.models import Empresa


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
