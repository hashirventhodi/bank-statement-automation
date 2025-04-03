import os
import magic
import PyPDF2
import pandas as pd
from pathlib import Path
from app.models.statement import StatementFormat
from app.utils.logger import logger

class DocumentAnalyzer:
    """Identifies document format and structure for bank statements."""
    
    def __init__(self, bank_templates):
        self.bank_templates = bank_templates
        
    def identify_format(self, file_path):
        """
        Identify the format of the document.
        """
        file_path = Path(file_path)
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(file_path))
        
        if "pdf" in mime_type:
            return StatementFormat.PDF
        elif "image" in mime_type:
            return StatementFormat.IMAGE
        elif "csv" in mime_type or file_path.suffix.lower() == ".csv":
            return StatementFormat.CSV
        elif "excel" in mime_type or file_path.suffix.lower() in [".xls", ".xlsx"]:
            return StatementFormat.EXCEL
        else:
            logger.warning(f"Unknown format for file: {file_path}")
            return StatementFormat.UNKNOWN
            
    def analyze_structure(self, file_path, file_format):
        """
        Analyzes the structure of the document to identify headers, footers, and transaction tables.
        """
        structure = {
            "bank_name": None,
            "has_header": False,
            "has_footer": False,
            "transaction_table_location": None,
            "summary_section_location": None,
            "detected_template": None
        }
        
        # Analyze based on format
        if file_format == StatementFormat.PDF:
            structure.update(self._analyze_pdf_structure(file_path))
        elif file_format in [StatementFormat.CSV, StatementFormat.EXCEL]:
            structure.update(self._analyze_tabular_structure(file_path, file_format))
        elif file_format == StatementFormat.IMAGE:
            structure["needs_ocr"] = True
        
        return structure
    
    def _analyze_pdf_structure(self, file_path):
        """Analyzes PDF structure to identify bank and layout."""
        structure = {}
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) > 0:
                    first_page_text = reader.pages[0].extract_text().lower()
                    for bank, template in self.bank_templates.items():
                        import json
                        template_data = json.loads(template)
                        identifiers = template_data.get("identifiers", [])
                        if any(identifier.lower() in first_page_text for identifier in identifiers):
                            structure["bank_name"] = bank
                            structure["detected_template"] = template
                            break
                    structure["has_header"] = any(term in first_page_text for term in 
                                                  ["statement", "account", "summary", "bank"])
                    structure["has_footer"] = any(term in first_page_text for term in 
                                                  ["page", "total", "balance", "continued"])
        except Exception as e:
            logger.error(f"Error analyzing PDF structure: {str(e)}")
        return structure
    
    def _analyze_tabular_structure(self, file_path, file_format):
        """Analyzes CSV/Excel structure to identify data patterns."""
        structure = {}
        try:
            if file_format == StatementFormat.CSV:
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            date_cols = [col for col in df.columns if "date" in str(col).lower()]
            if date_cols:
                structure["transaction_table_location"] = "found"
            amount_cols = [col for col in df.columns if any(term in str(col).lower() for term in 
                                                             ["amount", "debit", "credit", "balance"])]
            if amount_cols:
                structure["has_transaction_data"] = True
            header_text = " ".join(str(col) for col in df.columns)
            for bank, template in self.bank_templates.items():
                import json
                template_data = json.loads(template)
                identifiers = template_data.get("identifiers", [])
                if any(identifier.lower() in header_text.lower() for identifier in identifiers):
                    structure["bank_name"] = bank
                    structure["detected_template"] = template
                    break
        except Exception as e:
            logger.error(f"Error analyzing tabular structure: {str(e)}")
        return structure
    
    def get_extraction_strategy(self, file_path):
        """
        Determines the best extraction strategy based on file analysis.
        """
        file_format = self.identify_format(file_path)
        structure = self.analyze_structure(file_path, file_format)
        strategy = {
            "file_format": file_format,
            "structure": structure,
            "recommended_extractor": None,
            "recommended_parser": None
        }
        if file_format == StatementFormat.PDF:
            if structure.get("detected_template"):
                strategy["recommended_extractor"] = "template_pdf_extractor"
            else:
                strategy["recommended_extractor"] = "generic_pdf_extractor"
        elif file_format == StatementFormat.IMAGE:
            strategy["recommended_extractor"] = "ocr_extractor"
        elif file_format == StatementFormat.CSV:
            strategy["recommended_extractor"] = "csv_extractor"
        elif file_format == StatementFormat.EXCEL:
            strategy["recommended_extractor"] = "excel_extractor"
        if structure.get("bank_name") and structure.get("detected_template"):
            strategy["recommended_parser"] = f"{structure['bank_name']}_parser"
        else:
            strategy["recommended_parser"] = "generic_parser"
        return strategy
