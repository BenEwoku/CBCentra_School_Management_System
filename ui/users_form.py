import sys
import os
import csv
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, QMenu,
    QApplication, QLineEdit
)
from PySide6.QtGui import QFont, QPalette, QIcon
from PySide6.QtCore import Qt, Signal, QSize

import mysql.connector
from mysql.connector import Error

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection
from utils.auth import hash_password
from utils.permissions import has_permission
from ui.audit_base_form import AuditBaseForm


# Change class definition
class UsersForm(AuditBaseForm):
    user_selected = Signal(int)

    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.user_session = user_session
        self.current_user_id = None
        self.current_teacher_id = None
        self.password_visible = False
        self.confirm_password_visible = False
        self.teacher_data = {}
        
        # Set up modern styling
        self.setup_styling()
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor()
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        """Setup the main UI with side-by-side layout"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(15)
    
        # Left side - Form (40% width)
        left_frame = QFrame()
        left_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['background']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
            }}
        """)
        left_frame.setMinimumWidth(490)  # Minimum width instead of fixed
        left_frame.setMaximumWidth(500)  # Maximum width to prevent excessive growth
    
        # Right side - Table (60% width)
        right_frame = QFrame()
        right_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['background']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
            }}
        """)
    
        main_layout.addWidget(left_frame, 2)  # 40% of space
        main_layout.addWidget(right_frame, 3)  # 60% of space
        
        # ADD THESE LINES TO ACTUALLY SET UP THE FORM AND TABLE:
        self.setup_form_section(left_frame)
        self.setup_table_section(right_frame)

    def setup_form_section(self, parent):
        """Setup the form section with scroll area"""
        # Create scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Main layout for scroll area
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
    
        # Header with gradient like table headers
        header_label = QLabel("User Management")
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_label.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
            color: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setMinimumHeight(60)
        layout.addWidget(header_label)
        
        # Form container
        form_group = QGroupBox("User Details")
        form_group.setFont(self.fonts['label'])
        form_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['primary']};
            }}
        """)
        
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
    
        # Username
        self.username_entry = QLineEdit()
        self.username_entry.setFont(self.fonts['entry'])
        self.username_entry.setPlaceholderText("Enter unique username")
        self.username_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_entry_style(self.username_entry)
        form_layout.addRow(self.create_label("Username*:"), self.username_entry)
    
        # Full Name
        self.fullname_entry = QLineEdit()
        self.fullname_entry.setFont(self.fonts['entry'])
        self.fullname_entry.setPlaceholderText("Enter full name")
        self.fullname_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_entry_style(self.fullname_entry)
        form_layout.addRow(self.create_label("Full Name*:"), self.fullname_entry)
    
        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "Headteacher", "Teacher", "Finance", "Subject Head", "Staff"])
        self.role_combo.setCurrentText("Teacher")
        self.role_combo.setFont(self.fonts['entry'])
        self.role_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_combo_style(self.role_combo)
        self.role_combo.currentTextChanged.connect(self.on_role_change)
        form_layout.addRow(self.create_label("Role*:"), self.role_combo)
    
        # Teacher selection
        self.teacher_combo = QComboBox()
        self.teacher_combo.setFont(self.fonts['entry'])
        self.teacher_combo.setPlaceholderText("Select teacher to link")
        self.teacher_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_combo_style(self.teacher_combo)
        self.teacher_combo.currentTextChanged.connect(self.on_teacher_select)
        self.teacher_combo_row = form_layout.rowCount()
        form_layout.addRow(self.create_label("Link to Teacher:"), self.teacher_combo)
    
        # Position
        self.position_entry = QLineEdit()
        self.position_entry.setFont(self.fonts['entry'])
        self.position_entry.setEnabled(False)
        self.position_entry.setPlaceholderText("Auto-filled from teacher record")
        self.position_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_entry_style(self.position_entry)
        self.position_row = form_layout.rowCount()
        form_layout.addRow(self.create_label("Position:"), self.position_entry)
    
        # Password field with toggle
        password_label = self.create_label("Password*:")
        password_label.setToolTip("Password must be at least 8 characters long")
        
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        
        self.password_entry = QLineEdit()
        self.password_entry.setFont(self.fonts['entry'])
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setPlaceholderText("Enter password (min 8 characters)")
        self.password_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_entry_style(self.password_entry)
        
        self.toggle_password_btn = QPushButton("👁")
        self.toggle_password_btn.setFixedSize(25, 25)
        self.toggle_password_btn.setToolTip("Show/hide password")
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        self.setup_icon_button_style(self.toggle_password_btn)
        
        password_layout.addWidget(self.password_entry)
        password_layout.addWidget(self.toggle_password_btn)
        
        form_layout.addRow(password_label, password_container)
    
        # Confirm Password field with toggle
        confirm_password_label = self.create_label("Confirm Password*:")
        
        confirm_password_container = QWidget()
        confirm_password_layout = QHBoxLayout(confirm_password_container)
        confirm_password_layout.setContentsMargins(0, 0, 0, 0)
        
        self.confirm_password_entry = QLineEdit()
        self.confirm_password_entry.setFont(self.fonts['entry'])
        self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_entry.setPlaceholderText("Re-enter password to confirm")
        self.confirm_password_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_entry_style(self.confirm_password_entry)
        
        self.toggle_confirm_password_btn = QPushButton("👁")
        self.toggle_confirm_password_btn.setFixedSize(25, 25)
        self.toggle_confirm_password_btn.setToolTip("Show/hide confirm password")
        self.toggle_confirm_password_btn.clicked.connect(self.toggle_confirm_password_visibility)
        self.setup_icon_button_style(self.toggle_confirm_password_btn)
        
        confirm_password_layout.addWidget(self.confirm_password_entry)
        confirm_password_layout.addWidget(self.toggle_confirm_password_btn)
        
        form_layout.addRow(confirm_password_label, confirm_password_container)
    
        # Status
        self.status_label = QLabel("New User")
        self.status_label.setFont(self.fonts['entry'])
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
        form_layout.addRow(self.create_label("Status:"), self.status_label)
    
        # Security status (new fields)
        self.failed_attempts_label = QLabel("0")
        self.failed_attempts_label.setFont(self.fonts['entry'])
        self.failed_attempts_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        form_layout.addRow(self.create_label("Failed Login Attempts:"), self.failed_attempts_label)
    
        self.lock_status_label = QLabel("Not Locked")
        self.lock_status_label.setFont(self.fonts['entry'])
        self.lock_status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
        form_layout.addRow(self.create_label("Account Lock Status:"), self.lock_status_label)
    
        layout.addWidget(form_group)
    
        # Load teachers and set initial state
        self.load_teachers()
        self.on_role_change("Teacher")
    
        # Buttons
        self.setup_buttons(layout)
        
        # Add some stretch to ensure proper scrolling
        layout.addStretch()

    def create_label(self, text):
        """Create a styled label"""
        label = QLabel(text)
        label.setFont(self.fonts['label'])
        label.setStyleSheet(f"color: {self.colors['text_primary']};")
        return label

    def setup_entry_style(self, entry):
        """Setup consistent entry styling matching TeachersForm"""
        entry.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 13px;
                background-color: {self.colors['input_background']};
                color: {self.colors['text_primary']};
                min-height: 20px;
                line-height: 1.4;
            }}
            QLineEdit:focus {{
                border-color: {self.colors['input_focus']};
                background-color: {self.colors['input_background']};
                border-width: 2px;
            }}
            QLineEdit:disabled {{
                background-color: #f1f5f9;
                color: #64748b;
                border-color: #cbd5e1;
            }}
            QLineEdit::placeholder {{
                color: #94a3b8;
                font-style: italic;
            }}
        """)

    def setup_combo_style(self, combo):
        """Setup consistent combobox styling matching TeachersForm"""
        combo.setStyleSheet(f"""
            QComboBox {{
                border: 2px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 13px;
                background-color: {self.colors['input_background']};
                color: {self.colors['text_primary']};
                min-height: 20px;
                line-height: 1.4;
            }}
            QComboBox:focus {{
                border-color: {self.colors['input_focus']};
                background-color: {self.colors['input_background']};
                border-width: 2px;
            }}
            QComboBox:disabled {{
                background-color: #f1f5f9;
                color: #64748b;
                border-color: #cbd5e1;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.colors['text_secondary']};
            }}
        """)
    
    def setup_size_policies(self):
        """Set consistent size policies for all widgets"""
        # Form widgets
        widgets_to_size = [
            'username_entry', 'fullname_entry', 'role_combo', 'teacher_combo',
            'position_entry', 'password_entry', 'confirm_password_entry'
        ]
        
        for widget_name in widgets_to_size:
            widget = getattr(self, widget_name, None)
            if widget:
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Buttons - only apply to action buttons, not toggle buttons
        action_buttons = []
        for btn in self.findChildren(QPushButton):
            if btn not in [self.toggle_password_btn, self.toggle_confirm_password_btn]:
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                action_buttons.append(btn)
                
    def setup_icon_button_style(self, button):
        """Setup icon button styling matching TeachersForm"""
        button.setStyleSheet(f"""
            QPushButton {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                padding: 4px;
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                min-width: 25px;
                min-height: 25px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['border']};
                border-color: {self.colors['primary']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['secondary']};
                color: white;
            }}
        """)

    def setup_buttons(self, layout):
        """Setup buttons in organized rows with equal width"""
        buttons_group = QGroupBox("Actions")
        buttons_group.setFont(self.fonts['label'])
        buttons_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['primary']};
            }}
        """)
        
        buttons_layout = QVBoxLayout(buttons_group)
    
        # Create all buttons
        buttons = [
            self.create_button("Add User", self.colors['success'], self.add_user),
            self.create_button("Update", self.colors['primary'], self.update_user),
            self.create_button("Clear", self.colors['secondary'], self.clear_form),
            self.create_button("Deactivate", self.colors['danger'], self.deactivate_user),
            self.create_button("Reactivate", self.colors['info'], self.reactivate_user),
            self.create_button("Reset Pwd", self.colors['warning'], self.reset_password),
            self.create_button("Unlock Account", self.colors['info'], self.unlock_account),
            self.create_button("Delete", '#8B0000', self.delete_user)
        ]
    
        # Arrange in rows with equal width
        row1_layout = QHBoxLayout()
        for btn in buttons[:3]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row1_layout.addWidget(btn)
        buttons_layout.addLayout(row1_layout)
    
        row2_layout = QHBoxLayout()
        for btn in buttons[3:6]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row2_layout.addWidget(btn)
        buttons_layout.addLayout(row2_layout)
    
        row3_layout = QHBoxLayout()
        for btn in buttons[6:]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row3_layout.addWidget(btn)
        buttons_layout.addLayout(row3_layout)
    
        layout.addWidget(buttons_group)
    
    def create_button(self, text, color, callback):
        """Create a styled button matching TeachersForm"""
        button = QPushButton(text)
        button.setFont(self.fonts['button'])
        button.clicked.connect(callback)
        button.setMinimumHeight(35)
        button.setMinimumWidth(120)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # ADD THIS LINE
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color_brightness(color, -20)};
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            QPushButton:pressed {{
                background-color: {self.adjust_color_brightness(color, -40)};
                padding: 13px 19px 11px 21px;
            }}
        """)
        return button

    def adjust_color_brightness(self, color, amount):
        """Adjust color brightness by amount (positive = lighter, negative = darker)"""
        if color.startswith('#'):
            color = color[1:]
        
        # Convert hex to RGB
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        
        # Adjust brightness
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        
        return f"#{r:02x}{g:02x}{b:02x}"

    def setup_table_section(self, parent):
        """Setup the table section"""
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
    
        # Search frame
        search_frame = QFrame()
        search_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        search_layout = QHBoxLayout(search_frame)
        
        search_label = QLabel("Search Users:")
        search_label.setFont(self.fonts['label'])
        search_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        search_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # ADDED
        
        self.search_entry = QLineEdit()
        self.search_entry.setFont(self.fonts['entry'])
        self.search_entry.setPlaceholderText("Enter username or full name...")
        self.search_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # ADDED
        self.setup_entry_style(self.search_entry)
        
        search_btn = self.create_button("Search", self.colors['primary'], self.search_users)
        search_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # ADDED
        
        clear_search_btn = self.create_button("Clear", self.colors['secondary'], self.clear_search)
        clear_search_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # ADDED
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(clear_search_btn)
        
        layout.addWidget(search_frame)
    
        # Table
        self.users_table = QTableWidget()
        self.users_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setup_table()
        layout.addWidget(self.users_table)

    def setup_table(self):
        """Setup the users table matching TeachersForm styling"""
        headers = ["ID", "Username", "Full Name", "Role", "Position", "Status", "Failed Attempts", "Lock Status"]
        self.users_table.setColumnCount(len(headers))
        self.users_table.setHorizontalHeaderLabels(headers)
        
        # Set table properties
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSortingEnabled(True)
        
        # Set fonts
        self.users_table.setFont(self.fonts['table'])
        
        # Header styling with green headers
        header = self.users_table.horizontalHeader()
        header.setFont(self.fonts['table_header'])
        header.setStyleSheet(f"""
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
                color: white;
                padding: 16px;
                border: none;
                font-weight: 700;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 6px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: 6px;
            }}
            QHeaderView::section:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f766e, stop:1 #115e59);
            }}
        """)
        
        # Table styling
        self.users_table.setStyleSheet(f"""
            QTableWidget {{
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['background']};
                alternate-background-color: #f8fafc;
                gridline-color: {self.colors['border']};
                selection-background-color: rgba(13, 148, 136, 0.15);
                selection-color: {self.colors['text_primary']};
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 12px 16px;
                border-bottom: 1px solid {self.colors['border']};
                color: {self.colors['text_primary']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(13, 148, 136, 0.2);
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['table_header']};
                font-weight: 600;
            }}
            QTableWidget::item:hover {{
                background-color: rgba(13, 148, 136, 0.1);
            }}
        """)
        
        # Resize columns
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        
        # Connect selection signal
        self.users_table.itemSelectionChanged.connect(self.on_user_select)

    def toggle_password_visibility(self):
        """Toggle password visibility"""
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_btn.setText("🔒")
        else:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_btn.setText("👁")

    def toggle_confirm_password_visibility(self):
        """Toggle confirm password visibility"""
        self.confirm_password_visible = not self.confirm_password_visible
        if self.confirm_password_visible:
            self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_confirm_password_btn.setText("🔒")
        else:
            self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_confirm_password_btn.setText("👁")

    def load_teachers(self):
        """Load available teachers for the dropdown"""
        try:
            # Get teachers who don't have user accounts yet
            query = '''
                SELECT t.id, t.full_name, t.position, t.teacher_id_code
                FROM teachers t
                LEFT JOIN users u ON u.full_name = t.full_name
                WHERE t.is_active = 1 AND u.id IS NULL
                ORDER BY t.full_name
            '''
            self.cursor.execute(query)
            available_teachers = self.cursor.fetchall()
            
            teacher_options = ["None - Manual Entry"]
            self.teacher_data = {}  # Store teacher data for lookup
            
            for teacher in available_teachers:
                teacher_id, full_name, position, teacher_code = teacher
                display_name = f"{full_name} ({teacher_code}) - {position or 'No Position'}"
                teacher_options.append(display_name)
                self.teacher_data[display_name] = {
                    'id': teacher_id,
                    'full_name': full_name,
                    'position': position or ''
                }
            
            # Also include already linked teachers for editing
            query = '''
                SELECT t.id, t.full_name, t.position, t.teacher_id_code, u.id as user_id
                FROM teachers t
                INNER JOIN users u ON u.full_name = t.full_name
                WHERE t.is_active = 1 AND u.role = 'teacher'
                ORDER BY t.full_name
            '''
            self.cursor.execute(query)
            linked_teachers = self.cursor.fetchall()
            
            for teacher in linked_teachers:
                teacher_id, full_name, position, teacher_code, user_id = teacher
                display_name = f"{full_name} ({teacher_code}) - {position or 'No Position'} [LINKED]"
                if display_name not in teacher_options:
                    teacher_options.append(display_name)
                    self.teacher_data[display_name] = {
                        'id': teacher_id,
                        'full_name': full_name,
                        'position': position or '',
                        'user_id': user_id
                    }
            
            self.teacher_combo.clear()
            self.teacher_combo.addItems(teacher_options)
            self.teacher_combo.setCurrentText("None - Manual Entry")
            
        except Error as e:
            print(f"Error loading teachers: {e}")
            self.teacher_combo.clear()
            self.teacher_combo.addItem("None - Manual Entry")

    def on_role_change(self, selected_role):
        """Handle role change event"""
        if selected_role.lower() == "teacher":
            self.teacher_combo.setVisible(True)
            self.position_entry.setVisible(True)
        else:
            self.teacher_combo.setVisible(False)
            self.position_entry.setVisible(False)
            self.teacher_combo.setCurrentText("None - Manual Entry")
            self.position_entry.clear()

    def on_teacher_select(self, selected_teacher):
        """Handle teacher selection from dropdown"""
        if selected_teacher == "None - Manual Entry":
            self.fullname_entry.setEnabled(True)
            self.position_entry.clear()
            self.current_teacher_id = None
        else:
            teacher_info = self.teacher_data.get(selected_teacher, {})
            if teacher_info:
                # Auto-fill name and position
                self.fullname_entry.setText(teacher_info['full_name'])
                self.fullname_entry.setEnabled(False)  # Make read-only
                
                self.position_entry.setText(teacher_info['position'])
                self.current_teacher_id = teacher_info['id']

    def load_users(self):
        """Load all users from database with teacher position info and security status"""
        try:
            query = '''
                SELECT u.id, u.username, u.full_name, u.role, u.is_active,
                       COALESCE(t.position, 'N/A') as position,
                       u.failed_login_attempts,
                       u.account_locked_until
                FROM users u
                LEFT JOIN teachers t ON t.full_name = u.full_name
                ORDER BY u.username
            '''
            self.cursor.execute(query)
            users = self.cursor.fetchall()
            self.update_user_table(users)
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to load users: {e}")

    def update_user_table(self, users):
        """Update the user table with new data including security info"""
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            # Convert is_active boolean to status text
            status = "Active" if user[4] else "Inactive"
            position = user[5] if len(user) > 5 and user[5] else "N/A"
            failed_attempts = user[6] if len(user) > 6 and user[6] is not None else 0
            locked_until = user[7] if len(user) > 7 and user[7] else None
            
            # Determine lock status
            lock_status = "Not Locked"
            if locked_until:
                if locked_until > datetime.now():
                    lock_status = f"Locked until {locked_until.strftime('%Y-%m-%d %H:%M')}"
                else:
                    lock_status = "Lock Expired"
            
            row_data = [
                str(user[0]), user[1], user[2], user[3], position, status,
                str(failed_attempts), lock_status
            ]
            
            for col, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
                
                # Color code status
                if col == 5:  # Status column
                    if data == "Active":
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['success'])
                    else:
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['danger'])
                
                # Color code lock status
                if col == 7:  # Lock status column
                    if "Locked" in data:
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['danger'])
                    elif "Expired" in data:
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['warning'])
                    else:
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['success'])
                
                self.users_table.setItem(row, col, item)

    def on_user_select(self):
        """Handle user selection from table"""
        try:
            current_row = self.users_table.currentRow()
            if current_row < 0:
                return
                
            # Get user ID from first column
            user_id_item = self.users_table.item(current_row, 0)
            if not user_id_item:
                return
                
            try:
                user_id = int(user_id_item.text())
            except ValueError:
                return
                
            # Load user data from database with teacher info and security status
            query = '''
                SELECT u.id, u.username, u.full_name, u.role, u.is_active,
                       t.id as teacher_id, t.position, t.teacher_id_code,
                       u.failed_login_attempts, u.account_locked_until
                FROM users u
                LEFT JOIN teachers t ON t.full_name = u.full_name
                WHERE u.id = %s
            '''
            self.cursor.execute(query, (user_id,))
            user_data = self.cursor.fetchone()
            
            if user_data:
                self.current_user_id = user_id
                self.current_teacher_id = user_data[5] if user_data[5] else None
                
                # Populate form fields
                self.username_entry.setText(user_data[1] or "")
                
                # Enable fullname entry for editing
                self.fullname_entry.setEnabled(True)
                self.fullname_entry.setText(user_data[2] or "")
                
                self.role_combo.setCurrentText(user_data[3] or "Teacher")
                self.on_role_change(user_data[3] or "Teacher")
                
                # Handle teacher selection if linked
                if user_data[5] and user_data[3].lower() == "teacher":  # Has linked teacher
                    teacher_display = f"{user_data[2]} ({user_data[7]}) - {user_data[6] or 'No Position'} [LINKED]"
                    if teacher_display in self.teacher_data:
                        self.teacher_combo.setCurrentText(teacher_display)
                        self.fullname_entry.setEnabled(False)
                    
                    # Show position
                    self.position_entry.setText(user_data[6] or "")
                else:
                    self.teacher_combo.setCurrentText("None - Manual Entry")
                
                # Clear password field for security
                self.password_entry.clear()
                self.confirm_password_entry.clear()
                
                # Update status display
                status = "Active" if user_data[4] else "Inactive"
                status_color = self.colors['success'] if user_data[4] else self.colors['danger']
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
                
                # Update security status
                failed_attempts = user_data[8] if len(user_data) > 8 and user_data[8] is not None else 0
                locked_until = user_data[9] if len(user_data) > 9 and user_data[9] else None
                
                self.failed_attempts_label.setText(str(failed_attempts))
                
                if locked_until and locked_until > datetime.now():
                    lock_status = f"Locked until {locked_until.strftime('%Y-%m-%d %H:%M')}"
                    lock_color = self.colors['danger']
                else:
                    lock_status = "Not Locked"
                    lock_color = self.colors['success']
                
                self.lock_status_label.setText(lock_status)
                self.lock_status_label.setStyleSheet(f"color: {lock_color}; font-weight: bold;")
                
                # Show success notification
                username = self.username_entry.text() or "User"
                QMessageBox.information(self, "Selected", f"{username} is now ready for update/operations")
                
        except Error as e:
            error_msg = f"Error selecting user: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)

    def search_users(self):
        """Search users by username or full name"""
        search_term = self.search_entry.text().strip()
        if not search_term:
            self.load_users()
            return
            
        try:
            query = '''
                SELECT u.id, u.username, u.full_name, u.role, u.is_active,
                       COALESCE(t.position, 'N/A') as position,
                       u.failed_login_attempts,
                       u.account_locked_until
                FROM users u
                LEFT JOIN teachers t ON t.full_name = u.full_name
                WHERE u.username LIKE %s OR u.full_name LIKE %s
                ORDER BY u.username
            '''
            search_pattern = f"%{search_term}%"
            self.cursor.execute(query, (search_pattern, search_pattern))
            users = self.cursor.fetchall()
            self.update_user_table(users)
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to search users: {e}")

    def clear_search(self):
        """Clear search and reload all users"""
        self.search_entry.clear()
        self.load_users()

    def add_user(self):
        print(f"DEBUG: User session role = '{self.user_session.get('role')}'")
        print(f"DEBUG: User session = {self.user_session}")
        """Add new user to database"""
        # Check user permissions
        # Check user permissions - FIXED
        if not has_permission(self.user_session, "create_user"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to create users.")
            return
            
        username = self.username_entry.text().strip()
        full_name = self.fullname_entry.text().strip()
        role = self.role_combo.currentText().strip()
        password = self.password_entry.text().strip()
        confirm_password = self.confirm_password_entry.text().strip()

        # Validate confirm password
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Password and Confirm Password do not match!")
            return

        if not all([username, full_name, password]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return

        try:
            password_hash = hash_password(password)
            
            query = """
                INSERT INTO users (username, full_name, role, password_hash, is_active, failed_login_attempts)
                VALUES (%s, %s, %s, %s, 1, 0)
            """
            self.cursor.execute(query, (username, full_name, role, password_hash))
            self.db_connection.commit()
            
            # Log the action
            self.log_audit_action("CREATE", "users", self.cursor.lastrowid, 
                                 f"Created user {username} with role {role}")
            
            QMessageBox.information(self, "Success", "User added successfully!")
            self.clear_form()
            self.load_users()
            
        except mysql.connector.IntegrityError:
            QMessageBox.critical(self, "Error", "Username already exists.")
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to add user: {e}")

    def update_user(self):
        """Update existing user"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for update")
            return
            
        # Check user permissions
        # Check user permissions - FIXED
        if not has_permission(self.user_session, "update_user"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to update users.")
            return

        username = self.username_entry.text().strip()
        full_name = self.fullname_entry.text().strip()
        role = self.role_combo.currentText().strip()

        if not all([username, full_name]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return

        try:
            # Get old values for audit log
            old_query = "SELECT username, full_name, role FROM users WHERE id = %s"
            self.cursor.execute(old_query, (self.current_user_id,))
            old_values = self.cursor.fetchone()
            
            query = """
                UPDATE users SET username=%s, full_name=%s, role=%s
                WHERE id=%s
            """
            self.cursor.execute(query, (username, full_name, role, self.current_user_id))
            self.db_connection.commit()
            
            # Log the action
            self.log_audit_action("UPDATE", "users", self.current_user_id, 
                                 f"Updated user {username}. Old: {old_values[0]}/{old_values[1]}/{old_values[2]}, New: {username}/{full_name}/{role}")
            
            QMessageBox.information(self, "Success", "User updated successfully!")
            self.clear_form()
            self.load_users()
            self.load_teachers()  # Refresh teacher dropdown
            
        except mysql.connector.IntegrityError:
            QMessageBox.critical(self, "Error", "Username already exists.")
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to update user: {e}")

    def reset_password(self):
        """Reset user password"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Warning", "Please select a user to reset password.")
            return
            
        # Check user permissions - FIXED
        if not has_permission(self.user_session, "reset_password"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to reset passwords.")
            return

        password = self.password_entry.text().strip()
        confirm_password = self.confirm_password_entry.text().strip()

        # Validate confirm password
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Password and Confirm Password do not match!")
            return

        if not password:
            QMessageBox.warning(self, "Warning", "Please enter a new password.")
            return

        try:
            hashed = hash_password(password)
            query = "UPDATE users SET password_hash=%s WHERE id=%s"
            self.cursor.execute(query, (hashed, self.current_user_id))
            self.db_connection.commit()
            
            # Log the action
            self.log_audit_action("UPDATE", "users", self.current_user_id, 
                                 "Password reset by administrator")
            
            QMessageBox.information(self, "Success", "Password reset successfully!")
            self.password_entry.clear()
            self.confirm_password_entry.clear()
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to reset password: {e}")

    def deactivate_user(self):
        """Deactivate user"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Warning", "Please select a user to deactivate.")
            return
            
        # Check user permissions - FIXED
        if not has_permission(self.user_session, "deactivate_user"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to deactivate user.")
            return

        reply = QMessageBox.question(
            self, 
            "Confirm", 
            "Are you sure you want to deactivate this user?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                query = "UPDATE users SET is_active=0 WHERE id=%s"
                self.cursor.execute(query, (self.current_user_id,))
                self.db_connection.commit()
                
                # Log the action
                self.log_audit_action("UPDATE", "users", self.current_user_id, 
                                     "User deactivated by administrator")
                
                QMessageBox.information(self, "Success", "User deactivated successfully!")
                self.clear_form()
                self.load_users()
            except Error as e:
                QMessageBox.critical(self, "Error", f"Failed to deactivate user: {e}")

    def reactivate_user(self):
        """Reactivate user"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Warning", "Please select a user to reactivate.")
            return
            
        # Check user permissions - FIXED
        if not has_permission(self.user_session, "reactivate_user"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to reactivate user.")
            return

        reply = QMessageBox.question(
            self, 
            "Confirm", 
            "Are you sure you want to reactivate this user?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                query = "UPDATE users SET is_active=1 WHERE id=%s"
                self.cursor.execute(query, (self.current_user_id,))
                self.db_connection.commit()
                
                # Log the action
                self.log_audit_action("UPDATE", "users", self.current_user_id, 
                                     "User reactivated by administrator")
                
                QMessageBox.information(self, "Success", "User reactivated successfully!")
                self.clear_form()
                self.load_users()
            except Error as e:
                QMessageBox.critical(self, "Error", f"Failed to reactivate user: {e}")

    def unlock_account(self):
        """Unlock user account"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Warning", "Please select a user to unlock.")
            return
            
        # Check user permissions - FIXED
        if not has_permission(self.user_session, "unlock_user"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to unlock user.")
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Unlock", 
            "Are you sure you want to unlock this user account and reset failed login attempts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                query = "UPDATE users SET failed_login_attempts=0, account_locked_until=NULL WHERE id=%s"
                self.cursor.execute(query, (self.current_user_id,))
                self.db_connection.commit()
                
                # Log the action
                self.log_audit_action("UPDATE", "users", self.current_user_id, 
                                     "Account unlocked and failed attempts reset by administrator")
                
                QMessageBox.information(self, "Success", "Account unlocked successfully!")
                self.clear_form()
                self.load_users()
            except Error as e:
                QMessageBox.critical(self, "Error", f"Failed to unlock account: {e}")

    def delete_user(self):
        """Delete user permanently"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Warning", "Please select a user to delete.")
            return
            
        # Check user permissions - FIXED
        if not has_permission(self.user_session, "delete_user"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete user.")
            return

        # Get username for confirmation
        username = self.username_entry.text() or "this user"

        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to permanently delete {username}?\n\nThis action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Get user info for audit log before deletion
                user_query = "SELECT username, full_name, role FROM users WHERE id = %s"
                self.cursor.execute(user_query, (self.current_user_id,))
                user_info = self.cursor.fetchone()
                
                query = "DELETE FROM users WHERE id=%s"
                self.cursor.execute(query, (self.current_user_id,))
                self.db_connection.commit()
                
                # Log the action
                if user_info:
                    self.log_audit_action("DELETE", "users", self.current_user_id, 
                                         f"Deleted user {user_info[0]} ({user_info[1]}) with role {user_info[2]}")
                
                QMessageBox.information(self, "Success", "User deleted successfully!")
                self.clear_form()
                self.load_users()
                self.load_teachers()  # Refresh teacher dropdown
            except Error as e:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {e}")

    def clear_form(self):
        """Clear all form fields"""
        self.username_entry.clear()
        
        # Enable fullname entry before clearing
        self.fullname_entry.setEnabled(True)
        self.fullname_entry.clear()
        
        self.role_combo.setCurrentText("Teacher")
        self.teacher_combo.setCurrentText("None - Manual Entry")
        
        # Clear position entry
        self.position_entry.clear()
        self.password_entry.clear()
        self.confirm_password_entry.clear()
        
        # Reset password visibility
        if self.password_visible:
            self.toggle_password_visibility()
        if self.confirm_password_visible:
            self.toggle_confirm_password_visibility()
        
        # Reset status
        self.status_label.setText("New User")
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
        
        # Reset security status
        self.failed_attempts_label.setText("0")
        self.lock_status_label.setText("Not Locked")
        self.lock_status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
        
        # Reset current selections
        self.current_user_id = None
        self.current_teacher_id = None
        
        # Handle role change to show/hide teacher fields
        self.on_role_change("Teacher")
    
    def refresh_data(self):
        """Refresh all data in the form with progress indication"""
        try:
            # Show loading state
            self.status_label.setText("Refreshing...")
            self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
            
            # Process events to update UI
            QApplication.processEvents()
            
            # Clear current selection
            self.current_user_id = None
            self.current_teacher_id = None
            
            # Reload users data
            self.load_users()
            
            # Reload teachers for dropdown
            self.load_teachers()
            
            # Clear form fields
            self.username_entry.clear()
            self.fullname_entry.clear()
            self.fullname_entry.setEnabled(True)
            self.password_entry.clear()
            self.confirm_password_entry.clear()
            self.position_entry.clear()
            self.role_combo.setCurrentText("Teacher")
            self.teacher_combo.setCurrentText("None - Manual Entry")
            
            # Reset security status
            self.failed_attempts_label.setText("0")
            self.lock_status_label.setText("Not Locked")
            self.lock_status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
            
            # Clear search
            self.search_entry.clear()
            
            # Update status message
            self.status_label.setText("Data Refreshed")
            self.status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
            
            # Show brief success message (optional)
            # QMessageBox.information(self, "Success", "User data refreshed successfully!")
            
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {e}")
            self.status_label.setText("Refresh Failed")
            self.status_label.setStyleSheet(f"color: {self.colors['danger']}; font-weight: bold;")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error during refresh: {e}")
            self.status_label.setText("Refresh Failed")
            self.status_label.setStyleSheet(f"color: {self.colors['danger']}; font-weight: bold;")

    
    def get_user_stats(self):
        """Get user statistics for display"""
        try:
            # Total users
            self.cursor.execute("SELECT COUNT(*) FROM users")
            total_users = self.cursor.fetchone()[0]
            
            # Active users
            self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active_users = self.cursor.fetchone()[0]
            
            # Locked users
            self.cursor.execute("SELECT COUNT(*) FROM users WHERE account_locked_until > NOW()")
            locked_users = self.cursor.fetchone()[0]
            
            # Users by role
            self.cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            role_stats = dict(self.cursor.fetchall())
            
            return {
                'total': total_users,
                'active': active_users,
                'inactive': total_users - active_users,
                'locked': locked_users,
                'roles': role_stats
            }
        except Error as e:
            print(f"Error getting user stats: {e}")
            return {'total': 0, 'active': 0, 'inactive': 0, 'locked': 0, 'roles': {}}

    def export_users(self, checked=False):
        """
        Export users to Excel with green header
        :param checked: Ignored. Supplied by Qt when used as direct slot
        """
        try:
            query = '''
                SELECT 
                    u.id,
                    u.username,
                    u.full_name,
                    u.role,
                    CASE WHEN u.is_active = 1 THEN 'Active' ELSE 'Inactive' END AS status,
                    COALESCE(t.position, 'N/A') AS position,
                    CASE 
                        WHEN u.account_locked_until IS NULL THEN 'Unlocked'
                        WHEN u.account_locked_until > NOW() THEN 'Locked'
                        ELSE 'Unlocked'
                    END AS lock_status
                FROM users u
                LEFT JOIN teachers t ON TRIM(UPPER(t.full_name)) = TRIM(UPPER(u.full_name))
                ORDER BY u.role, u.full_name
            '''
            self.cursor.execute(query)
            users = self.cursor.fetchall()
    
            if not users:
                QMessageBox.information(self, "No Data", "No users found to export.")
                return
    
            school_info = self.get_school_info()
            title = f"{school_info['name']} - Users Export"
    
            self.export_with_green_header(
                data=users,
                headers=["ID", "Username", "Full Name", "Role", "Status", "Position", "Lock Status"],
                filename_prefix="users",
                title=title
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export users: {str(e)}")
        
    def refresh_data(self):
        """Refresh all data"""
        try:
            self.load_users()
            self.load_teachers()
            QMessageBox.information(self, "Success", "Data refreshed successfully!")
        except Exception as e:  # or mysql.connector.Error if using MySQL
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {e}")


    def closeEvent(self, event):
        """Handle close event to clean up database connection"""
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'db_connection'):
                self.db_connection.close()
        except:
            pass
        event.accept()

    def __del__(self):
        """Close database connection when object is destroyed"""
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'db_connection'):
                self.db_connection.close()
        except:
            pass