from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from minio import Minio

# MinIO Client Global
minio_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global minio_client
    print("Starting up LifeLog...")
    
    # Initialize MinIO
    try:
        minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
            print(f"Created MinIO bucket: {settings.MINIO_BUCKET}")
    except Exception as e:
        print(f"Error connecting to MinIO: {e}")

    yield
    
    # Shutdown
    print("Shutting down LifeLog...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}

@app.get("/")
def read_root():
    return {"message": "Welcome to LifeLog API"}
