# ui/tab_access_form.py
import os
from datetime import datetime

import mysql.connector
from mysql.connector import Error

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QCheckBox, QGroupBox, QMessageBox,
    QHeaderView, QTabWidget, QLineEdit, QFrame, QScrollArea,
    QApplication, QStyledItemDelegate, QStyleOptionButton, QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont, QPalette, QColor

from models.models import get_db_connection
from ui.audit_base_form import AuditBaseForm


class CheckBoxDelegate(QStyledItemDelegate):
    """Custom delegate for painting a checkbox in a table cell."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        # Optional: draw the cell background as usual
        # super().paint(painter, option, index)  # if you want default bg rendering

        checked = index.data(Qt.CheckStateRole) == Qt.Checked

        opt = QStyleOptionButton()
        opt.state = QStyleOptionButton.State_Enabled
        opt.state |= QStyleOptionButton.State_On if checked else QStyleOptionButton.State_Off

        # Center the checkbox in the cell
        box_size = 16
        x = option.rect.x() + (option.rect.width() - box_size) // 2
        y = option.rect.y() + (option.rect.height() - box_size) // 2
        opt.rect = Qt.QRect(x, y, box_size, box_size)

        QApplication.style().drawControl(QApplication.style().CE_CheckBox, opt, painter)


class TabAccessManagementForm(AuditBaseForm):
    """Enhanced UI for managing tab access for roles and individual users"""
    access_changed = Signal()  # Emit when access changes

    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.user_session = user_session or {}

        # Database connection
        self.db_connection = None
        self.cursor = None
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True)
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")

        # Define all available tabs and nested tabs
        self.all_tabs = {
            'Dashboard': {
                'Overview': 'Dashboard Overview',
                'User Management': 'User Management',
                'Permissions': 'Role Permissions',
                'User Permissions': 'Individual User Permissions',
                'Tab Access Management': 'Tab Access Management',
                'Login Activity': 'Login Activity Logs',
                'Audit Trail': 'System Audit Trail'
            },
            'Schools': {
                'School Registration': 'School Registration Form',
                'Schools Database': 'Schools Database View'
            },
            'Staff': {
                'Staff Form': 'Staff Registration Form',
                'Staff Data': 'Staff Database',
                'Staff Analytics': 'Staff Analytics',
                'Departments': 'Department Management'
            },
            'Classes': {
                'Class Form': 'Class Registration Form',
                'Student Class Assignments': 'Class Assignments',
                'Academic Years': 'Academic Year Management',
                'Terms': 'Term Management'
            },
            'Parents': {
                'Parent Form': 'Parent Registration Form',
                'Parents List': 'Parents Database',
                'Analytics': 'Parent Analytics'
            },
            'Students': {
                'Student Form': 'Student Registration Form',
                'Students List': 'Students Database',
                'Analytics': 'Student Analytics'
            },
            'Exams': {
                'Exam Setup': 'Examination Setup',
                'Results Entry': 'Results Entry',
                'Report Cards': 'Report Card Generation'
            },
            'Activities': {
                'Activity Management': 'Activity Setup',
                'Participation': 'Student Participation'
            },
            'Finance': {
                'Fee Management': 'Fee Structure',
                'Payments': 'Payment Processing',
                'Reports': 'Financial Reports'
            },
            'Others': {
                'System Settings': 'System Configuration',
                'Backup': 'Data Backup & Restore'
            }
        }

        self.role_checkboxes = {}
        self.user_overrides = {}

        self.setup_ui()
        self.load_data()
        self.connect_modification_signals()

    # ---------------------------
    # UI
    # ---------------------------
    def setup_ui(self):
        self.setWindowTitle("Tab Access Management")
        self.setMinimumSize(1100, 700)

        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header
        header = QLabel("TAB ACCESS MANAGEMENT SYSTEM")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #34495e);
                color: white;
                border-radius: 8px;
            }
        """)
        main_layout.addWidget(header)

        # Info
        info = QLabel(
            "Manage which tabs and features users can access based on their roles. "
            "Use role-based access for general permissions and user-specific overrides for exceptions."
        )
        info.setWordWrap(True)
        main_layout.addWidget(info)

        # Splitter to ensure footer never gets squeezed away
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        main_layout.addWidget(splitter, stretch=1)

        # ------- Top: main content (tabs) -------
        content_holder = QWidget()
        content_layout = QVBoxLayout(content_holder)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Role Management Tab
        self.role_tab = self.create_role_management_tab()
        self.tab_widget.addTab(self.role_tab, "🏛️ Role-Based Access")

        # User Management Tab
        self.user_tab = self.create_user_management_tab()
        self.tab_widget.addTab(self.user_tab, "👥 Individual User Access")

        content_layout.addWidget(self.tab_widget)
        splitter.addWidget(content_holder)

        # ------- Bottom: sticky footer with buttons -------
        footer = QFrame()
        footer.setObjectName("footerBar")
        footer.setStyleSheet("""
            QFrame#footerBar {
                border-top: 1px solid #e1e5ea;
                background: #f8f9fa;
            }
        """)
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 8, 10, 8)
        footer_layout.setSpacing(10)

        # Add some left info if desired
        hint = QLabel("Changes are local until you click Save.")
        hint.setStyleSheet("color: #6c757d;")
        footer_layout.addWidget(hint)
        footer_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_data)

        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False)

        footer_layout.addWidget(self.refresh_btn)
        footer_layout.addWidget(self.save_btn)

        splitter.addWidget(footer)

        # Give more space to top area by default
        splitter.setSizes([600, 60])

    def create_role_management_tab(self):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)

        # Role selection
        role_section = QGroupBox("Select Role to Manage")
        role_layout = QHBoxLayout(role_section)
        role_layout.addWidget(QLabel("Role:"))

        self.role_combo = QComboBox()
        self.role_combo.setMinimumWidth(220)
        self.role_combo.currentTextChanged.connect(self.load_role_permissions)
        role_layout.addWidget(self.role_combo)
        role_layout.addStretch()
        layout.addWidget(role_section)

        # Scroll area for the permissions list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(6, 6, 6, 6)
        scroll_layout.setSpacing(8)

        self.role_checkboxes = {}

        for main_tab, nested_tabs in self.all_tabs.items():
            group = QGroupBox(f"{main_tab} Access")
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                    margin-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #2c3e50;
                }
            """)
            group_layout = QVBoxLayout(group)

            # Main tab checkbox
            main_cb = QCheckBox(f"Access to {main_tab} section")
            main_cb.setProperty("tab_name", main_tab)
            main_cb.stateChanged.connect(self.on_main_tab_toggled)
            self.role_checkboxes[main_tab] = {'main': main_cb}
            group_layout.addWidget(main_cb)

            # Nested tabs (disabled by default)
            nested_frame = QFrame()
            nested_layout = QVBoxLayout(nested_frame)
            nested_layout.setContentsMargins(20, 5, 5, 5)

            nested_label = QLabel("Sub-features:")
            nested_label.setStyleSheet("font-weight: bold; color: #6c757d;")
            nested_layout.addWidget(nested_label)

            for nested_key, nested_name in nested_tabs.items():
                full_tab_name = f"{main_tab}.{nested_key}"
                cb = QCheckBox(nested_name)
                cb.setProperty("tab_name", full_tab_name)
                cb.setEnabled(False)
                self.role_checkboxes[full_tab_name] = cb
                nested_layout.addWidget(cb)

            group_layout.addWidget(nested_frame)
            scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        return tab_widget

    def create_user_management_tab(self):
        tab_widget = QWidget()
        layout = QHBoxLayout(tab_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)

        # Left panel
        left_panel = QGroupBox("User Selection")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)

        # Search
        search_group = QGroupBox("Search Users")
        search_layout = QHBoxLayout(search_group)
        search_layout.addWidget(QLabel("🔍 Search:"))

        self.user_search = QLineEdit()
        self.user_search.setPlaceholderText("Search by name, username, or role...")
        self.user_search.textChanged.connect(self.filter_users)
        search_layout.addWidget(self.user_search)
        left_layout.addWidget(search_group)

        # Users table
        self.users_table = QTableWidget()
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.itemSelectionChanged.connect(self.load_user_permissions)
        self.users_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.users_table)

        layout.addWidget(left_panel, stretch=5)

        # Right panel
        right_panel = QGroupBox("User Permissions")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(6)

        user_info_frame = QFrame()
        user_info_layout = QVBoxLayout(user_info_frame)
        self.selected_user_label = QLabel("Please select a user from the list")
        self.selected_user_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px;")
        self.user_role_label = QLabel("")
        self.user_role_label.setStyleSheet("color: #6c757d; font-style: italic;")
        user_info_layout.addWidget(self.selected_user_label)
        user_info_layout.addWidget(self.user_role_label)
        right_layout.addWidget(user_info_frame)

        # Scroll for permissions on the right side
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        scroll_widget = QWidget()
        self.user_permissions_layout = QVBoxLayout(scroll_widget)
        self.user_permissions_layout.setContentsMargins(6, 6, 6, 6)
        self.user_permissions_layout.setSpacing(6)

        self.create_user_permission_controls()

        scroll_area.setWidget(scroll_widget)
        right_layout.addWidget(scroll_area)

        layout.addWidget(right_panel, stretch=6)

        return tab_widget

    # ---------------------------
    # Wiring & helpers
    # ---------------------------
    def connect_modification_signals(self):
        """Enable Save when anything changes."""
        # Role tab signals
        for tab_name, control in self.role_checkboxes.items():
            if isinstance(control, dict) and 'main' in control:
                control['main'].stateChanged.connect(self.on_modification_made)
            elif isinstance(control, QCheckBox):
                control.stateChanged.connect(self.on_modification_made)

        # User tab signals
        for controls in self.user_overrides.values():
            for k in ('grant', 'deny'):
                if k in controls and isinstance(controls[k], QCheckBox):
                    controls[k].stateChanged.connect(self.on_modification_made)

    def on_modification_made(self):
        self.save_btn.setEnabled(True)

    def on_main_tab_toggled(self, state):
        """Enable/disable nested tabs when a main tab is toggled."""
        sender = self.sender()
        main_tab = sender.property("tab_name")
        if not main_tab:
            return

        for nested_key in self.all_tabs.get(main_tab, {}).keys():
            full_tab_name = f"{main_tab}.{nested_key}"
            cb = self.role_checkboxes.get(full_tab_name)
            if isinstance(cb, QCheckBox):
                enable = (state == Qt.Checked)
                cb.setEnabled(enable)
                if not enable:
                    cb.setChecked(False)

    def create_user_permission_controls(self):
        """Create user permission controls with better error handling"""
        try:
            # Clear existing widgets safely
            for i in reversed(range(self.user_permissions_layout.count())):
                item = self.user_permissions_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        self.user_permissions_layout.removeWidget(widget)
                        widget.setParent(None)
                        widget.deleteLater()
    
            self.user_overrides = {}
    
            for main_tab, nested_tabs in self.all_tabs.items():
                group = QGroupBox(f"{main_tab} Access")
                group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        border: 1px solid #ced4da;
                        border-radius: 6px;
                        margin-top: 10px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px;
                        color: #2c3e50;
                    }
                """)
                group_layout = QVBoxLayout(group)
    
                # Main row
                main_frame = QFrame()
                main_h = QHBoxLayout(main_frame)
                main_h.setContentsMargins(5, 5, 5, 5)
    
                main_label = QLabel(f"{main_tab}:")
                main_label.setMinimumWidth(120)
                main_h.addWidget(main_label)
    
                role_label = QLabel("(Role default)")
                role_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
                role_label.setProperty("tab_name", main_tab)
                main_h.addWidget(role_label)
    
                main_h.addStretch()
    
                grant_cb = QCheckBox("Grant Override")
                grant_cb.setProperty("tab_name", main_tab)
                grant_cb.setProperty("access_type", "grant")
                # Connect to mutual exclusion
                grant_cb.stateChanged.connect(lambda state, tab=main_tab: self.handle_override_mutual_exclusion(tab, "grant", state))
    
                deny_cb = QCheckBox("Deny Override")
                deny_cb.setProperty("tab_name", main_tab)
                deny_cb.setProperty("access_type", "deny")
                # Connect to mutual exclusion
                deny_cb.stateChanged.connect(lambda state, tab=main_tab: self.handle_override_mutual_exclusion(tab, "deny", state))
    
                main_h.addWidget(grant_cb)
                main_h.addWidget(deny_cb)
    
                self.user_overrides[main_tab] = {
                    'grant': grant_cb,
                    'deny': deny_cb,
                    'role_label': role_label
                }
                group_layout.addWidget(main_frame)
    
                # Nested rows
                for nested_key, nested_name in nested_tabs.items():
                    full_tab_name = f"{main_tab}.{nested_key}"
    
                    row = QFrame()
                    row_h = QHBoxLayout(row)
                    row_h.setContentsMargins(25, 2, 5, 2)
    
                    nested_label = QLabel(f"• {nested_name}:")
                    nested_label.setMinimumWidth(120)
                    row_h.addWidget(nested_label)
    
                    nested_role_label = QLabel("(Role default)")
                    nested_role_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
                    nested_role_label.setProperty("tab_name", full_tab_name)
                    row_h.addWidget(nested_role_label)
    
                    row_h.addStretch()
    
                    nested_grant = QCheckBox("Grant")
                    nested_grant.setProperty("tab_name", full_tab_name)
                    nested_grant.setProperty("access_type", "grant")
                    nested_grant.stateChanged.connect(lambda state, tab=full_tab_name: self.handle_override_mutual_exclusion(tab, "grant", state))
    
                    nested_deny = QCheckBox("Deny")
                    nested_deny.setProperty("tab_name", full_tab_name)
                    nested_deny.setProperty("access_type", "deny")
                    nested_deny.stateChanged.connect(lambda state, tab=full_tab_name: self.handle_override_mutual_exclusion(tab, "deny", state))
    
                    row_h.addWidget(nested_grant)
                    row_h.addWidget(nested_deny)
    
                    self.user_overrides[full_tab_name] = {
                        'grant': nested_grant,
                        'deny': nested_deny,
                        'role_label': nested_role_label
                    }
    
                    group_layout.addWidget(row)
    
                self.user_permissions_layout.addWidget(group)
    
            self.user_permissions_layout.addStretch()
    
        except Exception as e:
            print(f"Error in create_user_permission_controls: {e}")
            QMessageBox.warning(self, "Error", f"Failed to create user permission controls: {str(e)}")
    
    def handle_override_mutual_exclusion(self, tab_name, clicked_type, state):
        """Ensure grant and deny checkboxes are mutually exclusive"""
        if state != Qt.Checked:
            return
            
        try:
            controls = self.user_overrides.get(tab_name)
            if not controls:
                return
                
            if clicked_type == "grant" and controls['deny'].isChecked():
                controls['deny'].blockSignals(True)
                controls['deny'].setChecked(False)
                controls['deny'].blockSignals(False)
            elif clicked_type == "deny" and controls['grant'].isChecked():
                controls['grant'].blockSignals(True)
                controls['grant'].setChecked(False)
                controls['grant'].blockSignals(False)
                
        except Exception as e:
            print(f"Error handling mutual exclusion for {tab_name}: {e}")

    # ---------------------------
    # Data loading
    # ---------------------------
    def load_data(self):
        self.load_roles()
        self.load_users()
        self.save_btn.setEnabled(False)

    def load_roles(self):
        self.role_combo.blockSignals(True)
        self.role_combo.clear()

        if not self.db_connection:
            # Fallback roles
            self.role_combo.addItems(['admin', 'headteacher', 'teacher', 'staff', 'finance', 'subject_head'])
            self.role_combo.blockSignals(False)
            return

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT role_name FROM roles WHERE is_active = 1 ORDER BY role_name")
            roles = [row[0] for row in cursor.fetchall()]
            cursor.close()

            self.role_combo.addItems(roles or ['admin', 'headteacher', 'teacher', 'staff', 'finance', 'subject_head'])
        except Exception as e:
            print(f"Error loading roles: {e}")
            self.role_combo.addItems(['admin', 'headteacher', 'teacher', 'staff', 'finance', 'subject_head'])

        self.role_combo.blockSignals(False)

        # Auto-load first role
        if self.role_combo.count() > 0:
            self.load_role_permissions(self.role_combo.currentText())

    def load_users(self):
        if not self.db_connection:
            return

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT u.id, u.username, u.full_name, u.role, u.is_active, u.last_login
                FROM users u
                ORDER BY u.full_name
            """)
            users = cursor.fetchall()
            cursor.close()

            self.users_table.setRowCount(len(users))
            self.users_table.setColumnCount(5)
            self.users_table.setHorizontalHeaderLabels(["Username", "Full Name", "Role", "Active", "Last Login"])

            for row, user in enumerate(users):
                user_id, username, full_name, role, is_active, last_login = user

                # Username
                username_item = QTableWidgetItem(username or "")
                username_item.setData(Qt.UserRole, user_id)
                self.users_table.setItem(row, 0, username_item)

                # Full Name
                self.users_table.setItem(row, 1, QTableWidgetItem(full_name or ""))

                # Role
                self.users_table.setItem(row, 2, QTableWidgetItem(role or ""))

                # Active checkbox
                active_item = QTableWidgetItem()
                active_item.setCheckState(Qt.Checked if is_active else Qt.Unchecked)
                # Make it not editable (only checkbox)
                active_item.setFlags(active_item.flags() & ~Qt.ItemIsEditable)
                self.users_table.setItem(row, 3, active_item)

                # Last Login
                last_login_text = ""
                if last_login:
                    try:
                        login_dt = last_login if isinstance(last_login, datetime) else datetime.strptime(str(last_login), '%Y-%m-%d %H:%M:%S')
                        last_login_text = login_dt.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        last_login_text = str(last_login)
                self.users_table.setItem(row, 4, QTableWidgetItem(last_login_text))

            header = self.users_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        except Exception as e:
            print(f"Error loading users: {e}")
            QMessageBox.warning(self, "Error", "Failed to load users from database")

    def filter_users(self, text):
        text_lower = (text or "").lower()
        for row in range(self.users_table.rowCount()):
            show_row = not text_lower
            if not show_row:
                for col in range(self.users_table.columnCount()):
                    item = self.users_table.item(row, col)
                    if item and text_lower in (item.text() or "").lower():
                        show_row = True
                        break
            self.users_table.setRowHidden(row, not show_row)

    def load_role_permissions(self, role_name):
        """Load role permissions and properly initialize checkboxes"""
        if not role_name:
            return
    
        # Reset all checkboxes first
        for tab_name, control in self.role_checkboxes.items():
            if isinstance(control, dict) and 'main' in control:
                control['main'].blockSignals(True)
                control['main'].setChecked(False)
                control['main'].blockSignals(False)
            elif isinstance(control, QCheckBox):
                control.blockSignals(True)
                control.setChecked(False)
                control.setEnabled(False)
                control.blockSignals(False)
    
        if not self.db_connection:
            self.load_default_role_permissions(role_name)
            return
    
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT tab_name, can_access
                FROM role_tab_permissions
                WHERE role_name = %s
            """, (role_name,))
            permissions = dict(cursor.fetchall())
            cursor.close()
    
            # Apply permissions
            for tab_name, has_access in permissions.items():
                if '.' in tab_name:
                    # Nested tab
                    main_tab = tab_name.split('.')[0]
                    if tab_name in self.role_checkboxes:
                        nested_cb = self.role_checkboxes[tab_name]
                        if isinstance(nested_cb, QCheckBox):
                            nested_cb.blockSignals(True)
                            nested_cb.setChecked(bool(has_access))
                            nested_cb.blockSignals(False)
                            # Enable if main tab is enabled
                            main_ctrl = self.role_checkboxes.get(main_tab)
                            if main_ctrl and isinstance(main_ctrl, dict) and 'main' in main_ctrl:
                                if main_ctrl['main'].isChecked():
                                    nested_cb.setEnabled(True)
                else:
                    # Main tab
                    if tab_name in self.role_checkboxes:
                        control = self.role_checkboxes[tab_name]
                        if isinstance(control, dict) and 'main' in control:
                            control['main'].blockSignals(True)
                            control['main'].setChecked(bool(has_access))
                            control['main'].blockSignals(False)
                            
                            # If main tab is checked, enable and load nested tabs
                            if has_access:
                                for nested_key in self.all_tabs.get(tab_name, {}).keys():
                                    nested_tab_name = f"{tab_name}.{nested_key}"
                                    if nested_tab_name in self.role_checkboxes:
                                        nested_cb = self.role_checkboxes[nested_tab_name]
                                        if isinstance(nested_cb, QCheckBox):
                                            nested_cb.setEnabled(True)
                                            # Check if nested permission exists in loaded permissions
                                            nested_access = permissions.get(nested_tab_name, has_access)
                                            nested_cb.blockSignals(True)
                                            nested_cb.setChecked(bool(nested_access))
                                            nested_cb.blockSignals(False)
    
            # For any main tabs not in database, use defaults
            for main_tab in self.all_tabs.keys():
                if main_tab not in permissions:
                    # Use fallback defaults
                    default_allowed = self.get_default_tabs_for_role(role_name)
                    main_ctrl = self.role_checkboxes.get(main_tab)
                    if main_ctrl and isinstance(main_ctrl, dict) and 'main' in main_ctrl:
                        has_default = main_tab in default_allowed
                        main_ctrl['main'].setChecked(has_default)
                        if has_default:
                            # Enable nested tabs with defaults
                            for nested_key in self.all_tabs.get(main_tab, {}).keys():
                                nested_tab_name = f"{main_tab}.{nested_key}"
                                nested_cb = self.role_checkboxes.get(nested_tab_name)
                                if isinstance(nested_cb, QCheckBox):
                                    nested_cb.setEnabled(True)
                                    nested_cb.setChecked(True)  # Default to enabled for new items
    
        except Exception as e:
            print(f"Error loading role permissions: {e}")
            self.load_default_role_permissions(role_name)
    
    def get_default_tabs_for_role(self, role_name):
        """Get default tabs for a role"""
        default_permissions = {
            'admin': list(self.all_tabs.keys()),
            'headteacher': ['Dashboard', 'Schools', 'Staff', 'Classes', 'Parents', 'Students', 'Exams', 'Activities'],
            'teacher': ['Dashboard', 'Classes', 'Students', 'Activities'],
            'staff': ['Dashboard', 'Students', 'Parents'],
            'finance': ['Dashboard', 'Finance', 'Students'],
            'subject_head': ['Dashboard', 'Classes', 'Students']
        }
        return default_permissions.get(role_name, ['Dashboard'])

    def load_user_permissions(self):
        current_row = self.users_table.currentRow()
        if current_row < 0:
            return

        user_id_item = self.users_table.item(current_row, 0)
        if not user_id_item:
            return

        user_id = user_id_item.data(Qt.UserRole)
        username = self.users_table.item(current_row, 0).text()
        full_name = self.users_table.item(current_row, 1).text()
        role = self.users_table.item(current_row, 2).text()

        self.selected_user_label.setText(f"Managing access for: {full_name} ({username})")
        self.user_role_label.setText(f"Primary Role: {role}")

        if not self.db_connection:
            QMessageBox.warning(self, "Database Error", "Cannot load user permissions without database connection")
            return

        try:
            cursor = self.db_connection.cursor()

            cursor.execute("""
                SELECT tab_name, access_type
                FROM user_tab_overrides
                WHERE user_id = %s
            """, (user_id,))
            overrides = dict(cursor.fetchall())

            cursor.execute("""
                SELECT tab_name, can_access
                FROM role_tab_permissions
                WHERE role_name = %s
            """, (role,))
            role_defaults = dict(cursor.fetchall())
            cursor.close()

            for tab_name, controls in self.user_overrides.items():
                # Clear current selections
                controls['grant'].blockSignals(True)
                controls['deny'].blockSignals(True)
                controls['grant'].setChecked(False)
                controls['deny'].setChecked(False)
                controls['grant'].blockSignals(False)
                controls['deny'].blockSignals(False)

                # Role default
                role_has = bool(role_defaults.get(tab_name, False))
                role_text = "✓ Allowed by role" if role_has else "✗ Denied by role"
                controls['role_label'].setText(role_text)
                controls['role_label'].setStyleSheet(
                    "color: #28a745; font-size: 10px;" if role_has else "color: #dc3545; font-size: 10px;"
                )

                # Overrides
                ov = overrides.get(tab_name)
                if ov == 'grant':
                    controls['grant'].setChecked(True)
                elif ov == 'deny':
                    controls['deny'].setChecked(True)

        except Exception as e:
            print(f"Error loading user permissions: {e}")
            QMessageBox.warning(self, "Error", "Failed to load user permissions")

    # ---------------------------
    # Save
    # ---------------------------
    def save_changes(self):
        if not self.db_connection:
            QMessageBox.warning(self, "Error", "No database connection available")
            return
    
        try:
            cursor = self.db_connection.cursor()
            granted_by = self.user_session.get('user_id', 1)
    
            # Save role permissions for the selected role
            current_role = self.role_combo.currentText()
            if current_role:
                self.save_role_permissions(cursor, current_role)
    
            # Save user overrides for the selected user
            current_row = self.users_table.currentRow()
            if current_row >= 0:
                user_id_item = self.users_table.item(current_row, 0)
                if user_id_item:
                    user_id = user_id_item.data(Qt.UserRole)
                    self.save_user_overrides(cursor, user_id, granted_by)
    
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Permissions saved successfully!")
            self.save_btn.setEnabled(False)
            self.access_changed.emit()
    
        except Exception as e:
            if self.db_connection:
                self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save permissions: {str(e)}")
    
    # ---------------------------
    # Role Permissions
    # ---------------------------
    def save_role_permissions(self, cursor, role_name):
        """Save role permissions - only update what's explicitly shown in UI"""
        
        for main_tab, nested_tabs in self.all_tabs.items():
            main_ctrl = self.role_checkboxes.get(main_tab)
            if not main_ctrl or 'main' not in main_ctrl:
                continue
    
            main_checked = main_ctrl['main'].isChecked()
    
            # Always save main tab permission
            cursor.execute("""
                INSERT INTO role_tab_permissions (role_name, tab_name, can_access)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE can_access = VALUES(can_access)
            """, (role_name, main_tab, main_checked))
    
            # For nested tabs, only save if checkbox is enabled (user can see/modify it)
            for nested_key in nested_tabs.keys():
                full_tab_name = f"{main_tab}.{nested_key}"
                nested_cb = self.role_checkboxes.get(full_tab_name)
                if not isinstance(nested_cb, QCheckBox):
                    continue
    
                if nested_cb.isEnabled():
                    # User can see this checkbox, save its current state
                    nested_checked = nested_cb.isChecked()
                    cursor.execute("""
                        INSERT INTO role_tab_permissions (role_name, tab_name, can_access)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE can_access = VALUES(can_access)
                    """, (role_name, full_tab_name, nested_checked))
                elif not main_checked:
                    # Main tab unchecked = force nested to 0
                    cursor.execute("""
                        INSERT INTO role_tab_permissions (role_name, tab_name, can_access)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE can_access = VALUES(can_access)
                    """, (role_name, full_tab_name, False))
                # If main is checked but nested is disabled, leave existing nested permissions alone
    
    # ---------------------------
    # User Overrides
    # ---------------------------
    def save_user_overrides(self, cursor, user_id, granted_by):
        """
        Save user-specific overrides as before.
        """
        for tab_name, controls in self.user_overrides.items():
            # Remove existing override for this tab
            cursor.execute("""
                DELETE FROM user_tab_overrides WHERE user_id = %s AND tab_name = %s
            """, (user_id, tab_name))
    
            # Insert new one if set
            if controls['grant'].isChecked():
                cursor.execute("""
                    INSERT INTO user_tab_overrides (user_id, tab_name, access_type, granted_by, reason)
                    VALUES (%s, %s, 'grant', %s, %s)
                """, (user_id, tab_name, granted_by, 'Manual override by administrator'))
            elif controls['deny'].isChecked():
                cursor.execute("""
                    INSERT INTO user_tab_overrides (user_id, tab_name, access_type, granted_by, reason)
                    VALUES (%s, %s, 'deny', %s, %s)
                """, (user_id, tab_name, granted_by, 'Manual restriction by administrator'))

    