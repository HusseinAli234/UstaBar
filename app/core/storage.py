# app/core/storage.py
from minio import Minio
from app.core.config import settings

# Инициализация клиента
client = Minio(
    settings.MINIO_Endpoint,
    access_key=settings.MINIO_Access_Key,
    secret_key=settings.MINIO_Secret_Key,
    secure=settings.MINIO_Secure
)

BUCKET_NAME = "order-photos"


def init_storage():
    """Безопасная инициализация бакета"""
    try:
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            print(f"✅ Бакет {BUCKET_NAME} создан")
        else:
            print(f"👌 Бакет {BUCKET_NAME} уже существует")
    except Exception as e:
        print(f"❌ Ошибка подключения к MinIO: {e}")
        
async def upload_file_to_minio(file_data, filename, content_type):
    """Загружает файл и возвращает имя"""
    # Важно: stream нужно читать, file_data - это SpooledTemporaryFile
    size = file_data.seek(0, 2) # Узнаем размер
    file_data.seek(0)
    
    client.put_object(
        BUCKET_NAME,
        filename,
        file_data,
        size,
        content_type=content_type
    )
    return filename