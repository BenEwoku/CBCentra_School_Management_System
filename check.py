import os
from pathlib import Path
import shutil

# Path to your .ui folder
ui_folder = Path(r"F:\projects\cbcentra\ui")

# Make a backup folder
backup_folder = ui_folder / "backup_ui_files"
backup_folder.mkdir(exist_ok=True)

# Iterate through all .ui files
for ui_file in ui_folder.rglob("*.ui"):
    # Backup original file
    shutil.copy(ui_file, backup_folder / ui_file.name)

    # Read lines
    with open(ui_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Remove lines containing 'user_session'
    new_lines = [line for line in lines if "user_session" not in line]

    # Write back cleaned file
    with open(ui_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"✅ Cleaned {ui_file.name}, backup saved.")
