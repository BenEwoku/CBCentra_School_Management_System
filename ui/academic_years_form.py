# ui/academic_years_form.py
import sys
import os
import traceback
import subprocess
import platform
from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QGroupBox, QFormLayout,
    QTabWidget, QCheckBox, QDateEdit, QComboBox, QTextEdit, QDialog, QApplication
)
from PySide6.QtCore import Qt, QDate, Signal, QSize
from PySide6.QtGui import QFont, QIcon

from utils.permissions import has_permission
from ui.audit_base_form import AuditBaseForm
from models.models import get_db_connection


class AcademicYearsForm(AuditBaseForm):
    """Enhanced Academic Years Management Form with Permissions and Audit Logging"""
    year_selected = Signal(int)

    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.user_session = user_session
        self.current_year_id = None

        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True)
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return

        self.setup_ui()
        self.load_academic_years()
        self.apply_button_permissions()

    def setup_ui(self):
        """Set up the main UI with tabs and consistent styling"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Academic Years Management")
        title_label.setFont(self.fonts['title'])
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"color: {self.colors['primary']}; margin-bottom: 16px;")
        layout.addWidget(title_label)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.fonts['tab'])

        self.year_form_tab = QWidget()
        self.year_data_tab = QWidget()

        self.tab_widget.addTab(self.year_form_tab, "Year Form")
        self.tab_widget.addTab(self.year_data_tab, "Years Data")

        self.setup_year_form_tab()
        self.setup_year_data_tab()

        layout.addWidget(self.tab_widget)

    def setup_year_form_tab(self):
        """Set up scrollable form tab"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(20)

        # Info Section
        self.create_info_section(form_layout)

        # Action Buttons
        self.create_action_buttons(form_layout)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
        form_layout.addWidget(self.status_label)

        scroll_area.setWidget(container)
        tab_layout = QVBoxLayout(self.year_form_tab)
        tab_layout.addWidget(scroll_area)

    def create_info_section(self, parent_layout):
        """Create styled form section"""
        group = QGroupBox("Academic Year Details")
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

        # Year Name
        self.year_name_entry = QLineEdit()
        self.year_name_entry.setPlaceholderText("e.g., 2024-2025")
        self.year_name_entry.setFont(self.fonts['entry'])
        self.year_name_entry.setStyleSheet(f"""
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
        layout.addRow(self.create_styled_label("Year Name:"), self.year_name_entry)

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

        # Current Year Checkbox
        self.is_current_checkbox = QCheckBox("Set as Current Academic Year")
        self.is_current_checkbox.setFont(self.fonts['entry'])
        layout.addRow("", self.is_current_checkbox)

        parent_layout.addWidget(group)
    
    def create_action_buttons(self, parent_layout):
        """Create action buttons with permission-aware styling"""
        button_layout = QHBoxLayout()
    
        # Add Year
        self.add_btn = QPushButton("Add Year")
        self.add_btn.setProperty("class", "success")
        self.add_btn.setMinimumSize(150, 40)
        self.add_btn.setIcon(QIcon("static/icons/add.png"))
        self.add_btn.setIconSize(QSize(20, 20))
        self.add_btn.clicked.connect(self.add_academic_year)
        self.add_btn.setToolTip("Add a new academic year")
    
        # Update Year
        self.update_btn = QPushButton("Update Year")
        self.update_btn.setProperty("class", "primary")
        self.update_btn.setMinimumSize(150, 40)
        self.update_btn.setIcon(QIcon("static/icons/update.png"))
        self.update_btn.setIconSize(QSize(20, 20))
        self.update_btn.clicked.connect(self.update_academic_year)
        self.update_btn.setToolTip("Update selected year")
    
        # Delete Year
        self.delete_btn = QPushButton("Delete Year")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setMinimumSize(150, 40)
        self.delete_btn.setIcon(QIcon("static/icons/delete.png"))
        self.delete_btn.setIconSize(QSize(20, 20))
        self.delete_btn.clicked.connect(self.delete_academic_year)
        self.delete_btn.setToolTip("Delete selected year")
    
        # Clear
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("class", "secondary")
        self.clear_btn.setMinimumSize(120, 40)
        self.clear_btn.setIcon(QIcon("static/icons/clear.png"))
        self.clear_btn.setIconSize(QSize(20, 20))
        self.clear_btn.clicked.connect(self.clear_fields)
        self.clear_btn.setToolTip("Clear form fields")
    
        # Layout arrangement
        button_layout.addStretch()
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
    
        parent_layout.addLayout(button_layout)
    
    def setup_year_data_tab(self):
        """Set up data display tab"""
        layout = QVBoxLayout(self.year_data_tab)
        layout.setSpacing(15)
    
        # === SEARCH & ACTIONS BAR ===
        actions_group = QGroupBox("Manage Academic Years")
        actions_group.setFont(self.fonts['section'])
        actions_layout = QHBoxLayout(actions_group)
    
        # Search box
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search by year name...")
        self.search_entry.setFixedWidth(250)
        actions_layout.addWidget(self.search_entry)
    
        # Search button
        search_btn = QPushButton("Search")
        search_btn.setProperty("class", "primary")
        search_btn.setFixedWidth(120)
        search_btn.setIcon(QIcon("static/icons/search.png"))
        search_btn.setIconSize(QSize(20, 20))
        search_btn.clicked.connect(self.search_academic_years_action)
        actions_layout.addWidget(search_btn)
    
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setFixedWidth(120)
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(20, 20))
        clear_btn.clicked.connect(self.clear_search)
        actions_layout.addWidget(clear_btn)
    
        actions_layout.addSpacing(20)
    
        # Export button
        export_btn = QPushButton("Export")
        export_btn.setProperty("class", "info")
        export_btn.setFixedWidth(120)
        export_btn.setIcon(QIcon("static/icons/export.png"))
        export_btn.setIconSize(QSize(20, 20))
        export_btn.clicked.connect(self.export_years_data)
        actions_layout.addWidget(export_btn)
    
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.setFixedWidth(120)
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(20, 20))
        refresh_btn.clicked.connect(self.refresh_data)
        actions_layout.addWidget(refresh_btn)
    
        actions_layout.addStretch()
        layout.addWidget(actions_group)


        # === TABLE ===
        table_group = QGroupBox("All Academic Years")
        table_group.setFont(self.fonts['section'])
        table_layout = QVBoxLayout(table_group)

        self.years_table = QTableWidget()
        self.years_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.years_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.years_table.setSortingEnabled(True)
        self.years_table.verticalHeader().setVisible(False)
        self.years_table.setFont(self.fonts['table'])

        headers = ["ID", "Year Name", "Start Date", "End Date", "Current"]
        self.years_table.setColumnCount(len(headers))
        self.years_table.setHorizontalHeaderLabels(headers)

        table_layout.addWidget(self.years_table)
        layout.addWidget(table_group)

        self.years_table.cellClicked.connect(self.on_year_select)

    def create_styled_label(self, text):
        """Create a styled label using shared fonts and colors"""
        label = QLabel(text)
        label.setFont(self.fonts['label'])
        label.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold;")
        return label

    def validate_fields(self):
        """Validate form fields"""
        if not self.year_name_entry.text().strip():
            QMessageBox.warning(self, "Validation Error", "Year name is required.")
            return False
        if self.start_date_entry.date() >= self.end_date_entry.date():
            QMessageBox.warning(self, "Validation Error", "End date must be after start date.")
            return False
        return True

    def add_academic_year(self):
        """Add a new academic year"""
        if not has_permission(self.user_session, 'create_academic_year'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add academic years.")
            return

        if not self.validate_fields():
            return

        try:
            # Unset current if setting new one
            if self.is_current_checkbox.isChecked():
                self.cursor.execute("UPDATE academic_years SET is_current = FALSE")

            # Insert year
            query = """
                INSERT INTO academic_years (year_name, start_date, end_date, is_current)
                VALUES (%s, %s, %s, %s)
            """
            values = (
                self.year_name_entry.text().strip(),
                self.start_date_entry.date().toPython(),
                self.end_date_entry.date().toPython(),
                self.is_current_checkbox.isChecked()
            )
            self.cursor.execute(query, values)
            year_id = self.cursor.lastrowid
            self.db_connection.commit()

            self.log_audit_action(
                action="CREATE",
                table_name="academic_years",
                record_id=year_id,
                description=f"Created academic year: {values[0]}"
            )

            QMessageBox.information(self, "Success", "Academic year added successfully!")
            self.clear_fields()
            self.load_academic_years()

        except Exception as e:
            self.db_connection.rollback()
            if "Duplicate entry" in str(e):
                QMessageBox.warning(self, "Error", "An academic year with this name already exists.")
            else:
                QMessageBox.critical(self, "Error", f"Failed to add year: {str(e)}")

    def update_academic_year(self):
        """Update selected academic year"""
        if not self.current_year_id:
            QMessageBox.warning(self, "Error", "Please select a year to update.")
            return

        if not has_permission(self.user_session, 'edit_academic_year'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit academic years.")
            return

        if not self.validate_fields():
            return

        try:
            # Unset current if setting new one
            if self.is_current_checkbox.isChecked():
                self.cursor.execute("UPDATE academic_years SET is_current = FALSE")

            # Update year
            query = """
                UPDATE academic_years SET
                    year_name = %s, start_date = %s, end_date = %s,
                    is_current = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            values = (
                self.year_name_entry.text().strip(),
                self.start_date_entry.date().toPython(),
                self.end_date_entry.date().toPython(),
                self.is_current_checkbox.isChecked(),
                self.current_year_id
            )
            self.cursor.execute(query, values)
            self.db_connection.commit()

            self.log_audit_action(
                action="UPDATE",
                table_name="academic_years",
                record_id=self.current_year_id,
                description=f"Updated academic year: {values[0]}"
            )

            QMessageBox.information(self, "Success", "Academic year updated successfully!")
            self.clear_fields()
            self.load_academic_years()

        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update year: {str(e)}")

    def delete_academic_year(self):
        """Delete selected academic year"""
        if not self.current_year_id:
            QMessageBox.warning(self, "Error", "Please select a year to delete.")
            return

        if not has_permission(self.user_session, 'delete_academic_year'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete academic years.")
            return

        # Check dependencies
        self.cursor.execute("SELECT COUNT(*) FROM terms WHERE academic_year_id = %s", (self.current_year_id,))
        term_count = self.cursor.fetchone()[0]
        if term_count > 0:
            QMessageBox.warning(self, "Error", f"Cannot delete: Year has {term_count} terms assigned.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this academic year? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        try:
            # Get year name for audit log
            self.cursor.execute("SELECT year_name FROM academic_years WHERE id = %s", (self.current_year_id,))
            year_name = self.cursor.fetchone()
            year_name = year_name[0] if year_name else "Unknown"

            # Delete year
            self.cursor.execute("DELETE FROM academic_years WHERE id = %s", (self.current_year_id,))
            self.db_connection.commit()

            self.log_audit_action(
                action="DELETE",
                table_name="academic_years",
                record_id=self.current_year_id,
                description=f"Deleted academic year: {year_name}"
            )

            QMessageBox.information(self, "Success", "Academic year deleted successfully!")
            self.clear_fields()
            self.load_academic_years()

        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete year: {str(e)}")

    def clear_fields(self):
        """Reset form fields"""
        self.current_year_id = None
        self.year_name_entry.clear()
        self.start_date_entry.setDate(QDate.currentDate())
        self.end_date_entry.setDate(QDate.currentDate())
        self.is_current_checkbox.setChecked(False)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")

    def load_academic_years(self):
        """Load all academic years into table"""
        try:
            query = """
                SELECT id, year_name, start_date, end_date, is_current
                FROM academic_years
                ORDER BY year_name
            """
            self.cursor.execute(query)
            years = self.cursor.fetchall()
            self.update_years_table(years)
        except Exception as e:
            print(f"Error loading academic years: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load years: {str(e)}")

    def update_years_table(self, years):
        """Update table with year data"""
        self.years_table.setRowCount(len(years))
        headers = ["ID", "Year Name", "Start Date", "End Date", "Current"]
        self.years_table.setHorizontalHeaderLabels(headers)

        for row, year in enumerate(years):
            for col, value in enumerate(year):
                if col == 4:  # is_current
                    text = "Yes" if value else "No"
                elif col in (2, 3) and value:  # dates
                    text = value.strftime("%Y-%m-%d") if hasattr(value, 'strftime') else str(value)
                else:
                    text = str(value) if value is not None else ""
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.years_table.setItem(row, col, item)

        header = self.years_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in [0, 2, 3, 4]:
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

    def on_year_select(self, row, col):
        """Handle year selection"""
        try:
            year_id_item = self.years_table.item(row, 0)
            if not year_id_item:
                return
            self.current_year_id = int(year_id_item.text())
            self.load_year_data(self.current_year_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load year: {str(e)}")

    def load_year_data(self, year_id):
        """Load year data into form"""
        try:
            query = """
                SELECT id, year_name, start_date, end_date, is_current
                FROM academic_years
                WHERE id = %s
            """
            self.cursor.execute(query, (year_id,))
            year = self.cursor.fetchone()
            if not year:
                return

            self.current_year_id = year[0]
            self.year_name_entry.setText(year[1] or "")
            if year[2]:
                self.start_date_entry.setDate(QDate.fromPython(year[2]))
            if year[3]:
                self.end_date_entry.setDate(QDate.fromPython(year[3]))
            self.is_current_checkbox.setChecked(bool(year[4]))

            self.status_label.setText(f"Selected: {year[1]} - Ready to update/delete")
            self.status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
            self.tab_widget.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load year  {str(e)}")

    def search_academic_years_action(self):
        """Trigger search"""
        self.search_academic_years(self.search_entry.text().strip())

    def search_academic_years(self, search_term=""):
        """Search years by name"""
        try:
            if search_term:
                query = """
                    SELECT id, year_name, start_date, end_date, is_current
                    FROM academic_years
                    WHERE year_name LIKE %s
                    ORDER BY year_name
                """
                self.cursor.execute(query, (f"%{search_term}%",))
            else:
                self.load_academic_years()
                return
            years = self.cursor.fetchall()
            self.update_years_table(years)
            if not years:
                QMessageBox.information(self, "Search Results", "No years found matching your search.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Search failed: {str(e)}")

    def clear_search(self):
        """Clear search and reload"""
        self.search_entry.clear()
        self.load_academic_years()

    def refresh_data(self):
        """Refresh data from database with user feedback"""
        try:
            self._ensure_connection()
            self.status_label.setText("Refreshing...")
            self.status_label.setStyleSheet(f"color: {self.colors['warning']}; font-weight: bold;")
            QApplication.processEvents()  # Ensure UI updates immediately
    
            # Perform refresh operations
            self.load_academic_years()
            self.clear_fields()
            self.apply_button_permissions()
    
            # Success feedback
            self.status_label.setText("✅ Data refreshed successfully")
            self.status_label.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
    
            # 👇 ADD THIS: Show success message box
            QMessageBox.information(
                self,
                "Success",
                "Data has been refreshed successfully!",
                QMessageBox.Ok
            )
    
        except Exception as e:
            # Error feedback
            self.status_label.setText("❌ Refresh failed")
            self.status_label.setStyleSheet(f"color: {self.colors['danger']}; font-weight: bold;")
    
            # 👇 ADD THIS: Show error message box
            QMessageBox.critical(
                self,
                "Refresh Failed",
                f"An error occurred while refreshing data:\n\n{str(e)}",
                QMessageBox.Ok
            )

    def export_years_data(self):
        """Export to Excel with green header"""
        try:
            query = """
                SELECT year_name, start_date, end_date, 
                       CASE WHEN is_current THEN 'Yes' ELSE 'No' END
                FROM academic_years
                ORDER BY year_name
            """
            self.cursor.execute(query)
            years = self.cursor.fetchall()
            if not years:
                QMessageBox.information(self, "No Data", "No academic years to export.")
                return

            headers = ['Year Name', 'Start Date', 'End Date', 'Current']
            school_info = self.get_school_info()
            title = f"{school_info['name']} - Academic Years Export"

            self.export_with_green_header(
                data=years,
                headers=headers,
                filename_prefix="academic_years_export",
                title=title
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

    def apply_button_permissions(self):
        """Enable/disable buttons based on user permissions"""
        if not self.user_session:
            return
    
        # Get permissions
        can_create = has_permission(self.user_session, 'create_academic_year')
        can_edit = has_permission(self.user_session, 'edit_academic_year')
        can_delete = has_permission(self.user_session, 'delete_academic_year')
        can_export = has_permission(self.user_session, 'export_academic_years') or has_permission(self.user_session, 'export_all_data')
        can_view = has_permission(self.user_session, 'view_academic_year')
    
        # Enable/disable buttons
        self.add_btn.setEnabled(can_create)
        self.update_btn.setEnabled(can_edit)
        self.delete_btn.setEnabled(can_delete)
    
        # Hide or disable export if not allowed
        # (Assuming you have export_btn in UI)
        if hasattr(self, 'export_btn'):
            self.export_btn.setEnabled(can_export)
    
        # If user can't even view, hide the whole form?
        if not can_view:
            QMessageBox.warning(self, "Access Denied", "You don't have permission to view academic years.")
            self.hide()  # Or disable all controls
            return
    
        # Update tooltips
        self.add_btn.setToolTip("Add year" if can_create else "Permission required: create_academic_year")
        self.update_btn.setToolTip("Update year" if can_edit else "Permission required: edit_academic_year")
        self.delete_btn.setToolTip("Delete year" if can_delete else "Permission required: delete_academic_year")
        if hasattr(self, 'export_btn'):
            self.export_btn.setToolTip("Export data" if can_export else "Permission required: export_academic_years")