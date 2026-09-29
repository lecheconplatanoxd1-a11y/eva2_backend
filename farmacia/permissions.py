from rest_framework.permissions import BasePermission


class EsInstitucion(BasePermission):
    """
    Permite el acceso únicamente a usuarios con rol INSTITUCION.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "perfil")
            and request.user.perfil.rol == "INSTITUCION"
        )


class EsGestor(BasePermission):
    """
    Permite el acceso únicamente a usuarios con rol GESTOR.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "perfil")
            and request.user.perfil.rol == "GESTOR"
        )


class EsInstitucionOGestor(BasePermission):
    """
    Permite el acceso a usuarios autenticados con rol válido.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "perfil")
            and request.user.perfil.rol in ["INSTITUCION", "GESTOR"]
        )