# context_processors.py

def user_role_context(request):
    """
    Context processor que agrega información del rol del usuario
    a todos los templates del sistema.
    
    Hace disponible:
    - user_role: El rol del usuario actual
    - is_admin: True si es administrador
    - is_teacher: True si es profesor o tutor
    - is_student: True si es estudiante
    """
    if request.user.is_authenticated:
        user_role = getattr(request.user, 'role', None)
        
        return {
            'user_role': user_role,
            'is_admin': user_role == 'admin',
            'is_teacher': user_role in ['profesor', 'tutor'],
            'is_student': user_role == 'estudiante',
        }
    
    # Usuario no autenticado
    return {
        'user_role': None,
        'is_admin': False,
        'is_teacher': False,
        'is_student': False,
    }


def sidebar_context(request):
    """
    Context processor que determina qué elementos del sidebar
    debe ver cada rol de usuario.
    """
    if not request.user.is_authenticated:
        return {'sidebar_items': []}
    
    user_role = getattr(request.user, 'role', None)
    
    # Elementos base que todos ven
    base_items = [
        {
            'name': 'Inicio',
            'url': 'home',
            'icon': 'fas fa-home',
            'roles': ['admin', 'profesor', 'tutor', 'estudiante']
        },
        {
            'name': 'Mi Perfil',
            'url': 'perfil',
            'icon': 'fas fa-user',
            'roles': ['admin', 'profesor', 'tutor', 'estudiante']
        },
    ]
    
    # Elementos específicos por rol
    admin_items = [
        {
            'name': 'Docentes',
            'url': 'docentes',
            'icon': 'fas fa-chalkboard-teacher',
            'roles': ['admin']
        },
        {
            'name': 'Estudiantes',
            'url': 'cedulas',
            'icon': 'fas fa-graduation-cap',
            'roles': ['admin']
        },
        {
            'name': 'Usuarios',
            'url': 'usuarios',
            'icon': 'fas fa-users',
            'roles': ['admin']
        },
        {
            'name': 'To-Do List',
            'url': 'todolist',
            'icon': 'fas fa-tasks',
            'roles': ['admin']
        },
        {
            'name': 'test_zone',
            'url': 'test_zone',
            'icon': 'fas fa-flask',
            'roles': ['admin']
        },
    ]
    
    academic_items = [
        {
            'name': 'Cursos',
            'url': 'cursos',
            'icon': 'fas fa-book',
            'roles': ['admin', 'profesor', 'tutor', 'estudiante']
        },
    ]
    
    # Combinar elementos según el rol
    all_items = base_items + academic_items
    
    if user_role == 'admin':
        all_items.extend(admin_items)
    
    # Filtrar elementos que el usuario puede ver
    visible_items = [
        item for item in all_items 
        if user_role in item['roles']
    ]
    
    return {
        'sidebar_items': visible_items
    }
