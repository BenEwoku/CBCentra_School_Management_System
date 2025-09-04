#!/usr/bin/env python3
"""
CBCentra School Management System
Main application entry point and source of truth
"""
import sys
import os
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from models.models import get_db_connection, test_connection, check_tables_exist
from ui.main_window import MainWindow
from ui.login_form import LoginForm
import traceback


class CBCentraApplication:
    """Main application controller - Source of Truth"""
    
    def __init__(self):
        # Load environment variables first
        load_dotenv()
        
        self.app = None
        self.main_window = None
        self.db_connection = None
        self.login_form = None
        
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
        
        # User session - will be populated after login
        self.user_session = None  # CHANGED: Start as None
        
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

    def debug_environment(self):
        """Debug environment variables and database connection"""
        print("=== CBCentra Database Debug ===")
        print(f"DB_HOST: {os.getenv('DB_HOST')}")
        print(f"DB_USER: {os.getenv('DB_USER')}")
        print(f"DB_NAME: {os.getenv('DB_NAME')}")
        print(f"DB_PASSWORD: {'*' * len(os.getenv('DB_PASSWORD', ''))}")
        print("==============================")

    def check_database_connection(self):
        """Verify database connectivity before starting UI"""
        try:
            # Show debug info if in debug mode
            if os.getenv('DEBUG', 'False').lower() == 'true':
                self.debug_environment()
            
            # Test connection first
            success, message = test_connection()
            if not success:
                raise Exception(message)
            
            print(f"✅ {message}")
            
            # Get actual connection
            self.db_connection = get_db_connection()
            
            # Check for existing tables
            existing_tables = check_tables_exist(self.db_connection)
            
            if not existing_tables:
                print("No tables found in database!")
                reply = QMessageBox.question(
                    None,
                    "Database Setup Required",
                    "No tables found in the database.\n\n"
                    "Would you like to initialize the database with default tables?\n\n"
                    "This will create: schools, users, teachers, students tables.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    from models.models import initialize_tables
                    print("Creating database tables...")
                    initialize_tables(self.db_connection, force=True)
                    print("✅ Database initialized successfully!")
                else:
                    print("Continuing without database initialization...")
            else:
                print(f"Found {len(existing_tables)} tables: {', '.join(existing_tables)}")
            
            return True
            
        except Exception as e:
            print(f"Database connection error: {e}")
            QMessageBox.critical(
                None, 
                "Database Error",
                f"Failed to connect to database:\n{str(e)}\n\n"
                f"Check your .env file settings:\n"
                f"DB_HOST={os.getenv('DB_HOST')}\n"
                f"DB_USER={os.getenv('DB_USER')}\n"
                f"DB_NAME={os.getenv('DB_NAME')}\n\n"
                f"Application will exit."
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
            
            # Step 4: Show login form first
            if not self.show_login_form():
                return 1
            
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
                    print("Closing database connection...")
                    self.db_connection.close()
                except:
                    pass
                
    def show_login_form(self):
        """Show login form modally"""
        self.login_form = LoginForm()  # Now QDialog
        self.login_form.login_successful.connect(self.on_login_successful)
        self.login_form.setWindowTitle(f"{self.app_config['name']} - Login")
    
        # Center on screen
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - 500) // 2
        y = (screen_geometry.height() - 600) // 2
        self.login_form.setGeometry(x, y, 500, 600)
    
        # Show MODALLY — blocks until accept() or reject()
        result = self.login_form.exec()
    
        # Only proceed if login was successful
        if not self.user_session:
            return False
    
        return True

    def on_login_successful(self, user_session):
        """Handle successful login"""
        try:
            # Store the user session
            self.user_session = user_session
            
            # Close login form
            self.login_form.close()
            self.login_form = None
            
            # Create and show main window
            self.main_window = MainWindow(
                config=self.app_config,
                user_session=self.user_session,
                db_connection=self.db_connection,
                app_paths=self.paths
            )
            
            # Connect main window signals - CORRECTED
            self.main_window.logout_requested.connect(self.on_logout_requested)
            # Connect the signal with the correct method signature
            self.main_window.user_session_updated.connect(self.handle_user_session_update)
            
            self.main_window.show()
            print(f"✅ User {user_session['username']} logged in successfully!")
            
        except Exception as e:
            QMessageBox.critical(None, "Login Error", f"Failed to initialize application: {str(e)}")
            self.app.quit()

    def on_logout_requested(self):
        """Handle logout request from main window"""
        print("Logout requested...")
        
        # Close main window
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        # Clear user session
        self.user_session = None
        
        # Show login form again
        self.show_login_form()

    def handle_user_session_update(self, updated_session):
        """Handle user session updates from main window - CORRECTED METHOD"""
        # This method receives the dict signal from MainWindow
        self.user_session = updated_session
        print(f"User session updated: {updated_session}")

    def get_user_session(self):
        """Provide access to user session data"""
        return self.user_session.copy() if self.user_session else {}
    
    def update_user_session(self, **kwargs):
        """Update user session data from application level"""
        if self.user_session:
            self.user_session.update(kwargs)
            
            # Update main window if it exists
            if self.main_window and hasattr(self.main_window, 'update_user_session'):
                self.main_window.update_user_session(self.user_session)

    def get_database_connection(self):
        """Provide access to database connection"""
        return self.db_connection


def main():
    """Application entry point"""
    print("Starting CBCentra School Management System...")
    
    # Create and run the application
    app = CBCentraApplication()
    exit_code = app.run()
    
    print(f"CBCentra exited with code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()