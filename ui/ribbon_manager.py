# ui/ribbon_manager.py
import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
    QScrollArea, QFrame, QMessageBox, QFileDialog, QInputDialog,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QIcon, QColor, QCursor 
from PySide6.QtCore import Qt, QSize
from datetime import datetime
from utils.permissions import has_permission


class RibbonManager:
    """Manages ribbon panel creation and updates for MainWindow"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.user_session = main_window.user_session
        self.colors = main_window.colors
        self.fonts = main_window.fonts
        
    def create_ribbon_panel(self):
        """Create the modern ribbon-style panel"""
        self.main_window.ribbon_container = QWidget()
        self.main_window.ribbon_container.setObjectName("ribbonContainer")
        self.main_window.ribbon_container.setFixedHeight(90)
    
        ribbon_layout = QVBoxLayout(self.main_window.ribbon_container)
        ribbon_layout.setContentsMargins(0, 0, 0, 0)
        ribbon_layout.setSpacing(0)
    
        # Scrollable ribbon area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
    
        # Disable default scroll context menu
        scroll_area.setContextMenuPolicy(Qt.NoContextMenu)
        scroll_area.horizontalScrollBar().setContextMenuPolicy(Qt.NoContextMenu)
        scroll_area.verticalScrollBar().setContextMenuPolicy(Qt.NoContextMenu)
    
        # Ribbon panel content
        self.main_window.ribbon_panel = QWidget()
        self.main_window.ribbon_panel.setObjectName("ribbonPanel")
        self.main_window.ribbon_panel_layout = QHBoxLayout(self.main_window.ribbon_panel)
        self.main_window.ribbon_panel_layout.setContentsMargins(10, 3, 10, 5)
        self.main_window.ribbon_panel_layout.setSpacing(8)
    
        scroll_area.setWidget(self.main_window.ribbon_panel)
        ribbon_layout.addWidget(scroll_area)
    
        # Add ribbon to toolbar
        self.main_window.addToolBarBreak(Qt.TopToolBarArea)
        self.main_window.ribbon_toolbar = self.main_window.addToolBar("Ribbon")
        self.main_window.ribbon_toolbar.setMovable(False)
        self.main_window.ribbon_toolbar.addWidget(self.main_window.ribbon_container)
    
        # Initialize ribbon content (Dashboard as default)
        self.update_ribbon_panel("Dashboard")

    def create_ribbon_group(self, title, actions):
        """Create a modern ribbon group with enhanced styling"""
        group = QWidget()
        group.setObjectName("ribbonGroup")
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        group.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Buttons container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(6, 5, 6, 5)
        buttons_layout.setSpacing(3)

        for action in actions:
            btn = QPushButton()
            btn.setObjectName("ribbonButton")
            btn.setToolTip(action["name"])
            
            # Load icon
            icon_path = f"static/icons/{action['icon']}"
            if not os.path.exists(icon_path):
                icon_path = icon_path.replace('.png', '.jpg')
            
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
            else:
                btn.setText(action["name"][:2].upper())
            
            btn.setIconSize(QSize(32, 32))
            if "handler" in action:
                btn.clicked.connect(action["handler"])
            buttons_layout.addWidget(btn)

        layout.addWidget(buttons_container)

        # Group title
        title_label = QLabel(title)
        title_label.setObjectName("ribbonGroupTitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        return group

    def update_ribbon_panel(self, main_tab):
        """Update ribbon panel based on selected tab"""
        # Clear existing content
        while self.main_window.ribbon_panel_layout.count():
            item = self.main_window.ribbon_panel_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
        # Get ribbon groups for the selected tab
        ribbon_groups = self._get_ribbon_groups_for_tab(main_tab)
    
        # Add each group to ribbon panel
        for group in ribbon_groups:
            ribbon_group_widget = self.create_ribbon_group(group["title"], group["actions"])
            self.main_window.ribbon_panel_layout.addWidget(ribbon_group_widget)
    
        self.main_window.ribbon_panel_layout.addStretch()

    def _get_ribbon_groups_for_tab(self, main_tab):
        """Get ribbon groups configuration for each tab"""
        # Get current subtab if Others tab is selected
        current_subtab = None
        if main_tab == "Others" and hasattr(self.main_window, 'others_tabs') and self.main_window.others_tabs:
            current_subtab = self.main_window.others_tabs.tabText(self.main_window.others_tabs.currentIndex())
        
        ribbon_config = {
            "Dashboard": [
                {"title": "View", "actions": [
                    {"name": "Overview", "icon": "overview.png", "handler": lambda: self.main_window.dashboard_tabs.setCurrentIndex(0)},
                    {"name": "Statistics", "icon": "statistics.png"},
                    {"name": "Print", "icon": "print.png", "handler": lambda: self.main_window.dashboard_tabs.setCurrentIndex(2)}
                ]},
                {"title": "User Management", "actions": [
                    {"name": "Manage Users", "icon": "users.png", "handler": lambda: self.main_window.dashboard_tabs.setCurrentIndex(1)},
                    {"name": "Add User", "icon": "adduser.jpg", "handler": self.main_window.add_new_user},
                    {"name": "Export User Data", "icon": "export.png", "handler": self.main_window.execute_user_export_dialog},
                    {"name": "Refresh", "icon": "refresh.png", "handler": self.main_window.refresh_user_data}
                ]},
                {"title": "Security & Reports", "actions": [
                    {"name": "Login Logs", "icon": "security.jpg", "handler": self.main_window.show_login_logs},
                    {"name": "Audit Trail", "icon": "audit.jpg", "handler": self.main_window.show_audit_logs},
                    {"name": "Security Report", "icon": "report_security.jpg", "handler": self.main_window.generate_security_report}
                ]},
                {"title": "Tools", "actions": [
                    {"name": "Settings", "icon": "settings.png", "handler": self.main_window.settings_action},
                    {"name": "Global Refresh", "icon": "refresh.png", "handler": self.main_window.refresh_all_data}
                ]}
            ],
            "Schools": [
                {"title": "Manage", "actions": [
                    {"name": "List Schools", "icon": "info.png"},
                    {"name": "Add New", "icon": "new.jpg"},
                    {"name": "Import", "icon": "import.png"}
                ]},
                {"title": "Configuration", "actions": [
                    {"name": "Settings", "icon": "settings.png"},
                    {"name": "Options", "icon": "options.png"},
                    {"name": "Export", "icon": "export.png"}
                ]}
            ],
            "Staff": [
                {"title": "Staff Records", "actions": [
                    {"name": "Teachers", "icon": "teacher.jpg", "handler": self.main_window.show_teachers_form},
                    {"name": "Add Teacher", "icon": "addstaff.jpg", "handler": self.main_window.add_new_teacher},
                    {"name": "View Teacher Summaries", "icon": "view.png", "handler": self.main_window.generate_teacher_summary}
                ]},
                {"title": "Actions", "actions": [
                    {"name": "Refresh", "icon": "refresh.png", "handler": self.main_window.refresh_teachers_data},
                    {"name": "Generate Teacher Form", "icon": "report.png", "handler": self.main_window.generate_teacher_profile},
                    {"name": "Print", "icon": "print.png"}
                ]},
                {"title": "Import & Export", "actions": [
                    {"name": "Import Teacher Data (CSV)", "icon": "import.png", "handler": self.main_window.import_teachers_data},
                    {"name": "Export Teacher Data (Excel)", "icon": "export.png", "handler": self.main_window.export_teachers_data}
                ]}
            ],
            "Parents": [
                {"title": "Parent Records", "actions": [
                    {"name": "Parents", "icon": "parents.jpg", "handler": self.main_window.show_parents_form},
                    {"name": "Add Parent", "icon": "addparent.jpg", "handler": self.main_window.add_new_parent},
                    {"name": "View Parent Summaries", "icon": "view.png", "handler": self.main_window.generate_parent_summary}
                ]},
                {"title": "Actions", "actions": [
                    {"name": "Refresh", "icon": "refresh.png", "handler": self.main_window.refresh_parents_data},
                    {"name": "Generate Parent Profile", "icon": "report.png", "handler": self.main_window.generate_parent_profile},
                    {"name": "Search Parents", "icon": "search.png", "handler": self.main_window.search_parents}
                ]},
                {"title": "Import & Export", "actions": [
                    {"name": "Import Parent Data", "icon": "import.png", "handler": self.main_window.import_parents_data},
                    {"name": "Export Parent Data", "icon": "export.png"},
                    {"name": "Backup Data", "icon": "backup.png", "handler": self.main_window.backup_parent_data}
                ]},
                {"title": "Tools", "actions": [
                    {"name": "View Children", "icon": "children.png", "handler": self.main_window.view_parent_children},
                    {"name": "Manage Contacts", "icon": "contacts.png", "handler": self.main_window.manage_parent_contacts},
                    {"name": "Validate Data", "icon": "validate.png", "handler": self.main_window.validate_parent_data}
                ]}
            ],
            # ADD THIS SECTION FOR OTHERS TAB WITH BOOKS SUPPORT
            "Others": self._get_others_ribbon_groups(current_subtab)
        }
        
        return ribbon_config.get(main_tab, [
            {"title": "Common", "actions": [
                {"name": "New", "icon": "new.jpg", "handler": self.main_window.new_action},
                {"name": "Open", "icon": "open.jpg", "handler": self.main_window.open_action},
                {"name": "Print", "icon": "print.png", "handler": self.main_window.print_action}
            ]},
            {"title": "Actions", "actions": [
                {"name": "Settings", "icon": "settings.png", "handler": self.main_window.settings_action},
                {"name": "Options", "icon": "options.png"}
            ]}
        ])

    
    def _get_others_ribbon_groups(self, current_subtab):
        """Get ribbon groups for Others tab based on current subtab"""
        if current_subtab == "Books Management":
            # Books-specific ribbon groups
            return [
                {"title": "Books Management", "actions": [
                    {"name": "Add Book", "icon": "add.png", "handler": self.main_window.ribbon_handlers.add_new_book},
                    {"name": "Edit Book", "icon": "edit.png", "handler": self.main_window.ribbon_handlers.edit_book},
                    {"name": "Delete Book", "icon": "delete.png", "handler": self.main_window.ribbon_handlers.delete_book}
                ]},
                {"title": "Data Operations", "actions": [
                    {"name": "Refresh", "icon": "refresh.png", "handler": self.main_window.ribbon_handlers.refresh_books_data},
                    {"name": "Export Books", "icon": "export.png", "handler": self.main_window.ribbon_handlers.export_books_data},
                    {"name": "Import Books", "icon": "import.png", "handler": self.main_window.ribbon_handlers.import_books_data}
                ]},
                {"title": "Categories", "actions": [
                    {"name": "Add Category", "icon": "add_category.png", "handler": self.main_window.ribbon_handlers.add_book_category},
                    {"name": "Manage Categories", "icon": "categories.png", "handler": self.main_window.ribbon_handlers.manage_book_categories}
                ]},
                {"title": "Reports", "actions": [
                    {"name": "Inventory Report", "icon": "report.png", "handler": self.main_window.ribbon_handlers.generate_inventory_report},
                    {"name": "Category Report", "icon": "category_report.png", "handler": self.main_window.ribbon_handlers.generate_category_report},
                    {"name": "Popular Books", "icon": "popular.png", "handler": self.main_window.ribbon_handlers.generate_popular_books_report}
                ]}
            ]
        
        elif current_subtab == "Health Management":  # ADD HEALTH MANAGEMENT SUPPORT
            # Health Management-specific ribbon groups
            return [
                {"title": "Health Records", "actions": [
                    {"name": "New Record", "icon": "add.png", "handler": self.main_window.ribbon_handlers.add_health_record},
                    {"name": "Edit Record", "icon": "edit.png", "handler": self.main_window.ribbon_handlers.edit_health_record},
                    {"name": "Delete Record", "icon": "delete.png", "handler": self.main_window.ribbon_handlers.delete_health_record}
                ]},
                {"title": "Actions", "actions": [
                    {"name": "Refresh", "icon": "refresh.png", "handler": self.main_window.ribbon_handlers.refresh_health_data},
                    {"name": "Export Data", "icon": "export.png", "handler": self.main_window.ribbon_handlers.export_health_data},
                    {"name": "Generate Report", "icon": "report.png", "handler": self.main_window.ribbon_handlers.generate_health_report}
                ]},
                {"title": "Medication", "actions": [
                    {"name": "Inventory", "icon": "medication.png", "handler": self.main_window.ribbon_handlers.view_medication_inventory},
                    {"name": "Add Medication", "icon": "add_medication.png", "handler": self.main_window.ribbon_handlers.add_medication},
                    {"name": "Low Stock Alert", "icon": "alert.png", "handler": self.main_window.ribbon_handlers.check_low_stock}
                ]},
                {"title": "Sick Bay", "actions": [
                    {"name": "New Visit", "icon": "sick_bay.png", "handler": self.main_window.ribbon_handlers.add_sick_bay_visit},
                    {"name": "Active Cases", "icon": "active.png", "handler": self.main_window.ribbon_handlers.view_active_cases},
                    {"name": "Discharge Patient", "icon": "discharge.png", "handler": self.main_window.ribbon_handlers.discharge_patient}
                ]}
            ]
        
        else:
            # Default groups for Other tab when no specific subtab is selected
            return [
                {"title": "Common", "actions": [
                    {"name": "New", "icon": "new.jpg", "handler": self.main_window.new_action},
                    {"name": "Open", "icon": "open.jpg", "handler": self.main_window.open_action},
                    {"name": "Print", "icon": "print.png", "handler": self.main_window.print_action}
                ]},
                {"title": "Actions", "actions": [
                    {"name": "Settings", "icon": "settings.png", "handler": self.main_window.settings_action},
                    {"name": "Options", "icon": "options.png"}
                ]}
            ]
        
    def toggle_ribbon_visibility(self):
        """Toggle ribbon visibility with animation"""
        if self.main_window.ribbon_visible:
            # Hide ribbon
            self.main_window.ribbon_toolbar.setFixedHeight(0)
            self.main_window.ribbon_toggle_btn.setText("▾")
            self.main_window.ribbon_visible = False
        else:
            # Show ribbon
            self.main_window.ribbon_toolbar.setFixedHeight(90)
            self.main_window.ribbon_toggle_btn.setText("▴")
            self.main_window.ribbon_visible = True

    def add_email_actions(self):
        """Add email actions to ribbon"""
        # Add to appropriate ribbon panel (e.g., Dashboard or Others)
        email_group = self.create_action_group("Email", "email.png")
        
        email_group.addAction(
            "Send Email", "send_email.png", 
            lambda: self.main_window.show_email_composer(), 
            "Send email to selected recipients"
        )
        
        email_group.addAction(
            "Check Mail", "refresh.png", 
            lambda: self.main_window.email_notifier._check_incoming_emails(), 
            "Check for new emails"
        )
        
        email_group.addAction(
            "Notification Center", "notification.png", 
            self.main_window.show_notification_center, 
            "View all notifications"
        )
        
        # Add to ribbon panel
        self.add_group_to_panel("Dashboard", email_group)
    
    def add_system_actions(self):
        """Add system actions to ribbon"""
        system_group = self.create_action_group("System", "settings.png")
        
        system_group.addAction(
            "Email Config", "email.png", 
            self.main_window.show_email_config, 
            "Configure email settings"
        )
        
        # Add other system actions...
        
        self.add_group_to_panel("Dashboard", system_group)