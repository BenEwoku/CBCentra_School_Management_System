#!/usr/bin/env python3
"""
CBCentra School Management System
Main application entry point and source of truth
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from models.models import get_db_connection
from ui.main_window import MainWindow


class CBCentraApplication:
    """Main application controller - Source of Truth"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.db_connection = None
        
        # Application configuration - Source of Truth
        self.app_config = {
            'name': 'CBCentra School Management System',
            'version': '1.0.0',
            'organization': 'CBCentra',
            'window_title': 'CBCentra SMS Desktop',
            'min_size': (1024, 768),
            'default_size': (1200, 700),
            'default_position': (100, 100)
        }
        
        # User session - managed here as source of truth
        self.user_session = {
            'user_id': 1,
            'username': 'admin', 
            'role': 'admin',
            'full_name': 'System Administrator'
        }
        
        # Application paths
        self.paths = {
            'icons': 'static/icons',
            'images': 'static/images',
            'app_icon': 'static/images/programlogo.jpg'
        }

    def initialize_application(self):
        """Initialize the Qt application"""
        self.app = QApplication(sys.argv)
        
        # Set application properties from config
        self.app.setApplicationName(self.app_config['name'])
        self.app.setApplicationVersion(self.app_config['version'])
        self.app.setOrganizationName(self.app_config['organization'])
        
        # Set application icon
        if os.path.exists(self.paths['app_icon']):
            self.app.setWindowIcon(QIcon(self.paths['app_icon']))
        
        return True

    def check_database_connection(self):
        """Verify database connectivity before starting UI"""
        try:
            self.db_connection = get_db_connection()
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()
            cursor.close()
            return True
        except Exception as e:
            QMessageBox.critical(
                None, 
                "Database Error",
                f"Failed to connect to database:\n{str(e)}\n\nApplication will exit."
            )
            return False

    def create_directories(self):
        """Ensure required directories exist"""
        for path in [self.paths['icons'], self.paths['images']]:
            os.makedirs(path, exist_ok=True)

    def create_main_window(self):
        """Create and configure the main window"""
        self.main_window = MainWindow(
            config=self.app_config,
            user_session=self.user_session,
            db_connection=self.db_connection,
            app_paths=self.paths
        )
        return self.main_window

    def run(self):
        """Main application run method - orchestrates everything"""
        try:
            # Step 1: Initialize Qt Application
            if not self.initialize_application():
                return 1
            
            # Step 2: Create required directories
            self.create_directories()
            
            # Step 3: Check database connection
            if not self.check_database_connection():
                return 1
            
            # Step 4: Create and show main window
            main_window = self.create_main_window()
            main_window.show()
            
            # Step 5: Start application event loop
            return self.app.exec()
            
        except Exception as e:
            QMessageBox.critical(
                None,
                "Application Error", 
                f"An unexpected error occurred:\n{str(e)}"
            )
            return 1
        
        finally:
            # Cleanup
            if self.db_connection:
                try:
                    self.db_connection.close()
                except:
                    pass

    def get_user_session(self):
        """Provide access to user session data"""
        return self.user_session.copy()
    
    def update_user_session(self, **kwargs):
        """Update user session data"""
        self.user_session.update(kwargs)
        if self.main_window:
            self.main_window.update_user_session(self.user_session)

    def get_database_connection(self):
        """Provide access to database connection"""
        return self.db_connection


def main():
    """Application entry point"""
    # Create and run the application
    app = CBCentraApplication()
    exit_code = app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()