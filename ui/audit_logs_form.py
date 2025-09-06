# audit_logs_form.py
import sys
import os
import csv
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QFrame, QGroupBox, QComboBox,
    QDateEdit, QProgressDialog, QGridLayout, QTabWidget
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QDate
import mysql.connector
from mysql.connector import Error

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection
from utils.permissions import has_permission
from ui.audit_base_form import AuditBaseForm



class AuditLogsForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)

        # Set up styling
        self.setup_styling()

        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(dictionary=True)
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return

        self.setup_ui()
        self.load_audit_logs()

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

        # Tab 2: Audit Log Table
        self.table_tab = QWidget()
        self.setup_table_tab()
        self.tabs.addTab(self.table_tab, "Audit Log Table")

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

        # Action type
        filter_layout.addWidget(QLabel("Action Type:"), 1, 0)
        self.action_combo = QComboBox()
        self.action_combo.addItems(["All", "CREATE", "UPDATE", "DELETE", "READ", "LOGIN", "LOGOUT"])
        filter_layout.addWidget(self.action_combo, 1, 1)

        # Table filter
        filter_layout.addWidget(QLabel("Table:"), 1, 2)
        self.table_combo = QComboBox()
        self.table_combo.addItems(["All", "users", "teachers", "students", "classes", "subjects"])
        filter_layout.addWidget(self.table_combo, 1, 3)

        # Username filter
        filter_layout.addWidget(QLabel("Username:"), 2, 0)
        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("Filter by username")
        filter_layout.addWidget(self.user_filter, 2, 1)

        # Description filter (new)
        filter_layout.addWidget(QLabel("Description:"), 2, 2)
        self.description_filter = QLineEdit()
        self.description_filter.setPlaceholderText("Search in description")
        filter_layout.addWidget(self.description_filter, 2, 3)

        # Buttons
        filter_btn = self.create_button("Apply Filters", self.colors['primary'], self.apply_filters)
        clear_btn = self.create_button("Clear Filters", self.colors['secondary'], self.clear_filters)
        filter_layout.addWidget(filter_btn, 3, 2)
        filter_layout.addWidget(clear_btn, 3, 3)

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

        self.total_actions_label = QLabel("Total Actions: 0")
        self.create_count_label = QLabel("CREATE: 0")
        self.update_count_label = QLabel("UPDATE: 0")
        self.delete_count_label = QLabel("DELETE: 0")

        for label in [self.total_actions_label, self.create_count_label,
                      self.update_count_label, self.delete_count_label]:
            label.setStyleSheet(f"font-weight: bold; color: {self.colors['text_primary']}; padding: 5px;")
            stats_layout.addWidget(label)

        stats_layout.addStretch()
        layout.addWidget(stats_frame)

        # Action Buttons
        action_layout = QHBoxLayout()
        export_btn = self.create_button("Export to CSV", self.colors['success'], self.export_logs)
        refresh_btn = self.create_button("Refresh", self.colors['info'], self.refresh_data)

        if has_permission(self.user_session, 'delete_audit_logs'):
            delete_btn = self.create_button("Delete Old Logs", self.colors['danger'], self.delete_old_logs)
            action_layout.addWidget(delete_btn)

        action_layout.addWidget(export_btn)
        action_layout.addWidget(refresh_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        layout.addStretch()

    def setup_table_tab(self):
        """Setup the audit log table tab"""
        layout = QVBoxLayout(self.table_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Table
        self.logs_table = QTableWidget()
        self.setup_table()
        layout.addWidget(self.logs_table, 1)

    def setup_table(self):
        """Setup the audit logs table with description"""
        headers = ["ID", "Timestamp", "Username", "Action", "Description", "Table", "Record ID",
                   "IP Address", "User Agent"]
        self.logs_table.setColumnCount(len(headers))
        self.logs_table.setHorizontalHeaderLabels(headers)
        self.logs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.logs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSortingEnabled(True)
        self.logs_table.setFont(self.fonts['table'])
        
        header = self.logs_table.horizontalHeader()
        
        # Set fixed widths for columns that don't need much space
        self.logs_table.setColumnWidth(0, 70)   # ID
        self.logs_table.setColumnWidth(6, 90)   # Record ID
        
        # Set reasonable widths for other columns
        self.logs_table.setColumnWidth(1, 180)  # Timestamp
        self.logs_table.setColumnWidth(2, 160)  # Username
        self.logs_table.setColumnWidth(3, 130)  # Action
        self.logs_table.setColumnWidth(5, 120)  # Table
        self.logs_table.setColumnWidth(7, 130)  # IP Address
        self.logs_table.setColumnWidth(8, 230)  # User Agent
        
        # Make Description column stretch to fill remaining space
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # Allow user to manually resize all columns
        for i in range(len(headers)):
            if i != 4:  # Don't override stretch mode for Description
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

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

    def load_audit_logs(self):
        try:
            # 🔁 Close and reopen cursor if needed
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'db_connection') and self.db_connection.is_connected():
                self.cursor = self.db_connection.cursor(dictionary=True)
            else:
                # Try to reconnect
                self.db_connection = get_db_connection()
                if not self.db_connection:
                    QMessageBox.critical(self, "Database Error", "Cannot reconnect to database")
                    return
                self.cursor = self.db_connection.cursor(dictionary=True)
    
            query = '''
                SELECT al.id, al.created_at, u.username, al.action, al.description,
                       al.table_name, al.record_id,
                       al.ip_address, al.user_agent
                FROM audit_log al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE 1=1
            '''
            params = []
    
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().addDays(1).toString("yyyy-MM-dd")
            query += " AND al.created_at >= %s AND al.created_at < %s"
            params.extend([from_date, to_date])
    
            action = self.action_combo.currentText()
            if action != "All":
                query += " AND al.action = %s"
                params.append(action)
    
            table = self.table_combo.currentText()
            if table != "All":
                query += " AND al.table_name = %s"
                params.append(table)
    
            username_filter = self.user_filter.text().strip()
            if username_filter:
                query += " AND u.username LIKE %s"
                params.append(f"%{username_filter}%")
    
            desc_filter = self.description_filter.text().strip()
            if desc_filter:
                query += " AND al.description LIKE %s"
                params.append(f"%{desc_filter}%")
    
            query += " ORDER BY al.created_at DESC LIMIT 1000"
    
            self.cursor.execute(query, params)
            logs = self.cursor.fetchall()
            self.update_logs_table(logs)
            self.update_statistics(logs)
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load audit logs: {e}")

    def update_logs_table(self, logs):
        """Update the audit logs table with new data and tooltips"""
        # Clear existing content
        self.logs_table.clearContents()  # Keeps headers, clears data
        self.logs_table.setRowCount(len(logs))
    
        for row, log in enumerate(logs):
            # Store original values for tooltips
            original_description = log['description'] or 'N/A'
            original_user_agent = log['user_agent'] or 'N/A'
            original_username = log['username'] or 'System'
            
            row_data = [
                str(log['id']),
                log['created_at'].strftime('%Y-%m-%d %H:%M:%S') if log['created_at'] else 'N/A',
                original_username,
                log['action'] or 'N/A',
                original_description[:60] + '...' if len(original_description) > 60 else original_description,
                log['table_name'] or 'N/A',
                str(log['record_id']) if log['record_id'] else 'N/A',
                log['ip_address'] or 'N/A',
                original_user_agent[:50] + '...' if len(original_user_agent) > 50 else original_user_agent
            ]
            
            for col, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Add comprehensive tooltips for all columns
                tooltip = self.create_tooltip_for_column(col, log, original_description, original_user_agent, original_username)
                if tooltip:
                    item.setToolTip(tooltip)
                
                # Color coding for Action column
                if col == 3:  # Action column
                    if data == 'CREATE':
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['success'])
                    elif data == 'UPDATE':
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['info'])
                    elif data == 'DELETE':
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['danger'])
                
                self.logs_table.setItem(row, col, item)
    
        # Optional: Resize columns to fit content after update
        self.logs_table.resizeColumnsToContents()
    
    def create_tooltip_for_column(self, col, log, original_description, original_user_agent, original_username):
        """Create detailed tooltips for each column"""
        if col == 0:  # ID
            return f"Audit Log ID: {log['id']}"
        
        elif col == 1:  # Timestamp
            if log['created_at']:
                return log['created_at'].strftime('%A, %B %d, %Y at %I:%M:%S %p')
            return "No timestamp available"
        
        elif col == 2:  # Username
            tooltip_parts = [f"User: {original_username}"]
            if log.get('user_id'):
                tooltip_parts.append(f"User ID: {log['user_id']}")
            return "\n".join(tooltip_parts)
        
        elif col == 3:  # Action
            action_descriptions = {
                'CREATE': 'Created a new record',
                'UPDATE': 'Modified an existing record', 
                'DELETE': 'Deleted a record',
                'READ': 'Accessed/viewed data',
                'LOGIN': 'User logged into system',
                'LOGOUT': 'User logged out of system'
            }
            action = log['action'] or 'N/A'
            base_tip = f"Action: {action}"
            if action in action_descriptions:
                base_tip += f"\n{action_descriptions[action]}"
            return base_tip
        
        elif col == 4:  # Description - Most important for your use case
            if original_description and original_description != 'N/A':
                # Add formatting for better readability
                formatted_desc = original_description.replace(';', '\n•').replace(':', ':\n  ')
                return f"Full Description:\n{formatted_desc}"
            return "No description available"
        
        elif col == 5:  # Table
            return f"Database Table: {log['table_name'] or 'N/A'}"
        
        elif col == 6:  # Record ID  
            return f"Record ID: {log['record_id'] or 'N/A'}"
        
        elif col == 7:  # IP Address
            ip = log['ip_address'] or 'N/A'
            tooltip_parts = [f"IP Address: {ip}"]
            # You could add geolocation info here if available
            if ip and ip != 'N/A' and ip != '127.0.0.1':
                tooltip_parts.append("(External IP)")
            elif ip == '127.0.0.1':
                tooltip_parts.append("(Local/System)")
            return "\n".join(tooltip_parts)
        
        elif col == 8:  # User Agent
            if original_user_agent and original_user_agent != 'N/A':
                # Parse user agent for better display
                return f"Full User Agent:\n{original_user_agent}"
            return "No user agent information"
        
        return None

    def update_statistics(self, logs):
        total = len(logs)
        create_count = sum(1 for log in logs if log['action'] == 'CREATE')
        update_count = sum(1 for log in logs if log['action'] == 'UPDATE')
        delete_count = sum(1 for log in logs if log['action'] == 'DELETE')
        self.total_actions_label.setText(f"Total Actions: {total}")
        self.create_count_label.setText(f"CREATE: {create_count}")
        self.update_count_label.setText(f"UPDATE: {update_count}")
        self.delete_count_label.setText(f"DELETE: {delete_count}")

    def apply_filters(self):
        self.load_audit_logs()

    def clear_filters(self):
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.action_combo.setCurrentText("All")
        self.table_combo.setCurrentText("All")
        self.user_filter.clear()
        self.description_filter.clear()
        self.load_audit_logs()

    def export_logs(self):
        """Export audit logs with the green header style"""
        try:
            # Get the full data
            query = '''
                SELECT al.id, al.created_at, u.username, al.action, al.description,
                       al.table_name, al.record_id,
                       al.ip_address, al.user_agent
                FROM audit_log al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE 1=1
            '''
            params = []
            
            # Apply the same filters
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().addDays(1).toString("yyyy-MM-dd")
            query += " AND al.created_at >= %s AND al.created_at < %s"
            params.extend([from_date, to_date])
    
            action = self.action_combo.currentText()
            if action != "All":
                query += " AND al.action = %s"
                params.append(action)
    
            table = self.table_combo.currentText()
            if table != "All":
                query += " AND al.table_name = %s"
                params.append(table)
    
            username_filter = self.user_filter.text().strip()
            if username_filter:
                query += " AND u.username LIKE %s"
                params.append(f"%{username_filter}%")
    
            desc_filter = self.description_filter.text().strip()
            if desc_filter:
                query += " AND al.description LIKE %s"
                params.append(f"%{desc_filter}%")
    
            query += " ORDER BY al.created_at DESC"
    
            self.cursor.execute(query, params)
            logs = self.cursor.fetchall()
    
            if not logs:
                QMessageBox.information(self, "No Data", "No audit logs found to export.")
                return
    
            # Prepare data for export - convert to list of lists
            export_data = []
            for log in logs:
                row_data = [
                    log['id'],
                    log['created_at'].strftime('%Y-%m-%d %H:%M:%S') if log['created_at'] else 'N/A',
                    log['username'] or 'System',
                    log['action'] or 'N/A',
                    log['description'] or 'N/A',
                    log['table_name'] or 'N/A',
                    str(log['record_id']) if log['record_id'] else 'N/A',
                    log['ip_address'] or 'N/A',
                    log['user_agent'] or 'N/A'
                ]
                export_data.append(row_data)
    
            # Define headers
            headers = [
                "ID", "Timestamp", "Username", "Action", "Description", 
                "Table", "Record ID", "IP Address", "User Agent"
            ]
    
            # Get school name for title
            school_info = self.get_school_info()
            
            # Include date range in the title
            title = (f"{school_info['name']} - AUDIT LOGS\n"
                     f"Date Range: {self.from_date.date().toString('yyyy-MM-dd')} "
                     f"to {self.to_date.date().toString('yyyy-MM-dd')}")
    
            # Use shared export method
            self.export_with_green_header(
                data=export_data,
                headers=headers,
                filename_prefix="audit_logs_export",
                title=title
            )
    
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export audit logs:\n{str(e)}")
        
    def delete_old_logs(self):
        if not has_permission(self.user_session, 'delete_audit_logs'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete audit logs.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete audit logs older than 1 year?\n\n"
            "This action is irreversible and affects compliance records!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                cutoff_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                query = "DELETE FROM audit_log WHERE created_at < %s"
                self.cursor.execute(query, (cutoff_date,))
                deleted_count = self.cursor.rowcount
                self.db_connection.commit()

                # Log this deletion action
                audit_query = """
                    INSERT INTO audit_log 
                    (user_id, action, description, table_name, ip_address, user_agent)
                    VALUES (%s, 'DELETE', %s, 'audit_log', %s, %s)
                """
                self.cursor.execute(audit_query, (
                    self.user_session.get('user_id'),
                    'Deleted old audit logs older than 1 year',
                    self.user_session.get('ip_address', '127.0.0.1'),
                    'System cleanup tool'
                ))
                self.db_connection.commit()

                QMessageBox.information(self, "Success", f"Deleted {deleted_count} old audit logs!")
                self.load_audit_logs()
            except Error as e:
                QMessageBox.critical(self, "Error", f"Failed to delete old logs: {e}")

    def refresh_data(self):
        #force
        self.db_connection.commit()
        self.load_audit_logs()
        self.logs_table.viewport().update()  # ✅ Fixed
        QMessageBox.information(self, "Success", "Audit data refreshed successfully!")

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