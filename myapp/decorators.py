# decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def role_required(allowed_roles):
    """
    Decorador que requiere que el usuario tenga uno de los roles especificados.
    
    Uso:
    @role_required(['admin', 'profesor'])
    def mi_vista(request):
        pass
    
    Args:
        allowed_roles (list): Lista de roles permitidos
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Verificar que el usuario esté autenticado
            if not request.user.is_authenticated:
                return redirect('login')
            
            user_role = getattr(request.user, 'role', None)
            
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                # Solo agregar mensaje si el usuario está autenticado
                if request.user.is_authenticated:
                    # Determinar mensaje según el rol
                    if user_role == 'estudiante':
                        message = 'Los estudiantes no tienen acceso a esta sección.'
                    elif user_role in ['profesor', 'tutor']:
                        message = 'Los profesores no tienen acceso a esta sección administrativa.'
                    else:
                        message = 'No tienes permisos para acceder a esta sección.'
                    
                    messages.error(request, message)
                    
                    # Todos redirigen a welcome (página de inicio)
                    return redirect('welcome')
                else:
                    # Si no está autenticado, redirigir a login sin mensaje
                    return redirect('login')
        
        return wrapper
    return decorator


def admin_required(view_func):
    """
    Decorador específico para vistas que solo pueden acceder administradores.
    
    Uso:
    @admin_required
    def vista_admin(request):
        pass
    """
    return role_required(['admin'])(view_func)


def teacher_required(view_func):
    """
    Decorador para vistas que pueden acceder profesores, tutores y administradores.
    
    Uso:
    @teacher_required
    def vista_profesor(request):
        pass
    """
    return role_required(['admin', 'profesor', 'tutor'])(view_func)


def student_required(view_func):
    """
    Decorador para vistas específicas de estudiantes.
    
    Uso:
    @student_required
    def vista_estudiante(request):
        pass
    """
    return role_required(['estudiante'])(view_func)


def academic_staff_required(view_func):
    """
    Decorador para vistas académicas (admin, profesores, tutores).
    Excluye estudiantes.
    
    Uso:
    @academic_staff_required
    def vista_academica(request):
        pass
    """
    return role_required(['admin', 'profesor', 'tutor'])(view_func)


def student_data_only(view_func):
    """
    Decorador que permite a estudiantes ver solo sus propios datos.
    Profesores y admin pueden ver todos los datos.
    
    Uso:
    @student_data_only
    def mis_notas(request):
        # La vista debe manejar el filtrado según el rol
        pass
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user_role = getattr(request.user, 'role', None)
        
        # Agregar información del filtrado al request
        if user_role == 'estudiante':
            request.student_filter = True
            request.current_student = request.user
        else:
            request.student_filter = False
            request.current_student = None
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def ajax_role_required(allowed_roles):
    """
    Decorador para vistas AJAX que requieren roles específicos.
    Retorna JSON en lugar de redireccionar.
    
    Uso:
    @ajax_role_required(['admin', 'profesor'])
    def api_view(request):
        pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user_role = getattr(request.user, 'role', None)
            
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No tienes permisos para realizar esta acción.',
                    'required_roles': allowed_roles,
                    'user_role': user_role
                }, status=403)
        
        return wrapper
    return decorator


def export_permission_required(export_type):
    """
    Decorador que valida permisos de exportación según contexto.
    
    Args:
        export_type (str): Tipo de exportación
            - 'administrative': Reportes administrativos (solo admin/profesor)
            - 'study_material': Material de estudio (todos)
            - 'personal_data': Datos personales (cada quien los suyos)
    
    Uso:
    @export_permission_required('administrative')
    def exportar_lista_estudiantes(request):
        pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Verificar que el usuario esté autenticado
            if not request.user.is_authenticated:
                return redirect('login')
            
            user_role = getattr(request.user, 'role', None)
            
            if export_type == 'administrative':
                # Solo Admin y Profesor pueden exportar reportes administrativos
                if user_role not in ['admin', 'profesor', 'tutor']:
                    if request.user.is_authenticated:
                        messages.error(
                            request, 
                            'No tienes permisos para exportar reportes administrativos. '
                            'Contacta a tu administrador.'
                        )
                        return redirect('welcome')
                    else:
                        return redirect('login')
            
            elif export_type == 'study_material':
                # Todos pueden exportar material de estudio
                pass  # Permitir a todos los roles autenticados
            
            elif export_type == 'personal_data':
                # Validación adicional se hace en la vista
                # Aquí solo verificamos que esté autenticado
                pass
            
            else:
                # Tipo de exportación no válido
                if request.user.is_authenticated:
                    messages.error(request, 'Tipo de exportación no válido.')
                    return redirect('welcome')
                else:
                    return redirect('login')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Decoradores de conveniencia para exportación
def admin_export_required(view_func):
    """Solo admin puede exportar"""
    return export_permission_required('administrative')(admin_required(view_func))


def academic_export_required(view_func):
    """Admin y profesores pueden exportar"""
    return export_permission_required('administrative')(academic_staff_required(view_func))


def study_material_export(view_func):
    """Todos pueden exportar material de estudio"""
    return export_permission_required('study_material')(login_required(view_func))


def personal_data_export(view_func):
    """Cada quien puede exportar sus propios datos"""
    return export_permission_required('personal_data')(student_data_only(view_func))


# Función helper para verificar permisos en templates
def user_can_access(user, required_roles):
    """
    Función helper para verificar permisos en templates o vistas.
    
    Args:
        user: Usuario de Django
        required_roles (list): Lista de roles requeridos
    
    Returns:
        bool: True si el usuario puede acceder
    
    Uso en template:
    {% load custom_tags %}
    {% if user|can_access:'admin,profesor' %}
        <button>Solo admin y profesores</button>
    {% endif %}
    """
    if not user.is_authenticated:
        return False
    
    user_role = getattr(user, 'role', None)
    
    if isinstance(required_roles, str):
        required_roles = [role.strip() for role in required_roles.split(',')]
    
    return user_role in required_roles


# Función para logging de accesos no autorizados
def log_unauthorized_access(user, view_name, required_roles):
    """
    Registra intentos de acceso no autorizado para auditoría.
    
    Args:
        user: Usuario que intentó acceder
        view_name (str): Nombre de la vista
        required_roles (list): Roles requeridos
    """
    import logging
    
    logger = logging.getLogger('security')
    
    user_info = f"{user.username} ({getattr(user, 'role', 'sin_rol')})" if user.is_authenticated else "Anónimo"
    
    logger.warning(
        f"Acceso no autorizado: {user_info} intentó acceder a {view_name}. "
        f"Roles requeridos: {required_roles}"
    )
