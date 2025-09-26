from pydantic import BaseModel
from fastapi import UploadFile, File

class LoadExcelRequest(BaseModel):
    file: UploadFile
