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
        """Export medical conditions to Excel"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Medical Conditions Excel", "", "Excel Files (*.xlsx)"
            )
            
            if file_path:
                df_data = []
                for record in self.medical_conditions_data:
                    df_data.append({
                        'ID': record['id'],
                        'Student': f"{record['first_name']} {record['surname']}",
                        'Condition': record['condition_name'],
                        'Diagnosis Date': record['diagnosis_date'],
                        'Severity': record['severity'],
                        'Status': 'Active' if record['is_active'] else 'Inactive',
                        'Treatment Plan': record['treatment_plan'],
                        'Special Requirements': record['special_requirements'],
                        'Recorded By': f"{record.get('recorded_first_name', '')} {record.get('recorded_last_name', '')}",
                        'Last Updated': record['updated_at']
                    })
                
                df = pd.DataFrame(df_data)
                
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Medical Conditions', index=False)
                    
                    worksheet = writer.sheets['Medical Conditions']
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
                
                QMessageBox.information(self, "Success", f"Medical conditions exported to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export medical conditions: {e}")

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
    
    def generate_medical_condition_pdf_bytes(self, selected_record):
        """Generate medical condition PDF bytes for the enhanced viewer"""
        from fpdf import FPDF
        import tempfile
        
        class MedicalConditionPDF(FPDF):
            def __init__(self):
                super().__init__()
                self.set_auto_page_break(auto=True, margin=15)
            
            def header(self):
                self.set_font("Arial", "B", 16)
                self.cell(0, 10, "MEDICAL CONDITION REPORT", 0, 1, "C")
                self.ln(5)
            
            def footer(self):
                self.set_y(-15)
                self.set_font("Arial", "I", 8)
                self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")
        
        pdf = MedicalConditionPDF()
        pdf.add_page()
        
        # Patient information
        patient_name = f"{selected_record.get('first_name', '')} {selected_record.get('surname', '')}".strip()
        
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "PATIENT INFORMATION", 0, 1)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 8, f"Name: {patient_name}", 0, 1)
        pdf.cell(0, 8, f"Condition ID: MC-{selected_record['id']:06d}", 0, 1)
        
        # Condition details
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "CONDITION DETAILS:", 0, 1)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Condition: {selected_record.get('condition_name', 'N/A')}", 0, 1)
        pdf.cell(0, 6, f"Diagnosis Date: {selected_record.get('diagnosis_date', 'N/A')}", 0, 1)
        pdf.cell(0, 6, f"Severity: {selected_record.get('severity', 'N/A')}", 0, 1)
        
        status = "[X] ACTIVE" if selected_record.get('is_active') else "[ ] INACTIVE"
        pdf.cell(0, 6, f"Status: {status}", 0, 1)
        
        # Treatment plan
        if selected_record.get('treatment_plan'):
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "TREATMENT PLAN:", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, selected_record['treatment_plan'])
        
        # Special requirements
        if selected_record.get('special_requirements'):
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "SPECIAL REQUIREMENTS:", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, selected_record['special_requirements'])
        
        # Recorded by
        recorded_by = f"{selected_record.get('recorded_first_name', '')} {selected_record.get('recorded_last_name', '')}".strip()
        if recorded_by:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "RECORDING INFORMATION:", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"Recorded By: {recorded_by}", 0, 1)
            pdf.cell(0, 6, f"Last Updated: {selected_record.get('updated_at', 'N/A')}", 0, 1)
        
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