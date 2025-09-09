# ui/health_management_form.py
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
from ui.sickbay_visit_form import SickBayVisitDialog  # Import the dialog
# In your imports section
from ui.medical_conditions_form import MedicalConditionsForm


class HealthManagementForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        print("DEBUG: HealthManagementForm initializing")
        self.user_session = user_session
        self.selected_record_id = None
        self.selected_sick_bay_id = None
        
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
        self.health_records_data = []
        self.filtered_data = []
        self.students_data = []
        self.teachers_data = []
        self.sick_bay_data = []
        
        self.setup_ui()
        self.load_data()
        print("DEBUG: HealthManagementForm initialized successfully")
        
    def setup_ui(self):
        """Setup the main UI components with tabbed interface"""
        self.setWindowTitle("Health Management System")
        self.setMinimumSize(1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty("class", "main-tabs")
        
        # Connect tab change signal for ribbon updates
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Create tabs in logical order
        self.create_sick_bay_tab()          # First: Sick bay management
        self.create_health_records_tab()    # Second: General health records
        self.create_medical_conditions_tab() # Third: Chronic conditions
        # self.create_medication_tab()       # Third: Medication management
        # self.create_conditions_tab()       # Fourth: Medical conditions
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
    
    def create_health_records_tab(self):
        """Create the health records management tab"""
        records_widget = QWidget()
        records_layout = QVBoxLayout(records_widget)
        records_layout.setContentsMargins(20, 20, 20, 20)
        records_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("🏥 Health Records Management")
        title_label.setProperty("class", "page-title")
        records_layout.addWidget(title_label)
        
        # Search and filter section
        search_group = QGroupBox("Search & Filter")
        search_group.setProperty("class", "search-section")
        search_layout = QHBoxLayout(search_group)
        search_layout.setContentsMargins(12, 16, 12, 8)
        search_layout.setSpacing(8)
        
        search_label = QLabel("Search:")
        search_label.setProperty("class", "field-label")
        search_layout.addWidget(search_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.setProperty("class", "form-control")
        self.search_entry.setPlaceholderText("Search by student, teacher, symptoms...")
        self.search_entry.textChanged.connect(self.search_records)
        search_layout.addWidget(self.search_entry)
        
        status_label = QLabel("Status:")
        status_label.setProperty("class", "field-label")
        search_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setProperty("class", "form-control")
        self.status_filter.addItems(["All", "Mild", "Moderate", "Severe", "Emergency"])
        self.status_filter.currentTextChanged.connect(self.filter_by_severity)
        search_layout.addWidget(self.status_filter)
        
        clear_btn = QPushButton("Clear Filters")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.clicked.connect(self.clear_filters)
        search_layout.addWidget(clear_btn)
        
        records_layout.addWidget(search_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        add_btn = QPushButton("New Health Record")
        add_btn.setProperty("class", "success")
        add_btn.setIcon(QIcon("static/icons/add.png"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_health_record)
        action_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Record")
        edit_btn.setProperty("class", "primary")
        edit_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.clicked.connect(self.edit_health_record)
        action_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Record")
        delete_btn.setProperty("class", "danger")
        delete_btn.setIcon(QIcon("static/icons/delete.png"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.clicked.connect(self.delete_health_record)
        action_layout.addWidget(delete_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "info")
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.clicked.connect(self.refresh_data)
        action_layout.addWidget(refresh_btn)

        # Add this after your existing buttons in create_health_records_tab()
        export_excel_btn = QPushButton("Export Excel")
        export_excel_btn.setProperty("class", "info")
        export_excel_btn.setIcon(QIcon("static/icons/excel.png"))
        export_excel_btn.setIconSize(QSize(16, 16))
        export_excel_btn.clicked.connect(self.export_health_records_excel)
        action_layout.addWidget(export_excel_btn)
        
        # Replace the existing PDF button with this:
        export_pdf_btn = QPushButton("Export Patient PDF")
        export_pdf_btn.setProperty("class", "warning")
        export_pdf_btn.setIcon(QIcon("static/icons/pdf.png"))
        export_pdf_btn.setIconSize(QSize(16, 16))
        export_pdf_btn.clicked.connect(self.export_patient_health_pdf)
        #export_pdf_btn.setEnabled(False)  # Disabled until selection
        action_layout.addWidget(export_pdf_btn)
        
        action_layout.addStretch()
        records_layout.addLayout(action_layout)
        
        # Health records table
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(12)
        self.records_table.setHorizontalHeaderLabels([
            "ID", "Patient", "Type", "Visit Date", "Symptoms", "Diagnosis", 
            "Treatment", "Medication", "Severity", "Follow-up", "Handled By", "Status"
        ])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.records_table.cellClicked.connect(self.on_record_row_click)
        self.records_table.setAlternatingRowColors(True)
        self.records_table.setProperty("class", "data-table")
        
        records_layout.addWidget(self.records_table)
        
        # Status info
        self.info_label = QLabel("Select a health record to manage")
        self.info_label.setProperty("class", "info-label")
        records_layout.addWidget(self.info_label)
        
        # Add tab
        self.tab_widget.addTab(records_widget, "Health Records")
    
    def create_sick_bay_tab(self):
        """Create the sick bay visits management tab"""
        sick_bay_widget = QWidget()
        sick_bay_layout = QVBoxLayout(sick_bay_widget)
        sick_bay_layout.setContentsMargins(20, 20, 20, 20)
        sick_bay_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Sick Bay Visit Management")
        title_label.setProperty("class", "page-title")
        sick_bay_layout.addWidget(title_label)
        
        # Search and filter section
        search_group = QGroupBox("Search & Filter")
        search_group.setProperty("class", "search-section")
        search_layout = QHBoxLayout(search_group)
        
        search_label = QLabel("Search:")
        search_label.setProperty("class", "field-label")
        search_layout.addWidget(search_label)
        
        self.sick_bay_search_entry = QLineEdit()
        self.sick_bay_search_entry.setProperty("class", "form-control")
        self.sick_bay_search_entry.setPlaceholderText("Search by patient name, reason...")
        self.sick_bay_search_entry.textChanged.connect(self.search_sick_bay_visits)
        search_layout.addWidget(self.sick_bay_search_entry)
        
        status_label = QLabel("Status:")
        status_label.setProperty("class", "field-label")
        search_layout.addWidget(status_label)
        
        self.sick_bay_status_filter = QComboBox()
        self.sick_bay_status_filter.setProperty("class", "form-control")
        self.sick_bay_status_filter.addItems(["All", "Active", "Discharged", "Referred", "Follow-up"])
        self.sick_bay_status_filter.currentTextChanged.connect(self.filter_sick_bay_by_status)
        search_layout.addWidget(self.sick_bay_status_filter)
        
        clear_btn = QPushButton("Clear Filters")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.clicked.connect(self.clear_sick_bay_filters)
        search_layout.addWidget(clear_btn)
        
        sick_bay_layout.addWidget(search_group)
        
        # Action buttons and stats combined in one row
        action_stats_layout = QHBoxLayout()
        action_stats_layout.setSpacing(15)
        
        # Left side: Action buttons
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(10)
        
        new_visit_btn = QPushButton("New Visit")
        new_visit_btn.setProperty("class", "success")
        new_visit_btn.setIcon(QIcon("static/icons/add.png"))
        new_visit_btn.setIconSize(QSize(16, 16))
        new_visit_btn.clicked.connect(self.add_sick_bay_visit)
        action_buttons_layout.addWidget(new_visit_btn)
        
        edit_visit_btn = QPushButton("Edit Visit")
        edit_visit_btn.setProperty("class", "primary")
        edit_visit_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_visit_btn.setIconSize(QSize(16, 16))
        edit_visit_btn.clicked.connect(self.edit_sick_bay_visit)
        action_buttons_layout.addWidget(edit_visit_btn)
        
        discharge_btn = QPushButton("Discharge")
        discharge_btn.setProperty("class", "warning")
        discharge_btn.setIcon(QIcon("static/icons/check.png"))
        discharge_btn.setIconSize(QSize(16, 16))
        discharge_btn.clicked.connect(self.discharge_patient)
        action_buttons_layout.addWidget(discharge_btn)
        
        notify_parent_btn = QPushButton("Notify Parent")
        notify_parent_btn.setProperty("class", "info")
        notify_parent_btn.setIcon(QIcon("static/icons/phone.png"))
        notify_parent_btn.setIconSize(QSize(16, 16))
        notify_parent_btn.clicked.connect(self.notify_parent)
        action_buttons_layout.addWidget(notify_parent_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.clicked.connect(self.refresh_sick_bay_data)
        action_buttons_layout.addWidget(refresh_btn)

        # Add this after your existing buttons in create_sick_bay_tab()
        export_excel_btn = QPushButton("Export Excel")
        export_excel_btn.setProperty("class", "info")
        export_excel_btn.setIcon(QIcon("static/icons/excel.png"))
        export_excel_btn.setIconSize(QSize(16, 16))
        export_excel_btn.clicked.connect(self.export_sick_bay_excel)
        action_buttons_layout.addWidget(export_excel_btn)
        
        # Replace the existing PDF button with this:
        export_pdf_btn = QPushButton("Export Visit PDF")
        export_pdf_btn.setProperty("class", "warning")
        export_pdf_btn.setIcon(QIcon("static/icons/pdf.png"))
        export_pdf_btn.setIconSize(QSize(16, 16))
        export_pdf_btn.clicked.connect(self.export_patient_sick_bay_pdf)
        #export_pdf_btn.setEnabled(False)  # Disabled until selection
        action_buttons_layout.addWidget(export_pdf_btn)
        
        # Add stretch to push stats to the right
        action_buttons_layout.addStretch()
        
        # Right side: Stats labels (without group box)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        self.active_cases_label = QLabel("Active: 0")
        self.active_cases_label.setProperty("class", "stat-label")
        self.active_cases_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stats_layout.addWidget(self.active_cases_label)
        
        self.today_visits_label = QLabel("Today: 0")
        self.today_visits_label.setProperty("class", "stat-label")
        self.today_visits_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stats_layout.addWidget(self.today_visits_label)
        
        self.awaiting_discharge_label = QLabel("Awaiting: 0")
        self.awaiting_discharge_label.setProperty("class", "stat-label")
        self.awaiting_discharge_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stats_layout.addWidget(self.awaiting_discharge_label)
        
        # Combine both sides
        action_stats_layout.addLayout(action_buttons_layout, 70)  # 70% width for buttons
        action_stats_layout.addLayout(stats_layout, 30)  # 30% width for stats
        
        sick_bay_layout.addLayout(action_stats_layout)
        
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
        
        sick_bay_layout.addWidget(self.sick_bay_table)
        
        # Status info
        self.sick_bay_info_label = QLabel("Select a sick bay visit to manage")
        self.sick_bay_info_label.setProperty("class", "info-label")
        sick_bay_layout.addWidget(self.sick_bay_info_label)
        
        # Add tab
        self.tab_widget.addTab(sick_bay_widget, "Sick Bay Visit")
    
    # In your setup_ui() method:
    def create_medical_conditions_tab(self):
        """Create the medical conditions management tab"""
        # Load students and teachers data if not already loaded
        if not hasattr(self, 'students_data') or not self.students_data:
            try:
                self.cursor.execute("SELECT id, first_name, surname FROM students WHERE is_active = TRUE ORDER BY first_name")
                self.students_data = self.cursor.fetchall()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to load students: {e}")
                return
        
        if not hasattr(self, 'teachers_data') or not self.teachers_data:
            try:
                self.cursor.execute("SELECT id, first_name, surname FROM teachers WHERE is_active = TRUE ORDER BY first_name")
                self.teachers_data = self.cursor.fetchall()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to load teachers: {e}")
                return
        
        # Create the medical conditions tab
        self.medical_conditions_tab = MedicalConditionsForm(
            parent=self,
            db_connection=self.db_connection,
            cursor=self.cursor,
            students_data=self.students_data,
            teachers_data=self.teachers_data,
            user_session=self.user_session  # Pass the user session for audit base
        )
        self.tab_widget.addTab(self.medical_conditions_tab, "Medical Conditions")
    
    def load_data(self):
        """Load all data from database"""
        try:
            # Load health records with related data
            self.cursor.execute("""
                SELECT hr.*, 
                       COALESCE(s.first_name, t.first_name) as first_name,
                       COALESCE(s.surname, t.surname) as last_name,
                       CASE 
                           WHEN hr.student_id IS NOT NULL THEN 'Student' 
                           ELSE 'Staff' 
                       END as patient_type,
                       ht.first_name as handler_first_name,
                       ht.surname as handler_last_name
                FROM health_records hr
                LEFT JOIN students s ON hr.student_id = s.id
                LEFT JOIN teachers t ON hr.teacher_id = t.id
                LEFT JOIN teachers ht ON hr.handled_by_teacher_id = ht.id
                ORDER BY hr.visit_date DESC, hr.visit_time DESC
            """)
            self.health_records_data = self.cursor.fetchall()
            self.filtered_data = self.health_records_data.copy()
            
            # Load sick bay data
            self.load_sick_bay_data()
            
            # Load students for dropdowns
            self.cursor.execute("SELECT id, first_name, surname FROM students WHERE is_active = TRUE ORDER BY first_name")
            self.students_data = self.cursor.fetchall()
            
            # Load teachers for dropdowns
            self.cursor.execute("SELECT id, first_name, surname FROM teachers WHERE is_active = TRUE ORDER BY first_name")
            self.teachers_data = self.cursor.fetchall()
            
            # Update UI
            self.update_records_table()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")
            print(f"Database error: {e}")
    
    def load_sick_bay_data(self):
        """Load sick bay visits data"""
        try:
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
            self.sick_bay_filtered_data = self.sick_bay_data.copy()
            
            # Update stats
            active_cases = sum(1 for record in self.sick_bay_data if record['status'] == 'Active')
            today_visits = sum(1 for record in self.sick_bay_data if str(record['visit_date']) == str(datetime.now().date()))
            awaiting_discharge = sum(1 for record in self.sick_bay_data if record['status'] == 'Active' and record['discharge_date'] is None)
            
            self.active_cases_label.setText(f"Active Cases: {active_cases}")
            self.today_visits_label.setText(f"Today's Visits: {today_visits}")
            self.awaiting_discharge_label.setText(f"Awaiting Discharge: {awaiting_discharge}")
            
            self.update_sick_bay_table()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load sick bay data: {e}")
    
    def update_sick_bay_table(self):
        """Update the sick bay table with current data"""
        self.sick_bay_table.setRowCount(0)
        
        for row, record in enumerate(self.sick_bay_filtered_data):
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
        
        self.sick_bay_info_label.setText(f"Showing {len(self.sick_bay_filtered_data)} of {len(self.sick_bay_data)} sick bay visits")
    
    def search_sick_bay_visits(self):
        """Search sick bay visits based on search text"""
        search_text = self.sick_bay_search_entry.text().lower().strip()
        
        if not search_text:
            self.sick_bay_filtered_data = self.sick_bay_data.copy()
        else:
            self.sick_bay_filtered_data = [
                record for record in self.sick_bay_data
                if (search_text in (record['first_name'] or '').lower() or 
                    search_text in (record['last_name'] or '').lower() or 
                    search_text in (record['reason'] or '').lower())
            ]
            
        self.update_sick_bay_table()
    
    def filter_sick_bay_by_status(self):
        """Filter sick bay visits by status"""
        status = self.sick_bay_status_filter.currentText()
        
        if status == "All":
            self.sick_bay_filtered_data = self.sick_bay_data.copy()
        else:
            self.sick_bay_filtered_data = [record for record in self.sick_bay_data if record['status'] == status]
            
        self.update_sick_bay_table()
    
    def clear_sick_bay_filters(self):
        """Clear all sick bay filters"""
        self.sick_bay_search_entry.clear()
        self.sick_bay_status_filter.setCurrentIndex(0)
        self.sick_bay_filtered_data = self.sick_bay_data.copy()
        self.update_sick_bay_table()
    
    def on_sick_bay_row_click(self, row, column):
        """Handle sick bay row selection"""
        if row < 0 or row >= len(self.sick_bay_filtered_data):
            return
            
        record_id = self.sick_bay_table.item(row, 0).text()
        self.selected_sick_bay_id = int(record_id)
        
        patient_name = self.sick_bay_table.item(row, 1).text()
        self.sick_bay_info_label.setText(f"Selected: {patient_name}'s sick bay visit")
        
        # Enable PDF export button
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QPushButton) and widget.text() == "Export Visit PDF":
                widget.setEnabled(True)
                break
    
    def add_sick_bay_visit(self):
        """Open dialog to add a new sick bay visit"""
        dialog = SickBayVisitDialog(self, students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            visit_data = dialog.get_visit_data()
            self.save_sick_bay_visit(visit_data)
    
    def edit_sick_bay_visit(self):
        """Open dialog to edit selected sick bay visit"""
        if not self.selected_sick_bay_id:
            QMessageBox.warning(self, "Warning", "Please select a sick bay visit to edit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.sick_bay_data:
            if record['id'] == self.selected_sick_bay_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected sick bay visit not found.")
            return
            
        dialog = SickBayVisitDialog(self, visit=selected_record, 
                                   students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            visit_data = dialog.get_visit_data()
            self.update_sick_bay_visit(self.selected_sick_bay_id, visit_data)
    
    def discharge_patient(self):
        """Discharge selected patient from sick bay"""
        if not self.selected_sick_bay_id:
            QMessageBox.warning(self, "Warning", "Please select a sick bay visit to discharge.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.sick_bay_data:
            if record['id'] == self.selected_sick_bay_id:
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
                """, (self.selected_sick_bay_id,))
                
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Patient discharged successfully!")
                self.load_sick_bay_data()
                
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to discharge patient: {e}")
    
    def notify_parent(self):
        """Mark parent as notified for selected visit"""
        if not self.selected_sick_bay_id:
            QMessageBox.warning(self, "Warning", "Please select a sick bay visit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.sick_bay_data:
            if record['id'] == self.selected_sick_bay_id:
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
            """, (self.selected_sick_bay_id,))
            
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Parent notification recorded!")
            self.load_sick_bay_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update parent notification: {e}")
    
    def refresh_sick_bay_data(self):
        """Refresh sick bay data"""
        self.load_sick_bay_data()
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
            self.load_sick_bay_data()
            
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
            self.load_sick_bay_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update sick bay visit: {e}")

    # ... (keep your existing health records methods) ...

    def update_records_table(self):
        """Update the records table with current data"""
        self.records_table.setRowCount(0)
        
        for row, record in enumerate(self.filtered_data):
            self.records_table.insertRow(row)
            
            # Format patient name
            patient_name = f"{record['first_name']} {record['last_name']}" if record['first_name'] else "Unknown"
            
            # Format handler name
            handler_name = f"{record['handler_first_name']} {record['handler_last_name']}" if record['handler_first_name'] else "Not specified"
            
            # Add items to table
            self.records_table.setItem(row, 0, QTableWidgetItem(str(record['id'])))
            self.records_table.setItem(row, 1, QTableWidgetItem(patient_name))
            self.records_table.setItem(row, 2, QTableWidgetItem(record['patient_type']))
            self.records_table.setItem(row, 3, QTableWidgetItem(str(record['visit_date'])))
            self.records_table.setItem(row, 4, QTableWidgetItem(record['symptoms'][:50] + "..." if record['symptoms'] and len(record['symptoms']) > 50 else record['symptoms'] or ""))
            self.records_table.setItem(row, 5, QTableWidgetItem(record['diagnosis'][:50] + "..." if record['diagnosis'] and len(record['diagnosis']) > 50 else record['diagnosis'] or ""))
            self.records_table.setItem(row, 6, QTableWidgetItem(record['treatment'][:50] + "..." if record['treatment'] and len(record['treatment']) > 50 else record['treatment'] or ""))
            self.records_table.setItem(row, 7, QTableWidgetItem(record['prescribed_medication'] or ""))
            self.records_table.setItem(row, 8, QTableWidgetItem(record['severity']))
            self.records_table.setItem(row, 9, QTableWidgetItem("Yes" if record['follow_up_required'] else "No"))
            self.records_table.setItem(row, 10, QTableWidgetItem(handler_name))
            self.records_table.setItem(row, 11, QTableWidgetItem("Referred" if record['referred_to_hospital'] else "Treated"))
            
        self.info_label.setText(f"Showing {len(self.filtered_data)} of {len(self.health_records_data)} health records")
        
    def on_record_row_click(self, row, column):
        """Handle record row selection"""
        if row < 0 or row >= len(self.filtered_data):
            return
            
        record_id = self.records_table.item(row, 0).text()
        self.selected_record_id = int(record_id)
        
        patient_name = self.records_table.item(row, 1).text()
        self.info_label.setText(f"Selected: {patient_name}'s health record")
        
        # Enable PDF export button
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QPushButton) and widget.text() == "Export Patient PDF":
                widget.setEnabled(True)
                break
        
    def search_records(self):
        """Search records based on search text"""
        search_text = self.search_entry.text().lower().strip()
        
        if not search_text:
            self.filtered_data = self.health_records_data.copy()
        else:
            self.filtered_data = [
                record for record in self.health_records_data
                if (search_text in (record['first_name'] or '').lower() or 
                    search_text in (record['last_name'] or '').lower() or 
                    search_text in (record['symptoms'] or '').lower() or 
                    search_text in (record['diagnosis'] or '').lower())
            ]
            
        self.update_records_table()
        
    def filter_by_severity(self):
        """Filter records by severity"""
        severity = self.status_filter.currentText()
        
        if severity == "All":
            self.filtered_data = self.health_records_data.copy()
        else:
            self.filtered_data = [record for record in self.health_records_data if record['severity'] == severity]
            
        self.update_records_table()

    # In your HealthManagementForm, add this method to handle tab changes for ribbon updates
    def on_tab_changed(self, index):
        """Handle tab changes to update ribbon"""
        if hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'update_ribbon_panel'):
            current_tab = self.tab_widget.tabText(index)
            self.parent().update_ribbon_panel("Health Management")
        
    def clear_filters(self):
        """Clear all filters"""
        self.search_entry.clear()
        self.status_filter.setCurrentIndex(0)
        self.filtered_data = self.health_records_data.copy()
        self.update_records_table()
        
    def add_health_record(self):
        """Open dialog to add a new health record"""
        dialog = HealthRecordDialog(self, students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            record_data = dialog.get_record_data()
            self.save_health_record(record_data)
            
    def edit_health_record(self):
        """Open dialog to edit selected health record"""
        if not self.selected_record_id:
            QMessageBox.warning(self, "Warning", "Please select a health record to edit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.health_records_data:
            if record['id'] == self.selected_record_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected health record not found.")
            return
            
        dialog = HealthRecordDialog(self, record=selected_record, students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            record_data = dialog.get_record_data()
            self.update_health_record(self.selected_record_id, record_data)
            
    def delete_health_record(self):
        """Delete selected health record"""
        if not self.selected_record_id:
            QMessageBox.warning(self, "Warning", "Please select a health record to delete.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.health_records_data:
            if record['id'] == self.selected_record_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected health record not found.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the health record for {selected_record['first_name']} {selected_record['last_name']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM health_records WHERE id = %s", (self.selected_record_id,))
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Health record deleted successfully!")
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete health record: {e}")
                
    def save_health_record(self, record_data):
        """Save new health record to database"""
        try:
            query = """
                INSERT INTO health_records 
                (student_id, teacher_id, visit_date, visit_time, temperature, blood_pressure, 
                 symptoms, diagnosis, treatment, prescribed_medication, dosage, 
                 follow_up_required, follow_up_date, severity, referred_to_hospital, 
                 notes, handled_by_teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                record_data['student_id'],
                record_data['teacher_id'],
                record_data['visit_date'],
                record_data['visit_time'],
                record_data['temperature'],
                record_data['blood_pressure'],
                record_data['symptoms'],
                record_data['diagnosis'],
                record_data['treatment'],
                record_data['prescribed_medication'],
                record_data['dosage'],
                record_data['follow_up_required'],
                record_data['follow_up_date'],
                record_data['severity'],
                record_data['referred_to_hospital'],
                record_data['notes'],
                record_data['handled_by_teacher_id']
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Health record added successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add health record: {e}")
            
    def update_health_record(self, record_id, record_data):
        """Update existing health record in database"""
        try:
            query = """
                UPDATE health_records 
                SET student_id = %s, teacher_id = %s, visit_date = %s, visit_time = %s, 
                    temperature = %s, blood_pressure = %s, symptoms = %s, diagnosis = %s, 
                    treatment = %s, prescribed_medication = %s, dosage = %s, 
                    follow_up_required = %s, follow_up_date = %s, severity = %s, 
                    referred_to_hospital = %s, notes = %s, handled_by_teacher_id = %s
                WHERE id = %s
            """
            values = (
                record_data['student_id'],
                record_data['teacher_id'],
                record_data['visit_date'],
                record_data['visit_time'],
                record_data['temperature'],
                record_data['blood_pressure'],
                record_data['symptoms'],
                record_data['diagnosis'],
                record_data['treatment'],
                record_data['prescribed_medication'],
                record_data['dosage'],
                record_data['follow_up_required'],
                record_data['follow_up_date'],
                record_data['severity'],
                record_data['referred_to_hospital'],
                record_data['notes'],
                record_data['handled_by_teacher_id'],
                record_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Health record updated successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update health record: {e}")
            
    def refresh_data(self):
        """Refresh all data from database"""
        self.load_data()
        QMessageBox.information(self, "Success", "Data refreshed successfully!")

    
    def export_health_records_excel(self):
        """Export health records to Excel file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Health Records Excel", "", "Excel Files (*.xlsx)"
            )
            
            if file_path:
                # Create DataFrame from health records data
                df_data = []
                for record in self.health_records_data:
                    df_data.append({
                        'ID': record['id'],
                        'Patient': f"{record.get('first_name', '')} {record.get('last_name', '')}",
                        'Type': 'Student' if record['student_id'] else 'Staff',
                        'Visit Date': record['visit_date'],
                        'Visit Time': record.get('visit_time', ''),
                        'Temperature': record.get('temperature', ''),
                        'Blood Pressure': record.get('blood_pressure', ''),
                        'Symptoms': record.get('symptoms', ''),
                        'Diagnosis': record.get('diagnosis', ''),
                        'Treatment': record.get('treatment', ''),
                        'Medication': record.get('prescribed_medication', ''),
                        'Dosage': record.get('dosage', ''),
                        'Severity': record.get('severity', ''),
                        'Follow-up Required': 'Yes' if record['follow_up_required'] else 'No',
                        'Follow-up Date': record.get('follow_up_date', ''),
                        'Referred to Hospital': 'Yes' if record['referred_to_hospital'] else 'No',
                        'Handler': f"{record.get('handler_first_name', '')} {record.get('handler_last_name', '')}",
                        'Notes': record.get('notes', '')
                    })
                
                df = pd.DataFrame(df_data)
                
                # Export to Excel
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Health Records', index=False)
                    
                    # Auto-adjust columns width
                    worksheet = writer.sheets['Health Records']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                QMessageBox.information(self, "Success", f"Health records exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export health records: {e}")
    
    def export_sick_bay_excel(self):
        """Export sick bay visits to Excel file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Sick Bay Excel", "", "Excel Files (*.xlsx)"
            )
            
            if file_path:
                # Create DataFrame from sick bay data
                df_data = []
                for record in self.sick_bay_data:
                    duration = f"{record['duration_minutes']} min" if record.get('duration_minutes') else "Ongoing"
                    
                    df_data.append({
                        'ID': record['id'],
                        'Patient': f"{record.get('first_name', '')} {record.get('last_name', '')}",
                        'Type': 'Student' if record['student_id'] else 'Staff',
                        'Visit Date': record['visit_date'],
                        'Visit Time': record.get('visit_time', ''),
                        'Discharge Date': record.get('discharge_date', ''),
                        'Discharge Time': record.get('discharge_time', ''),
                        'Duration': duration,
                        'Reason': record.get('reason', ''),
                        'Initial Assessment': record.get('initial_assessment', ''),
                        'Action Taken': record.get('action_taken', ''),
                        'Status': record.get('status', ''),
                        'Parent Notified': 'Yes' if record['parent_notified'] else 'No',
                        'Parent Notification Time': record.get('parent_notification_time', ''),
                        'Handler': f"{record.get('handler_first_name', '')} {record.get('handler_last_name', '')}",
                        'Vital Signs': record.get('vital_signs', '')
                    })
                
                df = pd.DataFrame(df_data)
                
                # Export to Excel
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Sick Bay Visits', index=False)
                    
                    # Auto-adjust columns width
                    worksheet = writer.sheets['Sick Bay Visits']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                QMessageBox.information(self, "Success", f"Sick bay visits exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export sick bay visits: {e}")
    
    def generate_health_record_pdf_bytes(self, selected_record):
        """Generate health record PDF with school branding, patient photo, compact two-column patient info, and signature section"""
        import os
        import tempfile
        from fpdf import FPDF
        from datetime import datetime
    
        # --- School information ---
        try:
            school_query = "SELECT school_name, address, phone, email, logo_path FROM schools WHERE id = %s LIMIT 1"
            school_id = getattr(self.user_session, 'school_id', 1) if self.user_session else 1
            self.cursor.execute(school_query, (school_id,))
            school_info = self.cursor.fetchone()
        except Exception:
            school_info = None
    
        default_logo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "images", "logo.png"
        )
        school_logo = school_info['logo_path'] if school_info and school_info.get('logo_path') else default_logo
    
        # --- Fetch patient photo ---
        patient_photo = None
        try:
            if selected_record.get('student_id'):
                self.cursor.execute("SELECT photo_path FROM students WHERE id = %s LIMIT 1", (selected_record['student_id'],))
                student_photo_res = self.cursor.fetchone()
                if student_photo_res and student_photo_res.get('photo_path'):
                    photo_path = student_photo_res['photo_path']
                    if os.path.exists(photo_path):
                        patient_photo = photo_path
            elif selected_record.get('teacher_id'):
                self.cursor.execute("SELECT photo_path FROM teachers WHERE id = %s LIMIT 1", (selected_record['teacher_id'],))
                teacher_photo_res = self.cursor.fetchone()
                if teacher_photo_res and teacher_photo_res.get('photo_path'):
                    photo_path = teacher_photo_res['photo_path']
                    if os.path.exists(photo_path):
                        patient_photo = photo_path
        except Exception:
            patient_photo = None
    
        # --- PDF class ---
        class HealthRecordPDF(FPDF):
            def __init__(self):
                super().__init__(orientation='P', unit='mm', format='A4')
                self.set_margins(15, 15, 15)
                self.set_auto_page_break(auto=False)
    
            def header(self):
                # School logo (left)
                if os.path.exists(school_logo):
                    try:
                        self.image(school_logo, 15, 10, 25)
                    except Exception:
                        pass
    
                # Patient photo (top-right)
                if patient_photo:
                    try:
                        self.image(patient_photo, 165, 5, 30, 30)
                    except Exception:
                        pass
    
                # School info (center)
                self.set_y(10)
                if school_info:
                    if school_info.get('school_name'):
                        self.set_font("Arial", "B", 16)
                        self.cell(0, 8, school_info['school_name'], 0, 1, "C")
    
                    self.set_font("Arial", "", 10)
                    if school_info.get('address'):
                        self.cell(0, 5, school_info['address'], 0, 1, "C")
    
                    contact_info = ""
                    if school_info.get('phone'):
                        contact_info += school_info['phone']
                    if school_info.get('phone') and school_info.get('email'):
                        contact_info += " | "
                    if school_info.get('email'):
                        contact_info += school_info['email']
    
                    if contact_info:
                        self.cell(0, 5, contact_info, 0, 1, "C")
    
                # Document title
                self.ln(3)
                self.set_font("Arial", "B", 14)
                self.set_text_color(70, 70, 70)
                self.cell(0, 8, "MEDICAL RECORD REPORT", 0, 1, "C")
    
                # Document info
                self.set_font("Arial", "", 9)
                self.set_text_color(100, 100, 100)
                doc_id = f"Document ID: HR-{selected_record['id']:06d}"
                gen_time = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.cell(0, 4, f"{doc_id} | {gen_time}", 0, 1, "C")
    
                # Confidentiality notice
                self.set_font("Arial", "I", 8)
                self.set_text_color(200, 0, 0)
                self.cell(0, 4, "CONFIDENTIAL MEDICAL INFORMATION", 0, 1, "C")
    
                # Separator line
                self.set_draw_color(200, 200, 200)
                self.line(15, self.get_y() + 2, 195, self.get_y() + 2)
                self.ln(4)
                self.set_text_color(0, 0, 0)
    
            def footer(self):
                self.set_y(-20)
                self.set_font("Arial", "I", 8)
                self.set_text_color(128, 128, 128)
                self.cell(0, 4, "This document contains confidential medical information.", 0, 1, "C")
                self.cell(0, 4, "Distribution limited to authorized personnel only.", 0, 1, "C")
                self.cell(0, 4, f"Page {self.page_no()}", 0, 0, "C")
    
            def draw_box(self, x, y, width, height, title="", fill_color=(240, 240, 240)):
                self.set_fill_color(*fill_color)
                self.set_draw_color(150, 150, 150)
                self.rect(x, y, width, height, 'DF')
                if title:
                    self.set_xy(x + 2, y + 1)
                    self.set_font("Arial", "B", 10)
                    self.set_text_color(0, 0, 0)
                    self.cell(width - 4, 6, title, 0, 0, "L")
    
            def add_info_box_two_column(self, title, fields, y_pos, height=38):
                box_width = 180
                self.draw_box(15, y_pos, box_width, height, title)
                current_y = y_pos + 8
                self.set_xy(20, current_y)
                label_width = 40
                col_width = (box_width - 2 * 5 - label_width) / 2
                col_count = 0
    
                for label, value in fields:
                    self.set_font("Arial", "", 9)
                    self.cell(label_width, 5, f"{label}:", 0, 0, "L")
                    self.set_font("Arial", "B", 9)
                    self.cell(col_width, 5, str(value) if value else "N/A", 0, 0, "L")
                    col_count += 1
                    if col_count % 2 == 0:
                        self.ln(5)
                        self.set_x(20)
                return y_pos + height
    
            def add_section_header(self, title, color=(70, 130, 180)):
                self.ln(2)
                self.set_fill_color(*color)
                self.set_text_color(255, 255, 255)
                self.set_font("Arial", "B", 11)
                self.cell(0, 8, title, 0, 1, "L", True)
                self.set_text_color(0, 0, 0)
                self.ln(1)
    
            def add_multiline_content(self, content, max_width=180):
                self.set_font("Arial", "", 10)
                if content:
                    words = str(content).split()
                    lines = []
                    current_line = ""
                    for word in words:
                        test_line = current_line + (" " if current_line else "") + word
                        if self.get_string_width(test_line) <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)
                    for line in lines:
                        self.cell(0, 6, line, 0, 1, "L")
                else:
                    self.cell(0, 6, "Not specified", 0, 1, "L")
    
            def add_signature_section(self, y_pos):
                """Add signature lines for handler/doctor"""
                self.set_y(y_pos + 5)
                self.set_font("Arial", "", 10)
                self.cell(100, 6, "_______________________________", 0, 0, "L")
                self.cell(0, 6, "_______________________________", 0, 1, "L")
                self.cell(100, 4, "Handler/Doctor Signature", 0, 0, "L")
                self.cell(0, 4, "Date", 0, 1, "L")
                self.ln(3)
    
        # --- Create PDF ---
        pdf = HealthRecordPDF()
        pdf.add_page()
    
        # --- Combined patient & visit fields ---
        patient_name = f"{selected_record.get('first_name', '')} {selected_record.get('last_name', '')}".strip()
        patient_type = "Student" if selected_record.get('student_id') else "Staff"
        handler_name = f"{selected_record.get('handler_first_name', '')} {selected_record.get('handler_last_name', '')}".strip()
    
        combined_fields = [
            ("Name", patient_name),
            ("Type", patient_type),
            ("Record ID", f"HR-{selected_record['id']:06d}"),
            ("Date", selected_record.get('visit_date', 'N/A')),
            ("Visit Time", str(selected_record.get('visit_time', 'N/A'))),
            ("Handler", handler_name or "Not specified"),
            ("Severity", selected_record.get('severity', 'N/A')),
        ]
    
        box_bottom = pdf.add_info_box_two_column("PATIENT INFORMATION", combined_fields, pdf.get_y(), height=35)
        pdf.set_y(box_bottom + 2)
    
        # --- Clinical Assessment ---
        pdf.add_section_header("CLINICAL ASSESSMENT")
        if selected_record.get('temperature') or selected_record.get('blood_pressure'):
            pdf.set_font("Arial", "B", 10)
            pdf.cell(90, 6, "VITAL SIGNS", 0, 0, "L")
            pdf.cell(90, 6, "OBSERVATIONS", 0, 1, "L")
            pdf.set_font("Arial", "", 10)
            temp_text = f"Temperature: {selected_record.get('temperature', 'N/A')}°C"
            bp_text = f"Blood Pressure: {selected_record.get('blood_pressure', 'N/A')}"
            pdf.cell(90, 5, temp_text, 0, 0, "L")
            pdf.cell(90, 5, "Patient cooperative", 0, 1, "L")
            pdf.cell(90, 5, bp_text, 0, 0, "L")
            pdf.cell(90, 5, "No acute distress", 0, 1, "L")
            pdf.ln(3)
    
        # --- Symptoms, Findings, Treatment ---
        pdf.add_section_header("PRESENTING SYMPTOMS")
        pdf.add_multiline_content(selected_record.get('symptoms'))
        pdf.ln(2)
    
        pdf.add_section_header("CLINICAL FINDINGS")
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "Primary Diagnosis:", 0, 1, "L")
        pdf.add_multiline_content(selected_record.get('diagnosis'))
        pdf.ln(2)
    
        pdf.add_section_header("TREATMENT ADMINISTERED")
        pdf.add_multiline_content(selected_record.get('treatment'))
        pdf.ln(2)
    
        # --- Medication ---
        if selected_record.get('prescribed_medication'):
            pdf.add_section_header("MEDICATION RECORD", (180, 100, 100))
            med_y = pdf.get_y()
            pdf.draw_box(15, med_y, 180, 18, "MEDICATION ADMINISTERED", (255, 240, 240))
            pdf.set_xy(20, med_y + 7)
            pdf.set_font("Arial", "", 9)
            med_text = f"Drug: {selected_record['prescribed_medication']}"
            if selected_record.get('dosage'):
                med_text += f" | Dosage: {selected_record['dosage']}"
            pdf.cell(0, 5, med_text, 0, 1, "L")
            pdf.set_x(20)
            pdf.cell(0, 5, f"Time: {selected_record.get('visit_time', 'N/A')}", 0, 1, "L")
            pdf.set_y(med_y + 20)
    
            pdf.add_section_header("FOLLOW-UP REQUIREMENTS")
            follow_up_text = "Follow-up required: "
            follow_up_text += "[X] YES" if selected_record.get('follow_up_required') else "[ ] NO"
            if selected_record.get('follow_up_date'):
                follow_up_text += f" (Due: {selected_record['follow_up_date']})"
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, follow_up_text, 0, 1, "L")
            referral_text = "Hospital referral: "
            referral_text += "[X] YES" if selected_record.get('referred_to_hospital') else "[ ] NO"
            pdf.cell(0, 6, referral_text, 0, 1, "L")
            pdf.ln(3)
    
        # --- Additional Notes ---
        if selected_record.get('notes'):
            pdf.add_section_header("ADDITIONAL NOTES")
            pdf.add_multiline_content(selected_record.get('notes'))
    
        # --- Signature Section ---
        pdf.add_signature_section(pdf.get_y() + 5)
    
        # --- Export PDF as bytes ---
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
        try:
            pdf.output(temp_path)
            with open(temp_path, 'rb') as f:
                pdf_bytes = f.read()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
        return pdf_bytes


    def export_patient_health_pdf(self):
        """Export individual patient's health record as PDF using enhanced viewer"""
        if not self.selected_record_id:
            QMessageBox.warning(self, "Warning", "Please select a health record first.")
            return
        
        try:
            # Find the selected record
            selected_record = None
            for record in self.health_records_data:
                if record['id'] == self.selected_record_id:
                    selected_record = record
                    break
            
            if not selected_record:
                QMessageBox.warning(self, "Error", "Selected record not found.")
                return
            
            # Generate PDF bytes with enhanced formatting
            pdf_bytes = self.generate_health_record_pdf_bytes(selected_record)
            
            # Use your enhanced PDF viewer
            try:
                from utils.pdf_utils import view_pdf
                view_pdf(pdf_bytes, self)
            except ImportError as e:
                print(f"PDF viewer import error: {e}")
                # Fallback to file save
                self.save_health_pdf_fallback(pdf_bytes, selected_record)
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate health record PDF: {str(e)}")

    def save_health_pdf_fallback(self, pdf_bytes, selected_record):
        """Fallback method to save health PDF if viewer not available"""
        patient_name = f"{selected_record.get('first_name', '')} {selected_record.get('last_name', '')}".strip()
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        default_filename = f"health_record_{safe_name}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Health Record PDF", default_filename, "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(pdf_bytes)
                QMessageBox.information(self, "Success", f"PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF: {str(e)}")

    def generate_sick_bay_pdf_bytes(self, selected_record):
        """Generate sick bay visit PDF with school branding, patient photo, compact layout, and signature line"""
        import tempfile
        import os
        import json
        from fpdf import FPDF
        from datetime import datetime
    
        # Get school information
        try:
            school_query = "SELECT school_name, address, phone, email, logo_path FROM schools WHERE id = %s LIMIT 1"
            school_id = getattr(self.user_session, 'school_id', 1) if self.user_session else 1
            self.cursor.execute(school_query, (school_id,))
            school_info = self.cursor.fetchone()
        except Exception:
            school_info = None
    
        # Default logo path
        default_logo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "images", "logo.png"
        )
        school_logo = school_info['logo_path'] if school_info and school_info.get('logo_path') else default_logo
    
        # Fetch patient photo
        patient_photo = None
        try:
            if selected_record.get('student_id'):
                self.cursor.execute("SELECT photo_path FROM students WHERE id = %s LIMIT 1", (selected_record['student_id'],))
                student_photo_res = self.cursor.fetchone()
                if student_photo_res and student_photo_res.get('photo_path'):
                    photo_path = student_photo_res['photo_path']
                    if os.path.exists(photo_path):
                        patient_photo = photo_path
            elif selected_record.get('teacher_id'):
                self.cursor.execute("SELECT photo_path FROM teachers WHERE id = %s LIMIT 1", (selected_record['teacher_id'],))
                teacher_photo_res = self.cursor.fetchone()
                if teacher_photo_res and teacher_photo_res.get('photo_path'):
                    photo_path = teacher_photo_res['photo_path']
                    if os.path.exists(photo_path):
                        patient_photo = photo_path
        except Exception:
            patient_photo = None
    
        class SickBayPDF(FPDF):
            def __init__(self):
                super().__init__(orientation='P', unit='mm', format='A4')
                self.set_margins(15, 15, 15)
                self.set_auto_page_break(auto=False)
    
            def header(self):
                if os.path.exists(school_logo):
                    try:
                        self.image(school_logo, 15, 10, 25)
                    except:
                        pass
                if patient_photo:
                    try:
                        self.image(patient_photo, 165, 5, 30, 30)
                    except:
                        pass
    
                self.set_y(10)
                if school_info:
                    if school_info.get('school_name'):
                        self.set_font("Arial", "B", 14)
                        self.cell(0, 7, school_info['school_name'], 0, 1, "C")
    
                    self.set_font("Arial", "", 9)
                    if school_info.get('address'):
                        self.cell(0, 5, school_info['address'], 0, 1, "C")
                    contact_info = ""
                    if school_info.get('phone'):
                        contact_info += school_info['phone']
                    if school_info.get('phone') and school_info.get('email'):
                        contact_info += " | "
                    if school_info.get('email'):
                        contact_info += school_info['email']
                    if contact_info:
                        self.cell(0, 5, contact_info, 0, 1, "C")
    
                self.ln(4)
                self.set_font("Arial", "B", 13)
                self.set_text_color(70, 70, 70)
                self.cell(0, 8, "SICK BAY VISIT REPORT", 0, 1, "C")
    
                self.set_font("Arial", "", 8)
                self.set_text_color(100, 100, 100)
                doc_id = f"Document ID: SB-{selected_record['id']:06d}"
                gen_time = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.cell(0, 4, f"{doc_id} | {gen_time}", 0, 1, "C")
    
                self.set_font("Arial", "I", 7)
                self.set_text_color(200, 0, 0)
                self.cell(0, 4, "CONFIDENTIAL MEDICAL INFORMATION", 0, 1, "C")
    
                self.set_draw_color(200, 200, 200)
                self.line(15, self.get_y() + 2, 195, self.get_y() + 2)
                self.ln(4)
                self.set_text_color(0, 0, 0)
    
            def footer(self):
                self.set_y(-20)
                self.set_font("Arial", "I", 7)
                self.set_text_color(128, 128, 128)
                self.cell(0, 4, "This document contains confidential medical information.", 0, 1, "C")
                self.cell(0, 4, "Distribution limited to authorized personnel only.", 0, 1, "C")
                self.cell(0, 4, f"Page {self.page_no()}", 0, 0, "C")
    
            def draw_box(self, x, y, width, height, title="", fill_color=(240, 240, 240)):
                self.set_fill_color(*fill_color)
                self.set_draw_color(150, 150, 150)
                self.rect(x, y, width, height, 'DF')
                if title:
                    self.set_xy(x + 2, y + 1)
                    self.set_font("Arial", "B", 9)
                    self.set_text_color(0, 0, 0)
                    self.cell(width - 4, 6, title, 0, 0, "L")
    
            def add_info_box(self, title, fields, y_pos, height=36):
                box_width = 180
                self.draw_box(15, y_pos, box_width, height, title)
                label_width = 50
                col1_x, col2_x = 20, 110
                col_y = y_pos + 10
    
                for i, (label, value) in enumerate(fields):
                    x = col1_x if i % 2 == 0 else col2_x
                    y = col_y + (i // 2) * 6
                    self.set_xy(x, y)
                    self.set_font("Arial", "B", 9)
                    self.cell(label_width, 5, f"{label}:", 0, 0, "L")
                    self.set_font("Arial", "", 9)
                    self.cell(0, 5, str(value) if value else "N/A", 0, 1, "L")
    
            def add_section_header(self, title, color=(70, 130, 180)):
                self.ln(4)
                self.set_fill_color(*color)
                self.set_text_color(255, 255, 255)
                self.set_font("Arial", "B", 11)
                self.cell(0, 8, title, 0, 1, "L", True)
                self.set_text_color(0, 0, 0)
                self.ln(2)
    
            def add_multiline_content(self, content, max_width=180):
                self.set_font("Arial", "", 9)
                if content:
                    words = str(content).split()
                    lines, current_line = [], ""
                    for word in words:
                        test_line = current_line + (" " if current_line else "") + word
                        if self.get_string_width(test_line) <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)
                    for line in lines:
                        self.cell(0, 5, line, 0, 1, "L")
                else:
                    self.cell(0, 5, "Not specified", 0, 1, "L")
    
        pdf = SickBayPDF()
        pdf.add_page()
    
        # Merge Patient + Visit Info (two-column)
        patient_name = f"{selected_record.get('first_name', '')} {selected_record.get('last_name', '')}".strip()
        patient_type = "Student" if selected_record.get('student_id') else "Staff"
        handler_name = f"{selected_record.get('handler_first_name', '')} {selected_record.get('handler_last_name', '')}".strip()
        patient_fields = [
            ("Name", patient_name),
            ("Type", patient_type),
            ("Visit ID", f"SB-{selected_record['id']:06d}"),
            ("Handler", handler_name or "Not specified"),
            ("Visit Date", selected_record.get('visit_date', 'N/A')),
            ("Status", selected_record.get('status', 'N/A')),
        ]
        pdf.add_info_box("PATIENT INFORMATION", patient_fields, pdf.get_y(), 40)
        pdf.ln(2)
    
        # Parent notification
        pdf.add_section_header("PARENT NOTIFICATION")
        parent_notified = "[X] YES" if selected_record.get('parent_notified') else "[ ] NO"
        pdf.set_font("Arial", "", 9)
        y_before = pdf.get_y()
        pdf.set_xy(20, y_before)
        pdf.cell(80, 5, f"Parent Notified: {parent_notified}", 0, 0, "L")
        pdf.set_xy(110, y_before)
        pdf.cell(80, 5, f"Reason: {selected_record.get('reason','Not specified')}", 0, 1, "L")
        pdf.ln(2)
    
        # Initial Assessment
        if selected_record.get('initial_assessment'):
            pdf.add_section_header("INITIAL ASSESSMENT")
            pdf.add_multiline_content(selected_record.get('initial_assessment'))
            pdf.ln(2)
    
        # Action Taken
        if selected_record.get('action_taken'):
            pdf.add_section_header("ACTION TAKEN")
            pdf.add_multiline_content(selected_record.get('action_taken'))
            pdf.ln(2)
    
        # Vital Signs
        if selected_record.get('vital_signs'):
            try:
                vital_signs = json.loads(selected_record['vital_signs']) if isinstance(selected_record['vital_signs'], str) else selected_record['vital_signs']
                pdf.add_section_header("VITAL SIGNS", (180, 100, 100))
                vitals_y = pdf.get_y()
                pdf.draw_box(15, vitals_y, 180, 24, "VITAL SIGNS RECORDED", (255, 240, 240))
                pdf.set_xy(20, vitals_y + 8)
                pdf.set_font("Arial", "", 9)
                vital_texts = []
                for key, value in vital_signs.items():
                    if value:
                        label = key.replace('_', ' ').title()
                        unit = {'Temperature': '°C', 'Heart Rate': ' bpm', 'Blood Pressure': ''}.get(label, '')
                        vital_texts.append(f"{label}: {value}{unit}")
                if vital_texts:
                    pdf.multi_cell(0, 5, " | ".join(vital_texts))
                else:
                    pdf.cell(0, 5, "No vital signs recorded", 0, 1, "L")
                pdf.ln(5)
            except:
                pass
    
        # Observations
        observations, status = [], selected_record.get('status')
        if status == 'Active':
            observations.append("Patient currently under observation in sick bay")
        elif status == 'Discharged':
            observations.append("Patient has been discharged from sick bay")
        elif status == 'Referred':
            observations.append("Patient referred for further medical attention")
    
        if observations:
            pdf.add_section_header("OBSERVATIONS")
            pdf.set_font("Arial", "", 9)
            for obs in observations:
                pdf.cell(0, 5, f"* {obs}", 0, 1, "L")
            pdf.ln(4)
    
        # Signature Section with Date
        pdf.ln(12)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, 6, "Handled By (Signature):", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, "........................................................", 0, 1, "L")
        pdf.cell(60, 5, "Date:", 0, 0, "L")
        pdf.cell(0, 5, datetime.now().strftime("%Y-%m-%d"), 0, 1, "L")
        pdf.ln(3)
    
        # Output pdf bytes
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
        try:
            pdf.output(temp_path)
            with open(temp_path, 'rb') as f:
                pdf_bytes = f.read()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        return pdf_bytes

    
    def export_patient_sick_bay_pdf(self):
        """Export individual sick bay visit as PDF using enhanced viewer"""
        if not self.selected_sick_bay_id:
            QMessageBox.warning(self, "Warning", "Please select a sick bay visit first.")
            return
        
        try:
            # Find the selected record
            selected_record = None
            for record in self.sick_bay_data:
                if record['id'] == self.selected_sick_bay_id:
                    selected_record = record
                    break
            
            if not selected_record:
                QMessageBox.warning(self, "Error", "Selected visit not found.")
                return
            
            # Generate PDF bytes with enhanced formatting
            pdf_bytes = self.generate_sick_bay_pdf_bytes(selected_record)
            
            # Use your enhanced PDF viewer
            try:
                from utils.pdf_utils import view_pdf
                view_pdf(pdf_bytes, self)
            except ImportError as e:
                print(f"PDF viewer import error: {e}")
                # Fallback to file save
                self.save_sick_bay_pdf_fallback(pdf_bytes, selected_record)
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate sick bay PDF: {str(e)}")
    
    def save_sick_bay_pdf_fallback(self, pdf_bytes, selected_record):
        """Fallback method to save sick bay PDF if viewer not available"""
        patient_name = f"{selected_record.get('first_name', '')} {selected_record.get('last_name', '')}".strip()
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"sick_bay_visit_{safe_name}_{timestamp}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Sick Bay Visit PDF", default_filename, "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Sick bay visit PDF saved successfully!\n\n"
                    f"Patient: {patient_name}\n"
                    f"Status: {selected_record.get('status', 'N/A')}\n"
                    f"File: {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF: {str(e)}")

        
        
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


class HealthRecordDialog(QDialog):
    def __init__(self, parent=None, record=None, students=None, teachers=None):
        super().__init__(parent)
        self.record = record
        self.students = students or []
        self.teachers = teachers or []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Edit Health Record" if self.record else "Add New Health Record")
        self.setMinimumSize(650, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)
        
        # Patient type selection
        type_group = QGroupBox("Patient Information")
        type_layout = QFormLayout(type_group)
        
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
        
        type_layout.addRow("Patient Type:", self.patient_type_combo)
        type_layout.addRow("Student:", self.student_combo)
        type_layout.addRow("Teacher:", self.teacher_combo)
        
        # Initially hide teacher combo
        self.teacher_combo.hide()
        type_layout.labelForField(self.teacher_combo).hide()
        
        form_layout.addWidget(type_group)
        
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
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setProperty("class", "form-control")
        self.temperature_spin.setRange(35.0, 42.0)
        self.temperature_spin.setValue(36.6)
        self.temperature_spin.setSuffix("°C")
        
        self.blood_pressure_edit = QLineEdit()
        self.blood_pressure_edit.setProperty("class", "form-control")
        self.blood_pressure_edit.setPlaceholderText("e.g., 120/80")
        
        visit_layout.addRow("Visit Date *:", self.visit_date_edit)
        visit_layout.addRow("Visit Time *:", self.visit_time_edit)
        visit_layout.addRow("Temperature:", self.temperature_spin)
        visit_layout.addRow("Blood Pressure:", self.blood_pressure_edit)
        
        form_layout.addWidget(visit_group)
        
        # Medical information
        medical_group = QGroupBox("Medical Information")
        medical_layout = QFormLayout(medical_group)
        
        self.symptoms_edit = QTextEdit()
        self.symptoms_edit.setProperty("class", "form-control")
        self.symptoms_edit.setMaximumHeight(80)
        
        self.diagnosis_edit = QTextEdit()
        self.diagnosis_edit.setProperty("class", "form-control")
        self.diagnosis_edit.setMaximumHeight(80)
        
        self.treatment_edit = QTextEdit()
        self.treatment_edit.setProperty("class", "form-control")
        self.treatment_edit.setMaximumHeight(80)
        
        self.medication_edit = QLineEdit()
        self.medication_edit.setProperty("class", "form-control")
        
        self.dosage_edit = QLineEdit()
        self.dosage_edit.setProperty("class", "form-control")
        
        medical_layout.addRow("Symptoms:", self.symptoms_edit)
        medical_layout.addRow("Diagnosis:", self.diagnosis_edit)
        medical_layout.addRow("Treatment:", self.treatment_edit)
        medical_layout.addRow("Prescribed Medication:", self.medication_edit)
        medical_layout.addRow("Dosage:", self.dosage_edit)
        
        form_layout.addWidget(medical_group)
        
        # Additional information
        additional_group = QGroupBox("Additional Information")
        additional_layout = QFormLayout(additional_group)
        
        self.severity_combo = QComboBox()
        self.severity_combo.setProperty("class", "form-control")
        self.severity_combo.addItems(["Mild", "Moderate", "Severe", "Emergency"])
        
        self.follow_up_check = QCheckBox("Follow-up required")
        
        self.follow_up_date_edit = QDateEdit()
        self.follow_up_date_edit.setProperty("class", "form-control")
        self.follow_up_date_edit.setDate(QDate.currentDate().addDays(7))
        self.follow_up_date_edit.setCalendarPopup(True)
        self.follow_up_date_edit.setEnabled(False)
        
        self.referral_check = QCheckBox("Referred to hospital")
        
        self.handler_combo = QComboBox()
        self.handler_combo.setProperty("class", "form-control")
        self.handler_combo.addItem("Select Handler", None)
        for teacher in self.teachers:
            self.handler_combo.addItem(f"{teacher['first_name']} {teacher['surname']}", teacher['id'])
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setProperty("class", "form-control")
        self.notes_edit.setMaximumHeight(60)
        
        additional_layout.addRow("Severity:", self.severity_combo)
        additional_layout.addRow("", self.follow_up_check)
        additional_layout.addRow("Follow-up Date:", self.follow_up_date_edit)
        additional_layout.addRow("", self.referral_check)
        additional_layout.addRow("Handled By:", self.handler_combo)
        additional_layout.addRow("Notes:", self.notes_edit)
        
        form_layout.addWidget(additional_group)
        
        # Connect signals
        self.follow_up_check.toggled.connect(self.follow_up_date_edit.setEnabled)
        self.follow_up_check.toggled.connect(lambda checked: self.follow_up_date_edit.setDate(QDate.currentDate().addDays(7) if checked else QDate.currentDate()))
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Pre-fill data if editing
        if self.record:
            self.prefill_data()
        
        # Button box
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
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
            for i in range(self.layout().count()):
                if isinstance(self.layout().itemAt(i), QFormLayout):
                    self.layout().itemAt(i).labelForField(self.student_combo).show()
                    self.layout().itemAt(i).labelForField(self.teacher_combo).hide()
        else:
            self.student_combo.hide()
            self.teacher_combo.show()
            for i in range(self.layout().count()):
                if isinstance(self.layout().itemAt(i), QFormLayout):
                    self.layout().itemAt(i).labelForField(self.student_combo).hide()
                    self.layout().itemAt(i).labelForField(self.teacher_combo).show()
        
    def prefill_data(self):
        """Pre-fill form data if editing"""
        if self.record['student_id']:
            self.patient_type_combo.setCurrentText("Student")
            index = self.student_combo.findData(self.record['student_id'])
            if index >= 0:
                self.student_combo.setCurrentIndex(index)
        else:
            self.patient_type_combo.setCurrentText("Staff/Teacher")
            index = self.teacher_combo.findData(self.record['teacher_id'])
            if index >= 0:
                self.teacher_combo.setCurrentIndex(index)
        
        self.visit_date_edit.setDate(QDate.fromString(str(self.record['visit_date']), "yyyy-MM-dd"))
        if self.record['visit_time']:
            self.visit_time_edit.setTime(QTime.fromString(str(self.record['visit_time']), "hh:mm:ss"))
        
        if self.record['temperature']:
            self.temperature_spin.setValue(float(self.record['temperature']))
        
        self.blood_pressure_edit.setText(self.record['blood_pressure'] or "")
        self.symptoms_edit.setText(self.record['symptoms'] or "")
        self.diagnosis_edit.setText(self.record['diagnosis'] or "")
        self.treatment_edit.setText(self.record['treatment'] or "")
        self.medication_edit.setText(self.record['prescribed_medication'] or "")
        self.dosage_edit.setText(self.record['dosage'] or "")
        
        if self.record['severity']:
            self.severity_combo.setCurrentText(self.record['severity'])
        
        if self.record['follow_up_required']:
            self.follow_up_check.setChecked(True)
            if self.record['follow_up_date']:
                self.follow_up_date_edit.setDate(QDate.fromString(str(self.record['follow_up_date']), "yyyy-MM-dd"))
        
        if self.record['referred_to_hospital']:
            self.referral_check.setChecked(True)
        
        if self.record['handled_by_teacher_id']:
            index = self.handler_combo.findData(self.record['handled_by_teacher_id'])
            if index >= 0:
                self.handler_combo.setCurrentIndex(index)
        
        self.notes_edit.setText(self.record['notes'] or "")
        
    def get_record_data(self):
        """Get the health record data from the form"""
        patient_type = self.patient_type_combo.currentData()
        
        return {
            'student_id': self.student_combo.currentData() if patient_type == 'student' else None,
            'teacher_id': self.teacher_combo.currentData() if patient_type == 'teacher' else None,
            'visit_date': self.visit_date_edit.date().toString("yyyy-MM-dd"),
            'visit_time': self.visit_time_edit.time().toString("hh:mm:ss"),
            'temperature': self.temperature_spin.value(),
            'blood_pressure': self.blood_pressure_edit.text(),
            'symptoms': self.symptoms_edit.toPlainText(),
            'diagnosis': self.diagnosis_edit.toPlainText(),
            'treatment': self.treatment_edit.toPlainText(),
            'prescribed_medication': self.medication_edit.text(),
            'dosage': self.dosage_edit.text(),
            'follow_up_required': self.follow_up_check.isChecked(),
            'follow_up_date': self.follow_up_date_edit.date().toString("yyyy-MM-dd") if self.follow_up_check.isChecked() else None,
            'severity': self.severity_combo.currentText(),
            'referred_to_hospital': self.referral_check.isChecked(),
            'notes': self.notes_edit.toPlainText(),
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
            QMessageBox.warning(self, "Validation Error", "Please select who handled this case.")
            return
            
        super().accept()


