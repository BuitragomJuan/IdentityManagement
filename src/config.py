from pathlib import Path

# API CONFIG
API_URL = "https://jsonplaceholder.typicode.com/users" #API that holds  the external contractors data in JSON format
API_TIMEOUT = 10  # Timeout in seconds for API requests


# LOG / Output
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_FILE = OUTPUT_DIR / "DemoCompanyApp.log"  # Log file name stored in output directory
LOG_LEVEL = "INFO"


# email generation config
EMAIL_DOMAIN = "democompany.com"  # Domain for generated email addresses


# csv file output
CSV_FILE = OUTPUT_DIR / "external_contractors.csv"