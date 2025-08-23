# ui/user_permissions_form.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QLabel, QCheckBox, QMessageBox, QLineEdit,
    QGroupBox, QHeaderView, QSizePolicy, QAbstractItemView
)
from PySide6.QtCore import Qt
from ui.audit_base_form import AuditBaseForm
from utils.permissions import has_permission
from models.models import get_db_connection
from mysql.connector import Error
from PySide6.QtGui import QColor
from datetime import datetime, timedelta


class UserPermissionsForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.all_permissions = []
        self.users = {}
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # === Header: Title + Description (Single Rich Text Label) ===
        header_label = QLabel()
        header_label.setTextFormat(Qt.TextFormat.RichText)
        header_label.setText(
            f"<h2 style='color: {self.colors['primary']}; margin: 0; display: inline;'>"
            f"User-Level Permissions</h2>"
            f"<span style='color: {self.colors['text_secondary']}; font-size: 13px; margin-left: 8px; vertical-align: top;'>"
            f"Grant special permissions to individual users beyond their role. "
            f"Use sparingly for trusted staff or temporary access.</span>"
        )
        header_label.setWordWrap(True)
        header_label.setStyleSheet("padding: 4px 0;")
        layout.addWidget(header_label)

        # === Controls Group ===
        controls_group = QGroupBox("Grant Permission")
        controls_layout = QHBoxLayout(controls_group)

        self.user_combo = QComboBox()
        self.user_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.perm_combo = QComboBox()
        self.perm_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Temporary access dropdown: 1–7 days
        self.days_combo = QComboBox()
        self.days_combo.addItems([f"{i} day{'s' if i > 1 else ''}" for i in range(1, 8)])
        self.days_combo.setCurrentIndex(6)  # Default: 7 days
        self.days_combo.setFixedWidth(120)

        grant_btn = QPushButton("Grant Permission")
        grant_btn.setProperty("class", "success")
        grant_btn.clicked.connect(self.grant_permission)
        grant_btn.setMinimumWidth(140)

        # Add to layout
        controls_layout.addWidget(QLabel("User:"))
        controls_layout.addWidget(self.user_combo, 2)
        controls_layout.addWidget(QLabel("Permission:"))
        controls_layout.addWidget(self.perm_combo, 2)
        controls_layout.addWidget(QLabel("Expires in:"))
        controls_layout.addWidget(self.days_combo)
        controls_layout.addWidget(grant_btn)

        layout.addWidget(controls_group)

        # === Permissions Table ===
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["User", "Permission", "Granted By", "Expires"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.table, 1)  # Expandable

        # === Bottom Controls: Delete Expired + Refresh (Same Line) ===
        bottom_layout = QHBoxLayout()
        
        # Expired Permissions Cleanup
        cleanup_group = QGroupBox("Cleanup Expired Permissions")
        cleanup_layout = QHBoxLayout(cleanup_group)
        
        self.expiry_combo = QComboBox()
        self.expiry_combo.addItems([
            "1 day ago",
            "3 days ago",
            "7 days ago",
            "All Expired"
        ])
        self.expiry_combo.setCurrentIndex(1)  # Default: 3 days
        
        delete_expired_btn = QPushButton("Delete Expired")
        delete_expired_btn.setProperty("class", "danger")
        delete_expired_btn.clicked.connect(self.delete_expired_permissions)
        delete_expired_btn.setMinimumWidth(120)
        
        cleanup_layout.addWidget(QLabel("Remove permissions expired:"))
        cleanup_layout.addWidget(self.expiry_combo)
        cleanup_layout.addWidget(delete_expired_btn)
        
        bottom_layout.addWidget(cleanup_group)
        
        # Add stretch to push refresh to the right
        bottom_layout.addStretch()
        
        # Refresh Button (on same line)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "info")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setMinimumWidth(100)
        
        bottom_layout.addWidget(refresh_btn)
        
        # Add to main layout
        layout.addLayout(bottom_layout)

    def load_data(self):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
    
            # Load users and permissions (your existing code)
            cursor.execute("SELECT id, username, full_name, role FROM users ORDER BY full_name")
            self.users = {row[0]: f"{row[2]} ({row[1]}) - {row[3].title()}" for row in cursor.fetchall()}
    
            self.user_combo.clear()
            for uid, name in self.users.items():
                self.user_combo.addItem(name, userData=uid)
    
            cursor.execute("SELECT DISTINCT permission FROM role_permissions ORDER BY permission")
            self.all_permissions = [row[0] for row in cursor.fetchall()]
    
            self.perm_combo.clear()
            for perm in self.all_permissions:
                self.perm_combo.addItem(perm)
    
            cursor.execute("""
                SELECT up.user_id, up.permission, up.granted_by, up.expires_at, u2.full_name as granted_name
                FROM user_permissions up
                JOIN users u ON u.id = up.user_id
                LEFT JOIN users u2 ON u2.id = up.granted_by
                ORDER BY up.granted_at DESC
            """)
            user_perms = cursor.fetchall()
    
            self.table.setRowCount(len(user_perms))
            # Inside load_data(), in the for loop after fetching user_perms
            for row_idx, (user_id, perm, granted_by, expires, granted_name) in enumerate(user_perms):
                self.table.setItem(row_idx, 0, QTableWidgetItem(self.users.get(user_id, "Unknown")))
                self.table.setItem(row_idx, 1, QTableWidgetItem(perm))
                self.table.setItem(row_idx, 2, QTableWidgetItem(granted_name or "System"))
            
                # === Highlight expiring permissions ===
                if expires:
                    expires_dt = expires  # Already a datetime object from MySQL
                    expires_str = str(expires_dt)
                    
                    item = QTableWidgetItem(expires_str)
                    
                    # Warning: Expires within 2 days
                    if expires_dt < datetime.now() + timedelta(days=2):
                        item.setData(Qt.ForegroundRole, QColor(self.colors['warning']))
                        item.setToolTip("This permission will expire soon!")
                    
                    # Danger: Already expired (but should be cleaned)
                    if expires_dt < datetime.now():
                        item.setData(Qt.ForegroundRole, QColor(self.colors['danger']))
                        item.setToolTip("This permission has expired")
                else:
                    item = QTableWidgetItem("Never")
            
                self.table.setItem(row_idx, 3, item)
                
            conn.close()
    
            # ✅ Critical: Resize and force layout update
            self.table.resizeColumnsToContents()
            self.table.updateGeometry()
            self.table.viewport().update()
    
            # Optional: Scroll to top
            self.table.scrollToTop()
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load  {e}")
        
    def grant_permission(self):
        user_id = self.user_combo.currentData()
        permission = self.perm_combo.currentText()
        selected_days = int(self.days_combo.currentText().split()[0])  # Extract number

        if not user_id or not permission:
            QMessageBox.warning(self, "Input Error", "Please select user and permission.")
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if already granted
            cursor.execute(
                "SELECT 1 FROM user_permissions WHERE user_id = %s AND permission = %s",
                (user_id, permission)
            )
            if cursor.fetchone():
                QMessageBox.warning(self, "Already Granted", "This user already has this permission.")
                return

            # Grant with expiration
            cursor.execute("""
                INSERT INTO user_permissions (user_id, permission, granted_by, expires_at)
                VALUES (%s, %s, %s, DATE_ADD(NOW(), INTERVAL %s DAY))
            """, (user_id, permission, self.user_session.get('user_id'), selected_days))

            conn.commit()
            conn.close()

            self.log_audit_action(
                "GRANT",
                "user_permissions",
                user_id,
                f"Granted permission '{permission}' to {self.users[user_id]} (expires in {selected_days} day(s))"
            )

            QMessageBox.information(
                self, "Success",
                f"Permission '{permission}' granted to user. Expires in {selected_days} day(s)."
            )
            self.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to grant permission: {e}")

    def delete_expired_permissions(self):
        """Manually delete expired permissions based on selected threshold"""
        if not has_permission(self.user_session, "manage_system_settings"):
            QMessageBox.warning(self, "Access Denied", "You don't have permission to manage system settings.")
            return
    
        selection = self.expiry_combo.currentText()  # e.g., "3 days ago"
    
        # Map selection to SQL condition
        if selection == "1 day ago":
            condition = "DATE_SUB(NOW(), INTERVAL 1 DAY)"
        elif selection == "3 days ago":
            condition = "DATE_SUB(NOW(), INTERVAL 3 DAY)"
        elif selection == "7 days ago":
            condition = "DATE_SUB(NOW(), INTERVAL 7 DAY)"
        else:  # "All Expired"
            condition = "'1970-01-01'"  # Anything before now
    
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
    
            # Count before deletion
            count_query = f"""
                SELECT COUNT(*) FROM user_permissions 
                WHERE expires_at IS NOT NULL AND expires_at <= {condition}
            """
            cursor.execute(count_query)
            count = cursor.fetchone()[0]
    
            if count == 0:
                QMessageBox.information(self, "No Expired", "No expired permissions found for the selected period.")
                return
    
            # Confirm deletion
            reply = QMessageBox.question(
                self, "Confirm Deletion",
                f"You are about to delete {count} expired permission(s) that expired {selection}.\n\n"
                "This action cannot be undone. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
    
            # Delete expired
            delete_query = f"""
                DELETE FROM user_permissions 
                WHERE expires_at IS NOT NULL AND expires_at <= {condition}
            """
            cursor.execute(delete_query)
            conn.commit()
            conn.close()
    
            # Log the action
            self.log_audit_action(
                "DELETE",
                "user_permissions",
                None,
                f"Admin deleted {count} expired user permissions (expired {selection})"
            )
    
            QMessageBox.information(self, "Success", f"{count} expired permission(s) removed.")
            self.load_data()  # Refresh table
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete expired permissions: {e}")