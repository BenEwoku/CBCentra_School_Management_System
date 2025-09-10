# ui/medication_inventory_form.py
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

class MedicationInventoryForm(AuditBaseForm):
    def __init__(self, parent=None, db_connection=None, cursor=None, user_session=None):
        super().__init__(parent, user_session)
        
        # Use provided connection or create new one
        if db_connection:
            self.db_connection = db_connection
            self.cursor = cursor
        else:
            try:
                self.db_connection = get_db_connection()
                self.cursor = self.db_connection.cursor(buffered=True, dictionary=True)
            except Error as e:
                print(f"DEBUG: Database connection failed: {e}")
                QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
                return
        
        self.selected_medication_id = None
        self.medication_data = []
        self.filtered_data = []
        self.teachers_data = []
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        # Create main widget for this form
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Medication Inventory Management")
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
        self.search_entry.setPlaceholderText("Search by medication name, type...")
        self.search_entry.textChanged.connect(self.search_medications)
        search_layout.addWidget(self.search_entry)
        
        status_label = QLabel("Stock Status:")
        status_label.setProperty("class", "field-label")
        search_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setProperty("class", "form-control")
        self.status_filter.addItems(["All", "Low Stock", "Adequate Stock", "Expired", "Expiring Soon"])
        self.status_filter.currentTextChanged.connect(self.filter_by_status)
        search_layout.addWidget(self.status_filter)
        
        type_label = QLabel("Medication Type:")
        type_label.setProperty("class", "field-label")
        search_layout.addWidget(type_label)
        
        self.type_filter = QComboBox()
        self.type_filter.setProperty("class", "form-control")
        self.type_filter.addItems(["All", "Tablet", "Syrup", "Injection", "Ointment", "Drops", "Inhaler"])
        self.type_filter.currentTextChanged.connect(self.filter_by_type)
        search_layout.addWidget(self.type_filter)
        
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
        
        add_btn = QPushButton("New Medication")
        add_btn.setProperty("class", "success")
        add_btn.setIcon(QIcon("static/icons/add.png"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_medication)
        action_buttons_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Medication")
        edit_btn.setProperty("class", "primary")
        edit_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.clicked.connect(self.edit_medication)
        action_buttons_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Medication")
        delete_btn.setProperty("class", "danger")
        delete_btn.setIcon(QIcon("static/icons/delete.png"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.clicked.connect(self.delete_medication)
        action_buttons_layout.addWidget(delete_btn)
        
        restock_btn = QPushButton("Restock")
        restock_btn.setProperty("class", "info")
        restock_btn.setIcon(QIcon("static/icons/restock.png"))
        restock_btn.setIconSize(QSize(16, 16))
        restock_btn.clicked.connect(self.restock_medication)
        action_buttons_layout.addWidget(restock_btn)
        
        export_excel_btn = QPushButton("Export Excel")
        export_excel_btn.setProperty("class", "info")
        export_excel_btn.setIcon(QIcon("static/icons/excel.png"))
        export_excel_btn.setIconSize(QSize(16, 16))
        export_excel_btn.clicked.connect(self.export_medications_excel)
        action_buttons_layout.addWidget(export_excel_btn)
        
        export_pdf_btn = QPushButton("Export PDF")
        export_pdf_btn.setProperty("class", "warning")
        export_pdf_btn.setIcon(QIcon("static/icons/pdf.png"))
        export_pdf_btn.setIconSize(QSize(16, 16))
        export_pdf_btn.clicked.connect(self.export_medication_pdf)
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
        
        self.total_medications_label = QLabel("Total: 0")
        self.total_medications_label.setProperty("class", "stat-label")
        self.total_medications_label.setAlignment(Qt.AlignCenter)
        self.total_medications_label.setMinimumWidth(80)
        stats_layout.addWidget(self.total_medications_label)
        
        self.low_stock_label = QLabel("Low Stock: 0")
        self.low_stock_label.setProperty("class", "stat-label")
        self.low_stock_label.setAlignment(Qt.AlignCenter)
        self.low_stock_label.setMinimumWidth(80)
        stats_layout.addWidget(self.low_stock_label)
        
        self.expired_label = QLabel("Expired: 0")
        self.expired_label.setProperty("class", "stat-label")
        self.expired_label.setAlignment(Qt.AlignCenter)
        self.expired_label.setMinimumWidth(80)
        stats_layout.addWidget(self.expired_label)
        
        # Combine both sides
        action_stats_layout.addLayout(action_buttons_layout, 70)  # 70% width for buttons
        action_stats_layout.addLayout(stats_layout, 30)  # 30% width for stats
        
        layout.addLayout(action_stats_layout)
        
        # Medication inventory table
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Generic Name", "Type", "Strength", "Quantity", 
            "Unit", "Min Stock", "Supplier", "Batch No", "Expiry Date", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self.on_row_click)
        self.table.setAlternatingRowColors(True)
        self.table.setProperty("class", "data-table")
        
        layout.addWidget(self.table)
        
        # Status info
        self.info_label = QLabel("Select a medication to manage")
        self.info_label.setProperty("class", "info-label")
        layout.addWidget(self.info_label)
        
        # Set the main widget
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(main_widget)
    
    def load_data(self):
        """Load medication inventory data"""
        try:
            # Load teachers for dropdowns
            self.cursor.execute("SELECT id, first_name, surname FROM teachers WHERE is_active = TRUE ORDER BY first_name")
            self.teachers_data = self.cursor.fetchall()
            
            # Load medication inventory
            self.cursor.execute("""
                SELECT mi.*, 
                       t.first_name as managed_first_name,
                       t.surname as managed_last_name
                FROM medication_inventory mi
                LEFT JOIN teachers t ON mi.managed_by_teacher_id = t.id
                ORDER BY mi.name, mi.expiration_date
            """)
            self.medication_data = self.cursor.fetchall()
            self.filtered_data = self.medication_data.copy()
            
            self.update_stats()
            self.update_table()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load medication inventory: {e}")
    
    def update_stats(self):
        """Update statistics labels"""
        total_medications = len(self.medication_data)
        low_stock = sum(1 for record in self.medication_data 
                       if record['quantity'] <= record.get('minimum_stock_level', 10))
        
        today = datetime.now().date()
        expired = sum(1 for record in self.medication_data 
                     if record['expiration_date'] and record['expiration_date'] < today)
        
        self.total_medications_label.setText(f"Total: {total_medications}")
        self.low_stock_label.setText(f"Low Stock: {low_stock}")
        self.expired_label.setText(f"Expired: {expired}")
    
    def update_table(self):
        """Update the medication table with current data"""
        self.table.setRowCount(0)
        today = datetime.now().date()
        
        for row, record in enumerate(self.filtered_data):
            self.table.insertRow(row)
            
            # Determine status and color
            status = "Adequate"
            color = QColor(230, 255, 230)  # Light green
            
            if record['quantity'] <= record.get('minimum_stock_level', 10):
                status = "Low Stock"
                color = QColor(255, 230, 230)  # Light red
            
            if record['expiration_date']:
                if record['expiration_date'] < today:
                    status = "Expired"
                    color = QColor(255, 200, 200)  # Darker red
                elif (record['expiration_date'] - today).days <= 30:
                    status = "Expiring Soon"
                    color = QColor(255, 245, 230)  # Light orange
            
            # Add items to table
            self.table.setItem(row, 0, QTableWidgetItem(str(record['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(record['name']))
            self.table.setItem(row, 2, QTableWidgetItem(record.get('generic_name', '')))
            self.table.setItem(row, 3, QTableWidgetItem(record.get('medication_type', '')))
            self.table.setItem(row, 4, QTableWidgetItem(record.get('strength', '')))
            self.table.setItem(row, 5, QTableWidgetItem(str(record['quantity'])))
            self.table.setItem(row, 6, QTableWidgetItem(record.get('unit', '')))
            self.table.setItem(row, 7, QTableWidgetItem(str(record.get('minimum_stock_level', 10))))
            self.table.setItem(row, 8, QTableWidgetItem(record.get('supplier', '')))
            self.table.setItem(row, 9, QTableWidgetItem(record.get('batch_number', '')))
            self.table.setItem(row, 10, QTableWidgetItem(str(record.get('expiration_date', ''))))
            self.table.setItem(row, 11, QTableWidgetItem(status))
            
            # Color code based on status
            for col in range(self.table.columnCount()):
                self.table.item(row, col).setBackground(color)
        
        self.info_label.setText(f"Showing {len(self.filtered_data)} of {len(self.medication_data)} medications")
    
    def search_medications(self):
        """Search medications based on search text"""
        search_text = self.search_entry.text().lower().strip()
        
        if not search_text:
            self.filtered_data = self.medication_data.copy()
        else:
            self.filtered_data = [
                record for record in self.medication_data
                if (search_text in (record['name'] or '').lower() or 
                    search_text in (record.get('generic_name', '') or '').lower() or 
                    search_text in (record.get('supplier', '') or '').lower() or
                    search_text in (record.get('batch_number', '') or '').lower())
            ]
            
        self.update_table()
    
    def filter_by_status(self):
        """Filter medications by stock status"""
        status = self.status_filter.currentText()
        today = datetime.now().date()
        
        if status == "All":
            self.filtered_data = self.medication_data.copy()
        elif status == "Low Stock":
            self.filtered_data = [record for record in self.medication_data 
                                if record['quantity'] <= record.get('minimum_stock_level', 10)]
        elif status == "Adequate Stock":
            self.filtered_data = [record for record in self.medication_data 
                                if record['quantity'] > record.get('minimum_stock_level', 10)]
        elif status == "Expired":
            self.filtered_data = [record for record in self.medication_data 
                                if record['expiration_date'] and record['expiration_date'] < today]
        elif status == "Expiring Soon":
            self.filtered_data = [record for record in self.medication_data 
                                if record['expiration_date'] and 
                                (record['expiration_date'] - today).days <= 30 and
                                record['expiration_date'] >= today]
            
        self.update_table()
    
    def filter_by_type(self):
        """Filter medications by type"""
        med_type = self.type_filter.currentText()
        
        if med_type == "All":
            self.filtered_data = self.medication_data.copy()
        else:
            self.filtered_data = [record for record in self.medication_data 
                                if record.get('medication_type') == med_type]
            
        self.update_table()
    
    def clear_filters(self):
        """Clear all filters"""
        self.search_entry.clear()
        self.status_filter.setCurrentIndex(0)
        self.type_filter.setCurrentIndex(0)
        self.filtered_data = self.medication_data.copy()
        self.update_table()
    
    def on_row_click(self, row, column):
        """Handle medication row selection"""
        if row < 0 or row >= len(self.filtered_data):
            return
            
        record_id = self.table.item(row, 0).text()
        self.selected_medication_id = int(record_id)
        
        medication_name = self.table.item(row, 1).text()
        self.info_label.setText(f"Selected: {medication_name}")
        
        # Enable PDF export button
        self.export_pdf_btn.setEnabled(True)
    
    def add_medication(self):
        """Open dialog to add a new medication"""
        dialog = MedicationDialog(self, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            medication_data = dialog.get_medication_data()
            self.save_medication(medication_data)
    
    def edit_medication(self):
        """Open dialog to edit selected medication"""
        if not hasattr(self, 'selected_medication_id') or not self.selected_medication_id:
            QMessageBox.warning(self, "Warning", "Please select a medication to edit.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.medication_data:
            if record['id'] == self.selected_medication_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected medication not found.")
            return
            
        dialog = MedicationDialog(self, medication=selected_record, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            medication_data = dialog.get_medication_data()
            self.update_medication(self.selected_medication_id, medication_data)
    
    def delete_medication(self):
        """Delete selected medication"""
        if not hasattr(self, 'selected_medication_id') or not self.selected_medication_id:
            QMessageBox.warning(self, "Warning", "Please select a medication to delete.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.medication_data:
            if record['id'] == self.selected_medication_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected medication not found.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {selected_record['name']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM medication_inventory WHERE id = %s", (self.selected_medication_id,))
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Medication deleted successfully!")
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete medication: {e}")
    
    def restock_medication(self):
        """Restock selected medication"""
        if not hasattr(self, 'selected_medication_id') or not self.selected_medication_id:
            QMessageBox.warning(self, "Warning", "Please select a medication to restock.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.medication_data:
            if record['id'] == self.selected_medication_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected medication not found.")
            return
            
        dialog = RestockDialog(self, medication=selected_record)
        if dialog.exec() == QDialog.Accepted:
            quantity_to_add = dialog.get_quantity()
            try:
                self.cursor.execute(
                    "UPDATE medication_inventory SET quantity = quantity + %s WHERE id = %s",
                    (quantity_to_add, self.selected_medication_id)
                )
                self.db_connection.commit()
                QMessageBox.information(self, "Success", f"Added {quantity_to_add} units to {selected_record['name']}!")
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to restock medication: {e}")
    
    def refresh_data(self):
        """Refresh medication data"""
        self.load_data()
        QMessageBox.information(self, "Success", "Medication data refreshed!")
    
    def save_medication(self, medication_data):
        """Save new medication to database"""
        try:
            query = """
                INSERT INTO medication_inventory 
                (name, generic_name, medication_type, strength, quantity, unit, 
                 minimum_stock_level, supplier, batch_number, expiration_date, 
                 storage_conditions, is_controlled, notes, managed_by_teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                medication_data['name'],
                medication_data['generic_name'],
                medication_data['medication_type'],
                medication_data['strength'],
                medication_data['quantity'],
                medication_data['unit'],
                medication_data['minimum_stock_level'],
                medication_data['supplier'],
                medication_data['batch_number'],
                medication_data['expiration_date'],
                medication_data['storage_conditions'],
                medication_data['is_controlled'],
                medication_data['notes'],
                medication_data['managed_by_teacher_id']
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Medication added successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add medication: {e}")
    
    def update_medication(self, medication_id, medication_data):
        """Update existing medication in database"""
        try:
            query = """
                UPDATE medication_inventory 
                SET name = %s, generic_name = %s, medication_type = %s, strength = %s, 
                    quantity = %s, unit = %s, minimum_stock_level = %s, supplier = %s, 
                    batch_number = %s, expiration_date = %s, storage_conditions = %s, 
                    is_controlled = %s, notes = %s, managed_by_teacher_id = %s
                WHERE id = %s
            """
            values = (
                medication_data['name'],
                medication_data['generic_name'],
                medication_data['medication_type'],
                medication_data['strength'],
                medication_data['quantity'],
                medication_data['unit'],
                medication_data['minimum_stock_level'],
                medication_data['supplier'],
                medication_data['batch_number'],
                medication_data['expiration_date'],
                medication_data['storage_conditions'],
                medication_data['is_controlled'],
                medication_data['notes'],
                medication_data['managed_by_teacher_id'],
                medication_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Medication updated successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update medication: {e}")
    
    def export_medications_excel(self):
        """Export medication inventory with the green header style"""
        try:
            # Get school info for the title
            school_info = self.get_school_info()
            
            # Prepare data for export - convert to list of lists
            export_data = []
            for record in self.medication_data:
                row_data = [
                    record['id'],
                    record['name'],
                    record.get('generic_name', ''),
                    record.get('medication_type', ''),
                    record.get('strength', ''),
                    record['quantity'],
                    record.get('unit', ''),
                    record.get('minimum_stock_level', 10),
                    record.get('supplier', ''),
                    record.get('batch_number', ''),
                    record.get('expiration_date', ''),
                    record.get('storage_conditions', ''),
                    'Yes' if record.get('is_controlled') else 'No',
                    f"{record.get('managed_first_name', '')} {record.get('managed_last_name', '')}",
                    record['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if record['updated_at'] else 'N/A'
                ]
                export_data.append(row_data)
    
            # Define headers
            headers = [
                'ID', 'Name', 'Generic Name', 'Type', 'Strength', 'Quantity', 
                'Unit', 'Min Stock Level', 'Supplier', 'Batch Number', 
                'Expiration Date', 'Storage Conditions', 'Controlled Substance', 
                'Managed By', 'Last Updated'
            ]
            
            # Create title
            title = f"{school_info['name']} - MEDICATION INVENTORY"
            
            # Use shared export method
            self.export_with_green_header(
                data=export_data,
                headers=headers,
                filename_prefix="medication_inventory_export",
                title=title
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export medication inventory: {e}")
    
    def export_medication_pdf(self):
        """Export individual medication as PDF"""
        if not hasattr(self, 'selected_medication_id') or not self.selected_medication_id:
            QMessageBox.warning(self, "Selection Required", "Please select a medication first by clicking on a row in the table.")
            return
        
        try:
            # Find the selected record
            selected_record = None
            for record in self.medication_data:
                if record['id'] == self.selected_medication_id:
                    selected_record = record
                    break
            
            if not selected_record:
                QMessageBox.warning(self, "Error", "Selected medication not found.")
                return
            
            # Generate PDF bytes
            pdf_bytes = self.generate_medication_pdf_bytes(selected_record)
            
            # Use enhanced PDF viewer
            try:
                from utils.pdf_utils import view_pdf
                view_pdf(pdf_bytes, self)
            except ImportError as e:
                print(f"PDF viewer import error: {e}")
                # Fallback to file save
                self.save_medication_pdf_fallback(pdf_bytes, selected_record)
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate medication PDF: {str(e)}")
    
    def generate_medication_pdf_bytes(self, selected_record):
        """Generate professional medication PDF with school branding"""
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
        
        class MedicationPDF(FPDF):
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
                self.cell(0, 8, "MEDICATION INFORMATION", 0, 1, "C")
                
                self.set_font("Arial", "", 8)
                self.set_text_color(100, 100, 100)
                doc_id = f"Document ID: MED-{selected_record['id']:06d}"
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
        
        # Create PDF
        pdf = MedicationPDF()
        pdf.add_page()
        
        # Medication information
        managed_by = f"{selected_record.get('managed_first_name', '')} {selected_record.get('managed_last_name', '')}".strip()
        
        # Determine status
        today = datetime.now().date()
        status = "Adequate"
        if selected_record['quantity'] <= selected_record.get('minimum_stock_level', 10):
            status = "Low Stock"
        if selected_record['expiration_date']:
            if selected_record['expiration_date'] < today:
                status = "Expired"
            elif (selected_record['expiration_date'] - today).days <= 30:
                status = "Expiring Soon"
        
        medication_fields = [
            ("Name", selected_record['name']),
            ("Generic Name", selected_record.get('generic_name', 'N/A')),
            ("Type", selected_record.get('medication_type', 'N/A')),
            ("Strength", selected_record.get('strength', 'N/A')),
            ("Quantity", f"{selected_record['quantity']} {selected_record.get('unit', 'units')}"),
            ("Min Stock Level", selected_record.get('minimum_stock_level', 10)),
            ("Batch Number", selected_record.get('batch_number', 'N/A')),
            ("Expiration Date", selected_record.get('expiration_date', 'N/A')),
            ("Supplier", selected_record.get('supplier', 'N/A')),
            ("Status", status),
            ("Controlled", "Yes" if selected_record.get('is_controlled') else "No"),
            ("Managed By", managed_by or "Not specified")
        ]
        
        pdf.add_info_box("MEDICATION DETAILS", medication_fields, pdf.get_y(), 50)
        pdf.ln(8)
        
        # Storage conditions
        if selected_record.get('storage_conditions'):
            pdf.add_section_header("STORAGE CONDITIONS")
            pdf.add_multiline_content(selected_record['storage_conditions'])
            pdf.ln(8)
        
        # Notes
        if selected_record.get('notes'):
            pdf.add_section_header("ADDITIONAL NOTES")
            pdf.add_multiline_content(selected_record['notes'])
            pdf.ln(2)
        
        # Warning if low stock or expired
        if status == "Low Stock":
            pdf.add_section_header("STOCK ALERT", (255, 100, 100))
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "This medication is running low. Please reorder soon.", 0, 1, "L")
            pdf.ln(2)
        
        if status == "Expired":
            pdf.add_section_header("EXPIRATION ALERT", (255, 100, 100))
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "This medication has expired. Do not administer.", 0, 1, "L")
            pdf.ln(2)
        
        elif status == "Expiring Soon":
            pdf.add_section_header("EXPIRATION ALERT", (255, 200, 100))
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "This medication will expire soon. Check before use.", 0, 1, "L")
            pdf.ln(2)
        
        # Signature section
        pdf.ln(10)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(60, 6, "Nurse/Medic/Inventory Manager:", 0, 0, "L")
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

    def save_medication_pdf_fallback(self, pdf_bytes, selected_record):
        """Fallback method to save medication PDF if viewer not available"""
        medication_name = selected_record['name'].replace(' ', '_')
        default_filename = f"medication_{medication_name}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Medication PDF", default_filename, "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(pdf_bytes)
                QMessageBox.information(self, "Success", f"PDF saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF: {str(e)}")


class MedicationDialog(QDialog):
    def __init__(self, parent=None, medication=None, teachers=None):
        super().__init__(parent)
        self.medication = medication
        self.teachers = teachers or []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Edit Medication" if self.medication else "Add New Medication")
        self.setMinimumSize(650, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)
        
        # Basic information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setProperty("class", "form-control")
        self.name_edit.setPlaceholderText("e.g., Paracetamol, Amoxicillin")
        
        self.generic_edit = QLineEdit()
        self.generic_edit.setProperty("class", "form-control")
        self.generic_edit.setPlaceholderText("Generic name if different")
        
        self.type_combo = QComboBox()
        self.type_combo.setProperty("class", "form-control")
        self.type_combo.addItems(["Tablet", "Syrup", "Injection", "Ointment", "Drops", "Inhaler"])
        
        self.strength_edit = QLineEdit()
        self.strength_edit.setProperty("class", "form-control")
        self.strength_edit.setPlaceholderText("e.g., 500mg, 5mg/ml")
        
        basic_layout.addRow("Medication Name *:", self.name_edit)
        basic_layout.addRow("Generic Name:", self.generic_edit)
        basic_layout.addRow("Type *:", self.type_combo)
        basic_layout.addRow("Strength:", self.strength_edit)
        
        form_layout.addWidget(basic_group)
        
        # Stock information
        stock_group = QGroupBox("Stock Information")
        stock_layout = QFormLayout(stock_group)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setProperty("class", "form-control")
        self.quantity_spin.setRange(0, 10000)
        self.quantity_spin.setValue(0)
        
        self.unit_combo = QComboBox()
        self.unit_combo.setProperty("class", "form-control")
        self.unit_combo.addItems(["Tablets", "Bottles", "Tubes", "Ampoules", "Packs"])
        
        self.min_stock_spin = QSpinBox()
        self.min_stock_spin.setProperty("class", "form-control")
        self.min_stock_spin.setRange(1, 1000)
        self.min_stock_spin.setValue(10)
        
        stock_layout.addRow("Quantity *:", self.quantity_spin)
        stock_layout.addRow("Unit *:", self.unit_combo)
        stock_layout.addRow("Minimum Stock Level *:", self.min_stock_spin)
        
        form_layout.addWidget(stock_group)
        
        # Supplier information
        supplier_group = QGroupBox("Supplier Information")
        supplier_layout = QFormLayout(supplier_group)
        
        self.supplier_edit = QLineEdit()
        self.supplier_edit.setProperty("class", "form-control")
        self.supplier_edit.setPlaceholderText("Supplier company name")
        
        self.batch_edit = QLineEdit()
        self.batch_edit.setProperty("class", "form-control")
        self.batch_edit.setPlaceholderText("Batch or lot number")
        
        self.expiry_date_edit = QDateEdit()
        self.expiry_date_edit.setProperty("class", "form-control")
        self.expiry_date_edit.setDate(QDate.currentDate().addYears(1))
        self.expiry_date_edit.setCalendarPopup(True)
        
        supplier_layout.addRow("Supplier:", self.supplier_edit)
        supplier_layout.addRow("Batch Number:", self.batch_edit)
        supplier_layout.addRow("Expiration Date:", self.expiry_date_edit)
        
        form_layout.addWidget(supplier_group)
        
        # Additional information
        additional_group = QGroupBox("Additional Information")
        additional_layout = QFormLayout(additional_group)
        
        self.storage_edit = QLineEdit()
        self.storage_edit.setProperty("class", "form-control")
        self.storage_edit.setPlaceholderText("e.g., Room temperature, Refrigerate")
        
        self.controlled_check = QCheckBox("Controlled substance (requires special handling)")
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setProperty("class", "form-control")
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Additional notes or instructions...")
        
        self.manager_combo = QComboBox()
        self.manager_combo.setProperty("class", "form-control")
        self.manager_combo.addItem("Select Manager", None)
        for teacher in self.teachers:
            self.manager_combo.addItem(f"{teacher['first_name']} {teacher['surname']}", teacher['id'])
        
        additional_layout.addRow("Storage Conditions:", self.storage_edit)
        additional_layout.addRow("", self.controlled_check)
        additional_layout.addRow("Notes:", self.notes_edit)
        additional_layout.addRow("Managed By *:", self.manager_combo)
        
        form_layout.addWidget(additional_group)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Pre-fill data if editing
        if self.medication:
            self.prefill_data()
        
        # Button box
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Medication")
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
        self.name_edit.setText(self.medication['name'] or "")
        self.generic_edit.setText(self.medication.get('generic_name', ""))
        
        if self.medication.get('medication_type'):
            index = self.type_combo.findText(self.medication['medication_type'])
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        
        self.strength_edit.setText(self.medication.get('strength', ""))
        self.quantity_spin.setValue(self.medication['quantity'] or 0)
        
        if self.medication.get('unit'):
            index = self.unit_combo.findText(self.medication['unit'])
            if index >= 0:
                self.unit_combo.setCurrentIndex(index)
        
        self.min_stock_spin.setValue(self.medication.get('minimum_stock_level', 10))
        self.supplier_edit.setText(self.medication.get('supplier', ""))
        self.batch_edit.setText(self.medication.get('batch_number', ""))
        
        if self.medication.get('expiration_date'):
            self.expiry_date_edit.setDate(QDate.fromString(str(self.medication['expiration_date']), "yyyy-MM-dd"))
        
        self.storage_edit.setText(self.medication.get('storage_conditions', ""))
        
        if self.medication.get('is_controlled'):
            self.controlled_check.setChecked(bool(self.medication['is_controlled']))
        
        self.notes_edit.setText(self.medication.get('notes', ""))
        
        if self.medication.get('managed_by_teacher_id'):
            index = self.manager_combo.findData(self.medication['managed_by_teacher_id'])
            if index >= 0:
                self.manager_combo.setCurrentIndex(index)
        
    def get_medication_data(self):
        """Get the medication data from the form"""
        return {
            'name': self.name_edit.text().strip(),
            'generic_name': self.generic_edit.text().strip() or None,
            'medication_type': self.type_combo.currentText(),
            'strength': self.strength_edit.text().strip() or None,
            'quantity': self.quantity_spin.value(),
            'unit': self.unit_combo.currentText(),
            'minimum_stock_level': self.min_stock_spin.value(),
            'supplier': self.supplier_edit.text().strip() or None,
            'batch_number': self.batch_edit.text().strip() or None,
            'expiration_date': self.expiry_date_edit.date().toString("yyyy-MM-dd") if self.expiry_date_edit.date() > QDate.currentDate() else None,
            'storage_conditions': self.storage_edit.text().strip() or None,
            'is_controlled': self.controlled_check.isChecked(),
            'notes': self.notes_edit.toPlainText().strip() or None,
            'managed_by_teacher_id': self.manager_combo.currentData()
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        # Basic validation
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a medication name.")
            return
            
        if self.quantity_spin.value() < 0:
            QMessageBox.warning(self, "Validation Error", "Quantity cannot be negative.")
            return
            
        if not self.manager_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select who manages this medication.")
            return
            
        super().accept()


class RestockDialog(QDialog):
    def __init__(self, parent=None, medication=None):
        super().__init__(parent)
        self.medication = medication
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Restock {self.medication['name'] if self.medication else 'Medication'}")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Current stock info
        if self.medication:
            current_label = QLabel(f"Current stock: {self.medication['quantity']} {self.medication.get('unit', 'units')}")
            current_label.setProperty("class", "info-label")
            layout.addWidget(current_label)
            
            min_label = QLabel(f"Minimum stock level: {self.medication.get('minimum_stock_level', 10)}")
            min_label.setProperty("class", "info-label")
            layout.addWidget(min_label)
        
        # Quantity to add
        quantity_layout = QHBoxLayout()
        quantity_label = QLabel("Quantity to add:")
        quantity_label.setProperty("class", "field-label")
        quantity_layout.addWidget(quantity_label)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setProperty("class", "form-control")
        self.quantity_spin.setRange(1, 10000)
        self.quantity_spin.setValue(10)
        quantity_layout.addWidget(self.quantity_spin)
        
        layout.addLayout(quantity_layout)
        
        # Button box
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Stock")
        add_btn.setProperty("class", "success")
        add_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def get_quantity(self):
        """Get the quantity to add"""
        return self.quantity_spin.value()