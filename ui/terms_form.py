# ui/terms_form.py
import sys
import os
import traceback
import platform
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QGroupBox, QFormLayout,
    QTabWidget, QCheckBox, QDateEdit, QSpinBox, QComboBox, QMenu, QApplication, 
    QSizePolicy, QProgressDialog
)
from PySide6.QtCore import Qt, QDate, QMetaObject, Slot, QSize
from PySide6.QtGui import QFont, QIcon

from utils.permissions import has_permission
from ui.audit_base_form import AuditBaseForm
from models.models import get_db_connection
from fpdf import FPDF
from utils.pdf_utils import view_pdf
from utils.pdf_constants import PDF_TABLE_HEADER_BG, PDF_ALTERNATE_ROW_BG, PDF_CURRENT_TERM_BG


class TermsForm(AuditBaseForm):
    """Enhanced Terms Management Form with Permissions and Audit Logging"""

    def __init__(self, parent=None, user_session: Optional[Dict[str, Any]] = None):
        print(f"DEBUG: TermsForm.__init__ received user_session: {user_session}")
        super().__init__(parent, user_session)
        self.user_session = user_session  # Ensure this is set
        self.current_term_id = None
    
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
    
        self.setup_ui()
        self.load_academic_years()
        self.load_terms()
        
        # FIX: Call directly instead of using QMetaObject.invokeMethod
        self.apply_button_permissions()

    def setup_ui(self):
        """Set up the main UI with tabs and consistent styling"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.fonts['tab'])
        self.tab_widget.setCurrentIndex(0)

        self.term_form_tab = QWidget()
        self.term_data_tab = QWidget()

        self.tab_widget.addTab(self.term_form_tab, "Term Form")
        self.tab_widget.addTab(self.term_data_tab, "Terms Data")

        self.setup_term_form_tab()
        self.setup_term_data_tab()

        layout.addWidget(self.tab_widget)

    def setup_term_form_tab(self):
        """Set up the form tab with scrollable layout"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(20)

        # Info Section
        self.create_info_section(form_layout)

        # Button Section
        self.create_button_section(form_layout)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
        form_layout.addWidget(self.status_label)

        scroll_area.setWidget(container)
        tab_layout = QVBoxLayout(self.term_form_tab)
        tab_layout.addWidget(scroll_area)

    def create_info_section(self, parent_layout):
        """Create styled form section"""
        group = QGroupBox("Term Details")
        group.setFont(self.fonts['section'])
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {self.colors['border']};
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 15px;
                background-color: {self.colors['background']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: {self.colors['background']};
                color: {self.colors['primary']};
                font-weight: bold;
            }}
        """)
        layout = QFormLayout(group)
        layout.setSpacing(15)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Term Name
        self.term_name_entry = QLineEdit()
        self.term_name_entry.setPlaceholderText("e.g., First Term, Mid-Year Term")
        self.term_name_entry.setFont(self.fonts['entry'])
        self.term_name_entry.setStyleSheet(f"""
            QLineEdit {{
                padding: 10px 14px;
                border: 2px solid {self.colors['input_border']};
                border-radius: 8px;
                font-size: 14px;
                background-color: {self.colors['input_background']};
            }}
            QLineEdit:focus {{
                border-color: {self.colors['input_focus']};
                background-color: #f8f9fa;
            }}
        """)
        layout.addRow(self.create_styled_label("Term Name:"), self.term_name_entry)

        # Term Number - FIXED: Smaller spinbox
        self.term_number_spin = QSpinBox()
        self.term_number_spin.setRange(0, 5)
        self.term_number_spin.setSpecialValueText("")
        self.term_number_spin.setFont(self.fonts['entry'])
        self.term_number_spin.setFixedWidth(80)  # Fixed width
        self.term_number_spin.setStyleSheet(f"""
            QSpinBox {{
                padding: 10px 8px;
                border: 2px solid {self.colors['input_border']};
                border-radius: 8px;
                font-size: 14px;
                background-color: {self.colors['input_background']};
            }}
        """)
        layout.addRow(self.create_styled_label("Term Number:"), self.term_number_spin)

        # Academic Year
        self.academic_year_combo = QComboBox()
        self.academic_year_combo.setFont(self.fonts['entry'])
        self.academic_year_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 10px 14px;
                border: 2px solid {self.colors['input_border']};
                border-radius: 8px;
                font-size: 14px;
                background-color: {self.colors['input_background']};
            }}
            QComboBox:focus {{
                border-color: {self.colors['input_focus']};
            }}
        """)
        layout.addRow(self.create_styled_label("Academic Year:"), self.academic_year_combo)

        # Date Row
        date_layout = QHBoxLayout()
        self.start_date_entry = QDateEdit()
        self.start_date_entry.setDate(QDate.currentDate())
        self.start_date_entry.setCalendarPopup(True)
        self.start_date_entry.setFont(self.fonts['entry'])

        self.end_date_entry = QDateEdit()
        self.end_date_entry.setDate(QDate.currentDate())
        self.end_date_entry.setCalendarPopup(True)
        self.end_date_entry.setFont(self.fonts['entry'])

        date_layout.addWidget(QLabel("Start Date:"))
        date_layout.addWidget(self.start_date_entry)
        date_layout.addSpacing(20)
        date_layout.addWidget(QLabel("End Date:"))
        date_layout.addWidget(self.end_date_entry)
        layout.addRow("", date_layout)

        # Current Term
        self.is_current_checkbox = QCheckBox("Set as Current Term")
        self.is_current_checkbox.setFont(self.fonts['entry'])
        layout.addRow("", self.is_current_checkbox)

        parent_layout.addWidget(group)

    def create_button_section(self, parent_layout):
        """Create action buttons with permission-aware styling"""
        button_layout = QHBoxLayout()
    
        # Add Term
        self.add_btn = QPushButton("Add Term")
        self.add_btn.setProperty("class", "success")
        self.add_btn.setMinimumSize(150, 40)
        self.add_btn.setIcon(QIcon("static/icons/add.png"))
        self.add_btn.setIconSize(QSize(20, 20))
        self.add_btn.clicked.connect(self.add_term)
        self.add_btn.setToolTip("Add a new academic term")
    
        # Update Term
        self.update_btn = QPushButton("Update Term")
        self.update_btn.setProperty("class", "primary")
        self.update_btn.setMinimumSize(150, 40)
        self.update_btn.setIcon(QIcon("static/icons/update.png"))
        self.update_btn.setIconSize(QSize(20, 20))
        self.update_btn.clicked.connect(self.update_term)
        self.update_btn.setToolTip("Update selected term")
    
        # Delete Term
        self.delete_btn = QPushButton("Delete Term")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setMinimumSize(150, 40)
        self.delete_btn.setIcon(QIcon("static/icons/delete.png"))
        self.delete_btn.setIconSize(QSize(20, 20))
        self.delete_btn.clicked.connect(self.delete_term)
        self.delete_btn.setToolTip("Delete selected term")
    
        # Clear
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("class", "secondary")
        self.clear_btn.setMinimumSize(120, 40)
        self.clear_btn.setIcon(QIcon("static/icons/clear.png"))
        self.clear_btn.setIconSize(QSize(20, 20))
        self.clear_btn.clicked.connect(self.clear_fields)
        self.clear_btn.setToolTip("Clear form fields")
    
        # Arrange with spacing
        button_layout.addStretch()
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
    
        parent_layout.addLayout(button_layout)


    def setup_term_data_tab(self):
        """Set up the terms data tab"""
        layout = QVBoxLayout(self.term_data_tab)
        layout.setSpacing(15)
    
        # === SEARCH & ACTIONS BAR ===
        search_actions_group = QGroupBox("Manage Terms")
        search_actions_group.setFont(self.fonts['section'])
        search_actions_layout = QHBoxLayout(search_actions_group)
    
        # Search Input
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search by term name, academic year...")
        self.search_entry.setFixedWidth(400)
        search_actions_layout.addWidget(self.search_entry)
        
        # Search Button
        search_btn = QPushButton("Search")
        search_btn.setProperty("class", "primary")
        search_btn.setFixedWidth(130)
        search_btn.setIcon(QIcon("static/icons/search.png"))
        search_btn.setIconSize(QSize(20, 20))
        search_btn.clicked.connect(self.search_terms_action)
        search_actions_layout.addWidget(search_btn)
        
        # Clear Button
        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setFixedWidth(130)
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(20, 20))
        clear_btn.clicked.connect(self.clear_search)
        search_actions_layout.addWidget(clear_btn)
        
        search_actions_layout.addSpacing(20)  # Spacer
        
        # Export Button
        export_btn = QPushButton("Export")
        export_btn.setProperty("class", "info")
        export_btn.setFixedWidth(130)
        export_btn.setIcon(QIcon("static/icons/export.png"))
        export_btn.setIconSize(QSize(20, 20))
        export_btn.clicked.connect(self.export_terms_data)
        search_actions_layout.addWidget(export_btn)
        
        # Report Button
        report_btn = QPushButton("Report")
        report_btn.setProperty("class", "primary")
        report_btn.setFixedWidth(160)  # wider for longer label
        report_btn.setIcon(QIcon("static/icons/report.png"))
        report_btn.setIconSize(QSize(20, 20))
        report_btn.clicked.connect(self.generate_term_report)
        search_actions_layout.addWidget(report_btn)
        
        # Refresh Button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.setFixedWidth(130)
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(20, 20))
        refresh_btn.clicked.connect(self.refresh_data)
        search_actions_layout.addWidget(refresh_btn)
        
        # Add stretch to keep group aligned neatly
        search_actions_layout.addStretch()
        
        layout.addWidget(search_actions_group)

        # === TABLE ===
        table_group = QGroupBox("All Terms")
        table_group.setFont(self.fonts['section'])
        table_layout = QVBoxLayout(table_group)
    
        self.terms_table = QTableWidget()
        self.terms_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.terms_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.terms_table.setSortingEnabled(True)
        self.terms_table.verticalHeader().setVisible(False)
        self.terms_table.setFont(self.fonts['table'])
        self.terms_table.horizontalHeader().setFont(self.fonts['table_header'])
    
        headers = ["ID", "Term Name", "Term #", "Academic Year", "Start Date", "End Date", "Current"]
        self.terms_table.setColumnCount(len(headers))
        self.terms_table.setHorizontalHeaderLabels(headers)
    
        table_layout.addWidget(self.terms_table)
        layout.addWidget(table_group)
    
        # Connect table selection
        self.terms_table.cellClicked.connect(self.on_term_select)
    
    def apply_button_permissions(self):
        """Apply button permissions with safety check"""
        print(f"DEBUG: apply_button_permissions called with user_session: {self.user_session}")
        
        # Safety check - ensure buttons exist
        if not hasattr(self, 'add_btn') or not hasattr(self, 'update_btn') or not hasattr(self, 'delete_btn'):
            print("Warning: UI buttons not fully initialized, skipping permissions")
            return
        
        # Debug the permission checks
        can_create = has_permission(self.user_session, 'create_term')
        can_edit = has_permission(self.user_session, 'edit_term')
        can_delete = has_permission(self.user_session, 'delete_term')
        
        print(f"DEBUG: Permissions - create: {can_create}, edit: {can_edit}, delete: {can_delete}")
        print(f"DEBUG: User role: {self.user_session.get('role') if self.user_session else 'No session'}")
    
        self.add_btn.setEnabled(can_create)
        self.update_btn.setEnabled(can_edit)
        self.delete_btn.setEnabled(can_delete)
    
        # Update tooltips
        self.add_btn.setToolTip("Add a new term" if can_create else "Permission required: create_term")
        self.update_btn.setToolTip("Update selected term" if can_edit else "Permission required: edit_term")
        self.delete_btn.setToolTip("Delete selected term" if can_delete else "Permission required: delete_term")


    def get_academic_year_id(self):
        """Get selected academic year ID"""
        if self.academic_year_combo.currentIndex() == -1:
            return None
        year_name = self.academic_year_combo.currentText()
        self.cursor.execute("SELECT id FROM academic_years WHERE year_name = %s", (year_name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def validate_fields(self):
        """Validate form fields"""
        if not self.term_name_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Term name is required.")
            return False
        if self.academic_year_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Validation Error", "Please select an academic year.")
            return False
        if self.start_date_entry.date() > self.end_date_entry.date():
            QMessageBox.warning(self, "Validation Error", "Start date cannot be after end date.")
            return False
        return True

    def add_term(self):
        """Add a new term"""
        if not has_permission(self.user_session, 'create_term'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add terms.")
            return

        if not self.validate_fields():
            return

        try:
            academic_year_id = self.get_academic_year_id()
            if not academic_year_id:
                QMessageBox.warning(self, "Error", "Invalid academic year selected.")
                return

            # Unset current term if setting new one
            if self.is_current_checkbox.isChecked():
                self.cursor.execute("UPDATE terms SET is_current = FALSE")

            # Insert term
            query = """
                INSERT INTO terms (term_name, term_number, academic_year_id, start_date, end_date, is_current)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            term_number = self.term_number_spin.value() if self.term_number_spin.value() > 0 else None
            values = (
                self.term_name_entry.text().strip(),
                term_number,
                academic_year_id,
                self.start_date_entry.date().toPython(),
                self.end_date_entry.date().toPython(),
                self.is_current_checkbox.isChecked()
            )
            self.cursor.execute(query, values)
            term_id = self.cursor.lastrowid
            self.db_connection.commit()

            self.log_audit_action(
                action="CREATE",
                table_name="terms",
                record_id=term_id,
                description=f"Added term '{values[0]}' (Term #{values[1] or 'N/A'})"
            )

            QMessageBox.information(self, "Success", "Term added successfully!")
            self.clear_fields()
            self.load_terms()

        except Exception as e:
            self.db_connection.rollback()
            if "Duplicate entry" in str(e):
                QMessageBox.warning(self, "Error", "A term with this name already exists.")
            else:
                QMessageBox.critical(self, "Error", f"Failed to add term: {str(e)}")

    def update_term(self):
        """Update selected term"""
        if not self.current_term_id:
            QMessageBox.warning(self, "Error", "Please select a term to update.")
            return

        if not has_permission(self.user_session, 'edit_term'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit terms.")
            return

        if not self.validate_fields():
            return

        try:
            academic_year_id = self.get_academic_year_id()
            if not academic_year_id:
                QMessageBox.warning(self, "Error", "Invalid academic year selected.")
                return

            # Unset current term if setting new one
            if self.is_current_checkbox.isChecked():
                self.cursor.execute("UPDATE terms SET is_current = FALSE")

            # Update term
            query = """
                UPDATE terms SET
                    term_name = %s, term_number = %s, academic_year_id = %s,
                    start_date = %s, end_date = %s, is_current = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            term_number = self.term_number_spin.value() if self.term_number_spin.value() > 0 else None
            values = (
                self.term_name_entry.text().strip(),
                term_number,
                academic_year_id,
                self.start_date_entry.date().toPython(),
                self.end_date_entry.date().toPython(),
                self.is_current_checkbox.isChecked(),
                self.current_term_id
            )
            self.cursor.execute(query, values)
            self.db_connection.commit()

            self.log_audit_action(
                action="UPDATE",
                table_name="terms",
                record_id=self.current_term_id,
                description=f"Updated term '{values[0]}'"
            )

            QMessageBox.information(self, "Success", "Term updated successfully!")
            self.clear_fields()
            self.load_terms()

        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update term: {str(e)}")

    def delete_term(self):
        """Delete selected term"""
        if not self.current_term_id:
            QMessageBox.warning(self, "Error", "Please select a term to delete.")
            return

        if not has_permission(self.user_session, 'delete_term'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete terms.")
            return

        # Check dependencies
        self.cursor.execute("SELECT COUNT(*) FROM classes WHERE term_id = %s", (self.current_term_id,))
        class_count = self.cursor.fetchone()[0]
        if class_count > 0:
            QMessageBox.warning(self, "Error", f"Cannot delete: Term has {class_count} classes assigned.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this term? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        try:
            # Get term name for audit log
            self.cursor.execute("SELECT term_name FROM terms WHERE id = %s", (self.current_term_id,))
            term_name = self.cursor.fetchone()
            term_name = term_name[0] if term_name else "Unknown"

            # Delete term
            self.cursor.execute("DELETE FROM terms WHERE id = %s", (self.current_term_id,))
            self.db_connection.commit()

            self.log_audit_action(
                action="DELETE",
                table_name="terms",
                record_id=self.current_term_id,
                description=f"Deleted term: {term_name}"
            )

            QMessageBox.information(self, "Success", "Term deleted successfully!")
            self.clear_fields()
            self.load_terms()

        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete term: {str(e)}")

    def clear_fields(self):
        """Reset form fields"""
        self.current_term_id = None
        self.term_name_entry.clear()
        self.term_number_spin.setValue(0)
        self.academic_year_combo.setCurrentIndex(-1)
        self.start_date_entry.setDate(QDate.currentDate())
        self.end_date_entry.setDate(QDate.currentDate())
        self.is_current_checkbox.setChecked(False)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")

    def load_academic_years(self):
        """Load academic years into combo box"""
        try:
            self.cursor.execute("SELECT year_name FROM academic_years ORDER BY year_name")
            years = self.cursor.fetchall()
            self.academic_year_combo.clear()
            for year in years:
                self.academic_year_combo.addItem(year[0])
        except Exception as e:
            print(f"Error loading academic years: {e}")

    def load_terms(self):
        """Load all terms into table"""
        try:
            query = """
                SELECT t.id, t.term_name, t.term_number, ay.year_name, 
                       t.start_date, t.end_date, t.is_current
                FROM terms t
                LEFT JOIN academic_years ay ON t.academic_year_id = ay.id
                ORDER BY ay.year_name, t.term_number
            """
            self.cursor.execute(query)
            terms = self.cursor.fetchall()
            self.update_terms_table(terms)
        except Exception as e:
            print(f"Error loading terms: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load terms: {str(e)}")

    def update_terms_table(self, terms):
        """Update table with term data and proper column widths"""
        self.terms_table.setRowCount(len(terms))
        headers = ["ID", "Term Name", "Term #", "Academic Year", "Start Date", "End Date", "Current"]
        self.terms_table.setHorizontalHeaderLabels(headers)

        for row, term in enumerate(terms):
            for col, value in enumerate(term):
                if col == 2:  # term_number
                    text = str(value) if value is not None else ""
                elif col == 6:  # is_current
                    text = "Yes" if value else "No"
                elif col in (4, 5) and value:  # dates
                    text = value.strftime("%Y-%m-%d") if hasattr(value, 'strftime') else str(value)
                else:
                    text = str(value) if value is not None else ""
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.terms_table.setItem(row, col, item)

        # FIXED: Proper column widths instead of all stretch
        header = self.terms_table.horizontalHeader()
        
        # Set specific widths for each column
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # ID
        self.terms_table.setColumnWidth(0, 60)
        
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Term Name (flexible)
        
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Term #
        self.terms_table.setColumnWidth(2, 150)
        
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Academic Year
        self.terms_table.setColumnWidth(3, 180)
        
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Start Date
        self.terms_table.setColumnWidth(4, 150)
        
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # End Date
        self.terms_table.setColumnWidth(5, 150)
        
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Current
        self.terms_table.setColumnWidth(6, 150)
    
    def on_term_select(self, row, col):
        """Handle row selection"""
        try:
            term_id_item = self.terms_table.item(row, 0)
            if not term_id_item:
                return
            self.current_term_id = int(term_id_item.text())
            self.load_term_data(self.current_term_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load term: {str(e)}")

    def load_term_data(self, term_id):
        """Load term data into form"""
        try:
            query = """
                SELECT t.id, t.term_name, t.term_number, t.academic_year_id,
                       t.start_date, t.end_date, t.is_current, ay.year_name
                FROM terms t
                LEFT JOIN academic_years ay ON t.academic_year_id = ay.id
                WHERE t.id = %s
            """
            self.cursor.execute(query, (term_id,))
            term = self.cursor.fetchone()
            if not term:
                return
    
            self.current_term_id = term[0]
            self.term_name_entry.setText(term[1] or "")
            self.term_number_spin.setValue(term[2] or 0)
            if term[7]:  # year_name
                idx = self.academic_year_combo.findText(term[7])
                if idx >= 0:
                    self.academic_year_combo.setCurrentIndex(idx)
            
            # FIX: Convert Python date/datetime to QDate properly
            if term[4]:  # start_date
                if hasattr(term[4], 'year'):  # It's a date/datetime object
                    self.start_date_entry.setDate(QDate(term[4].year, term[4].month, term[4].day))
                elif isinstance(term[4], str):  # It's a string
                    # Parse string date (assuming format like YYYY-MM-DD)
                    date_parts = term[4].split('-')
                    if len(date_parts) == 3:
                        self.start_date_entry.setDate(QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2])))
            
            if term[5]:  # end_date
                if hasattr(term[5], 'year'):  # It's a date/datetime object
                    self.end_date_entry.setDate(QDate(term[5].year, term[5].month, term[5].day))
                elif isinstance(term[5], str):  # It's a string
                    # Parse string date (assuming format like YYYY-MM-DD)
                    date_parts = term[5].split('-')
                    if len(date_parts) == 3:
                        self.end_date_entry.setDate(QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2])))
            
            self.is_current_checkbox.setChecked(bool(term[6]))
    
            self.status_label.setText(f"Selected: {term[1]} - Ready to update/delete")
            self.status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
            self.tab_widget.setCurrentIndex(0)
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load term data: {str(e)}")

    def search_terms_action(self):
        """Trigger search"""
        self.search_terms(self.search_entry.text().strip())

    def search_terms(self, search_term=""):
        """Search terms by name AND academic year"""
        try:
            if search_term:
                query = """
                    SELECT t.id, t.term_name, t.term_number, ay.year_name, 
                           t.start_date, t.end_date, t.is_current
                    FROM terms t
                    LEFT JOIN academic_years ay ON t.academic_year_id = ay.id
                    WHERE t.term_name LIKE %s OR ay.year_name LIKE %s
                    ORDER BY ay.year_name, t.term_number
                """
                self.cursor.execute(query, (f"%{search_term}%", f"%{search_term}%"))
            else:
                self.load_terms()
                return
    
            terms = self.cursor.fetchall()
            self.update_terms_table(terms)
            if not terms:
                QMessageBox.information(self, "Search Results", "No terms found matching your search.")
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Search failed: {str(e)}")
        
    def clear_search(self):
        """Clear search and reload"""
        self.search_entry.clear()
        self.load_terms()

    def export_terms_data(self):
        """Export to Excel with green header"""
        try:
            query = """
                SELECT t.term_name, t.term_number, ay.year_name, 
                       t.start_date, t.end_date, 
                       CASE WHEN t.is_current THEN 'Yes' ELSE 'No' END as is_current
                FROM terms t
                LEFT JOIN academic_years ay ON t.academic_year_id = ay.id
                ORDER BY ay.year_name, t.term_number
            """
            self.cursor.execute(query)
            terms = self.cursor.fetchall()
            if not terms:
                QMessageBox.information(self, "No Data", "No terms to export.")
                return
    
            headers = ['Term Name', 'Term #', 'Academic Year', 'Start Date', 'End Date', 'Current']
            
            # Convert to list of lists (fix for "no attribute get" error)
            data = []
            for term in terms:
                # Handle different database cursor return types
                if isinstance(term, dict):  # If using dictionary cursor
                    term_name = term.get('term_name', 'N/A')
                    term_number = str(term.get('term_number', 'N/A')) if term.get('term_number') not in [None, ''] else 'N/A'
                    year_name = term.get('year_name', 'N/A')
                    start_date = term.get('start_date')
                    end_date = term.get('end_date')
                    is_current = term.get('is_current', 'No')
                else:  # If using tuple cursor (default)
                    term_name = term[0] if len(term) > 0 else 'N/A'
                    term_number = str(term[1]) if len(term) > 1 and term[1] not in [None, ''] else 'N/A'
                    year_name = term[2] if len(term) > 2 else 'N/A'
                    start_date = term[3] if len(term) > 3 else None
                    end_date = term[4] if len(term) > 4 else None
                    is_current = term[5] if len(term) > 5 else 'No'
                
                # Format dates
                start_date_str = start_date.strftime('%Y-%m-%d') if start_date and hasattr(start_date, 'strftime') else 'N/A'
                end_date_str = end_date.strftime('%Y-%m-%d') if end_date and hasattr(end_date, 'strftime') else 'N/A'
                
                data.append([
                    term_name,
                    term_number,
                    year_name,
                    start_date_str,
                    end_date_str,
                    is_current
                ])
    
            school_info = self.get_school_info()
            title = f"{school_info['name']} - Terms Export"
    
            self.export_with_green_header(
                data=data,
                headers=headers,
                filename_prefix="terms_export",
                title=title
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}\n{traceback.format_exc()}")
        
    def refresh_data(self):
        """Refresh all data with user feedback"""
        try:
            # Show progress dialog
            progress = QProgressDialog("Refreshing data...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Refreshing")
            progress.setWindowModality(Qt.WindowModal)
            progress.setValue(10)
            QApplication.processEvents()
            
            self._ensure_connection()
            progress.setValue(30)
            
            self.status_label.setText("Refreshing...")
            progress.setValue(50)
            
            self.load_terms()
            progress.setValue(70)
            
            self.load_academic_years()
            progress.setValue(90)
            
            self.clear_fields()
            self.apply_button_permissions()
            progress.setValue(100)
            
            self.status_label.setText("Data refreshed successfully")
            self.status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
            
            QMessageBox.information(self, "Success", "Data refreshed successfully!")
            
        except Exception as e:
            self.status_label.setText("Refresh failed")
            self.status_label.setStyleSheet(f"color: {self.colors['danger']}; font-weight: bold;")
            QMessageBox.critical(self, "Error", f"Refresh failed: {str(e)}")
        finally:
            if 'progress' in locals():
                progress.close()

    def create_styled_label(self, text):
        """Create a styled label using shared fonts and colors"""
        label = QLabel(text)
        label.setFont(self.fonts['label'])
        label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold;")
        return label

    def generate_term_report(self):
        """Generate Terms Report PDF and preview using view_pdf()"""
        try:
            from fpdf import FPDF
            from datetime import datetime
            import os
            import io
    
            # Ensure DB connection
            self._ensure_connection()
    
            def safe_encode(text):
                """Safely encode text for FPDF (latin-1 compatible)"""
                if not text:
                    return "N/A"
                replacements = {
                    '\u2013': '-', '\u2014': '--', '\u2018': "'", '\u2019': "'",
                    '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u25cf': '•'
                }
                result = str(text)
                for a, b in replacements.items():
                    result = result.replace(a, b)
                return result.encode('latin-1', 'replace').decode('latin-1')
    
            # === Fetch school info ===
            school_query = "SELECT school_name, address, phone, email, logo_path FROM schools LIMIT 1"
            self.cursor.execute(school_query)
            school_result = self.cursor.fetchone()
    
            if school_result:
                if isinstance(school_result, tuple):
                    school_name = school_result[0] or "CBCentra School Management System"
                    school_address = school_result[1] or "P.O. Box 12345"
                    school_phone = school_result[2] or "Tel: +254 700 000000"
                    school_email = school_result[3] or "info@cbcentra.edu"
                    school_logo_path = school_result[4]
                else:
                    school_name = school_result.get('school_name', "CBCentra School")
                    school_address = school_result.get('address', "P.O. Box 12345")
                    school_phone = school_result.get('phone', "Tel: +254 700 000000")
                    school_email = school_result.get('email', "info@cbcentra.edu")
                    school_logo_path = school_result.get('logo_path')
            else:
                school_name = "CBCentra School"
                school_address = "P.O. Box 12345"
                school_phone = "Tel: +254 700 000000"
                school_email = "info@cbcentra.edu"
                school_logo_path = None
    
            default_logo = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "static", "images", "logo.png"
            )
            school_logo = school_logo_path or default_logo
    
            # === Fetch terms data ===
            query = """
                SELECT 
                    t.id,
                    t.term_name, 
                    t.term_number, 
                    ay.year_name as academic_year,
                    t.start_date, 
                    t.end_date, 
                    t.is_current,
                    COUNT(c.id) as class_count
                FROM terms t
                LEFT JOIN academic_years ay ON t.academic_year_id = ay.id
                LEFT JOIN classes c ON t.id = c.term_id
                GROUP BY t.id, t.term_name, t.term_number, ay.year_name, t.start_date, t.end_date, t.is_current
                ORDER BY ay.year_name, t.term_number
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
    
            if not rows:
                QMessageBox.information(self, "No Data", "No terms found to export.")
                return
    
            total_terms = len(rows)
            current_term_name = "None"
            for row in rows:
                is_current = row[6] if isinstance(row, tuple) else row.get('is_current')
                if is_current:
                    current_term_name = row[1] if isinstance(row, tuple) else row.get('term_name')
                    break
    
            total_classes = sum(row[7] if isinstance(row, tuple) else row.get('class_count', 0) for row in rows)
    
            user_name = self.user_session.get('full_name', 'Unknown') if self.user_session else "Unknown"
    
            # === Define PDF class ===
            class TermsPDF(FPDF):
                def __init__(self):
                    super().__init__(orientation='P', unit='mm', format='A4')
                    self.set_margins(15, 15, 15)
                    self.set_auto_page_break(auto=True, margin=15)
    
                def header(self):
                    if os.path.exists(school_logo):
                        try:
                            self.image(school_logo, 15, 10, 25)
                        except Exception as e:
                            print(f"Logo load error: {e}")
    
                    x = 16
                    y = 10
                    self.set_xy(x, y)
                    self.set_font("Arial", "B", 14)
                    self.cell(0, 6, safe_encode(school_name), ln=True, align='C')
                    self.set_x(x)
                    self.set_font("Arial", "", 10)
                    self.cell(0, 4, safe_encode(school_address), ln=True, align='C')
                    self.set_x(x)
                    self.cell(0, 4, safe_encode(school_phone), ln=True, align='C')
                    self.set_x(x)
                    self.cell(0, 4, safe_encode(school_email), ln=True, align='C')
    
                    self.ln(10)
                    self.set_font("Arial", "B", 16)
                    self.set_text_color(0, 0, 0)
                    self.cell(0, 8, "TERMS REPORT", 0, 1, "C")
    
                    self.set_font("Arial", "I", 10)
                    self.cell(0, 6, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "C")
                    self.cell(0, 6, f"Generated by: {user_name}", 0, 1, "C")
                    self.ln(5)
    
                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", "I", 8)
                    self.set_text_color(128, 128, 128)
                    self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")
    
                def section_header(self, title):
                    self.ln(3)
                    self.set_font("Arial", "B", 12)
                    self.set_text_color(0, 0, 0)
                    self.cell(0, 8, safe_encode(title), 0, 1, "L")
                    self.ln(2)
    
            # === GENERATE PDF IN MEMORY ===
            pdf = TermsPDF()
            pdf.add_page()
    
            # Summary
            pdf.section_header("Summary")
            pdf.set_font("Arial", "", 10)
            col_w = [95, 95]
            pdf.cell(col_w[0], 6, "Total Terms:", 1, 0, "L")
            pdf.cell(col_w[1], 6, str(total_terms), 1, 1, "L")
            pdf.cell(col_w[0], 6, "Current Term:", 1, 0, "L")
            pdf.cell(col_w[1], 6, safe_encode(current_term_name), 1, 1, "L")
            pdf.cell(col_w[0], 6, "Total Classes Across Terms:", 1, 0, "L")
            pdf.cell(col_w[1], 6, str(total_classes), 1, 1, "L")
            pdf.ln(5)
    
            # Terms List
            pdf.section_header("Terms List")
            pdf.set_fill_color(*PDF_TABLE_HEADER_BG)  # Use your constant
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "B", 9)
            col_widths = [40, 25, 40, 30, 30, 25]
            headers = ["Term Name", "Term #", "Academic Year", "Start Date", "End Date", "Classes"]
    
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 8, safe_encode(h), border=1, align="C", fill=True)
            pdf.ln()
    
            pdf.set_font("Arial", "", 8)
            for i, row in enumerate(rows):
                if isinstance(row, tuple):
                    term_name = safe_encode(row[1] or 'N/A')
                    term_number = str(row[2]) if row[2] else "N/A"
                    academic_year = safe_encode(row[3] or 'N/A')
                    start_date = row[4]
                    end_date = row[5]
                    is_current = row[6]
                    class_count = str(row[7])
                else:
                    term_name = safe_encode(row.get('term_name', 'N/A'))
                    term_number = str(row.get('term_number')) if row.get('term_number') else "N/A"
                    academic_year = safe_encode(row.get('academic_year', 'N/A'))
                    start_date = row.get('start_date')
                    end_date = row.get('end_date')
                    is_current = row.get('is_current', False)
                    class_count = str(row.get('class_count', 0))
    
                start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date) if start_date else 'N/A'
                end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date) if end_date else 'N/A'
    
                if is_current:
                    pdf.set_fill_color(*PDF_CURRENT_TERM_BG)
                else:
                    pdf.set_fill_color(*PDF_ALTERNATE_ROW_BG if i % 2 == 0 else (255, 255, 255))
    
                pdf.cell(col_widths[0], 6, term_name, border=1, fill=True)
                pdf.cell(col_widths[1], 6, term_number, border=1, fill=True, align="C")
                pdf.cell(col_widths[2], 6, academic_year, border=1, fill=True)
                pdf.cell(col_widths[3], 6, start_date_str, border=1, fill=True, align="C")
                pdf.cell(col_widths[4], 6, end_date_str, border=1, fill=True, align="C")
                pdf.cell(col_widths[5], 6, class_count, border=1, fill=True, align="C")
                pdf.ln()
    
            if any(row[6] if isinstance(row, tuple) else row.get('is_current') for row in rows):
                pdf.ln(3)
                pdf.set_font("Arial", "I", 8)
                pdf.set_fill_color(*PDF_CURRENT_TERM_BG)
                pdf.cell(5, 5, "", 1, 0, "C", fill=True)
                pdf.cell(0, 5, " = Current Term", ln=True)
    
            pdf.ln(5)
            pdf.set_font("Arial", "I", 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 6, safe_encode("Report generated by: CBCentra School Management System."), ln=True, align="C")
    
            # === GET PDF BYTES ===
            pdf_bytes = pdf.output(dest='S').encode('latin1')  # Output as bytes
    
            # Open in built-in viewer
            from utils.pdf_utils import view_pdf
            view_pdf(pdf_bytes, parent=self)
    
        except ImportError:
            QMessageBox.critical(self, "Missing Library", "Please install fpdf2: pip install fpdf2")
        except Exception as e:
            error_msg = str(e)
            print(f"❌ PDF Export Error: {error_msg}")
            QMessageBox.critical(self, "Export Failed", f"Failed to generate PDF: {str(e)}")

        
    def _ensure_connection(self):
        """Ensure database connection is active"""
        try:
            self.cursor.execute("SELECT 1")
        except:
            try:
                self.db_connection = get_db_connection()
                self.cursor = self.db_connection.cursor(buffered=True)
            except Exception as e:
                raise Exception(f"Database reconnection failed: {e}")

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