import sys
import os
import csv
import traceback
import subprocess
import platform
from datetime import datetime
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, 
    QTabWidget, QMenu, QCheckBox, QDateEdit, QTextEdit, QApplication
)
from PySide6.QtGui import QFont, QPalette, QIcon, QPixmap, QPainter, QAction
from PySide6.QtCore import Qt, Signal, QSize, QDate
import mysql.connector
from mysql.connector import Error
from PIL import Image, ImageQt

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection

class TeachersForm(QWidget):
    teacher_selected = Signal(int)  # Signal emitted when a teacher is selected
    
    def __init__(self, parent=None, user_session: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.user_session = user_session
        self.current_teacher_id = None
        self.photo_path = None
        self.teacher_data = {}
        
        # Set up modern styling
        self.setup_styling()
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True)
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        # Ensure photos directory exists
        self.photos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'photos', 'teachers')
        os.makedirs(self.photos_dir, exist_ok=True)
        
        self.setup_ui()
        self.load_teachers()
        self.load_schools()

    def setup_styling(self):
        """Set up modern QSS styling"""
        self.setStyleSheet("""
            /* Main container styling */
            QWidget {
                background-color: #f5f5f5;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* Tab widget styling */
            QTabWidget::pane {
                border: 2px solid #c0c0c0;
                background-color: white;
                border-radius: 8px;
            }
            
            QTabWidget::tab-bar {
                alignment: left;
            }
            
            QTabBar::tab {
                background-color: #e1e1e1;
                border: 2px solid #c0c0c0;
                border-bottom-color: #c0c0c0;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                min-width: 120px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 14px;
                color: #555555;
            }
            
            QTabBar::tab:selected {
                background-color: #4472C4;
                color: white;
                border-bottom-color: #4472C4;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #d0d0d0;
            }
            
            /* Group box styling */
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: white;
                color: #2c3e50;
            }
            
            /* Label styling */
            QLabel {
                font-size: 14px;
                font-weight: 500;
                color: #2c3e50;
                padding: 2px;
            }
            
            /* Entry field styling */
            QLineEdit, QComboBox, QDateEdit {
                padding: 8px 12px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
                min-height: 20px;
            }
            
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
            
            QLineEdit[readOnly="true"] {
                background-color: #ecf0f1;
                color: #7f8c8d;
            }
            
            /* ComboBox dropdown styling */
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #7f8c8d;
            }
            
            /* Button styling */
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
                min-height: 35px;
            }
            
            QPushButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton:pressed {
                background-color: #21618c;
            }
            
            /* Specific button colors */
            QPushButton[class="success"] {
                background-color: #27ae60;
            }
            
            QPushButton[class="success"]:hover {
                background-color: #229954;
            }
            
            QPushButton[class="danger"] {
                background-color: #e74c3c;
            }
            
            QPushButton[class="danger"]:hover {
                background-color: #c0392b;
            }
            
            QPushButton[class="warning"] {
                background-color: #f39c12;
            }
            
            QPushButton[class="warning"]:hover {
                background-color: #e67e22;
            }
            
            QPushButton[class="info"] {
                background-color: #8e44ad;
            }
            
            QPushButton[class="info"]:hover {
                background-color: #7d3c98;
            }
            
            /* Table styling */
            QTableWidget {
                gridline-color: #bdc3c7;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #3498db;
                selection-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                font-size: 13px;
            }
            
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 10px 8px;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }
            
            QHeaderView::section:hover {
                background-color: #2c3e50;
            }
            
            /* Checkbox styling */
            QCheckBox {
                font-size: 14px;
                color: #2c3e50;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border-color: #27ae60;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMC42IDEuNEw0LjIgNy44IDEuNCA1IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
            
            /* Photo label styling */
            QLabel[class="photo"] {
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #7f8c8d;
                font-size: 12px;
                text-align: center;
                padding: 20px;
                min-width: 180px;
                min-height: 180px;
                max-width: 180px;
                max-height: 180px;
            }
            
            /* Scroll area styling */
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QScrollBar:vertical {
                background-color: #ecf0f1;
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }
            
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
            
            /* Frame styling */
            QFrame {
                border: none;
                background-color: transparent;
            }
        """)

    def setup_ui(self):
        """Set up the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.teacher_form_tab = QWidget()
        self.teacher_data_tab = QWidget()
        self.departments_tab = QWidget()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.teacher_form_tab, "Staff Form")
        self.tab_widget.addTab(self.teacher_data_tab, "Staff Data")
        self.tab_widget.addTab(self.departments_tab, "Departments")
        
        # Setup each tab
        self.setup_teacher_form_tab()
        self.setup_teacher_data_tab()
        self.setup_departments_tab()

    def setup_teacher_form_tab(self):
        """Set up the teacher form tab"""
        layout = QHBoxLayout(self.teacher_form_tab)
        
        # Left side - Form fields (70% width)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(800)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Title
        title_label = QLabel("Staff Information")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 20px;
                background-color: #ecf0f1;
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        left_layout.addWidget(title_label)
        
        # Create form sections
        self.create_personal_info_section(left_layout)
        self.create_contact_info_section(left_layout)
        self.create_employment_info_section(left_layout)
        
        left_scroll.setWidget(left_widget)
        layout.addWidget(left_scroll, 6)  # 60% width
        
        # Right side - Photo and actions (30% width)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_widget.setMaximumWidth(400)
        
        # Photo section
        self.create_photo_section(right_layout)
        
        # Action buttons
        self.create_action_buttons(right_layout)
        
        layout.addWidget(right_widget, 3)  # 30% width

    def create_personal_info_section(self, parent_layout):
        """Create personal information section"""
        personal_group = QGroupBox("Personal Information")
        personal_layout = QGridLayout(personal_group)
        
        # Row 1: Teacher ID, Salutation, First Name
        row = 0
        personal_layout.addWidget(QLabel("Staff ID Code:"), row, 0)
        self.teacher_id_entry = QLineEdit()
        personal_layout.addWidget(self.teacher_id_entry, row, 1)
        
        personal_layout.addWidget(QLabel("Salutation:"), row, 2)
        self.salutation_combo = QComboBox()
        self.salutation_combo.addItems(["Mr.", "Mrs.", "Ms.", "Dr.", "Prof."])
        personal_layout.addWidget(self.salutation_combo, row, 3)
        
        personal_layout.addWidget(QLabel("First Name:"), row, 4)
        self.first_name_entry = QLineEdit()
        self.first_name_entry.textChanged.connect(self.update_full_name)
        personal_layout.addWidget(self.first_name_entry, row, 5)
        
        # Row 2: Surname, Full Name, Gender
        row += 1
        personal_layout.addWidget(QLabel("Surname:"), row, 0)
        self.surname_entry = QLineEdit()
        self.surname_entry.textChanged.connect(self.update_full_name)
        personal_layout.addWidget(self.surname_entry, row, 1)
        
        personal_layout.addWidget(QLabel("Full Name:"), row, 2)
        self.full_name_entry = QLineEdit()
        self.full_name_entry.setReadOnly(True)
        personal_layout.addWidget(self.full_name_entry, row, 3)
        
        personal_layout.addWidget(QLabel("Gender:"), row, 4)
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Male", "Female", "Other"])
        personal_layout.addWidget(self.gender_combo, row, 5)
        
        # Row 3: Birth Date, National ID, Next of Kin
        row += 1
        personal_layout.addWidget(QLabel("Birth Date:"), row, 0)
        self.birth_date_edit = QDateEdit()
        self.birth_date_edit.setCalendarPopup(True)
        self.birth_date_edit.setDate(QDate.currentDate())
        personal_layout.addWidget(self.birth_date_edit, row, 1)
        
        personal_layout.addWidget(QLabel("National ID:"), row, 2)
        self.national_id_entry = QLineEdit()
        personal_layout.addWidget(self.national_id_entry, row, 3)
        
        personal_layout.addWidget(QLabel("Next of Kin:"), row, 4)
        self.next_of_kin_entry = QLineEdit()
        personal_layout.addWidget(self.next_of_kin_entry, row, 5)
        
        parent_layout.addWidget(personal_group)

    def create_contact_info_section(self, parent_layout):
        """Create contact information section"""
        contact_group = QGroupBox("Contact & Address Information")
        contact_layout = QGridLayout(contact_group)
        
        # Row 1: Email, Phone Contact 1
        row = 0
        contact_layout.addWidget(QLabel("Email:"), row, 0)
        self.email_entry = QLineEdit()
        contact_layout.addWidget(self.email_entry, row, 1, 1, 2)  # Span 2 columns
        
        contact_layout.addWidget(QLabel("Phone Contact 1:"), row, 3)
        self.phone_contact_1_entry = QLineEdit()
        contact_layout.addWidget(self.phone_contact_1_entry, row, 4)
        
        # Row 2: Day Phone, Home District
        row += 1
        contact_layout.addWidget(QLabel("Day Phone:"), row, 0)
        self.day_phone_entry = QLineEdit()
        contact_layout.addWidget(self.day_phone_entry, row, 1)
        
        contact_layout.addWidget(QLabel("Home District:"), row, 2)
        self.home_district_entry = QLineEdit()
        contact_layout.addWidget(self.home_district_entry, row, 3, 1, 2)
        
        # Row 3: Position, Current Address
        row += 1
        contact_layout.addWidget(QLabel("Position:"), row, 0)
        self.position_combo = QComboBox()
        self.position_combo.setEditable(True)
        self.position_combo.addItems(["Teacher", "Accountant", "Bursar", "HR", "Registrar", "Librarian"])
        contact_layout.addWidget(self.position_combo, row, 1)
        
        contact_layout.addWidget(QLabel("Current Address:"), row, 2)
        self.current_address_entry = QLineEdit()
        contact_layout.addWidget(self.current_address_entry, row, 3, 1, 2)
        
        # Row 4: Emergency Contacts
        row += 1
        contact_layout.addWidget(QLabel("Emergency Contact 1:"), row, 0)
        self.emergency_contact_1_entry = QLineEdit()
        contact_layout.addWidget(self.emergency_contact_1_entry, row, 1, 1, 2)
        
        contact_layout.addWidget(QLabel("Emergency Contact 2:"), row, 3)
        self.emergency_contact_2_entry = QLineEdit()
        contact_layout.addWidget(self.emergency_contact_2_entry, row, 4)
        
        parent_layout.addWidget(contact_group)

    def create_employment_info_section(self, parent_layout):
        """Create employment information section"""
        employment_group = QGroupBox("Employment Information")
        employment_layout = QGridLayout(employment_group)
        
        # Row 1: School, Subject Specialty
        row = 0
        employment_layout.addWidget(QLabel("School:"), row, 0)
        self.school_combo = QComboBox()
        self.school_combo.setMinimumWidth(250)
        employment_layout.addWidget(self.school_combo, row, 1, 1, 2)
        
        employment_layout.addWidget(QLabel("Subject Specialty:"), row, 3)
        self.subject_specialty_entry = QLineEdit()
        employment_layout.addWidget(self.subject_specialty_entry, row, 4)
        
        # Row 2: Qualification, Date Joined, Staff Type
        row += 1
        employment_layout.addWidget(QLabel("Qualification:"), row, 0)
        self.qualification_entry = QLineEdit()
        employment_layout.addWidget(self.qualification_entry, row, 1)
        
        employment_layout.addWidget(QLabel("Date Joined:"), row, 2)
        self.date_joined_edit = QDateEdit()
        self.date_joined_edit.setCalendarPopup(True)
        self.date_joined_edit.setDate(QDate.currentDate())
        employment_layout.addWidget(self.date_joined_edit, row, 3)
        
        employment_layout.addWidget(QLabel("Staff Type:"), row, 4)
        self.staff_type_combo = QComboBox()
        self.staff_type_combo.addItems(["Teaching", "Administrative", "Support", "Intern", "Volunteer", "Contractor"])
        employment_layout.addWidget(self.staff_type_combo, row, 5)
        
        # Row 3: Employment Status, Bank Account, Active Status
        row += 1
        employment_layout.addWidget(QLabel("Employment Status:"), row, 0)
        self.employment_status_combo = QComboBox()
        self.employment_status_combo.addItems(["Full-time", "Part-time", "Contract", "Probation", "Terminated"])
        employment_layout.addWidget(self.employment_status_combo, row, 1)
        
        employment_layout.addWidget(QLabel("Bank Account:"), row, 2)
        self.bank_account_entry = QLineEdit()
        employment_layout.addWidget(self.bank_account_entry, row, 3)
        
        employment_layout.addWidget(QLabel("Monthly Salary:"), row, 4)
        self.monthly_salary_entry = QLineEdit()
        self.monthly_salary_entry.setPlaceholderText("0.00")
        employment_layout.addWidget(self.monthly_salary_entry, row, 5)
        
        # Row 4: Active checkbox
        row += 1
        self.is_active_checkbox = QCheckBox("Active Staff Member")
        self.is_active_checkbox.setChecked(True)
        employment_layout.addWidget(self.is_active_checkbox, row, 0, 1, 2)
        
        parent_layout.addWidget(employment_group)

    def create_photo_section(self, parent_layout):
        """Create photo section"""
        photo_group = QGroupBox("Staff Photo")
        photo_layout = QVBoxLayout(photo_group)
        
        # Photo display
        self.photo_label = QLabel("No Photo\nSelected")
        self.photo_label.setProperty("class", "photo")
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setScaledContents(False)
        photo_layout.addWidget(self.photo_label)
        
        # Photo buttons
        photo_btn_layout = QHBoxLayout()
        
        self.select_photo_btn = QPushButton("Select Photo")
        self.select_photo_btn.setProperty("class", "info")
        self.select_photo_btn.clicked.connect(self.select_photo)
        photo_btn_layout.addWidget(self.select_photo_btn)
        
        self.remove_photo_btn = QPushButton("Remove")
        self.remove_photo_btn.setProperty("class", "danger")
        self.remove_photo_btn.clicked.connect(self.remove_photo)
        photo_btn_layout.addWidget(self.remove_photo_btn)
        
        photo_layout.addLayout(photo_btn_layout)
        parent_layout.addWidget(photo_group)

    def create_action_buttons(self, parent_layout):
        """Create action buttons section"""
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Primary actions
        primary_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Teacher")
        self.add_btn.setProperty("class", "success")
        self.add_btn.clicked.connect(self.add_teacher)
        primary_layout.addWidget(self.add_btn)
        
        self.update_btn = QPushButton("Update")
        self.update_btn.clicked.connect(self.update_teacher)
        primary_layout.addWidget(self.update_btn)
        
        actions_layout.addLayout(primary_layout)
        
        # Secondary actions
        secondary_layout = QHBoxLayout()
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.clicked.connect(self.delete_teacher)
        secondary_layout.addWidget(self.delete_btn)
        
        self.clear_btn = QPushButton("Clear Fields")
        self.clear_btn.setProperty("class", "warning")
        self.clear_btn.clicked.connect(self.clear_fields)
        secondary_layout.addWidget(self.clear_btn)
        
        actions_layout.addLayout(secondary_layout)
        
        # Utility actions
        utility_layout = QHBoxLayout()
        
        self.edit_selected_btn = QPushButton("Edit Selected")
        self.edit_selected_btn.clicked.connect(self.edit_selected_teacher)
        utility_layout.addWidget(self.edit_selected_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        utility_layout.addWidget(self.refresh_btn)
        
        actions_layout.addLayout(utility_layout)
        
        parent_layout.addWidget(actions_group)
        parent_layout.addStretch()  # Push everything to top

    def setup_teacher_data_tab(self):
        """Set up the teacher data tab"""
        layout = QVBoxLayout(self.teacher_data_tab)
        
        # Search section
        search_group = QGroupBox("Search Teachers")
        search_layout = QHBoxLayout(search_group)
        
        search_layout.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Enter name, ID, or email...")
        self.search_entry.textChanged.connect(self.search_teachers)
        search_layout.addWidget(self.search_entry)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_teachers)
        search_layout.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("Clear")
        self.clear_search_btn.setProperty("class", "warning")
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        layout.addWidget(search_group)
        
        #Data actions
        #actions_group = QGroupBox("Data Actions")
        #actions_layout = QHBoxLayout(actions_group)
        
        #self.export_btn = QPushButton("Export Data")
        #self.export_btn.setProperty("class", "success")
        #self.export_btn.clicked.connect(self.export_teachers_data)
        #actions_layout.addWidget(self.export_btn)

        # Add Import button
        #self.import_btn = QPushButton("Import Data")
        #self.import_btn.setProperty("class", "info")
        #self.import_btn.clicked.connect(self.import_teachers_data)
        #actions_layout.addWidget(self.import_btn)
        
        #self.report_btn = QPushButton("Generate Report")
        #self.report_btn.setProperty("class", "success")
        #self.report_btn.clicked.connect(self.generate_teacher_report)
        #actions_layout.addWidget(self.report_btn)
        
        #self.word_form_btn = QPushButton("Generate Teacher Form")
        #self.word_form_btn.setProperty("class", "info")
        #self.word_form_btn.clicked.connect(self.generate_teacher_profile_pdf)
        #actions_layout.addWidget(self.word_form_btn)
        
        #layout.addWidget(actions_group)
        
        # Teachers table
        self.create_teachers_table(layout)

    def create_teachers_table(self, parent_layout):
        """Create the teachers table"""
        table_group = QGroupBox("Teachers List")
        table_layout = QVBoxLayout(table_group)
        
        # Create table
        self.teachers_table = QTableWidget()
        self.teachers_table.setAlternatingRowColors(True)
        self.teachers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.teachers_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.teachers_table.setSortingEnabled(True)
        
        # Set headers
        self.teachers_table_headers = [
            "ID", "Teacher ID", "Full Name", "Email", "Phone", 
            "Subject", "Staff Type", "Emp. Status", "Active", "Position",
            "Date Joined", "Qualification", "Gender", "Current Address"
        ]
        self.teachers_table.setColumnCount(len(self.teachers_table_headers))
        self.teachers_table.setHorizontalHeaderLabels(self.teachers_table_headers)
        
        # Configure table
        header = self.teachers_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        
        # Connect selection signal
        self.teachers_table.itemSelectionChanged.connect(self.on_teacher_select)
        self.teachers_table.itemDoubleClicked.connect(self.edit_selected_teacher)
        
        table_layout.addWidget(self.teachers_table)
        parent_layout.addWidget(table_group)

    def setup_departments_tab(self):
        """Set up departments tab placeholder"""
        layout = QVBoxLayout(self.departments_tab)
        placeholder_label = QLabel("Departments functionality will be implemented here")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("font-size: 18px; color: #7f8c8d; padding: 50px;")
        layout.addWidget(placeholder_label)

    def update_full_name(self):
        """Automatically update full name when first name or surname changes"""
        first_name = self.first_name_entry.text().strip()
        surname = self.surname_entry.text().strip()
        full_name = f"{first_name} {surname}".strip()
        self.full_name_entry.setText(full_name)

    def select_photo(self):
        """Select and display teacher photo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Teacher Photo",
            "",
            "Image files (*.jpg *.jpeg *.png *.gif *.bmp)"
        )
        
        if file_path:
            try:
                # Load and resize image
                image = Image.open(file_path)
                image = image.resize((180, 180), Image.Resampling.LANCZOS)
                
                # Convert to QPixmap
                qimage = ImageQt.ImageQt(image)
                pixmap = QPixmap.fromImage(qimage)
                
                # Update label
                self.photo_label.setPixmap(pixmap)
                self.photo_label.setText("")
                
                # Store path for saving
                self.photo_path = file_path
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading image: {str(e)}")

    def remove_photo(self):
        """Remove selected photo"""
        self.reset_photo_display()
        self.photo_path = None
        print("Photo removed")

    def reset_photo_display(self):
        """Reset photo display to default state"""
        self.photo_label.clear()
        self.photo_label.setText("No Photo\nSelected")
        self.photo_label.setProperty("class", "photo")
        self.photo_label.setAlignment(Qt.AlignCenter)

    def load_photo(self, photo_path):
        """Load and display teacher photo"""
        try:
            if not photo_path or not os.path.exists(photo_path):
                self.reset_photo_display()
                return
                
            # Load and process image
            image = Image.open(photo_path)
            image = image.resize((180, 180), Image.Resampling.LANCZOS)
            
            # Convert to QPixmap
            qimage = ImageQt.ImageQt(image)
            pixmap = QPixmap.fromImage(qimage)
            
            # Update display
            self.photo_label.setPixmap(pixmap)
            self.photo_label.setText("")
            
        except Exception as e:
            print(f"Error loading photo: {e}")
            self.reset_photo_display()

    def save_photo(self, teacher_id):
        """Save photo to teachers directory"""
        if not self.photo_path:
            return None
            
        try:
            # Create filename
            filename = f"teacher_{teacher_id}.jpg"
            destination = os.path.join(self.photos_dir, filename)
            
            # Copy and resize image
            image = Image.open(self.photo_path)
            image = image.resize((300, 300), Image.Resampling.LANCZOS)
            image.save(destination, "JPEG", quality=85)
            
            return destination
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving photo: {str(e)}")
            return None

    def load_schools(self):
        """Load schools for dropdown"""
        try:
            self.cursor.execute("SELECT id, school_name FROM schools ORDER BY school_name")
            schools = self.cursor.fetchall()
            
            self.school_combo.clear()
            self.school_combo.addItem("", None)  # Empty option
            
            for school in schools:
                display_text = f"{school[1]} (ID: {school[0]})"
                self.school_combo.addItem(display_text, school[0])
                
        except Exception as e:
            print(f"Error loading schools: {e}")
            QMessageBox.critical(self, "Error", f"Error loading schools: {str(e)}")

    def get_school_id_from_selection(self):
        """Get school ID from combo box selection"""
        return self.school_combo.currentData()

    def validate_fields(self):
        """Enhanced validation with duplicate checking"""
        # Basic field validation
        if not self.teacher_id_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Teacher ID Code is required!")
            return False

        if not self.first_name_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "First Name is required!")
            return False

        if not self.surname_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Surname is required!")
            return False

        if not self.get_school_id_from_selection():
            QMessageBox.warning(self, "Validation Error", "School selection is required!")
            return False

        if not self.position_combo.currentText().strip():
            QMessageBox.warning(self, "Validation Error", "Position is required!")
            return False
        
        # Email format validation
        email = self.email_entry.text().strip()
        if email and "@" not in email:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address!")
            return False
        
        # Check for duplicates
        teacher_id_code = self.teacher_id_entry.text().strip()
        national_id = self.national_id_entry.text().strip()
        
        duplicates = self.check_for_duplicates(
            teacher_id_code=teacher_id_code,
            email=email,
            national_id=national_id,
            exclude_id=self.current_teacher_id
        )
        
        if duplicates:
            duplicate_msg = "Duplicate records found:\n\n" + "\n".join(duplicates)
            QMessageBox.warning(self, "Duplicate Error", duplicate_msg)
            return False

        return True

    def check_for_duplicates(self, teacher_id_code=None, email=None, national_id=None, exclude_id=None):
        """Check for duplicate teachers based on key identifiers"""
        duplicates = []
        
        try:
            # Check Teacher ID Code
            if teacher_id_code:
                query = "SELECT id, full_name FROM teachers WHERE teacher_id_code = %s"
                params = [teacher_id_code.strip()]
                if exclude_id:
                    query += " AND id != %s"
                    params.append(exclude_id)
                    
                self.cursor.execute(query, params)
                result = self.cursor.fetchone()
                if result:
                    duplicates.append(f"Teacher ID '{teacher_id_code}' is already used by {result[1]}")
            
            # Check Email
            if email:
                query = "SELECT id, full_name FROM teachers WHERE email = %s"
                params = [email.strip().lower()]
                if exclude_id:
                    query += " AND id != %s"
                    params.append(exclude_id)
                    
                self.cursor.execute(query, params)
                result = self.cursor.fetchone()
                if result:
                    duplicates.append(f"Email '{email}' is already used by {result[1]}")
            
            # Check National ID
            if national_id:
                query = "SELECT id, full_name FROM teachers WHERE national_id_number = %s"
                params = [national_id.strip()]
                if exclude_id:
                    query += " AND id != %s"
                    params.append(exclude_id)
                    
                self.cursor.execute(query, params)
                result = self.cursor.fetchone()
                if result:
                    duplicates.append(f"National ID '{national_id}' is already used by {result[1]}")
                    
        except Exception as e:
            print(f"Error checking duplicates: {e}")
            
        return duplicates

    def add_teacher(self):
        """Add new teacher"""
        if not self.validate_fields():
            return
            
        try:
            school_id = self.get_school_id_from_selection()
            
            # Get form data
            first_name = self.first_name_entry.text().strip()
            surname = self.surname_entry.text().strip()
            full_name = f"{first_name} {surname}".strip()
            
            # Update full name display
            self.full_name_entry.setText(full_name)
            
            # Get salary value
            try:
                monthly_salary = float(self.monthly_salary_entry.text().strip() or 0)
            except ValueError:
                monthly_salary = 0.0
            
            # Insert teacher record
            query = '''
                INSERT INTO teachers (
                    school_id, teacher_id_code, salutation, first_name, surname, full_name,
                    email, gender, phone_contact_1, day_phone, current_address, home_district,
                    subject_specialty, qualification, date_joined, emergency_contact_1,
                    emergency_contact_2, national_id_number, birth_date, bank_account_number,
                    next_of_kin, employment_status, is_active, staff_type, position, monthly_salary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            
            values = (
                school_id,
                self.teacher_id_entry.text().strip(),
                self.salutation_combo.currentText(),
                first_name,
                surname,
                full_name,
                self.email_entry.text().strip(),
                self.gender_combo.currentText(),
                self.phone_contact_1_entry.text().strip(),
                self.day_phone_entry.text().strip(),
                self.current_address_entry.text().strip(),
                self.home_district_entry.text().strip(),
                self.subject_specialty_entry.text().strip(),
                self.qualification_entry.text().strip(),
                self.date_joined_edit.date().toString("yyyy-MM-dd"),
                self.emergency_contact_1_entry.text().strip(),
                self.emergency_contact_2_entry.text().strip(),
                self.national_id_entry.text().strip(),
                self.birth_date_edit.date().toString("yyyy-MM-dd"),
                self.bank_account_entry.text().strip(),
                self.next_of_kin_entry.text().strip(),
                self.employment_status_combo.currentText(),
                self.is_active_checkbox.isChecked(),
                self.staff_type_combo.currentText(),
                self.position_combo.currentText().strip().title(),
                monthly_salary
            )
            
            self.cursor.execute(query, values)
            teacher_id = self.cursor.lastrowid
            
            # Save photo if selected
            if self.photo_path:
                photo_path = self.save_photo(teacher_id)
                if photo_path:
                    self.cursor.execute("UPDATE teachers SET photo_path = %s WHERE id = %s",
                                      (photo_path, teacher_id))
            
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Teacher added successfully!")
            self.clear_fields()
            self.load_teachers()
            
        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Error adding teacher: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")

    def update_teacher(self):
        """Update existing teacher"""
        if not self.current_teacher_id:
            QMessageBox.warning(self, "Error", "Please select a teacher to update!")
            return
            
        if not self.validate_fields():
            return
            
        try:
            school_id = self.get_school_id_from_selection()
            
            # Get form data
            first_name = self.first_name_entry.text().strip()
            surname = self.surname_entry.text().strip()
            full_name = f"{first_name} {surname}".strip()
            
            # Update full name display
            self.full_name_entry.setText(full_name)
            
            # Get salary value
            try:
                monthly_salary = float(self.monthly_salary_entry.text().strip() or 0)
            except ValueError:
                monthly_salary = 0.0
            
            # Handle photo update
            photo_path = None
            if self.photo_path:
                photo_path = self.save_photo(self.current_teacher_id)
                
            # Update teacher record
            query = '''
                UPDATE teachers SET
                    school_id = %s, teacher_id_code = %s, salutation = %s, first_name = %s,
                    surname = %s, full_name = %s, email = %s, gender = %s, phone_contact_1 = %s,
                    day_phone = %s, current_address = %s, home_district = %s, subject_specialty = %s,
                    qualification = %s, date_joined = %s, emergency_contact_1 = %s,
                    emergency_contact_2 = %s, national_id_number = %s, birth_date = %s,
                    bank_account_number = %s, next_of_kin = %s, employment_status = %s,
                    is_active = %s, staff_type = %s, position = %s, monthly_salary = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            '''
            
            values = (
                school_id,
                self.teacher_id_entry.text().strip(),
                self.salutation_combo.currentText(),
                first_name,
                surname,
                full_name,
                self.email_entry.text().strip(),
                self.gender_combo.currentText(),
                self.phone_contact_1_entry.text().strip(),
                self.day_phone_entry.text().strip(),
                self.current_address_entry.text().strip(),
                self.home_district_entry.text().strip(),
                self.subject_specialty_entry.text().strip(),
                self.qualification_entry.text().strip(),
                self.date_joined_edit.date().toString("yyyy-MM-dd"),
                self.emergency_contact_1_entry.text().strip(),
                self.emergency_contact_2_entry.text().strip(),
                self.national_id_entry.text().strip(),
                self.birth_date_edit.date().toString("yyyy-MM-dd"),
                self.bank_account_entry.text().strip(),
                self.next_of_kin_entry.text().strip(),
                self.employment_status_combo.currentText(),
                self.is_active_checkbox.isChecked(),
                self.staff_type_combo.currentText(),
                self.position_combo.currentText().strip().title(),
                monthly_salary,
                self.current_teacher_id
            )
            
            self.cursor.execute(query, values)
            
            # Update photo path if new photo was saved
            if photo_path:
                self.cursor.execute("UPDATE teachers SET photo_path = %s WHERE id = %s",
                                  (photo_path, self.current_teacher_id))
                
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Teacher updated successfully!")
            self.clear_fields()
            self.load_teachers()
            
        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Error updating teacher: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")

    def delete_teacher(self):
        """Delete selected teacher"""
        if not self.current_teacher_id:
            QMessageBox.warning(self, "Error", "Please select a teacher to delete!")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Delete",
            "Are you sure you want to delete this teacher?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Get photo path before deletion
                self.cursor.execute("SELECT photo_path FROM teachers WHERE id = %s", (self.current_teacher_id,))
                result = self.cursor.fetchone()
                photo_path = result[0] if result else None
                
                # Delete teacher
                self.cursor.execute("DELETE FROM teachers WHERE id = %s", (self.current_teacher_id,))
                self.db_connection.commit()
                
                # Delete photo file if exists
                if photo_path and os.path.exists(photo_path):
                    try:
                        os.remove(photo_path)
                    except Exception as e:
                        print(f"Error deleting photo file: {e}")
                
                QMessageBox.information(self, "Success", "Teacher deleted successfully!")
                self.clear_fields()
                self.load_teachers()
                
            except Exception as e:
                self.db_connection.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting teacher: {str(e)}")

    def clear_fields(self):
        """Clear all form fields and selection"""
        self.current_teacher_id = None
        self.photo_path = None
        
        # Clear all entry fields
        self.teacher_id_entry.clear()
        self.first_name_entry.clear()
        self.surname_entry.clear()
        self.full_name_entry.clear()
        self.email_entry.clear()
        self.phone_contact_1_entry.clear()
        self.day_phone_entry.clear()
        self.current_address_entry.clear()
        self.home_district_entry.clear()
        self.subject_specialty_entry.clear()
        self.qualification_entry.clear()
        self.emergency_contact_1_entry.clear()
        self.emergency_contact_2_entry.clear()
        self.national_id_entry.clear()
        self.bank_account_entry.clear()
        self.next_of_kin_entry.clear()
        self.monthly_salary_entry.clear()
        
        # Reset combo boxes
        self.salutation_combo.setCurrentText("Mr.")
        self.gender_combo.setCurrentText("Male")
        self.school_combo.setCurrentIndex(0)
        self.employment_status_combo.setCurrentText("Full-time")
        self.staff_type_combo.setCurrentText("Teaching")
        self.position_combo.setCurrentText("")
        
        # Reset dates
        self.birth_date_edit.setDate(QDate.currentDate())
        self.date_joined_edit.setDate(QDate.currentDate())
        
        # Reset checkbox
        self.is_active_checkbox.setChecked(True)
        
        # Clear photo
        self.reset_photo_display()
        
        print("All fields cleared and selection reset")

    def load_teachers(self):
        """Load teachers data into the table"""
        try:
            # Update query to include the new fields
            query = '''
                SELECT
                    t.id, t.teacher_id_code, t.full_name, t.email, t.phone_contact_1,
                    t.subject_specialty, t.staff_type, t.employment_status, t.is_active,
                    t.position, t.date_joined, t.qualification, t.gender, t.current_address
                FROM teachers t
                ORDER BY t.full_name
            '''
            self.cursor.execute(query)
            teachers = self.cursor.fetchall()
    
            # Set table dimensions
            self.teachers_table.setRowCount(len(teachers))
            self.teachers_table.setColumnCount(len(self.teachers_table_headers))
            
            # Populate table
            for row_idx, teacher in enumerate(teachers):
                items = [
                    str(teacher[0]),                              # id
                    teacher[1] or "",                             # teacher_id_code
                    teacher[2] or "",                             # full_name
                    teacher[3] or "",                             # email
                    teacher[4] or "",                             # phone_contact_1
                    teacher[5] or "",                             # subject_specialty
                    teacher[6] or "",                             # staff_type
                    teacher[7] or "",                             # employment_status
                    "Yes" if teacher[8] else "No",                # is_active
                    teacher[9] or "",                             # position
                    str(teacher[10] or ""),                       # date_joined
                    teacher[11] or "",                            # qualification
                    teacher[12] or "",                            # gender
                    teacher[13] or ""                             # current_address
                ]
                
                for col_idx, item in enumerate(items):
                    table_item = QTableWidgetItem(str(item))
                    table_item.setData(Qt.UserRole, teacher[0])  # Store teacher ID
                    
                    #Right-align current address column
                    if col_idx == 13:  # current address column
                        table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    
                    self.teachers_table.setItem(row_idx, col_idx, table_item)
    
            # Configure column sizing
            self.configure_table_columns()
            
        except Exception as e:
            print(f"Error loading teachers: {e}")
            QMessageBox.critical(self, "Error", f"Error loading teachers: {str(e)}")

    def configure_table_columns(self):
        """Configure table column sizing policies"""
        header = self.teachers_table.horizontalHeader()
        
        # Set resize modes for different columns
        # Fixed size columns
        fixed_columns = [0, 1, 7, 8, 10, 12]  # ID, Teacher ID, Emp. Status, Active, Date Joined, Gender
        for col in fixed_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        
        # Stretchable columns
        stretch_columns = [2, 3, 5, 9, 11, 12]  # Full Name, Email, Subject, Position, Qualification
        for col in stretch_columns:
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        
        # Interactive columns (user can resize)
        interactive_columns = [4, 6, 13]  # Phone, Staff Type, current address
        for col in interactive_columns:
            header.setSectionResizeMode(col, QHeaderView.Interactive)
            # Set initial width
            if col == 13:  # current address column
                header.resizeSection(col, 100)
            else:
                header.resizeSection(col, 120)

    def search_teachers(self):
        """Search teachers based on search entry"""
        search_term = self.search_entry.text().strip()
        
        try:
            if not search_term:
                self.load_teachers()
                return
    
            # Update query to include new fields in search
            query = '''
                SELECT  
                    t.id, t.teacher_id_code, t.full_name, t.email, t.phone_contact_1,
                    t.subject_specialty, t.staff_type, t.employment_status, t.is_active,
                    t.position, t.date_joined, t.qualification, t.gender, t.current_address
                FROM teachers t
                WHERE  
                    LOWER(t.full_name) LIKE LOWER(%s) OR  
                    LOWER(t.first_name) LIKE LOWER(%s) OR  
                    LOWER(t.surname) LIKE LOWER(%s) OR
                    LOWER(t.teacher_id_code) LIKE LOWER(%s) OR
                    LOWER(t.email) LIKE LOWER(%s) OR
                    LOWER(t.subject_specialty) LIKE LOWER(%s) OR
                    LOWER(t.staff_type) LIKE LOWER(%s) OR
                    LOWER(t.employment_status) LIKE LOWER(%s) OR
                    LOWER(t.position) LIKE LOWER(%s) OR
                    LOWER(t.qualification) LIKE LOWER(%s) OR
                    LOWER(t.gender) LIKE LOWER(%s) OR
                    LOWER(t.current_address) LIKE LOWER(%s)
                ORDER BY t.full_name
            '''
    
            search_pattern = f"%{search_term}%"
            params = tuple([search_pattern] * 12)  # Increased to 12 for the new search fields
            self.cursor.execute(query, params)
            teachers = self.cursor.fetchall()
    
            # Update table with search results
            self.teachers_table.setRowCount(len(teachers))
            
            for row_idx, teacher in enumerate(teachers):
                items = [
                    str(teacher[0]),                              # id
                    teacher[1] or "",                             # teacher_id_code
                    teacher[2] or "",                             # full_name
                    teacher[3] or "",                             # email
                    teacher[4] or "",                             # phone_contact_1
                    teacher[5] or "",                             # subject_specialty
                    teacher[6] or "",                             # staff_type
                    teacher[7] or "",                             # employment_status
                    "Yes" if teacher[8] else "No",                # is_active
                    teacher[9] or "",                             # position
                    str(teacher[10] or ""),                       # date_joined
                    teacher[11] or "",                            # qualification
                    teacher[12] or "",                            # gender
                    teacher[13] or ""                             # current_address
                    #f"{float(teacher[14] or 0):,.2f}" if teacher[14] else "0.00"  # monthly_salary
                ]
                
                for col_idx, item in enumerate(items):
                    table_item = QTableWidgetItem(str(item))
                    table_item.setData(Qt.UserRole, teacher[0])
                    
                    # Right-align salary column
                    if col_idx == 13:  # current address column
                        table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    
                    self.teachers_table.setItem(row_idx, col_idx, table_item)
    
            self.configure_table_columns()
    
        except Exception as e:
            print(f"Error searching teachers: {e}")
            QMessageBox.critical(self, "Error", f"Error searching teachers: {str(e)}")
        
    def clear_search(self):
        """Clear search and reload all teachers"""
        self.search_entry.clear()
        self.load_teachers()

    def on_teacher_select(self):
        """Handle teacher selection from table"""
        try:
            selected_items = self.teachers_table.selectedItems()
            if not selected_items:
                return
                
            # Get teacher ID from the first selected item (first column)
            row = selected_items[0].row()
            teacher_id_item = self.teachers_table.item(row, 0)
            
            if teacher_id_item:
                teacher_id = int(teacher_id_item.text())
                self.current_teacher_id = teacher_id
                self.load_teacher_data(teacher_id)
                
                # Show selection message
                teacher_name = self.teachers_table.item(row, 2).text()
                QMessageBox.information(
                    self, 
                    "Teacher Selected",
                    f"Selected: {teacher_name}\n\nYou can now Update or Delete this teacher."
                )
                
        except Exception as e:
            print(f"Error in teacher selection: {e}")
            QMessageBox.critical(self, "Error", f"Error selecting teacher: {str(e)}")

    def load_teacher_data(self, teacher_id):
        """Load teacher data into form fields"""
        try:
            # Get teacher data with school info
            query = '''
                SELECT t.*, s.school_name
                FROM teachers t
                LEFT JOIN schools s ON t.school_id = s.id
                WHERE t.id = %s
            '''
            self.cursor.execute(query, (teacher_id,))
            teacher = self.cursor.fetchone()
            
            if not teacher:
                QMessageBox.warning(self, "Error", "Teacher data not found")
                return
                
            # Clear all fields first
            self.clear_fields()
            
            # Set current teacher ID
            self.current_teacher_id = teacher_id
            
            # Populate form fields
            self.teacher_id_entry.setText(teacher[2] or "")        # teacher_id_code
            self.salutation_combo.setCurrentText(teacher[3] or "Mr.")  # salutation
            self.first_name_entry.setText(teacher[4] or "")       # first_name
            self.surname_entry.setText(teacher[5] or "")          # surname
            
            # Auto-generate full name
            self.update_full_name()
            
            self.email_entry.setText(teacher[7] or "")            # email
            self.gender_combo.setCurrentText(teacher[8] or "Male")  # gender
            self.phone_contact_1_entry.setText(teacher[9] or "")   # phone_contact_1
            self.day_phone_entry.setText(teacher[10] or "")       # day_phone
            self.current_address_entry.setText(teacher[11] or "") # current_address
            self.home_district_entry.setText(teacher[12] or "")   # home_district
            self.subject_specialty_entry.setText(teacher[13] or "") # subject_specialty
            self.qualification_entry.setText(teacher[14] or "")   # qualification
            
            # Handle dates
            if teacher[15]:  # date_joined
                try:
                    date_joined = QDate.fromString(str(teacher[15]), "yyyy-MM-dd")
                    self.date_joined_edit.setDate(date_joined)
                except:
                    self.date_joined_edit.setDate(QDate.currentDate())
            
            self.emergency_contact_1_entry.setText(teacher[16] or "") # emergency_contact_1
            self.emergency_contact_2_entry.setText(teacher[17] or "") # emergency_contact_2
            self.national_id_entry.setText(teacher[18] or "")      # national_id_number
            
            # Birth date
            if teacher[19]:  # birth_date
                try:
                    birth_date = QDate.fromString(str(teacher[19]), "yyyy-MM-dd")
                    self.birth_date_edit.setDate(birth_date)
                except:
                    self.birth_date_edit.setDate(QDate.currentDate())
            
            self.bank_account_entry.setText(teacher[20] or "")     # bank_account_number
            self.next_of_kin_entry.setText(teacher[21] or "")      # next_of_kin
            
            # Handle photo
            photo_path = teacher[22]
            if photo_path and os.path.exists(photo_path):
                self.load_photo(photo_path)
            else:
                self.reset_photo_display()
            
            self.employment_status_combo.setCurrentText(teacher[23] or "Full-time")  # employment_status
            self.is_active_checkbox.setChecked(bool(teacher[24]))   # is_active
            self.staff_type_combo.setCurrentText(teacher[25] or "Teaching")  # staff_type
            self.position_combo.setCurrentText(teacher[26] or "")   # position
            self.monthly_salary_entry.setText(str(teacher[27] or 0))  # monthly_salary
            
            # Handle school selection
            if teacher[1]:  # school_id exists
                for i in range(self.school_combo.count()):
                    if self.school_combo.itemData(i) == teacher[1]:
                        self.school_combo.setCurrentIndex(i)
                        break
            
            print(f"Teacher data loaded successfully for ID: {teacher_id}")
            
        except Exception as e:
            print(f"Error loading teacher data: {e}")
            QMessageBox.critical(self, "Error", f"Error loading teacher data: {str(e)}")

    def edit_selected_teacher(self):
        """Edit selected teacher from table"""
        if not self.current_teacher_id:
            QMessageBox.warning(self, "Error", "Please select a teacher from the table first!")
            return
        
        # Switch to teacher form tab
        self.tab_widget.setCurrentIndex(0)  # Index 0 is the form tab
        QMessageBox.information(self, "Info", "Teacher data loaded in the form. Make changes and click Update.")

    def refresh_data(self):
        """Refresh all data"""
        self.load_teachers()
        self.load_schools()
        QMessageBox.information(self, "Success", "Data refreshed successfully!")

    def export_teachers_data(self):
        """Export teachers data to Excel with professional formatting"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from datetime import datetime
            import os
            import subprocess
            import platform
    
            # Get all teachers data with school information
            self.cursor.execute('''
                SELECT
                    t.teacher_id_code, t.salutation, t.first_name, t.surname, t.full_name,
                    t.email, t.gender, t.phone_contact_1, t.day_phone, t.current_address,
                    t.home_district, t.subject_specialty, t.qualification, t.date_joined,
                    t.emergency_contact_1, t.emergency_contact_2, t.national_id_number,
                    t.birth_date, t.bank_account_number, t.next_of_kin, t.employment_status,
                    t.is_active, t.staff_type, t.position, t.monthly_salary, s.school_name
                FROM teachers t
                LEFT JOIN schools s ON t.school_id = s.id
                ORDER BY t.full_name
            ''')
            teachers = self.cursor.fetchall()
    
            if not teachers:
                QMessageBox.information(self, "Info", "No teacher data to export")
                return
    
            # Create workbook and worksheet
            wb = Workbook()
            ws = wb.active
            ws.title = "Teachers"
    
            # Add headers
            headers = [
                "Teacher ID", "Salutation", "First Name", "Surname", "Full Name",
                "Email", "Gender", "Phone Contact 1", "Day Phone", "Current Address",
                "Home District", "Subject Specialty", "Qualification", "Date Joined",
                "Emergency Contact 1", "Emergency Contact 2", "National ID",
                "Birth Date", "Bank Account", "Next of Kin", "Employment Status",
                "Active Status", "Staff Type", "Position", "Monthly Salary", "School Name"
            ]
            ws.append(headers)
    
            # Process and add teacher data
            processed_teachers = []
            for teacher in teachers:
                teacher_row = list(teacher)
                # Convert is_active boolean to "Yes"/"No"
                teacher_row[21] = "Yes" if teacher_row[21] else "No"
                processed_teachers.append(teacher_row)
                ws.append(teacher_row)
    
            # === HEADER FORMATTING ===
            # Define styles
            header_font = Font(
                name='Arial',
                size=12,
                bold=True,
                color='FFFFFF'  # White text
            )
            
            header_fill = PatternFill(
                start_color='2E7D32',  # Professional green for teachers
                end_color='2E7D32',
                fill_type='solid'
            )
            
            header_alignment = Alignment(
                horizontal='center',
                vertical='center',
                wrap_text=True
            )
            
            # Define border style
            thin_border = Border(
                left=Side(style='thin', color='000000'),
                right=Side(style='thin', color='000000'),
                top=Side(style='thin', color='000000'),
                bottom=Side(style='thin', color='000000')
            )
    
            # Apply header formatting
            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
    
            # === COLUMN WIDTH ADJUSTMENT ===
            # Auto-adjust column widths based on content
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        cell_length = len(str(cell.value)) if cell.value else 0
                        if cell_length > max_length:
                            max_length = cell_length
                    except:
                        pass
                
                # Set column width (with some padding and max limit)
                adjusted_width = min(max_length + 3, 50)
                ws.column_dimensions[column_letter].width = max(adjusted_width, 12)  # Minimum width of 12
    
            # === DATA FORMATTING ===
            # Apply border to all data cells
            data_font = Font(name='Arial', size=10)
            data_alignment = Alignment(horizontal='left', vertical='center')
            
            for row_num in range(2, len(processed_teachers) + 2):  # Start from row 2 (after header)
                for col_num in range(1, len(headers) + 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    cell.border = thin_border
                    cell.font = data_font
                    cell.alignment = data_alignment
                    
                    # Special formatting for specific columns
                    if col_num == 1:  # Teacher ID - center align
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    elif col_num == 7:  # Gender - center align
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    elif col_num == 22:  # Active Status - center align
                        cell.alignment = Alignment(horizontal='center', vertical='center')
    
            # === ADD TITLE AND METADATA ===
            # Insert rows at the top for title and metadata
            ws.insert_rows(1, 3)  # Insert 3 rows at the top
            
            # School title
            total_cols = len(headers)
            col_letter = chr(64 + total_cols)  # Convert to letter (A=1, B=2, etc.)
            ws.merge_cells(f'A1:{col_letter}1')  # Merge cells for title
            title_cell = ws['A1']
            title_cell.value = "WINSPIRE LEARNING HUB - TEACHERS DATA"
            title_cell.font = Font(name='Arial', size=16, bold=True, color='2E7D32')
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Export info
            ws.merge_cells(f'A2:{col_letter}2')
            info_cell = ws['A2']
            info_cell.value = f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Teachers: {len(processed_teachers)}"
            info_cell.font = Font(name='Arial', size=10, italic=True, color='666666')
            info_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Empty row for spacing
            ws['A3'].value = ""
            
            # Update header row (now row 4)
            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=4, column=col_num)  # Header is now in row 4
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
    
            # Update data formatting (starts from row 5 now)
            for row_num in range(5, len(processed_teachers) + 5):  # Start from row 5
                for col_num in range(1, len(headers) + 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    cell.border = thin_border
                    cell.font = data_font
                    cell.alignment = data_alignment
                    
                    # Special formatting for specific columns
                    if col_num == 1:  # Teacher ID
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    elif col_num == 7:  # Gender
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    elif col_num == 22:  # Active Status
                        cell.alignment = Alignment(horizontal='center', vertical='center')
    
            # === FREEZE PANES ===
            # Freeze the header row so it stays visible when scrolling
            ws.freeze_panes = 'A5'  # Freeze everything above row 5 (our data starts at row 5)
    
            # === ADD FOOTER ===
            footer_row = len(processed_teachers) + 6  # Row after all data
            ws.merge_cells(f'A{footer_row}:{col_letter}{footer_row}')
            footer_cell = ws[f'A{footer_row}']
            footer_cell.value = "Generated by CBCentra School Management System"
            footer_cell.font = Font(name='Arial', size=9, italic=True, color='999999')
            footer_cell.alignment = Alignment(horizontal='center', vertical='center')
    
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
            os.makedirs(export_dir, exist_ok=True)
            filename = os.path.join(export_dir, f"teachers_export_{timestamp}.xlsx")
    
            # Save workbook
            wb.save(filename)
    
            # Auto-open the file
            try:
                if platform.system() == "Windows":
                    os.startfile(filename)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", filename])
                else:
                    subprocess.call(["xdg-open", filename])
            except Exception as e:
                print(f"Error opening file: {e}")
    
            QMessageBox.information(
                self, 
                "Success", 
                f"Teacher data exported successfully!\n\nFile: {os.path.basename(filename)}\nTotal Teachers: {len(processed_teachers)}\nLocation: {export_dir}"
            )
    
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to export teacher data: {e}"
            )
    
    def generate_teacher_report(self):
        """Generate a teacher summary report"""
        try:
            from datetime import datetime
    
            # Get statistics including staff_type breakdown
            self.cursor.execute("SELECT COUNT(*) FROM teachers WHERE is_active = 1")
            active_count = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM teachers WHERE is_active = 0")
            inactive_count = self.cursor.fetchone()[0]
            
            # Employment status breakdown
            self.cursor.execute('''
                SELECT employment_status, COUNT(*)
                FROM teachers
                GROUP BY employment_status
            ''')
            employment_stats = self.cursor.fetchall()
            
            # Staff type breakdown
            self.cursor.execute('''
                SELECT staff_type, COUNT(*)
                FROM teachers
                GROUP BY staff_type
            ''')
            staff_type_stats = self.cursor.fetchall()
            
            # School distribution
            self.cursor.execute('''
                SELECT s.school_name, COUNT(t.id) as teacher_count
                FROM schools s
                LEFT JOIN teachers t ON s.id = t.school_id
                GROUP BY s.id, s.school_name
                ORDER BY teacher_count DESC
            ''')
            school_stats = self.cursor.fetchall()
    
            # Generate report with staff type information
            report = f"""
    TEACHERS SUMMARY REPORT
    Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    OVERVIEW:
    - Active Teachers: {active_count}
    - Inactive Teachers: {inactive_count}
    - Total Teachers: {active_count + inactive_count}
    
    STAFF TYPE BREAKDOWN:
    """
            for staff_type, count in staff_type_stats:
                report += f"- {staff_type or 'Unknown'}: {count}\n"
    
            report += "\nEMPLOYMENT STATUS BREAKDOWN:\n"
            for status, count in employment_stats:
                report += f"- {status or 'Unknown'}: {count}\n"
    
            report += "\nSCHOOL DISTRIBUTION:\n"
            for school, count in school_stats:
                report += f"- {school or 'Unknown'}: {count}\n"
    
            # Show report in a new window
            report_window = QDialog(self)
            report_window.setWindowTitle("Teachers Report")
            report_window.setMinimumSize(600, 500)
            
            layout = QVBoxLayout(report_window)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Courier", 10))
            text_edit.setText(report)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(report_window.close)
            
            layout.addWidget(text_edit)
            layout.addWidget(close_button)
            
            report_window.exec()
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating report: {str(e)}")


    # Updated method for TeachersForm to generate PDF bytes correctly
    def generate_teacher_profile_pdf(self, teacher_id=None):
        """Generate teacher profile PDF and return proper PDF bytes"""
        try:
            import os
            from fpdf import FPDF
            from datetime import datetime
            import tempfile
    
            # Use provided teacher_id or current selection
            target_teacher_id = teacher_id or getattr(self, 'current_teacher_id', None)
            
            if not target_teacher_id:
                raise ValueError("No teacher selected")
    
            # Fetch teacher data by ID including staff_type
            self.cursor.execute('''
                SELECT 
                    t.teacher_id_code, t.salutation, t.first_name, t.surname, t.email, 
                    t.gender, t.phone_contact_1, t.day_phone, t.current_address, 
                    t.home_district, t.subject_specialty, t.qualification, t.date_joined,
                    t.emergency_contact_1, t.emergency_contact_2, t.national_id_number,
                    t.birth_date, t.bank_account_number, t.next_of_kin, t.employment_status,
                    t.is_active, t.staff_type, t.position, t.school_id
                FROM teachers t
                WHERE t.id = %s
            ''', (target_teacher_id,))
    
            teacher = self.cursor.fetchone()
    
            if not teacher:
                raise ValueError("Teacher data not found")
    
            # Fetch school info for this teacher
            school_id = teacher[-1]  # school_id is last in the tuple
            self.cursor.execute('''
                SELECT school_name, address, phone, email, logo_path
                FROM schools
                WHERE id = %s
            ''', (school_id,))
            school = self.cursor.fetchone()
    
            school_name = school[0] if school else "Winspire Learning Hub"
            school_address = school[1] if school else "P.O.Box 12345"
            school_phone = school[2] if school else "Tel: +254 700 000000"
            school_email = school[3] if school else "info@winspire.com"
            school_logo = school[4] if school and school[4] else os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "static", "images", "logo.png")
    
            # Create PDF with custom class for better formatting
            class TeacherPDF(FPDF):
                def __init__(self):
                    super().__init__()
                    self.set_auto_page_break(auto=True, margin=15)
                    
                def header(self):
                    # Header with logo and school info
                    if os.path.exists(school_logo):
                        try:
                            self.image(school_logo, 10, 10, 25)  # Logo: x=10, y=10, width=25mm
                        except:
                            pass  # Skip logo if there's an error loading it
                    
                    # School information
                    self.set_xy(40, 10)  # Position next to logo
                    self.set_font('Arial', 'B', 14)
                    self.cell(0, 6, school_name.encode('latin-1', 'replace').decode('latin-1'), ln=True)
                    
                    self.set_x(40)
                    self.set_font('Arial', '', 10)
                    self.cell(0, 4, school_address.encode('latin-1', 'replace').decode('latin-1'), ln=True)
                    self.set_x(40)
                    self.cell(0, 4, school_phone.encode('latin-1', 'replace').decode('latin-1'), ln=True)
                    self.set_x(40)
                    self.cell(0, 4, school_email.encode('latin-1', 'replace').decode('latin-1'), ln=True)
                    
                    # Title
                    self.ln(10)
                    self.set_font('Arial', 'B', 16)
                    self.set_text_color(68, 114, 196)  # Blue color
                    self.cell(0, 8, 'TEACHER PROFILE FORM', 0, 1, 'C')
                    
                    # Subtitle
                    self.set_font('Arial', 'I', 10)
                    self.set_text_color(0, 0, 0)  # Reset to black
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.cell(0, 6, f'Generated on: {timestamp}', 0, 1, 'C')
                    self.ln(5)
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.set_text_color(128, 128, 128)
                    self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
                
                def section_header(self, title):
                    """Add a green section header"""
                    self.ln(3)
                    self.set_fill_color(34, 139, 34)  # Forest green
                    self.set_text_color(255, 255, 255)  # White text
                    self.set_font('Arial', 'B', 12)
                    self.cell(0, 8, title.encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L', True)
                    self.set_text_color(0, 0, 0)  # Reset to black
                    self.ln(2)
                
                def add_field(self, label, value, col1_width=60):
                    """Add a labeled field"""
                    self.set_font('Arial', 'B', 10)
                    # Encode label to handle special characters
                    safe_label = label.encode('latin-1', 'replace').decode('latin-1')
                    self.cell(col1_width, 6, safe_label + ':', 0, 0, 'L')
                    
                    self.set_font('Arial', '', 10)
                    # Handle None values and encode text
                    safe_value = str(value) if value else 'N/A'
                    safe_value = safe_value.encode('latin-1', 'replace').decode('latin-1')
                    self.cell(0, 6, safe_value, 0, 1, 'L')
                
                def add_signature_line(self, label, width=80):
                    """Add a signature line"""
                    self.set_font('Arial', '', 10)
                    safe_label = label.encode('latin-1', 'replace').decode('latin-1')
                    self.cell(len(safe_label) * 2, 6, safe_label + ': ', 0, 0, 'L')
                    
                    # Draw line
                    current_x = self.get_x()
                    current_y = self.get_y()
                    self.line(current_x, current_y + 5, current_x + width, current_y + 5)
                    self.ln(10)
    
            # Create PDF instance
            pdf = TeacherPDF()
            pdf.add_page()
    
            # Personal Information Section
            pdf.section_header("Personal Information")
            pdf.add_field("Teacher ID", teacher[0])
            full_name = f"{teacher[1] or ''} {teacher[2] or ''} {teacher[3] or ''}".strip()
            pdf.add_field("Full Name", full_name)
            pdf.add_field("Gender", teacher[5])
            pdf.add_field("Birth Date", str(teacher[16]) if teacher[16] else None)
            pdf.add_field("National ID Number", teacher[15])
            pdf.add_field("Email", teacher[4])
            pdf.add_field("Phone 1", teacher[6])
            pdf.add_field("Day Phone", teacher[7])
    
            # Professional Information Section
            pdf.section_header("Professional Information")
            pdf.add_field("Subject Specialty", teacher[10])
            pdf.add_field("Qualification", teacher[11])
            pdf.add_field("Date Joined", str(teacher[12]) if teacher[12] else None)
            pdf.add_field("Staff Type", teacher[21])
            pdf.add_field("Position", teacher[22])
            pdf.add_field("Bank Account Number", teacher[17])
            pdf.add_field("Employment Status", teacher[19])
    
            # School Information Section
            pdf.section_header("School Information")
            pdf.add_field("School Name", school_name)
            pdf.add_field("School Address", school_address)
            pdf.add_field("School Phone", school_phone)
            pdf.add_field("School Email", school_email)
    
            # Address & Emergency Section
            pdf.section_header("Address & Emergency Contact")
            pdf.add_field("Current Address", teacher[8])
            pdf.add_field("Home District", teacher[9])
            pdf.add_field("Next of Kin", teacher[18])
            pdf.add_field("Emergency Contact 1", teacher[13])
            pdf.add_field("Emergency Contact 2", teacher[14])
    
            # Declaration Section
            pdf.section_header("Declaration")
            pdf.ln(2)
            pdf.set_font('Arial', '', 10)
            
            declaration_text = ("I, __________________________________________________, "
                              "hereby declare that the above information is true and that any "
                              "attached documents are authentic.")
            
            # Split long text for better formatting
            words = declaration_text.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                if pdf.get_string_width(test_line) < 180:
                    line = test_line
                else:
                    if line:
                        pdf.cell(0, 5, line.encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L')
                    line = word + " "
            if line:
                pdf.cell(0, 5, line.encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L')
            
            pdf.ln(10)
            pdf.add_signature_line("Signature", 60)
            pdf.add_signature_line("Date", 60)
    
            # Official Use Section
            pdf.section_header("For Official Use Only")
            pdf.ln(2)
            pdf.add_signature_line("Recommended for appointment on (Date)", 80)
            pdf.ln(5)
            pdf.add_signature_line("Administrator Signature", 80)
    
            # Generate PDF bytes properly
            # First, create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_filename = temp_file.name
                
            # Output PDF to temporary file
            pdf.output(temp_filename)
            
            # Read the PDF file as bytes
            with open(temp_filename, 'rb') as f:
                pdf_bytes = f.read()
                
            # Clean up temporary file
            try:
                os.remove(temp_filename)
            except:
                pass
            
            # Store for printing functionality
            self.current_pdf_bytes = pdf_bytes
            self.current_file_type = "pdf"
            
            return pdf_bytes
    
        except Exception as e:
            raise Exception(f"Error generating teacher profile PDF: {str(e)}")
    
    # Update the original export method to use the new method
    def export_teacher_to_pdf_form(self):
        """Export selected teacher to PDF and show viewer"""
        try:
            if not hasattr(self, 'current_teacher_id') or not self.current_teacher_id:
                QMessageBox.warning(self, "No Selection", "Please select a teacher first")
                return
                
            # Generate PDF
            pdf_bytes = self.generate_teacher_profile_pdf(self.current_teacher_id)
            
            # Show PDF viewer using main window's method
            if hasattr(self.parent(), 'show_pdf_preview_dialog'):
                self.parent().show_pdf_preview_dialog(pdf_bytes)
            else:
                # Fallback
                try:
                    from utils.pdf_utils import view_pdf
                    view_pdf(pdf_bytes, parent=self)
                except ImportError:
                    QMessageBox.critical(self, "Error", "PDF viewer not available")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF:\n{str(e)}")

    def import_teachers_data(self):
        """Import teachers data from CSV or Excel file"""
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Import File",
                "",
                "Data Files (*.csv *.xlsx *.xls);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Show import options dialog
            dialog = ImportOptionsDialog(self)
            if dialog.exec() != QDialog.Accepted:
                return
            
            options = dialog.get_options()
            
            # Process the file based on extension
            if file_path.lower().endswith('.csv'):
                teachers_data = self.process_csv_file(file_path, options)
            elif file_path.lower().endswith(('.xlsx', '.xls')):
                teachers_data = self.process_excel_file(file_path, options)
            else:
                QMessageBox.warning(self, "Error", "Unsupported file format")
                return
            
            if not teachers_data:
                QMessageBox.warning(self, "Error", "No valid data found in the file")
                return
            
            # Show preview and get confirmation
            preview_dialog = ImportPreviewDialog(teachers_data, self)
            if preview_dialog.exec() != QDialog.Accepted:
                return
            
            # Import the data
            success_count, error_count = self.import_to_database(teachers_data, options.get('update_existing', False))
            
            # Show results
            QMessageBox.information(
                self,
                "Import Complete",
                f"Import completed successfully!\n\n"
                f"Successfully imported: {success_count} teachers\n"
                f"Failed to import: {error_count} teachers"
            )
            
            # Refresh the table
            self.load_teachers()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error during import: {str(e)}")
            print(f"Import error: {traceback.format_exc()}")
    
    def process_csv_file(self, file_path, options):
        """Process CSV file and extract teacher data"""
        teachers_data = []
        
        try:
            with open(file_path, 'r', encoding=options.get('encoding', 'utf-8')) as file:
                # Detect delimiter
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                
                reader = csv.DictReader(file, dialect=dialect)
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        teacher = self.map_csv_row_to_teacher(row, options.get('column_mapping', {}))
                        if teacher:
                            teachers_data.append(teacher)
                    except Exception as e:
                        print(f"Error processing row {row_num}: {e}")
                        
        except Exception as e:
            raise Exception(f"Error processing CSV file: {str(e)}")
        
        return teachers_data
    
    def process_excel_file(self, file_path, options):
        """Process Excel file and extract teacher data"""
        try:
            import openpyxl
            
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook.active
            
            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                headers.append(cell.value or f"Column_{cell.column}")
            
            teachers_data = []
            
            # Process each row
            for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
                try:
                    row_dict = dict(zip(headers, row))
                    teacher = self.map_csv_row_to_teacher(row_dict, options.get('column_mapping', {}))
                    if teacher:
                        teachers_data.append(teacher)
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    
            return teachers_data
            
        except Exception as e:
            raise Exception(f"Error processing Excel file: {str(e)}")
    
    def map_csv_row_to_teacher(self, row, column_mapping):
        """Map CSV row data to teacher dictionary"""
        if not row:
            return None
        
        # Apply column mapping if provided
        if column_mapping:
            mapped_row = {}
            for db_field, csv_column in column_mapping.items():
                if csv_column in row:
                    mapped_row[db_field] = row[csv_column]
            row = mapped_row
        
        # Create teacher dictionary with default values
        teacher = {
            'teacher_id_code': row.get('teacher_id_code', '').strip(),
            'salutation': row.get('salutation', 'Mr.').strip(),
            'first_name': row.get('first_name', '').strip(),
            'surname': row.get('surname', '').strip(),
            'full_name': f"{row.get('first_name', '').strip()} {row.get('surname', '').strip()}".strip(),
            'email': row.get('email', '').strip().lower(),
            'gender': row.get('gender', 'Male').strip(),
            'phone_contact_1': row.get('phone_contact_1', '').strip(),
            'day_phone': row.get('day_phone', '').strip(),
            'current_address': row.get('current_address', '').strip(),
            'home_district': row.get('home_district', '').strip(),
            'subject_specialty': row.get('subject_specialty', '').strip(),
            'qualification': row.get('qualification', '').strip(),
            'date_joined': row.get('date_joined', ''),
            'emergency_contact_1': row.get('emergency_contact_1', '').strip(),
            'emergency_contact_2': row.get('emergency_contact_2', '').strip(),
            'national_id_number': row.get('national_id_number', '').strip(),
            'birth_date': row.get('birth_date', ''),
            'bank_account_number': row.get('bank_account_number', '').strip(),
            'next_of_kin': row.get('next_of_kin', '').strip(),
            'employment_status': row.get('employment_status', 'Full-time').strip(),
            'is_active': str(row.get('is_active', 'True')).lower() in ('true', 'yes', '1', 'y'),
            'staff_type': row.get('staff_type', 'Teaching').strip(),
            'position': row.get('position', '').strip(),
            'monthly_salary': float(row.get('monthly_salary', 0) or 0),
            'school_id': None  # Will be set based on school name mapping
        }
        
        # Handle school mapping
        school_name = row.get('school_name', '').strip()
        if school_name:
            teacher['school_name'] = school_name
        
        return teacher
    
    def import_to_database(self, teachers_data, update_existing=False):
        """Import teachers data into database"""
        success_count = 0
        error_count = 0
        
        try:
            for teacher_data in teachers_data:
                try:
                    # Get school ID
                    school_id = None
                    if 'school_name' in teacher_data:
                        school_id = self.get_school_id_by_name(teacher_data['school_name'])
                    
                    if not school_id:
                        print(f"Warning: School not found for {teacher_data.get('full_name')}")
                        error_count += 1
                        continue
                    
                    teacher_data['school_id'] = school_id
                    
                    # Check if teacher already exists
                    existing_teacher_id = None
                    if teacher_data['teacher_id_code']:
                        self.cursor.execute(
                            "SELECT id FROM teachers WHERE teacher_id_code = %s",
                            (teacher_data['teacher_id_code'],)
                        )
                        result = self.cursor.fetchone()
                        if result:
                            existing_teacher_id = result[0]
                    
                    if existing_teacher_id and update_existing:
                        # Update existing teacher
                        query = '''
                            UPDATE teachers SET
                                school_id = %s, salutation = %s, first_name = %s, surname = %s,
                                full_name = %s, email = %s, gender = %s, phone_contact_1 = %s,
                                day_phone = %s, current_address = %s, home_district = %s,
                                subject_specialty = %s, qualification = %s, date_joined = %s,
                                emergency_contact_1 = %s, emergency_contact_2 = %s,
                                national_id_number = %s, birth_date = %s, bank_account_number = %s,
                                next_of_kin = %s, employment_status = %s, is_active = %s,
                                staff_type = %s, position = %s, monthly_salary = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        '''
                        values = (
                            teacher_data['school_id'], teacher_data['salutation'],
                            teacher_data['first_name'], teacher_data['surname'],
                            teacher_data['full_name'], teacher_data['email'],
                            teacher_data['gender'], teacher_data['phone_contact_1'],
                            teacher_data['day_phone'], teacher_data['current_address'],
                            teacher_data['home_district'], teacher_data['subject_specialty'],
                            teacher_data['qualification'], teacher_data['date_joined'],
                            teacher_data['emergency_contact_1'], teacher_data['emergency_contact_2'],
                            teacher_data['national_id_number'], teacher_data['birth_date'],
                            teacher_data['bank_account_number'], teacher_data['next_of_kin'],
                            teacher_data['employment_status'], teacher_data['is_active'],
                            teacher_data['staff_type'], teacher_data['position'],
                            teacher_data['monthly_salary'], existing_teacher_id
                        )
                    else:
                        # Insert new teacher
                        query = '''
                            INSERT INTO teachers (
                                school_id, teacher_id_code, salutation, first_name, surname, full_name,
                                email, gender, phone_contact_1, day_phone, current_address, home_district,
                                subject_specialty, qualification, date_joined, emergency_contact_1,
                                emergency_contact_2, national_id_number, birth_date, bank_account_number,
                                next_of_kin, employment_status, is_active, staff_type, position, monthly_salary
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        '''
                        values = (
                            teacher_data['school_id'], teacher_data['teacher_id_code'],
                            teacher_data['salutation'], teacher_data['first_name'],
                            teacher_data['surname'], teacher_data['full_name'],
                            teacher_data['email'], teacher_data['gender'],
                            teacher_data['phone_contact_1'], teacher_data['day_phone'],
                            teacher_data['current_address'], teacher_data['home_district'],
                            teacher_data['subject_specialty'], teacher_data['qualification'],
                            teacher_data['date_joined'], teacher_data['emergency_contact_1'],
                            teacher_data['emergency_contact_2'], teacher_data['national_id_number'],
                            teacher_data['birth_date'], teacher_data['bank_account_number'],
                            teacher_data['next_of_kin'], teacher_data['employment_status'],
                            teacher_data['is_active'], teacher_data['staff_type'],
                            teacher_data['position'], teacher_data['monthly_salary']
                        )
                    
                    self.cursor.execute(query, values)
                    success_count += 1
                    
                except Exception as e:
                    print(f"Error importing teacher {teacher_data.get('full_name')}: {e}")
                    error_count += 1
            
            self.db_connection.commit()
            
        except Exception as e:
            self.db_connection.rollback()
            raise e
        
        return success_count, error_count
    
    def get_school_id_by_name(self, school_name):
        """Get school ID by name"""
        try:
            self.cursor.execute(
                "SELECT id FROM schools WHERE school_name = %s",
                (school_name,)
            )
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting school ID: {e}")
            return None

class ImportOptionsDialog(QDialog):
    """Dialog for import options"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Options")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.options = {
            'encoding': 'utf-8',
            'update_existing': False,
            'column_mapping': {}
        }
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Encoding selection
        encoding_group = QGroupBox("File Encoding")
        encoding_layout = QVBoxLayout(encoding_group)
        
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(['utf-8', 'latin-1', 'cp1252', 'ascii'])
        encoding_layout.addWidget(QLabel("Select file encoding:"))
        encoding_layout.addWidget(self.encoding_combo)
        
        layout.addWidget(encoding_group)
        
        # Update option
        self.update_checkbox = QCheckBox("Update existing teachers if found")
        layout.addWidget(self.update_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def get_options(self):
        self.options['encoding'] = self.encoding_combo.currentText()
        self.options['update_existing'] = self.update_checkbox.isChecked()
        return self.options


class ImportPreviewDialog(QDialog):
    """Dialog to preview import data"""
    
    def __init__(self, teachers_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Preview")
        self.setModal(True)
        self.setMinimumSize(800, 500)
        
        self.teachers_data = teachers_data
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setRowCount(min(10, len(self.teachers_data)))  # Show max 10 rows
        self.preview_table.setColumnCount(5)  # Show key columns
        
        headers = ["Teacher ID", "Full Name", "Email", "Position", "School"]
        self.preview_table.setHorizontalHeaderLabels(headers)
        
        # Populate table
        for row, teacher in enumerate(self.teachers_data[:10]):
            self.preview_table.setItem(row, 0, QTableWidgetItem(teacher.get('teacher_id_code', '')))
            self.preview_table.setItem(row, 1, QTableWidgetItem(teacher.get('full_name', '')))
            self.preview_table.setItem(row, 2, QTableWidgetItem(teacher.get('email', '')))
            self.preview_table.setItem(row, 3, QTableWidgetItem(teacher.get('position', '')))
            self.preview_table.setItem(row, 4, QTableWidgetItem(teacher.get('school_name', '')))
        
        self.preview_table.resizeColumnsToContents()
        layout.addWidget(QLabel(f"Preview (showing first 10 of {len(self.teachers_data)} records):"))
        layout.addWidget(self.preview_table)
        
        # Summary
        layout.addWidget(QLabel(f"Total records to import: {len(self.teachers_data)}"))
        
        # Buttons
        button_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        
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
