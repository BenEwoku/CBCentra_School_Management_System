"""
Role-based permission system for the school management system
"""

# Permission matrix - defines what each role can do
"""
Role-based permission system for the school management system
"""

# utils/permissions.py
from models.models import get_db_connection  # ← Add this line
from mysql.connector import Error

# Permission matrix - defines what each role can do
PERMISSIONS = {
    'admin': [
        # User Management
        'create_user', 'update_user', 'delete_user', 'reset_password',
        'deactivate_user', 'reactivate_user', 'unlock_user',
        
        # Teacher Management
        'create_teacher', 'edit_teacher', 'delete_teacher',
        'view_teacher', 'import_teachers', 'export_teachers',
        'unlock_teacher_account',

        # Logs & Monitoring
        'view_login_logs', 'delete_login_logs', 'view_audit_logs',
        
        # System Management
        'manage_system_settings', 'backup_database', 'restore_database',
        
        # All data access
        'view_all_data', 'edit_all_data', 'export_all_data',
        
        # Audit logs
        'view_audit_logs', 'delete_audit_logs', 'export_audit_logs',
    ],
    
    'headteacher': [
        # User Management (limited)
        'create_user', 'update_user', 'reset_password',
        'deactivate_user', 'reactivate_user',
        
        # Teacher Management (can edit, but not delete)
        'create_teacher', 'edit_teacher', 'view_teacher',
        'import_teachers', 'export_teachers',

        # Logs & Monitoring
        'view_login_logs', 'view_audit_logs',
        
        # Data access
        'view_academic_data', 'edit_academic_data', 'export_academic_data',
        
        # Audit logs
        'view_audit_logs', 'export_audit_logs'
    ],
    
    'finance': [
        # Financial operations only
        'view_financial_data', 'edit_financial_data', 'export_financial_data',
        'process_payments', 'generate_financial_reports',
        
        # Can view teacher salary info, but not personal/ID details
        'view_teacher', 'export_teachers'
    ],
    
    'subject_head': [
        # Subject-specific access
        'view_subject_data', 'edit_subject_data', 'export_subject_data',
        'manage_subject_grades', 'view_student_progress',
        
        # Can view teachers in their subject
        'view_teacher', 'export_teachers'
    ],
    
    'teacher': [
        # Classroom operations
        'view_own_classes', 'edit_own_grades', 'take_attendance',
        'view_student_profiles', 'communicate_with_parents',
        
        # Can view own teacher profile
        'view_teacher'
    ],
    
    'staff': [
        # Basic operations
        'view_own_profile', 'update_own_profile', 'change_own_password',
        
        # Can view teacher directory
        'view_teacher', 'export_teachers'
    ]
}
# 2. Updated permissions.py with better error handling:

def has_permission(user_session, permission):
    """
    Check if user has permission:
    1. First: Check user-specific overrides (user_permissions)
    2. Then: Check role-based permissions (role_permissions)
    """
    if not user_session or not isinstance(user_session, dict):
        return False

    user_id = user_session.get('user_id')
    role = user_session.get('role', '').strip().lower()

    if not user_id or not role:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Check user-level override
        query = """
            SELECT 1 FROM user_permissions 
            WHERE user_id = %s AND permission = %s 
            AND (expires_at IS NULL OR expires_at > NOW())
        """
        cursor.execute(query, (user_id, permission))
        result = cursor.fetchone()
        if result:
            conn.close()
            return True  # User has direct access

        # 2. Check role-based permission
        query = """
            SELECT 1 FROM role_permissions rp
            JOIN roles r ON rp.role_id = r.id
            WHERE r.role_name = %s AND rp.permission = %s
        """
        cursor.execute(query, (role, permission))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    except Exception as e:
        print(f"Permission check error: {e}")
        return False

def get_role_permissions(role: str) -> list:
    """
    Get all permissions for a specific role
    
    Args:
        role: The role to get permissions for
    
    Returns:
        list: List of permissions for the role
    """
    return PERMISSIONS.get(role.lower(), [])

def get_all_permissions() -> dict:
    """
    Get the complete permissions matrix
    
    Returns:
        dict: Complete permissions dictionary
    """
    return PERMISSIONS.copy()

def check_user_permission(user_session, permission):
    """
    Alternative function name for checking permissions
    (for backward compatibility)
    """
    return has_permission(user_session, permission)