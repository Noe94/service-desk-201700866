from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.rol != "ADMIN":
            raise PermissionDenied(
                "No tiene permisos para realizar esta operación."
            )

        return view_func(request, *args, **kwargs)

    return wrapper
