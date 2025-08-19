import sys
import os
import csv
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, QMenu
)
from PySide6.QtGui import QFont, QPalette, QIcon
from PySide6.QtCore import Qt, Signal, QSize

import mysql.connector
from mysql.connector import Error

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection
from utils.auth import hash_password

class UsersForm(QWidget):
    user_selected = Signal(int)  # Signal emitted when a user is selected
    
    def __init__(self, parent=None, user_session: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.user_session = user_session
        self.current_user_id = None
        self.current_teacher_id = None
        self.password_visible = False
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

    def setup_styling(self):
        """Set up modern professional styling"""
        # Define color palette
        self.colors = {
            'primary': '#2563eb',        # Blue
            'primary_dark': '#1d4ed8',   # Darker blue
            'secondary': '#64748b',      # Slate
            'success': '#059669',        # Emerald
            'warning': '#d97706',        # Amber
            'danger': '#dc2626',         # Red
            'info': '#0891b2',          # Cyan
            'light': '#f8fafc',         # Very light gray
            'dark': '#0f172a',          # Very dark blue
            'border': '#e2e8f0',        # Light border
            'text_primary': '#1e293b',   # Dark slate
            'text_secondary': '#64748b', # Medium slate
            'background': '#ffffff',     # White
            'surface': '#f1f5f9',       # Light surface
            'table_header': '#10b981',   # Nice green for table headers
            'table_header_dark': '#059669'  # Darker green for hover
        }
        
        # Set up fonts
        self.fonts = {
            'label': QFont("Arial", 14, QFont.Weight.Bold),
            'entry': QFont("Arial", 14),
            'section': QFont("Arial", 18, QFont.Weight.Bold),
            'button': QFont("Arial", 12, QFont.Weight.Bold),
            'header': QFont("Arial", 18, QFont.Weight.Bold),
            'table': QFont("Tahoma", 12),
            'table_header': QFont("Tahoma", 13, QFont.Weight.Bold)
        }

    def setup_ui(self):
        """Setup the main UI with side-by-side layout"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left side - Form (smaller width)
        left_frame = QFrame()
        left_frame.setFixedWidth(400)
        left_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['background']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
            }}
        """)

        # Right side - Table (larger width)
        right_frame = QFrame()
        right_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['background']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
            }}
        """)

        main_layout.addWidget(left_frame)
        main_layout.addWidget(right_frame, 1)  # Give more space to table

        self.setup_form_section(left_frame)
        self.setup_table_section(right_frame)

    def setup_form_section(self, parent):
        """Setup the form section"""
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_label = QLabel("User Management")
        header_label.setFont(self.fonts['header'])
        header_label.setStyleSheet(f"color: {self.colors['primary']}; margin-bottom: 10px;")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        form_layout.setSpacing(10)

        # Username
        self.username_entry = QLineEdit()
        self.username_entry.setFont(self.fonts['entry'])
        self.setup_entry_style(self.username_entry)
        form_layout.addRow(self.create_label("Username*:"), self.username_entry)

        # Full Name
        self.fullname_entry = QLineEdit()
        self.fullname_entry.setFont(self.fonts['entry'])
        self.setup_entry_style(self.fullname_entry)
        form_layout.addRow(self.create_label("Full Name*:"), self.fullname_entry)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "Headteacher", "Teacher", "Finance", "Subject Head", "Staff"])
        self.role_combo.setCurrentText("Teacher")
        self.role_combo.setFont(self.fonts['entry'])
        self.setup_combo_style(self.role_combo)
        self.role_combo.currentTextChanged.connect(self.on_role_change)
        form_layout.addRow(self.create_label("Role*:"), self.role_combo)

        # Teacher selection
        self.teacher_combo = QComboBox()
        self.teacher_combo.setFont(self.fonts['entry'])
        self.setup_combo_style(self.teacher_combo)
        self.teacher_combo.currentTextChanged.connect(self.on_teacher_select)
        self.teacher_combo_row = form_layout.rowCount()
        form_layout.addRow(self.create_label("Link to Teacher:"), self.teacher_combo)

        # Position
        self.position_entry = QLineEdit()
        self.position_entry.setFont(self.fonts['entry'])
        self.position_entry.setEnabled(False)
        self.setup_entry_style(self.position_entry)
        self.position_row = form_layout.rowCount()
        form_layout.addRow(self.create_label("Position:"), self.position_entry)

        # Password field with toggle
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        
        self.password_entry = QLineEdit()
        self.password_entry.setFont(self.fonts['entry'])
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.setup_entry_style(self.password_entry)
        
        self.toggle_password_btn = QPushButton("👁")
        self.toggle_password_btn.setFixedSize(30, 30)
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        self.setup_icon_button_style(self.toggle_password_btn)
        
        password_layout.addWidget(self.password_entry)
        password_layout.addWidget(self.toggle_password_btn)
        
        form_layout.addRow(self.create_label("Password*:"), password_container)

        # Status
        self.status_label = QLabel("New User")
        self.status_label.setFont(self.fonts['entry'])
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
        form_layout.addRow(self.create_label("Status:"), self.status_label)

        layout.addWidget(form_group)

        # Load teachers and set initial state
        self.load_teachers()
        self.on_role_change("Teacher")

        # Buttons
        self.setup_buttons(layout)

    def create_label(self, text):
        """Create a styled label"""
        label = QLabel(text)
        label.setFont(self.fonts['label'])
        label.setStyleSheet(f"color: {self.colors['text_primary']};")
        return label

    def setup_entry_style(self, entry):
        """Setup consistent entry styling"""
        entry.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px;
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {self.colors['primary']};
            }}
            QLineEdit:disabled {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_secondary']};
            }}
        """)

    def setup_combo_style(self, combo):
        """Setup consistent combobox styling"""
        combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px;
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                min-height: 20px;
            }}
            QComboBox:focus {{
                border-color: {self.colors['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
        """)

    def setup_icon_button_style(self, button):
        """Setup icon button styling"""
        button.setStyleSheet(f"""
            QPushButton {{
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['border']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['secondary']};
            }}
        """)

    def setup_buttons(self, layout):
        """Setup buttons in organized rows"""
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

        # Row 1 - Primary actions
        row1_layout = QHBoxLayout()
        
        self.add_btn = self.create_button("Add User", self.colors['success'], self.add_user)
        self.update_btn = self.create_button("Update", self.colors['primary'], self.update_user)
        self.clear_btn = self.create_button("Clear", self.colors['secondary'], self.clear_form)
        
        row1_layout.addWidget(self.add_btn)
        row1_layout.addWidget(self.update_btn)
        row1_layout.addWidget(self.clear_btn)
        buttons_layout.addLayout(row1_layout)

        # Row 2 - Status actions
        row2_layout = QHBoxLayout()
        
        self.deactivate_btn = self.create_button("Deactivate", self.colors['danger'], self.deactivate_user)
        self.reactivate_btn = self.create_button("Reactivate", self.colors['info'], self.reactivate_user)
        
        row2_layout.addWidget(self.deactivate_btn)
        row2_layout.addWidget(self.reactivate_btn)
        row2_layout.addStretch()
        buttons_layout.addLayout(row2_layout)

        # Row 3 - Other actions
        row3_layout = QHBoxLayout()
        
        self.reset_btn = self.create_button("Reset Pwd", self.colors['warning'], self.reset_password)
        self.delete_btn = self.create_button("Delete", '#8B0000', self.delete_user)
        
        row3_layout.addWidget(self.reset_btn)
        row3_layout.addWidget(self.delete_btn)
        row3_layout.addStretch()
        buttons_layout.addLayout(row3_layout)

        layout.addWidget(buttons_group)
        layout.addStretch()

    def create_button(self, text, color, callback):
        """Create a styled button"""
        button = QPushButton(text)
        button.setFont(self.fonts['button'])
        button.clicked.connect(callback)
        button.setMinimumHeight(35)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color_brightness(color, -20)};
            }}
            QPushButton:pressed {{
                background-color: {self.adjust_color_brightness(color, -40)};
            }}
        """)
        return button

    def adjust_color_brightness(self, color, amount):
        """Adjust color brightness by amount (positive = lighter, negative = darker)"""
        # Simple color adjustment - in a real app you might want more sophisticated color manipulation
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
        search_layout = QHBoxLayout(search_frame)
        
        search_label = QLabel("Search Users:")
        search_label.setFont(self.fonts['label'])
        search_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        
        self.search_entry = QLineEdit()
        self.search_entry.setFont(self.fonts['entry'])
        self.search_entry.setPlaceholderText("Enter username or full name...")
        self.setup_entry_style(self.search_entry)
        
        search_btn = self.create_button("Search", self.colors['primary'], self.search_users)
        clear_search_btn = self.create_button("Clear", self.colors['secondary'], self.clear_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(clear_search_btn)
        
        layout.addWidget(search_frame)

        # Table
        self.users_table = QTableWidget()
        self.setup_table()
        layout.addWidget(self.users_table)

    def setup_table(self):
        """Setup the users table"""
        headers = ["ID", "Username", "Full Name", "Role", "Position", "Status"]
        self.users_table.setColumnCount(len(headers))
        self.users_table.setHorizontalHeaderLabels(headers)
        
        # Set table properties
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSortingEnabled(True)
        
        # Set fonts
        self.users_table.setFont(self.fonts['table'])
        
        # Header styling
        header = self.users_table.horizontalHeader()
        header.setFont(self.fonts['table_header'])
        header.setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {self.colors['table_header']};
                color: white;
                padding: 8px;
                border: 1px solid {self.colors['table_header_dark']};
                font-weight: bold;
            }}
            QHeaderView::section:hover {{
                background-color: {self.colors['table_header_dark']};
            }}
        """)
        
        # Table styling
        self.users_table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {self.colors['border']};
                background-color: {self.colors['background']};
                alternate-background-color: {self.colors['light']};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.colors['border']};
            }}
            QTableWidget::item:selected {{
                background-color: {self.colors['primary']};
                color: white;
            }}
        """)
        
        # Resize columns
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        
        # Connect selection signal
        self.users_table.itemSelectionChanged.connect(self.on_user_select)

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

    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.password_visible:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_btn.setText("👁")
            self.password_visible = False
        else:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_btn.setText("🙈")
            self.password_visible = True

    def load_users(self):
        """Load all users from database with teacher position info"""
        try:
            query = '''
                SELECT u.id, u.username, u.full_name, u.role, u.is_active,
                       COALESCE(t.position, 'N/A') as position
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
        """Update the user table with new data"""
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            # Convert is_active boolean to status text
            status = "Active" if user[4] else "Inactive"
            position = user[5] if len(user) > 5 and user[5] else "N/A"
            
            row_data = [str(user[0]), user[1], user[2], user[3], position, status]
            
            for col, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
                
                # Color code status
                if col == 5:  # Status column
                    if data == "Active":
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['success'])
                    else:
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['danger'])
                
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
                
            # Load user data from database with teacher info
            query = '''
                SELECT u.id, u.username, u.full_name, u.role, u.is_active,
                       t.id as teacher_id, t.position, t.teacher_id_code
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
                
                # Update status display
                status = "Active" if user_data[4] else "Inactive"
                status_color = self.colors['success'] if user_data[4] else self.colors['danger']
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
                
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
                       COALESCE(t.position, 'N/A') as position
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
        """Add new user to database"""
        username = self.username_entry.text().strip()
        full_name = self.fullname_entry.text().strip()
        role = self.role_combo.currentText().strip()
        password = self.password_entry.text().strip()

        if not all([username, full_name, password]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return

        try:
            password_hash = hash_password(password)
            
            query = """
                INSERT INTO users (username, full_name, role, password_hash, is_active)
                VALUES (%s, %s, %s, %s, 1)
            """
            self.cursor.execute(query, (username, full_name, role, password_hash))
            self.db_connection.commit()
            
            QMessageBox.information(self, "Success", "User added successfully!")
            self.clear_form()
            self.load_users()
            self.load_teachers()  # Refresh teacher dropdown
            
        except mysql.connector.IntegrityError:
            QMessageBox.critical(self, "Error", "Username already exists.")
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to add user: {e}")

    def update_user(self):
        """Update existing user"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for update")
            return

        username = self.username_entry.text().strip()
        full_name = self.fullname_entry.text().strip()
        role = self.role_combo.currentText().strip()

        if not all([username, full_name]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return

        try:
            query = """
                UPDATE users SET username=%s, full_name=%s, role=%s
                WHERE id=%s
            """
            self.cursor.execute(query, (username, full_name, role, self.current_user_id))
            self.db_connection.commit()
            
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

        password = self.password_entry.text().strip()
        if not password:
            QMessageBox.warning(self, "Warning", "Please enter a new password.")
            return

        try:
            hashed = hash_password(password)
            query = "UPDATE users SET password_hash=%s WHERE id=%s"
            self.cursor.execute(query, (hashed, self.current_user_id))
            self.db_connection.commit()
            
            QMessageBox.information(self, "Success", "Password reset successfully!")
            self.password_entry.clear()  # Clear password field
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to reset password: {e}")

    def deactivate_user(self):
        """Deactivate user"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Warning", "Please select a user to deactivate.")
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
                
                QMessageBox.information(self, "Success", "User reactivated successfully!")
                self.clear_form()
                self.load_users()
            except Error as e:
                QMessageBox.critical(self, "Error", f"Failed to reactivate user: {e}")

    def delete_user(self):
        """Delete user permanently"""
        if not self.current_user_id:
            QMessageBox.warning(self, "Warning", "Please select a user to delete.")
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
                query = "DELETE FROM users WHERE id=%s"
                self.cursor.execute(query, (self.current_user_id,))
                self.db_connection.commit()
                
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
        
        # Reset password visibility
        if self.password_visible:
            self.toggle_password_visibility()
        
        # Reset status
        self.status_label.setText("New User")
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
        
        # Reset current selections
        self.current_user_id = None
        self.current_teacher_id = None
        
        # Handle role change to show/hide teacher fields
        self.on_role_change("Teacher")

    def validate_form_data(self):
        """Validate form data before submission"""
        username = self.username_entry.text().strip()
        full_name = self.fullname_entry.text().strip()
        role = self.role_combo.currentText().strip()
        password = self.password_entry.text().strip()

        if not username:
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return False
        
        if len(username) < 3:
            QMessageBox.warning(self, "Validation Error", "Username must be at least 3 characters long.")
            return False
            
        if not full_name:
            QMessageBox.warning(self, "Validation Error", "Full Name is required.")
            return False
            
        valid_roles = ["Admin", "Headteacher", "Teacher", "Finance", "Subject Head", "Staff"]
        if not role or role not in valid_roles:
            QMessageBox.warning(self, "Validation Error", "Please select a valid role.")
            return False
            
        # Password validation for new users
        if not self.current_user_id and not password:
            QMessageBox.warning(self, "Validation Error", "Password is required for new users.")
            return False
            
        if password and len(password) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters long.")
            return False

        return True

    def get_user_stats(self):
        """Get user statistics for display"""
        try:
            # Total users
            self.cursor.execute("SELECT COUNT(*) FROM users")
            total_users = self.cursor.fetchone()[0]
            
            # Active users
            self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active_users = self.cursor.fetchone()[0]
            
            # Users by role
            self.cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            role_stats = dict(self.cursor.fetchall())
            
            return {
                'total': total_users,
                'active': active_users,
                'inactive': total_users - active_users,
                'roles': role_stats
            }
        except Error as e:
            print(f"Error getting user stats: {e}")
            return {'total': 0, 'active': 0, 'inactive': 0, 'roles': {}}

    def export_users(self):
        """Export users to CSV file"""
        try:
            # Ask user for save location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Users to CSV",
                "users_export.csv",
                "CSV files (*.csv);;All files (*.*)"
            )
            
            if filename:
                query = '''
                    SELECT u.id, u.username, u.full_name, u.role, 
                           CASE WHEN u.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status,
                           COALESCE(t.position, 'N/A') as position,
                           u.created_at
                    FROM users u
                    LEFT JOIN teachers t ON t.full_name = u.full_name
                    ORDER BY u.username
                '''
                self.cursor.execute(query)
                users = self.cursor.fetchall()
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write header
                    writer.writerow(['ID', 'Username', 'Full Name', 'Role', 'Status', 'Position', 'Created At'])
                    # Write data
                    writer.writerows(users)
                
                QMessageBox.information(self, "Success", f"Users exported successfully to {filename}")
                
        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to export users: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export users: {e}")

    def refresh_data(self):
        """Refresh all data"""
        try:
            self.load_users()
            self.load_teachers()
            QMessageBox.information(self, "Success", "Data refreshed successfully!")
        except Error as e:
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

