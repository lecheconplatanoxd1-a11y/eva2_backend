from django.db import models


class Category(models.Model):
    """
    Representa las categorías de los insumos médicos
    disponibles en la farmacia.
    """

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Insumo(models.Model):
    """
    Representa un insumo médico disponible para las instituciones.
    """

    class TipoInsumo(models.TextChoices):
        MATERIAL_QUIRURGICO = "MATERIAL", "Material Quirúrgico"
        MEDICAMENTO = "MEDICAMENTO", "Medicamento"
        EQUIPAMIENTO = "EQUIPAMIENTO", "Equipamiento"

    commercial_name = models.CharField(max_length=150)
    active_ingredient = models.CharField(max_length=150, blank=True)
    lot = models.CharField(max_length=100)
    expiration_date = models.DateField()
    unit_price_per_box = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    tipo = models.CharField(
        max_length=20,
        choices=TipoInsumo.choices
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="insumos"
    )

    def __str__(self):
        return self.commercial_name


class Carro(models.Model):
    """
    Carrito persistente asociado a un usuario.
    Cada usuario puede tener un solo carrito.
    """

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="carro"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carro de {self.user.username}"


class ItemCarro(models.Model):
    """
    Representa un insumo y su cantidad dentro del carrito.
    """

    carro = models.ForeignKey(
        Carro,
        on_delete=models.CASCADE,
        related_name="items"
    )

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="items_carro"
    )

    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.insumo.commercial_name} x {self.quantity}"


class Solicitud(models.Model):
    """
    Representa una solicitud de abastecimiento realizada por una institución.
    Se conserva como historial de la compra.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    class MetodoPago(models.TextChoices):
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia bancaria"
        TARJETA = "TARJETA", "Tarjeta de crédito/débito"
        ORDEN_COMPRA = "ORDEN_COMPRA", "Orden de compra institucional"

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="solicitudes"
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.choices,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solicitud #{self.id} - {self.estado}"


class ItemSolicitud(models.Model):
    """
    Representa cada insumo incluido en una solicitud.
    Guarda el precio del producto en el momento de la compra.
    """

    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="items"
    )

    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name="items_solicitud"
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.insumo.commercial_name} x {self.quantity}"


class Perfil(models.Model):
    """
    Extiende el usuario de Django para indicar su rol dentro del sistema.
    """

    class Rol(models.TextChoices):
        INSTITUCION = "INSTITUCION", "Institución"
        GESTOR = "GESTOR", "Gestor"

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="perfil"
    )

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.INSTITUCION
    )

    def __str__(self):
        return f"{self.user.username} - {self.rol}"
