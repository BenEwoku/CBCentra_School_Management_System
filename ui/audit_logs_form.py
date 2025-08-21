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


class AuditLogsForm(QWidget):
    def __init__(self, parent=None, user_session: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.user_session = user_session

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

    def setup_styling(self):
        """Set up modern professional styling"""
        self.colors = {
            'primary': '#1e40af',
            'primary_dark': '#1e3a8a',
            'secondary': '#475569',
            'success': '#065f46',
            'warning': '#b45309',
            'danger': '#b91c1c',
            'info': '#0e7490',
            'light': '#f1f5f9',
            'dark': '#0f172a',
            'border': '#cbd5e1',
            'text_primary': '#0f172a',
            'text_secondary': '#475569',
            'background': '#ffffff',
            'surface': '#f8fafc',
            'input_background': '#ffffff',
            'input_border': '#94a3b8',
            'input_focus': '#3b82f6',
            'table_header': '#10b981',
            'table_header_dark': '#059669'
        }

        self.fonts = {
            'label': QFont("Arial", 14, QFont.Weight.Bold),
            'entry': QFont("Arial", 14),
            'button': QFont("Arial", 12, QFont.Weight.Bold),
            'header': QFont("Arial", 18, QFont.Weight.Bold),
            'table': QFont("Tahoma", 11),
            'table_header': QFont("Tahoma", 12, QFont.Weight.Bold)
        }

        self.setStyleSheet(f"""
            QWidget {{
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
                color: {self.colors['text_primary']};
                background-color: {self.colors['background']};
            }}
            
            QTableWidget {{
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['background']};
                alternate-background-color: #f8fafc;
                gridline-color: {self.colors['border']};
                selection-background-color: rgba(13, 148, 136, 0.15);
                selection-color: {self.colors['text_primary']};
                font-size: 13px;
            }}
            
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
                color: white;
                padding: 16px;
                border: none;
                font-weight: 700;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            QTabWidget::pane {{
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                background: {self.colors['background']};
            }}
            
            QTabBar::tab {{
                background: {self.colors['light']};
                color: {self.colors['text_secondary']};
                padding: 12px 20px;
                border: 1px solid {self.colors['border']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
                font-weight: 500;
            }}
            
            QTabBar::tab:selected {{
                background: {self.colors['background']};
                color: {self.colors['primary']};
                border-bottom: 2px solid {self.colors['primary']};
                font-weight: 600;
            }}
            
            QTabBar::tab:hover {{
                background: #e2e8f0;
            }}
        """)

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
        """Update the audit logs table with new data"""
        # 🔁 Clear existing content
        self.logs_table.clearContents()  # ✅ Keeps headers, clears data
        self.logs_table.setRowCount(len(logs))
    
        for row, log in enumerate(logs):
            row_data = [
                str(log['id']),
                log['created_at'].strftime('%Y-%m-%d %H:%M:%S') if log['created_at'] else 'N/A',
                log['username'] or 'System',
                log['action'] or 'N/A',
                (log['description'] or 'N/A')[:60] + '...' if log['description'] and len(log['description']) > 60 else (log['description'] or 'N/A'),
                log['table_name'] or 'N/A',
                str(log['record_id']) if log['record_id'] else 'N/A',
                log['ip_address'] or 'N/A',
                (log['user_agent'] or 'N/A')[:50] + '...' if log['user_agent'] and len(log['user_agent']) > 50 else (log['user_agent'] or 'N/A')
            ]
            for col, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
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
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Audit Logs to CSV",
                f"audit_logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV files (*.csv);;All files (*)"
            )
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['ID', 'Timestamp', 'Username', 'Action', 'Description', 'Table',
                                   'Record ID', 'IP Address', 'User Agent'])
                    for row in range(self.logs_table.rowCount()):
                        row_data = [self.logs_table.item(row, col).text() if self.logs_table.item(row, col) else ''
                                    for col in range(self.logs_table.columnCount())]
                        writer.writerow(row_data)
                QMessageBox.information(self, "Success", f"Audit logs exported successfully to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export logs: {e}")

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