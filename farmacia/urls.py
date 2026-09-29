from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()

router.register(r'categories', views.CategoryViewSet)
router.register(r'insumos', views.InsumoViewSet)
router.register(r'carros', views.CarroViewSet)
router.register(r'items-carro', views.ItemCarroViewSet)
router.register(r'solicitudes', views.SolicitudViewSet)
router.register(r'items-solicitud', views.ItemSolicitudViewSet)
router.register(r'perfiles', views.PerfilViewSet)


urlpatterns = router.urls