"""
Role-based permission system for the school management system
"""

# utils/permissions.py
from models.models import get_db_connection
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
        
        # Parent Management
        'create_parent', 'edit_parent', 'delete_parent', 'view_parent',
        
        # School Management
        'create_school', 'edit_school', 'delete_school',
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
        'view_audit_logs', 'export_audit_logs',
        
        # School Management
        'create_school', 'edit_school',
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
        'view_teacher', 'export_teachers',
        
        # Parent viewing
        'view_parent',
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

# Add this fixed version to your utils/permissions.py

def has_permission(user_session, permission):
    """
    Fixed version that works with both role_id and role name
    Check if user has permission with three-tier fallback:
    1. First: Check user-specific overrides (user_permissions table)
    2. Second: Check role-based permissions (role_permissions table)
    3. Third: Fallback to hardcoded PERMISSIONS dictionary
    """

    if not user_session or not isinstance(user_session, dict):
        print("No valid user session")
        return False

    user_id = user_session.get('user_id')
    role = user_session.get('role', '').strip().lower()
    role_id = user_session.get('role_id')

    print(f"Permission check - user_id: {user_id}, role: {role}, role_id: {role_id}, permission: {permission}")

    if not user_id:
        print("No user_id found")
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Check user-level override first
        query = """
            SELECT 1 FROM user_permissions 
            WHERE user_id = %s AND permission = %s 
            AND (expires_at IS NULL OR expires_at > NOW())
        """
        cursor.execute(query, (user_id, permission))
        result = cursor.fetchone()
        if result:
            print(f"Permission granted via user override")
            conn.close()
            return True

        # 2. Check role_permissions table using role_id (your main method)
        if role_id:
            query = """
                SELECT 1 FROM role_permissions 
                WHERE role_id = %s AND permission = %s
            """
            cursor.execute(query, (role_id, permission))
            result = cursor.fetchone()
            if result:
                print(f"Permission granted via role_id {role_id}")
                conn.close()
                return True

        # 3. If no role_id but we have role name, try to get role_id
        if not role_id and role:
            cursor.execute("SELECT id FROM roles WHERE role_name = %s", (role,))
            role_result = cursor.fetchone()
            if role_result:
                role_id = role_result[0]
                # Try the query again with the found role_id
                query = """
                    SELECT 1 FROM role_permissions 
                    WHERE role_id = %s AND permission = %s
                """
                cursor.execute(query, (role_id, permission))
                result = cursor.fetchone()
                if result:
                    print(f"Permission granted via role name {role} (ID: {role_id})")
                    conn.close()
                    return True

        conn.close()

        # 4. Fallback to hardcoded permissions if role name exists
        if role:
            role_permissions = PERMISSIONS.get(role, [])
            has_hardcoded = permission in role_permissions
            print(f"Hardcoded permission check for {role}: {has_hardcoded}")
            return has_hardcoded

        print(f"Permission denied - no valid role information")
        return False

    except Exception as e:
        print(f"Permission check error: {e}")
        # If database fails, try hardcoded permissions as fallback
        if role:
            role_permissions = PERMISSIONS.get(role.lower(), [])
            return permission in role_permissions
        return False

# Also add this debug version that shows exactly what's happening
def debug_has_permission(user_session, permission):
    """Debug version with detailed output"""
    print(f"\n=== DEBUGGING PERMISSION CHECK ===")
    print(f"Permission requested: {permission}")
    print(f"User session: {user_session}")
    
    if not user_session:
        print("FAIL: No user session provided")
        return False
    
    user_id = user_session.get('user_id')
    role = user_session.get('role', '').strip().lower()
    role_id = user_session.get('role_id')
    
    print(f"Extracted - user_id: {user_id}, role: '{role}', role_id: {role_id}")
    
    if not user_id:
        print("FAIL: No user_id in session")
        return False
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check what's actually in the role_permissions table for this role_id
        if role_id:
            cursor.execute("SELECT permission FROM role_permissions WHERE role_id = %s", (role_id,))
            permissions = [row[0] for row in cursor.fetchall()]
            print(f"Permissions in DB for role_id {role_id}: {permissions}")
            
            has_perm = permission in permissions
            print(f"Has permission '{permission}': {has_perm}")
            
            conn.close()
            return has_perm
        else:
            print("No role_id to check against")
            conn.close()
            return False
            
    except Exception as e:
        print(f"Database error: {e}")
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

