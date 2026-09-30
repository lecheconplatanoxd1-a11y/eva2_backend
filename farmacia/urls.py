from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()

router.register(r'categories', views.CategoryViewSet)
router.register(r'insumos', views.InsumoViewSet)

router.register(
    r'carro-insumos',
    views.ItemCarroViewSet,
    basename='carro-insumos'
)

router.register(r'solicitudes', views.SolicitudViewSet)


urlpatterns = [
    path(
        'mis-solicitudes/',
        views.mis_solicitudes_view,
        name='mis-solicitudes'
    ),
] + router.urls