from typing import Dict, List, Any, Optional
import requests
import json
from datetime import datetime
from app.utils.logger import logger
from app.models.transaction import Transaction
from app.models.account import Account

class TallyIntegration:
    """Integration with Tally accounting software."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Tally integration.
        
        Args:
            config: Configuration dictionary with connection details
        """
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 9000)
        self.company = config.get("company")
        self.base_url = f"http://{self.host}:{self.port}"
    
    def export_transactions(self, transactions: List[Transaction], account: Account) -> Dict[str, Any]:
        """
        Export transactions to Tally.
        
        Args:
            transactions: List of transactions to export
            account: Account details for mapping
            
        Returns:
            Dict with export results
        """
        try:
            # Prepare Tally XML request
            xml_request = self._prepare_xml_request(transactions, account)
            
            # Send to Tally
            response = self._send_to_tally(xml_request)
            
            # Process response
            return self._process_response(response)
            
        except Exception as e:
            logger.error(f"Error exporting to Tally: {str(e)}")
            raise
    
    def _prepare_xml_request(self, transactions: List[Transaction], account: Account) -> str:
        """Prepare XML request for Tally."""
        # Start XML envelope
        xml = """<ENVELOPE>
                    <HEADER>
                        <VERSION>1</VERSION>
                        <TALLYREQUEST>Import</TALLYREQUEST>
                        <TYPE>Data</TYPE>
                        <ID>Vouchers</ID>
                    </HEADER>
                    <BODY>
                        <IMPORTDATA>
                            <REQUESTDESC>
                                <REPORTNAME>Vouchers</REPORTNAME>
                                <STATICVARIABLES>
                                    <SVCURRENTCOMPANY>""" + str(self.company) + """</SVCURRENTCOMPANY>
                                </STATICVARIABLES>
                            </REQUESTDESC>
                            <REQUESTDATA>"""
        
        # Add vouchers for each transaction
        for tx in transactions:
            voucher = self._transaction_to_voucher(tx, account)
            xml += voucher
            
        # Close XML envelope
        xml += """        </REQUESTDATA>
                    </IMPORTDATA>
                </BODY>
            </ENVELOPE>"""
        
        return xml
    
    def _transaction_to_voucher(self, transaction: Transaction, account: Account) -> str:
        """Convert transaction to Tally voucher XML."""
        # Determine voucher type
        voucher_type = "Receipt" if transaction.transaction_type == "credit" else "Payment"
        
        # Format date for Tally
        tally_date = datetime.strptime(transaction.date, "%d/%m/%Y").strftime("%Y%m%d")
        
        # Create voucher XML
        voucher = f"""
            <TALLYMESSAGE xmlns:UDF="TallyUDF">
                <VOUCHER REMOTEID="{transaction.id}" VCHTYPE="{voucher_type}" ACTION="Create">
                    <DATE>{tally_date}</DATE>
                    <NARRATION>{transaction.description}</NARRATION>
                    <VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>
                    <VOUCHERNUMBER>{transaction.reference_number or ''}</VOUCHERNUMBER>
                    <PARTYLEDGERNAME>{account.tally_ledger_name}</PARTYLEDGERNAME>
                    <ALLLEDGERENTRIES.LIST>
                        <LEDGERNAME>{account.tally_ledger_name}</LEDGERNAME>
                        <AMOUNT>{-transaction.amount if transaction.transaction_type == "credit" else transaction.amount}</AMOUNT>
                    </ALLLEDGERENTRIES.LIST>"""
        
        # Add contra entry
        default_contra = "Cash" if transaction.description.lower().find("cash") != -1 else "Bank"
        voucher += f"""
                    <ALLLEDGERENTRIES.LIST>
                        <LEDGERNAME>{default_contra}</LEDGERNAME>
                        <AMOUNT>{transaction.amount if transaction.transaction_type == "credit" else -transaction.amount}</AMOUNT>
                    </ALLLEDGERENTRIES.LIST>
                </VOUCHER>
            </TALLYMESSAGE>"""
        
        return voucher
    
    def _send_to_tally(self, xml_request: str) -> str:
        """Send XML request to Tally."""
        try:
            headers = {
                'Content-Type': 'text/xml',
                'Accept': 'text/xml'
            }
            
            response = requests.post(
                f"{self.base_url}/",
                data=xml_request,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Tally: {str(e)}")
            raise
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """Process Tally response."""
        result = {
            "success": False,
            "imported_count": 0,
            "errors": []
        }
        
        try:
            # Parse response XML
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response)
            
            # Check for import status
            status = root.find(".//IMPORTRESULT")
            if status is not None:
                result["success"] = status.text == "Success"
                
            # Count imported vouchers
            imported = root.findall(".//CREATED")
            result["imported_count"] = len(imported)
            
            # Collect any errors
            errors = root.findall(".//ERROR")
            result["errors"] = [error.text for error in errors]
            
        except Exception as e:
            logger.error(f"Error processing Tally response: {str(e)}")
            result["errors"].append(str(e))
        
        return result