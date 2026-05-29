import os
import httpx
import structlog
from core.config import settings

logger = structlog.get_logger()

BUCKET_NAME = "nischay-db-bucket"
FILE_PATH = "nischay.db"

def get_supabase_headers():
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
    }

def init_supabase_bucket():
    """Ensure the Supabase storage bucket exists."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        return False
    
    url = f"{settings.SUPABASE_URL}/storage/v1/bucket"
    headers = get_supabase_headers()
    
    try:
        # Check if bucket exists
        check_url = f"{url}/{BUCKET_NAME}"
        r = httpx.get(check_url, headers=headers)
        if r.status_code == 200:
            return True
            
        # Create bucket if it doesn't exist
        payload = {"id": BUCKET_NAME, "name": BUCKET_NAME, "public": False}
        r = httpx.post(url, headers=headers, json=payload)
        if r.status_code in (200, 201):
            logger.info("supabase_bucket_created", bucket=BUCKET_NAME)
            return True
        else:
            logger.error("supabase_bucket_creation_failed", status=r.status_code, body=r.text)
    except Exception as e:
        logger.error("supabase_bucket_init_error", error=str(e))
    return False

def download_database_from_supabase(local_db_path: str):
    """Download SQLite database file from Supabase Storage."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        return False
        
    url = f"{settings.SUPABASE_URL}/storage/v1/object/authenticated/{BUCKET_NAME}/{FILE_PATH}"
    headers = get_supabase_headers()
    
    try:
        logger.info("downloading_db_from_supabase", url=url)
        r = httpx.get(url, headers=headers)
        if r.status_code == 200:
            # Write to local file
            os.makedirs(os.path.dirname(local_db_path), exist_ok=True)
            with open(local_db_path, "wb") as f:
                f.write(r.content)
            logger.info("download_db_success", size=len(r.content))
            return True
        else:
            logger.info("no_existing_db_found_in_supabase", status=r.status_code)
    except Exception as e:
        logger.error("download_db_error", error=str(e))
    return False

def upload_database_to_supabase(local_db_path: str):
    """Upload/Overwrite SQLite database file to Supabase Storage."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        return False
        
    if not os.path.exists(local_db_path):
        logger.error("local_db_not_found_for_upload", path=local_db_path)
        return False
        
    # We must first ensure bucket is initialized
    init_supabase_bucket()
    
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{FILE_PATH}"
    headers = get_supabase_headers()
    
    try:
        with open(local_db_path, "rb") as f:
            file_data = f.read()
            
        logger.info("uploading_db_to_supabase", size=len(file_data))
        # Use PUT to overwrite the existing file
        r = httpx.put(
            url, 
            headers={**headers, "Content-Type": "application/x-sqlite3"}, 
            content=file_data
        )
        
        # If PUT returns 404/400 (e.g. file doesn't exist yet), try POST to create it
        if r.status_code not in (200, 201):
            logger.info("put_failed_trying_post", status=r.status_code)
            r = httpx.post(
                url,
                headers={**headers, "Content-Type": "application/x-sqlite3"},
                content=file_data
            )
            
        if r.status_code in (200, 201):
            logger.info("upload_db_success")
            return True
        else:
            logger.error("upload_db_failed", status=r.status_code, body=r.text)
    except Exception as e:
        logger.error("upload_db_error", error=str(e))
    return False
