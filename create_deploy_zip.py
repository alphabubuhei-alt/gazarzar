import zipfile
import os
import shutil

frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
output_zip = os.path.join(os.path.dirname(__file__), 'gazarzar_deploy.zip')

# Remove old zip if exists
if os.path.exists(output_zip):
    os.remove(output_zip)

with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(frontend_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, frontend_dir)
            zf.write(file_path, arcname)

size_kb = os.path.getsize(output_zip) / 1024
print(f"\nSUCCESS: Deploy ZIP created!")
print(f"File: gazarzar_deploy.zip ({size_kb:.1f} KB)")
print(f"Path: {output_zip}")
print(f"\nNEXT STEPS:")
print(f"  1. Open browser: https://app.netlify.com/drop")
print(f"  2. Drag 'gazarzar_deploy.zip' onto the page")
print(f"  3. You will get a free public URL in seconds!")

