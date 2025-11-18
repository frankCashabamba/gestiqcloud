#!/usr/bin/env python3
import re

file_path = "app/modules/pos/interface/http/tenant.py"

with open(file_path, encoding="utf-8") as f:
    content = f.read()

# Find the section and add db.commit()
# Use regex to handle special characters (soft hyphens, etc.)
pattern = r"(receipt_id = row\[0\])\n\n(\s+# Insertar.*?neas)"
replacement = r"\1\n\n        # Commit the receipt insertion to make it visible for RLS policies\n        db.commit()\n\n\2"

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

if new_content != content:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully updated tenant.py")
else:
    print("Pattern not found")
