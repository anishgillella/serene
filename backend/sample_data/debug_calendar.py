
import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.db_service import DEFAULT_RELATIONSHIP_ID as DB_DEFAULT
from app.services.calendar_service import DEFAULT_RELATIONSHIP_ID as CAL_DEFAULT

print(f"DB_DEFAULT: {DB_DEFAULT}")
print(f"CAL_DEFAULT: {CAL_DEFAULT}")

if DB_DEFAULT == "default":
    print("❌ DB_DEFAULT is 'default'")
if CAL_DEFAULT == "default":
    print("❌ CAL_DEFAULT is 'default'")

if DB_DEFAULT != CAL_DEFAULT:
    print("❌ Mismatch between DB and CAL defaults")
