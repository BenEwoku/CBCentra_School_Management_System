# ui/sickbay_visit_form.py
import sys
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, 
    QTabWidget, QMenu, QCheckBox, QDateEdit, QTextEdit, QApplication,
    QSplitter, QListWidget, QListWidgetItem, QProgressDialog, QSpinBox,
    QTimeEdit, QDoubleSpinBox
)
from PySide6.QtGui import QIcon, QFont, QPixmap, QPainter, QAction, QColor, QTextCursor
from PySide6.QtCore import Qt, Signal, QSize, QDate, QTimer, QDateTime, QTime
import mysql.connector
from mysql.connector import Error
import json
import pandas as pd
from fpdf import FPDF

from models.models import get_db_connection
from ui.audit_base_form import AuditBaseForm

class SickBayVisitForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        print("DEBUG: SickBayVisitForm initializing")
        self.user_session = user_session
        self.selected_visit_id = None
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True, dictionary=True)
            print("DEBUG: Database connection successful")
        except Error as e:
            print(f"DEBUG: Database connection failed: {e}")
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        # Data storage
        self.sick_bay_data = []
        self.filtered_data = []
        self.students_data = []
        self.teachers_data = []
        
        self.setup_ui()
        self.load_data()
        print("DEBUG: SickBayVisitForm initialized successfully")
        
    def setup_ui(self):
        """Setup the main UI components"""
        self.setWindowTitle("Sick Bay Visit Management System")
        self.setMinimumSize(1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Sick Bay Visit Management")
        title_label.setProperty("class", "page-title")
        main_layout.addWidget(title_label)
        
        # Stats overview
        stats_group = QGroupBox("Current Status")
        stats_group.setProperty("class", "stats-section")
        stats_layout = QHBoxLayout(stats_group)
        
        self.active_cases_label = QLabel("Active Cases: 0")
        self.active_cases_label.setProperty("class", "stat-number")
        
        self.today_visits_label = QLabel("Today's Visits: 0")
        self.today_visits_label.setProperty("class", "stat-number")
        
        self.awaiting_discharge_label = QLabel("Awaiting Discharge: 0")
        self.awaiting_discharge_label.setProperty("class", "stat-number")
        
        stats_layout.addWidget(self.active_cases_label)
        stats_layout.addWidget(self.today_visits_label)
        stats_layout.addWidget(self.awaiting_discharge_label)
        stats_layout.addStretch()
        
        main_layout.addWidget(stats_group)
        
        # Search and filter section
        search_group = QGroupBox("Search & Filter")
        search_group.setProperty("class", "search-section")
        search_layout = QHBoxLayout(search_group)
        
        search_label = QLabel("Search:")
        search_label.setProperty("class", "field-label")
        search_layout.addWidget(search_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.setProperty("class", "form-control")
        self.search_entry.setPlaceholderText("Search by patient name, reason...")
        self.search_entry.textChanged.connect(self.search_visits)
        search_layout.addWidget(self.search_entry)
        
        status_label = QLabel("Status:")
        status_label.setProperty("class", "field-label")
        search_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setProperty("class", "form-control")
        self.status_filter.addItems(["All", "Active", "Discharged", "Referred", "Follow-up"])
        self.status_filter.currentTextChanged.connect(self.filter_by_status)
        search_layout.addWidget(self.status_filter)
        
        clear_btn = QPushButton("Clear Filters")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.clicked.connect(self.clear_filters)
        search_layout.addWidget(clear_btn)
        
        main_layout.addWidget(search_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        new_visit_btn = QPushButton("New Visit")
        new_visit_btn.setProperty("class", "success")
        new_visit_btn.setIcon(QIcon("static/icons/add.png"))
        new_visit_btn.setIconSize(QSize(16, 16))
        new_visit_btn.clicked.connect(self.add_sick_bay_visit)
        action_layout.addWidget(new_visit_btn)
        
        edit_visit_btn = QPushButton("Edit Visit")
        edit_visit_btn.setProperty("class", "primary")
        edit_visit_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_visit_btn.setIconSize(QSize(16, 16))
        edit_visit_btn.clicked.connect(self.edit_sick_bay_visit)
        action_layout.addWidget(edit_visit_btn)
        
        discharge_btn = QPushButton("Discharge")
        discharge_btn.setProperty("class", "warning")
        discharge_btn.setIcon(QIcon("static/icons/check.png"))
        discharge_btn.setIconSize(QSize(16, 16))
        discharge_btn.clicked.connect(self.discharge_patient)
        action_layout.addWidget(discharge_btn)
        
        notify_parent_btn = QPushButton("Notify Parent")
        notify_parent_btn.setProperty("class", "info")
        notify_parent_btn.setIcon(QIcon("static/icons/phone.png"))
        notify_parent_btn.setIconSize(QSize(16, 16))
        notify_parent_btn.clicked.connect(self.notify_parent)
        action_layout.addWidget(notify_parent_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.clicked.connect(self.refresh_sick_bay_data)
        action_layout.addWidget(refresh_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        # Sick bay visits table
        self.sick_bay_table = QTableWidget()
        self.sick_bay_table.setColumnCount(11)
        self.sick_bay_table.setHorizontalHeaderLabels([
            "ID", "Patient", "Type", "Visit Date", "Visit Time", "Reason", 
            "Action Taken", "Status", "Parent Notified", "Duration", "Handler"
        ])
        self.sick_bay_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sick_bay_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sick_bay_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sick_bay_table.cellClicked.connect(self.on_sick_bay_row_click)
        self.sick_bay_table.setAlternatingRowColors(True)
        self.sick_bay_table.setProperty("class", "data-table")
        
        main_layout.addWidget(self.sick_bay_table)
        
        # Status info
        self.sick_bay_info_label = QLabel("Select a sick bay visit to manage")
        self.sick_bay_info_label.setProperty("class", "info-label")
        main_layout.addWidget(self.sick_bay_info_label)
    
    def load_data(self):
        """Load all data from database"""
        try:
            # Load sick bay visits with related data
            self.cursor.execute("""
                SELECT sv.*, 
                       COALESCE(s.first_name, t.first_name) as first_name,
                       COALESCE(s.surname, t.surname) as last_name,
                       CASE 
                           WHEN sv.student_id IS NOT NULL THEN 'Student' 
                           ELSE 'Staff' 
                       END as patient_type,
                       ht.first_name as handler_first_name,
                       ht.surname as handler_last_name,
                       TIMESTAMPDIFF(MINUTE, 
                           CONCAT(sv.visit_date, ' ', sv.visit_time), 
                           CONCAT(COALESCE(sv.discharge_date, CURDATE()), ' ', 
                                  COALESCE(sv.discharge_time, CURTIME()))) as duration_minutes
                FROM sick_bay_visits sv
                LEFT JOIN students s ON sv.student_id = s.id
                LEFT JOIN teachers t ON sv.teacher_id = t.id
                LEFT JOIN teachers ht ON sv.handled_by_teacher_id = ht.id
                ORDER BY sv.visit_date DESC, sv.visit_time DESC
            """)
            self.sick_bay_data = self.cursor.fetchall()
            self.filtered_data = self.sick_bay_data.copy()
            
            # Load students for dropdowns
            self.cursor.execute("SELECT id, first_name, surname FROM students WHERE is_active = TRUE ORDER BY first_name")
            self.students_data = self.cursor.fetchall()
            
            # Load teachers for dropdowns
            self.cursor.execute("SELECT id, first_name, surname FROM teachers WHERE is_active = TRUE ORDER BY first_name")
            self.teachers_data = self.cursor.fetchall()
            
            # Update stats and table
            self.update_stats()
            self.update_sick_bay_table()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")
            print(f"Database error: {e}")
    
    def update_stats(self):
        """Update statistics labels"""
        active_cases = sum(1 for record in self.sick_bay_data if record['status'] == 'Active')
        today_visits = sum(1 for record in self.sick_bay_data 
                          if str(record['visit_date']) == str(datetime.now().date()))
        awaiting_discharge = sum(1 for record in self.sick_bay_data 
                               if record['status'] == 'Active' and record['discharge_date'] is None)
        
        self.active_cases_label.setText(f"Active: {active_cases}")
        self.today_visits_label.setText(f"Today: {today_visits}")
        self.awaiting_discharge_label.setText(f"Awaiting: {awaiting_discharge}")
    
    def update_sick_bay_table(self):
        """Update the sick bay table with current data"""
        self.sick_bay_table.setRowCount(0)
        
        for row, record in enumerate(self.filtered_data):
            self.sick_bay_table.insertRow(row)
            
            # Format patient name
            patient_name = f"{record['first_name']} {record['last_name']}" if record['first_name'] else "Unknown"
            
            # Format handler name
            handler_name = f"{record['handler_first_name']} {record['handler_last_name']}" if record['handler_first_name'] else "Not specified"
            
            # Format duration
            if record['discharge_date'] and record['discharge_time']:
                duration = f"{record['duration_minutes']} min"
            else:
                duration = "Ongoing"
            
            # Add items to table
            self.sick_bay_table.setItem(row, 0, QTableWidgetItem(str(record['id'])))
            self.sick_bay_table.setItem(row, 1, QTableWidgetItem(patient_name))
            self.sick_bay_table.setItem(row, 2, QTableWidgetItem(record['patient_type']))
            self.sick_bay_table.setItem(row, 3, QTableWidgetItem(str(record['visit_date'])))
            self.sick_bay_table.setItem(row, 4, QTableWidgetItem(str(record['visit_time']) if record['visit_time'] else ""))
            self.sick_bay_table.setItem(row, 5, QTableWidgetItem(
                record['reason'][:50] + "..." if record['reason'] and len(record['reason']) > 50 
                else record['reason'] or ""
            ))
            self.sick_bay_table.setItem(row, 6, QTableWidgetItem(record['action_taken'] or ""))
            self.sick_bay_table.setItem(row, 7, QTableWidgetItem(record['status']))
            self.sick_bay_table.setItem(row, 8, QTableWidgetItem("Yes" if record['parent_notified'] else "No"))
            self.sick_bay_table.setItem(row, 9, QTableWidgetItem(duration))
            self.sick_bay_table.setItem(row, 10, QTableWidgetItem(handler_name))
            
            # Color code based on status
            if record['status'] == 'Active':
                color = QColor(255, 245, 230)  # Light orange
            elif record['status'] == 'Referred':
                color = QColor(255, 230, 230)  # Light red
            elif record['status'] == 'Discharged':
                color = QColor(230, 255, 230)  # Light green
            else:
                color = QColor(240, 240, 240)  # Light gray
                
            for col in range(self.sick_bay_table.columnCount()):
                self.sick_bay_table.item(row, col).setBackground(color)
        
        self.sick_bay_info_label.setText(f"Showing {len(self.filtered_data)} of {len(self.sick_bay_data)} sick bay visits")
    
    def search_visits(self):
        """Search visits based on search text"""
        search_text = self.search_entry.text().lower().strip()
        
        if not search_text:
            self.filtered_data = self.sick_bay_data.copy()
        else:
            self.filtered_data = [
                record for record in self.sick_bay_data
                if (search_text in (record['first_name'] or '').lower() or 
                    search_text in (record['last_name'] or '').lower() or 
                    search_text in (record['reason'] or '').lower())
            ]
            
        self.update_sick_bay_table()
    
    def filter_by_status(self):
        """Filter visits by status"""
        status = self.status_filter.currentText()
        
        if status == "All":
            self.filtered_data = self.sick_bay_data.copy()
        else:
            self.filtered_data = [record for record in self.sick_bay_data if record['status'] == status]
            
        self.update_sick_bay_table()
    
    def clear_filters(self):
        """Clear all filters"""
        self.search_entry.clear()
        self.status_filter.setCurrentIndex(0)
        self.filtered_data = self.sick_bay_data.copy()
        self.update_sick_bay_table()
    
    def on_sick_bay_row_click(self, row, column):
        """Handle sick bay row selection"""
        if row < 0 or row >= len(self.filtered_data):
            return
            
        record_id = self.sick_bay_table.item(row, 0).text()
        self.selected_visit_id = int(record_id)
        
        patient_name = self.sick_bay_table.item(row, 1).text()
        self.sick_bay_info_label.setText(f"Selected: {patient_name}'s sick bay visit")
    
    def add_sick_bay_visit(self):
        """Open dialog to add a new sick bay visit"""
        dialog = SickBayVisitDialog(self, students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            visit_data = dialog.get_visit_data()
            self.save_sick_bay_visit(visit_data)
    
    def edit_sick_bay_visit(self):
        """Open dialog to edit selected sick bay visit"""
        if not self.selected_visit_id:
            QMessageBox.warning(self, "Warning", "Please select a sick bay visit to edit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.sick_bay_data:
            if record['id'] == self.selected_visit_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected sick bay visit not found.")
            return
            
        dialog = SickBayVisitDialog(self, visit=selected_record, 
                                   students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            visit_data = dialog.get_visit_data()
            self.update_sick_bay_visit(self.selected_visit_id, visit_data)
    
    def discharge_patient(self):
        """Discharge selected patient from sick bay"""
        if not self.selected_visit_id:
            QMessageBox.warning(self, "Warning", "Please select a sick bay visit to discharge.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.sick_bay_data:
            if record['id'] == self.selected_visit_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected sick bay visit not found.")
            return
            
        if selected_record['status'] != 'Active':
            QMessageBox.warning(self, "Warning", "Only active visits can be discharged.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Discharge",
            f"Are you sure you want to discharge {selected_record['first_name']} {selected_record['last_name']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("""
                    UPDATE sick_bay_visits 
                    SET discharge_date = CURDATE(), discharge_time = CURTIME(), status = 'Discharged'
                    WHERE id = %s
                """, (self.selected_visit_id,))
                
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Patient discharged successfully!")
                self.load_data()
                
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to discharge patient: {e}")
    
    def notify_parent(self):
        """Mark parent as notified for selected visit"""
        if not self.selected_visit_id:
            QMessageBox.warning(self, "Warning", "Please select a sick bay visit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.sick_bay_data:
            if record['id'] == self.selected_visit_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected sick bay visit not found.")
            return
        
        if selected_record['parent_notified']:
            QMessageBox.information(self, "Info", "Parent has already been notified.")
            return
            
        try:
            self.cursor.execute("""
                UPDATE sick_bay_visits 
                SET parent_notified = TRUE, parent_notification_time = NOW()
                WHERE id = %s
            """, (self.selected_visit_id,))
            
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Parent notification recorded!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update parent notification: {e}")
    
    def refresh_sick_bay_data(self):
        """Refresh sick bay data"""
        self.load_data()
        QMessageBox.information(self, "Success", "Sick bay data refreshed!")
    
    def save_sick_bay_visit(self, visit_data):
        """Save new sick bay visit to database"""
        try:
            query = """
                INSERT INTO sick_bay_visits 
                (student_id, teacher_id, visit_date, visit_time, reason, 
                 initial_assessment, vital_signs, action_taken, status, handled_by_teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Convert vital signs to JSON
            vital_signs_json = json.dumps(visit_data.get('vital_signs', {})) if visit_data.get('vital_signs') else None
            
            values = (
                visit_data['student_id'],
                visit_data['teacher_id'],
                visit_data['visit_date'],
                visit_data['visit_time'],
                visit_data['reason'],
                visit_data['initial_assessment'],
                vital_signs_json,
                visit_data['action_taken'],
                'Active',  # Always active when created
                visit_data['handled_by_teacher_id']
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Sick bay visit recorded successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save sick bay visit: {e}")
    
    def update_sick_bay_visit(self, visit_id, visit_data):
        """Update existing sick bay visit in database"""
        try:
            query = """
                UPDATE sick_bay_visits 
                SET student_id = %s, teacher_id = %s, visit_date = %s, visit_time = %s,
                    reason = %s, initial_assessment = %s, vital_signs = %s, 
                    action_taken = %s, handled_by_teacher_id = %s
                WHERE id = %s
            """
            
            # Convert vital signs to JSON
            vital_signs_json = json.dumps(visit_data.get('vital_signs', {})) if visit_data.get('vital_signs') else None
            
            values = (
                visit_data['student_id'],
                visit_data['teacher_id'],
                visit_data['visit_date'],
                visit_data['visit_time'],
                visit_data['reason'],
                visit_data['initial_assessment'],
                vital_signs_json,
                visit_data['action_taken'],
                visit_data['handled_by_teacher_id'],
                visit_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Sick bay visit updated successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update sick bay visit: {e}")
    
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


class SickBayVisitDialog(QDialog):
    def __init__(self, parent=None, visit=None, students=None, teachers=None):
        super().__init__(parent)
        self.visit = visit
        self.students = students or []
        self.teachers = teachers or []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Edit Sick Bay Visit" if self.visit else "New Sick Bay Visit")
        self.setMinimumSize(650, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)
        
        # Patient information
        patient_group = QGroupBox("Patient Information")
        patient_layout = QFormLayout(patient_group)
        
        self.patient_type_combo = QComboBox()
        self.patient_type_combo.setProperty("class", "form-control")
        self.patient_type_combo.addItem("Student", "student")
        self.patient_type_combo.addItem("Staff/Teacher", "teacher")
        self.patient_type_combo.currentTextChanged.connect(self.on_patient_type_changed)
        
        self.student_combo = QComboBox()
        self.student_combo.setProperty("class", "form-control")
        self.student_combo.addItem("Select Student", None)
        for student in self.students:
            self.student_combo.addItem(f"{student['first_name']} {student['surname']}", student['id'])
        
        self.teacher_combo = QComboBox()
        self.teacher_combo.setProperty("class", "form-control")
        self.teacher_combo.addItem("Select Teacher", None)
        for teacher in self.teachers:
            self.teacher_combo.addItem(f"{teacher['first_name']} {teacher['surname']}", teacher['id'])
        
        patient_layout.addRow("Patient Type:", self.patient_type_combo)
        patient_layout.addRow("Student:", self.student_combo)
        patient_layout.addRow("Teacher:", self.teacher_combo)
        
        # Initially hide teacher combo
        self.teacher_combo.hide()
        patient_layout.labelForField(self.teacher_combo).hide()
        
        form_layout.addWidget(patient_group)
        
        # Visit information
        visit_group = QGroupBox("Visit Information")
        visit_layout = QFormLayout(visit_group)
        
        self.visit_date_edit = QDateEdit()
        self.visit_date_edit.setProperty("class", "form-control")
        self.visit_date_edit.setDate(QDate.currentDate())
        self.visit_date_edit.setCalendarPopup(True)
        
        self.visit_time_edit = QTimeEdit()
        self.visit_time_edit.setProperty("class", "form-control")
        self.visit_time_edit.setTime(QTime.currentTime())
        
        self.reason_edit = QTextEdit()
        self.reason_edit.setProperty("class", "form-control")
        self.reason_edit.setMaximumHeight(80)
        self.reason_edit.setPlaceholderText("Describe the reason for the visit...")
        
        self.assessment_edit = QTextEdit()
        self.assessment_edit.setProperty("class", "form-control")
        self.assessment_edit.setMaximumHeight(80)
        self.assessment_edit.setPlaceholderText("Initial observations and assessment...")
        
        visit_layout.addRow("Visit Date *:", self.visit_date_edit)
        visit_layout.addRow("Visit Time *:", self.visit_time_edit)
        visit_layout.addRow("Reason *:", self.reason_edit)
        visit_layout.addRow("Initial Assessment:", self.assessment_edit)
        
        form_layout.addWidget(visit_group)
        
        # Vital signs
        vitals_group = QGroupBox("Vital Signs")
        vitals_layout = QFormLayout(vitals_group)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setProperty("class", "form-control")
        self.temperature_spin.setRange(35.0, 42.0)
        self.temperature_spin.setValue(36.6)
        self.temperature_spin.setSuffix("°C")
        
        self.heart_rate_spin = QSpinBox()
        self.heart_rate_spin.setProperty("class", "form-control")
        self.heart_rate_spin.setRange(40, 200)
        self.heart_rate_spin.setValue(80)
        self.heart_rate_spin.setSuffix(" bpm")
        
        self.blood_pressure_edit = QLineEdit()
        self.blood_pressure_edit.setProperty("class", "form-control")
        self.blood_pressure_edit.setPlaceholderText("e.g., 120/80")
        
        vitals_layout.addRow("Temperature:", self.temperature_spin)
        vitals_layout.addRow("Heart Rate:", self.heart_rate_spin)
        vitals_layout.addRow("Blood Pressure:", self.blood_pressure_edit)
        
        form_layout.addWidget(vitals_group)
        
        # Action and handler information
        action_group = QGroupBox("Treatment Information")
        action_layout = QFormLayout(action_group)
        
        self.action_combo = QComboBox()
        self.action_combo.setProperty("class", "form-control")
        self.action_combo.addItems(["Observation", "First Aid", "Medication", "Parent Called", "Hospital Referral", "Rest"])
        
        self.handler_combo = QComboBox()
        self.handler_combo.setProperty("class", "form-control")
        self.handler_combo.addItem("Select Handler", None)
        for teacher in self.teachers:
            self.handler_combo.addItem(f"{teacher['first_name']} {teacher['surname']}", teacher['id'])
        
        action_layout.addRow("Action Taken:", self.action_combo)
        action_layout.addRow("Handled By *:", self.handler_combo)
        
        form_layout.addWidget(action_group)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Pre-fill data if editing
        if self.visit:
            self.prefill_data()
        
        # Button box
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Visit")
        save_btn.setProperty("class", "success")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def on_patient_type_changed(self, text):
        """Handle patient type change"""
        if text == "Student":
            self.student_combo.show()
            self.teacher_combo.hide()
            # Show/hide labels properly
            parent_layout = self.student_combo.parent().layout()
            if isinstance(parent_layout, QFormLayout):
                parent_layout.labelForField(self.student_combo).show()
                parent_layout.labelForField(self.teacher_combo).hide()
        else:
            self.student_combo.hide()
            self.teacher_combo.show()
            # Show/hide labels properly
            parent_layout = self.student_combo.parent().layout()
            if isinstance(parent_layout, QFormLayout):
                parent_layout.labelForField(self.student_combo).hide()
                parent_layout.labelForField(self.teacher_combo).show()
        
    def prefill_data(self):
        """Pre-fill form data if editing"""
        if self.visit['student_id']:
            self.patient_type_combo.setCurrentText("Student")
            index = self.student_combo.findData(self.visit['student_id'])
            if index >= 0:
                self.student_combo.setCurrentIndex(index)
        else:
            self.patient_type_combo.setCurrentText("Staff/Teacher")
            index = self.teacher_combo.findData(self.visit['teacher_id'])
            if index >= 0:
                self.teacher_combo.setCurrentIndex(index)
        
        self.visit_date_edit.setDate(QDate.fromString(str(self.visit['visit_date']), "yyyy-MM-dd"))
        if self.visit['visit_time']:
            self.visit_time_edit.setTime(QTime.fromString(str(self.visit['visit_time']), "hh:mm:ss"))
        
        self.reason_edit.setText(self.visit['reason'] or "")
        self.assessment_edit.setText(self.visit['initial_assessment'] or "")
        
        # Pre-fill vital signs from JSON
        if self.visit['vital_signs']:
            try:
                vital_signs = json.loads(self.visit['vital_signs']) if isinstance(self.visit['vital_signs'], str) else self.visit['vital_signs']
                self.temperature_spin.setValue(float(vital_signs.get('temperature', 36.6)))
                self.heart_rate_spin.setValue(int(vital_signs.get('heart_rate', 80)))
                self.blood_pressure_edit.setText(vital_signs.get('blood_pressure', ''))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass  # Keep default values if JSON is invalid
        
        if self.visit['action_taken']:
            index = self.action_combo.findText(self.visit['action_taken'])
            if index >= 0:
                self.action_combo.setCurrentIndex(index)
        
        if self.visit['handled_by_teacher_id']:
            index = self.handler_combo.findData(self.visit['handled_by_teacher_id'])
            if index >= 0:
                self.handler_combo.setCurrentIndex(index)
        
    def get_visit_data(self):
        """Get the sick bay visit data from the form"""
        patient_type = self.patient_type_combo.currentData()
        
        # Collect vital signs
        vital_signs = {
            'temperature': self.temperature_spin.value(),
            'heart_rate': self.heart_rate_spin.value(),
            'blood_pressure': self.blood_pressure_edit.text().strip()
        }
        
        return {
            'student_id': self.student_combo.currentData() if patient_type == 'student' else None,
            'teacher_id': self.teacher_combo.currentData() if patient_type == 'teacher' else None,
            'visit_date': self.visit_date_edit.date().toString("yyyy-MM-dd"),
            'visit_time': self.visit_time_edit.time().toString("hh:mm:ss"),
            'reason': self.reason_edit.toPlainText(),
            'initial_assessment': self.assessment_edit.toPlainText(),
            'vital_signs': vital_signs,
            'action_taken': self.action_combo.currentText(),
            'handled_by_teacher_id': self.handler_combo.currentData()
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        # Basic validation
        patient_type = self.patient_type_combo.currentData()
        if patient_type == 'student' and not self.student_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a student.")
            return
        elif patient_type == 'teacher' and not self.teacher_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a teacher.")
            return
            
        if not self.handler_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select who handled this visit.")
            return
            
        if not self.reason_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Please provide a reason for the visit.")
            return
            
        super().accept()