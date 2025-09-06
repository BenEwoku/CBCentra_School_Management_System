# login_logs_form.py
import sys
import os
import csv
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QComboBox, QTabWidget, QDateEdit
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, QDate

import mysql.connector
from mysql.connector import Error
from utils.permissions import has_permission

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection
from ui.audit_base_form import AuditBaseForm



class LoginLogsForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)

        # Set up styling
        self.setup_styling()

        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor()
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return

        self.setup_ui()
        self.load_login_logs()

    def setup_ui(self):
        """Setup the main UI with two tabs"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(15)


        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)

        # Tab 1: Summary & Filters
        self.summary_tab = QWidget()
        self.setup_summary_tab()
        self.tabs.addTab(self.summary_tab, "Summary & Filters")

        # Tab 2: Login Logs Table
        self.table_tab = QWidget()
        self.setup_table_tab()
        self.tabs.addTab(self.table_tab, "Login Logs Table")

        # Add icons to tabs (optional)
        if os.path.exists("static/icons/security.jpg"):
            self.tabs.setTabIcon(0, QIcon("static/icons/security.jpg"))
            self.tabs.setTabIcon(1, QIcon("static/icons/table.jpg"))

        main_layout.addWidget(self.tabs)

    def setup_summary_tab(self):
        """Setup the summary and filter tab"""
        layout = QVBoxLayout(self.summary_tab)
        layout.setSpacing(15)

        # Filter controls
        filter_group = QGroupBox("Filter Options")
        filter_group.setFont(self.fonts['label'])
        filter_layout = QGridLayout(filter_group)

        # Date range
        filter_layout.addWidget(QLabel("From Date:"), 0, 0)
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setCalendarPopup(True)
        filter_layout.addWidget(self.from_date, 0, 1)

        filter_layout.addWidget(QLabel("To Date:"), 0, 2)
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        filter_layout.addWidget(self.to_date, 0, 3)

        # Status filter
        filter_layout.addWidget(QLabel("Login Status:"), 1, 0)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Success", "Failed", "Locked"])
        filter_layout.addWidget(self.status_combo, 1, 1)

        # Username filter
        filter_layout.addWidget(QLabel("Username:"), 1, 2)
        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("Filter by username")
        filter_layout.addWidget(self.user_filter, 1, 3)

        # Buttons
        filter_btn = self.create_button("Apply Filters", self.colors['primary'], self.apply_filters)
        clear_btn = self.create_button("Clear Filters", self.colors['secondary'], self.clear_filters)
        filter_layout.addWidget(filter_btn, 2, 0, 1, 2)
        filter_layout.addWidget(clear_btn, 2, 2, 1, 2)

        layout.addWidget(filter_group)

        # Statistics
        stats_frame = QFrame()
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        stats_frame.setStyleSheet(f"""
            background: {self.colors['surface']};
            border: 1px solid {self.colors['border']};
            border-radius: 8px;
            padding: 10px;
        """)

        self.total_logins_label = QLabel("Total Logins: 0")
        self.successful_logins_label = QLabel("Successful: 0")
        self.failed_logins_label = QLabel("Failed: 0")
        self.locked_logins_label = QLabel("Locked: 0")

        for label in [self.total_logins_label, self.successful_logins_label,
                      self.failed_logins_label, self.locked_logins_label]:
            label.setStyleSheet(f"font-weight: bold; color: {self.colors['text_primary']}; padding: 5px;")
            stats_layout.addWidget(label)

        stats_layout.addStretch()
        layout.addWidget(stats_frame)

        # Action Buttons
        action_layout = QHBoxLayout()
        export_btn = self.create_button("Export to CSV", self.colors['success'], self.export_logs)
        refresh_btn = self.create_button("Refresh", self.colors['info'], self.refresh_data)
        delete_btn = self.create_button("Delete Old Logs", self.colors['danger'], self.delete_old_logs)

        action_layout.addWidget(export_btn)
        action_layout.addWidget(refresh_btn)
        action_layout.addWidget(delete_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        layout.addStretch()

    def setup_table_tab(self):
        """Setup the login logs table tab"""
        layout = QVBoxLayout(self.table_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Table
        self.logs_table = QTableWidget()
        self.setup_table()
        layout.addWidget(self.logs_table, 1)

    def setup_table(self):
        """Setup the login logs table"""
        headers = ["ID", "Username", "Login Time", "Logout Time", "Status",
                   "Failure Reason", "IP Address", "Device", "User Agent"]
        self.logs_table.setColumnCount(len(headers))
        self.logs_table.setHorizontalHeaderLabels(headers)

        self.logs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.logs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSortingEnabled(True)
        self.logs_table.setFont(self.fonts['table'])

        header = self.logs_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)

    def create_button(self, text, color, callback):
        button = QPushButton(text)
        button.setFont(self.fonts['button'])
        button.clicked.connect(callback)
        button.setMinimumHeight(35)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color_brightness(color, -20)};
            }}
        """)
        return button

    def adjust_color_brightness(self, color, amount):
        if color.startswith('#'):
            color = color[1:]
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        return f"#{r:02x}{g:02x}{b:02x}"

    def load_login_logs(self):
        try:
            query = '''
                SELECT ll.id, u.username, ll.login_time, ll.logout_time, 
                       ll.login_status, ll.failure_reason, ll.ip_address, 
                       ll.device, ll.user_agent
                FROM login_logs ll
                LEFT JOIN users u ON ll.user_id = u.id
                WHERE 1=1
            '''
            params = []

            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().addDays(1).toString("yyyy-MM-dd")
            query += " AND ll.login_time >= %s AND ll.login_time < %s"
            params.extend([from_date, to_date])

            status = self.status_combo.currentText()
            if status != "All":
                if status == "Success":
                    query += " AND ll.login_status = 'success'"
                elif status == "Failed":
                    query += " AND ll.login_status = 'failed'"
                elif status == "Locked":
                    query += " AND ll.login_status = 'locked'"

            username_filter = self.user_filter.text().strip()
            if username_filter:
                query += " AND u.username LIKE %s"
                params.append(f"%{username_filter}%")

            query += " ORDER BY ll.login_time DESC LIMIT 1000"

            self.cursor.execute(query, params)
            logs = self.cursor.fetchall()
            self.update_logs_table(logs)
            self.update_statistics(logs)

        except Error as e:
            QMessageBox.critical(self, "Error", f"Failed to load login logs: {e}")

    def update_logs_table(self, logs):
        self.logs_table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            row_data = [
                str(log[0]), log[1] or 'N/A',
                log[2].strftime('%Y-%m-%d %H:%M:%S') if log[2] else 'N/A',
                log[3].strftime('%Y-%m-%d %H:%M:%S') if log[3] else 'N/A',
                log[4] or 'N/A', log[5] or 'N/A',
                log[6] or 'N/A', log[7] or 'N/A', log[8] or 'N/A'
            ]
            for col, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 4:  # Status
                    if data.lower() == 'success':
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['success'])
                    elif data.lower() in ['failed', 'locked']:
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['danger'])
                self.logs_table.setItem(row, col, item)

    def update_statistics(self, logs):
        total = len(logs)
        successful = sum(1 for log in logs if log[4] and log[4].lower() == 'success')
        failed = sum(1 for log in logs if log[4] and log[4].lower() == 'failed')
        locked = sum(1 for log in logs if log[4] and log[4].lower() == 'locked')

        self.total_logins_label.setText(f"Total Logins: {total}")
        self.successful_logins_label.setText(f"Successful: {successful}")
        self.failed_logins_label.setText(f"Failed: {failed}")
        self.locked_logins_label.setText(f"Locked: {locked}")

    def apply_filters(self):
        self.load_login_logs()

    def clear_filters(self):
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.status_combo.setCurrentText("All")
        self.user_filter.clear()
        self.load_login_logs()

    def export_logs(self):
        """Export login logs with the green header style"""
        try:
            query = '''
                SELECT ll.id, u.username, ll.login_time, ll.logout_time, 
                       ll.login_status, ll.failure_reason, ll.ip_address, 
                       ll.device, ll.user_agent
                FROM login_logs ll
                LEFT JOIN users u ON ll.user_id = u.id
                WHERE 1=1
            '''
            params = []
    
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().addDays(1).toString("yyyy-MM-dd")
            query += " AND ll.login_time >= %s AND ll.login_time < %s"
            params.extend([from_date, to_date])
    
            status = self.status_combo.currentText()
            if status != "All":
                if status == "Success":
                    query += " AND ll.login_status = 'success'"
                elif status == "Failed":
                    query += " AND ll.login_status = 'failed'"
                elif status == "Locked":
                    query += " AND ll.login_status = 'locked'"
    
            username_filter = self.user_filter.text().strip()
            if username_filter:
                query += " AND u.username LIKE %s"
                params.append(f"%{username_filter}%")
    
            query += " ORDER BY ll.login_time DESC"
    
            self.cursor.execute(query, params)
            logs = self.cursor.fetchall()
    
            if not logs:
                QMessageBox.information(self, "No Data", "No login logs found to export.")
                return
    
            # Prepare data for export - convert to list of lists
            export_data = []
            for log in logs:
                row_data = [
                    log[0],  # ID
                    log[1] or 'N/A',  # Username
                    log[2].strftime('%Y-%m-%d %H:%M:%S') if log[2] else 'N/A',  # Login Time
                    log[3].strftime('%Y-%m-%d %H:%M:%S') if log[3] else 'N/A',  # Logout Time
                    log[4] or 'N/A',  # Status
                    log[5] or 'N/A',  # Failure Reason
                    log[6] or 'N/A',  # IP Address
                    log[7] or 'N/A',  # Device
                    log[8] or 'N/A'   # User Agent
                ]
                export_data.append(row_data)
    
            # Define headers
            headers = [
                "ID", "Username", "Login Time", "Logout Time", "Status",
                "Failure Reason", "IP Address", "Device", "User Agent"
            ]
    
            # Get school name for title
            school_info = self.get_school_info()
            
            # Include date range in the title
            title = (f"{school_info['name']} - LOGIN LOGS\n"
                     f"Date Range: {self.from_date.date().toString('yyyy-MM-dd')} "
                     f"to {self.to_date.date().toString('yyyy-MM-dd')}")
    
            # Use shared export method
            self.export_with_green_header(
                data=export_data,
                headers=headers,
                filename_prefix="login_logs_export",
                title=title
            )
    
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export login logs:\n{str(e)}")

    def delete_old_logs(self):
        if not has_permission(self.user_session, 'delete_login_logs'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete login logs.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete login logs older than 90 days?\n\n"
            "This action is irreversible!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                query = "DELETE FROM login_logs WHERE login_time < %s"
                self.cursor.execute(query, (cutoff_date,))
                deleted_count = self.cursor.rowcount
                self.db_connection.commit()

                if self.user_session:
                    audit_query = """
                        INSERT INTO audit_log (user_id, action, table_name, description)
                        VALUES (%s, 'DELETE', 'login_logs', %s)
                    """
                    self.cursor.execute(audit_query, (
                        self.user_session.get('user_id'),
                        f"Deleted {deleted_count} login logs older than {cutoff_date}"
                    ))
                    self.db_connection.commit()

                QMessageBox.information(self, "Success", f"Deleted {deleted_count} old login logs!")
                self.load_login_logs()
            except Error as e:
                QMessageBox.critical(self, "Error", f"Failed to delete old logs: {e}")

    def refresh_data(self):
        """Refresh data from database"""
        try:
            # Ensure connection is alive
            self._ensure_connection()
            self.db_connection.commit()
            
            # Reload the logs
            self.load_login_logs()
            
            # Show success message
            QMessageBox.information(self, "Success", "Data refreshed successfully!")
            
        except Exception as e:
            # Handle any error during refresh
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {str(e)}")

    def closeEvent(self, event):
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'db_connection'):
                self.db_connection.close()
        except:
            pass
        event.accept()

    def __del__(self):
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'db_connection'):
                self.db_connection.close()
        except:
            pass