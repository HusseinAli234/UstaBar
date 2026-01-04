# app/api/upload_router.py
import uuid
from fastapi import APIRouter, UploadFile, File
from app.core.storage import upload_file_to_minio

router = APIRouter(tags=["Upload"])

@router.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    # Генерируем уникальное имя, чтобы файлы не перезатерлись
    file_extension = file.filename.split(".")[-1]
    new_filename = f"{uuid.uuid4()}.{file_extension}"
    
    # Загружаем в MinIO
    await upload_file_to_minio(file.file, new_filename, file.content_type)
    
    # Возвращаем имя файла фронтенду
    return {"filename": new_filename, "url": f"/static/photos/{new_filename}"} # URL пока условный