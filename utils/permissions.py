"""
Role-based permission system for the school management system
"""

# Permission matrix - defines what each role can do
PERMISSIONS = {
    'admin': [
        # User Management
        'create_user', 'update_user', 'delete_user', 'reset_password',
        'deactivate_user', 'reactivate_user', 'unlock_user',
        
        # Logs & Monitoring
        'view_login_logs', 'delete_login_logs', 'view_audit_logs',
        
        # System Management
        'manage_system_settings', 'backup_database', 'restore_database',
        
        # All data access
        'view_all_data', 'edit_all_data', 'export_all_data',
        # Audit logs
        'view_audit_logs', 'delete_audit_logs', 'export_audit_logs',

        #staff
        
    ],
    
    'headteacher': [
        # User Management (limited)
        'create_user', 'update_user', 'reset_password',
        'deactivate_user', 'reactivate_user',
        
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
        'process_payments', 'generate_financial_reports'
    ],
    
    'subject_head': [
        # Subject-specific access
        'view_subject_data', 'edit_subject_data', 'export_subject_data',
        'manage_subject_grades', 'view_student_progress'
    ],
    
    'teacher': [
        # Classroom operations
        'view_own_classes', 'edit_own_grades', 'take_attendance',
        'view_student_profiles', 'communicate_with_parents'
    ],
    
    'staff': [
        # Basic operations
        'view_own_profile', 'update_own_profile', 'change_own_password'
    ]
}

# 2. Updated permissions.py with better error handling:

def has_permission(user_session, permission):
    """
    Check if a user has the specified permission with better error handling
    """
    # Debug print (remove in production)
    print(f"DEBUG: Checking permission '{permission}' for session: {user_session}")
    
    if not user_session or not isinstance(user_session, dict):
        print(f"DEBUG: Invalid session - type: {type(user_session)}, value: {user_session}")
        return False
    
    role = user_session.get('role', '').strip()
    if not role:
        print(f"DEBUG: No role found in session. Session keys: {list(user_session.keys())}")
        return False
    
    # Convert to lowercase for comparison but also check original case
    role_lower = role.lower()
    
    print(f"DEBUG: Original role: '{role}', Lower role: '{role_lower}'")
    print(f"DEBUG: Available roles in PERMISSIONS: {list(PERMISSIONS.keys())}")
    
    # Check both lowercase and original case
    role_permissions = PERMISSIONS.get(role_lower, [])
    if not role_permissions:
        # Try with original case
        role_permissions = PERMISSIONS.get(role, [])
    
    print(f"DEBUG: Role permissions: {role_permissions}")
    
    has_perm = permission in role_permissions
    print(f"DEBUG: Permission '{permission}' found: {has_perm}")
    
    return has_perm

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