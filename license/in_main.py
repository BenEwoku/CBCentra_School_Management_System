#Step 4: Use License Check in Your App...Put this in your main app entry point (main.py or app.py)

from app_license import ensure_license_ok

ok, msg = ensure_license_ok("license_masaka.json")
if not ok:
    print(msg)
    # Or show a message box in PySide6 / PyQt
    raise SystemExit(1)
print(msg)

# Continue launching the app...

#====How it works=======

You generate PEM keys → private for signing, public in the app.

For each school, you create a signed license.json using license_tool.py.

App checks license:

Signature is valid

License not expired

Machine is registered

Max devices not exceeded

If everything is OK → app runs.

Activation file tracks the registered machines tamper-evident with HMAC.


#=====Step 5: PySide6 GUI License Check===========

Step 8: Remember License Path

Here’s the updated main.py:

import sys, os, json
from PySide6.QtWidgets import QApplication, QMessageBox, QMainWindow, QFileDialog
from app_license import ensure_license_ok

# File to store last known license path
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Masala School Management System")
        self.resize(800, 600)

        settings = load_settings()
        license_path = settings.get("license_path", None)

        # --- License check on startup ---
        if not license_path or not os.path.exists(license_path):
            self.ask_for_license(settings)
        else:
            ok, msg = ensure_license_ok(license_path)
            if not ok:
                self.ask_for_license(settings)
            else:
                QMessageBox.information(self, "License Status", msg)


        # --- Continue initializing the main app ---
        self.init_ui()

    def init_ui(self):
        # Example placeholder
        pass


# ---------------------------
# Launch the app
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())

🔑 What’s New

settings.json is used to store the last valid license path. Example:

{
  "license_path": "C:/Users/Admin/Desktop/license_masaka.json"
}


On startup:

Tries settings.json → license_path

If missing, tries default license_masala.json

If invalid, asks school to browse for correct file

If valid, saves new path into settings.json

Next time → the app automatically uses the saved license file.