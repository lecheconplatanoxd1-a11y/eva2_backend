from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.db import transaction

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import EsGestor, EsInstitucion

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
    Permite consultar las categorías públicamente.
    Solo los gestores pueden crear, modificar o eliminar categorías.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]

        return [EsGestor()]


class InsumoViewSet(viewsets.ModelViewSet):
    """
    Permite consultar los insumos públicamente.
    Solo los gestores pueden crear, modificar o eliminar insumos.
    """

    queryset = Insumo.objects.all()
    serializer_class = InsumoSerializer


    filterset_fields = [
        "tipo",
        "category",
        "stock",
    ]

    search_fields = [
        "commercial_name",
        "active_ingredient",
        "lot",
    ]

    ordering_fields = [
        "commercial_name",
        "unit_price_per_box",
        "stock",
        "expiration_date",
    ]

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
        return Carro.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )


class ItemCarroViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    Permite a una institución administrar los productos
    de su propio carrito.
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

        serializer.save(
            carro=carro
        )


class SolicitudViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Permite a una institución consultar únicamente
    sus propias solicitudes.
    """

    queryset = Solicitud.objects.all()
    serializer_class = SolicitudSerializer
    filterset_fields = [
        "estado",
    ]
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
        Convierte el carrito persistente en una solicitud
        pendiente de pago.

        En este momento no se descuenta stock porque el usuario
        todavía no ha realizado el pago.
        """

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

        # Creamos la solicitud como PENDIENTE.
        solicitud = Solicitud.objects.create(
            user=request.user,
            estado=Solicitud.Estado.PENDIENTE
        )

        # Guardamos los productos de la solicitud.
        # El stock todavía no se modifica.
        for item in items:

            ItemSolicitud.objects.create(
                solicitud=solicitud,
                insumo=item.insumo,
                quantity=item.quantity,
                unit_price=item.insumo.unit_price_per_box
            )

        # Vaciamos el carrito.
        carro.items.all().delete()

        return Response(
            {
                "mensaje": "Solicitud creada. Pendiente de pago.",
                "solicitud_id": solicitud.id,
                "estado": solicitud.estado
            },
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["patch"],
        url_path="estado",
        permission_classes=[EsGestor]
    )
    def cambiar_estado(self, request, pk=None):
        """
        Permite al gestor cambiar el estado de una solicitud.

        Si la solicitud pasa a CANCELADO y estaba PAGADO,
        se devuelve al stock la cantidad de cada producto.
        """

        nuevo_estado = request.data.get("estado")

        estados_validos = [
            Solicitud.Estado.PENDIENTE,
            Solicitud.Estado.PAGADO,
            Solicitud.Estado.ENTREGADO,
            Solicitud.Estado.CANCELADO,
        ]

        if nuevo_estado not in estados_validos:
            return Response(
                {
                    "error": "Estado no válido."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            solicitud = (
                Solicitud.objects
                .select_for_update()
                .get(pk=pk)
            )

            estado_anterior = solicitud.estado

            # Evita devolver stock dos veces
            # si la solicitud ya estaba cancelada.
            if (
                nuevo_estado == Solicitud.Estado.CANCELADO
                and estado_anterior != Solicitud.Estado.CANCELADO
            ):

                if estado_anterior == Solicitud.Estado.PAGADO:

                    for item in solicitud.items.select_related("insumo"):

                        insumo = (
                            Insumo.objects
                            .select_for_update()
                            .get(pk=item.insumo.id)
                        )

                        insumo.stock += item.quantity

                        insumo.save(
                            update_fields=["stock"]
                        )

            solicitud.estado = nuevo_estado

            solicitud.save(
                update_fields=["estado"]
            )

        return Response(
            {
                "mensaje": "Estado actualizado correctamente.",
                "solicitud_id": solicitud.id,
                "estado_anterior": estado_anterior,
                "estado_actual": solicitud.estado
            },
            status=status.HTTP_200_OK
        )


@login_required
def gestor_cambiar_estado_view(request, solicitud_id):
    """
Permite al gestor cambiar el estado de una solicitud
desde la interfaz web.

    ```
Si una solicitud PAGADA pasa a CANCELADA,
se devuelve el stock de sus productos.
    """

    if not hasattr(request.user, "perfil"):
        return redirect("/")

    if request.user.perfil.rol != Perfil.Rol.GESTOR:
        return redirect("/")

    if request.method != "POST":
        return redirect("/gestor/")

    nuevo_estado = request.POST.get("estado")

    estados_validos = [
        Solicitud.Estado.PENDIENTE,
        Solicitud.Estado.PAGADO,
        Solicitud.Estado.ENTREGADO,
        Solicitud.Estado.CANCELADO,
]

    if nuevo_estado not in estados_validos:
        return redirect("/gestor/")

    with transaction.atomic():

        solicitud = (
        Solicitud.objects
        .select_for_update()
        .get(pk=solicitud_id)
        )

        estado_anterior = solicitud.estado

        if (
        nuevo_estado == Solicitud.Estado.CANCELADO
        and estado_anterior != Solicitud.Estado.CANCELADO
        ):

            if estado_anterior == Solicitud.Estado.PAGADO:

                for item in solicitud.items.select_related("insumo"):

                    insumo = (
                    Insumo.objects
                    .select_for_update()
                    .get(pk=item.insumo.id)
                )

                insumo.stock += item.quantity

                insumo.save(
                    update_fields=["stock"]
                )

        solicitud.estado = nuevo_estado

        solicitud.save(
        update_fields=["estado"]
    )

        return redirect("/gestor/")




class ItemSolicitudViewSet(viewsets.ModelViewSet):
    """
    Permite consultar y administrar los productos
    de las solicitudes.
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
    Vista personalizada para generar JWT incluyendo
    el rol del usuario.
    """

    serializer_class = CustomTokenObtainPairSerializer


@api_view(["GET"])
@permission_classes([EsInstitucion])
def mis_solicitudes_view(request):
    """
    Devuelve las solicitudes pertenecientes
    al usuario autenticado.
    """

    solicitudes = Solicitud.objects.filter(
        user=request.user
    )

    serializer = SolicitudSerializer(
        solicitudes,
        many=True
    )

    return Response(serializer.data)


def home_view(request):
    """
    Muestra la página principal del sistema
    mediante una plantilla HTML.
    """

    return render(
        request,
        "farmacia/home.html"
    )


@login_required
def mis_solicitudes_web_view(request):
    """
Muestra todas las solicitudes realizadas
por la institución que inició sesión.
    """


    if not hasattr(request.user, "perfil"):
        return redirect("/")

    if request.user.perfil.rol != Perfil.Rol.INSTITUCION:
        return redirect("/")

    solicitudes = (
    Solicitud.objects
    .filter(user=request.user)
    .prefetch_related("items__insumo")
    .order_by("-created_at")
)

    datos_solicitudes = []

    for solicitud in solicitudes:

        items = []
        total = 0

        for item in solicitud.items.all():

            subtotal = item.quantity * item.unit_price

            items.append({
                "insumo": item.insumo,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": subtotal,
            })

            total += subtotal

        datos_solicitudes.append({
            "solicitud": solicitud,
            "items": items,
            "total": total,
    })

    print("SOLICITUDES ENVIADAS AL TEMPLATE:", len(datos_solicitudes))

    for dato in datos_solicitudes:
        print("ENVIANDO:", dato["solicitud"].id)

    return render(
        request,
        "farmacia/mis_solicitudes.html",
        {
            "solicitudes": datos_solicitudes,
        }
    )





def insumos_view(request):
    """
    Obtiene los insumos registrados en la base de datos
    y los envía a la plantilla del catálogo.
    """

    insumos = Insumo.objects.all()

    return render(
        request,
        "farmacia/insumos.html",
        {
            "insumos": insumos
        }
    )


@login_required
def carrito_view(request):
    """
    Muestra el carrito persistente del usuario autenticado.
    Si el usuario todavía no tiene carrito,
    se crea automáticamente.
    """

    carro, created = Carro.objects.get_or_create(
        user=request.user
    )

    items = carro.items.select_related("insumo")

    return render(
        request,
        "farmacia/carrito.html",
        {
            "carro": carro,
            "items": items
        }
    )

def logout_view(request):
    logout(request)
    return redirect("/")


def registro_view(request):
    """
    Permite registrar una nueva institución.

    Todo usuario registrado desde esta página recibe
    automáticamente el rol INSTITUCION.
    """

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            return render(
                request,
                "farmacia/registro.html",
                {
                    "error": "Debes completar todos los campos."
                }
            )

        from django.contrib.auth.models import User

        if User.objects.filter(username=username).exists():
            return render(
                request,
                "farmacia/registro.html",
                {
                    "error": "Ese usuario ya existe."
                }
            )

        user = User.objects.create_user(
            username=username,
            password=password
        )

        Perfil.objects.create(
            user=user,
            rol=Perfil.Rol.INSTITUCION
        )

        login(request, user)

        return redirect("/")

    return render(
        request,
        "farmacia/registro.html"
    )


def login_view(request):
    """
    Permite iniciar sesión utilizando un usuario
    registrado en Django.
    """

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            return redirect("/")

        return render(
            request,
            "farmacia/login.html",
            {
                "error": "Usuario o contraseña incorrectos."
            }
        )

    return render(
        request,
        "farmacia/login.html"
    )


@login_required
def agregar_carrito_view(request, insumo_id):
    """
    Agrega un insumo al carrito persistente del usuario.

    El stock no se modifica en este momento.
    """

    if request.method != "POST":
        return redirect("/insumos/")

    insumo = Insumo.objects.get(
        id=insumo_id
    )

    carro, created = Carro.objects.get_or_create(
        user=request.user
    )

    item, created = ItemCarro.objects.get_or_create(
        carro=carro,
        insumo=insumo,
        defaults={
            "quantity": 1
        }
    )

    if not created:

        item.quantity += 1

        item.save(
            update_fields=["quantity"]
        )

    return redirect("/carrito/")


@login_required
def actualizar_carrito_view(request, item_id):
    """
    Actualiza la cantidad de un producto del carrito.

    El stock del insumo no se modifica.
    """

    if request.method != "POST":
        return redirect("/carrito/")

    item = ItemCarro.objects.get(
        id=item_id,
        carro__user=request.user
    )

    accion = request.POST.get("accion")
    cantidad = request.POST.get("quantity")

    if accion == "sumar":

        item.quantity += 1

    elif accion == "restar":

        item.quantity -= 1

        if item.quantity < 1:
            item.quantity = 1

    elif cantidad:

        try:

            cantidad = int(cantidad)

            if cantidad >= 1:
                item.quantity = cantidad

        except ValueError:
            pass

    item.save(
        update_fields=["quantity"]
    )

    return redirect("/carrito/")


@login_required
def eliminar_carrito_view(request, item_id):
    """
    Elimina completamente un producto del carrito.

    El stock del insumo no se modifica.
    """

    if request.method == "POST":

        item = ItemCarro.objects.get(
            id=item_id,
            carro__user=request.user
        )

        item.delete()

    return redirect("/carrito/")


@login_required
def confirmar_carrito_view(request):
    """
    Convierte el carrito en una solicitud pendiente de pago.

    El stock no se modifica en este momento.
    El descuento se realizará solamente cuando
    se procese el pago.
    """

    if request.method != "POST":
        return redirect("/carrito/")

    carro, created = Carro.objects.get_or_create(
        user=request.user
    )

    items = list(
        carro.items.select_related("insumo")
    )

    if not items:
        return redirect("/carrito/")

    # Creamos la solicitud como PENDIENTE.
    solicitud = Solicitud.objects.create(
        user=request.user,
        estado=Solicitud.Estado.PENDIENTE
    )

    # Guardamos los productos de la solicitud.
    # El stock todavía no se modifica.
    for item in items:

        ItemSolicitud.objects.create(
            solicitud=solicitud,
            insumo=item.insumo,
            quantity=item.quantity,
            unit_price=item.insumo.unit_price_per_box
        )

    # Vaciamos el carrito.
    carro.items.all().delete()

    # Enviamos al usuario a la pantalla de pago.
    return redirect(
        f"/pago/{solicitud.id}/"
    )


@login_required
def pago_view(request, solicitud_id):
    """
    Procesa el pago de una solicitud pendiente.

    El stock solamente se descuenta cuando el usuario
    selecciona un método de pago y confirma el pago.
    """

    solicitud = Solicitud.objects.get(
        id=solicitud_id,
        user=request.user
    )

    # Una solicitud que ya fue pagada no puede pagarse nuevamente.
    if solicitud.estado != Solicitud.Estado.PENDIENTE:

        return redirect("/")


    if request.method == "POST":

        metodo_pago = request.POST.get(
            "metodo_pago"
        )

        metodos_validos = [
            Solicitud.MetodoPago.TRANSFERENCIA,
            Solicitud.MetodoPago.TARJETA,
            Solicitud.MetodoPago.ORDEN_COMPRA,
        ]

        if metodo_pago not in metodos_validos:

            return render(
                request,
                "farmacia/pago.html",
                {
                    "solicitud": solicitud,
                    "error": "Debes seleccionar un método de pago."
                }
            )

        with transaction.atomic():

            # Primero verificamos que exista stock suficiente.
            for item in solicitud.items.select_related("insumo"):

                insumo = (
                    Insumo.objects
                    .select_for_update()
                    .get(pk=item.insumo.id)
                )

                if insumo.stock < item.quantity:

                    return render(
                        request,
                        "farmacia/pago.html",
                        {
                            "solicitud": solicitud,
                            "error": (
                                f"Stock insuficiente para "
                                f"{insumo.commercial_name}."
                            )
                        }
                    )

            # Una vez validado el stock,
            # lo descontamos por cada producto.
            for item in solicitud.items.select_related("insumo"):

                insumo = (
                    Insumo.objects
                    .select_for_update()
                    .get(pk=item.insumo.id)
                )

                insumo.stock -= item.quantity

                insumo.save(
                    update_fields=["stock"]
                )

            # Finalmente marcamos la solicitud como PAGADA.
            solicitud.estado = Solicitud.Estado.PAGADO

            solicitud.metodo_pago = metodo_pago

            solicitud.save(
                update_fields=[
                    "estado",
                    "metodo_pago"
                ]
            )

        return render(
            request,
            "farmacia/confirmacion.html",
            {
                "solicitud": solicitud
            }
        )

    return render(
        request,
        "farmacia/pago.html",
        {
            "solicitud": solicitud
        }
    )


@login_required
def gestor_view(request):
    """
Muestra el panel de gestión de insumos y solicitudes.

    ```
Solo los usuarios con rol GESTOR pueden acceder.
    """

    if not hasattr(request.user, "perfil"):
        return redirect("/")

    if request.user.perfil.rol != Perfil.Rol.GESTOR:
        return redirect("/")

    insumos = Insumo.objects.select_related("category").all()

    solicitudes = Solicitud.objects.select_related("user").prefetch_related(
        "items__insumo"
    ).order_by("-created_at")

    return render(
    request,
    "farmacia/gestor.html",
    {
        "insumos": insumos,
        "solicitudes": solicitudes,
        "estados_solicitud": Solicitud.Estado.choices
    }
)




@login_required
def crear_insumo_view(request):
    """
    Permite al gestor crear un nuevo insumo desde la interfaz web.
    """

    if not hasattr(request.user, "perfil"):
        return redirect("/")

    if request.user.perfil.rol != Perfil.Rol.GESTOR:
        return redirect("/")

    categories = Category.objects.all()

    if request.method == "POST":
        commercial_name = request.POST.get("commercial_name")
        active_ingredient = request.POST.get("active_ingredient")
        lot = request.POST.get("lot")
        expiration_date = request.POST.get("expiration_date")
        unit_price_per_box = request.POST.get("unit_price_per_box")
        stock = request.POST.get("stock")
        tipo = request.POST.get("tipo")
        category_id = request.POST.get("category")

        Insumo.objects.create(
            commercial_name=commercial_name,
            active_ingredient=active_ingredient,
            lot=lot,
            expiration_date=expiration_date,
            unit_price_per_box=unit_price_per_box,
            stock=stock,
            tipo=tipo,
            category_id=category_id
        )

        return redirect("/gestor/")

    return render(
        request,
        "farmacia/crear_insumo.html",
        {
            "categories": categories,
            "tipos": Insumo.TipoInsumo.choices
        }
    )


@login_required
def editar_insumo_view(request, insumo_id):
    """
Permite al gestor editar un insumo existente.
    """

    if not hasattr(request.user, "perfil"):
        return redirect("/")

    if request.user.perfil.rol != Perfil.Rol.GESTOR:
        return redirect("/")

    insumo = Insumo.objects.get(id=insumo_id)
    categories = Category.objects.all()

    if request.method == "POST":

        insumo.commercial_name = request.POST.get("commercial_name")
        insumo.active_ingredient = request.POST.get("active_ingredient")
        insumo.lot = request.POST.get("lot")
        insumo.expiration_date = request.POST.get("expiration_date")
        insumo.unit_price_per_box = request.POST.get("unit_price_per_box")
        insumo.stock = request.POST.get("stock")
        insumo.tipo = request.POST.get("tipo")
        insumo.category_id = request.POST.get("category")

        insumo.save()

        return redirect("/gestor/")

    return render(
    request,
    "farmacia/editar_insumo.html",
    {
        "insumo": insumo,
        "categories": categories,
        "tipos": Insumo.TipoInsumo.choices
    }
)


@login_required
def eliminar_insumo_view(request, insumo_id):
    """
Permite al gestor eliminar un insumo existente.
    """


    if not hasattr(request.user, "perfil"):
        return redirect("/")

    if request.user.perfil.rol != Perfil.Rol.GESTOR:
        return redirect("/")

    insumo = Insumo.objects.get(id=insumo_id)

    if request.method == "POST":
        insumo.delete()

    return redirect("/gestor/")


def error_404_view(request, exception):
    """
    Muestra una página personalizada cuando
    el usuario intenta acceder a una URL inexistente.
    """

    return render(
        request,
        "farmacia/404.html",
        status=404
    )