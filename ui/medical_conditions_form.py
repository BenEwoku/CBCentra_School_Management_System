# ui/medical_conditions_form.py
import sys
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, 
    QTabWidget, QMenu, QCheckBox, QDateEdit, QTextEdit, QApplication
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

class MedicalConditionsForm(AuditBaseForm):
    def __init__(self, parent=None, db_connection=None, cursor=None, students_data=None, teachers_data=None, user_session=None):
        # Call parent constructor
        super().__init__(parent, user_session)
        
        # Use provided connection or create new one
        if db_connection:
            self.db_connection = db_connection
            self.cursor = cursor
        else:
            # Fallback: create new connection if not provided
            try:
                self.db_connection = get_db_connection()
                self.cursor = self.db_connection.cursor(buffered=True, dictionary=True)
            except Error as e:
                print(f"DEBUG: Database connection failed: {e}")
                QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
                return
        
        self.students_data = students_data or []
        self.teachers_data = teachers_data or []
        self.selected_condition_id = None
        self.medical_conditions_data = []
        self.conditions_filtered_data = []
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        # Create main widget for this form
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Medical Conditions Management")
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
        self.search_entry.setPlaceholderText("Search by student, condition...")
        self.search_entry.textChanged.connect(self.search_conditions)
        search_layout.addWidget(self.search_entry)
        
        status_label = QLabel("Status:")
        status_label.setProperty("class", "field-label")
        search_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setProperty("class", "form-control")
        self.status_filter.addItems(["All", "Active", "Inactive"])
        self.status_filter.currentTextChanged.connect(self.filter_conditions_by_status)
        search_layout.addWidget(self.status_filter)
        
        severity_label = QLabel("Severity:")
        severity_label.setProperty("class", "field-label")
        search_layout.addWidget(severity_label)
        
        self.severity_filter = QComboBox()
        self.severity_filter.setProperty("class", "form-control")
        self.severity_filter.addItems(["All", "Mild", "Moderate", "Severe"])
        self.severity_filter.currentTextChanged.connect(self.filter_conditions_by_severity)
        search_layout.addWidget(self.severity_filter)
        
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
        
        add_btn = QPushButton("New Condition")
        add_btn.setProperty("class", "success")
        add_btn.setIcon(QIcon("static/icons/add.png"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_medical_condition)
        action_buttons_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Condition")
        edit_btn.setProperty("class", "primary")
        edit_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.clicked.connect(self.edit_medical_condition)
        action_buttons_layout.addWidget(edit_btn)
        
        toggle_btn = QPushButton("Toggle Status")
        toggle_btn.setProperty("class", "warning")
        toggle_btn.setIcon(QIcon("static/icons/toggle.png"))
        toggle_btn.setIconSize(QSize(16, 16))
        toggle_btn.clicked.connect(self.toggle_condition_status)
        action_buttons_layout.addWidget(toggle_btn)
        
        export_excel_btn = QPushButton("Export Excel")
        export_excel_btn.setProperty("class", "info")
        export_excel_btn.setIcon(QIcon("static/icons/excel.png"))
        export_excel_btn.setIconSize(QSize(16, 16))
        export_excel_btn.clicked.connect(self.export_conditions_excel)
        action_buttons_layout.addWidget(export_excel_btn)
        
        export_pdf_btn = QPushButton("Export PDF")
        export_pdf_btn.setProperty("class", "warning")
        export_pdf_btn.setIcon(QIcon("static/icons/pdf.png"))
        export_pdf_btn.setIconSize(QSize(16, 16))
        export_pdf_btn.clicked.connect(self.export_condition_pdf)
        #export_pdf_btn.setEnabled(False)
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
        
        self.total_conditions_label = QLabel("Total: 0")
        self.total_conditions_label.setProperty("class", "stat-label")
        self.total_conditions_label.setAlignment(Qt.AlignCenter)
        self.total_conditions_label.setMinimumWidth(80)
        stats_layout.addWidget(self.total_conditions_label)
        
        self.active_conditions_label = QLabel("Active: 0")
        self.active_conditions_label.setProperty("class", "stat-label")
        self.active_conditions_label.setAlignment(Qt.AlignCenter)
        self.active_conditions_label.setMinimumWidth(80)
        stats_layout.addWidget(self.active_conditions_label)
        
        self.severe_conditions_label = QLabel("Severe: 0")
        self.severe_conditions_label.setProperty("class", "stat-label")
        self.severe_conditions_label.setAlignment(Qt.AlignCenter)
        self.severe_conditions_label.setMinimumWidth(80)
        stats_layout.addWidget(self.severe_conditions_label)
        
        # Combine both sides
        action_stats_layout.addLayout(action_buttons_layout, 70)  # 70% width for buttons
        action_stats_layout.addLayout(stats_layout, 30)  # 30% width for stats
        
        layout.addLayout(action_stats_layout)
        
        # Medical conditions table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Student", "Condition", "Diagnosis Date", "Severity", 
            "Status", "Special Requirements", "Recorded By", "Last Updated"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self.on_row_click)
        self.table.setAlternatingRowColors(True)
        self.table.setProperty("class", "data-table")
        
        layout.addWidget(self.table)
        
        # Status info
        self.info_label = QLabel("Select a medical condition to manage")
        self.info_label.setProperty("class", "info-label")
        layout.addWidget(self.info_label)
        
        # Set the main widget
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(main_widget)
    
    def load_data(self):
        """Load medical conditions data"""
        try:
            self.cursor.execute("""
                SELECT mc.*, 
                       s.first_name, s.surname,
                       t.first_name as recorded_first_name,
                       t.surname as recorded_last_name
                FROM student_medical_conditions mc
                JOIN students s ON mc.student_id = s.id
                LEFT JOIN teachers t ON mc.recorded_by_teacher_id = t.id
                ORDER BY mc.is_active DESC, mc.severity DESC, mc.updated_at DESC
            """)
            self.medical_conditions_data = self.cursor.fetchall()
            self.conditions_filtered_data = self.medical_conditions_data.copy()
            
            self.update_stats()
            self.update_table()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load medical conditions: {e}")
    
    def update_stats(self):
        """Update statistics labels"""
        total_conditions = len(self.medical_conditions_data)
        active_conditions = sum(1 for record in self.medical_conditions_data if record['is_active'])
        severe_conditions = sum(1 for record in self.medical_conditions_data if record['severity'] == 'Severe')
        
        self.total_conditions_label.setText(f"Total: {total_conditions}")
        self.active_conditions_label.setText(f"Active: {active_conditions}")
        self.severe_conditions_label.setText(f"Severe: {severe_conditions}")
    
    def update_table(self):
        """Update the medical conditions table with current data"""
        self.table.setRowCount(0)
        
        for row, record in enumerate(self.conditions_filtered_data):
            self.table.insertRow(row)
            
            # Format student name
            student_name = f"{record['first_name']} {record['surname']}"
            
            # Format recorded by name
            recorded_by = f"{record['recorded_first_name']} {record['recorded_last_name']}" if record['recorded_first_name'] else "System"
            
            # Format special requirements (shortened)
            special_reqs = (record['special_requirements'][:50] + '...') if record['special_requirements'] and len(record['special_requirements']) > 50 else record['special_requirements'] or "None"
            
            # Add items to table
            self.table.setItem(row, 0, QTableWidgetItem(str(record['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(student_name))
            self.table.setItem(row, 2, QTableWidgetItem(record['condition_name']))
            self.table.setItem(row, 3, QTableWidgetItem(str(record['diagnosis_date']) if record['diagnosis_date'] else "Unknown"))
            self.table.setItem(row, 4, QTableWidgetItem(record['severity']))
            self.table.setItem(row, 5, QTableWidgetItem("Active" if record['is_active'] else "Inactive"))
            self.table.setItem(row, 6, QTableWidgetItem(special_reqs))
            self.table.setItem(row, 7, QTableWidgetItem(recorded_by))
            self.table.setItem(row, 8, QTableWidgetItem(str(record['updated_at'])))
            
            # Color code based on severity
            if record['severity'] == 'Severe':
                color = QColor(255, 230, 230)  # Light red for severe
            elif record['severity'] == 'Moderate':
                color = QColor(255, 245, 230)  # Light orange for moderate
            else:
                color = QColor(230, 255, 230)  # Light green for mild
                
            for col in range(self.table.columnCount()):
                self.table.item(row, col).setBackground(color)
        
        self.info_label.setText(f"Showing {len(self.conditions_filtered_data)} of {len(self.medical_conditions_data)} medical conditions")
    
    def search_conditions(self):
        """Search conditions based on search text"""
        search_text = self.search_entry.text().lower().strip()
        
        if not search_text:
            self.conditions_filtered_data = self.medical_conditions_data.copy()
        else:
            self.conditions_filtered_data = [
                record for record in self.medical_conditions_data
                if (search_text in (record['first_name'] or '').lower() or 
                    search_text in (record['surname'] or '').lower() or 
                    search_text in (record['condition_name'] or '').lower() or
                    search_text in (record['special_requirements'] or '').lower())
            ]
            
        self.update_table()
    
    def filter_conditions_by_status(self):
        """Filter conditions by active status"""
        status = self.status_filter.currentText()
        
        if status == "All":
            self.conditions_filtered_data = self.medical_conditions_data.copy()
        elif status == "Active":
            self.conditions_filtered_data = [record for record in self.medical_conditions_data if record['is_active']]
        else:  # Inactive
            self.conditions_filtered_data = [record for record in self.medical_conditions_data if not record['is_active']]
            
        self.update_table()
    
    def filter_conditions_by_severity(self):
        """Filter conditions by severity"""
        severity = self.severity_filter.currentText()
        
        if severity == "All":
            self.conditions_filtered_data = self.medical_conditions_data.copy()
        else:
            self.conditions_filtered_data = [record for record in self.medical_conditions_data if record['severity'] == severity]
            
        self.update_table()
    
    def clear_filters(self):
        """Clear all conditions filters"""
        self.search_entry.clear()
        self.status_filter.setCurrentIndex(0)
        self.severity_filter.setCurrentIndex(0)
        self.conditions_filtered_data = self.medical_conditions_data.copy()
        self.update_table()
    
    def on_row_click(self, row, column):
        """Handle medical condition row selection"""
        if row < 0 or row >= len(self.conditions_filtered_data):
            return
            
        record_id = self.table.item(row, 0).text()
        self.selected_condition_id = int(record_id)
        
        student_name = self.table.item(row, 1).text()
        condition_name = self.table.item(row, 2).text()
        self.info_label.setText(f"Selected: {student_name}'s {condition_name}")
        
        # Enable PDF export button
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QPushButton) and widget.text() == "Export Condition PDF":
                widget.setEnabled(True)
                break
    
    def add_medical_condition(self):
        """Open dialog to add a new medical condition"""
        dialog = MedicalConditionDialog(self, students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            condition_data = dialog.get_condition_data()
            self.save_medical_condition(condition_data)
    
    def edit_medical_condition(self):
        """Open dialog to edit selected medical condition"""
        if not hasattr(self, 'selected_condition_id') or not self.selected_condition_id:
            QMessageBox.warning(self, "Warning", "Please select a medical condition to edit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.medical_conditions_data:
            if record['id'] == self.selected_condition_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected medical condition not found.")
            return
            
        dialog = MedicalConditionDialog(self, condition=selected_record, students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            condition_data = dialog.get_condition_data()
            self.update_medical_condition(self.selected_condition_id, condition_data)
    
    def toggle_condition_status(self):
        """Toggle active status of selected medical condition"""
        if not hasattr(self, 'selected_condition_id') or not self.selected_condition_id:
            QMessageBox.warning(self, "Warning", "Please select a medical condition to toggle.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.medical_conditions_data:
            if record['id'] == self.selected_condition_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected medical condition not found.")
            return
            
        new_status = not selected_record['is_active']
        status_text = "active" if new_status else "inactive"
        
        reply = QMessageBox.question(
            self, "Confirm Status Change",
            f"Are you sure you want to mark {selected_record['condition_name']} as {status_text} for {selected_record['first_name']} {selected_record['surname']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute(
                    "UPDATE student_medical_conditions SET is_active = %s WHERE id = %s",
                    (new_status, self.selected_condition_id)
                )
                self.db_connection.commit()
                QMessageBox.information(self, "Success", f"Medical condition status updated to {status_text}!")
                self.load_data()
                
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to update condition status: {e}")
    
    def refresh_data(self):
        """Refresh medical conditions data"""
        self.load_data()
        QMessageBox.information(self, "Success", "Medical conditions data refreshed!")
    
    def save_medical_condition(self, condition_data):
        """Save new medical condition to database"""
        try:
            query = """
                INSERT INTO student_medical_conditions 
                (student_id, condition_name, diagnosis_date, severity, 
                 treatment_plan, special_requirements, is_active, recorded_by_teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                condition_data['student_id'],
                condition_data['condition_name'],
                condition_data['diagnosis_date'],
                condition_data['severity'],
                condition_data['treatment_plan'],
                condition_data['special_requirements'],
                condition_data['is_active'],
                condition_data['recorded_by_teacher_id']
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Medical condition added successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add medical condition: {e}")
    
    def update_medical_condition(self, condition_id, condition_data):
        """Update existing medical condition in database"""
        try:
            query = """
                UPDATE student_medical_conditions 
                SET student_id = %s, condition_name = %s, diagnosis_date = %s, 
                    severity = %s, treatment_plan = %s, special_requirements = %s, 
                    is_active = %s, recorded_by_teacher_id = %s
                WHERE id = %s
            """
            values = (
                condition_data['student_id'],
                condition_data['condition_name'],
                condition_data['diagnosis_date'],
                condition_data['severity'],
                condition_data['treatment_plan'],
                condition_data['special_requirements'],
                condition_data['is_active'],
                condition_data['recorded_by_teacher_id'],
                condition_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Medical condition updated successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update medical condition: {e}")
    
    def export_conditions_excel(self):
        """Export medical conditions with the green header style"""
        try:
            # Get school info for the title
            school_info = self.get_school_info()
            
            # Prepare data for export - convert to list of lists
            export_data = []
            for record in self.medical_conditions_data:
                row_data = [
                    record['id'],
                    f"{record['first_name']} {record['surname']}",
                    record['condition_name'],
                    record['diagnosis_date'].strftime('%Y-%m-%d') if record['diagnosis_date'] else 'N/A',
                    record['severity'],
                    'Active' if record['is_active'] else 'Inactive',
                    record['treatment_plan'],
                    record['special_requirements'],
                    f"{record.get('recorded_first_name', '')} {record.get('recorded_last_name', '')}",
                    record['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if record['updated_at'] else 'N/A'
                ]
                export_data.append(row_data)
    
            # Define headers
            headers = [
                'ID', 'Student', 'Condition', 'Diagnosis Date', 'Severity', 
                'Status', 'Treatment Plan', 'Special Requirements', 
                'Recorded By', 'Last Updated'
            ]
            
            # Create title
            title = f"{school_info['name']} - MEDICAL CONDITIONS"
            
            # Use shared export method
            self.export_with_green_header(
                data=export_data,
                headers=headers,
                filename_prefix="medical_conditions_export",
                title=title
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export medical conditions: {e}")

    def generate_medical_condition_pdf_bytes(self, selected_record):
        """Generate professional medical condition PDF with school branding and detailed layout"""
        import tempfile
        import os
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
        
        # Fetch student photo and registration number
        student_photo = None
        student_reg_no = "N/A"
        try:
            self.cursor.execute("SELECT photo_path, regNo FROM students WHERE id = %s LIMIT 1", (selected_record['student_id'],))
            student_photo_res = self.cursor.fetchone()
            if student_photo_res:
                if student_photo_res.get('photo_path'):
                    photo_path = student_photo_res['photo_path']
                    if os.path.exists(photo_path):
                        student_photo = photo_path
                student_reg_no = student_photo_res.get('regNo', 'N/A')
        except Exception:
            student_photo = None
        
        class MedicalConditionPDF(FPDF):
            def __init__(self):
                super().__init__(orientation='P', unit='mm', format='A4')
                self.set_margins(15, 15, 15)
                self.set_auto_page_break(auto=False)
            
            def header(self):
                # School logo (left)
                if os.path.exists(school_logo):
                    try:
                        self.image(school_logo, 15, 10, 25)
                    except:
                        pass
                
                # Student photo (top-right)
                if student_photo:
                    try:
                        self.image(student_photo, 165, 5, 30, 30)
                    except:
                        pass
                
                # School info (center)
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
                
                # Document title
                self.ln(4)
                self.set_font("Arial", "B", 13)
                self.set_text_color(70, 70, 70)
                self.cell(0, 8, "MEDICAL CONDITION REPORT", 0, 1, "C")
                
                self.set_font("Arial", "", 8)
                self.set_text_color(100, 100, 100)
                doc_id = f"Document ID: MC-{selected_record['id']:06d}"
                gen_time = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.cell(0, 4, f"{doc_id} | {gen_time}", 0, 1, "C")
                
                self.set_font("Arial", "I", 7)
                self.set_text_color(200, 0, 0)
                self.cell(0, 4, "CONFIDENTIAL MEDICAL INFORMATION", 0, 1, "C")
                
                # Separator line
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
            
            def add_info_box(self, title, fields, y_pos, height=28):  # Reduced height from 36 to 28
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
        
        # Create PDF
        pdf = MedicalConditionPDF()
        pdf.add_page()
        
        # Student information
        student_name = f"{selected_record.get('first_name', '')} {selected_record.get('surname', '')}".strip()
        recorded_by = f"{selected_record.get('recorded_first_name', '')} {selected_record.get('recorded_last_name', '')}".strip()
        
        student_fields = [
            ("Name", student_name),
            ("Registration No", student_reg_no),  # Using regNo instead of student_id
            ("Condition ID", f"MC-{selected_record['id']:06d}"),
            ("Status", "Active" if selected_record['is_active'] else "Inactive"),
            ("Diagnosis Date", selected_record.get('diagnosis_date', 'N/A')),
            ("Severity", selected_record.get('severity', 'N/A')),
            ("Recorded By", recorded_by or "System"),
            ("Last Updated", selected_record.get('updated_at', 'N/A'))
        ]
        
        pdf.add_info_box("STUDENT INFORMATION", student_fields, pdf.get_y(), 35)  # Reduced height
        pdf.ln(4)  # Added extra space to push content down
        
        # Condition details
        pdf.add_section_header("CONDITION DETAILS")
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"Condition: {selected_record.get('condition_name', 'N/A')}", 0, 1, "L")
        pdf.ln(2)
        
        # Treatment plan
        if selected_record.get('treatment_plan'):
            pdf.add_section_header("TREATMENT PLAN")
            pdf.add_multiline_content(selected_record['treatment_plan'])
            pdf.ln(2)
        
        # Special requirements
        if selected_record.get('special_requirements'):
            pdf.add_section_header("SPECIAL REQUIREMENTS & ACCOMMODATIONS")
            pdf.add_multiline_content(selected_record['special_requirements'])
            pdf.ln(2)
        
        # Emergency procedures
        if selected_record['severity'] == 'Severe':
            pdf.add_section_header("EMERGENCY PROCEDURES", (180, 100, 100))
            pdf.set_font("Arial", "B", 9)
            pdf.cell(0, 5, "In case of emergency:", 0, 1, "L")
            pdf.set_font("Arial", "", 9)
            pdf.cell(0, 5, "1. Administer prescribed emergency medication if available", 0, 1, "L")
            pdf.cell(0, 5, "2. Contact emergency services immediately", 0, 1, "L")
            pdf.cell(0, 5, "3. Notify parents/guardians", 0, 1, "L")
            pdf.cell(0, 5, "4. Follow specific instructions from healthcare provider", 0, 1, "L")
            pdf.ln(2)
        
        # Additional notes section
        pdf.add_section_header("ADDITIONAL NOTES")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, "This condition requires ongoing monitoring and management.", 0, 1, "L")
        if selected_record['is_active']:
            pdf.cell(0, 5, "All staff should be aware of this condition and its management requirements.", 0, 1, "L")
        pdf.ln(10)
        
        # Signature section
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, 6, "School Nurse/Medical Officer:", 0, 0, "L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, "........................................................", 0, 1, "L")
        pdf.cell(60, 5, "Date:", 0, 0, "L")
        pdf.cell(0, 5, datetime.now().strftime("%Y-%m-%d"), 0, 1, "L")
        pdf.ln(3)
        
        # Generate PDF bytes
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

    def export_condition_pdf(self):
        """Export individual medical condition as PDF using enhanced viewer"""
        if not hasattr(self, 'selected_condition_id') or not self.selected_condition_id:
            QMessageBox.warning(self, "Warning", "Please select a medical condition first.")
            return
        
        try:
            # Find the selected record
            selected_record = None
            for record in self.medical_conditions_data:
                if record['id'] == self.selected_condition_id:
                    selected_record = record
                    break
            
            if not selected_record:
                QMessageBox.warning(self, "Error", "Selected condition not found.")
                return
            
            # Generate PDF bytes
            pdf_bytes = self.generate_medical_condition_pdf_bytes(selected_record)
            
            # Use your enhanced PDF viewer
            try:
                from utils.pdf_utils import view_pdf
                view_pdf(pdf_bytes, self)
            except ImportError as e:
                print(f"PDF viewer import error: {e}")
                # Fallback to file save
                self.save_condition_pdf_fallback(pdf_bytes, selected_record)
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate medical condition PDF: {str(e)}")
    
   
    def save_condition_pdf_fallback(self, pdf_bytes, selected_record):
        """Fallback method to save medical condition PDF if viewer not available"""
        patient_name = f"{selected_record.get('first_name', '')} {selected_record.get('surname', '')}".strip()
        condition_name = selected_record.get('condition_name', 'condition').replace(' ', '_')
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        default_filename = f"medical_condition_{safe_name}_{condition_name}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Medical Condition PDF", default_filename, "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(pdf_bytes)
                QMessageBox.information(self, "Success", f"PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF: {str(e)}")


class MedicalConditionDialog(QDialog):
    def __init__(self, parent=None, condition=None, students=None, teachers=None):
        super().__init__(parent)
        self.condition = condition
        self.students = students or []
        self.teachers = teachers or []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Edit Medical Condition" if self.condition else "Add New Medical Condition")
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
        
        # Condition information
        condition_group = QGroupBox("Condition Information")
        condition_layout = QFormLayout(condition_group)
        
        self.condition_name_edit = QLineEdit()
        self.condition_name_edit.setProperty("class", "form-control")
        self.condition_name_edit.setPlaceholderText("e.g., Asthma, Diabetes, Allergy")
        
        self.diagnosis_date_edit = QDateEdit()
        self.diagnosis_date_edit.setProperty("class", "form-control")
        self.diagnosis_date_edit.setDate(QDate.currentDate())
        self.diagnosis_date_edit.setCalendarPopup(True)
        
        self.severity_combo = QComboBox()
        self.severity_combo.setProperty("class", "form-control")
        self.severity_combo.addItems(["Mild", "Moderate", "Severe"])
        
        self.status_check = QCheckBox("Condition is currently active")
        self.status_check.setChecked(True)
        
        condition_layout.addRow("Condition Name *:", self.condition_name_edit)
        condition_layout.addRow("Diagnosis Date:", self.diagnosis_date_edit)
        condition_layout.addRow("Severity:", self.severity_combo)
        condition_layout.addRow("", self.status_check)
        
        form_layout.addWidget(condition_group)
        
        # Treatment and requirements
        treatment_group = QGroupBox("Treatment & Requirements")
        treatment_layout = QFormLayout(treatment_group)
        
        self.treatment_edit = QTextEdit()
        self.treatment_edit.setProperty("class", "form-control")
        self.treatment_edit.setMaximumHeight(80)
        self.treatment_edit.setPlaceholderText("Describe the treatment plan...")
        
        self.requirements_edit = QTextEdit()
        self.requirements_edit.setProperty("class", "form-control")
        self.requirements_edit.setMaximumHeight(80)
        self.requirements_edit.setPlaceholderText("Any special requirements or accommodations...")
        
        treatment_layout.addRow("Treatment Plan:", self.treatment_edit)
        treatment_layout.addRow("Special Requirements:", self.requirements_edit)
        
        form_layout.addWidget(treatment_group)
        
        # Recorded by
        recorded_group = QGroupBox("Recording Information")
        recorded_layout = QFormLayout(recorded_group)
        
        self.recorded_by_combo = QComboBox()
        self.recorded_by_combo.setProperty("class", "form-control")
        self.recorded_by_combo.addItem("Select Staff Member", None)
        for teacher in self.teachers:
            self.recorded_by_combo.addItem(f"{teacher['first_name']} {teacher['surname']}", teacher['id'])
        
        recorded_layout.addRow("Recorded By *:", self.recorded_by_combo)
        form_layout.addWidget(recorded_group)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Pre-fill data if editing
        if self.condition:
            self.prefill_data()
        
        # Button box
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Condition")
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
        if self.condition['student_id']:
            index = self.student_combo.findData(self.condition['student_id'])
            if index >= 0:
                self.student_combo.setCurrentIndex(index)
        
        self.condition_name_edit.setText(self.condition['condition_name'] or "")
        
        if self.condition['diagnosis_date']:
            self.diagnosis_date_edit.setDate(QDate.fromString(str(self.condition['diagnosis_date']), "yyyy-MM-dd"))
        
        if self.condition['severity']:
            self.severity_combo.setCurrentText(self.condition['severity'])
        
        if self.condition['is_active'] is not None:
            self.status_check.setChecked(bool(self.condition['is_active']))
        
        self.treatment_edit.setText(self.condition['treatment_plan'] or "")
        self.requirements_edit.setText(self.condition['special_requirements'] or "")
        
        if self.condition['recorded_by_teacher_id']:
            index = self.recorded_by_combo.findData(self.condition['recorded_by_teacher_id'])
            if index >= 0:
                self.recorded_by_combo.setCurrentIndex(index)
        
    def get_condition_data(self):
        """Get the medical condition data from the form"""
        return {
            'student_id': self.student_combo.currentData(),
            'condition_name': self.condition_name_edit.text().strip(),
            'diagnosis_date': self.diagnosis_date_edit.date().toString("yyyy-MM-dd"),
            'severity': self.severity_combo.currentText(),
            'treatment_plan': self.treatment_edit.toPlainText(),
            'special_requirements': self.requirements_edit.toPlainText(),
            'is_active': self.status_check.isChecked(),
            'recorded_by_teacher_id': self.recorded_by_combo.currentData()
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        # Basic validation
        if not self.student_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a student.")
            return
            
        if not self.condition_name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a condition name.")
            return
            
        if not self.recorded_by_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select who is recording this condition.")
            return
            
        super().accept()