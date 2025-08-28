# ui/students_form.py
import sys
import os
import csv
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QGroupBox, QGridLayout, QComboBox,
    QFormLayout, QTabWidget, QMenu, QCheckBox, QDateEdit, QTextEdit, QApplication
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QPixmap, QIcon, QFont

# Import from your existing structure
from ui.audit_base_form import AuditBaseForm
from models.models import get_db_connection  # Centralized DB connection
from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import platform
import subprocess
import random

class StudentDetailsPopup(QDialog):
    """Popup window to view detailed student information"""

    def __init__(self, parent, student_id, user_session=None):
        super().__init__(parent)
        self.student_id = student_id
        self.user_session = user_session
        self.db_connection = None
        self.cursor = None

        self.setWindowTitle("Student Details")
        self.resize(900, 700)
        self.setModal(True)

        # Apply styling
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { font-weight: bold; color: #333; }
            QTextEdit { background-color: white; border: 1px solid #ddd; }
        """)

        self.setup_ui()
        self.load_student_details()

    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        title = QLabel("Student Details")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f538d; padding: 10px;")
        layout.addWidget(title)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form_layout = QFormLayout()
        content.setLayout(form_layout)

        # Create labels for student information
        self.full_name_lbl = QLabel()
        self.reg_no_lbl = QLabel()
        self.sex_lbl = QLabel()
        self.dob_lbl = QLabel()
        self.email_lbl = QLabel()
        self.grade_lbl = QLabel()
        self.class_year_lbl = QLabel()
        self.enrollment_lbl = QLabel()
        self.religion_lbl = QLabel()
        self.citizenship_lbl = QLabel()
        self.last_school_lbl = QLabel()
        self.status_lbl = QLabel()

        self.medical_lbl = QTextEdit()
        self.medical_lbl.setReadOnly(True)
        self.medical_lbl.setMaximumHeight(100)

        self.allergies_lbl = QTextEdit()
        self.allergies_lbl.setReadOnly(True)
        self.allergies_lbl.setMaximumHeight(100)

        # Add form rows
        form_layout.addRow("Full Name:", self.full_name_lbl)
        form_layout.addRow("Registration No:", self.reg_no_lbl)
        form_layout.addRow("Sex:", self.sex_lbl)
        form_layout.addRow("Date of Birth:", self.dob_lbl)
        form_layout.addRow("Email:", self.email_lbl)
        form_layout.addRow("Grade Applied For:", self.grade_lbl)
        form_layout.addRow("Class Year:", self.class_year_lbl)
        form_layout.addRow("Enrollment Date:", self.enrollment_lbl)
        form_layout.addRow("Religion:", self.religion_lbl)
        form_layout.addRow("Citizenship:", self.citizenship_lbl)
        form_layout.addRow("Last School:", self.last_school_lbl)
        form_layout.addRow("Status:", self.status_lbl)
        form_layout.addRow("Medical Conditions:", self.medical_lbl)
        form_layout.addRow("Allergies:", self.allergies_lbl)

        # Parents section
        parents_label = QLabel("Parents / Guardians")
        parents_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #1f538d; padding: 10px 0;")
        form_layout.addRow(parents_label)

        self.parents_table = QTableWidget()
        self.parents_table.setColumnCount(6)
        self.parents_table.setHorizontalHeaderLabels([
            "Name", "Relation", "Phone", "Email", "Fee Payer", "Emergency Contact"
        ])
        self.parents_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parents_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.parents_table.setMaximumHeight(200)
        form_layout.addRow(self.parents_table)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c82333; }
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    def load_student_details(self):
        """Load student details from database"""
        try:
            self.db_connection = get_db_connection()
            if not self.db_connection:
                QMessageBox.critical(self, "Error", "Failed to connect to database")
                return
            self.cursor = self.db_connection.cursor(buffered=True)

            query = '''
                SELECT s.first_name, s.surname, s.sex, s.date_of_birth, s.email,
                       s.grade_applied_for, s.class_year, s.enrollment_date, s.regNo,
                       s.religion, s.citizenship, s.last_school, s.medical_conditions, 
                       s.allergies, s.is_active
                FROM students s
                WHERE s.id = %s
            '''
            self.cursor.execute(query, (self.student_id,))
            student = self.cursor.fetchone()

            if not student:
                QMessageBox.warning(self, "Error", "Student not found.")
                return

            self.full_name_lbl.setText(f"{student[0] or ''} {student[1] or ''}".strip())
            self.reg_no_lbl.setText(student[8] or "N/A")
            self.sex_lbl.setText(student[2] or "N/A")
            self.dob_lbl.setText(str(student[3]) if student[3] else "N/A")
            self.email_lbl.setText(student[4] or "N/A")
            self.grade_lbl.setText(student[5] or "N/A")
            self.class_year_lbl.setText(student[6] or "N/A")
            self.enrollment_lbl.setText(str(student[7]) if student[7] else "N/A")
            self.religion_lbl.setText(student[9] or "N/A")
            self.citizenship_lbl.setText(student[10] or "N/A")
            self.last_school_lbl.setText(student[11] or "N/A")
            self.status_lbl.setText("Active" if student[14] else "Inactive")
            self.medical_lbl.setPlainText(student[12] or "None")
            self.allergies_lbl.setPlainText(student[13] or "None")

            self.load_parents_info()

        except Exception as e:
            print(f"Error loading student details: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load student details: {str(e)}")

    def load_parents_info(self):
        """Load parent information for the student"""
        try:
            parent_query = '''
                SELECT p.full_name, sp.relation_type, p.phone, p.email,
                       sp.is_fee_payer, sp.is_emergency_contact
                FROM student_parent sp
                JOIN parents p ON sp.parent_id = p.id
                WHERE sp.student_id = %s AND p.is_active = TRUE
                ORDER BY sp.is_primary_contact DESC
            '''
            self.cursor.execute(parent_query, (self.student_id,))
            parents = self.cursor.fetchall()

            self.parents_table.setRowCount(len(parents))
            for row_idx, parent in enumerate(parents):
                for col_idx, data in enumerate(parent):
                    text = "Yes" if data is True else ("No" if data is False else str(data or "N/A"))
                    self.parents_table.setItem(row_idx, col_idx, QTableWidgetItem(text))

        except Exception as e:
            print(f"Error loading parents: {e}")

    def closeEvent(self, event):
        """Clean up database connection"""
        if self.cursor:
            self.cursor.close()
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
        event.accept()


class StudentsForm(AuditBaseForm):
    """Main students management form"""

    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.user_session = user_session
        self.current_student_id = None
        self.photo_path = None
        self.db_connection = None
        self.cursor = None

        # Use centralized DB connection
        try:
            self.db_connection = get_db_connection()
            if not self.db_connection:
                raise Exception("Failed to establish database connection")
            self.cursor = self.db_connection.cursor(buffered=True)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect: {str(e)}")
            return

        self.setup_ui()
        self.load_initial_data()

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Students Management")
        self.resize(1200, 800)

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create tabs
        self.form_tab = QWidget()
        self.list_tab = QWidget()

        self.tabs.addTab(self.form_tab, "Student Form")
        self.tabs.addTab(self.list_tab, "Students List")

        self.setup_form_tab()
        self.setup_list_tab()
        
    def setup_form_tab(self):
        """Setup the Student Form tab with two-column layout and scroll bar"""
        # Create main scroll area for the entire form tab
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QFrame.NoFrame)
        
        # Create container widget for scroll area
        form_container = QWidget()
        main_container_layout = QVBoxLayout(form_container)
        form_scroll.setWidget(form_container)
        
        # Set the scroll area as the main layout for the form tab
        self.form_tab.setLayout(QVBoxLayout())
        self.form_tab.layout().addWidget(form_scroll)
        self.form_tab.layout().setContentsMargins(0, 0, 0, 0)
        
        # Add some styling for better spacing
        form_container.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
        """)
    
        # Main form layout inside the container
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(15)
        main_container_layout.addLayout(form_layout)
    
        # Main horizontal splitter
        main_splitter = QHBoxLayout()
        main_splitter.setSpacing(20)
        form_layout.addLayout(main_splitter)
    
        # === LEFT SIDE: Photo, Student & Academic Info ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        main_splitter.addLayout(left_layout, 6)
    
        # --- Photo Section ---
        photo_group = QGroupBox("Student Photo")
        photo_layout = QGridLayout()
        photo_layout.setContentsMargins(10, 15, 10, 10)
        photo_layout.setSpacing(10)
        photo_group.setLayout(photo_layout)
    
        self.photo_label = QLabel("No Photo")
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setFixedSize(150, 180)
        self.photo_label.setStyleSheet("""
            border: 2px dashed #ccc;
            background-color: #f0f0f0;
            color: #888;
            font-size: 12px;
        """)
        photo_layout.addWidget(self.photo_label, 0, 0, 3, 1, Qt.AlignCenter)
    
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setMaximumWidth(100)
        self.upload_btn.clicked.connect(self.upload_photo)
        photo_layout.addWidget(self.upload_btn, 0, 1)
    
        self.remove_photo_btn = QPushButton("Remove")
        self.remove_photo_btn.setMaximumWidth(100)
        self.remove_photo_btn.clicked.connect(self.remove_photo)
        photo_layout.addWidget(self.remove_photo_btn, 1, 1)
    
        left_layout.addWidget(photo_group)
    
        # --- Student Personal Info ---
        personal_group = QGroupBox("Personal Information")
        personal_layout = QGridLayout()
        personal_layout.setContentsMargins(10, 15, 10, 10)
        personal_layout.setSpacing(10)
        personal_layout.setVerticalSpacing(12)
        personal_layout.setHorizontalSpacing(15)
        personal_group.setLayout(personal_layout)
    
        self.first_name_entry = QLineEdit()
        self.surname_entry = QLineEdit()
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["", "Male", "Female"])
        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDate(QDate.currentDate().addYears(-10))  # Default to 10 years ago
        self.email_entry = QLineEdit()
        self.reg_no_entry = QLineEdit()
        self.religion_entry = QLineEdit()
        self.citizenship_entry = QLineEdit()
    
        personal_layout.addWidget(QLabel("First Name *"), 0, 0)
        personal_layout.addWidget(self.first_name_entry, 0, 1)
        personal_layout.addWidget(QLabel("Surname *"), 0, 2)
        personal_layout.addWidget(self.surname_entry, 0, 3)
    
        personal_layout.addWidget(QLabel("Sex"), 1, 0)
        personal_layout.addWidget(self.sex_combo, 1, 1)
        personal_layout.addWidget(QLabel("Date of Birth"), 1, 2)
        personal_layout.addWidget(self.dob_edit, 1, 3)
    
        personal_layout.addWidget(QLabel("Email"), 2, 0)
        personal_layout.addWidget(self.email_entry, 2, 1, 1, 3)
    
        # With this updated code:
        personal_layout.addWidget(QLabel("Reg No *"), 3, 0)
        
        # Create a horizontal layout for reg no and generate button
        reg_no_layout = QHBoxLayout()
        reg_no_layout.setSpacing(5)
        reg_no_layout.addWidget(self.reg_no_entry)
        
        self.generate_reg_btn = QPushButton("Generate")
        self.generate_reg_btn.setMaximumWidth(80)
        self.generate_reg_btn.setToolTip("Click to generate Registration Number")
        self.generate_reg_btn.clicked.connect(self.generate_reg_no)
        reg_no_layout.addWidget(self.generate_reg_btn)
        
        # Add the layout to the grid
        personal_layout.addLayout(reg_no_layout, 3, 1)

        personal_layout.addWidget(QLabel("Religion"), 3, 2)
        personal_layout.addWidget(self.religion_entry, 3, 3)
    
        personal_layout.addWidget(QLabel("Citizenship"), 4, 0)
        personal_layout.addWidget(self.citizenship_entry, 4, 1, 1, 3)
    
        # Add stretch to columns for better spacing
        personal_layout.setColumnStretch(1, 1)
        personal_layout.setColumnStretch(3, 1)
    
        left_layout.addWidget(personal_group)
    
        # --- Academic Information ---
        academic_group = QGroupBox("Academic Information")
        academic_layout = QGridLayout()
        academic_layout.setContentsMargins(10, 15, 10, 10)
        academic_layout.setSpacing(10)
        academic_layout.setVerticalSpacing(12)
        academic_layout.setHorizontalSpacing(15)
        academic_group.setLayout(academic_layout)
    
        self.grade_combo = QComboBox()
        self.class_year_entry = QLineEdit()
        self.enrollment_date = QDateEdit()
        self.enrollment_date.setCalendarPopup(True)
        self.enrollment_date.setDate(QDate.currentDate())
        self.last_school_entry = QLineEdit()
    
        academic_layout.addWidget(QLabel("Grade Applied For *"), 0, 0)
        academic_layout.addWidget(self.grade_combo, 0, 1)
        academic_layout.addWidget(QLabel("Class Year"), 0, 2)
        academic_layout.addWidget(self.class_year_entry, 0, 3)
    
        academic_layout.addWidget(QLabel("Enrollment Date"), 1, 0)
        academic_layout.addWidget(self.enrollment_date, 1, 1)
        academic_layout.addWidget(QLabel("Last School"), 1, 2)
        academic_layout.addWidget(self.last_school_entry, 1, 3)
    
        # Add stretch to columns for better spacing
        academic_layout.setColumnStretch(1, 1)
        academic_layout.setColumnStretch(3, 1)
    
        left_layout.addWidget(academic_group)
        left_layout.addStretch()
    
        # === RIGHT SIDE: Medical & Parent Info ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        main_splitter.addLayout(right_layout, 4)
    
        # --- Medical Information ---
        medical_group = QGroupBox("Medical Information")
        medical_layout = QVBoxLayout()
        medical_layout.setContentsMargins(10, 15, 10, 10)
        medical_layout.setSpacing(8)
        medical_group.setLayout(medical_layout)
    
        self.medical_text = QTextEdit()
        self.medical_text.setMaximumHeight(100)
        self.medical_text.setPlaceholderText("List any medical conditions (e.g., asthma, diabetes)")
        medical_layout.addWidget(QLabel("Medical Conditions"))
        medical_layout.addWidget(self.medical_text)
    
        self.allergies_text = QTextEdit()
        self.allergies_text.setMaximumHeight(100)
        self.allergies_text.setPlaceholderText("List known allergies (e.g., peanuts, penicillin)")
        medical_layout.addWidget(QLabel("Allergies"))
        medical_layout.addWidget(self.allergies_text)
    
        right_layout.addWidget(medical_group)
    
        # --- Parent/Guardian Information ---
        parent_group = QGroupBox("Parent / Guardian")
        parent_layout = QVBoxLayout()
        parent_layout.setContentsMargins(10, 15, 10, 10)
        parent_layout.setSpacing(10)
        parent_group.setLayout(parent_layout)
    
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.parent_search_entry = QLineEdit()
        self.parent_search_entry.setPlaceholderText("Search parent...")
        search_parent_btn = QPushButton("Search")
        search_row.addWidget(self.parent_search_entry)
        search_row.addWidget(search_parent_btn)
        parent_layout.addLayout(search_row)
    
        # Add scroll area for parent table
        parent_scroll = QScrollArea()
        parent_scroll.setWidgetResizable(True)
        parent_scroll.setMinimumHeight(200)
        parent_scroll.setMaximumHeight(300)
        
        parent_table_container = QWidget()
        parent_table_layout = QVBoxLayout(parent_table_container)
        parent_table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.parents_table = QTableWidget()
        self.parents_table.setColumnCount(5)
        self.parents_table.setHorizontalHeaderLabels(["Name", "Relation", "Phone", "Email", "Actions"])
        self.parents_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parents_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        parent_table_layout.addWidget(self.parents_table)
        parent_scroll.setWidget(parent_table_container)
        parent_layout.addWidget(parent_scroll)
    
        add_parent_btn = QPushButton("+ Add Parent")
        add_parent_btn.setStyleSheet("font-weight: bold; color: green;")
        add_parent_btn.clicked.connect(self.add_parent_to_student)
        parent_layout.addWidget(add_parent_btn)
    
        right_layout.addWidget(parent_group)
    
        # --- Active Status & Save Button ---
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)
        self.is_active_check = QCheckBox("Is Active")
        self.is_active_check.setChecked(True)
        bottom_row.addWidget(self.is_active_check)
    
        self.save_btn = QPushButton("Save Student")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.save_btn.clicked.connect(self.save_student)
        bottom_row.addStretch()
        bottom_row.addWidget(self.save_btn)
    
        form_layout.addLayout(bottom_row)

    def setup_list_tab(self):
        """Setup the list tab for viewing students with scroll bar"""
        # Create main scroll area for the list tab
        list_scroll = QScrollArea()
        list_scroll.setWidgetResizable(True)
        list_scroll.setFrameShape(QFrame.NoFrame)
        
        # Create container widget for scroll area
        list_container = QWidget()
        container_layout = QVBoxLayout(list_container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(15)
        
        list_scroll.setWidget(list_container)
        
        # Set the scroll area as the main layout for the list tab
        self.list_tab.setLayout(QVBoxLayout())
        self.list_tab.layout().addWidget(list_scroll)
        self.list_tab.layout().setContentsMargins(0, 0, 0, 0)
    
        # Search section
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        search_layout.addWidget(QLabel("Search Students:"))
    
        self.list_search_entry = QLineEdit()
        self.list_search_entry.setPlaceholderText("Search by name, reg no, or parent...")
        self.list_search_entry.textChanged.connect(self.search_students_list)
        search_layout.addWidget(self.list_search_entry)
    
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_students)
        search_layout.addWidget(refresh_btn)
    
        clear_list_search_btn = QPushButton("Clear")
        clear_list_search_btn.clicked.connect(self.clear_list_search)
        search_layout.addWidget(clear_list_search_btn)
    
        container_layout.addLayout(search_layout)
    
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
    
        edit_btn = QPushButton("Edit Selected")
        edit_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        edit_btn.clicked.connect(self.edit_selected_student)
        action_layout.addWidget(edit_btn)
    
        view_btn = QPushButton("View Details")
        view_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")
        view_btn.clicked.connect(self.view_student_details)
        action_layout.addWidget(view_btn)
    
        export_excel_btn = QPushButton("Export to Excel")
        export_excel_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        export_excel_btn.clicked.connect(self.export_to_excel)
        action_layout.addWidget(export_excel_btn)
    
        export_pdf_btn = QPushButton("Generate PDF")
        export_pdf_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        export_pdf_btn.clicked.connect(self.generate_pdf_report)
        action_layout.addWidget(export_pdf_btn)
    
        action_layout.addStretch()
        container_layout.addLayout(action_layout)
    
        # Students table with its own scroll area
        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setMinimumHeight(400)
        
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(10)
        self.students_table.setHorizontalHeaderLabels([
            "ID", "Reg No", "Name", "Sex", "Grade", "Class Year",
            "Status", "Email", "Enrollment", "Parent"
        ])
    
        header = self.students_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
    
        self.students_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.students_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.students_table.cellClicked.connect(self.on_student_select)
        self.students_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.students_table.customContextMenuRequested.connect(self.show_context_menu)
    
        table_layout.addWidget(self.students_table)
        table_scroll.setWidget(table_container)
        container_layout.addWidget(table_scroll)

    def show_context_menu(self, position):
        """Show context menu for table"""
        if self.current_student_id:
            context_menu = QMenu()

            view_action = QAction("View Details", self)
            view_action.triggered.connect(self.view_student_details)
            context_menu.addAction(view_action)

            edit_action = QAction("Edit Student", self)
            edit_action.triggered.connect(self.edit_selected_student)
            context_menu.addAction(edit_action)

            context_menu.addSeparator()

            delete_action = QAction("Delete Student", self)
            delete_action.triggered.connect(self.delete_student)
            context_menu.addAction(delete_action)

            context_menu.exec_(self.students_table.mapToGlobal(position))

    def load_initial_data(self):
        """Load initial data for dropdowns and tables"""
        if not self.cursor:
            return
        self.load_grades()
        self.load_students()

    def load_grades(self):
        """Load grades for dropdown"""
        try:
            self.cursor.execute("""
                SELECT DISTINCT grade_applied_for 
                FROM students 
                WHERE grade_applied_for IS NOT NULL AND is_active = TRUE
                ORDER BY grade_applied_for
            """)
            grades = [row[0] for row in self.cursor.fetchall()]
            default_grades = ["S1", "S2", "S3", "S4", "S5", "S6"]

            self.grade_combo.clear()
            self.grade_combo.addItems(grades or default_grades)

        except Exception as e:
            print(f"Error loading grades: {e}")
            self.grade_combo.clear()
            self.grade_combo.addItems(default_grades)

    def load_parents(self):
        """Load parents for dropdown"""
        try:
            self.cursor.execute("""
                SELECT id, full_name, relation_type, phone, email
                FROM parents 
                WHERE is_active = TRUE 
                ORDER BY full_name
            """)
            parents = self.cursor.fetchall()
            
            self.parent_dropdown.clear()
            self.parent_dropdown.addItem("Select Parent", None)
            
            for parent in parents:
                parent_id, name, relation, phone, email = parent
                display_text = f"{name} ({relation or 'Guardian'})"
                self.parent_dropdown.addItem(display_text, parent_id)
                
        except Exception as e:
            print(f"Error loading parents: {e}")

    def load_students(self):
        """Load students into the table"""
        try:
            query = '''
                SELECT s.id, s.regNo, s.first_name, s.surname, s.sex, 
                       s.grade_applied_for, s.class_year, s.is_active, 
                       s.email, s.enrollment_date,
                       GROUP_CONCAT(DISTINCT p.full_name SEPARATOR ', ') as parents
                FROM students s
                LEFT JOIN student_parent sp ON s.id = sp.student_id
                LEFT JOIN parents p ON sp.parent_id = p.id AND p.is_active = TRUE
                WHERE s.is_active = TRUE
                GROUP BY s.id
                ORDER BY s.surname, s.first_name
                LIMIT 200
            '''
            self.cursor.execute(query)
            students = self.cursor.fetchall()
            
            self.update_students_table(students)
            
        except Exception as e:
            print(f"Error loading students: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load students: {str(e)}")

    def update_students_table(self, students):
        """Update the students table with data"""
        self.students_table.setRowCount(len(students))
        
        for row_idx, student in enumerate(students):
            # ID
            self.students_table.setItem(row_idx, 0, QTableWidgetItem(str(student[0])))
            
            # Reg No
            self.students_table.setItem(row_idx, 1, QTableWidgetItem(student[1] or ""))
            
            # Full Name
            full_name = f"{student[2] or ''} {student[3] or ''}".strip()
            self.students_table.setItem(row_idx, 2, QTableWidgetItem(full_name))
            
            # Sex
            self.students_table.setItem(row_idx, 3, QTableWidgetItem(student[4] or ""))
            
            # Grade
            self.students_table.setItem(row_idx, 4, QTableWidgetItem(student[5] or ""))
            
            # Class Year
            self.students_table.setItem(row_idx, 5, QTableWidgetItem(student[6] or ""))
            
            # Status
            status = "Active" if student[7] else "Inactive"
            self.students_table.setItem(row_idx, 6, QTableWidgetItem(status))
            
            # Email
            self.students_table.setItem(row_idx, 7, QTableWidgetItem(student[8] or ""))
            
            # Enrollment Date
            enrollment_date = str(student[9]) if student[9] else ""
            self.students_table.setItem(row_idx, 8, QTableWidgetItem(enrollment_date))
            
            # Parents
            self.students_table.setItem(row_idx, 9, QTableWidgetItem(student[10] or ""))

    def update_full_name(self):
        """Update full name when first name or surname changes"""
        first_name = self.first_name_entry.text().strip()
        surname = self.surname_entry.text().strip()
        full_name = f"{first_name} {surname}".strip()
        self.full_name_entry.setText(full_name)

    def upload_photo(self):
        """Upload student photo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Student Photo",
            "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        
        if file_path:
            try:
                # Load and display the photo
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # Scale the image to fit the label
                    scaled_pixmap = pixmap.scaled(
                        150, 150, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.photo_label.setPixmap(scaled_pixmap)
                    self.photo_path = file_path
                else:
                    QMessageBox.warning(self, "Error", "Failed to load image file")
                    
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load image: {str(e)}")

    def remove_photo(self):
        """Remove student photo"""
        self.photo_label.clear()
        self.photo_label.setText("No Photo")
        self.photo_path = None

    def generate_reg_no(self):
        """Generate registration number in format HIMHYYXXXX-ST"""
        try:
            year_suffix = datetime.now().year % 100
            year_str = f"{year_suffix:02d}"
            
            # Generate random number between 1000 and 9999
            rand_num = random.randint(1000, 9999)
            
            reg_no = f"HIMH{year_str}{rand_num}-ST"
            self.reg_no_entry.setText(reg_no)
            
        except Exception as e:
            print(f"Error generating registration number: {e}")
            self.reg_no_entry.setText("HIMH250000-ST")

    def search_parents(self):
        """Search for parents"""
        search_term = self.parent_search_entry.text().strip()
        
        if not search_term:
            self.load_parents()
            return
        
        try:
            query = """
                SELECT id, full_name, relation_type, phone, email, address1, address2,
                       is_fee_payer, is_emergency_contact
                FROM parents 
                WHERE is_active = TRUE 
                AND (full_name LIKE %s OR phone LIKE %s OR email LIKE %s)
                ORDER BY full_name
                LIMIT 20
            """
            like_term = f"%{search_term}%"
            self.cursor.execute(query, (like_term, like_term, like_term))
            parents = self.cursor.fetchall()
            
            self.parent_dropdown.clear()
            self.parent_dropdown.addItem("Select Parent", None)
            
            for parent in parents:
                parent_id, name, relation, phone, email = parent[:5]
                display_text = f"{name} ({relation or 'Guardian'}) - {phone or 'No Phone'}"
                self.parent_dropdown.addItem(display_text, parent_id)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to search parents: {str(e)}")

    def on_parent_select(self):
        """Handle parent selection"""
        parent_id = self.parent_dropdown.currentData()
        
        if not parent_id:
            self.parent_info_text.setText("No parent selected")
            return
        
        try:
            query = """
                SELECT full_name, relation_type, phone, email, address1, address2,
                       is_fee_payer, is_emergency_contact
                FROM parents 
                WHERE id = %s AND is_active = TRUE
            """
            self.cursor.execute(query, (parent_id,))
            parent = self.cursor.fetchone()
            
            if parent:
                name, relation, phone, email, addr1, addr2, is_payer, is_emergency = parent
                
                # Format address
                address_parts = []
                if addr1:
                    address_parts.append(addr1)
                if addr2:
                    address_parts.append(addr2)
                address = ", ".join(address_parts) if address_parts else "N/A"
                
                info_text = f"""Name: {name}
Relation: {relation or 'N/A'}
Phone: {phone or 'N/A'}
Email: {email or 'N/A'}
Address: {address}
Fee Payer: {'Yes' if is_payer else 'No'}
Emergency Contact: {'Yes' if is_emergency else 'No'}"""
                
                self.parent_info_text.setText(info_text)
            else:
                self.parent_info_text.setText("Parent information not found")
                
        except Exception as e:
            print(f"Error loading parent info: {e}")
            self.parent_info_text.setText("Error loading parent information")

    def add_parent_to_student(self):
        """Open dialog to add or select parent for the student"""
        if not self.current_student_id:
            QMessageBox.warning(self, "No Student", "Please save the student first before adding a parent.")
            return
    
        dialog = QDialog(self)
        dialog.setWindowTitle("Link Parent / Guardian")
        dialog.resize(600, 400)
        dialog.setModal(True)
    
        layout = QVBoxLayout(dialog)
    
        # Search bar
        search_layout = QHBoxLayout()
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Search parents by name, phone, or email...")
        search_btn = QPushButton("Search")
        search_layout.addWidget(search_edit)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)
    
        # Parents table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Name", "Relation", "Phone", "Email", "Select"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(table)
    
        # Role checkboxes
        role_group = QGroupBox("Parent Roles")
        role_layout = QGridLayout()
        role_group.setLayout(role_layout)
    
        is_primary_check = QCheckBox("Primary Contact")
        is_primary_check.setChecked(True)
        is_payer_check = QCheckBox("Fee Payer")
        is_payer_check.setChecked(True)
        is_emergency_check = QCheckBox("Emergency Contact")
        is_emergency_check.setChecked(True)
    
        relation_edit = QLineEdit("Guardian")
        relation_edit.setPlaceholderText("e.g., Father, Mother, Guardian")
    
        role_layout.addWidget(QLabel("Relation:"), 0, 0)
        role_layout.addWidget(relation_edit, 0, 1)
        role_layout.addWidget(is_primary_check, 1, 0)
        role_layout.addWidget(is_payer_check, 1, 1)
        role_layout.addWidget(is_emergency_check, 2, 0, 1, 2)
    
        layout.addWidget(role_group)
    
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Link Parent")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
        # Load parents
        def load_parents():
            search_term = search_edit.text().strip()
            table.setRowCount(0)
            try:
                if search_term:
                    query = """
                        SELECT id, full_name, relation, phone, email
                        FROM parents
                        WHERE is_active = TRUE
                        AND (full_name LIKE %s OR phone LIKE %s OR email LIKE %s)
                        ORDER BY full_name
                    """
                    params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
                else:
                    query = """
                        SELECT id, full_name, relation, phone, email
                        FROM parents
                        WHERE is_active = TRUE
                        ORDER BY full_name
                    """
                    params = []
    
                self.cursor.execute(query, params)
                parents = self.cursor.fetchall()
    
                table.setRowCount(len(parents))
                for row_idx, parent in enumerate(parents):
                    for col_idx, data in enumerate(parent[1:]):  # Skip ID
                        table.setItem(row_idx, col_idx, QTableWidgetItem(str(data) if data else "N/A"))
    
                    # Select button
                    select_btn = QPushButton("Select")
                    select_btn.setProperty("parent_id", parent[0])
                    select_btn.setProperty("full_name", parent[1])
                    select_btn.setProperty("relation", parent[2])
                    select_btn.clicked.connect(lambda _, btn=select_btn: on_parent_selected(btn))
                    table.setCellWidget(row_idx, 4, select_btn)
    
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to load parents: {str(e)}")
    
        def on_parent_selected(button):
            self.selected_parent_id = button.property("parent_id")
            self.selected_parent_name = button.property("full_name")
            relation_edit.setText(button.property("relation") or "Guardian")
            QMessageBox.information(dialog, "Selected", f"Parent selected: {self.selected_parent_name}")
    
        search_btn.clicked.connect(load_parents)
        load_parents()  # Load on open
    
        # Handle save
        def on_save():
            if not hasattr(self, 'selected_parent_id'):
                QMessageBox.warning(dialog, "No Selection", "Please select a parent first.")
                return
    
            relation = relation_edit.text().strip()
            is_primary = is_primary_check.isChecked()
            is_payer = is_payer_check.isChecked()
            is_emergency = is_emergency_check.isChecked()
    
            if not relation:
                QMessageBox.warning(dialog, "Input Required", "Please enter the relation type.")
                return
    
            try:
                # Prevent duplicate links
                self.cursor.execute("""
                    SELECT id FROM student_parent
                    WHERE student_id = %s AND parent_id = %s
                """, (self.current_student_id, self.selected_parent_id))
                if self.cursor.fetchone():
                    QMessageBox.warning(dialog, "Already Linked", "This parent is already linked to the student.")
                    return
    
                # If marking as primary, remove primary from others
                if is_primary:
                    self.cursor.execute("""
                        UPDATE student_parent SET is_primary_contact = FALSE
                        WHERE student_id = %s AND is_primary_contact = TRUE
                    """, (self.current_student_id,))
    
                # Insert new relationship
                self.cursor.execute("""
                    INSERT INTO student_parent (
                        student_id, parent_id, relation_type,
                        is_primary_contact, is_fee_payer, is_emergency_contact
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    self.current_student_id,
                    self.selected_parent_id,
                    relation,
                    is_primary,
                    is_payer,
                    is_emergency
                ))
                self.db_connection.commit()
    
                QMessageBox.information(dialog, "Success", "Parent linked successfully!")
                dialog.accept()
                self.load_student_parents()  # Refresh parent list in form
            except Exception as e:
                self.db_connection.rollback()
                QMessageBox.critical(dialog, "Error", f"Failed to link parent: {str(e)}")
    
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
    
        dialog.exec()

    def search_students(self):
        """Search students from form tab"""
        search_term = self.search_entry.text().strip()
        
        if not search_term:
            self.load_students()
            return
        
        self.search_students_common(search_term)

    def search_students_list(self):
        """Search students from list tab"""
        search_term = self.list_search_entry.text().strip()
        
        if not search_term:
            self.load_students()
            return
        
        self.search_students_common(search_term)

    def search_students_common(self, search_term):
        """Common search functionality"""
        try:
            query = '''
                SELECT s.id, s.regNo, s.first_name, s.surname, s.sex, 
                       s.grade_applied_for, s.class_year, s.is_active, 
                       s.email, s.enrollment_date,
                       GROUP_CONCAT(DISTINCT p.full_name SEPARATOR ', ') as parents
                FROM students s
                LEFT JOIN student_parent sp ON s.id = sp.student_id
                LEFT JOIN parents p ON sp.parent_id = p.id AND p.is_active = TRUE
                WHERE s.is_active = TRUE
                AND (s.first_name LIKE %s OR s.surname LIKE %s OR s.regNo LIKE %s 
                     OR p.full_name LIKE %s)
                GROUP BY s.id
                ORDER BY s.surname, s.first_name
                LIMIT 100
            '''
            like_term = f"%{search_term}%"
            self.cursor.execute(query, (like_term, like_term, like_term, like_term))
            students = self.cursor.fetchall()
            
            self.update_students_table(students)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Search failed: {str(e)}")

    def clear_search(self):
        """Clear search in form tab"""
        self.search_entry.clear()
        self.load_students()

    def clear_list_search(self):
        """Clear search in list tab"""
        self.list_search_entry.clear()
        self.load_students()

    def on_student_select(self, row, col):
        """Handle student selection from table"""
        try:
            item = self.students_table.item(row, 0)  # Get ID from first column
            if item:
                self.current_student_id = int(item.text())
                print(f"Selected student ID: {self.current_student_id}")
        except Exception as e:
            print(f"Error selecting student: {e}")

    def edit_selected_student(self):
        """Load selected student for editing"""
        if not self.current_student_id:
            QMessageBox.warning(self, "No Selection", "Please select a student from the table first.")
            return
        
        self.load_student_details(self.current_student_id)
        self.tabs.setCurrentIndex(0)  # Switch to form tab
        
        # Get student name for confirmation
        student_name = self.full_name_entry.text().strip()
        QMessageBox.information(self, "Student Loaded", 
                              f"Student '{student_name}' loaded for editing.")

    def load_student_details(self, student_id):
        """Load student details into form for editing"""
        try:
            query = '''
                SELECT first_name, surname, sex, date_of_birth, email, 
                       grade_applied_for, class_year, enrollment_date, regNo, 
                       religion, citizenship, last_school, medical_conditions, 
                       allergies, is_active, photo_path
                FROM students 
                WHERE id = %s
            '''
            self.cursor.execute(query, (student_id,))
            student = self.cursor.fetchone()
            
            if not student:
                QMessageBox.warning(self, "Error", "Student not found")
                return
            
            # Clear form first
            self.clear_form()
            
            # Set current student ID
            self.current_student_id = student_id
            
            # Populate form fields
            self.first_name_entry.setText(student[0] or "")
            self.surname_entry.setText(student[1] or "")
            self.sex_combo.setCurrentText(student[2] or "Male")
            
            # Handle date of birth
            if student[3]:
                if isinstance(student[3], str):
                    dob = QDate.fromString(student[3], "yyyy-MM-dd")
                else:
                    dob = QDate(student[3])
                self.dob_edit.setDate(dob)
            
            self.email_entry.setText(student[4] or "")
            self.grade_combo.setCurrentText(student[5] or "")
            self.class_year_entry.setText(student[6] or "")
            
            # Handle enrollment date
            if student[7]:
                if isinstance(student[7], str):
                    enrollment = QDate.fromString(student[7], "yyyy-MM-dd")
                else:
                    enrollment = QDate(student[7])
                self.enrollment_date.setDate(enrollment)
            
            self.reg_no_entry.setText(student[8] or "")
            self.religion_entry.setText(student[9] or "")
            self.citizenship_entry.setText(student[10] or "")
            self.last_school_entry.setText(student[11] or "")
            self.medical_text.setPlainText(student[12] or "")
            self.allergies_text.setPlainText(student[13] or "")
            self.is_active_check.setChecked(bool(student[14]))
            
            # Load photo if exists
            if student[15] and os.path.exists(student[15]):
                pixmap = QPixmap(student[15])
                scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.photo_label.setPixmap(scaled_pixmap)
                self.photo_path = student[15]
            
            # Load associated parent
            self.load_student_parents(student_id)
            
        except Exception as e:
            print(f"Error loading student details: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load student details: {str(e)}")

    def load_student_parents(self):
        """Load all parents linked to the current student"""
        if not self.current_student_id:
            self.parents_table.setRowCount(0)
            return
    
        try:
            query = """
                SELECT p.full_name, sp.relation_type, p.phone, p.email,
                       CONCAT(
                           IF(sp.is_primary_contact, 'Primary', ''),
                           IF(sp.is_fee_payer AND sp.is_emergency_contact, ', Payer & Emergency', ''),
                           IF(sp.is_fee_payer AND NOT sp.is_emergency_contact, ', Payer', ''),
                           IF(sp.is_emergency_contact AND NOT sp.is_fee_payer, ', Emergency', '')
                       ) AS roles
                FROM student_parent sp
                JOIN parents p ON sp.parent_id = p.id
                WHERE sp.student_id = %s AND p.is_active = TRUE
                ORDER BY sp.is_primary_contact DESC
            """
            self.cursor.execute(query, (self.current_student_id,))
            parents = self.cursor.fetchall()
    
            self.parents_table.setRowCount(len(parents))
            for row_idx, parent in enumerate(parents):
                for col_idx, data in enumerate(parent):
                    text = str(data).strip(" ,") if data else "N/A"
                    self.parents_table.setItem(row_idx, col_idx, QTableWidgetItem(text))
        except Exception as e:
            print(f"Error loading student parents: {e}")
            QMessageBox.warning(self, "Warning", "Could not load parent list.")

    def view_student_details(self):
        """Show student details popup"""
        if not self.current_student_id:
            QMessageBox.warning(self, "No Selection", "Please select a student from the table first.")
            return
        
        try:
            popup = StudentDetailsPopup(self, self.current_student_id, self.user_session)
            popup.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show student details: {str(e)}")

    def save_student(self):
        """Save new student to database"""
        if not self.validate_form():
            return
        
        if self.current_student_id:
            QMessageBox.information(self, "Info", "Student already exists. Use Update instead.")
            return
        
        try:
            # Prepare data
            first_name = self.first_name_entry.text().strip()
            surname = self.surname_entry.text().strip()
            full_name = f"{first_name} {surname}".strip()
            
            # Convert dates
            dob = self.dob_edit.date().toPython()
            enrollment = self.enrollment_date.date().toPython()
            
            # Insert student
            query = '''
                INSERT INTO students (
                    school_id, first_name, surname, full_name, sex, date_of_birth,
                    email, grade_applied_for, class_year, enrollment_date, regNo,
                    religion, citizenship, last_school, medical_conditions, allergies,
                    is_active, photo_path
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            '''
            
            school_id = 1  # Default school ID - modify as needed
            
            values = (
                school_id, first_name, surname, full_name, self.sex_combo.currentText(),
                dob, self.email_entry.text().strip(), self.grade_combo.currentText(),
                self.class_year_entry.text().strip(), enrollment, self.reg_no_entry.text().strip(),
                self.religion_entry.text().strip(), self.citizenship_entry.text().strip(),
                self.last_school_entry.text().strip(), self.medical_text.toPlainText(),
                self.allergies_text.toPlainText(), self.is_active_check.isChecked(),
                self.photo_path
            )
            
            self.cursor.execute(query, values)
            student_id = self.cursor.lastrowid
            
            # Link to parent if selected
            parent_id = self.parent_dropdown.currentData()
            if parent_id:
                self.link_student_parent(student_id, parent_id)
            
            self.db_connection.commit()
            
            QMessageBox.information(self, "Success", "Student saved successfully!")
            self.clear_form()
            self.load_students()
            
        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save student: {str(e)}")

    def update_student(self):
        """Update existing student"""
        if not self.current_student_id:
            QMessageBox.warning(self, "Error", "No student selected for update")
            return
        
        if not self.validate_form():
            return
        
        try:
            # Prepare data
            first_name = self.first_name_entry.text().strip()
            surname = self.surname_entry.text().strip()
            full_name = f"{first_name} {surname}".strip()
            
            # Convert dates
            dob = self.dob_edit.date().toPython()
            enrollment = self.enrollment_date.date().toPython()
            
            # Update student
            query = '''
                UPDATE students SET
                    first_name = %s, surname = %s, full_name = %s, sex = %s,
                    date_of_birth = %s, email = %s, grade_applied_for = %s,
                    class_year = %s, enrollment_date = %s, regNo = %s,
                    religion = %s, citizenship = %s, last_school = %s,
                    medical_conditions = %s, allergies = %s, is_active = %s,
                    photo_path = %s
                WHERE id = %s
            '''
            
            values = (
                first_name, surname, full_name, self.sex_combo.currentText(),
                dob, self.email_entry.text().strip(), self.grade_combo.currentText(),
                self.class_year_entry.text().strip(), enrollment, self.reg_no_entry.text().strip(),
                self.religion_entry.text().strip(), self.citizenship_entry.text().strip(),
                self.last_school_entry.text().strip(), self.medical_text.toPlainText(),
                self.allergies_text.toPlainText(), self.is_active_check.isChecked(),
                self.photo_path, self.current_student_id
            )
            
            self.cursor.execute(query, values)
            
            # Update parent link if changed
            parent_id = self.parent_dropdown.currentData()
            self.update_student_parent(self.current_student_id, parent_id)
            
            self.db_connection.commit()
            
            QMessageBox.information(self, "Success", "Student updated successfully!")
            self.load_students()
            
        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update student: {str(e)}")

    def delete_student(self):
        """Delete (soft delete) selected student"""
        if not self.current_student_id:
            QMessageBox.warning(self, "Error", "No student selected for deletion")
            return
        
        # Confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this student?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Soft delete by setting is_active to False
                query = "UPDATE students SET is_active = FALSE WHERE id = %s"
                self.cursor.execute(query, (self.current_student_id,))
                self.db_connection.commit()
                
                QMessageBox.information(self, "Success", "Student deleted successfully!")
                self.clear_form()
                self.load_students()
                
            except Exception as e:
                self.db_connection.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete student: {str(e)}")

    def link_student_parent(self, student_id, parent_id, relation_type=None, is_primary=True):
        """Link student to parent"""
        try:
            if not relation_type:
                # Get relation type from parent record or use default
                self.cursor.execute("SELECT relation_type FROM parents WHERE id = %s", (parent_id,))
                result = self.cursor.fetchone()
                relation_type = result[0] if result and result[0] else "Guardian"
            
            query = '''
                INSERT INTO student_parent 
                (student_id, parent_id, relation_type, is_primary_contact, is_fee_payer, is_emergency_contact)
                VALUES (%s, %s, %s, %s, TRUE, TRUE)
                ON DUPLICATE KEY UPDATE
                relation_type = VALUES(relation_type),
                is_primary_contact = VALUES(is_primary_contact)
            '''
            
            self.cursor.execute(query, (student_id, parent_id, relation_type, is_primary))
            
        except Exception as e:
            print(f"Error linking student to parent: {e}")

    def update_student_parent(self, student_id, parent_id):
        """Update student-parent relationship"""
        try:
            # Remove existing relationships
            self.cursor.execute("DELETE FROM student_parent WHERE student_id = %s", (student_id,))
            
            # Add new relationship if parent selected
            if parent_id:
                self.link_student_parent(student_id, parent_id)
                
        except Exception as e:
            print(f"Error updating student-parent relationship: {e}")

    def validate_form(self):
        """Validate form data"""
        if not self.first_name_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "First name is required")
            self.first_name_entry.setFocus()
            return False
        
        if not self.surname_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Surname is required")
            self.surname_entry.setFocus()
            return False
        
        if not self.reg_no_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Registration number is required")
            self.reg_no_entry.setFocus()
            return False
        
        # Check if registration number already exists (for new students or different student)
        reg_no = self.reg_no_entry.text().strip()
        if self.current_student_id:
            query = "SELECT id FROM students WHERE regNo = %s AND id != %s AND is_active = TRUE"
            self.cursor.execute(query, (reg_no, self.current_student_id))
        else:
            query = "SELECT id FROM students WHERE regNo = %s AND is_active = TRUE"
            self.cursor.execute(query, (reg_no,))
        
        if self.cursor.fetchone():
            QMessageBox.warning(self, "Validation Error", 
                              "Registration number already exists for another student")
            self.reg_no_entry.setFocus()
            return False
        
        return True

    def clear_form(self):
        """Clear all form fields"""
        # Clear text fields
        self.first_name_entry.clear()
        self.surname_entry.clear()
        self.full_name_entry.clear()
        self.email_entry.clear()
        self.reg_no_entry.clear()
        self.religion_entry.clear()
        self.citizenship_entry.clear()
        self.last_school_entry.clear()
        self.class_year_entry.clear()
        self.medical_text.clear()
        self.allergies_text.clear()
        self.parent_search_entry.clear()
        
        # Reset dropdowns
        self.sex_combo.setCurrentIndex(0)
        self.grade_combo.setCurrentIndex(0)
        self.parent_dropdown.setCurrentIndex(0)
        
        # Reset dates
        self.dob_edit.setDate(QDate.currentDate().addYears(-10))
        self.enrollment_date.setDate(QDate.currentDate())
        
        # Reset photo
        self.remove_photo()
        
        # Reset checkboxes
        self.is_active_check.setChecked(True)
        
        # Clear parent info
        self.parent_info_text.setText("No parent selected")
        
        # Reset current student ID
        self.current_student_id = None

    def export_to_excel(self):
        """Export student data to Excel"""
        try:
            # Get all student data
            query = '''
                SELECT s.regNo, s.first_name, s.surname, s.sex, s.date_of_birth,
                       s.email, s.grade_applied_for, s.class_year, s.enrollment_date,
                       s.religion, s.citizenship, s.last_school, s.medical_conditions,
                       s.allergies, 
                       GROUP_CONCAT(DISTINCT CONCAT(p.full_name, ' (', sp.relation_type, ')') 
                                   SEPARATOR '; ') as parents
                FROM students s
                LEFT JOIN student_parent sp ON s.id = sp.student_id
                LEFT JOIN parents p ON sp.parent_id = p.id AND p.is_active = TRUE
                WHERE s.is_active = TRUE
                GROUP BY s.id
                ORDER BY s.surname, s.first_name
            '''
            
            self.cursor.execute(query)
            data = self.cursor.fetchall()
            
            if not data:
                QMessageBox.information(self, "No Data", "No student data to export")
                return
            
            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Students"
            
            # Headers
            headers = [
                "Reg No", "First Name", "Surname", "Sex", "Date of Birth",
                "Email", "Grade", "Class Year", "Enrollment Date", "Religion",
                "Citizenship", "Last School", "Medical Conditions", "Allergies", "Parents"
            ]
            ws.append(headers)
            
            # Add data
            for row in data:
                ws.append(list(row))
            
            # Format headers
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            
            # Auto-adjust column widths
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
                
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = max(adjusted_width, 10)
            
            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"students_export_{timestamp}.xlsx"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Excel File", default_filename, "Excel Files (*.xlsx)"
            )
            
            if file_path:
                wb.save(file_path)
                QMessageBox.information(self, "Success", 
                                      f"Student data exported successfully!\nFile: {file_path}")
                
                # Try to open the file
                try:
                    if platform.system() == "Windows":
                        os.startfile(file_path)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", file_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", file_path])
                except Exception as e:
                    print(f"Could not open file: {e}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export to Excel: {str(e)}")

    def generate_pdf_report(self):
        """Generate PDF report for selected student"""
        if not self.current_student_id:
            QMessageBox.warning(self, "No Selection", "Please select a student first.")
            return
        
        try:
            # Get student data
            query = '''
                SELECT s.first_name, s.surname, s.sex, s.date_of_birth, s.email,
                       s.grade_applied_for, s.class_year, s.enrollment_date, s.regNo,
                       s.religion, s.citizenship, s.last_school, s.medical_conditions, 
                       s.allergies,
                       GROUP_CONCAT(DISTINCT CONCAT(p.full_name, ' (', sp.relation_type, ')') 
                                   SEPARATOR ', ') as parents
                FROM students s
                LEFT JOIN student_parent sp ON s.id = sp.student_id
                LEFT JOIN parents p ON sp.parent_id = p.id AND p.is_active = TRUE
                WHERE s.id = %s
                GROUP BY s.id
            '''
            
            self.cursor.execute(query, (self.current_student_id,))
            student = self.cursor.fetchone()
            
            if not student:
                QMessageBox.warning(self, "Error", "Student data not found")
                return
            
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Header
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "WINSPIRE LEARNING HUB", 0, 1, "C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 5, "Student Profile Report", 0, 1, "C")
            pdf.ln(10)
            
            # Student Information
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 8, "STUDENT INFORMATION", 0, 1)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_font("Arial", "", 11)
            
            # Data fields
            fields = [
                ("Full Name", f"{student[0]} {student[1]}"),
                ("Registration Number", student[8]),
                ("Sex", student[2]),
                ("Date of Birth", str(student[3]) if student[3] else "N/A"),
                ("Email", student[4] or "N/A"),
                ("Grade Applied For", student[5] or "N/A"),
                ("Class Year", student[6] or "N/A"),
                ("Enrollment Date", str(student[7]) if student[7] else "N/A"),
                ("Religion", student[9] or "N/A"),
                ("Citizenship", student[10] or "N/A"),
                ("Last School", student[11] or "N/A"),
                ("Parents/Guardians", student[14] or "N/A")
            ]
            
            for label, value in fields:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(50, 8, f"{label}:", 0, 0)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, str(value), 0, 1)
            
            # Medical Information
            pdf.ln(5)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 8, "MEDICAL INFORMATION", 0, 1)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 8, "Medical Conditions:", 0, 1)
            pdf.set_font("Arial", "", 10)
            medical_text = student[12] or "None reported"
            pdf.multi_cell(0, 6, medical_text)
            pdf.ln(3)
            
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 8, "Allergies:", 0, 1)
            pdf.set_font("Arial", "", 10)
            allergies_text = student[13] or "None reported"
            pdf.multi_cell(0, 6, allergies_text)
            
            # Footer
            pdf.ln(10)
            pdf.set_font("Arial", "I", 8)
            pdf.cell(0, 5, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "C")
            
            # Save PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            student_name = f"{student[0]}_{student[1]}".replace(" ", "_")
            default_filename = f"student_profile_{student_name}_{timestamp}.pdf"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF File", default_filename, "PDF Files (*.pdf)"
            )
            
            if file_path:
                pdf.output(file_path)
                QMessageBox.information(self, "Success", 
                                      f"PDF report generated successfully!\nFile: {file_path}")
                
                # Try to open the PDF
                try:
                    if platform.system() == "Windows":
                        os.startfile(file_path)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", file_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", file_path])
                except Exception as e:
                    print(f"Could not open PDF: {e}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {str(e)}")


def main():
    """Main function to run the application"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Students Management System")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Winspire Learning Hub")
    
    # Create and show the main window
    window = StudentsForm()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


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