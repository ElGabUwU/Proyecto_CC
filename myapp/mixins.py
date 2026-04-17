# mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Mixin base que requiere roles específicos para acceder a la vista.
    
    Uso:
    class MiVista(RoleRequiredMixin, View):
        allowed_roles = ['admin', 'profesor']
    """
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar autenticación primero
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Verificar rol
        user_role = getattr(request.user, 'role', None)
        
        if user_role not in self.allowed_roles:
            return self.handle_role_permission_denied(request, user_role)
        
        return super().dispatch(request, *args, **kwargs)
    
    def handle_role_permission_denied(self, request, user_role):
        """
        Maneja el caso cuando el usuario no tiene el rol requerido.
        """
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


class AdminRequiredMixin(RoleRequiredMixin):
    """
    Mixin que requiere rol de administrador.
    
    Uso:
    class VistaAdmin(AdminRequiredMixin, View):
        pass
    """
    allowed_roles = ['admin']


class TeacherRequiredMixin(RoleRequiredMixin):
    """
    Mixin que permite acceso a profesores, tutores y administradores.
    
    Uso:
    class VistaProfesor(TeacherRequiredMixin, View):
        pass
    """
    allowed_roles = ['admin', 'profesor', 'tutor']


class StudentRequiredMixin(RoleRequiredMixin):
    """
    Mixin que requiere rol de estudiante.
    
    Uso:
    class VistaEstudiante(StudentRequiredMixin, View):
        pass
    """
    allowed_roles = ['estudiante']


class AcademicStaffRequiredMixin(RoleRequiredMixin):
    """
    Mixin para personal académico (admin, profesores, tutores).
    Excluye estudiantes.
    
    Uso:
    class VistaAcademica(AcademicStaffRequiredMixin, View):
        pass
    """
    allowed_roles = ['admin', 'profesor', 'tutor']


class StudentDataOnlyMixin(LoginRequiredMixin):
    """
    Mixin que permite a estudiantes ver solo sus propios datos.
    Profesores y admin pueden ver todos los datos.
    
    Uso:
    class MisNotasView(StudentDataOnlyMixin, View):
        def get_queryset(self):
            if self.request.student_filter:
                # Filtrar solo datos del estudiante
                return MyModel.objects.filter(student__user=self.request.user)
            else:
                # Admin y profesores ven todos
                return MyModel.objects.all()
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar autenticación
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Agregar información del filtrado al request
        user_role = getattr(request.user, 'role', None)
        
        if user_role == 'estudiante':
            request.student_filter = True
            request.current_student = request.user
        else:
            request.student_filter = False
            request.current_student = None
        
        return super().dispatch(request, *args, **kwargs)


class AjaxRoleRequiredMixin(LoginRequiredMixin):
    """
    Mixin para vistas AJAX que requieren roles específicos.
    Retorna JSON en lugar de redireccionar.
    
    Uso:
    class ApiView(AjaxRoleRequiredMixin, View):
        allowed_roles = ['admin', 'profesor']
    """
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar autenticación
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Debes iniciar sesión para acceder.',
                'redirect': '/login/'
            }, status=401)
        
        # Verificar rol
        user_role = getattr(request.user, 'role', None)
        
        if user_role not in self.allowed_roles:
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para realizar esta acción.',
                'required_roles': self.allowed_roles,
                'user_role': user_role
            }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


class ExportPermissionMixin(LoginRequiredMixin):
    """
    Mixin que valida permisos de exportación según contexto.
    
    Uso:
    class ExportarView(ExportPermissionMixin, View):
        export_type = 'administrative'  # o 'study_material' o 'personal_data'
    """
    export_type = None
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar autenticación
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Verificar permisos de exportación
        if not self.check_export_permission(request):
            return self.handle_export_permission_denied(request)
        
        return super().dispatch(request, *args, **kwargs)
    
    def check_export_permission(self, request):
        """
        Verifica si el usuario puede exportar según el tipo.
        """
        user_role = getattr(request.user, 'role', None)
        
        if self.export_type == 'administrative':
            return user_role in ['admin', 'profesor', 'tutor']
        elif self.export_type == 'study_material':
            return True  # Todos pueden exportar material de estudio
        elif self.export_type == 'personal_data':
            return True  # Validación adicional en la vista
        else:
            return False  # Tipo no válido
    
    def handle_export_permission_denied(self, request):
        """
        Maneja el caso cuando no tiene permisos de exportación.
        """
        # Solo agregar mensaje si el usuario está autenticado
        if request.user.is_authenticated:
            if self.export_type == 'administrative':
                message = 'No tienes permisos para exportar reportes administrativos.'
            else:
                message = 'No tienes permisos para exportar este tipo de contenido.'
            
            messages.error(request, message)
            
            # Todos redirigen a welcome (página de inicio)
            return redirect('welcome')
        else:
            # Si no está autenticado, redirigir a login sin mensaje
            return redirect('login')


# Mixins de conveniencia para exportación
class AdminExportMixin(ExportPermissionMixin, AdminRequiredMixin):
    """Solo admin puede exportar"""
    export_type = 'administrative'


class AcademicExportMixin(ExportPermissionMixin, AcademicStaffRequiredMixin):
    """Admin y profesores pueden exportar"""
    export_type = 'administrative'


class StudyMaterialExportMixin(ExportPermissionMixin):
    """Todos pueden exportar material de estudio"""
    export_type = 'study_material'


class PersonalDataExportMixin(ExportPermissionMixin, StudentDataOnlyMixin):
    """Cada quien puede exportar sus propios datos"""
    export_type = 'personal_data'


# Mixin para logging de actividad
class ActivityLogMixin:
    """
    Mixin que registra la actividad del usuario en las vistas.
    
    Uso:
    class MiVista(ActivityLogMixin, View):
        log_action = 'crear_curso'
    """
    log_action = None
    
    def dispatch(self, request, *args, **kwargs):
        """
        Registra la actividad antes de ejecutar la vista.
        """
        response = super().dispatch(request, *args, **kwargs)
        
        # Registrar actividad si está configurado
        if self.log_action and request.user.is_authenticated:
            self.log_user_activity(request)
        
        return response
    
    def log_user_activity(self, request):
        """
        Registra la actividad del usuario.
        """
        import logging
        
        logger = logging.getLogger('activity')
        
        user_info = f"{request.user.username} ({getattr(request.user, 'role', 'sin_rol')})"
        
        logger.info(
            f"Actividad: {user_info} realizó acción '{self.log_action}' "
            f"en {request.path}"
        )
