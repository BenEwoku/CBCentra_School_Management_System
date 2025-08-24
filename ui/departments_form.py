# ui/departments_form.py
import sys
import os
import csv
from datetime import datetime
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QTabWidget, QGroupBox, QComboBox,
    QTextEdit, QCheckBox, QMenu, QGridLayout
)
from PySide6.QtGui import QFont, QPalette, QIcon, QAction
from PySide6.QtCore import Qt, Signal

from utils.permissions import has_permission
from ui.audit_base_form import AuditBaseForm
from models.models import get_db_connection
from utils.pdf_utils import view_pdf  # Assuming you have this from teachers_form
import csv
import openpyxl  # For Excel support
from openpyxl import load_workbook
from io import StringIO

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DepartmentsForm(AuditBaseForm):
    """
    Comprehensive Departments Management with:
    - Audit logging
    - CSV/PDF export
    - Teacher count
    - Inactive filter
    - Two-tab UI (Form + Data)
    """
    department_selected = Signal(int)

    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.user_session = user_session
        self.current_department_id = None
        self.schools_map = {}
        self.teachers_map = {}
        self.all_teachers = []

        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(dictionary=True)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return

        self.setup_ui()
        self.load_schools()
        self.load_teachers()
        self.apply_permissions()
        self.load_departments()

    def setup_ui(self):
        """Set up the tabbed UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.tab_widget = QTabWidget()
        self.department_form_tab = QWidget()
        self.department_data_tab = QWidget()

        self.tab_widget.addTab(self.department_form_tab, "Department Form")
        self.tab_widget.addTab(self.department_data_tab, "Departments Data")

        layout.addWidget(self.tab_widget)

        self.setup_department_form_tab()
        self.setup_department_data_tab()

    def setup_department_form_tab(self):
        """Form tab: Add/Edit Department"""
        layout = QVBoxLayout(self.department_form_tab)
        layout.setSpacing(10)

        title = QLabel("Department Management")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(title)

        form_group = QGroupBox("Department Details")
        form_layout = QGridLayout(form_group)

        # Department Name
        form_layout.addWidget(QLabel("Department Name:"), 0, 0)
        self.name_entry = QLineEdit()
        form_layout.addWidget(self.name_entry, 0, 1)

        # School
        form_layout.addWidget(QLabel("School:"), 0, 2)
        self.school_combo = QComboBox()
        self.school_combo.currentTextChanged.connect(self.on_school_selected)
        form_layout.addWidget(self.school_combo, 0, 3)

        # Head
        form_layout.addWidget(QLabel("Department Head:"), 1, 0)
        self.head_combo = QComboBox()
        self.head_combo.setEditable(True)
        self.head_combo.setPlaceholderText("Search teacher...")
        self.head_combo.editTextChanged.connect(self.on_head_search)
        form_layout.addWidget(self.head_combo, 1, 1)
        # Connect signals ONCE
        self.head_combo.editTextChanged.connect(self.on_head_search)
        self.head_combo.activated.connect(self.on_head_combo_activated)  # ← Critical!
        #self.head_combo.setCompleter(None)  # Disable default completer

        # Description
        form_layout.addWidget(QLabel("Description:"), 1, 2)
        self.description_box = QTextEdit()
        self.description_box.setMaximumHeight(60)
        form_layout.addWidget(self.description_box, 1, 3)

        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Department")
        self.add_btn.clicked.connect(self.add_department)
        btn_layout.addWidget(self.add_btn)

        self.update_btn = QPushButton("Update")
        self.update_btn.clicked.connect(self.update_department)
        btn_layout.addWidget(self.update_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_department)
        btn_layout.addWidget(self.delete_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_fields)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

    def setup_department_data_tab(self):
        """Data tab: View/Search Departments"""
        layout = QVBoxLayout(self.department_data_tab)
        layout.setSpacing(10)

        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QGridLayout(filter_group)

        filter_layout.addWidget(QLabel("Search:"), 0, 0)
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search by name...")
        self.search_entry.textChanged.connect(self.load_departments)
        filter_layout.addWidget(self.search_entry, 0, 1)

        self.active_filter = QCheckBox("Show Inactive Departments")
        self.active_filter.stateChanged.connect(self.load_departments)
        filter_layout.addWidget(self.active_filter, 0, 2)

        self.filter_btn = QPushButton("Filter")
        self.filter_btn.clicked.connect(self.load_departments)
        filter_layout.addWidget(self.filter_btn, 0, 3)

        layout.addWidget(filter_group)

        # Action Buttons
        action_layout = QHBoxLayout()
        self.export_csv_btn = QPushButton("Export to CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        action_layout.addWidget(self.export_csv_btn)

        self.export_pdf_btn = QPushButton("Export to PDF")
        self.export_pdf_btn.clicked.connect(self.export_to_pdf)
        action_layout.addWidget(self.export_pdf_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_departments)
        action_layout.addWidget(self.refresh_btn)

        layout.addLayout(action_layout)

        # Table
        table_group = QGroupBox("Departments List")
        table_layout = QVBoxLayout(table_group)

        self.departments_table = QTableWidget()
        self.departments_table.setColumnCount(8)
        self.departments_table.setHorizontalHeaderLabels([
            "ID", "School", "Department Name", "Head", "Teacher Count", "Description", "Created At", "Active"
        ])
        self.departments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.departments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.departments_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.departments_table.setSortingEnabled(True)
        self.departments_table.itemSelectionChanged.connect(self.on_department_select)
        self.departments_table.itemDoubleClicked.connect(self.edit_selected_department)

        table_layout.addWidget(self.departments_table)
        layout.addWidget(table_group)

    def on_school_selected(self):
        """Reload teachers when school changes"""
        self.load_teachers()
        self.head_combo.clearEditText()

    def load_schools(self):
        """Load schools into combo box"""
        try:
            self.cursor.execute("SELECT id, school_name FROM schools ORDER BY school_name")
            schools = self.cursor.fetchall()
            self.schools_map = {row['school_name']: row['id'] for row in schools}
            self.school_combo.clear()
            self.school_combo.addItem("All Schools", None)
            for name in self.schools_map.keys():
                self.school_combo.addItem(name, self.schools_map[name])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load schools: {e}")

    def load_teachers(self):
        """Load teachers based on selected school"""
        try:
            school_id = self.school_combo.currentData()
            query = "SELECT id, full_name FROM teachers WHERE is_active = 1"
            params = []

            if school_id:
                query += " AND school_id = %s"
                params.append(school_id)

            query += " ORDER BY full_name"
            self.cursor.execute(query, params)
            teachers = self.cursor.fetchall()

            self.teachers_map = {t['full_name']: t['id'] for t in teachers}
            self.all_teachers = [t['full_name'] for t in teachers]

            self.head_combo.clear()
            self.head_combo.addItems(self.all_teachers)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load teachers: {e}")

    def on_head_search(self, text):
        """Filter head combo based on search text"""
        self.head_combo.clear()
        filtered = [t for t in self.all_teachers if text.lower() in t.lower()]
        
        if filtered:
            self.head_combo.addItems(filtered)
        else:
            # Show all if no match
            self.head_combo.addItems(self.all_teachers)
        
        # Reconnect after clear to avoid signal issues
        self.head_combo.activated.connect(self.on_head_combo_activated)

    def load_departments(self):
        """Load departments with filters"""
        try:
            search_term = self.search_entry.text().strip()
            show_inactive = self.active_filter.isChecked()

            query = """
                SELECT 
                    d.id, s.school_name, d.department_name, COALESCE(t.full_name, 'N/A') as head_name,
                    d.description, d.created_at, d.is_active,
                    (SELECT COUNT(*) FROM teachers t WHERE t.department_id = d.id AND t.is_active = 1) as teacher_count
                FROM departments d
                LEFT JOIN schools s ON d.school_id = s.id
                LEFT JOIN teachers t ON d.department_head_id = t.id
            """
            params = []

            if not show_inactive:
                query += " WHERE d.is_active = 1"
            else:
                query += " WHERE 1=1"

            if search_term:
                query += " AND LOWER(d.department_name) LIKE %s"
                params.append(f"%{search_term.lower()}%")

            query += " ORDER BY s.school_name, d.department_name"

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            self.departments_table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                items = [
                    str(row['id']),
                    row['school_name'] or 'N/A',
                    row['department_name'] or 'N/A',
                    row['head_name'] or 'N/A',
                    str(row['teacher_count']),
                    row['description'] or 'N/A',
                    row['created_at'].strftime('%Y-%m-%d %H:%M') if row['created_at'] else 'N/A',
                    'Yes' if row['is_active'] else 'No'
                ]
                for col_idx, item in enumerate(items):
                    table_item = QTableWidgetItem(item)
                    table_item.setData(Qt.UserRole, row['id'])
                    if col_idx == 4:  # Teacher count → right align
                        table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.departments_table.setItem(row_idx, col_idx, table_item)

            self.departments_table.resizeColumnsToContents()
            self.clear_selection()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load departments: {e}")

    def on_department_select(self):
        """Handle row selection"""
        selected = self.departments_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.departments_table.item(row, 0)
        if item:
            dept_id = int(item.data(Qt.UserRole))
            self.current_department_id = dept_id
            self.load_department_data(dept_id)

    def edit_selected_department(self):
        """Switch to form tab on double-click"""
        if self.current_department_id:
            self.tab_widget.setCurrentIndex(0)

    def load_department_data(self, dept_id):
        """Load department data into form"""
        try:
            query = """
                SELECT d.department_name, d.school_id, d.department_head_id, d.description, d.is_active
                FROM departments d
                WHERE d.id = %s
            """
            self.cursor.execute(query, (dept_id,))
            row = self.cursor.fetchone()
            if not row:
                return

            self.name_entry.setText(row['department_name'])
            self.description_box.setPlainText(row['description'] or "")

            # School
            idx = self.school_combo.findData(row['school_id'])
            if idx >= 0:
                self.school_combo.setCurrentIndex(idx)

            # Head
            head_name = next((name for name, tid in self.teachers_map.items() if tid == row['department_head_id']), "")
            self.head_combo.setCurrentText(head_name)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load department: {e}")

    def on_head_combo_activated(self, index):
        """Handle selection from department head combo box"""
        selected_text = self.head_combo.itemText(index)
        self.head_combo.setCurrentText(selected_text)
        self.head_combo.setCurrentIndex(index)  # Optional: sync index
        print(f"Selected department head: {selected_text}")

    def add_department(self):
        """Add new department"""
        if not has_permission(self.user_session, "create_department"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add departments.")
            return

        name = self.name_entry.text().strip()
        school_id = self.school_combo.currentData()
        head_text = self.head_combo.currentText().strip()
        description = self.description_box.toPlainText().strip()

        if not name or not school_id:
            QMessageBox.warning(self, "Validation Error", "Department name and school are required.")
            return

        head_id = self.teachers_map.get(head_text)

        try:
            # Check duplicates
            self.cursor.execute(
                "SELECT id FROM departments WHERE school_id = %s AND department_name = %s AND is_active = 1",
                (school_id, name)
            )
            if self.cursor.fetchone():
                QMessageBox.warning(self, "Duplicate", "A department with this name already exists.")
                return

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO departments (
                    school_id, department_name, department_head_id, description, 
                    is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (school_id, name, head_id, description, 1, now, now))

            dept_id = self.cursor.lastrowid
            self.db_connection.commit()

            # ✅ Audit Log
            self.log_audit_action(
                action="CREATE",
                table_name="departments",
                record_id=dept_id,
                description=f"Created department '{name}' in {self.school_combo.currentText()}"
            )

            QMessageBox.information(self, "Success", "Department added successfully!")
            self.clear_fields()
            self.load_departments()

        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to add department: {e}")

    def update_department(self):
        """Update existing department"""
        if not has_permission(self.user_session, "edit_department"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit departments.")
            return

        if not self.current_department_id:
            QMessageBox.warning(self, "Error", "No department selected.")
            return

        name = self.name_entry.text().strip()
        school_id = self.school_combo.currentData()
        head_text = self.head_combo.currentText().strip()
        description = self.description_box.toPlainText().strip()

        if not name or not school_id:
            QMessageBox.warning(self, "Validation Error", "Department name and school are required.")
            return

        head_id = self.teachers_map.get(head_text)

        try:
            # Check duplicates
            self.cursor.execute(
                "SELECT id FROM departments WHERE school_id = %s AND department_name = %s AND id != %s AND is_active = 1",
                (school_id, name, self.current_department_id)
            )
            if self.cursor.fetchone():
                QMessageBox.warning(self, "Duplicate", "Another department with this name exists in the school.")
                return

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                UPDATE departments SET
                    school_id = %s, department_name = %s, department_head_id = %s,
                    description = %s, updated_at = %s
                WHERE id = %s
            """, (school_id, name, head_id, description, now, self.current_department_id))

            self.db_connection.commit()

            # ✅ Audit Log
            self.log_audit_action(
                action="UPDATE",
                table_name="departments",
                record_id=self.current_department_id,
                description=f"Updated department '{name}' (ID: {self.current_department_id})"
            )

            QMessageBox.information(self, "Success", "Department updated successfully!")
            self.clear_fields()
            self.load_departments()

        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update department: {e}")

    def delete_department(self):
        """Soft delete department"""
        if not has_permission(self.user_session, "delete_department"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete departments.")
            return

        if not self.current_department_id:
            QMessageBox.warning(self, "Error", "No department selected.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Deactivate this department? Teachers will still be assigned.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "UPDATE departments SET is_active = 0, updated_at = %s WHERE id = %s",
                (now, self.current_department_id)
            )
            self.db_connection.commit()

            # ✅ Audit Log
            self.log_audit_action(
                action="DELETE",
                table_name="departments",
                record_id=self.current_department_id,
                description=f"Deactivated department (ID: {self.current_department_id})"
            )

            QMessageBox.information(self, "Success", "Department deactivated.")
            self.clear_fields()
            self.load_departments()

        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete department: {e}")

    def clear_fields(self):
        """Clear all form fields"""
        self.current_department_id = None
        self.name_entry.clear()
        self.school_combo.setCurrentIndex(0)
        self.head_combo.clearEditText()
        self.description_box.clear()

    def clear_selection(self):
        """Clear selection and form"""
        self.clear_fields()
        self.departments_table.clearSelection()

    def apply_permissions(self):
        """Apply UI permissions"""
        can_create = has_permission(self.user_session, "create_department")
        can_edit = has_permission(self.user_session, "edit_department")
        can_delete = has_permission(self.user_session, "delete_department")

        self.add_btn.setEnabled(can_create)
        self.update_btn.setEnabled(can_edit)
        self.delete_btn.setEnabled(can_delete)

        self.add_btn.setToolTip("Add Department" if can_create else "Permission required")
        self.update_btn.setToolTip("Update Department" if can_edit else "Permission required")
        self.delete_btn.setToolTip("Delete Department" if can_delete else "Permission required")

    def export_to_csv(self):
        """Export departments to CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Departments to CSV",
                f"departments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )
            if not filename:
                return

            self.cursor.execute("""
                SELECT 
                    s.school_name, d.department_name, COALESCE(t.full_name, 'N/A') as head,
                    d.description, COUNT(te.id) as teacher_count, d.created_at, d.is_active
                FROM departments d
                LEFT JOIN schools s ON d.school_id = s.id
                LEFT JOIN teachers t ON d.department_head_id = t.id
                LEFT JOIN teachers te ON te.department_id = d.id AND te.is_active = 1
                GROUP BY d.id
                ORDER BY s.school_name, d.department_name
            """)
            rows = self.cursor.fetchall()

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "School", "Department Name", "Head", "Description",
                    "Teacher Count", "Created At", "Active"
                ])
                for row in rows:
                    writer.writerow([
                        row['school_name'],
                        row['department_name'],
                        row['head'],
                        row['description'],
                        row['teacher_count'],
                        row['created_at'].strftime('%Y-%m-%d %H:%M') if row['created_at'] else 'N/A',
                        'Yes' if row['is_active'] else 'No'
                    ])
            QMessageBox.information(self, "Success", f"Exported to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    def export_to_pdf(self):
        """Generate and view PDF report"""
        try:
            from fpdf import FPDF
            import io

            self.cursor.execute("""
                SELECT 
                    s.school_name, d.department_name, COALESCE(t.full_name, 'N/A') as head,
                    d.description, COUNT(te.id) as teacher_count, d.created_at, d.is_active
                FROM departments d
                LEFT JOIN schools s ON d.school_id = s.id
                LEFT JOIN teachers t ON d.department_head_id = t.id
                LEFT JOIN teachers te ON te.department_id = d.id AND te.is_active = 1
                GROUP BY d.id
                ORDER BY s.school_name, d.department_name
            """)
            rows = self.cursor.fetchall()

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Departments Report", ln=True, align="C")
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
            pdf.ln(10)

            col_widths = [40, 40, 40, 40, 20, 20]
            headers = ["School", "Dept Name", "Head", "Desc", "Teachers", "Active"]
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 10, h, 1)
            pdf.ln(10)

            for row in rows:
                data = [
                    row['school_name'][:15] + "..." if len(row['school_name']) > 15 else row['school_name'],
                    row['department_name'][:15] + "..." if len(row['department_name']) > 15 else row['department_name'],
                    row['head'][:15] + "..." if len(row['head']) > 15 else row['head'],
                    (row['description'] or '')[:15] + "..." if row['description'] and len(row['description']) > 15 else (row['description'] or ''),
                    str(row['teacher_count']),
                    'Yes' if row['is_active'] else 'No'
                ]
                for i, d in enumerate(data):
                    pdf.cell(col_widths[i], 10, str(d), 1)
                pdf.ln(10)

            # Output to bytes
            pdf_bytes = pdf.output(dest='S').encode('latin1')
            view_pdf(pdf_bytes, parent=self)

        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed to generate PDF: {e}")