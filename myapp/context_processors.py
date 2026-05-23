# context_processors.py

def user_role_context(request):
    """
    Context processor que inyecta los nuevos roles del Consejo Comunal
    basándose en el usuario nativo de Django.
    """
    if request.user.is_authenticated:
        # Si el usuario es el Superusuario de la terminal, le asignamos rol 'admin' por defecto
        if request.user.is_superuser or request.user.is_staff:
            user_role = 'admin'
        else:
            # Si en el futuro extiendes el modelo o usas perfiles, buscará el rol; si no, es un vecino
            user_role = getattr(request.user, 'role', 'vecino')
        
        # Lista de voceros oficiales según las condicionales de tu sidebar
        voceros_validos = ['vocero_finanzas', 'vocero_secretaria', 'vocero_salud', 'vocero_educacion']
        
        return {
            'user_role': user_role,
            'is_admin': user_role == 'admin',
            'is_vocero': user_role in voceros_validos,
        }
    
    # Usuario visitante / Anónimo
    return {
        'user_role': None,
        'is_admin': False,
        'is_vocero': False,
    }


def sidebar_context(request):
    """
    Context processor que genera dinámicamente el menú del sidebar
    exclusivamente para la Gestión del Consejo Comunal.
    """
    if not request.user.is_authenticated:
        return {'sidebar_items': []}
    
    # Resolver el rol adaptativo
    if request.user.is_superuser or request.user.is_staff:
        user_role = 'admin'
    else:
        user_role = getattr(request.user, 'role', 'vecino')

    # 1. Menú Base (Lo ven todos los usuarios autenticados)
    base_items = [
        {
            'name': 'Inicio',
            'url': 'welcome',  # Sincronizado con tu 'welcome.html'
            'icon': 'fa fa-home',
            'roles': ['admin', 'vocero_finanzas', 'vocero_secretaria', 'vocero_salud', 'vocero_educacion', 'vecino']
        },
        {
            'name': 'Mi Perfil',
            'url': 'perfil',
            'icon': 'fas fa-user',
            'roles': ['admin', 'vocero_finanzas', 'vocero_secretaria', 'vocero_salud', 'vocero_educacion', 'vecino']
        },
    ]
    
    # 2. Menú de Control Interno (Solo para el Administrador del sistema)
    admin_items = [
        {
            'name': 'Usuarios',
            'url': 'usuarios',
            'icon': 'fas fa-users',
            'roles': ['admin']
        },
        {
            'name': 'To-Do List',
            'url': 'todolist',
            'icon': 'fas fa-clipboard-list',
            'roles': ['admin']
        },
    ]
    
    # 3. Menú de Gestión Comunitaria (Admin y Voceros autorizados)
    comunidad_roles = ['admin']
    comunidad_items = [
{
            'name': 'Familias - Habitantes', 
            'url': 'familias',
            'icon': 'fas fa-home',
            'roles': comunidad_roles
        },
        {
            'name': 'Finanzas',
            'url': 'finanzas',
            'icon': 'fas fa-money-bill-wave',
            'roles': comunidad_roles
        },
        {
            'name': 'Documentación',
            'url': 'documentacion',
            'icon': 'fas fa-file-contract',
            'roles': comunidad_roles
        },
    ]
    
    # Construir y filtrar el árbol de navegación final
    all_items = base_items + admin_items + comunidad_items
    
    visible_items = [
        item for item in all_items 
        if user_role in item['roles']
    ]
    
    return {
        'sidebar_items': visible_items
    }