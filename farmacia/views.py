from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from rest_framework.permissions import AllowAny
from .permissions import EsGestor, EsInstitucion
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import (
    Category,
    Insumo,
    Carro,
    ItemCarro,
    Solicitud,
    ItemSolicitud,
    Perfil,
)

from .serializers import (
    CategorySerializer,
    InsumoSerializer,
    CarroSerializer,
    ItemCarroSerializer,
    SolicitudSerializer,
    ItemSolicitudSerializer,
    PerfilSerializer,
    CustomTokenObtainPairSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Permite consultar y administrar las categorías de los insumos.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class InsumoViewSet(viewsets.ModelViewSet):
    """
    Permite consultar los insumos públicamente.
    Solo los gestores pueden crear, modificar o eliminar insumos.
    """

    queryset = Insumo.objects.all()
    serializer_class = InsumoSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]

        return [EsGestor()]


class CarroViewSet(viewsets.ModelViewSet):
    """
    Permite a una institución administrar únicamente su propio carrito.
    """

    queryset = Carro.objects.all()
    serializer_class = CarroSerializer
    permission_classes = [EsInstitucion]

    def get_queryset(self):
        return Carro.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ItemCarroViewSet(viewsets.ModelViewSet):
    """
    Permite a una institución administrar los productos de su propio carrito.
    """

    queryset = ItemCarro.objects.all()
    serializer_class = ItemCarroSerializer
    permission_classes = [EsInstitucion]

    def get_queryset(self):
        return ItemCarro.objects.filter(
            carro__user=self.request.user
        )

    def perform_create(self, serializer):
        carro, created = Carro.objects.get_or_create(
            user=self.request.user
        )

        serializer.save(carro=carro)


class SolicitudViewSet(viewsets.ModelViewSet):
    """
    Permite a una institución consultar únicamente sus propias solicitudes.
    """

    queryset = Solicitud.objects.all()
    serializer_class = SolicitudSerializer
    permission_classes = [EsInstitucion]

    def get_queryset(self):
        return Solicitud.objects.filter(
            user=self.request.user
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="confirmar"
    )
    def confirmar(self, request):
        """
        Convierte el carrito persistente en una solicitud pagada.

        Primero verifica que el carrito tenga productos y que exista
        stock suficiente. Si todo está correcto, crea la solicitud,
        guarda sus productos, descuenta el stock y vacía el carrito.
        """

        with transaction.atomic():

            carro, created = Carro.objects.get_or_create(
                user=request.user
            )

            items = list(
                carro.items.select_related("insumo")
            )

            if not items:
                return Response(
                    {
                        "error": "El carrito está vacío."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Bloqueamos los insumos mientras se realiza la operación.
            insumos = {}

            for item in items:
                insumo = (
                    Insumo.objects
                    .select_for_update()
                    .get(id=item.insumo.id)
                )

                if insumo.stock < item.quantity:
                    return Response(
                        {
                            "error": (
                                f"Stock insuficiente para "
                                f"{insumo.commercial_name}."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                insumos[item.id] = insumo

            # Creamos la solicitud histórica.
            solicitud = Solicitud.objects.create(
                user=request.user,
                estado=Solicitud.Estado.PAGADO
            )

            # Creamos los productos de la solicitud
            # y descontamos el stock.
            for item in items:

                insumo = insumos[item.id]

                ItemSolicitud.objects.create(
                    solicitud=solicitud,
                    insumo=insumo,
                    quantity=item.quantity,
                    unit_price=insumo.unit_price_per_box
                )

                insumo.stock -= item.quantity
                insumo.save(update_fields=["stock"])

            # El carrito queda vacío después de confirmar.
            carro.items.all().delete()

        return Response(
            {
                "mensaje": "Solicitud confirmada correctamente.",
                "solicitud_id": solicitud.id,
                "estado": solicitud.estado
            },
            status=status.HTTP_201_CREATED
        )


class ItemSolicitudViewSet(viewsets.ModelViewSet):
    """
    Permite consultar y administrar los productos de las solicitudes.
    """

    queryset = ItemSolicitud.objects.all()
    serializer_class = ItemSolicitudSerializer


class PerfilViewSet(viewsets.ModelViewSet):
    """
    Permite consultar y administrar los perfiles de usuario.
    """

    queryset = Perfil.objects.all()
    serializer_class = PerfilSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para generar JWT incluyendo el rol del usuario.
    """

    serializer_class = CustomTokenObtainPairSerializer