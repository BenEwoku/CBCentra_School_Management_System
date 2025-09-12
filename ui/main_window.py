# ui/main_window.py
import os
import mysql.connector
from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QToolBar, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QStackedWidget,
    QSizePolicy, QScrollArea, QTabWidget, QInputDialog, QGraphicsDropShadowEffect,
    QDialog, QFileDialog, QGroupBox, QRadioButton, QComboBox, QProgressDialog, QLineEdit,
    QButtonGroup, QApplication, QListWidget
)
from datetime import datetime
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QLinearGradient, QAction, QFont, QCursor 
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, Signal, QTimer
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintPreviewWidget, QPrintDialog
from PySide6.QtPdf import QPdfDocument

# Import your UI forms
from ui.schools_form import SchoolsForm
from ui.users_form import UsersForm
from ui.teachers_form import TeachersForm
from ui.login_logs_form import LoginLogsForm
from ui.audit_logs_form import AuditLogsForm
from ui.audit_base_form import AuditBaseForm
from ui.students_form import StudentsForm
from ui.parents_form import ParentsForm
from ui.class_form import ClassesForm
from ui.books_management_form import BooksManagementForm
from ui.health_management_form import HealthManagementForm

# Import the tab access management form
from ui.tab_access_form import TabAccessManagementForm

# Import the new ribbon components
from ui.ribbon_manager import RibbonManager
from ui.ribbon_handlers import RibbonHandlers

# Email imports
from services.email_service import EmailService, EmailTemplates
from services.email_notification_service import EmailNotificationService
from ui.notification_center import NotificationCenter
from ui.email_composer_dialog import EmailComposerDialog

# Other imports
from utils.permissions import has_permission
from fpdf import FPDF
from docx import Document
import tempfile
import csv

class MainWindow(QMainWindow):
    # Signals
    logout_requested = Signal()
    user_session_updated = Signal(dict)
    
    def __init__(self, config=None, parent=None, user_session=None, db_connection=None, app_paths=None):
        super().__init__(parent)
        
        # Store instance variables
        self.user_session = user_session or {}
        self.app_config = config or {}
        self.db_connection = db_connection
        self.app_paths = app_paths or {}
        
        # Create AuditBaseForm instance for styling and utilities
        self.audit_base = AuditBaseForm(user_session=user_session)
        
        # Inherit all styling from AuditBaseForm
        self.setStyleSheet(self.audit_base.styleSheet())
        self.colors = self.audit_base.colors
        self.fonts = self.audit_base.fonts
        
        # Store reference to audit methods
        self.log_audit_action = self.audit_base.log_audit_action
        self.export_with_green_header = self.audit_base.export_with_green_header
        self.get_school_info = self.audit_base.get_school_info
        
        # Initialize ribbon components
        self.ribbon_manager = RibbonManager(self)
        self.ribbon_handlers = RibbonHandlers(self)
        
        # App configuration
        self.app_config = config or {
            'name': 'CBCentra School Management System',
            'window_title': 'CBCentra SMS Desktop', 
            'min_size': (1024, 768),
            'default_size': (1200, 700)
        }
        
        # Ensure user_session is properly set up
        if isinstance(user_session, dict):
            self.user_session = user_session.copy()
        else:
            # Use safe fallback session
            self.user_session = {
                'user_id': 1,
                'username': 'admin',
                'role': 'admin', 
                'full_name': 'System Administrator',
                'ip_address': '127.0.0.1',
                'permissions': [
                    'view_all_data', 'edit_all_data', 'create_user', 'delete_user',
                    'view_login_logs', 'view_audit_logs', 'export_all_data',
                    'manage_system_settings', 'backup_database'
                ]
            }
        
        # Auto-generate permissions if missing
        if 'permissions' not in self.user_session or self.user_session['permissions'] is None:
            try:
                from utils.permissions import get_role_permissions
                role = self.user_session.get('role', 'user')
                self.user_session['permissions'] = get_role_permissions(role)
                print(f"Permissions auto-generated for role '{role}': {self.user_session['permissions']}")
            except Exception as e:
                print(f"Failed to load permissions: {e}")
                self.user_session['permissions'] = ['view_own_profile'] if self.user_session.get('role') != 'admin' else [
                    'view_login_logs', 'view_audit_logs', 'view_all_data'
                ]
        
        self.app_paths = app_paths or {
            'icons': 'static/icons',
            'images': 'static/images',
            'app_icon': 'static/images/programlogo.png'
        }
        
        self.sidebar_visible = False
        self.ribbon_visible = True
        self.current_pdf_bytes = None
        self.current_file_path = None
        self.current_file_type = None
        self.visible_nested_tabs = {}

        self.init_ui()
        self.setup_window()
        
        # Initialize email services AFTER UI is set up
        self.email_service = EmailService(self.db_connection)
        self.email_notifier = EmailNotificationService(self.db_connection, self.email_service)
        
        # Connect email notification signals
        self.email_notifier.new_notification.connect(self.show_new_notification)
        self.email_notifier.notification_count_changed.connect(self.update_notification_badge)
        
        # Start email monitoring (with check)
        if self.check_email_configuration():
            self.email_notifier.start()
        else:
            print("⚠️ Email not configured - monitoring disabled")
        
        # Check email configuration on startup
        QTimer.singleShot(2000, self.check_email_configuration_on_startup)
    
    def setup_window(self):
        self.setWindowTitle(self.app_config['window_title'])
        self.setGeometry(100, 100, *self.app_config['default_size'])
        self.setMinimumSize(*self.app_config['min_size'])
        if os.path.exists(self.app_paths['app_icon']):
            self.setWindowIcon(QIcon(self.app_paths['app_icon']))
    
            
    # ========================================
    # DATABASE-DRIVEN TAB VISIBILITY METHODS 
    # ========================================
    def get_visible_tabs_for_user(self):
        """Return tabs visible to current user from database"""
        if not self.db_connection:
            return self.get_fallback_visible_tabs()
        
        user_id = self.user_session.get('user_id')
        user_role = self.user_session.get('role', 'user')
        
        try:
            cursor = self.db_connection.cursor()
            
            # Get role-based defaults
            cursor.execute("""
                SELECT tab_name, can_access 
                FROM role_tab_permissions 
                WHERE role_name = %s AND can_access = 1
            """, (user_role,))
            role_tabs = set(row[0] for row in cursor.fetchall())
            
            # Apply user-specific overrides
            cursor.execute("""
                SELECT tab_name, access_type 
                FROM user_tab_overrides 
                WHERE user_id = %s
            """, (user_id,))
            user_overrides = cursor.fetchall()
            cursor.close()
            
            # Build final tab list
            accessible_tabs = set(role_tabs)
            
            for tab_name, access_type in user_overrides:
                if access_type == 'grant':
                    accessible_tabs.add(tab_name)
                elif access_type == 'deny':
                    accessible_tabs.discard(tab_name)
            
            # Separate main tabs from nested tabs
            main_tabs = []
            nested_tabs = {
                'Dashboard': [],
                'Schools': [],
                'Staff': [],
                'Classes': [],
                'Parents': [],
                'Students': [],
                'Others': [],
                'Books Management': [],
                'Health Management': []
            }
            
            for tab_name in accessible_tabs:
                if '.' in tab_name:  # Nested tab format: MainTab.NestedTab
                    parent, child = tab_name.split('.', 1)
                    if parent in nested_tabs:
                        nested_tabs[parent].append(child)
                else:  # Main tab
                    if tab_name not in ['Dashboard']:  # Dashboard is always available if user can log in
                        main_tabs.append(tab_name)
            
            # Always include Dashboard if user is logged in
            if 'Dashboard' not in main_tabs:
                main_tabs.insert(0, 'Dashboard')
                
            return sorted(main_tabs), nested_tabs
            
        except Exception as e:
            print(f"Error loading user tabs from database: {e}")
            return self.get_fallback_visible_tabs()

    def get_fallback_visible_tabs(self):
        """Fallback method using hardcoded rules if database fails"""
        user_role = self.user_session.get('role', 'user')
        
        # Fallback main tabs by role
        if user_role == 'admin':
            main_tabs = ['Dashboard', 'Schools', 'Staff', 'Classes', 'Parents', 'Students', 'Exams', 'Activities', 'Finance', 'Others']
        elif user_role == 'headteacher':
            main_tabs = ['Dashboard', 'Schools', 'Staff', 'Classes', 'Parents', 'Students', 'Exams', 'Activities', 'Others']
        elif user_role == 'teacher':
            main_tabs = ['Dashboard', 'Classes', 'Students', 'Activities', 'Others']
        elif user_role == 'secretary':
            main_tabs = ['Dashboard', 'Students', 'Parents', 'Others']
        elif user_role == 'accountant':
            main_tabs = ['Dashboard', 'Finance', 'Students', 'Others']
        else:
            main_tabs = ['Dashboard']
        
        # Fallback nested tabs - UPDATE THIS SECTION
        nested_tabs = {
            'Dashboard': ['Overview'] if user_role != 'admin' else [
                'Overview', 'User Management', 'Permissions', 'User Permissions', 
                'Tab Access Management', 'Login Activity', 'Audit Trail'
            ],
            'Schools': ['School Registration', 'Schools Database'] if 'Schools' in main_tabs else [],
            'Staff': ['Staff Form', 'Staff Data', 'Staff Analytics', 'Departments'] if 'Staff' in main_tabs else [],
            'Classes': ['Class Form', 'Student Class Assignments', 'Academic Years', 'Terms'] if 'Classes' in main_tabs else [],
            'Parents': ['Parent Form', 'Parents List', 'Analytics'] if 'Parents' in main_tabs else [],
            'Students': ['Student Form', 'Students List', 'Analytics'] if 'Students' in main_tabs else [],
            'Others': ['Books Management', 'Health Management'],  # Books Management under Others
            'Books Management': ['Categories', 'Books', 'Borrowing', 'Reports'],  # Nested tabs within Books Management
            'Health Management': ['Sick Bay Visit', 'Health Records', 'Medical Conditions', 'Medical Inventory', 'Medical Administration']  # ADD HEALTH SUBTABS
        }
        
        return main_tabs, nested_tabs
    
    # ========================
    # UI INITIALIZATION
    # ========================
    def init_ui(self):
        # Get visible tabs once and store them
        self.visible_main_tabs, self.visible_nested_tabs = self.get_visible_tabs_for_user()
        
        self.create_main_tabs()
        # Use the ribbon manager to create ribbon panel
        self.ribbon_manager.create_ribbon_panel()
        self.create_sidebar()
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.create_content_pages()
        
        # Update status bar with user info
        user_info = f"Ready - CBCentra School Management System | User: {self.user_session.get('full_name', 'Unknown')}"
        self.statusBar().showMessage(user_info)
    
        self.sidebar_animation = QPropertyAnimation(self.sidebar_frame, b"geometry")
        self.sidebar_animation.setDuration(300)
        self.sidebar_animation.setEasingCurve(QEasingCurve.OutCubic)
    
        self.overlay_animation = QPropertyAnimation(self.sidebar_overlay, b"windowOpacity")
        self.overlay_animation.setDuration(300)
        
        # Update UI for current user session
        self.update_ui_for_user_session()

        # ================================
        # DEBUG: Check visible tabs
        # ================================
        print("=== DEBUG: User Tab Visibility ===")
        print("Main Tabs:", self.visible_main_tabs)
        for main_tab, nested in self.visible_nested_tabs.items():
            print(f"Nested Tabs for {main_tab}: {nested}")
        print("=================================")


    # ======================================
    # MAIN TABS CREATION (DATABASE-DRIVEN)
    # ======================================
    def create_main_tabs(self):
        """Create the main navigation tabs based on database permissions"""
        self.main_tabbar = QToolBar("Main Tabs")
        self.main_tabbar.setObjectName("mainTabs")
        self.main_tabbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.main_tabbar)
        
        # Add menu toggle button first
        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("tabButton")
        menu_btn.setToolTip("Toggle Menu")
        menu_btn.setCheckable(True)
        menu_btn.clicked.connect(self.toggle_sidebar)
        self.main_tabbar.addWidget(menu_btn)
        
        self.tab_buttons = [menu_btn]
        
        # Use the stored visible tabs instead of querying again
        visible_main_tabs = self.visible_main_tabs
        
        # Create tab mapping for navigation
        self.tab_to_index = {}
        current_index = 0
        
        # Create tab buttons only for visible tabs
        for tab_name in visible_main_tabs:
            btn = QPushButton(tab_name)
            btn.setObjectName("tabButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, t=tab_name: self.on_tab_clicked(t))
            self.main_tabbar.addWidget(btn)
            self.tab_buttons.append(btn)
            
            # Map tab to content page index
            self.tab_to_index[tab_name] = current_index
            current_index += 1
        
        # Set first visible tab as active
        if len(self.tab_buttons) > 1:
            self.tab_buttons[1].setChecked(True)
        
        # Add spacer and profile section
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        self.main_tabbar.addWidget(spacer)
    
        # Create profile section (now includes the toggle button)
        self.create_profile_section()
    
    # =====================================
    # CONTENT PAGES CREATION (NESTED TABS)
    # =====================================
    def create_content_pages(self):
        """Create content pages only for visible tabs with their nested tabs"""
        # Use the stored visible tabs instead of querying again
        visible_main_tabs = self.visible_main_tabs
        
        for tab_name in visible_main_tabs:
            if tab_name == 'Dashboard':
                dashboard_page = self.create_dashboard_page()
                self.stacked_widget.addWidget(dashboard_page)
            elif tab_name == 'Schools':
                schools_page = self.create_schools_page()
                self.stacked_widget.addWidget(schools_page)
            elif tab_name == 'Staff':
                staff_page = self.create_staff_page()
                self.stacked_widget.addWidget(staff_page)
            elif tab_name == 'Classes':
                classes_page = self.create_classes_page()
                self.stacked_widget.addWidget(classes_page)
            elif tab_name == 'Parents':
                parents_page = self.create_parents_page()
                self.stacked_widget.addWidget(parents_page)
            elif tab_name == 'Students':
                students_page = self.create_students_page()
                self.stacked_widget.addWidget(students_page)
            elif tab_name == 'Others':  # REPLACE THIS
                others_page = self.create_others_page()  # Use the actual Others page
                self.stacked_widget.addWidget(others_page)
            else:
                # Placeholder for other tabs (Exams, Activities, Finance)
                placeholder_page = self.create_placeholder_page(tab_name)
                self.stacked_widget.addWidget(placeholder_page)

    def create_others_page(self):
        """Create Others page with nested tabs"""
        others_page = QWidget()
        others_layout = QVBoxLayout(others_page)
        others_layout.setContentsMargins(0, 10, 0, 0)
        
        # Create tab widget for nested tabs
        self.others_tabs = QTabWidget()
        self.others_tabs.setDocumentMode(True)
        self.others_tabs.setTabPosition(QTabWidget.North)
        
        # Connect tab change signal to update ribbon
        self.others_tabs.currentChanged.connect(self.on_others_subtab_changed)
        
        # Get visible nested tabs for Others
        others_subtabs = self.visible_nested_tabs.get('Others', [])
        
        print(f"DEBUG: Others subtabs: {others_subtabs}")
        
        # Add tabs based on visibility
        for subtab_name in others_subtabs:
            if subtab_name == 'Books Management':
                if not hasattr(self, 'books_management_form') or self.books_management_form is None:
                    self.books_management_form = BooksManagementForm(parent=self, user_session=self.user_session)
                self.others_tabs.addTab(self.books_management_form, "Books Management")
                
            elif subtab_name == 'Health Management':  # ADD THIS
                if not hasattr(self, 'health_management_form') or self.health_management_form is None:
                    self.health_management_form = HealthManagementForm(parent=self, user_session=self.user_session)
                self.others_tabs.addTab(self.health_management_form, "Health Management")
                
            # Add other Others tab content here if needed
                    
        others_layout.addWidget(self.others_tabs)
        return others_page
    
    # ui/main_window.py (relevant snippet)
    def on_others_subtab_changed(self, index):
        """Handle subtab changes in Others tab to update ribbon"""
        if hasattr(self, 'others_tabs') and self.others_tabs:
            tab_name = self.others_tabs.tabText(index)
            # Update ribbon based on the active subtab
            self.update_ribbon_panel("Others") 
        
    # =========================================
    # DASHBOARD PAGE WITH NESTED TABS
    # =========================================
    def create_dashboard_page(self):
        """Create dashboard page with permission-controlled nested tabs - FIXED DUPLICATION ISSUE"""
        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(0, 10, 0, 0)
        
        # Create tab widget FIRST
        self.dashboard_tabs = QTabWidget()
        self.dashboard_tabs.setDocumentMode(True)
        self.dashboard_tabs.setTabPosition(QTabWidget.North)
        
        # Get visible nested tabs for Dashboard
        dashboard_subtabs = self.visible_nested_tabs.get('Dashboard', [])
        
        # Track which tabs we've already added to prevent duplicates
        added_tabs = set()
        
        # Add tabs based on visibility - NO DUPLICATES
        for subtab_name in dashboard_subtabs:
            if subtab_name in added_tabs:
                continue  # Skip if already added
                
            if subtab_name == 'Overview':
                overview_tab = self.create_dashboard_overview_tab()
                self.dashboard_tabs.addTab(overview_tab, "Overview")
                added_tabs.add(subtab_name)
                
            elif subtab_name == 'User Management':
                if not hasattr(self, 'users_form') or self.users_form is None:
                    self.users_form = UsersForm(parent=self, user_session=self.user_session)
                self.dashboard_tabs.addTab(self.users_form, "User Management")
                added_tabs.add(subtab_name)
                
            elif subtab_name == 'Permissions':
                from ui.permissions_form import PermissionsForm
                if not hasattr(self, 'permissions_form') or self.permissions_form is None:
                    self.permissions_form = PermissionsForm(parent=self, user_session=self.user_session)
                self.dashboard_tabs.addTab(self.permissions_form, "Permissions")
                added_tabs.add(subtab_name)
                
            elif subtab_name == 'User Permissions':
                from ui.user_permissions_form import UserPermissionsForm
                if not hasattr(self, 'user_perms_tab') or self.user_perms_tab is None:
                    self.user_perms_tab = UserPermissionsForm(parent=self, user_session=self.user_session)
                self.dashboard_tabs.addTab(self.user_perms_tab, "User Permissions")
                added_tabs.add(subtab_name)
                
            elif subtab_name == 'Tab Access Management':
                if not hasattr(self, 'tab_access_form') or self.tab_access_form is None:
                    self.tab_access_form = TabAccessManagementForm(parent=self, user_session=self.user_session)
                    self.tab_access_form.access_changed.connect(self.refresh_user_tabs)
                self.dashboard_tabs.addTab(self.tab_access_form, "Tab Access")
                added_tabs.add(subtab_name)
                
            elif subtab_name == 'Login Activity':
                login_logs_tab = QWidget()
                login_logs_layout = QVBoxLayout(login_logs_tab)
                if not hasattr(self, 'login_logs_form') or self.login_logs_form is None:
                    self.login_logs_form = LoginLogsForm(user_session=self.user_session)
                login_logs_layout.addWidget(self.login_logs_form)
                self.dashboard_tabs.addTab(login_logs_tab, "Login Activity")
                added_tabs.add(subtab_name)
                
            elif subtab_name == 'Audit Trail':
                audit_logs_tab = QWidget()
                audit_logs_layout = QVBoxLayout(audit_logs_tab)
                if not hasattr(self, 'audit_logs_form') or self.audit_logs_form is None:
                    self.audit_logs_form = AuditLogsForm(parent=audit_logs_tab, user_session=self.user_session)
                audit_logs_layout.addWidget(self.audit_logs_form)
                self.dashboard_tabs.addTab(audit_logs_tab, "Audit Trail")
                added_tabs.add(subtab_name)
        
        dashboard_layout.addWidget(self.dashboard_tabs)
        return dashboard_page
    
    def create_dashboard_overview_tab(self):
        """Create the overview tab for dashboard"""
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        welcome_label = QLabel("Welcome to CBCentra School Management System")
        welcome_label.setStyleSheet("""
            font-size: 24px; font-weight: 600; color: #2c3e50;
            padding: 20px; text-align: center;
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        overview_layout.addWidget(welcome_label)
        return overview_tab

    # =========================================
    # SCHOOLS PAGE WITH NESTED TABS  
    # =========================================
    def create_schools_page(self):
        """Create schools page - SIMPLIFIED: Just add the form directly without nested tabs"""
        schools_page = QWidget()
        schools_layout = QVBoxLayout(schools_page)
        schools_layout.setContentsMargins(0, 10, 0, 0)
        
        # DIRECTLY ADD THE SCHOOLS FORM - NO NESTED TABS
        if not hasattr(self, 'schools_form') or self.schools_form is None:
            self.schools_form = SchoolsForm(self)
        schools_layout.addWidget(self.schools_form)
        
        return schools_page

    # =========================================
    # STAFF/TEACHERS PAGE
    # =========================================
    def create_staff_page(self):
        """Create staff page - SIMPLIFIED: Just add the form directly without nested tabs"""
        staff_page = QWidget()
        staff_layout = QVBoxLayout(staff_page)
        staff_layout.setContentsMargins(0, 10, 0, 0)
        
        # DIRECTLY ADD THE TEACHERS FORM - NO NESTED TABS
        if not hasattr(self, 'staff_form') or self.staff_form is None:
            self.staff_form = TeachersForm(parent=self, user_session=self.user_session)
        staff_layout.addWidget(self.staff_form)
        
        return staff_page

    # =========================================
    # CLASSES PAGE
    # =========================================
    def create_classes_page(self):
        """Create classes page - SIMPLIFIED: Just add the form directly without nested tabs"""
        classes_page = QWidget()
        classes_layout = QVBoxLayout(classes_page)
        classes_layout.setContentsMargins(0, 10, 0, 0)
        
        # DIRECTLY ADD THE CLASSES FORM - NO NESTED TABS
        if not hasattr(self, 'classes_form') or self.classes_form is None:
            self.classes_form = ClassesForm(parent=self, user_session=self.user_session)
        classes_layout.addWidget(self.classes_form)
        
        return classes_page

    # =========================================
    # PARENTS PAGE
    # =========================================
    def create_parents_page(self):
        """Create parents page - SIMPLIFIED: Just add the form directly without nested tabs"""
        parents_page = QWidget()
        parents_layout = QVBoxLayout(parents_page)
        parents_layout.setContentsMargins(0, 10, 0, 0)
        
        # DIRECTLY ADD THE PARENTS FORM - NO NESTED TABS
        if not hasattr(self, 'parents_form') or self.parents_form is None:
            self.parents_form = ParentsForm(parent=self, user_session=self.user_session)
        parents_layout.addWidget(self.parents_form)
        
        return parents_page

    # =========================================
    # STUDENTS PAGE
    # =========================================
    def create_students_page(self):
        """Create students page - SIMPLIFIED: Just add the form directly without nested tabs"""
        students_page = QWidget()
        students_layout = QVBoxLayout(students_page)
        students_layout.setContentsMargins(0, 10, 0, 0)
        
        # DIRECTLY ADD THE STUDENTS FORM - NO NESTED TABS
        if not hasattr(self, 'students_form') or self.students_form is None:
            self.students_form = StudentsForm(parent=self, user_session=self.user_session)
        students_layout.addWidget(self.students_form)
        
        return students_page

    def create_placeholder_page(self, tab_name):
        """Create placeholder page for unimplemented tabs"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        page_label = QLabel(f"{tab_name} - Coming Soon")
        page_label.setStyleSheet("""
            font-size: 18px;
            color: #6c757d;
            padding: 40px;
            text-align: center;
        """)
        page_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(page_label)
        return page

    # ============================================
    # TAB REFRESH FUNCTIONALITY (DATABASE-DRIVEN)
    # ============================================
    def refresh_user_tabs(self):
        """Refresh tabs when permissions change - preserves spacer and profile section, auto-selects first tab."""
        try:
            # Get updated visible tabs
            self.visible_main_tabs, self.visible_nested_tabs = self.get_visible_tabs_for_user()
    
            # Safely remove all existing tab buttons except the menu button
            buttons_to_remove = []
            for btn in self.tab_buttons[1:]:  # skip menu button at index 0
                if btn and btn.parent():  # Check if button exists and has a parent
                    buttons_to_remove.append(btn)
    
            # Remove buttons from toolbar
            for btn in buttons_to_remove:
                try:
                    # Find the action associated with the widget
                    for action in self.main_tabbar.actions():
                        if self.main_tabbar.widgetForAction(action) == btn:
                            self.main_tabbar.removeAction(action)
                            break
                    else:
                        # If no action found, try direct widget removal
                        self.main_tabbar.removeWidget(btn)
                    
                    # Set parent to None to properly delete the widget
                    btn.setParent(None)
                    btn.deleteLater()
                except Exception as e:
                    print(f"Warning: Could not remove button {btn.text() if hasattr(btn, 'text') else 'unknown'}: {e}")
    
            # Keep only menu button
            self.tab_buttons = [self.tab_buttons[0]]  # menu button remains
            self.tab_to_index = {}
            current_index = 0
    
            # Find the position to insert new buttons (after menu button, before spacer and profile)
            insert_index = 1  # After menu button
    
            # Recreate visible tab buttons
            for tab_name in self.visible_main_tabs:
                btn = QPushButton(tab_name)
                btn.setObjectName("tabButton")
                btn.setCheckable(True)
                btn.clicked.connect(lambda _, t=tab_name: self.on_tab_clicked(t))
    
                # Insert button at the correct position
                action = self.main_tabbar.insertWidget(
                    self.main_tabbar.actions()[insert_index] if len(self.main_tabbar.actions()) > insert_index else None,
                    btn
                )
                
                self.tab_buttons.append(btn)
                insert_index += 1
    
                # Map tab name to content index
                self.tab_to_index[tab_name] = current_index
                current_index += 1
    
            # Recreate content pages to match new tab structure
            self.recreate_content_pages()
    
            # Auto-select the first visible tab
            if len(self.tab_buttons) > 1:
                first_tab = self.tab_buttons[1]
                first_tab.setChecked(True)
                self.on_tab_clicked(self.visible_main_tabs[0])
    
            QMessageBox.information(self, "Success", "Tab access updated! Changes are now active.")
    
        except Exception as e:
            print(f"Error in refresh_user_tabs: {e}")
            QMessageBox.warning(self, "Error", f"Failed to refresh tabs: {str(e)}")
    
    def recreate_content_pages(self):
        """Recreate content pages to match current visible tabs"""
        try:
            # Clear existing pages
            while self.stacked_widget.count() > 0:
                widget = self.stacked_widget.widget(0)
                self.stacked_widget.removeWidget(widget)
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
    
            # Recreate content pages for visible tabs
            for tab_name in self.visible_main_tabs:
                if tab_name == 'Dashboard':
                    dashboard_page = self.create_dashboard_page()
                    self.stacked_widget.addWidget(dashboard_page)
                elif tab_name == 'Schools':
                    schools_page = self.create_schools_page()
                    self.stacked_widget.addWidget(schools_page)
                elif tab_name == 'Staff':
                    staff_page = self.create_staff_page()
                    self.stacked_widget.addWidget(staff_page)
                elif tab_name == 'Classes':
                    classes_page = self.create_classes_page()
                    self.stacked_widget.addWidget(classes_page)
                elif tab_name == 'Parents':
                    parents_page = self.create_parents_page()
                    self.stacked_widget.addWidget(parents_page)
                elif tab_name == 'Students':
                    students_page = self.create_students_page()
                    self.stacked_widget.addWidget(students_page)
                elif tab_name == 'Others':  # REPLACE THIS
                    others_page = self.create_others_page()  # Use the actual Others page
                    self.stacked_widget.addWidget(others_page)
                else:
                    # Placeholder for other tabs
                    placeholder_page = self.create_placeholder_page(tab_name)
                    self.stacked_widget.addWidget(placeholder_page)
    
        except Exception as e:
            print(f"Error recreating content pages: {e}")
            QMessageBox.warning(self, "Error", f"Failed to recreate content pages: {str(e)}")


    # =====================================
    # TAB NAVIGATION HANDLING  
    # =====================================
    def on_tab_clicked(self, tab_name):
        """Handle tab clicks with dynamic mapping"""
        # Update tab visual state
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(btn.text() == tab_name)
        
        # Update ribbon panel
        self.update_ribbon_panel(tab_name)
        
        # Use dynamic mapping instead of hardcoded
        if tab_name in self.tab_to_index:
            page_index = self.tab_to_index[tab_name]
            self.stacked_widget.setCurrentIndex(page_index)
        
        # Update status bar
        self.statusBar().showMessage(f"Current Section: {tab_name}")
        
        # Special handling for specific tabs
        if tab_name == "Staff" and hasattr(self, 'staff_form'):
            self.staff_form.load_teachers()
            self.staff_form.load_schools()
        elif tab_name == "Others" and hasattr(self, 'books_management_form'):  # Add this
            # Load data when Others tab is selected and Books is the active subtab
            current_subtab = self.others_tabs.tabText(self.others_tabs.currentIndex()) if hasattr(self, 'others_tabs') else ""
            if current_subtab == "Books Management":
                self.books_management_form.load_data()

    # =====================================
    # RIBBON MANAGEMENT
    # =====================================
    def toggle_ribbon(self):
        """Toggle ribbon visibility - now delegates to ribbon manager"""
        self.ribbon_manager.toggle_ribbon_visibility()
    
    def update_ribbon_panel(self, main_tab):
        """Update ribbon panel - now delegates to ribbon manager"""
        self.ribbon_manager.update_ribbon_panel(main_tab)

    # =====================================
    # RIBBON ACTION DELEGATES
    # =====================================
    def add_new_user(self):
        return self.ribbon_handlers.add_new_user()
    
    def refresh_user_data(self):
        return self.ribbon_handlers.refresh_user_data()
    
    def execute_user_export_dialog(self):
        return self.ribbon_handlers.execute_user_export_dialog()

    def show_teachers_form(self):
        return self.ribbon_handlers.show_teachers_form()
    
    def add_new_teacher(self):
        return self.ribbon_handlers.add_new_teacher()
    
    def export_teachers_data(self):
        return self.ribbon_handlers.export_teachers_data()
    
    def import_teachers_data(self):
        return self.ribbon_handlers.import_teachers_data()
    
    def generate_teacher_summary(self):
        return self.ribbon_handlers.generate_teacher_summary()
    
    def refresh_teachers_data(self):
        return self.ribbon_handlers.refresh_teachers_data()
    
    def generate_teacher_profile(self):
        return self.ribbon_handlers.generate_teacher_profile()

    def show_parents_form(self):
        return self.ribbon_handlers.show_parents_form()
    
    def add_new_parent(self):
        return self.ribbon_handlers.add_new_parent()
    
    def refresh_parents_data(self):
        return self.ribbon_handlers.refresh_parents_data()
    
    def import_parents_data(self):
        return self.ribbon_handlers.import_parents_data()
    
    def generate_parent_summary(self):
        return self.ribbon_handlers.generate_parent_summary()
    
    def generate_parent_profile(self):
        return self.ribbon_handlers.generate_parent_profile()
    
    def search_parents(self):
        return self.ribbon_handlers.search_parents()
    
    def manage_parent_contacts(self):
        return self.ribbon_handlers.manage_parent_contacts()
    
    def view_parent_children(self):
        return self.ribbon_handlers.view_parent_children()
    
    def backup_parent_data(self):
        return self.ribbon_handlers.backup_parent_data()
    
    def validate_parent_data(self):
        return self.ribbon_handlers.validate_parent_data()

    def show_login_logs(self):
        return self.ribbon_handlers.show_login_logs()
    
    def show_audit_logs(self):
        return self.ribbon_handlers.show_audit_logs()
    
    def generate_security_report(self):
        return self.ribbon_handlers.generate_security_report()

    def refresh_all_data(self):
        return self.ribbon_handlers.refresh_all_data()
    
    def settings_action(self):
        return self.ribbon_handlers.settings_action()
    
    def new_action(self):
        return self.ribbon_handlers.new_action()
    
    def open_action(self):
        return self.ribbon_handlers.open_action()
    
    def print_action(self):
        return self.ribbon_handlers.print_action()

    # =====================================
    # USER SESSION MANAGEMENT
    # =====================================
    def safe_disconnect(self, signal, slot):
        try:
            signal.disconnect(slot)
        except (RuntimeWarning, RuntimeError, TypeError):
            pass

    def update_user_session(self, new_session_data):
        """Update user session data - CORRECTED METHOD"""
        if isinstance(new_session_data, dict):
            # Update the dictionary directly
            self.user_session.update(new_session_data)
        else:
            # Replace entire session
            self.user_session = new_session_data
        
        # Update UI elements that depend on user session
        self.update_ui_for_user_session()
        self.update_profile_picture()
        self.update_profile_tooltip()
        
        # Emit signal to notify other components
        self.user_session_updated.emit(self.user_session.copy())
        
    def get_user_session(self):
        """Get copy of current user session"""
        return self.user_session.copy() if self.user_session else {}
    
    def update_ui_for_user_session(self):
        """Update UI based on current user session"""
        if not self.user_session:
            return
            
        # Update window title
        username = self.user_session.get('username', 'User')
        title = f"{self.app_config.get('window_title', 'CBCentra')} - {username}"
        self.setWindowTitle(title)
        
        # Update status bar
        if hasattr(self, 'statusBar'):
            user_info = f"Logged in as: {self.user_session.get('full_name', 'User')} ({self.user_session.get('role', 'Unknown')})"
            self.statusBar().showMessage(user_info)
        
        # Update any UI labels that show user info
        if hasattr(self, 'user_name_label'):
            self.user_name_label.setText(self.user_session.get('full_name', 'User'))
            
        if hasattr(self, 'user_role_label'):
            self.user_role_label.setText(self.user_session.get('role', 'User'))

    def on_logout(self):
        """Handle logout request"""
        reply = QMessageBox.question(
            self,
            "Confirm Logout", 
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.logout_requested.emit()

    # =====================================
    # PROFILE SECTION
    # =====================================
    def create_profile_section(self):
        """Create a modern, compact profile section with notification badge."""
        size = 32
        
        # Container
        profile_container = QWidget()
        profile_container.setObjectName("profileContainer")
        profile_layout = QHBoxLayout(profile_container)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(6)
        profile_layout.setAlignment(Qt.AlignVCenter)
        
        # User name
        self.user_name_label = QLabel(self.user_session.get('full_name', 'User'))
        self.user_name_label.setObjectName("userName")
        self.user_name_label.setAlignment(Qt.AlignVCenter)
        profile_layout.addWidget(self.user_name_label)
        
        # Notification badge with right-click functionality
        self.notification_badge = QLabel("0")
        self.notification_badge.setObjectName("notificationBadge")
        self.notification_badge.setStyleSheet("""
            QLabel#notificationBadge {
                background-color: #e74c3c;
                color: white;
                border-radius: 8px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
                min-width: 16px;
                max-width: 16px;
                min-height: 16px;
                max-height: 16px;
            }
            QLabel#notificationBadge:hover {
                background-color: #c0392b;
            }
        """)
        self.notification_badge.setAlignment(Qt.AlignCenter)
        self.notification_badge.hide()  # Hidden by default
        self.notification_badge.setCursor(Qt.PointingHandCursor)
        self.notification_badge.mousePressEvent = self.on_notification_badge_clicked
        profile_layout.addWidget(self.notification_badge)
        
        # Profile picture
        self.profile_pic = QLabel()
        self.profile_pic.setObjectName("profilePic")
        self.profile_pic.setFixedSize(size, size)
        self.profile_pic.setScaledContents(True)
        self.profile_pic.setAlignment(Qt.AlignCenter)
        self.profile_pic.setCursor(Qt.PointingHandCursor)
        self.profile_pic.mousePressEvent = self.on_profile_clicked
        
        # Load image or placeholder
        profile_pixmap = self.load_profile_image(size)
        self.profile_pic.setPixmap(profile_pixmap)
        self.update_profile_tooltip()
        
        profile_layout.addWidget(self.profile_pic)
        
        # Ribbon toggle
        self.ribbon_toggle_btn = QPushButton("▴")
        self.ribbon_toggle_btn.setObjectName("ribbonToggle")
        self.ribbon_toggle_btn.setToolTip("Toggle Ribbon Visibility")
        self.ribbon_toggle_btn.setFixedHeight(size)
        self.ribbon_toggle_btn.clicked.connect(self.toggle_ribbon)
        profile_layout.addWidget(self.ribbon_toggle_btn)
        
        # Add to toolbar
        self.main_tabbar.addWidget(profile_container)
    
    def load_profile_image(self, size):
        """Load and process profile image with fallback to enhanced placeholder"""
        profile_pixmap = None
        profile_image_path = self.user_session.get('profile_image')
        
        if profile_image_path:
            full_path = os.path.join("static", profile_image_path.lstrip("/\\"))
            if os.path.exists(full_path):
                original_pixmap = QPixmap(full_path)
                if not original_pixmap.isNull():
                    profile_pixmap = self.create_circular_pixmap(original_pixmap, size)
    
        # Try fallback image
        if not profile_pixmap or profile_pixmap.isNull():
            fallback_path = "static/icons/profile.png"
            if os.path.exists(fallback_path):
                fallback_pixmap = QPixmap(fallback_path)
                if not fallback_pixmap.isNull():
                    profile_pixmap = self.create_circular_pixmap(fallback_pixmap, size)
    
        # If still no image, create enhanced placeholder
        if not profile_pixmap or profile_pixmap.isNull():
            profile_pixmap = self.create_enhanced_profile_placeholder(size)
    
        return profile_pixmap

    def create_enhanced_profile_placeholder(self, size):
        """Create a more professional and recognizable profile placeholder"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create professional gradient background
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#ffffff"))
        gradient.setColorAt(0.5, QColor("#357abd"))
        gradient.setColorAt(1, QColor("#2e6ba8"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw user icon with better proportions
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(Qt.NoPen)
        
        # Head (circle)
        head_size = size // 4
        head_x = (size - head_size) // 2
        head_y = size // 4
        painter.drawEllipse(head_x, head_y, head_size, head_size)
        
        # Body (rounded rectangle/ellipse)
        body_width = size // 2
        body_height = size // 3
        body_x = (size - body_width) // 2
        body_y = size // 2 + 2
        painter.drawEllipse(body_x, body_y, body_width, body_height)
        
        # Add initials if available
        full_name = self.user_session.get('full_name', 'User')
        if full_name and full_name != 'User':
            initials = ''.join([word[0].upper() for word in full_name.split()[:2]])
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", size//4, QFont.Bold))
            
            # Clear the center and draw initials
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, size-4, size-4)
            
            painter.setPen(QColor("white"))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, initials)
        
        painter.end()
        return pixmap

    def create_circular_pixmap(self, pixmap, size):
        """Create a circular version of the pixmap"""
        # Scale the pixmap to the desired size
        scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Create a new pixmap with transparency
        circular_pixmap = QPixmap(size, size)
        circular_pixmap.fill(Qt.transparent)
        
        # Create a painter to draw the circular image
        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create a circular clipping path
        painter.setBrush(QBrush(scaled_pixmap))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        
        return circular_pixmap

    def on_profile_clicked(self, event):
        """Handle profile picture click - show user menu with email options"""
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
        """)
        
        # Add notification center option
        notification_action = menu.addAction("📧 Notifications")
        notification_action.triggered.connect(self.show_notification_center)
        
        # Add email configuration option (ADD THIS)
        email_config_action = menu.addAction("⚙️ Email Configuration")
        email_config_action.triggered.connect(self.show_email_config)
        
        menu.addSeparator()
        
        # Add existing menu actions
        profile_action = menu.addAction("View Profile")
        profile_action.triggered.connect(self.show_user_profile)
        
        settings_action = menu.addAction("Account Settings")
        settings_action.triggered.connect(self.show_account_settings)
        
        menu.addSeparator()
        
        logout_action = menu.addAction("Logout")
        logout_action.triggered.connect(self.on_logout)
        
        # Show menu at profile picture position
        menu.exec(self.profile_pic.mapToGlobal(self.profile_pic.rect().bottomLeft()))
    
    def show_email_config(self):
        """Show email configuration dialog"""
        from ui.email_config_dialog import EmailConfigDialog
        dialog = EmailConfigDialog(self, self.db_connection)
        dialog.exec()

    def show_user_profile(self):
        """Show user profile dialog"""
        QMessageBox.information(self, "Profile", f"User Profile for: {self.user_session.get('full_name', 'User')}")
    
    def show_account_settings(self):
        """Show account settings dialog"""
        QMessageBox.information(self, "Settings", "Account settings will be available in the next update.")

    def update_profile_picture(self):
        """Update profile picture when session changes"""
        if not hasattr(self, 'profile_pic'):
            return
    
        size = 36
        profile_pixmap = None
        profile_image_path = self.user_session.get('profile_image')
    
        if profile_image_path:
            full_path = os.path.join("static", profile_image_path.lstrip("/\\"))
            if os.path.exists(full_path):
                profile_pixmap = QPixmap(full_path)
    
        if not profile_pixmap or profile_pixmap.isNull():
            fallback_path = "static/icons/profile.png"
            if os.path.exists(fallback_path):
                profile_pixmap = QPixmap(fallback_path)
    
        if profile_pixmap and not profile_pixmap.isNull():
            circular_pixmap = self.create_circular_pixmap(profile_pixmap, size)
            self.profile_pic.setPixmap(circular_pixmap)
        else:
            self.profile_pic.setPixmap(self.create_profile_placeholder(size))

    def update_profile_tooltip(self):
        """Update the profile picture tooltip when session changes"""
        if not hasattr(self, 'profile_pic'):
            return
    
        full_name = self.user_session.get('full_name', 'User')
        position = self.user_session.get('position', 'N/A')
        login_time = self.user_session.get('login_time', 'Unknown')
    
        try:
            login_dt = datetime.fromisoformat(login_time)
            login_str = login_dt.strftime('%Y-%m-%d %H:%M')
        except:
            login_str = 'Just now'
    
        tooltip_text = f"""
        <b>Full Name:</b> {full_name}<br>
        <b>Position:</b> {position}<br>
        <b>Status:</b> <span style="color: #00aa00;">Signed In</span><br>
        <b>Since:</b> {login_str}
        """.strip()
    
        self.profile_pic.setToolTip(tooltip_text)

    #===Email Notifications========
    #    EMAILS
    #===============================

        
    def on_notification_badge_clicked(self, event):
        """Handle notification badge clicks - left click for center, right click for manual check"""
        if event.button() == Qt.LeftButton:
            # Left click - show notification center
            self.show_notification_center()
        elif event.button() == Qt.RightButton:
            # Right click - manual email check
            self.force_email_check()
    
    def force_email_check(self):
        """Manually trigger email check with visual feedback"""
        if hasattr(self, 'email_notifier'):
            # Show checking indicator
            original_text = self.statusBar().currentMessage()
            self.statusBar().showMessage("🔄 Checking for new emails...")
            
            # Force email check
            self.email_notifier._check_incoming_emails()
            
            # Show success message
            self.show_temp_message("✅ Manual email check completed", 3000)
            
            # Restore original status after delay
            QTimer.singleShot(3000, lambda: self.statusBar().showMessage(original_text))
        else:
            self.show_temp_message("❌ Email service not available", 3000, "#dc3545")
    
    def show_temp_message(self, message, duration=3000, color="#28a745"):
        """Show temporary status message in status bar"""
        # Store original message
        if not hasattr(self, '_original_status_message'):
            self._original_status_message = self.statusBar().currentMessage()
        
        # Show temporary message
        self.statusBar().showMessage(message)
        
        # Apply color if specified
        if color:
            self.statusBar().setStyleSheet(f"color: {color};")
        
        # Restore original message after duration
        QTimer.singleShot(duration, self.restore_original_status)
    
    def restore_original_status(self):
        """Restore original status bar message"""
        if hasattr(self, '_original_status_message'):
            self.statusBar().showMessage(self._original_status_message)
            self.statusBar().setStyleSheet("")  # Reset style
    
    # Also update your update_notification_badge method to add tooltip:
    def update_notification_badge(self, count):
        """Update notification badge count with tooltip"""
        if count > 0:
            self.notification_badge.setText(str(count))
            self.notification_badge.show()
            self.notification_badge.setToolTip(
                f"{count} unread notifications\n"
                "Left-click: Open notifications\n"
                "Right-click: Check for new emails"
            )
            
            # Optional: Add animation for new notifications
            if hasattr(self, 'notification_animation'):
                self.notification_animation.stop()
            
            self.notification_animation = QPropertyAnimation(self.notification_badge, b"geometry")
            self.notification_animation.setDuration(200)
            self.notification_animation.setKeyValueAt(0.3, QRect(
                self.notification_badge.x() - 2, 
                self.notification_badge.y() - 2,
                self.notification_badge.width() + 4,
                self.notification_badge.height() + 4
            ))
            self.notification_animation.setEndValue(self.notification_badge.geometry())
            self.notification_animation.start()
        else:
            self.notification_badge.hide()
            self.notification_badge.setToolTip("No unread notifications\nRight-click: Check for new emails")
    
    def show_new_notification(self, notification_data):
        """Show popup for new notification"""
        # Show system tray notification if available
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(
                f"New message from {notification_data['from']}",
                notification_data['preview'],
                QSystemTrayIcon.Information,
                5000
            )
        
        # Optional: Show in-app toast notification
        self.show_toast_notification(notification_data)
    
    def show_toast_notification(self, notification_data):
        """Show in-app toast notification"""
        toast = QLabel(self)
        toast.setObjectName("toastNotification")
        toast.setText(f"📧 {notification_data['from']}: {notification_data['preview']}")
        toast.setStyleSheet("""
            QLabel#toastNotification {
                background-color: #2c3e50;
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                border: 1px solid #34495e;
                font-size: 12px;
            }
        """)
        toast.setAlignment(Qt.AlignCenter)
        toast.setWordWrap(True)
        toast.adjustSize()
        
        # Position at bottom right
        toast.move(
            self.width() - toast.width() - 20,
            self.height() - toast.height() - 60
        )
        toast.show()
        
        # Auto-hide after 5 seconds
        QTimer.singleShot(5000, toast.hide)
    
    def show_notification_center(self, event=None):
        """Show notification center dialog"""
        dialog = NotificationCenter(self, self.db_connection, self.email_notifier)
        dialog.exec()

    def show_email_composer(self, recipient_type=None, recipient_ids=None, subject=None, body=None):
        """Show email composer dialog with configuration check"""
        # Check if email is configured first
        if not self.check_email_configuration():
            # Show configuration dialog instead of just returning
            reply = QMessageBox.question(
                self,
                "Email Not Configured",
                "Email is not configured. Would you like to set it up now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.show_email_config()
            return
        
        dialog = EmailComposerDialog(
            self, 
            self.db_connection,
            recipient_type=recipient_type,
            recipient_ids=recipient_ids,
            subject=subject,
            body=body
        )
        
        if dialog.exec() == QDialog.Accepted:
            email_data = dialog.get_email_data()
            
            # Get selected emails directly from the dialog
            selected_emails = dialog.get_selected_emails()
            
            if not selected_emails:
                QMessageBox.warning(self, "No Recipients", "No email addresses were selected.")
                return
                
            # Show progress dialog for sending
            progress = QProgressDialog("Sending emails...", "Cancel", 0, len(selected_emails), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            success_count = 0
            failed_emails = []
            
            for i, email in enumerate(selected_emails):
                if progress.wasCanceled():
                    break
                    
                progress.setValue(i)
                progress.setLabelText(f"Sending to {email}...")
                QApplication.processEvents()
                
                success, message = self.email_service.send_email(
                    [email],  # Send to one recipient at a time for better error handling
                    email_data['subject'],
                    email_data['body'],
                    email_data.get('attachments'),
                    email_data.get('is_html', True)
                )
                
                if success:
                    success_count += 1
                else:
                    failed_emails.append((email, message))
            
            progress.close()
            
            # Show results
            if success_count > 0:
                if failed_emails:
                    result_msg = f"Successfully sent to {success_count} recipients.\n\nFailed to send to {len(failed_emails)} recipients:\n"
                    for email, error in failed_emails[:5]:  # Show first 5 errors
                        result_msg += f"\n• {email}: {error}"
                    if len(failed_emails) > 5:
                        result_msg += f"\n\n... and {len(failed_emails) - 5} more failures."
                    
                    QMessageBox.warning(self, "Partial Success", result_msg)
                else:
                    QMessageBox.information(self, "Success", f"Email sent to {success_count} recipients!")
            else:
                QMessageBox.warning(self, "Failed", "Failed to send email to any recipients.")

    def email_selected_students(self, student_ids):
        """Quick email for selected students"""
        self.show_email_composer(
            recipient_type='students',
            recipient_ids=student_ids,
            subject="Message from School Administration"
        )
    
    def email_selected_teachers(self, teacher_ids):
        """Quick email for selected teachers"""
        self.show_email_composer(
            recipient_type='teachers', 
            recipient_ids=teacher_ids,
            subject="Staff Communication"
        )
    
    def email_selected_parents(self, parent_ids):
        """Quick email for selected parents"""
        self.show_email_composer(
            recipient_type='parents',
            recipient_ids=parent_ids, 
            subject="Parent Communication from School"
        )
    
    def email_assignment_notification(self, student_id, assignment_data):
        """Send assignment notification email"""
        from services.email_service import EmailTemplates
        
        student_name = self.get_student_name(student_id)
        if not student_name:
            return
            
        self.show_email_composer(
            recipient_type='students',
            recipient_ids=[student_id],
            subject=f"Class Assignment: {assignment_data.get('class_name', 'New Class')}",
            body=EmailTemplates.assignment_notification(student_name, assignment_data)
        )
    
    def get_student_name(self, student_id):
        """Get student name from database"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT full_name FROM students WHERE id = %s", (student_id,))
            result = cursor.fetchone()
            return result['full_name'] if result else None
        except:
            return None
    
    # In your MainWindow class
    
    def show_email_config(self):
        """Show email configuration dialog"""
        from ui.email_config_dialog import EmailConfigDialog
        
        dialog = EmailConfigDialog(self, self.db_connection)
        dialog.config_saved.connect(self.on_email_config_saved)  # Connect the signal
        dialog.exec()
    
    def on_email_config_saved(self):
        """Handle email configuration being saved"""
        # Refresh email service with new configuration
        if hasattr(self, 'email_service'):
            # Reinitialize email service to load new config
            self.email_service = EmailService(self.db_connection)
        
        # Also refresh the notifier if it exists
        if hasattr(self, 'email_notifier'):
            self.email_notifier.stop()
            self.email_notifier = EmailNotificationService(self.db_connection, self.email_service)
            self.email_notifier.new_notification.connect(self.show_new_notification)
            self.email_notifier.notification_count_changed.connect(self.update_notification_badge)
            self.email_notifier.start()
        
        QMessageBox.information(self, "Configuration Updated", 
            "Email configuration has been updated successfully!\n\n"
            "The email service has been restarted with the new settings."
        )
    
    def check_email_configuration(self):
        """Check if email is configured with better error handling"""
        try:
            if not hasattr(self, 'email_service') or self.email_service is None:
                return False
                
            config = self.email_service.get_email_config()
            
            if not config:
                return False
                
            # Handle different config formats
            if isinstance(config, dict):
                return bool(config.get('email_address') and config.get('email_password'))
            elif isinstance(config, tuple) and len(config) >= 3:
                return bool(config[1] and config[2])  # email_address and email_password
            
            return False
            
        except Exception as e:
            print(f"Error checking email config: {e}")
            return False

    def check_email_configuration_on_startup(self):
        """Check email configuration on startup"""
        if not self.check_email_configuration():
            self.statusBar().showMessage("Email not configured - Click the profile menu to set up")

    def test_email_dialog(self):
        """Test method to verify the email dialog appears"""
        try:
            dialog = EmailComposerDialog(self, self.db_connection)
            dialog.setWindowTitle("Test Email Dialog")
            result = dialog.exec()
            print(f"Dialog closed with result: {result}")
        except Exception as e:
            print(f"Error showing dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show dialog: {str(e)}")

    # =====================================
    # SIDEBAR CREATION AND MANAGEMENT  
    # =====================================
    def create_sidebar(self):
        """Create modern floating sidebar with darker gradient background, full height, and animations"""
        # Create overlay background
        self.sidebar_overlay = QFrame(self)
        self.sidebar_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        self.sidebar_overlay.setGeometry(0, 0, self.width(), self.height())
        self.sidebar_overlay.hide()
        self.sidebar_overlay.mousePressEvent = lambda e: self.toggle_sidebar()
    
        # Create sidebar frame
        self.sidebar_frame = QFrame(self)
        self.sidebar_frame.setObjectName("sideMenu")
        self.sidebar_frame.setFixedWidth(300)
    
        # Set full height: starts at y=80 (mainTabs + ribbon), goes to bottom
        self.sidebar_frame.setFixedHeight(self.height() - 80)
        self.sidebar_frame.move(-300, 80)  # Aligns with bottom of ribbon
    
        self.sidebar_frame.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.sidebar_frame.setAttribute(Qt.WA_TranslucentBackground, False)
        self.sidebar_frame.raise_()
        self.sidebar_frame.setParent(self)
    
        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(6, 6)
        self.sidebar_frame.setGraphicsEffect(shadow)
    
        # Apply DARKER gradient background (deeper than main tabs)
        self.sidebar_frame.setStyleSheet("""
            QFrame#sideMenu {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #002B5B,
                    stop:1 #001F44
                );
                border: 1px solid #001428;
                border-radius: 12px;
            }
        """)
    
        # Main sidebar layout
        layout = QVBoxLayout(self.sidebar_frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
    
        # Menu Header
        menu_header = QLabel(" MENU ")
        menu_header.setObjectName("menuHeader")
        menu_header.setStyleSheet(f"""
            QLabel#menuHeader {{
                background-color: {self.colors['main_tab_gradient_start']};
                color: white;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 6px 8px;
                border-radius: 6px;
                border: 1px solid {self.colors['main_tab_border']};
            }}
        """)
        menu_header.setAlignment(Qt.AlignLeft)
        layout.addWidget(menu_header)
    
        # Action Buttons
        actions = [
            ("Home", self.home_action, "home.png"),
            ("Dashboard", self.dashboard_action, "dashboard.png"),
            ("Info", self.info_action, "info.png"),
            ("Print", self.print_action, "print.png"),
            ("Import", self.import_action, "import.png"),
            ("Export", self.export_action, "export.png"),
            ("Settings", self.settings_action, "settings.png"),
            ("Options", self.options_action, "options.png"),
            ("Quit", self.close, "quit.jpg")
        ]
    
        for name, func, icon in actions:
            btn = QPushButton(f"  {name}")
            btn.setObjectName("menuAction")
            btn.setProperty("menuActionName", name.lower())
        
            icon_path = f"static/icons/{icon}"
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(20, 20))
        
            btn.setStyleSheet(f"""
                QPushButton#menuAction {{
                    background-color: {self.colors['background']};
                    color: {self.colors['text_primary']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 13px;
                    font-weight: 500;
                    text-align: left;
                    min-height: 40px;
                    max-height: 40px;
                }}
                QPushButton#menuAction:hover {{
                    background-color: {self.colors['surface']};
                }}
                QPushButton#menuAction:checked {{
                    background-color: #d0e0f0;
                    border-color: {self.colors['primary']};
                    font-weight: bold;
                }}
            """)
        
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, f=func: self.on_sidebar_button_clicked(f, btn))
            layout.addWidget(btn)
    
        layout.addStretch()

    def toggle_sidebar(self):
        """Animate sidebar in and out with proper z-order management and overlay"""
        if self.sidebar_visible:
            # Hide sidebar and overlay
            self.sidebar_animation.setStartValue(QRect(0, 80, 300, self.sidebar_frame.height()))
            self.sidebar_animation.setEndValue(QRect(-300, 80, 300, self.sidebar_frame.height()))
            
            # Fade out overlay
            self.overlay_animation.setStartValue(1.0)
            self.overlay_animation.setEndValue(0.0)
            
            # Safely disconnect signals
            try:
                if self.overlay_animation.finished:
                    self.overlay_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            try:
                if self.sidebar_animation.finished:
                    self.sidebar_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            self.overlay_animation.finished.connect(lambda: self.sidebar_overlay.hide())
            self.sidebar_animation.finished.connect(lambda: self.sidebar_frame.hide())
            self.sidebar_visible = False
            
            # Uncheck menu button
            if self.tab_buttons:
                self.tab_buttons[0].setChecked(False)
            
        else:
            # Show overlay first
            self.sidebar_overlay.setGeometry(0, 0, self.width(), self.height())
            self.sidebar_overlay.show()
            self.sidebar_overlay.raise_()
            
            # Fade in overlay
            self.overlay_animation.setStartValue(0.0)
            self.overlay_animation.setEndValue(1.0)
            
            # Safely disconnect any previous connections
            try:
                if self.overlay_animation.finished:
                    self.overlay_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            try:
                if self.sidebar_animation.finished:
                    self.sidebar_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            # Show sidebar
            self.sidebar_frame.show()
            self.sidebar_frame.raise_()
            
            # Force the sidebar to be above everything
            for child in self.findChildren(QWidget):
                if child not in [self.sidebar_frame, self.sidebar_overlay]:
                    child.stackUnder(self.sidebar_overlay)
            
            self.sidebar_animation.setStartValue(QRect(-300, 80, 300, self.sidebar_frame.height()))
            self.sidebar_animation.setEndValue(QRect(0, 80, 300, self.sidebar_frame.height()))
            self.sidebar_visible = True
            
            # Check menu button
            if self.tab_buttons:
                self.tab_buttons[0].setChecked(True)
        
        # Start both animations
        self.sidebar_animation.start()
        self.overlay_animation.start()

    def on_sidebar_button_clicked(self, func, button):
        """Handle sidebar button click with visual feedback"""
        # Uncheck all other buttons
        for child in self.sidebar_frame.findChildren(QPushButton, "menuAction"):
            if child is not button:
                child.setChecked(False)
        # Execute action
        func()

    # =====================================
    # PDF AND FILE HANDLING
    # =====================================
    def show_pdf_preview_dialog(self, pdf_bytes):
        """Show PDF using the new viewer"""
        try:
            from utils.pdf_utils import view_pdf
            view_pdf(pdf_bytes, parent=self)
        except ImportError:
            # Fallback if utils module is not available
            QMessageBox.critical(self, "Error", "PDF viewer utilities not available")

    # =====================================
    # SIDEBAR ACTIONS
    # =====================================
    def home_action(self):
        self.stacked_widget.setCurrentIndex(0)
        self.update_ribbon_panel("Dashboard")
        for btn in self.tab_buttons:
            btn.setChecked(False)
        self.toggle_sidebar()

    def dashboard_action(self):
        self.stacked_widget.setCurrentIndex(0)
        self.update_ribbon_panel("Dashboard")
        for btn in self.tab_buttons:
            btn.setChecked(False)
        self.toggle_sidebar()

    def info_action(self):
        QMessageBox.about(self, "About CBCentra SMS", 
                         "CBCentra School Management System v1.0.0\n\n"
                         "A comprehensive solution for modern school management.")
        self.toggle_sidebar()

    def import_action(self):
        QMessageBox.information(self, "Import", "Import data from external source")
        self.toggle_sidebar()

    def export_action(self):
        QMessageBox.information(self, "Export", "Export data to external format")
        self.toggle_sidebar()

    def options_action(self):
        QMessageBox.information(self, "Options", "Configure application options")
        self.toggle_sidebar()

    def closeEvent(self, event):
        """Handle application closing with proper cleanup"""
        reply = QMessageBox.question(
            self, "Confirm Exit", 
            "Are you sure you want to exit CBCentra School Management System?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Show closing message
            self.statusBar().showMessage("Closing application - please wait...")
            
            # Force UI update
            QApplication.processEvents()
            
            # Stop email monitoring with timeout
            if hasattr(self, 'email_notifier'):
                print("Stopping email services...")
                self.email_notifier.stop()
                
                # Small delay to allow graceful shutdown
                import time
                time.sleep(1)  # 1 second grace period
            
            # Close database connection
            if self.db_connection:
                try:
                    self.db_connection.close()
                    print("Database connection closed")
                except Exception as e:
                    print(f"Error closing database: {e}")
            
            # Close all child windows
            for child in self.findChildren(QDialog):
                try:
                    child.close()
                    child.deleteLater()
                except:
                    pass
            
            print("Application shutdown complete")
            event.accept()
        else:
            event.ignore()