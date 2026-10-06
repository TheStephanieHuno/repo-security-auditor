import os

target_folder = "backend_app_test"

for root, dirs, files in os.walk(target_folder):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = content.replace("from app.", "from backend_app_test.").replace("import app.", "import backend_app_test.")

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Fixed imports in: {filepath}")

print("All imports updated successfully!")