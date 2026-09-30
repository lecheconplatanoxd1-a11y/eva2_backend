from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import (
    Category,
    Insumo,
    Carro,
    ItemCarro,
    Solicitud,
    ItemSolicitud,
    Perfil,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class InsumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insumo
        fields = "__all__"


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = "__all__"


class ItemCarroSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCarro
        fields = "__all__"
        read_only_fields = ["carro"]


class CarroSerializer(serializers.ModelSerializer):
    items = ItemCarroSerializer(many=True, read_only=True)

    class Meta:
        model = Carro
        fields = "__all__"


class ItemSolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemSolicitud
        fields = "__all__"


class SolicitudSerializer(serializers.ModelSerializer):
    items = ItemSolicitudSerializer(many=True, read_only=True)

    class Meta:
        model = Solicitud
        fields = "__all__"


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Agrega el rol del usuario dentro del token JWT.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["rol"] = user.perfil.rol

        return token