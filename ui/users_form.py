import sys
import os
import traceback
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, 
    QTabWidget, QMenu, QCheckBox, QDateEdit, QTextEdit, QApplication,
    QSplitter, QListWidget, QListWidgetItem, QProgressDialog
)
from PySide6.QtGui import QFont, QPalette, QIcon, QPixmap, QPainter, QAction, QColor, QTextCursor
from PySide6.QtCore import Qt, Signal, QSize, QDate, QTimer, QDateTime
import mysql.connector
from mysql.connector import Error

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection
from utils.auth import hash_password
from utils.permissions import has_permission
from ui.audit_base_form import AuditBaseForm


class SearchableComboBox(QComboBox):
    """Enhanced ComboBox with search functionality"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.original_data = []  # Store (display_text, value) pairs
        self.lineEdit().textEdited.connect(self.filter_values)
        self.lineEdit().returnPressed.connect(self.on_return_pressed)
        self.setMaxVisibleItems(10)
        
    def setData(self, data_list):
        """Set the data for the combobox - list of (display_text, value) tuples"""
        self.original_data = data_list
        self.clear()
        for display, value in data_list:
            self.addItem(display, value)
        
    def filter_values(self, text):
        """Filter values based on typed text"""
        if not text:
            self.clear()
            for display, value in self.original_data:
                self.addItem(display, value)
            self.showPopup()
            return
            
        filtered_data = [
            (display, value) for display, value in self.original_data 
            if text.lower() in display.lower()
        ]
        
        self.clear()
        for display, value in filtered_data:
            self.addItem(display, value)
        
        if filtered_data:
            self.showPopup()
        
    def on_return_pressed(self):
        """Handle return pressed to select the first item"""
        if self.count() > 0:
            self.setCurrentIndex(0)
            self.hidePopup()

    def getCurrentValue(self):
        """Get the current selected value (not display text)"""
        current_index = self.currentIndex()
        if current_index >= 0:
            return self.itemData(current_index)
        return None


class UsersForm(AuditBaseForm):
    user_selected = Signal(int)
    
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.current_user_id = None
        self.current_teacher_id = None
        self.password_visible = False
        self.confirm_password_visible = False
        self.teacher_data = {}
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor()
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        self.setup_ui()
        self.load_data()
        self.apply_permissions()
        
    def setup_ui(self):
        """Setup the main UI with side-by-side layout"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
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
        left_frame.setMinimumWidth(450)
        left_frame.setMaximumWidth(500)
    
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
        
        # Setup form and table sections
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
        header_label.setFont(self.fonts['section'])
        header_label.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
            color: white;
            margin: 10px 0;
            padding: 10px;
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
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
    
        # Username
        self.username_entry = QLineEdit()
        self.username_entry.setFont(self.fonts['entry'])
        self.username_entry.setPlaceholderText("Enter unique username")
        self.setup_entry_style(self.username_entry)
        form_layout.addRow(self.create_styled_label("Username*:"), self.username_entry)
    
        # Full Name
        self.fullname_entry = QLineEdit()
        self.fullname_entry.setFont(self.fonts['entry'])
        self.fullname_entry.setPlaceholderText("Enter full name")
        self.setup_entry_style(self.fullname_entry)
        form_layout.addRow(self.create_styled_label("Full Name*:"), self.fullname_entry)
    
        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "Headteacher", "Teacher", "Finance", "Subject Head", "Staff"])
        self.role_combo.setCurrentText("Teacher")
        self.role_combo.setFont(self.fonts['entry'])
        self.setup_combo_style(self.role_combo)
        self.role_combo.currentTextChanged.connect(self.on_role_change)
        form_layout.addRow(self.create_styled_label("Role*:"), self.role_combo)
    
        # Teacher selection
        self.teacher_combo = SearchableComboBox()
        self.teacher_combo.setFont(self.fonts['entry'])
        self.teacher_combo.setPlaceholderText("Select teacher to link")
        self.setup_combo_style(self.teacher_combo)
        self.teacher_combo.currentTextChanged.connect(self.on_teacher_select)
        form_layout.addRow(self.create_styled_label("Link to Teacher:"), self.teacher_combo)
    
        # Position
        self.position_entry = QLineEdit()
        self.position_entry.setFont(self.fonts['entry'])
        self.position_entry.setEnabled(False)
        self.position_entry.setPlaceholderText("Auto-filled from teacher record")
        self.setup_entry_style(self.position_entry)
        form_layout.addRow(self.create_styled_label("Position:"), self.position_entry)
    
        # Password field with toggle
        password_label = self.create_styled_label("Password*:")
        password_label.setToolTip("Password must be at least 8 characters long")
        
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        
        self.password_entry = QLineEdit()
        self.password_entry.setFont(self.fonts['entry'])
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setPlaceholderText("Enter password (min 8 characters)")
        self.setup_entry_style(self.password_entry)
        
        self.toggle_password_btn = QPushButton("👁")
        self.toggle_password_btn.setFixedSize(30, 30)
        self.toggle_password_btn.setToolTip("Show/hide password")
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        self.setup_icon_button_style(self.toggle_password_btn)
        
        password_layout.addWidget(self.password_entry)
        password_layout.addWidget(self.toggle_password_btn)
        
        form_layout.addRow(password_label, password_container)
    
        # Confirm Password field with toggle
        confirm_password_label = self.create_styled_label("Confirm Password*:")
        
        confirm_password_container = QWidget()
        confirm_password_layout = QHBoxLayout(confirm_password_container)
        confirm_password_layout.setContentsMargins(0, 0, 0, 0)
        
        self.confirm_password_entry = QLineEdit()
        self.confirm_password_entry.setFont(self.fonts['entry'])
        self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_entry.setPlaceholderText("Re-enter password to confirm")
        self.setup_entry_style(self.confirm_password_entry)
        
        self.toggle_confirm_password_btn = QPushButton("👁")
        self.toggle_confirm_password_btn.setFixedSize(30, 30)
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
        form_layout.addRow(self.create_styled_label("Status:"), self.status_label)
    
        # Security status
        self.failed_attempts_label = QLabel("0")
        self.failed_attempts_label.setFont(self.fonts['entry'])
        self.failed_attempts_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        form_layout.addRow(self.create_styled_label("Failed Login Attempts:"), self.failed_attempts_label)
    
        self.lock_status_label = QLabel("Not Locked")
        self.lock_status_label.setFont(self.fonts['entry'])
        self.lock_status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
        form_layout.addRow(self.create_styled_label("Account Lock Status:"), self.lock_status_label)
    
        layout.addWidget(form_group)
    
        # Load teachers and set initial state
        self.load_teachers()
        self.on_role_change("Teacher")
    
        # Buttons
        self.setup_action_buttons(layout)
        
        # Add some stretch to ensure proper scrolling
        layout.addStretch()

    def create_styled_label(self, text):
        """Create a styled label"""
        label = QLabel(text)
        label.setFont(self.fonts['label'])
        label.setStyleSheet(f"color: {self.colors['text_primary']};")
        return label

    def setup_entry_style(self, entry):
        """Setup consistent entry styling"""
        entry.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: {self.colors['input_background']};
                color: {self.colors['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {self.colors['input_focus']};
                background-color: {self.colors['input_background']};
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
        """Setup consistent combobox styling"""
        combo.setStyleSheet(f"""
            QComboBox {{
                border: 2px solid {self.colors['input_border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: {self.colors['input_background']};
                color: {self.colors['text_primary']};
            }}
            QComboBox:focus {{
                border-color: {self.colors['input_focus']};
                background-color: {self.colors['input_background']};
            }}
            QComboBox:disabled {{
                background-color: #f1f5f9;
                color: #64748b;
                border-color: #cbd5e1;
            }}
        """)
    
    def setup_icon_button_style(self, button):
        """Setup icon button styling"""
        button.setStyleSheet(f"""
            QPushButton {{
                border: 2px solid {self.colors['border']};
                border-radius: 4px;
                padding: 4px;
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
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

    def setup_action_buttons(self, layout):
        """Setup action buttons with icons using inherited styling"""
        buttons_group = QGroupBox("Actions")
        buttons_group.setFont(self.fonts['label'])
        buttons_layout = QVBoxLayout(buttons_group)
    
        # Create all buttons
        self.save_btn = QPushButton("Add User")
        self.save_btn.setIcon(QIcon("static/icons/add.png"))
        self.save_btn.setIconSize(QSize(20, 20))
        self.save_btn.setProperty("class", "success")
        self.save_btn.setFont(self.fonts['button'])
        self.save_btn.clicked.connect(self.add_user)
        
        self.update_btn = QPushButton("Update")
        self.update_btn.setIcon(QIcon("static/icons/update.png"))
        self.update_btn.setIconSize(QSize(20, 20))
        self.update_btn.setProperty("class", "primary")
        self.update_btn.setFont(self.fonts['button'])
        self.update_btn.clicked.connect(self.update_user)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(QIcon("static/icons/clear.png"))
        self.clear_btn.setIconSize(QSize(20, 20))
        self.clear_btn.setProperty("class", "secondary")
        self.clear_btn.setFont(self.fonts['button'])
        self.clear_btn.clicked.connect(self.clear_form)
        
        self.deactivate_btn = QPushButton("Deactivate")
        self.deactivate_btn.setIcon(QIcon("static/icons/deactivate.png"))
        self.deactivate_btn.setIconSize(QSize(20, 20))
        self.deactivate_btn.setProperty("class", "warning")
        self.deactivate_btn.setFont(self.fonts['button'])
        self.deactivate_btn.clicked.connect(self.deactivate_user)
        
        self.reactivate_btn = QPushButton("Reactivate")
        self.reactivate_btn.setIcon(QIcon("static/icons/reactivate.png"))
        self.reactivate_btn.setIconSize(QSize(20, 20))
        self.reactivate_btn.setProperty("class", "info")
        self.reactivate_btn.setFont(self.fonts['button'])
        self.reactivate_btn.clicked.connect(self.reactivate_user)
        
        self.reset_pwd_btn = QPushButton("Reset Pwd")
        self.reset_pwd_btn.setIcon(QIcon("static/icons/reset.png"))
        self.reset_pwd_btn.setIconSize(QSize(20, 20))
        self.reset_pwd_btn.setProperty("class", "warning")
        self.reset_pwd_btn.setFont(self.fonts['button'])
        self.reset_pwd_btn.clicked.connect(self.reset_password)
        
        self.unlock_btn = QPushButton("Unlock")
        self.unlock_btn.setIcon(QIcon("static/icons/unlock.png"))
        self.unlock_btn.setIconSize(QSize(20, 20))
        self.unlock_btn.setProperty("class", "info")
        self.unlock_btn.setFont(self.fonts['button'])
        self.unlock_btn.clicked.connect(self.unlock_account)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setIcon(QIcon("static/icons/delete.png"))
        self.delete_btn.setIconSize(QSize(20, 20))
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setFont(self.fonts['button'])
        self.delete_btn.clicked.connect(self.delete_user)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        self.refresh_btn.setIconSize(QSize(20, 20))
        self.refresh_btn.setProperty("class", "info")
        self.refresh_btn.setFont(self.fonts['button'])
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.setIcon(QIcon("static/icons/export.png"))
        self.export_btn.setIconSize(QSize(20, 20))
        self.export_btn.setProperty("class", "primary")
        self.export_btn.setFont(self.fonts['button'])
        self.export_btn.clicked.connect(self.export_users)
    
        # Arrange in rows with equal width
        row1_layout = QHBoxLayout()
        for btn in [self.save_btn, self.update_btn, self.clear_btn]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row1_layout.addWidget(btn)
        buttons_layout.addLayout(row1_layout)
    
        row2_layout = QHBoxLayout()
        for btn in [self.deactivate_btn, self.reactivate_btn, self.reset_pwd_btn]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row2_layout.addWidget(btn)
        buttons_layout.addLayout(row2_layout)
    
        row3_layout = QHBoxLayout()
        for btn in [self.unlock_btn, self.delete_btn, self.refresh_btn]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row3_layout.addWidget(btn)
        buttons_layout.addLayout(row3_layout)
        
        row4_layout = QHBoxLayout()
        self.export_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row4_layout.addWidget(self.export_btn)
        buttons_layout.addLayout(row4_layout)
    
        layout.addWidget(buttons_group)

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
        
        self.search_entry = QLineEdit()
        self.search_entry.setFont(self.fonts['entry'])
        self.search_entry.setPlaceholderText("Enter username or full name...")
        self.setup_entry_style(self.search_entry)
        self.search_entry.textChanged.connect(self.on_search_changed)
        
        search_btn = QPushButton("Search")
        search_btn.setIcon(QIcon("static/icons/search.png"))
        search_btn.setIconSize(QSize(16, 16))
        search_btn.setProperty("class", "primary")
        search_btn.setFont(self.fonts['button'])
        search_btn.clicked.connect(self.search_users)
        
        clear_search_btn = QPushButton("Clear")
        clear_search_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_search_btn.setIconSize(QSize(16, 16))
        clear_search_btn.setProperty("class", "secondary")
        clear_search_btn.setFont(self.fonts['button'])
        clear_search_btn.clicked.connect(self.clear_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(clear_search_btn)
        
        layout.addWidget(search_frame)
    
        # Table
        self.users_table = QTableWidget()
        self.setup_table()
        layout.addWidget(self.users_table)
        
        # Table info
        self.table_info = QLabel("Total users: 0")
        self.table_info.setStyleSheet(f"color: {self.colors['text_secondary']}; font-style: italic;")
        layout.addWidget(self.table_info)

    def setup_table(self):
        """Setup the users table"""
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
        
        # Header styling
        header = self.users_table.horizontalHeader()
        header.setFont(self.fonts['table_header'])
        header.setStyleSheet(f"""
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }}
        """)
        
        # Resize columns
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.users_table.setColumnWidth(0, 60)
        
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect selection signal
        self.users_table.itemSelectionChanged.connect(self.on_user_select)

    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_btn.setIcon(QIcon("static/icons/view.png"))  # eye icon
            self.toggle_password_btn.setIconSize(QSize(20, 20))
            self.toggle_password_btn.setText("")  # remove text
        else:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_btn.setIcon(QIcon("static/icons/lock.png"))  # lock icon
            self.toggle_password_btn.setIconSize(QSize(20, 20))
            self.toggle_password_btn.setText("")
    
    def toggle_confirm_password_visibility(self):
        """Toggle confirm password visibility"""
        self.confirm_password_visible = not self.confirm_password_visible
        if self.confirm_password_visible:
            self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_confirm_password_btn.setIcon(QIcon("static/icons/view.png"))
            self.toggle_confirm_password_btn.setIconSize(QSize(20, 20))
            self.toggle_confirm_password_btn.setText("")
        else:
            self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_confirm_password_btn.setIcon(QIcon("static/icons/lock.png"))
            self.toggle_confirm_password_btn.setIconSize(QSize(20, 20))
            self.toggle_confirm_password_btn.setText("")


    def load_data(self):
        """Load all necessary data"""
        try:
            self._ensure_connection()
            self.load_teachers()
            self.load_users()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")
        
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
            
            teacher_options = [("None - Manual Entry", None)]
            self.teacher_data = {}  # Store teacher data for lookup
            
            for teacher in available_teachers:
                teacher_id, full_name, position, teacher_code = teacher
                display_name = f"{full_name} ({teacher_code}) - {position or 'No Position'}"
                teacher_options.append((display_name, teacher_id))
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
                if display_name not in self.teacher_data:
                    teacher_options.append((display_name, teacher_id))
                    self.teacher_data[display_name] = {
                        'id': teacher_id,
                        'full_name': full_name,
                        'position': position or '',
                        'user_id': user_id
                    }
            
            self.teacher_combo.setData(teacher_options)
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
                
        # Update info label
        total_users = len(users)
        active_users = len([user for user in users if user[4]])
        self.table_info.setText(f"Total users: {total_users} (Active: {active_users})")

    def on_search_changed(self):
        """Handle search text changes with delay"""
        if hasattr(self, 'search_timer'):
            self.search_timer.stop()
        
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self.search_users)
        self.search_timer.setSingleShot(True)
        self.search_timer.start(300)
        
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
                
        except Error as e:
            error_msg = f"Error selecting user: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)

    def validate_form(self):
        """Validate form data before saving/updating"""
        if not self.username_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            self.username_entry.setFocus()
            return False
            
        if not self.fullname_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Full name is required.")
            self.fullname_entry.setFocus()
            return False
            
        if not self.password_entry.text().strip() and not self.current_user_id:
            QMessageBox.warning(self, "Validation Error", "Password is required for new users.")
            self.password_entry.setFocus()
            return False
            
        if self.password_entry.text() != self.confirm_password_entry.text():
            QMessageBox.warning(self, "Validation Error", "Password and confirmation do not match.")
            self.password_entry.setFocus()
            return False
            
        if len(self.password_entry.text()) < 8 and not self.current_user_id:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters long.")
            self.password_entry.setFocus()
            return False
            
        return True
        
    def check_for_duplicates(self, exclude_id=None):
        """Check if username already exists"""
        try:
            self._ensure_connection()
            username = self.username_entry.text().strip()
            
            query = "SELECT id, username FROM users WHERE username = %s"
            params = [username]
            
            if exclude_id:
                query += " AND id != %s"
                params.append(exclude_id)
                
            self.cursor.execute(query, params)
            existing = self.cursor.fetchone()
            
            if existing:
                return True, f"Username '{existing[1]}' already exists (ID: {existing[0]})"
                
            return False, "No duplicates found"
            
        except Exception as e:
            return True, f"Error checking duplicates: {e}"

    def add_user(self):
        """Add new user to database"""
        if not has_permission(self.user_session, 'create_user'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to create users.")
            return
            
        if not self.validate_form():
            return
    
        try:
            self._ensure_connection()
            
            # Check for duplicates
            is_duplicate, duplicate_msg = self.check_for_duplicates()
            if is_duplicate:
                QMessageBox.warning(self, "Duplicate Username", duplicate_msg)
                return
    
            username = self.username_entry.text().strip()
            full_name = self.fullname_entry.text().strip()
            role = self.role_combo.currentText().strip()
            password = self.password_entry.text().strip()
            school_id = self.user_session.get('school_id', 1) if self.user_session else 1
            
            password_hash = hash_password(password)
            
            # Insert new user
            query = '''
                INSERT INTO users (
                    school_id, username, full_name, role, password_hash, is_active
                ) VALUES (%s, %s, %s, %s, %s, 1)
            '''
            values = (
                school_id,
                username,
                full_name,
                role,
                password_hash
            )
            
            self.cursor.execute(query, values)
            user_id = self.cursor.lastrowid
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="CREATE",
                table_name="users",
                record_id=user_id,
                description=f"Created user '{username}' with role '{role}'"
            )
            
            QMessageBox.information(self, "Success", "User added successfully!")
            self.update_status("User added successfully!", "success")
            
            self.clear_form()
            self.load_users()
            self.load_teachers()
    
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to add user: {e}")
            self.update_status("Failed to add user", "danger")
            
    def update_user(self):
        """Update existing user"""
        if not has_permission(self.user_session, 'update_user'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to update users.")
            return
            
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for update")
            return
    
        if not self.validate_form():
            return
    
        try:
            self._ensure_connection()
            
            # Check for duplicates
            is_duplicate, duplicate_msg = self.check_for_duplicates(exclude_id=self.current_user_id)
            if is_duplicate:
                QMessageBox.warning(self, "Duplicate Username", duplicate_msg)
                return
    
            username = self.username_entry.text().strip()
            full_name = self.fullname_entry.text().strip()
            role = self.role_combo.currentText().strip()
            
            # Get old values for audit log
            old_query = "SELECT username, full_name, role FROM users WHERE id = %s"
            self.cursor.execute(old_query, (self.current_user_id,))
            old_values = self.cursor.fetchone()
            
            # Update user
            query = '''
                UPDATE users SET
                    username = %s, full_name = %s, role = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            '''
            values = (
                username,
                full_name,
                role,
                self.current_user_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="UPDATE",
                table_name="users",
                record_id=self.current_user_id,
                description=f"Updated user '{username}'. Old: {old_values[0]}/{old_values[1]}/{old_values[2]}, New: {username}/{full_name}/{role}"
            )
            
            QMessageBox.information(self, "Success", "User updated successfully!")
            self.update_status("User updated successfully!", "success")
            
            self.clear_form()
            self.load_users()
            self.load_teachers()

        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to update user: {e}")
            self.update_status("Failed to update user", "danger")
            
    def reset_password(self):
        """Reset user password"""
        if not has_permission(self.user_session, 'reset_password'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to reset passwords.")
            return
            
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for password reset")
            return
            
        password = self.password_entry.text().strip()
        confirm_password = self.confirm_password_entry.text().strip()

        # Validate password
        if not password:
            QMessageBox.warning(self, "Validation Error", "Please enter a new password.")
            self.password_entry.setFocus()
            return
            
        if len(password) < 8:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters long.")
            self.password_entry.setFocus()
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "Validation Error", "Password and confirmation do not match.")
            self.password_entry.setFocus()
            return
            
        try:
            self._ensure_connection()
            password_hash = hash_password(password)
            
            query = "UPDATE users SET password_hash = %s WHERE id = %s"
            self.cursor.execute(query, (password_hash, self.current_user_id))
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="UPDATE",
                table_name="users",
                record_id=self.current_user_id,
                description="Password reset by administrator"
            )
            
            QMessageBox.information(self, "Success", "Password reset successfully!")
            self.update_status("Password reset successfully!", "success")
            
            self.password_entry.clear()
            self.confirm_password_entry.clear()
            
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to reset password: {e}")
            self.update_status("Failed to reset password", "danger")
            
    def deactivate_user(self):
        """Deactivate user"""
        if not has_permission(self.user_session, 'deactivate_user'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to deactivate users.")
            return
            
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for deactivation")
            return
            
        # Get username for confirmation
        username = self.username_entry.text() or "this user"

        reply = QMessageBox.question(
            self,
            "Confirm Deactivation", 
            f"Are you sure you want to deactivate user '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            self._ensure_connection()
            
            # Deactivate the user
            query = "UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            self.cursor.execute(query, (self.current_user_id,))
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="UPDATE",
                table_name="users",
                record_id=self.current_user_id,
                description=f"Deactivated user '{username}'"
            )
            
            QMessageBox.information(self, "Success", "User deactivated successfully!")
            self.update_status("User deactivated successfully!", "success")
            
            self.clear_form()
            self.load_users()
            
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to deactivate user: {e}")
            self.update_status("Failed to deactivate user", "danger")
            
    def reactivate_user(self):
        """Reactivate user"""
        if not has_permission(self.user_session, 'reactivate_user'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to reactivate users.")
            return
            
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for reactivation")
            return
            
        # Get username for confirmation
        username = self.username_entry.text() or "this user"

        reply = QMessageBox.question(
            self,
            "Confirm Reactivation", 
            f"Are you sure you want to reactivate user '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            self._ensure_connection()
            
            # Reactivate the user
            query = "UPDATE users SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            self.cursor.execute(query, (self.current_user_id,))
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="UPDATE",
                table_name="users",
                record_id=self.current_user_id,
                description=f"Reactivated user '{username}'"
            )
            
            QMessageBox.information(self, "Success", "User reactivated successfully!")
            self.update_status("User reactivated successfully!", "success")
            
            self.clear_form()
            self.load_users()
            
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to reactivate user: {e}")
            self.update_status("Failed to reactivate user", "danger")
            
    def unlock_account(self):
        """Unlock user account"""
        if not has_permission(self.user_session, 'unlock_user'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to unlock user accounts.")
            return
            
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for unlocking")
            return
            
        # Get username for confirmation
        username = self.username_entry.text() or "this user"

        reply = QMessageBox.question(
            self,
            "Confirm Unlock", 
            f"Are you sure you want to unlock user account '{username}' and reset failed login attempts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            self._ensure_connection()
            
            # Unlock the account
            query = "UPDATE users SET failed_login_attempts = 0, account_locked_until = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            self.cursor.execute(query, (self.current_user_id,))
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="UPDATE",
                table_name="users",
                record_id=self.current_user_id,
                description=f"Unlocked user account '{username}' and reset failed login attempts"
            )
            
            QMessageBox.information(self, "Success", "User account unlocked successfully!")
            self.update_status("User account unlocked successfully!", "success")
            
            self.clear_form()
            self.load_users()
            
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to unlock user account: {e}")
            self.update_status("Failed to unlock user account", "danger")
            
    def delete_user(self):
        """Delete user permanently"""
        if not has_permission(self.user_session, 'delete_user'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete users.")
            return
            
        if not self.current_user_id:
            QMessageBox.warning(self, "Error", "No user selected for deletion")
            return
            
        # Get username for confirmation
        username = self.username_entry.text() or "this user"

        reply = QMessageBox.question(
            self,
            "Confirm Delete", 
            f"Are you sure you want to permanently delete user '{username}'?\n\nThis action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            self._ensure_connection()
            
            # Get user info for audit log before deletion
            user_query = "SELECT username, full_name, role FROM users WHERE id = %s"
            self.cursor.execute(user_query, (self.current_user_id,))
            user_info = self.cursor.fetchone()
            
            # Delete the user
            query = "DELETE FROM users WHERE id = %s"
            self.cursor.execute(query, (self.current_user_id,))
            self.db_connection.commit()
            
            # Log audit action using inherited method
            if user_info:
                self.log_audit_action(
                    action="DELETE",
                    table_name="users",
                    record_id=self.current_user_id,
                    description=f"Deleted user '{user_info[0]}' ({user_info[1]}) with role {user_info[2]}"
                )
            
            QMessageBox.information(self, "Success", "User deleted successfully!")
            self.update_status("User deleted successfully!", "success")
            
            self.clear_form()
            self.load_users()
            self.load_teachers()
            
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to delete user: {e}")
            self.update_status("Failed to delete user", "danger")
                
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
        
    def update_status(self, message, status_type="info"):
        """Update status label with inherited colors"""
        color_map = {
            "success": self.colors['success'],
            "danger": self.colors['danger'],
            "warning": self.colors['warning'],
            "info": self.colors['info']
        }
        
        color = color_map.get(status_type, self.colors['info'])
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    def refresh_data(self):
        """Refresh all data"""
        try:
            self._ensure_connection()
            self.db_connection.commit()
            
            self.load_teachers()
            self.load_users()
            
            self.update_status("All data refreshed successfully", "success")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {e}")
            self.update_status("Failed to refresh data", "danger")
            
    def export_users(self):
        """Export users to Excel using inherited export method"""
        try:
            self._ensure_connection()
            
            # Get data for export
            query = '''
                SELECT 
                    u.username,
                    u.full_name,
                    u.role,
                    COALESCE(t.position, 'N/A') as position,
                    CASE WHEN u.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status,
                    u.failed_login_attempts,
                    CASE 
                        WHEN u.account_locked_until IS NULL THEN 'Not Locked'
                        WHEN u.account_locked_until > NOW() THEN CONCAT('Locked until ', DATE_FORMAT(u.account_locked_until, '%Y-%m-%d %H:%i'))
                        ELSE 'Lock Expired'
                    END as lock_status,
                    u.created_at
                FROM users u
                LEFT JOIN teachers t ON t.full_name = u.full_name
                ORDER BY u.role, u.username
            '''
            self.cursor.execute(query)
            users = self.cursor.fetchall()
            
            if not users:
                QMessageBox.information(self, "No Data", "No users to export.")
                return

            headers = [
                'Username', 'Full Name', 'Role', 'Position', 'Status', 
                'Failed Attempts', 'Lock Status', 'Created Date'
            ]
            
            # Convert to proper format for export
            data = []
            for user in users:
                row = []
                for i, value in enumerate(user):
                    if i == 7 and value:  # created_at date
                        row.append(value.strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        row.append(str(value) if value is not None else '')
                data.append(row)

            # Use inherited school info method
            school_info = self.get_school_info()
            title = f"{school_info['name']} - Users Export"

            # Use inherited export method
            self.export_with_green_header(
                data=data,
                headers=headers,
                filename_prefix="users_export",
                title=title
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export users: {str(e)}")
            
    def apply_permissions(self):
        """Apply permissions to form controls using inherited user_session"""
        if not self.user_session:
            # Disable buttons if no session
            for btn in [self.save_btn, self.update_btn, self.delete_btn, 
                       self.deactivate_btn, self.reactivate_btn, self.reset_pwd_btn, 
                       self.unlock_btn]:
                btn.setEnabled(False)
            return
            
        # Set button states based on permissions
        self.save_btn.setEnabled(has_permission(self.user_session, 'create_user'))
        self.update_btn.setEnabled(has_permission(self.user_session, 'update_user'))
        self.delete_btn.setEnabled(has_permission(self.user_session, 'delete_user'))
        self.deactivate_btn.setEnabled(has_permission(self.user_session, 'deactivate_user'))
        self.reactivate_btn.setEnabled(has_permission(self.user_session, 'reactivate_user'))
        self.reset_pwd_btn.setEnabled(has_permission(self.user_session, 'reset_password'))
        self.unlock_btn.setEnabled(has_permission(self.user_session, 'unlock_user'))
        
        # Set tooltips
        self.save_btn.setToolTip("Add new user" if self.save_btn.isEnabled() else "Permission required: create_user")
        self.update_btn.setToolTip("Update selected user" if self.update_btn.isEnabled() else "Permission required: update_user")
        self.delete_btn.setToolTip("Delete selected user" if self.delete_btn.isEnabled() else "Permission required: delete_user")
        self.deactivate_btn.setToolTip("Deactivate selected user" if self.deactivate_btn.isEnabled() else "Permission required: deactivate_user")
        self.reactivate_btn.setToolTip("Reactivate selected user" if self.reactivate_btn.isEnabled() else "Permission required: reactivate_user")
        self.reset_pwd_btn.setToolTip("Reset password for selected user" if self.reset_pwd_btn.isEnabled() else "Permission required: reset_password")
        self.unlock_btn.setToolTip("Unlock selected user account" if self.unlock_btn.isEnabled() else "Permission required: unlock_user")

    def closeEvent(self, event):
        """Cleanup when the form is closed"""
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'db_connection') and self.db_connection:
                self.db_connection.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")
        
        event.accept()