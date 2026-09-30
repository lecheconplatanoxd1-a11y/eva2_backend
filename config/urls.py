
from django.contrib import admin
from django.urls import path, include, re_path

from farmacia.views import home_view, insumos_view
from farmacia.views import (
    home_view,
    insumos_view,
    carrito_view,
    login_view,
    agregar_carrito_view,
    actualizar_carrito_view,
    eliminar_carrito_view,
    confirmar_carrito_view,
    pago_view,
    logout_view,
    registro_view,
    gestor_view,
    crear_insumo_view,
    editar_insumo_view,
    eliminar_insumo_view,
    gestor_cambiar_estado_view,
    mis_solicitudes_web_view
    
)

from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView
)

from farmacia.views import CustomTokenObtainPairView


urlpatterns = [

    path('', home_view, name='home'),
    path('insumos/', insumos_view, name='insumos'),
    path('carrito/', carrito_view, name='carrito'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('registro/', registro_view, name='registro'),
    path('gestor/', gestor_view, name='gestor'),
    

    path(
    'gestor/nuevo/',
    crear_insumo_view,
    name='crear-insumo'
),
    path(
    'gestor/editar/<int:insumo_id>/',
    editar_insumo_view,
    name='editar-insumo'
),

    path(
    'gestor/eliminar/<int:insumo_id>/',
    eliminar_insumo_view,
    name='eliminar-insumo'
),

    path(
    'gestor/solicitud/<int:solicitud_id>/estado/',
    gestor_cambiar_estado_view,
    name='gestor-cambiar-estado'
),

    re_path(
    r'^mis-solicitudes/?$',
    mis_solicitudes_web_view,
    name='mis-solicitudes-web'
),

    path(
    'carrito/agregar/<int:insumo_id>/',
    agregar_carrito_view,
    name='agregar-carrito'
    ),
    path(
    'carrito/actualizar/<int:item_id>/',
    actualizar_carrito_view,
    name='actualizar-carrito'
    ),
    path(
    'carrito/eliminar/<int:item_id>/',
    eliminar_carrito_view,
    name='eliminar-carrito'
    ),
    path(
    'carrito/confirmar/',
    confirmar_carrito_view,
    name='confirmar-carrito'
    ),
    path(
    'pago/<int:solicitud_id>/',
    pago_view,
    name='pago'
),


    path('admin/', admin.site.urls),
    path('api/', include('farmacia.urls')),

    path(
        'api/token/',
        CustomTokenObtainPairView.as_view(),
        name='token_obtain_pair'
    ),

    path(
        'api/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),

    path(
        'api/schema/',
        SpectacularAPIView.as_view(),
        name='schema'
    ),

    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
]

handler404 = 'farmacia.views.error_404_view'