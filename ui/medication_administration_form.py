# ui/medication_administration_form.py
import sys
import os
from datetime import datetime
from datetime import timedelta
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

class MedicationAdministrationForm(AuditBaseForm):  # Use the correct class name
    def __init__(self, parent=None, user_session=None, administration=None, students=None, medications=None, teachers=None):
        # Call the parent constructor, which handles db_connection, user_session, and styling
        super().__init__(parent, user_session) 
        
        # Store the specific data passed for this instance
        self.administration = administration
        self.students_data = students or []
        self.medications_data = medications or []
        self.teachers_data = teachers or []
        
        # Initialize other attributes
        self.selected_administration_id = None
        # Note: We'll load data later, after ensuring the connection
        
        # Setup UI first
        self.setup_ui()
        
        # Now load data, ensuring the database connection is active
        self.load_data() # This method should call self._ensure_connection() internally if needed
        
    def setup_ui(self):
        # Create main widget for this form
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("💊 Medication Administration Log")
        title_label.setProperty("class", "page-title")
        layout.addWidget(title_label)
        
        # Search and filter section
        search_group = QGroupBox("Search & Filter")
        search_group.setProperty("class", "search-section")
        search_layout = QHBoxLayout(search_group)
        
        search_label = QLabel("Search:")
        search_label.setProperty("class", "field-label")
        search_layout.addWidget(search_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.setProperty("class", "form-control")
        self.search_entry.setPlaceholderText("Search by student, medication, reason...")
        self.search_entry.textChanged.connect(self.search_administrations)
        search_layout.addWidget(self.search_entry)
        
        date_label = QLabel("Date Range:")
        date_label.setProperty("class", "field-label")
        search_layout.addWidget(date_label)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setProperty("class", "form-control")
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.dateChanged.connect(self.filter_by_date)
        search_layout.addWidget(self.start_date_edit)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setProperty("class", "form-control")
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.dateChanged.connect(self.filter_by_date)
        search_layout.addWidget(self.end_date_edit)
        
        clear_btn = QPushButton("Clear Filters")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.clicked.connect(self.clear_filters)
        search_layout.addWidget(clear_btn)
        
        layout.addWidget(search_group)
        
        # Action buttons and stats combined in one row
        action_stats_layout = QHBoxLayout()
        action_stats_layout.setSpacing(15)
        
        # Left side: Action buttons
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(10)
        
        add_btn = QPushButton("New Administration")
        add_btn.setProperty("class", "success")
        add_btn.setIcon(QIcon("static/icons/add.png"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_administration)
        action_buttons_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Record")
        edit_btn.setProperty("class", "primary")
        edit_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.clicked.connect(self.edit_administration)
        action_buttons_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Record")
        delete_btn.setProperty("class", "danger")
        delete_btn.setIcon(QIcon("static/icons/delete.png"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.clicked.connect(self.delete_administration)
        action_buttons_layout.addWidget(delete_btn)
        
        export_excel_btn = QPushButton("Export Excel")
        export_excel_btn.setProperty("class", "info")
        export_excel_btn.setIcon(QIcon("static/icons/excel.png"))
        export_excel_btn.setIconSize(QSize(16, 16))
        export_excel_btn.clicked.connect(self.export_administrations_excel)
        action_buttons_layout.addWidget(export_excel_btn)
        
        export_pdf_btn = QPushButton("Export PDF")
        export_pdf_btn.setProperty("class", "warning")
        export_pdf_btn.setIcon(QIcon("static/icons/export.png"))
        export_pdf_btn.setIconSize(QSize(16, 16))
        export_pdf_btn.clicked.connect(self.export_administration_pdf)
        #export_pdf_btn.setEnabled(False)  # Disabled until selection
        action_buttons_layout.addWidget(export_pdf_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.clicked.connect(self.refresh_data)
        action_buttons_layout.addWidget(refresh_btn)
        
        # Add stretch to push stats to the right
        action_buttons_layout.addStretch()
        
        # Right side: Stats labels (without group box)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.total_administrations_label = QLabel("Total: 0")
        self.total_administrations_label.setProperty("class", "stat-label")
        self.total_administrations_label.setAlignment(Qt.AlignCenter)
        self.total_administrations_label.setMinimumWidth(80)
        stats_layout.addWidget(self.total_administrations_label)
        
        self.today_administrations_label = QLabel("Today: 0")
        self.today_administrations_label.setProperty("class", "stat-label")
        self.today_administrations_label.setAlignment(Qt.AlignCenter)
        self.today_administrations_label.setMinimumWidth(80)
        stats_layout.addWidget(self.today_administrations_label)
        
        self.this_week_label = QLabel("This Week: 0")
        self.this_week_label.setProperty("class", "stat-label")
        self.this_week_label.setAlignment(Qt.AlignCenter)
        self.this_week_label.setMinimumWidth(80)
        stats_layout.addWidget(self.this_week_label)
        
        # Combine both sides
        action_stats_layout.addLayout(action_buttons_layout, 70)  # 70% width for buttons
        action_stats_layout.addLayout(stats_layout, 30)  # 30% width for stats
        
        layout.addLayout(action_stats_layout)
        
        # Store reference to the PDF button
        self.export_pdf_btn = export_pdf_btn
        
        # Medication administration table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Student", "Medication", "Dosage", "Date", "Time", 
            "Administered By", "Reason", "Notes", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self.on_row_click)
        self.table.setAlternatingRowColors(True)
        self.table.setProperty("class", "data-table")
        
        layout.addWidget(self.table)
        
        # Status info
        self.info_label = QLabel("Select a medication administration record to manage")
        self.info_label.setProperty("class", "info-label")
        layout.addWidget(self.info_label)
        
        # Set the main widget
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(main_widget)
    
    # Inside your current ui/medication_administration_form.py
    
    def load_data(self):
        """Load medication administration data"""
        try:
            # --- ADD THIS BLOCK AT THE VERY BEGINNING ---
            # Ensure database connection is active before performing any DB operations
            try:
                self._ensure_connection() # This is defined in AuditBaseForm
                # Add a check to be extra sure self.cursor is not None after _ensure_connection
                if not hasattr(self, 'cursor') or self.cursor is None:
                    raise Exception("Database cursor is None after _ensure_connection.")
            except Exception as conn_error:
                error_msg = f"Cannot load data: Failed to establish database connection. {conn_error}"
                print(f"ERROR in MedicationAdministrationForm.load_data: {error_msg}")
                QMessageBox.critical(self, "Database Connection Error", error_msg)
                # Optionally, disable UI elements that require data
                self.administration_data = [] # Ensure data list exists even if empty
                self.filtered_data = []
                self.update_table() # Update UI to reflect no data
                self.update_stats()
                return # Stop loading data if connection fails
            # --- END OF ADDITION ---
    
            # Now it's safe to use self.cursor (assuming _ensure_connection worked)
            
            # Load students for dropdowns
            self.cursor.execute("SELECT id, first_name, surname FROM students WHERE is_active = TRUE ORDER BY first_name")
            self.students_data = self.cursor.fetchall()
            
            # Load medications for dropdowns
            self.cursor.execute("SELECT id, name, strength FROM medication_inventory WHERE quantity > 0 ORDER BY name")
            self.medications_data = self.cursor.fetchall()
            
            # Load teachers for dropdowns
            self.cursor.execute("SELECT id, first_name, surname FROM teachers WHERE is_active = TRUE ORDER BY first_name")
            self.teachers_data = self.cursor.fetchall()
    
            # Load administration records
            self.cursor.execute("""
                SELECT ma.*,
                       s.first_name as student_first_name, s.surname as student_last_name,
                       m.name as medication_name, m.strength as medication_strength,
                       t.first_name as teacher_first_name, t.surname as teacher_last_name
                FROM medication_administration ma
                JOIN students s ON ma.student_id = s.id
                JOIN medication_inventory m ON ma.medication_id = m.id
                JOIN teachers t ON ma.administered_by_teacher_id = t.id
                ORDER BY ma.administration_date DESC, ma.administration_time DESC
            """)
            self.administration_data = self.cursor.fetchall()
            
            # Update UI elements
            self.filtered_data = self.administration_data.copy()
            self.update_stats()
            self.update_table()
            
        except mysql.connector.Error as db_error: # Be specific about mysql errors
            error_msg = f"Database error occurred while loading medication administration records: {db_error}"
            print(f"DATABASE ERROR in MedicationAdministrationForm.load_data: {db_error}")
            # Check if it's a specific table missing error
            if "medication_administration" in str(db_error).lower():
                 QMessageBox.warning(self, "Database Setup Required",
                                    "The medication administration table doesn't exist yet. "
                                    "Please contact your administrator to run the database setup.")
                 self.administration_data = []
                 self.filtered_data = []
                 self.update_table()
                 self.update_stats()
            else:
                 QMessageBox.critical(self, "Database Error", error_msg)
        except Exception as e: # Catch other unexpected errors
            error_msg = f"An unexpected error occurred while loading data: {e}"
            print(f"UNEXPECTED ERROR in MedicationAdministrationForm.load_data: {e}")
            QMessageBox.critical(self, "Error", error_msg)

    def update_table(self):
        """Update the administration table with current data"""
        self.table.setRowCount(0)
        
        for row, record in enumerate(self.filtered_data):
            self.table.insertRow(row)
            
            # Format student name
            student_name = f"{record['student_first_name']} {record['student_last_name']}"
            
            # Format medication name with strength
            medication_name = f"{record['medication_name']}"
            if record.get('medication_strength'):
                medication_name += f" ({record['medication_strength']})"
            
            # Format administered by name
            administered_by = f"{record['teacher_first_name']} {record['teacher_last_name']}"
            
            # Format date and time - using the pre-formatted time from database
            admin_date = record['administration_date'].strftime('%Y-%m-%d') if record['administration_date'] else ""
            admin_time = record.get('formatted_time', '')
            
            # Add items to table
            self.table.setItem(row, 0, QTableWidgetItem(str(record['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(student_name))
            self.table.setItem(row, 2, QTableWidgetItem(medication_name))
            self.table.setItem(row, 3, QTableWidgetItem(record.get('dosage', '')))
            self.table.setItem(row, 4, QTableWidgetItem(admin_date))
            self.table.setItem(row, 5, QTableWidgetItem(admin_time))
            self.table.setItem(row, 6, QTableWidgetItem(administered_by))
            self.table.setItem(row, 7, QTableWidgetItem(record.get('reason', '')[:50] + '...' 
                                                       if record.get('reason') and len(record['reason']) > 50 
                                                       else record.get('reason', '')))
            self.table.setItem(row, 8, QTableWidgetItem(record.get('notes', '')[:30] + '...' 
                                                       if record.get('notes') and len(record['notes']) > 30 
                                                       else record.get('notes', '')))
            self.table.setItem(row, 9, QTableWidgetItem("Completed"))
            
            # Color code based on date (recent entries get highlighted)
            try:
                if record['administration_date']:
                    admin_datetime = datetime.combine(record['administration_date'], datetime.min.time())
                    days_diff = (datetime.now().date() - record['administration_date']).days
                    
                    if days_diff < 1:
                        color = QColor(230, 255, 230)  # Light green for today's entries
                    elif days_diff < 7:
                        color = QColor(255, 245, 230)  # Light orange for this week's entries
                    else:
                        color = QColor(240, 240, 240)  # Light gray for older entries
                else:
                    color = QColor(240, 240, 240)  # Default color
            except Exception:
                color = QColor(240, 240, 240)  # Fallback color in case of error
                
            for col in range(self.table.columnCount()):
                self.table.item(row, col).setBackground(color)
        
        self.info_label.setText(f"Showing {len(self.filtered_data)} of {len(self.administration_data)} administration records")
    
    def update_stats(self):
        """Update statistics labels"""
        total_administrations = len(self.administration_data)
        
        today = datetime.now().date()
        today_administrations = sum(1 for record in self.administration_data 
                                   if record['administration_date'] == today)
        
        # Calculate this week's administrations
        week_start = today - timedelta(days=today.weekday())
        this_week_administrations = sum(1 for record in self.administration_data 
                                       if record['administration_date'] >= week_start)
        
        self.total_administrations_label.setText(f"Total: {total_administrations}")
        self.today_administrations_label.setText(f"Today: {today_administrations}")
        self.this_week_label.setText(f"This Week: {this_week_administrations}")
    
    
    def search_administrations(self):
        """Search administrations based on search text"""
        search_text = self.search_entry.text().lower().strip()
        
        if not search_text:
            self.filtered_data = self.administration_data.copy()
        else:
            self.filtered_data = [
                record for record in self.administration_data
                if (search_text in (record['student_first_name'] or '').lower() or 
                    search_text in (record['student_last_name'] or '').lower() or 
                    search_text in (record['medication_name'] or '').lower() or
                    search_text in (record.get('reason', '') or '').lower() or
                    search_text in (record.get('notes', '') or '').lower())
            ]
            
        self.update_table()
    
    def filter_by_date(self):
        """Filter administrations by date range"""
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()
        
        self.filtered_data = [
            record for record in self.administration_data
            if record['administration_date'] and start_date <= record['administration_date'] <= end_date
        ]
            
        self.update_table()
    
    def clear_filters(self):
        """Clear all filters"""
        self.search_entry.clear()
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit.setDate(QDate.currentDate())
        self.filtered_data = self.administration_data.copy()
        self.update_table()
    
    def on_row_click(self, row, column):
        """Handle administration row selection"""
        if row < 0 or row >= len(self.filtered_data):
            return
            
        record_id = self.table.item(row, 0).text()
        self.selected_administration_id = int(record_id)
        
        student_name = self.table.item(row, 1).text()
        medication_name = self.table.item(row, 2).text()
        self.info_label.setText(f"Selected: {student_name}'s {medication_name} administration")
        
        # Enable PDF export button
        self.export_pdf_btn.setEnabled(True)
    
    def add_administration(self):
        """Open dialog to add a new medication administration"""
        dialog = MedicationAdministrationDialog(
            self, 
            students=self.students_data, 
            medications=self.medications_data, 
            teachers=self.teachers_data
        )
        if dialog.exec() == QDialog.Accepted:
            administration_data = dialog.get_administration_data()
            self.save_administration(administration_data)
    
    def edit_administration(self):
        """Open dialog to edit selected administration"""
        if not hasattr(self, 'selected_administration_id') or not self.selected_administration_id:
            QMessageBox.warning(self, "Warning", "Please select a medication administration record to edit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.administration_data:
            if record['id'] == self.selected_administration_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected administration record not found.")
            return
            
        dialog = MedicationAdministrationDialog(
            self, 
            administration=selected_record, 
            students=self.students_data, 
            medications=self.medications_data, 
            teachers=self.teachers_data
        )
        if dialog.exec() == QDialog.Accepted:
            administration_data = dialog.get_administration_data()
            self.update_administration(self.selected_administration_id, administration_data)
    
    def delete_administration(self):
        """Delete selected administration record"""
        if not hasattr(self, 'selected_administration_id') or not self.selected_administration_id:
            QMessageBox.warning(self, "Warning", "Please select a medication administration record to delete.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.administration_data:
            if record['id'] == self.selected_administration_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected administration record not found.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the administration record for {selected_record['student_first_name']} {selected_record['student_last_name']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM medication_administration WHERE id = %s", (self.selected_administration_id,))
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Administration record deleted successfully!")
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete administration record: {e}")
    
    def refresh_data(self):
        """Refresh administration data"""
        self.load_data()
        QMessageBox.information(self, "Success", "Medication administration data refreshed!")
    
    def save_administration(self, administration_data):
        """Save new medication administration to database"""
        try:
            query = """
                INSERT INTO medication_administration 
                (student_id, medication_id, administered_by_teacher_id, 
                 administration_date, administration_time, dosage, reason, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                administration_data['student_id'],
                administration_data['medication_id'],
                administration_data['administered_by_teacher_id'],
                administration_data['administration_date'],
                administration_data['administration_time'],
                administration_data['dosage'],
                administration_data['reason'],
                administration_data['notes']
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Medication administration recorded successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to record medication administration: {e}")
    
    def update_administration(self, administration_id, administration_data):
        """Update existing medication administration in database"""
        try:
            query = """
                UPDATE medication_administration 
                SET student_id = %s, medication_id = %s, administered_by_teacher_id = %s,
                    administration_date = %s, administration_time = %s, dosage = %s,
                    reason = %s, notes = %s
                WHERE id = %s
            """
            values = (
                administration_data['student_id'],
                administration_data['medication_id'],
                administration_data['administered_by_teacher_id'],
                administration_data['administration_date'],
                administration_data['administration_time'],
                administration_data['dosage'],
                administration_data['reason'],
                administration_data['notes'],
                administration_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Medication administration updated successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update medication administration: {e}")
    
    def export_administrations_excel(self):
        """Export medication administrations with the green header style"""
        try:
            # Get school info for the title
            school_info = self.get_school_info()
            
            # Prepare data for export - convert to list of lists
            export_data = []
            for record in self.administration_data:
                row_data = [
                    record['id'],
                    f"{record['student_first_name']} {record['student_last_name']}",
                    record['medication_name'],
                    record.get('medication_strength', ''),
                    record.get('dosage', ''),
                    record['administration_date'].strftime('%Y-%m-%d') if record['administration_date'] else 'N/A',
                    str(record['administration_time']) if record['administration_time'] else 'N/A',
                    record.get('reason', ''),
                    record.get('notes', ''),
                    f"{record['teacher_first_name']} {record['teacher_last_name']}",
                    record['created_at'].strftime('%Y-%m-%d %H:%M:%S') if record['created_at'] else 'N/A'
                ]
                export_data.append(row_data)
    
            # Define headers
            headers = [
                'ID', 'Student', 'Medication', 'Strength', 'Dosage', 'Date', 
                'Time', 'Reason', 'Notes', 'Administered By', 'Recorded At'
            ]
            
            # Include date range in the title if filters are applied
            start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            
            title = (f"{school_info['name']} - MEDICATION ADMINISTRATIONS\n"
                     f"Date Range: {start_date} to {end_date}")
            
            # Use shared export method
            self.export_with_green_header(
                data=export_data,
                headers=headers,
                filename_prefix="medication_administrations_export",
                title=title
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export medication administrations: {e}")
    
    def export_administration_pdf(self):
        """Export individual administration as PDF"""
        if not hasattr(self, 'selected_administration_id') or not self.selected_administration_id:
            QMessageBox.warning(self, "Selection Required", "Please select a medication administration record first by clicking on a row in the table.")
            return
        
        try:
            # Find the selected record
            selected_record = None
            for record in self.administration_data:
                if record['id'] == self.selected_administration_id:
                    selected_record = record
                    break
            
            if not selected_record:
                QMessageBox.warning(self, "Error", "Selected administration record not found.")
                return
            
            # Generate PDF bytes
            pdf_bytes = self.generate_administration_pdf_bytes(selected_record)
            
            # Use enhanced PDF viewer
            try:
                from utils.pdf_utils import view_pdf
                view_pdf(pdf_bytes, self)
            except ImportError as e:
                print(f"PDF viewer import error: {e}")
                # Fallback to file save
                self.save_administration_pdf_fallback(pdf_bytes, selected_record)
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate administration PDF: {str(e)}")
    
    def generate_administration_pdf_bytes(self, selected_record):
        import tempfile
        import os
        from fpdf import FPDF
        from datetime import datetime
    
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
    
        # --- Simplified and Direct Time Handling ---
        # Assume the value from the database is a string like '14:40:02'
        raw_admin_time = selected_record.get('administration_time')
        admin_time = "N/A"
        if raw_admin_time:
            if isinstance(raw_admin_time, str):
                # If it's already a string in HH:MM:SS format, just take HH:MM
                parts = raw_admin_time.split(':')
                if len(parts) >= 2:
                    admin_time = f"{parts[0]}:{parts[1]}"
                else:
                    admin_time = raw_admin_time # Fallback if format is unexpected
            else:
                # If it's not a string, try converting it to string first, then parse
                try:
                    time_str = str(raw_admin_time)
                    parts = time_str.split(':')
                    if len(parts) >= 2:
                        admin_time = f"{parts[0]}:{parts[1]}"
                    else:
                        admin_time = time_str
                except:
                    admin_time = "N/A" # Final fallback
        # --- End Simplified Time Handling ---
    
        # --- Simplified and Direct Date Handling ---
        # Assume the value from the database is a string like '2025-09-10'
        raw_admin_date = selected_record.get('administration_date')
        admin_date = "N/A"
        if raw_admin_date:
            if isinstance(raw_admin_date, str):
                # If it's already a string, use it directly or reformat if needed
                # Assuming format is YYYY-MM-DD, which is fine for display
                admin_date = raw_admin_date
            else:
                # If it's not a string, try converting it to string
                try:
                    admin_date = str(raw_admin_date)
                except:
                    admin_date = "N/A" # Final fallback
        # --- End Simplified Date Handling ---
    
        class AdministrationPDF(FPDF):
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
                self.cell(0, 8, "MEDICATION ADMINISTRATION RECORD", 0, 1, "C")
                
                self.set_font("Arial", "", 8)
                self.set_text_color(100, 100, 100)
                doc_id = f"Document ID: MA-{selected_record['id']:06d}"
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
                # --- Reduced label width ---
                label_width = 40 # Changed from 50 to 40 to reduce space
                # ---
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
    
        pdf = AdministrationPDF()
        pdf.add_page()
        
        student_name = f"{selected_record['student_first_name']} {selected_record['student_last_name']}"
        medication_name = f"{selected_record['medication_name']}"
        if selected_record.get('medication_strength'):
            medication_name += f" ({selected_record['medication_strength']})"
        
        administered_by = f"{selected_record['teacher_first_name']} {selected_record['teacher_last_name']}"
        
        # Use the processed admin_date and admin_time
        administration_fields = [
            ("Student", student_name),
            ("Medication", medication_name),
            ("Dosage", selected_record.get('dosage', 'N/A')),
            ("Date", admin_date),       # Use processed date
            ("Time", admin_time),       # Use processed time
            ("Administered By", administered_by),
            ("Reason", selected_record.get('reason', 'N/A')),
            ("Record ID", f"MA-{selected_record['id']:06d}")
        ]
        
        pdf.add_info_box("ADMINISTRATION DETAILS", administration_fields, pdf.get_y(), 36)
        pdf.ln(6)
        
        if selected_record.get('notes'):
            pdf.add_section_header("ADMINISTRATION NOTES")
            pdf.add_multiline_content(selected_record['notes'])
            pdf.ln(2)
        
        pdf.add_section_header("IMPORTANT INFORMATION")
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 5, "This document serves as an official record of medication administration.", 0, 1, "L")
        pdf.cell(0, 5, "All medication administrations must be documented for legal and medical safety purposes.", 0, 1, "L")
        pdf.ln(8)
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, 6, "Administering Staff Signature:", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, "........................................................", 0, 1, "L")
        pdf.cell(60, 5, "Date:", 0, 0, "L")
        pdf.cell(0, 5, datetime.now().strftime("%Y-%m-%d"), 0, 1, "L")
        pdf.ln(6)
        
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, 6, "Witness Signature (if required):", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, "........................................................", 0, 1, "L")
        pdf.cell(60, 5, "Date:", 0, 0, "L")
        pdf.cell(0, 5, datetime.now().strftime("%Y-%m-%d"), 0, 1, "L")
        pdf.ln(3)
        
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

    def save_administration_pdf_fallback(self, pdf_bytes, selected_record):
        """Fallback method to save administration PDF if viewer not available"""
        student_name = f"{selected_record['student_first_name']}_{selected_record['student_last_name']}"
        medication_name = selected_record['medication_name'].replace(' ', '_')
        default_filename = f"medication_administration_{student_name}_{medication_name}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Administration PDF", default_filename, "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(pdf_bytes)
                QMessageBox.information(self, "Success", f"PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF: {str(e)}")


class MedicationAdministrationDialog(QDialog):
    def __init__(self, parent=None, administration=None, students=None, medications=None, teachers=None):
        super().__init__(parent)
        self.administration = administration
        self.students = students or []
        self.medications = medications or []
        self.teachers = teachers or []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Edit Medication Administration" if self.administration else "Record New Medication Administration")
        self.setMinimumSize(650, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)
        
        # Student selection
        student_group = QGroupBox("Student Information")
        student_layout = QFormLayout(student_group)
        
        self.student_combo = QComboBox()
        self.student_combo.setProperty("class", "form-control")
        self.student_combo.addItem("Select Student", None)
        for student in self.students:
            self.student_combo.addItem(f"{student['first_name']} {student['surname']}", student['id'])
        
        student_layout.addRow("Student *:", self.student_combo)
        form_layout.addWidget(student_group)
        
        # Medication information
        medication_group = QGroupBox("Medication Information")
        medication_layout = QFormLayout(medication_group)
        
        self.medication_combo = QComboBox()
        self.medication_combo.setProperty("class", "form-control")
        self.medication_combo.addItem("Select Medication", None)
        for medication in self.medications:
            display_text = f"{medication['name']}"
            if medication.get('strength'):
                display_text += f" ({medication['strength']})"
            self.medication_combo.addItem(display_text, medication['id'])
        
        self.dosage_edit = QLineEdit()
        self.dosage_edit.setProperty("class", "form-control")
        self.dosage_edit.setPlaceholderText("e.g., 1 tablet, 5ml, 1 spray")
        
        medication_layout.addRow("Medication *:", self.medication_combo)
        medication_layout.addRow("Dosage *:", self.dosage_edit)
        
        form_layout.addWidget(medication_group)
        
        # Administration details
        admin_group = QGroupBox("Administration Details")
        admin_layout = QFormLayout(admin_group)
        
        self.date_edit = QDateEdit()
        self.date_edit.setProperty("class", "form-control")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setProperty("class", "form-control")
        self.time_edit.setTime(QTime.currentTime())
        
        self.reason_edit = QLineEdit()
        self.reason_edit.setProperty("class", "form-control")
        self.reason_edit.setPlaceholderText("Reason for administration")
        
        admin_layout.addRow("Date *:", self.date_edit)
        admin_layout.addRow("Time *:", self.time_edit)
        admin_layout.addRow("Reason:", self.reason_edit)
        
        form_layout.addWidget(admin_group)
        
        # Administered by
        admin_by_group = QGroupBox("Administration Record")
        admin_by_layout = QFormLayout(admin_by_group)
        
        self.admin_by_combo = QComboBox()
        self.admin_by_combo.setProperty("class", "form-control")
        self.admin_by_combo.addItem("Select Staff Member", None)
        for teacher in self.teachers:
            self.admin_by_combo.addItem(f"{teacher['first_name']} {teacher['surname']}", teacher['id'])
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setProperty("class", "form-control")
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Additional notes or observations...")
        
        admin_by_layout.addRow("Administered By *:", self.admin_by_combo)
        admin_by_layout.addRow("Notes:", self.notes_edit)
        
        form_layout.addWidget(admin_by_group)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Pre-fill data if editing
        if self.administration:
            self.prefill_data()
        
        # Button box
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Record")
        save_btn.setProperty("class", "success")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def prefill_data(self):
        """Pre-fill form data if editing"""
        if self.administration['student_id']:
            index = self.student_combo.findData(self.administration['student_id'])
            if index >= 0:
                self.student_combo.setCurrentIndex(index)
        
        if self.administration['medication_id']:
            index = self.medication_combo.findData(self.administration['medication_id'])
            if index >= 0:
                self.medication_combo.setCurrentIndex(index)
        
        self.dosage_edit.setText(self.administration.get('dosage', ''))
        
        if self.administration['administration_date']:
            self.date_edit.setDate(QDate.fromString(str(self.administration['administration_date']), "yyyy-MM-dd"))
        
        if self.administration['administration_time']:
            self.time_edit.setTime(QTime.fromString(str(self.administration['administration_time']), "hh:mm:ss"))
        
        self.reason_edit.setText(self.administration.get('reason', ''))
        
        if self.administration['administered_by_teacher_id']:
            index = self.admin_by_combo.findData(self.administration['administered_by_teacher_id'])
            if index >= 0:
                self.admin_by_combo.setCurrentIndex(index)
        
        self.notes_edit.setText(self.administration.get('notes', ''))
        
    def get_administration_data(self):
        """Get the administration data from the form"""
        return {
            'student_id': self.student_combo.currentData(),
            'medication_id': self.medication_combo.currentData(),
            'administered_by_teacher_id': self.admin_by_combo.currentData(),
            'administration_date': self.date_edit.date().toString("yyyy-MM-dd"),
            'administration_time': self.time_edit.time().toString("hh:mm:ss"),
            'dosage': self.dosage_edit.text().strip(),
            'reason': self.reason_edit.text().strip(),
            'notes': self.notes_edit.toPlainText().strip()
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        # Basic validation
        if not self.student_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a student.")
            return
            
        if not self.medication_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a medication.")
            return
            
        if not self.dosage_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a dosage.")
            return
            
        if not self.admin_by_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select who administered the medication.")
            return
            
        super().accept()