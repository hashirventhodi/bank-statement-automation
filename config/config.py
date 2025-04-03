import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "config" / "bank_templates"

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "bank_statements"),
    "user": os.getenv("DB_USER", "user"),
    "password": os.getenv("DB_PASSWORD", "password"),
}

# API configuration
API_CONFIG = {
    "secret_key": os.getenv("API_SECRET_KEY", "default-secret-key"),
    "port": int(os.getenv("API_PORT", "8000")),
    "host": "0.0.0.0",
    "debug": os.getenv("DEBUG", "False").lower() == "true",
}

# Google Cloud Vision API
GCV_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# OCR configuration
OCR_CONFIG = {
    "tesseract_cmd": os.getenv("TESSERACT_CMD", "tesseract"),
    "lang": "eng",
    "config": "--psm 6",
}

# ML configuration
ML_CONFIG = {
    "model_dir": os.getenv("ML_MODEL_DIR", "ml/models"),
    "confidence_threshold": 0.8,
}

# Extraction settings
EXTRACTION_CONFIG = {
    "balance_verification_enabled": True,
    "duplicate_detection_enabled": True,
    "ml_extraction_enabled": True,
}

# Bank template settings
BANK_TEMPLATES = {
    # Load all JSON templates from the templates directory
    template_file.stem: Path(template_file).read_text()
    for template_file in TEMPLATES_DIR.glob("*.json")
}
