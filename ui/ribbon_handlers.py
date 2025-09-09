# ui/ribbon_handlers.py
import os
from datetime import datetime
from PySide6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QLinearGradient, QAction, QFont, QCursor 
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, Signal
from PySide6.QtCore import QBuffer, QByteArray, QIODevice


class RibbonHandlers:
    """Handles all ribbon button actions for MainWindow"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.user_session = main_window.user_session
        
    # === USER MANAGEMENT HANDLERS ===
    def open_users_form(self):
        """Open the users management form in dashboard"""
        self.main_window.on_tab_clicked("Dashboard")
        self.main_window.dashboard_tabs.setCurrentIndex(1)
        self.main_window.statusBar().showMessage("User Management - Ready to manage system users")

    def add_new_user(self):
        """Quick action to add a new user"""
        self.main_window.on_tab_clicked("Dashboard")
        self.main_window.dashboard_tabs.setCurrentIndex(1)
        if hasattr(self.main_window, 'users_form'):
            self.main_window.users_form.clear_form()
        self.main_window.statusBar().showMessage("Ready to add new user")

    def refresh_user_data(self):
        """Refresh user data in the dashboard users form"""
        self.main_window.on_tab_clicked("Dashboard")
        self.main_window.dashboard_tabs.setCurrentIndex(1)
        
        if hasattr(self.main_window, 'users_form'):
            try:
                self.main_window.users_form.refresh_data()
                self.main_window.statusBar().showMessage("User data refreshed successfully!")
            except Exception as e:
                self.main_window.statusBar().showMessage(f"Error refreshing user data: {str(e)}")
                QMessageBox.critical(self.main_window, "Refresh Error", f"Failed to refresh user data: {e}")
        else:
            self.main_window.statusBar().showMessage("Users form not available for refresh")
            QMessageBox.warning(self.main_window, "Refresh Failed", "Users form is not initialized")

    def execute_user_export_dialog(self):
        """Open export dialog and safely call users_form.export_users"""
        if not hasattr(self.main_window, 'users_form') or self.main_window.users_form is None:
            QMessageBox.warning(self.main_window, "Error", "User management form not available.")
            return
    
        filename, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Export Users",
            f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;PDF Files (*.pdf);;All Files (*)"
        )
        if not filename:
            return
    
        try:
            success = self.main_window.users_form.export_users(filename)
            if success:
                QMessageBox.information(self.main_window, "Success", f"Users exported to:\n{os.path.basename(filename)}")
                self.main_window.statusBar().showMessage(f"Exported user data to {os.path.basename(filename)}")
            else:
                QMessageBox.critical(self.main_window, "Export Failed", "Could not export data.")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Export Error", f"Failed to export: {str(e)}")

    # === STAFF/TEACHERS HANDLERS ===
    def show_teachers_form(self):
        """Switch to teachers form and ensure it's visible"""
        self.main_window.on_tab_clicked("Staff")
        if hasattr(self.main_window, 'staff_form'):
            self.main_window.staff_form.load_teachers()
    
    def add_new_teacher(self):
        """Prepare the form for adding a new teacher"""
        self.main_window.on_tab_clicked("Staff")
        if hasattr(self.main_window, 'staff_form'):
            self.main_window.staff_form.clear_fields()
            self.main_window.staff_form.tab_widget.setCurrentIndex(0)
    
    def export_teachers_data(self):
        """Export teachers data to Excel"""
        self.main_window.on_tab_clicked("Staff")
        if hasattr(self.main_window, 'staff_form'):
            self.main_window.staff_form.export_teachers_data()

    def import_teachers_data(self):
        """Import teachers data from CSV"""
        self.main_window.on_tab_clicked("Staff")
        if hasattr(self.main_window, 'staff_form'):
            self.main_window.staff_form.import_teachers_data()

    def generate_teacher_summary(self):
        """Generate teacher summary report"""
        self.main_window.on_tab_clicked("Staff")
        if hasattr(self.main_window, 'staff_form'):
            self.main_window.staff_form.generate_teacher_report()
    
    def refresh_teachers_data(self):
        """Refresh teachers data"""
        self.main_window.on_tab_clicked("Staff")
        if hasattr(self.main_window, 'staff_form'):
            self.main_window.staff_form.load_teachers()
            self.main_window.staff_form.load_schools()
            QMessageBox.information(self.main_window, "Refreshed", "Teacher data has been refreshed")
    
    def generate_teacher_profile(self):
        """Generate teacher report from the staff form"""
        if not hasattr(self.main_window, 'staff_form'):
            QMessageBox.warning(self.main_window, "Error", "Staff form not loaded")
            return
        
        teacher_id = getattr(self.main_window.staff_form, 'current_teacher_id', None)
        if not teacher_id:
            QMessageBox.warning(self.main_window, "Warning", "Please select a teacher")
            return
        
        try:
            pdf_bytes = self.main_window.staff_form.generate_teacher_profile_pdf(teacher_id)
            self.main_window.show_pdf_preview_dialog(pdf_bytes)
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to generate PDF:\n{str(e)}")

    # === PARENTS HANDLERS ===
    def show_parents_form(self):
        """Switch to parents form and ensure it's visible"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            self.main_window.parents_form.load_parents()
    
    def add_new_parent(self):
        """Prepare the form for adding a new parent"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            self.main_window.parents_form.clear_fields()
            if hasattr(self.main_window.parents_form, 'tab_widget'):
                self.main_window.parents_form.tab_widget.setCurrentIndex(0)
    
    def refresh_parents_data(self):
        """Show the full refresh options menu when ribbon 'Refresh' is clicked"""
        self.main_window.on_tab_clicked("Parents")
    
        if not hasattr(self.main_window, 'parents_form') or not self.main_window.parents_form:
            QMessageBox.warning(self.main_window, "Unavailable", "Parents module not ready.")
            return
    
        if not hasattr(self.main_window.parents_form, 'refresh_menu'):
            QMessageBox.warning(self.main_window, "Error", "Refresh menu not available.")
            return
    
        # Show the menu at the current cursor position
        menu = self.main_window.parents_form.refresh_menu
        cursor_pos = QCursor.pos()
        menu.exec(cursor_pos)
    
    def import_parents_data(self):
        """Import parents data from CSV"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            try:
                self.main_window.parents_form.import_parents_data()
                self.main_window.statusBar().showMessage("Parent data import initiated")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Import Error", f"Failed to import parent data: {str(e)}")
        else:
            QMessageBox.warning(self.main_window, "Error", "Parents form not available")
    
    def generate_parent_summary(self):
        """Generate parent summary report"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            try:
                self.main_window.parents_form.generate_parent_report()
                self.main_window.statusBar().showMessage("Parent summary report generated")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Report Error", f"Failed to generate parent summary: {str(e)}")
        else:
            QMessageBox.warning(self.main_window, "Error", "Parents form not available")
    
    def generate_parent_profile(self):
        """Generate individual parent profile PDF"""
        if not hasattr(self.main_window, 'parents_form'):
            QMessageBox.warning(self.main_window, "Error", "Parents form not loaded")
            return
        
        parent_id = getattr(self.main_window.parents_form, 'current_parent_id', None)
        if not parent_id:
            QMessageBox.warning(self.main_window, "Warning", "Please select a parent")
            return
        
        try:
            pdf_bytes = self.main_window.parents_form.generate_parent_profile_pdf(parent_id)
            self.main_window.current_pdf_bytes = pdf_bytes
            self.main_window.show_pdf_preview_dialog(pdf_bytes)
            self.main_window.statusBar().showMessage("Parent profile PDF generated")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to generate parent profile PDF: {str(e)}")
    
    def search_parents(self):
        """Open parent search dialog"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            try:
                if hasattr(self.main_window.parents_form, 'show_search_dialog'):
                    self.main_window.parents_form.show_search_dialog()
                else:
                    search_term, ok = QInputDialog.getText(self.main_window, "Search Parents", "Enter parent name or ID:")
                    if ok and search_term:
                        self.main_window.parents_form.search_parents(search_term)
            except Exception as e:
                QMessageBox.critical(self.main_window, "Search Error", f"Failed to search parents: {str(e)}")
        else:
            QMessageBox.warning(self.main_window, "Error", "Parents form not available")
    
    def manage_parent_contacts(self):
        """Manage parent contact information"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            try:
                if hasattr(self.main_window.parents_form, 'manage_contacts'):
                    self.main_window.parents_form.manage_contacts()
                else:
                    QMessageBox.information(self.main_window, "Contacts", "Contact management feature coming soon")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to open contact management: {str(e)}")
        else:
            QMessageBox.warning(self.main_window, "Error", "Parents form not available")
    
    def view_parent_children(self):
        """View children linked to selected parent"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            parent_id = getattr(self.main_window.parents_form, 'current_parent_id', None)
            if not parent_id:
                QMessageBox.warning(self.main_window, "Warning", "Please select a parent first")
                return
            
            try:
                if hasattr(self.main_window.parents_form, 'view_children'):
                    self.main_window.parents_form.view_children(parent_id)
                else:
                    QMessageBox.information(self.main_window, "Children", "Child viewing feature coming soon")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to view parent's children: {str(e)}")
        else:
            QMessageBox.warning(self.main_window, "Error", "Parents form not available")
    
    def backup_parent_data(self):
        """Create backup of parent data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self.main_window,
                "Backup Parent Data",
                f"parents_backup_{timestamp}.sql",
                "SQL Files (*.sql);;All Files (*)"
            )
            
            if filename:
                if hasattr(self.main_window, 'parents_form') and hasattr(self.main_window.parents_form, 'backup_data'):
                    success = self.main_window.parents_form.backup_data(filename)
                    if success:
                        QMessageBox.information(self.main_window, "Backup Complete", f"Parent data backed up to: {filename}")
                        self.main_window.statusBar().showMessage("Parent data backup completed successfully")
                    else:
                        QMessageBox.critical(self.main_window, "Backup Failed", "Failed to create backup")
                else:
                    QMessageBox.information(self.main_window, "Backup", "Backup functionality will be implemented")
                    
        except Exception as e:
            QMessageBox.critical(self.main_window, "Backup Error", f"Failed to backup parent data: {str(e)}")
    
    def validate_parent_data(self):
        """Validate parent data integrity"""
        self.main_window.on_tab_clicked("Parents")
        if hasattr(self.main_window, 'parents_form'):
            try:
                if hasattr(self.main_window.parents_form, 'validate_data'):
                    issues = self.main_window.parents_form.validate_data()
                    if issues:
                        QMessageBox.warning(self.main_window, "Data Issues Found", f"Found {len(issues)} data integrity issues")
                    else:
                        QMessageBox.information(self.main_window, "Validation Complete", "All parent data is valid")
                else:
                    QMessageBox.information(self.main_window, "Validation", "Data validation feature coming soon")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Validation Error", f"Failed to validate data: {str(e)}")
        else:
            QMessageBox.warning(self.main_window, "Error", "Parents form not available")

    # === SECURITY & REPORTS HANDLERS ===
    def show_login_logs(self):
        """Show Login Activity tab directly"""
        from utils.permissions import has_permission
        if not has_permission(self.user_session, "view_login_logs"):
            QMessageBox.warning(self.main_window, "Permission Denied", "You don't have permission to view login logs.")
            return
    
        self.main_window.on_tab_clicked("Dashboard")
        self.main_window.dashboard_tabs.setCurrentIndex(2)
        self.main_window.login_logs_form.load_login_logs()
        self.main_window.statusBar().showMessage("Login activity logs loaded")
    
    def show_audit_logs(self):
        """Show Audit Trail tab directly"""
        from utils.permissions import has_permission
        if not has_permission(self.user_session, "view_audit_logs"):
            QMessageBox.warning(self.main_window, "Permission Denied", "You don't have permission to view audit logs.")
            return
    
        self.main_window.on_tab_clicked("Dashboard")
        self.main_window.dashboard_tabs.setCurrentIndex(3)
        self.main_window.audit_logs_form.load_audit_logs()
        self.main_window.statusBar().showMessage("Audit trail logs loaded")
    
    def generate_security_report(self):
        """Generate security report"""
        self.main_window.on_tab_clicked("Dashboard")
        self.main_window.dashboard_tabs.setCurrentIndex(2)
        QMessageBox.information(self.main_window, "Coming Soon", "Security reports feature will be available in the next update")

    # === GLOBAL SYSTEM HANDLERS ===
    def refresh_all_data(self):
        """Refresh all data across dashboard tabs"""
        current_tab = self.main_window.dashboard_tabs.currentIndex()
        
        if current_tab == 0:  # Overview tab
            if hasattr(self.main_window, 'load_dashboard_stats'):
                self.main_window.load_dashboard_stats()
            self.main_window.statusBar().showMessage("Dashboard overview refreshed!")
        elif current_tab == 1 and hasattr(self.main_window, 'users_form'):  # Users tab
            self.refresh_user_data()
        elif current_tab == 2 and hasattr(self.main_window, 'login_logs_form'):  # Login Logs
            self.main_window.login_logs_form.load_login_logs()
            self.main_window.statusBar().showMessage("Login logs refreshed!")
        elif current_tab == 3 and hasattr(self.main_window, 'audit_logs_form'):  # Audit Logs
            self.main_window.audit_logs_form.load_audit_logs()
            self.main_window.statusBar().showMessage("Audit logs refreshed!")
        else:
            self.main_window.statusBar().showMessage("Refresh completed")

    def settings_action(self):
        """Handle settings action"""
        QMessageBox.information(self.main_window, "Settings", "Settings panel will be implemented here.")

    def new_action(self):
        """Handle new action"""
        QMessageBox.information(self.main_window, "New", "New action triggered from ribbon.")

    def open_action(self):
        """Handle open action"""
        QMessageBox.information(self.main_window, "Open", "Open action triggered from ribbon.")

    def print_action(self):
        """Handle print action"""
        QMessageBox.information(self.main_window, "Print", "Print action triggered from ribbon.")

    # In your ribbon_handlers.py file, add these methods:
    
    def add_new_book(self):
        """Handle adding a new book"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.add_book()
    
    def edit_book(self):
        """Handle editing a book"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.edit_book()
    
    def delete_book(self):
        """Handle deleting a book"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.delete_book()
    
    def refresh_books_data(self):
        """Handle refreshing books data"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.refresh_data()
    
    def export_books_data(self):
        """Handle exporting books data"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.generate_inventory_report()
    
    def import_books_data(self):
        """Handle importing books data"""
        QMessageBox.information(self.main_window, "Import", "Book import functionality will be available soon")
    
    def add_book_category(self):
        """Handle adding a book category"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.add_category()
    
    def manage_book_categories(self):
        """Handle managing book categories"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            # Switch to categories tab if available
            if hasattr(self.main_window.books_management_form, 'tab_widget'):
                self.main_window.books_management_form.tab_widget.setCurrentIndex(1)  # Categories tab
    
    def generate_inventory_report(self):
        """Handle generating inventory report"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.generate_inventory_report()
    
    def generate_category_report(self):
        """Handle generating category report"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.generate_category_report()
    
    def generate_popular_books_report(self):
        """Handle generating popular books report"""
        if hasattr(self.main_window, 'books_management_form') and self.main_window.books_management_form:
            self.main_window.books_management_form.generate_popular_books_report()

    # In your ribbon_handlers.py, add these methods:
    
    def add_health_record(self):
        """Handle adding a health record"""
        if hasattr(self.main_window, 'health_management_form') and self.main_window.health_management_form:
            self.main_window.health_management_form.add_health_record()
    
    def edit_health_record(self):
        """Handle editing a health record"""
        if hasattr(self.main_window, 'health_management_form') and self.main_window.health_management_form:
            self.main_window.health_management_form.edit_health_record()
    
    def delete_health_record(self):
        """Handle deleting a health record"""
        if hasattr(self.main_window, 'health_management_form') and self.main_window.health_management_form:
            self.main_window.health_management_form.delete_health_record()
    
    def refresh_health_data(self):
        """Handle refreshing health data"""
        if hasattr(self.main_window, 'health_management_form') and self.main_window.health_management_form:
            self.main_window.health_management_form.refresh_data()
    
    def export_health_data(self):
        """Handle exporting health data"""
        QMessageBox.information(self.main_window, "Export", "Health data export functionality will be available soon")
    
    def generate_health_report(self):
        """Handle generating health reports"""
        QMessageBox.information(self.main_window, "Reports", "Health reports functionality will be available soon")

    # In your ribbon_handlers.py, add these additional methods:
    
    def view_medication_inventory(self):
        """Handle viewing medication inventory"""
        if hasattr(self.main_window, 'health_management_form') and self.main_window.health_management_form:
            # This will switch to the Medication tab when we implement it
            QMessageBox.information(self.main_window, "Medication", "Medication inventory view will be available soon")
    
    def add_medication(self):
        """Handle adding medication to inventory"""
        QMessageBox.information(self.main_window, "Medication", "Add medication functionality will be available soon")
    
    def check_low_stock(self):
        """Handle checking for low medication stock"""
        QMessageBox.information(self.main_window, "Medication", "Low stock alert functionality will be available soon")
    
    def add_sick_bay_visit(self):
        """Handle adding sick bay visit"""
        QMessageBox.information(self.main_window, "Sick Bay", "Add sick bay visit functionality will be available soon")
    
    def view_active_cases(self):
        """Handle viewing active sick bay cases"""
        QMessageBox.information(self.main_window, "Sick Bay", "Active cases view will be available soon")
    
    def discharge_patient(self):
        """Handle discharging patient from sick bay"""
        QMessageBox.information(self.main_window, "Sick Bay", "Discharge patient functionality will be available soon")