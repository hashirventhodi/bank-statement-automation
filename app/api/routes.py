from fastapi import APIRouter, UploadFile, File, HTTPException
from app.api.controllers import process_statement

router = APIRouter()

@router.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    """
    Endpoint to upload a bank statement file.
    """
    try:
        # Read file content and save temporarily
        contents = await file.read()
        # You may save the file to disk if needed.
        # For this example, we pass the file bytes and filename to the controller.
        result = process_statement(contents, file.filename)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
