# test_classes_form.py
import sys
import traceback
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt

# === GLOBAL EXCEPTION HOOK ===
def handle_exception(exc_type, exc_value, exc_traceback):
    print("💥 UNCAUGHT EXCEPTION:", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
    
    # Show error dialog
    msg = QMessageBox()
    msg.setWindowTitle("Critical Error")
    msg.setText("An unexpected error occurred.")
    msg.setInformativeText(f"{exc_type.__name__}: {exc_value}")
    msg.setIcon(QMessageBox.Critical)
    try:
        msg.setDetailedText(''.join(traceback.format_tb(exc_traceback)))
    except:
        pass
    msg.exec()

sys.excepthook = handle_exception
# =============================

# Mock user session
user_session = {
    'user_id': 1,
    'username': 'admin',
    'role': 'admin',
    'school_id': 1,
    'permissions': ['create', 'update', 'delete']
}

app = QApplication(sys.argv)

try:
    from ui.class_form import ClassesForm

    window = QWidget()
    layout = QVBoxLayout(window)
    
    # Create and add ClassesForm
    form = ClassesForm(parent=window, user_session=user_session)
    layout.addWidget(form)
    
    window.setWindowTitle("Test: ClassesForm")
    window.resize(1000, 700)
    window.show()

    sys.exit(app.exec())

except Exception as e:
    print(f"❌ Top-level error: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")