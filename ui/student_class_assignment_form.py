# student_class_assignment_form.py
import sys
import os
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
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
from fpdf import FPDF
import platform
import subprocess
from ui.audit_base_form import AuditBaseForm
from models.models import get_db_connection


class SearchableComboBox(QComboBox):
    """Enhanced ComboBox with search functionality"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.original_values = []
        self.lineEdit().textEdited.connect(self.filter_values)
        self.lineEdit().returnPressed.connect(self.on_return_pressed)
        
    def setValues(self, values):
        """Set the values for the combobox"""
        self.original_values = values
        self.clear()
        self.addItems(values)
        
    def filter_values(self, text):
        """Filter values based on typed text"""
        if not text:
            self.clear()
            self.addItems(self.original_values)
            return
            
        filtered_values = [
            value for value in self.original_values 
            if text.lower() in value.lower()
        ]
        
        self.clear()
        self.addItems(filtered_values)
        self.showPopup()
        
    def on_return_pressed(self):
        """Handle return pressed to select the first item"""
        if self.count() > 0:
            self.setCurrentIndex(0)

class StudentClassAssignmentForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.user_session = user_session
        self.selected_assignment_id = None
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True)
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        # Data storage for dropdowns
        self.all_students = []
        self.all_classes = []
        self.all_terms = []
        self.all_academic_years = []
        self.all_grade_levels = []
        self.current_table_data = []
        self.current_assignments_data = []
        
        # Filtered data for the new UI flow
        self.filtered_classes_by_level = []
        self.filtered_students_by_class = []
        self.available_streams = []
        
        self.setup_ui()
        self.load_dropdown_data()
        self.load_data()
        
    def setup_ui(self):
        """Setup the main UI components"""
        self.setWindowTitle("Student Class Assignments")
        self.setMinimumSize(1200, 800)
        
        # Main layout
        main_layout = QHBoxLayout(self)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.create_table_panel(left_layout)
        
        # Right panel - Form
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.create_form_panel(right_layout)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])  # 40% table, 60% form
        
        main_layout.addWidget(splitter)
        
    def create_table_panel(self, layout):
        """Create the table panel for displaying student class assignments"""
        # Title
        title_label = QLabel("Student Class Assignments")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # Action buttons frame
        action_frame = QHBoxLayout()
        
        # Promotion button
        promote_btn = QPushButton("📈 Promote")
        promote_btn.setFont(QFont("Arial", 10))
        promote_btn.setStyleSheet("background-color: #28A745; color: white;")
        promote_btn.clicked.connect(self.open_promotion_popup)
        action_frame.addWidget(promote_btn)
        
        # Demotion button
        demote_btn = QPushButton("📉 Demote")
        demote_btn.setFont(QFont("Arial", 10))
        demote_btn.setStyleSheet("background-color: #DC3545; color: white;")
        demote_btn.clicked.connect(self.open_demotion_popup)
        action_frame.addWidget(demote_btn)
        
        # Export button
        export_btn = QPushButton("📄 Export PDF")
        export_btn.setFont(QFont("Arial", 10))
        export_btn.setStyleSheet("background-color: #007bff; color: white;")
        export_btn.clicked.connect(self.export_to_pdf)
        action_frame.addWidget(export_btn)
        
        layout.addLayout(action_frame)
        
        # Search components
        search_frame = QHBoxLayout()
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search assignments...")
        self.search_entry.textChanged.connect(self.search_assignments)
        search_frame.addWidget(self.search_entry)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.search_assignments)
        search_frame.addWidget(search_btn)
        
        layout.addLayout(search_frame)
        
        # Table
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        self.table_widget.setHorizontalHeaderLabels(["Student", "Grade", "Class", "Term", "Year", "Status"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.cellClicked.connect(self.on_table_row_click)
        
        layout.addWidget(self.table_widget)
        
    def create_form_panel(self, layout):
        """Create the form panel with improved UI flow"""
        # Form title
        form_title = QLabel("Assignment Details")
        form_title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(form_title)
        
        # Scroll area for form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QVBoxLayout(scroll_widget)
        
        # === NEW UI FLOW ===
        
        # STEP 1: Level (O-Level/A-Level)
        level_label = QLabel("📚 Education Level *")
        level_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(level_label)
        
        self.level_dropdown = QComboBox()
        self.level_dropdown.currentTextChanged.connect(self.on_level_selection_changed)
        form_layout.addWidget(self.level_dropdown)
        
        # STEP 2: Class Name (filtered by level)
        class_label = QLabel("🏫 Class Name *")
        class_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(class_label)
        
        self.class_name_dropdown = QComboBox()
        self.class_name_dropdown.currentTextChanged.connect(self.on_class_name_selection_changed)
        form_layout.addWidget(self.class_name_dropdown)
        
        # STEP 3: Stream (filtered by class)
        stream_label = QLabel("🎯 Stream *")
        stream_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(stream_label)
        
        self.stream_dropdown = QComboBox()
        self.stream_dropdown.currentTextChanged.connect(self.on_stream_selection_changed)
        form_layout.addWidget(self.stream_dropdown)
        
        # STEP 4: Students (filtered by class and stream)
        student_label = QLabel("👨‍🎓 Student *")
        student_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(student_label)
        
        self.student_dropdown = SearchableComboBox()
        form_layout.addWidget(self.student_dropdown)
        
        # === ASSIGNMENT DETAILS ===
        
        # Academic Year dropdown
        year_label = QLabel("📅 Academic Year *")
        year_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(year_label)
        
        self.academic_year_dropdown = QComboBox()
        form_layout.addWidget(self.academic_year_dropdown)
        
        # Term dropdown
        term_label = QLabel("📊 Term *")
        term_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(term_label)
        
        self.term_dropdown = QComboBox()
        form_layout.addWidget(self.term_dropdown)
        
        # Status dropdown
        status_label = QLabel("📋 Status *")
        status_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(status_label)
        
        self.status_dropdown = QComboBox()
        self.status_dropdown.addItems(["Promoted", "Completed", "Repeated"])
        form_layout.addWidget(self.status_dropdown)
        
        # Assignment Date (readonly display)
        date_label = QLabel("📆 Assignment Date")
        date_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(date_label)
        
        self.assignment_date_entry = QLineEdit()
        self.assignment_date_entry.setReadOnly(True)
        self.assignment_date_entry.setPlaceholderText("Will be set automatically")
        form_layout.addWidget(self.assignment_date_entry)
        
        # Notes
        notes_label = QLabel("📝 Notes")
        notes_label.setFont(QFont("Arial", 11, QFont.Bold))
        form_layout.addWidget(notes_label)
        
        self.notes_textbox = QTextEdit()
        self.notes_textbox.setMaximumHeight(100)
        form_layout.addWidget(self.notes_textbox)
        
        # Is Current checkbox
        self.is_current_checkbox = QCheckBox("✅ Current Assignment")
        self.is_current_checkbox.setChecked(True)
        form_layout.addWidget(self.is_current_checkbox)
        
        # Action buttons
        buttons_frame = QHBoxLayout()
        
        # Save button
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("background-color: #28A745; color: white;")
        save_btn.clicked.connect(self.save_assignment)
        buttons_frame.addWidget(save_btn)
        
        # Update button
        update_btn = QPushButton("✏️ Update")
        update_btn.setStyleSheet("background-color: #007bff; color: white;")
        update_btn.clicked.connect(self.update_assignment)
        buttons_frame.addWidget(update_btn)
        
        # Delete button
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setStyleSheet("background-color: #DC3545; color: white;")
        delete_btn.clicked.connect(self.delete_assignment)
        buttons_frame.addWidget(delete_btn)
        
        # Clear button
        clear_btn = QPushButton("🔄 Clear")
        clear_btn.setStyleSheet("background-color: #6C757D; color: white;")
        clear_btn.clicked.connect(self.clear_form)
        buttons_frame.addWidget(clear_btn)
        
        form_layout.addLayout(buttons_frame)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh All Data")
        refresh_btn.setStyleSheet("background-color: #17A2B8; color: white;")
        refresh_btn.clicked.connect(self.refresh_all_data)
        form_layout.addWidget(refresh_btn)
        
        # Status label
        self.status_label = QLabel("Ready to assign students")
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")
        form_layout.addWidget(self.status_label)
        
        # Add spacer
        form_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
    def load_dropdown_data(self):
        """Load all dropdown data with the new structure"""
        try:
            # Load distinct education levels (O-Level/A-Level)
            self.cursor.execute("""
                SELECT DISTINCT level 
                FROM classes 
                WHERE level IS NOT NULL AND level != ''
                ORDER BY level
            """)
            levels = [row[0] for row in self.cursor.fetchall()]
            self.level_dropdown.clear()
            if levels:
                self.level_dropdown.addItems(levels)
            else:
                self.level_dropdown.addItem("No levels found")
            self.all_grade_levels = levels
            
            # Load all students with their grade information
            self.cursor.execute("""
                SELECT id, full_name, grade_applied_for 
                FROM students 
                WHERE full_name IS NOT NULL AND full_name != ''
                ORDER BY full_name
            """)
            self.all_students = self.cursor.fetchall()
            
            # Load all classes with their details
            self.cursor.execute("""
                SELECT id, class_name, stream, level 
                FROM classes 
                WHERE class_name IS NOT NULL AND class_name != ''
                ORDER BY 
                    level,
                    CASE 
                        WHEN class_name LIKE 'S%' THEN CAST(SUBSTR(class_name, 2) AS SIGNED)
                        ELSE 999 
                    END,
                    stream
            """)
            self.all_classes = self.cursor.fetchall()
            
            # Load terms
            self.cursor.execute("SELECT id, term_name FROM terms ORDER BY term_name")
            self.all_terms = self.cursor.fetchall()
            self.term_dropdown.clear()
            if self.all_terms:
                terms = [row[1] for row in self.all_terms]
                self.term_dropdown.addItems(terms)
            else:
                self.term_dropdown.addItem("No terms found")
            
            # Load academic years
            self.cursor.execute("SELECT id, year_name FROM academic_years ORDER BY year_name DESC")
            self.all_academic_years = self.cursor.fetchall()
            self.academic_year_dropdown.clear()
            if self.all_academic_years:
                academic_years = [row[1] for row in self.all_academic_years]
                self.academic_year_dropdown.addItems(academic_years)
            else:
                self.academic_year_dropdown.addItem("No academic years found")
            
            self.status_label.setText(f"Data loaded: {len(self.all_students)} students, {len(self.all_classes)} classes")
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")
            print(f"Database error: {e}")
            traceback.print_exc()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")
            print(f"Unexpected error: {e}")
            traceback.print_exc()
            
    def on_level_selection_changed(self, selected_level):
        """Filter classes by selected education level"""
        if not selected_level or selected_level == "No levels found":
            self.class_name_dropdown.clear()
            self.class_name_dropdown.addItem("Select education level first")
            self.student_dropdown.setValues(["Select level first..."])
            return
        
        # Get unique class names for this level
        unique_classes = set()
        self.filtered_classes_by_level = []
        
        for class_id, class_name, stream, level in self.all_classes:
            if level == selected_level:
                unique_classes.add(class_name)
                self.filtered_classes_by_level.append((class_id, class_name, stream, level))
        
        # Update class dropdown
        class_names = sorted(list(unique_classes))
        self.class_name_dropdown.clear()
        if class_names:
            self.class_name_dropdown.addItems(class_names)
        else:
            self.class_name_dropdown.addItem("No classes found")
        
        # Reset student and stream dropdowns
        self.student_dropdown.setValues(["Select class first..."])
        self.stream_dropdown.clear()
        self.stream_dropdown.addItem("Select student first...")
        
    def on_class_name_selection_changed(self, selected_class_name):
        """Load students for selected class (filter by grade_applied_for)"""
        selected_level = self.level_dropdown.currentText()
        
        if not selected_class_name or not selected_level or selected_class_name == "Select education level first":
            self.student_dropdown.setValues(["Select class first..."])
            return
        
        # Find the class details to get the grade level
        class_grade = None
        for class_id, class_name, stream, level in self.filtered_classes_by_level:
            if class_name == selected_class_name and level == selected_level:
                class_grade = class_name  # Assuming class_name matches grade (e.g., "S2")
                break
        
        if not class_grade:
            self.student_dropdown.setValues(["No matching class found"])
            return
        
        # Filter students by grade_applied_for
        matching_students = []
        for student_id, full_name, grade in self.all_students:
            if grade == class_grade:
                # Check if student already has current assignment
                self.cursor.execute("""
                    SELECT sca.id, c.class_name, c.stream 
                    FROM student_class_assignments sca
                    JOIN classes c ON sca.class_id = c.id
                    WHERE sca.student_id = %s AND sca.is_current = 1
                """, (student_id,))
                current_assignment = self.cursor.fetchone()
                
                status = ""
                if current_assignment:
                    stream = current_assignment[2] if current_assignment[2] else "No Stream"
                    status = f" [Currently in {current_assignment[1]} {stream}]"
                
                matching_students.append(f"{full_name} (ID: {student_id}){status}")
        
        if matching_students:
            self.student_dropdown.setValues(matching_students)
            status_msg = f"{len(matching_students)} students in {class_grade}"
        else:
            self.student_dropdown.setValues([f"No students in {class_grade}"])
            status_msg = f"No students in {class_grade}"
        
        # Load available streams for this class
        streams = set()
        for class_id, class_name, stream, level in self.filtered_classes_by_level:
            if class_name == selected_class_name and level == selected_level:
                stream_display = stream if stream else "No Stream"
                streams.add(stream_display)
        
        self.available_streams = sorted(list(streams))
        self.stream_dropdown.clear()
        if self.available_streams:
            self.stream_dropdown.addItems(self.available_streams)
        else:
            self.stream_dropdown.addItem("No streams available")
        
        self.status_label.setText(status_msg)
        
    def on_stream_selection_changed(self, selected_stream):
        """Load students for the selected class and stream combination"""
        try:
            selected_level = self.level_dropdown.currentText()
            selected_class_name = self.class_name_dropdown.currentText()
            
            if not selected_stream or not selected_level or not selected_class_name:
                self.student_dropdown.setValues(["Select stream first..."])
                return
            
            # Find the matching class record
            target_class_id = None
            for class_id, class_name, stream, level in self.filtered_classes_by_level:
                stream_match = (stream == selected_stream) if selected_stream != "No Stream" else (stream is None or stream == "")
                if class_name == selected_class_name and level == selected_level and stream_match:
                    target_class_id = class_id
                    break
            
            if not target_class_id:
                self.student_dropdown.setValues(["No matching class found"])
                return
            
            # Get ALL students who match the grade level for this class
            self.cursor.execute("""
                SELECT DISTINCT s.id, s.full_name, s.grade_applied_for,
                       CASE 
                           WHEN EXISTS (
                               SELECT 1 FROM student_class_assignments sca2 
                               WHERE sca2.student_id = s.id 
                               AND sca2.class_id = %s 
                               AND sca2.is_current = 1
                           ) THEN 'current_class'
                           WHEN EXISTS (
                               SELECT 1 FROM student_class_assignments sca3 
                               WHERE sca3.student_id = s.id 
                               AND sca3.is_current = 1
                           ) THEN 'other_class'
                           ELSE 'unassigned'
                       END as assignment_status
                FROM students s
                WHERE s.grade_applied_for = %s
                ORDER BY s.full_name
            """, (target_class_id, selected_level))
            
            all_matching_students = self.cursor.fetchall()
            
            # Update student dropdown with enhanced status information
            if all_matching_students:
                student_list = []
                for student in all_matching_students:
                    student_id, full_name, grade, status = student
                    display_text = f"{full_name} (ID: {student_id})"
                    
                    if status == 'current_class':
                        display_text += " [Currently in this class]"
                    elif status == 'other_class':
                        # Get the current class name for better information
                        self.cursor.execute("""
                            SELECT c.class_name, c.stream
                            FROM student_class_assignments sca
                            JOIN classes c ON sca.class_id = c.id
                            WHERE sca.student_id = %s AND sca.is_current = 1
                            LIMIT 1
                        """, (student_id,))
                        current_class = self.cursor.fetchone()
                        if current_class:
                            current_class_display = f"{current_class[0]} {current_class[1]}" if current_class[1] else current_class[0]
                            display_text += f" [Currently in {current_class_display}]"
                        else:
                            display_text += " [Assigned elsewhere]"
                    else:
                        display_text += " [Unassigned]"
                    
                    student_list.append(display_text)
                
                self.student_dropdown.setValues(student_list)
                self.filtered_students_by_class = all_matching_students
                
                # Count students by status
                current_count = sum(1 for s in all_matching_students if s[3] == 'current_class')
                other_count = sum(1 for s in all_matching_students if s[3] == 'other_class')
                unassigned_count = sum(1 for s in all_matching_students if s[3] == 'unassigned')
                
                status_msg = f"{selected_class_name} {selected_stream}: {len(all_matching_students)} students available"
                status_msg += f" (Current: {current_count}, Other classes: {other_count}, Unassigned: {unassigned_count})"
                
            else:
                self.student_dropdown.setValues([f"No students found for grade {selected_level}"])
                self.filtered_students_by_class = []
                status_msg = f"No students found matching grade level {selected_level}"
            
            self.status_label.setText(status_msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Stream selection error: {e}")
            print(f"Stream selection error: {e}")
            traceback.print_exc()
            
    def get_selected_id(self, dropdown, data_list=None):
        """Extract ID from dropdown selection"""
        try:
            selection = dropdown.currentText()
            if not selection:
                return None
                
            if dropdown == self.student_dropdown:
                # Extract ID from enhanced format: "Name (ID: X) [Status]"
                if hasattr(self, 'filtered_students_by_class') and self.filtered_students_by_class:
                    for student in self.filtered_students_by_class:
                        student_id = student[0]
                        if f"(ID: {student_id})" in selection:
                            return student_id
                
                # Fallback: try to extract ID from the selection string directly
                import re
                id_match = re.search(r'\(ID: (\d+)\)', selection)
                if id_match:
                    return int(id_match.group(1))
                    
            elif dropdown == self.term_dropdown:
                for term in self.all_terms:
                    if term[1] == selection:
                        return term[0]
            elif dropdown == self.academic_year_dropdown:
                for year in self.all_academic_years:
                    if year[1] == selection:
                        return year[0]
            
            return None
                
        except (IndexError, ValueError) as e:
            print(f"Error getting selected ID: {e}")
            return None
            
    def get_selected_class_id(self):
        """Get the class ID for the selected level, class name, and stream combination"""
        try:
            selected_level = self.level_dropdown.currentText()
            selected_class_name = self.class_name_dropdown.currentText()
            selected_stream = self.stream_dropdown.currentText()
            
            if not all([selected_level, selected_class_name, selected_stream]):
                return None
            
            # Find matching class
            for class_id, class_name, stream, level in self.filtered_classes_by_level:
                stream_match = (stream == selected_stream) if selected_stream != "No Stream" else (stream is None or stream == "")
                if class_name == selected_class_name and level == selected_level and stream_match:
                    return class_id
            
            return None
        except Exception as e:
            print(f"Error getting class ID: {e}")
            return None
            
    def validate_form(self):
        """Validate form inputs"""
        if not self.level_dropdown.currentText():
            QMessageBox.warning(self, "Validation Error", "Please select an education level")
            return False
            
        if not self.class_name_dropdown.currentText():
            QMessageBox.warning(self, "Validation Error", "Please select a class name")
            return False
        
        if not self.stream_dropdown.currentText():
            QMessageBox.warning(self, "Validation Error", "Please select a stream")
            return False
            
        student_id = self.get_selected_id(self.student_dropdown)
        if not student_id:
            QMessageBox.warning(self, "Validation Error", "Please select a valid student")
            return False
        
        class_id = self.get_selected_class_id()
        if not class_id:
            QMessageBox.warning(self, "Validation Error", "Invalid class selection")
            return False
        
        if not self.get_selected_id(self.academic_year_dropdown):
            QMessageBox.warning(self, "Validation Error", "Please select an academic year")
            return False
        
        if not self.get_selected_id(self.term_dropdown):
            QMessageBox.warning(self, "Validation Error", "Please select a term")
            return False
        
        if not self.status_dropdown.currentText():
            QMessageBox.warning(self, "Validation Error", "Please select a status")
            return False
        
        return True
        
    def check_duplicate_assignment(self, student_id, class_id, academic_year_id, term_id, exclude_id=None):
        """Check if the assignment already exists"""
        query = """
            SELECT id FROM student_class_assignments 
            WHERE student_id = %s AND class_id = %s AND academic_year_id = %s AND term_id = %s
        """
        params = [student_id, class_id, academic_year_id, term_id]
        
        if exclude_id:
            query += " AND id != %s"
            params.append(exclude_id)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchone() is not None
        
    def save_assignment(self):
        """Save new student class assignment"""
        # Validate required fields first
        if not self.validate_form():
            return
        
        try:
            # Get all selected values
            student_id = self.get_selected_id(self.student_dropdown)
            selected_level = self.level_dropdown.currentText()
            selected_class_name = self.class_name_dropdown.currentText()
            selected_stream = self.stream_dropdown.currentText()
            academic_year_id = self.get_selected_id(self.academic_year_dropdown)
            term_id = self.get_selected_id(self.term_dropdown)
            status = self.status_dropdown.currentText()
            notes = self.notes_textbox.toPlainText().strip()
            is_current = self.is_current_checkbox.isChecked()
            
            # Additional validation beyond the basic form validation
            if not all([student_id, selected_level, selected_class_name, selected_stream]):
                QMessageBox.critical(self, "Error", "Missing required selection")
                return
            
            # Find the exact class with matching stream
            class_id = None
            for c in self.filtered_classes_by_level:
                stream_match = (c[2] == selected_stream) if selected_stream != "No Stream" else (c[2] is None or c[2] == "")
                if c[1] == selected_class_name and c[3] == selected_level and stream_match:
                    class_id = c[0]
                    break
            
            if not class_id:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"No matching class found for:\nLevel: {selected_level}\nClass: {selected_class_name}\nStream: {selected_stream}"
                )
                return
            
            # Check for duplicate assignment (same student, class, year, term)
            if self.check_duplicate_assignment(student_id, class_id, academic_year_id, term_id):
                # Get student and class details for better error message
                student_name = next((s[1] for s in self.all_students if s[0] == student_id), "Unknown Student")
                class_display = f"{selected_class_name} {selected_stream}" if selected_stream != "No Stream" else selected_class_name
                
                QMessageBox.warning(
                    self,
                    "Duplicate Assignment", 
                    f"Student '{student_name}' already has an assignment to:\n"
                    f"{class_display} for the selected term and academic year.\n\n"
                    f"Please check existing assignments or select different parameters."
                )
                return
            
            # Get school_id from user session or default to 1
            school_id = self.user_session.get('school_id', 1) if self.user_session else 1
            
            # If this is a current assignment, deactivate other current assignments for this student
            if is_current:
                self.cursor.execute("""
                    UPDATE student_class_assignments 
                    SET is_current = 0 
                    WHERE student_id = %s AND is_current = 1
                """, (student_id,))
            
            # Insert new assignment
            self.cursor.execute("""
                INSERT INTO student_class_assignments (
                    school_id, student_id, class_id, academic_year_id, term_id,
                    assignment_date, is_current, status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                school_id, 
                student_id, 
                class_id, 
                academic_year_id, 
                term_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                1 if is_current else 0, 
                status, 
                notes
            ))
            
            # For current assignments, update student's grade_applied_for if needed
            if is_current:
                self.cursor.execute("""
                    UPDATE students 
                    SET grade_applied_for = %s
                    WHERE id = %s
                """, (selected_class_name, student_id))
            
            self.db_connection.commit()
            
            # Get student name for success message
            student_name = next((s[1] for s in self.all_students if s[0] == student_id), "Student")
            class_display = f"{selected_class_name} {selected_stream}" if selected_stream != "No Stream" else selected_class_name
            
            QMessageBox.information(
                self,
                "Success", 
                f"Successfully assigned:\n"
                f"Student: {student_name}\n"
                f"Class: {class_display}\n"
                f"Status: {status}\n"
                f"Current: {'Yes' if is_current else 'No'}"
            )
            
            # Refresh data and clear form
            self.clear_form()
            self.load_data()
            
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save assignment:\n{e}")
            print(f"Database error: {e}")
            traceback.print_exc()
        
        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{e}")
            print(f"Unexpected error: {e}")
            traceback.print_exc()
            
    def update_assignment(self):
        """Update existing student class assignment"""
        if not self.selected_assignment_id:
            QMessageBox.warning(self, "Warning", "Please select an assignment to update")
            return
        
        if not self.validate_form():
            return
        
        try:
            student_id = self.get_selected_id(self.student_dropdown)
            class_id = self.get_selected_class_id()
            academic_year_id = self.get_selected_id(self.academic_year_dropdown)
            term_id = self.get_selected_id(self.term_dropdown)
            
            # Check for duplicate assignment (excluding current record)
            if self.check_duplicate_assignment(student_id, class_id, academic_year_id, term_id, self.selected_assignment_id):
                QMessageBox.warning(
                    self,
                    "Duplicate Assignment", 
                    "This student is already assigned to this class for the selected term and academic year."
                )
                return
            
            status = self.status_dropdown.currentText()
            notes = self.notes_textbox.toPlainText().strip()
            
            self.cursor.execute("""
                UPDATE student_class_assignments SET 
                    student_id = %s, class_id = %s, academic_year_id = %s, term_id = %s,
                    is_current = %s, status = %s, notes = %s
                WHERE id = %s
            """, (
                student_id, class_id, academic_year_id, term_id,
                self.is_current_checkbox.isChecked(), status, notes,
                self.selected_assignment_id
            ))
            
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Student class assignment updated successfully!")
            self.clear_form()
            self.load_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update assignment: {e}")
            print(f"Update error: {e}")
            traceback.print_exc()
            
    def delete_assignment(self):
        """Delete selected student class assignment"""
        if not self.selected_assignment_id:
            QMessageBox.warning(self, "Warning", "Please select an assignment to delete")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this student class assignment?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM student_class_assignments WHERE id = %s", (self.selected_assignment_id,))
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Student class assignment deleted successfully!")
                self.clear_form()
                self.load_data()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete assignment: {e}")
                print(f"Delete error: {e}")
                traceback.print_exc()
                
    def clear_form(self):
        """Clear all form fields"""
        self.level_dropdown.setCurrentIndex(-1)
        self.class_name_dropdown.clear()
        self.class_name_dropdown.addItem("Select education level first")
        self.stream_dropdown.clear()
        self.stream_dropdown.addItem("Select class name first...")
        
        # Show all students when form is cleared
        student_values = [f"{s[1]} (ID: {s[0]})" for s in self.all_students]
        self.student_dropdown.setValues(student_values)
        self.student_dropdown.setCurrentIndex(-1)
        
        self.academic_year_dropdown.setCurrentIndex(-1)
        self.term_dropdown.setCurrentIndex(-1)
        self.status_dropdown.setCurrentIndex(-1)
        self.assignment_date_entry.clear()
        self.notes_textbox.clear()
        self.is_current_checkbox.setChecked(True)
        self.selected_assignment_id = None
        
        self.filtered_classes_by_level = []
        self.filtered_students_by_class = []
        
        self.status_label.setText(f"Form cleared - Showing all {len(self.all_students)} students")
        
    def refresh_all_data(self):
        """Refresh all data"""
        self.load_dropdown_data()
        self.load_data()
        self.status_label.setText("All data refreshed")
        
    def load_data(self):
        """Load student class assignments data into table"""
        try:
            self.cursor.execute("""
                SELECT sca.id, s.full_name, s.grade_applied_for,
                       CASE 
                           WHEN c.stream IS NOT NULL AND c.stream != '' 
                           THEN CONCAT(c.class_name, ' ', c.stream)
                           ELSE c.class_name 
                       END as class_stream,
                       t.term_name, ay.year_name, 
                       sca.status, sca.is_current,
                       sca.assignment_date, sca.notes
                FROM student_class_assignments sca
                JOIN students s ON sca.student_id = s.id
                JOIN classes c ON sca.class_id = c.id
                JOIN terms t ON sca.term_id = t.id
                JOIN academic_years ay ON sca.academic_year_id = ay.id
                ORDER BY s.full_name, c.class_name, c.stream
            """)
            assignments = self.cursor.fetchall()
            
            self.update_assignments_table(assignments)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")
            print(f"Load data error: {e}")
            traceback.print_exc()
            
    def update_assignments_table(self, assignments):
        """Update the assignments table with new data"""
        self.table_widget.setRowCount(0)
        self.current_assignments_data = assignments
        
        for row, assignment in enumerate(assignments):
            self.table_widget.insertRow(row)
            
            # Format data for display
            student_name = assignment[1] or "N/A"
            grade = assignment[2] or "N/A"
            class_stream = assignment[3] or "N/A"
            term = assignment[4] or "N/A"
            year = assignment[5] or "N/A"
            status = assignment[6] or "Active"
            
            # Add items to table
            self.table_widget.setItem(row, 0, QTableWidgetItem(self.truncate_text(student_name, 20)))
            self.table_widget.setItem(row, 1, QTableWidgetItem(self.truncate_text(grade, 10)))
            self.table_widget.setItem(row, 2, QTableWidgetItem(self.truncate_text(class_stream, 15)))
            self.table_widget.setItem(row, 3, QTableWidgetItem(self.truncate_text(term, 10)))
            self.table_widget.setItem(row, 4, QTableWidgetItem(self.truncate_text(year, 10)))
            self.table_widget.setItem(row, 5, QTableWidgetItem(self.truncate_text(status, 15)))
            
    def truncate_text(self, text, max_length):
        """Truncate text to fit in table cells"""
        if not text:
            return "N/A"
        text_str = str(text)
        return text_str[:max_length] + "..." if len(text_str) > max_length else text_str
        
    def on_table_row_click(self, row, column):
        """Handle row selection from table"""
        try:
            if row < 0 or row >= len(self.current_assignments_data):
                return
                
            # Get assignment data
            assignment_data = self.current_assignments_data[row]
            assignment_id = assignment_data[0]
            
            self.load_assignment_data(assignment_id)
            
        except Exception as e:
            print(f"Error selecting assignment: {e}")
            traceback.print_exc()
            
    def load_assignment_data(self, assignment_id):
        """Load assignment data into form"""
        try:
            self.cursor.execute("""
                SELECT sca.id, sca.student_id, sca.class_id, sca.academic_year_id,
                       sca.term_id, sca.status, sca.is_current, sca.assignment_date,
                       sca.notes, s.full_name, s.grade_applied_for, c.class_name, 
                       c.stream, c.level, t.term_name, ay.year_name
                FROM student_class_assignments sca
                JOIN students s ON sca.student_id = s.id
                JOIN classes c ON sca.class_id = c.id
                JOIN terms t ON sca.term_id = t.id
                JOIN academic_years ay ON sca.academic_year_id = ay.id
                WHERE sca.id = %s
            """, (assignment_id,))
            
            assignment_data = self.cursor.fetchone()
            
            if not assignment_data:
                QMessageBox.critical(self, "Error", "Assignment not found")
                return
            
            self.selected_assignment_id = assignment_id
            
            # Extract data
            level = assignment_data[13]           # c.level
            class_name = assignment_data[11]      # c.class_name
            stream = assignment_data[12]          # c.stream
            student_name = assignment_data[9]     # s.full_name
            student_id = assignment_data[1]       # sca.student_id
            term_name = assignment_data[14]       # t.term_name
            year_name = assignment_data[15]       # ay.year_name
            
            # Set level first (this will trigger the cascade)
            if level:
                index = self.level_dropdown.findText(level)
                if index >= 0:
                    self.level_dropdown.setCurrentIndex(index)
                    self.on_level_selection_changed(level)
            
            # Set class name
            if class_name:
                index = self.class_name_dropdown.findText(class_name)
                if index >= 0:
                    self.class_name_dropdown.setCurrentIndex(index)
                    self.on_class_name_selection_changed(class_name)
            
            # Set stream
            stream_display = stream if stream else "No Stream"
            index = self.stream_dropdown.findText(stream_display)
            if index >= 0:
                self.stream_dropdown.setCurrentIndex(index)
                self.on_stream_selection_changed(stream_display)
            
            # Set student after a short delay to allow dropdowns to populate
            QTimer.singleShot(100, lambda: self._set_student_selection(student_id, student_name))
            
            # Set other dropdown values
            if year_name:
                index = self.academic_year_dropdown.findText(year_name)
                if index >= 0:
                    self.academic_year_dropdown.setCurrentIndex(index)
            if term_name:
                index = self.term_dropdown.findText(term_name)
                if index >= 0:
                    self.term_dropdown.setCurrentIndex(index)
            if assignment_data[5]:  # Status
                index = self.status_dropdown.findText(assignment_data[5])
                if index >= 0:
                    self.status_dropdown.setCurrentIndex(index)
            
            # Set assignment date
            if assignment_data[7]:
                self.assignment_date_entry.setText(str(assignment_data[7]))
            
            # Set notes
            if assignment_data[8]:  # notes
                self.notes_textbox.setPlainText(assignment_data[8])
            
            # Set is_current checkbox
            self.is_current_checkbox.setChecked(assignment_data[6])  # is_current
            
            self.status_label.setText(f"Assignment ID {assignment_id} loaded successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load assignment data: {e}")
            print(f"Load assignment error: {e}")
            traceback.print_exc()
            
    def _set_student_selection(self, student_id, student_name):
        """Helper method to set student selection after dropdown is populated"""
        try:
            if hasattr(self, 'filtered_students_by_class') and self.filtered_students_by_class:
                for student in self.filtered_students_by_class:
                    if student[0] == student_id:
                        # Find the exact text in the dropdown
                        for i in range(self.student_dropdown.count()):
                            if f"(ID: {student_id})" in self.student_dropdown.itemText(i):
                                self.student_dropdown.setCurrentIndex(i)
                                return
                
                # If not found in current dropdown, try to set by name
                self.student_dropdown.setCurrentText(f"{student_name} (ID: {student_id}) [Not in current list]")
            else:
                self.student_dropdown.setCurrentText(f"{student_name} (ID: {student_id}) [Load class first]")
                
        except Exception as e:
            print(f"Error setting student selection: {e}")
            
    def search_assignments(self):
        """Search assignments based on search entry"""
        try:
            search_term = self.search_entry.text().strip().lower()
            
            if not search_term:
                self.load_data()
                return
            
            self.cursor.execute("""
                SELECT sca.id, s.full_name, s.grade_applied_for,
                       CASE 
                           WHEN c.stream IS NOT NULL AND c.stream != '' 
                           THEN CONCAT(c.class_name, ' ', c.stream)
                           ELSE c.class_name 
                       END as class_stream,
                       t.term_name, ay.year_name, 
                       sca.status, sca.is_current,
                       sca.assignment_date, sca.notes
                FROM student_class_assignments sca
                JOIN students s ON sca.student_id = s.id
                JOIN classes c ON sca.class_id = c.id
                JOIN terms t ON sca.term_id = t.id
                JOIN academic_years ay ON sca.academic_year_id = ay.id
                WHERE LOWER(s.full_name) LIKE %s 
                   OR LOWER(c.class_name) LIKE %s
                   OR LOWER(c.stream) LIKE %s
                   OR LOWER(sca.status) LIKE %s
                   OR LOWER(s.grade_applied_for) LIKE %s
                   OR LOWER(t.term_name) LIKE %s
                   OR LOWER(ay.year_name) LIKE %s
                ORDER BY s.full_name, c.class_name, c.stream
            """, tuple([f'%{search_term}%'] * 7))
            
            assignments = self.cursor.fetchall()
            self.update_assignments_table(assignments)
            
            self.status_label.setText(f"Search: Found {len(assignments)} assignments")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Search failed: {e}")
            print(f"Search error: {e}")
            traceback.print_exc()
            
    def open_promotion_popup(self):
        """Open promotion dialog"""
        # Implementation would be similar to the original, but adapted for PySide6
        QMessageBox.information(self, "Info", "Promotion feature will be implemented in the next version")
        
    def open_demotion_popup(self):
        """Open demotion dialog"""
        # Implementation would be similar to the original, but adapted for PySide6
        QMessageBox.information(self, "Info", "Demotion feature will be implemented in the next version")
        
    def export_to_pdf(self):
        """Export student class assignments to PDF"""
        try:
            # Validation: Check if there's data to export
            if not hasattr(self, 'current_assignments_data') or not self.current_assignments_data:
                QMessageBox.warning(self, "Warning", "No assignment data to export")
                return

            # File save dialog
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Student Assignments Report As",
                f"student_class_assignments_{timestamp}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return

            # Custom PDF class with footer
            class PDF(FPDF):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.school_name = "WINSPIRE LEARNING HUB"
                    
                def footer(self):
                    """Add footer with page number and school name"""
                    self.set_y(-15)
                    self.set_font("Arial", 'I', 8)
                    self.cell(0, 10, f'{self.school_name} - Page {self.page_no()}', 0, 0, 'C')

            # Initialize PDF
            pdf = PDF(orientation='P', unit='mm', format='A4')
            pdf.set_margins(15, 20, 15)
            pdf.add_page()
            pdf.set_auto_page_break(True, 25)

            # === SCHOOL HEADER SECTION ===
            self._add_school_header(pdf)
            
            # === REPORT SUMMARY ===
            self._add_report_summary(pdf)
            
            # === ASSIGNMENTS TABLE ===
            self._add_assignments_table(pdf)
            
            # === REPORT FOOTER ===
            self._add_report_footer(pdf)

            # Save PDF
            pdf.output(file_path)
            
            # Open PDF automatically
            self._open_pdf(file_path)

            # Success message
            QMessageBox.information(
                self,
                "Export Successful",
                f"Student assignments report exported successfully!\n\n"
                f"Total Records: {len(self.current_assignments_data)}\n"
                f"File Location: {os.path.dirname(file_path)}\n"
                f"Filename: {os.path.basename(file_path)}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF:\n{e}")
            traceback.print_exc()
            
    def _add_school_header(self, pdf):
        """Add school header with logo beside the school information"""
        # School configuration
        school_config = {
            'name': "WINSPIRE LEARNING HUB",
            'address': "P.O.Box 12345",
            'location': "Nairobi, Kenya",
            'tel': "Tel: +254 700 000000",
            'email': "info@winspirelearning.ac.ke",
            'logo_path': "static/images/logo.png"
        }

        # Add school information
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, school_config['name'], 0, 1, 'C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 8, school_config['address'], 0, 1, 'C')
        pdf.cell(0, 8, school_config['location'], 0, 1, 'C')
        pdf.cell(0, 8, school_config['tel'], 0, 1, 'C')
        pdf.ln(10)
        
        # Report title
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "STUDENT CLASS ASSIGNMENTS REPORT", 0, 1, 'C')
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
        pdf.ln(10)
        
    def _add_report_summary(self, pdf):
        """Add summary information about the assignments"""
        # Calculate summary statistics
        total_assignments = len(self.current_assignments_data)
        active_assignments = sum(1 for assignment in self.current_assignments_data if assignment[7])
        
        # Summary section
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "REPORT SUMMARY", 0, 1)
        pdf.ln(2)

        # Summary table
        pdf.set_font("Arial", '', 10)
        
        summary_data = [
            ("Total Assignment Records:", str(total_assignments)),
            ("Current Assignments:", str(active_assignments)),
        ]

        for label, value in summary_data:
            pdf.cell(80, 6, label)
            pdf.cell(40, 6, value, 0, 1)
        
        pdf.ln(8)
        
    def _add_assignments_table(self, pdf):
        """Add the main assignments table"""
        # Table headers
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, "ASSIGNMENT DETAILS", 0, 1)
        pdf.ln(3)

        # Define headers and column widths
        headers = ["Student Name", "Grade", "Class/Stream", "Term", "Year", "Status", "Current"]
        col_widths = [45, 15, 30, 25, 25, 20, 17]

        # Table headers with styling
        pdf.set_fill_color(70, 130, 180)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 9)
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, 1, 0, 'C', True)
        pdf.ln()

        # Reset text color for data rows
        pdf.set_text_color(0, 0, 0)

        # Table data
        pdf.set_font("Arial", '', 8)
        row_height = 6
        
        for i, assignment in enumerate(self.current_assignments_data):
            # Check if we need a new page
            if pdf.get_y() + row_height > pdf.h - 25:
                pdf.add_page()
                # Repeat headers on new page
                pdf.set_fill_color(70, 130, 180)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", 'B', 9)
                for j, header in enumerate(headers):
                    pdf.cell(col_widths[j], 8, header, 1, 0, 'C', True)
                pdf.ln()
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 8)

            # Format data for display
            def truncate_text(text, max_length):
                text_str = str(text) if text is not None else "N/A"
                return text_str[:max_length] + "..." if len(text_str) > max_length else text_str

            row_data = [
                truncate_text(assignment[1], 35),  # Student name
                truncate_text(assignment[2], 10),  # Grade
                truncate_text(assignment[3], 25),  # Class/Stream
                truncate_text(assignment[4], 20),  # Term
                truncate_text(assignment[5], 20),  # Year
                truncate_text(assignment[6], 15),  # Status
                "Yes" if assignment[7] else "No"   # Current
            ]
            
            # Alternate row colors
            if i % 2 == 0:
                pdf.set_fill_color(248, 249, 250)
                fill = True
            else:
                pdf.set_fill_color(255, 255, 255)
                fill = True
            
            # Add row data
            for j, cell_data in enumerate(row_data):
                align = 'C' if j in [1, 6] else 'L'
                pdf.cell(col_widths[j], row_height, str(cell_data), 1, 0, align, fill)
            pdf.ln()
            
    def _add_report_footer(self, pdf):
        """Add footer section with report information"""
        pdf.ln(10)
        
        # Footer text
        pdf.set_font("Arial", 'I', 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 6, "This report contains confidential student information.", 0, 1, 'C')
        pdf.cell(0, 6, "Please handle with appropriate care and in accordance with data protection policies.", 0, 1, 'C')
        pdf.ln(3)
        
        # Report generation info
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, f"Report generated by Winspire Learning Hub Management System", 0, 1, 'C')
        
        # Generation timestamp
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 5, f"Generated on: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}", 0, 1, 'C')
        
    def _open_pdf(self, path):
        """Open PDF file with the system's default viewer"""
        try:
            system = platform.system()
            
            if system == 'Windows':
                os.startfile(path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', path], check=True)
            else:  # Linux and others
                try:
                    subprocess.run(['xdg-open', path], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback options for Linux
                    try:
                        subprocess.run(['gnome-open', path], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        try:
                            subprocess.run(['kde-open', path], check=True)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            try:
                                subprocess.run(['evince', path], check=True)  # GNOME PDF viewer
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                try:
                                    subprocess.run(['okular', path], check=True)  # KDE PDF viewer
                                except (subprocess.CalledProcessError, FileNotFoundError):
                                    raise Exception("No suitable PDF viewer found")
            
        except Exception as e:
            print(f"Failed to open PDF automatically: {e}")
            # Show a message with the file location instead of error
            QMessageBox.information(
                self,
                "PDF Saved Successfully", 
                f"PDF report has been saved successfully!\n\n"
                f"Location: {path}\n\n"
                f"The file couldn't open automatically, but you can open it manually from the saved location."
            )

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


    def __del__(self):
        """Close database connection when object is destroyed"""
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'db_connection'):
                self.db_connection.close()
        except:
            pass