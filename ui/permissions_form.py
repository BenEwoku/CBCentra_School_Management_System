# ui/permissions_form.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QGroupBox, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QMessageBox, QFrame, QAbstractItemView, QLineEdit,
    QSizePolicy
)
from PySide6.QtCore import Qt, QMetaObject, Slot
from PySide6.QtGui import QFont
from ui.audit_base_form import AuditBaseForm
from utils.permissions import has_permission
from models.models import get_db_connection
from mysql.connector import Error
import traceback


class PermissionsForm(AuditBaseForm):
    """
    UI for managing role-based permissions.
    Allows admin and headteacher to view and edit permissions via a matrix.
    """

    def __init__(self, parent=None, user_session: dict = None):
        super().__init__(parent, user_session)
        self.role_id_map = {}  # {id: role_name}
        self.role_name_map = {}  # {role_name: id}
        self.all_permissions = []
        self.original_permissions = set()  # (role_id, permission)
        self.current_permissions = set()  # (role_id, permission)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Build the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Combined Title + Description (Single Label)
        header_label = QLabel()
        header_label.setTextFormat(Qt.TextFormat.RichText)
        header_label.setText(
            "<h2 style='color: #007BFF; margin: 0; display: inline;'>Role-Based Permissions Management</h2>"
            "<span style='color: #6c757d; font-size: 13px; margin-left: 8px; vertical-align: top;'>"  
            "Manage what each role can do in the system. Changes are saved immediately. "
            "Only Admin, Headteacher, and Top Level staff (e.g., Directors) can access this."
            "</span>"
        )
        header_label.setWordWrap(True)
        header_label.setStyleSheet("padding: 4px 0;")
        layout.addWidget(header_label)

        # Controls
        controls_layout = QHBoxLayout()

        self.role_filter = QComboBox()
        self.role_filter.addItem("All Roles")
        self.role_filter.currentTextChanged.connect(self.filter_table)

        save_btn = QPushButton("Save Changes")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self.save_permissions)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "info")
        refresh_btn.clicked.connect(self.refresh_data)

        clear_btn = QPushButton("Clear Changes")
        clear_btn.setProperty("class", "warning")
        clear_btn.clicked.connect(self.clear_changes)

        controls_layout.addWidget(QLabel("Filter:"))
        controls_layout.addWidget(self.role_filter)
        controls_layout.addStretch()
        controls_layout.addWidget(clear_btn)
        controls_layout.addWidget(refresh_btn)
        controls_layout.addWidget(save_btn)

        layout.addLayout(controls_layout)

        # Table Group
        table_group = QGroupBox("Permissions Matrix")
        table_layout = QVBoxLayout(table_group)
        
        self.permissions_table = QTableWidget()
        self.permissions_table.setAlternatingRowColors(True)
        self.permissions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.permissions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.permissions_table.horizontalHeader().setStretchLastSection(True)
        self.permissions_table.verticalHeader().setVisible(True)
        self.permissions_table.setSortingEnabled(False)
        
        # 🔧 Make table expand vertically
        self.permissions_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.permissions_table.setMinimumHeight(300)  # Prevent from being too small
        
        table_layout.addWidget(self.permissions_table)
        
        # Add to main layout
        layout.addWidget(table_group)
        
        # ✅ Let this section take available space
        layout.setStretch(layout.indexOf(table_group), 1)

    def load_data(self):
        """Load roles and permissions from database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Load roles
            cursor.execute("SELECT id, role_name FROM roles ORDER BY role_name")
            results = cursor.fetchall()
            self.role_id_map = {row[0]: row[1] for row in results}
            self.role_name_map = {row[1]: row[0] for row in results}

            # Populate filter
            self.role_filter.clear()
            self.role_filter.addItem("All Roles")
            for name in sorted(self.role_name_map.keys()):
                self.role_filter.addItem(name)

            # Load all distinct permissions
            cursor.execute("SELECT DISTINCT permission FROM role_permissions ORDER BY permission")
            self.all_permissions = [row[0] for row in cursor.fetchall()]

            # Load current permissions
            cursor.execute("""
                SELECT role_id, permission FROM role_permissions
            """)
            self.original_permissions = {(role_id, perm) for role_id, perm in cursor.fetchall()}
            self.current_permissions = set(self.original_permissions)  # Start with current

            conn.close()

            self.build_table()

        except Exception as e:
            print(f"Error loading permissions: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")

    def build_table(self):
        """Build the permissions matrix table"""
        self.permissions_table.clear()

        n_roles = len(self.role_id_map)
        n_perms = len(self.all_permissions)

        self.permissions_table.setRowCount(n_roles)
        self.permissions_table.setColumnCount(n_perms + 1)  # +1 for Role column

        # Headers
        header_labels = ["Role"] + [p.replace('_', ' ').title() for p in self.all_permissions]
        self.permissions_table.setHorizontalHeaderLabels(header_labels)

        # Freeze role column
        self.permissions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        # Fill rows
        for row_idx, (role_id, role_name) in enumerate(self.role_id_map.items()):
            # Role name
            role_item = QTableWidgetItem(role_name.title())
            role_item.setFlags(role_item.flags() ^ Qt.ItemIsEditable)
            self.permissions_table.setItem(row_idx, 0, role_item)

            for col_idx, permission in enumerate(self.all_permissions, start=1):
                checkbox = QCheckBox()
                checkbox.setChecked((role_id, permission) in self.current_permissions)
                checkbox.setProperty("role_id", role_id)
                checkbox.setProperty("permission", permission)
                checkbox.stateChanged.connect(self.on_permission_toggled)

                cell_widget = QFrame()
                cell_layout = QHBoxLayout(cell_widget)
                cell_layout.addWidget(checkbox)
                cell_layout.setAlignment(Qt.AlignCenter)
                cell_layout.setContentsMargins(5, 0, 5, 0)
                cell_widget.setLayout(cell_layout)

                self.permissions_table.setCellWidget(row_idx, col_idx, cell_widget)

        self.permissions_table.resizeColumnsToContents()
        self.permissions_table.resizeRowsToContents()

    def on_permission_toggled(self):
        """Track changes when a checkbox is toggled"""
        checkbox = self.sender()
        role_id = checkbox.property("role_id")
        permission = checkbox.property("permission")
        is_checked = checkbox.isChecked()

        perm_tuple = (role_id, permission)
        if is_checked:
            self.current_permissions.add(perm_tuple)
        else:
            self.current_permissions.discard(perm_tuple)

    def save_permissions(self):
        """Save all permission changes to the database"""
        if not has_permission(self.user_session, "manage_system_settings"):
            QMessageBox.warning(self, "Access Denied", "You don't have permission to manage system settings.")
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Delete all and re-insert (simple and safe)
            cursor.execute("DELETE FROM role_permissions")
            for role_id, perm in self.current_permissions:
                cursor.execute(
                    "INSERT INTO role_permissions (role_id, permission) VALUES (%s, %s)",
                    (role_id, perm)
                )
            conn.commit()
            conn.close()

            # Update original state
            self.original_permissions = set(self.current_permissions)

            QMessageBox.information(self, "Success", "All permissions saved successfully!")
            self.log_audit_action(
                action="UPDATE",
                table_name="role_permissions",
                record_id=None,
                description="Updated role-based permissions via UI"
            )

        except Exception as e:
            print(f"Save error: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Save Failed", f"Could not save permissions: {e}")

    def refresh_data(self):
        """Reload all data from the database"""
        reply = QMessageBox.question(
            self, "Confirm Refresh",
            "This will discard unsaved changes. Refresh from database?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        self.load_data()
        QMessageBox.information(self, "Success", "Data refreshed from database.")

    def clear_changes(self):
        """Reset current changes to last saved state"""
        self.current_permissions = set(self.original_permissions)
        self.build_table()
        QMessageBox.information(self, "Cleared", "Unsaved changes have been cleared.")

    def filter_table(self):
        """Filter rows by selected role"""
        filter_text = self.role_filter.currentText()
        if filter_text == "All Roles":
            for row in range(self.permissions_table.rowCount()):
                self.permissions_table.setRowHidden(row, False)
        else:
            for row in range(self.permissions_table.rowCount()):
                item = self.permissions_table.item(row, 0)
                show = item.text().lower() == filter_text.lower()
                self.permissions_table.setRowHidden(row, not show)

    def showEvent(self, event):
        """On tab show, check permission"""
        super().showEvent(event)
        if not has_permission(self.user_session, "manage_system_settings"):
            QMessageBox.warning(self, "Access Denied", "You don't have permission to view this tab.")
            # Try to go back to previous tab
            parent = self.parent()
            if hasattr(parent, 'setCurrentIndex') and hasattr(parent, 'currentIndex'):
                parent.setCurrentIndex(parent.currentIndex() - 1)