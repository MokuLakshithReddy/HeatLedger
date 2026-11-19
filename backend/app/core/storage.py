import os
import io
import logging
from abc import ABC, abstractmethod
from typing import Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """Abstract interface for secure private object and document storage."""

    @abstractmethod
    def save_file(self, relative_path: str, content: bytes, content_type: Optional[str] = None) -> str:
        """Save file bytes to storage at the relative path. Returns the stored file path/key."""
        pass

    @abstractmethod
    def read_file(self, relative_path: str) -> bytes:
        """Read and return file bytes from storage."""
        pass

    @abstractmethod
    def delete_file(self, relative_path: str) -> bool:
        """Delete file from storage. Returns True if deleted or already gone."""
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Check if file exists in storage."""
        pass


class LocalStorageProvider(StorageProvider):
    """Private filesystem storage provider with path traversal protection."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.LOCAL_STORAGE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> str:
        # Sanitize path: remove leading slashes and drive letters
        clean_path = relative_path.lstrip("/\\")
        abs_path = os.path.abspath(os.path.join(self.base_dir, clean_path))
        if not abs_path.startswith(self.base_dir):
            raise PermissionError("Attempted path traversal outside storage directory.")
        return abs_path

    def save_file(self, relative_path: str, content: bytes, content_type: Optional[str] = None) -> str:
        target_path = self._resolve_safe_path(relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(content)
        logger.info(f"LocalStorageProvider saved {len(content)} bytes to {target_path}")
        return target_path

    def read_file(self, relative_path: str) -> bytes:
        target_path = self._resolve_safe_path(relative_path)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"File not found: {relative_path}")
        with open(target_path, "rb") as f:
            return f.read()

    def delete_file(self, relative_path: str) -> bool:
        target_path = self._resolve_safe_path(relative_path)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                logger.info(f"LocalStorageProvider deleted {target_path}")
                return True
            except OSError as e:
                logger.error(f"Failed to delete {target_path}: {e}")
                return False
        return True

    def exists(self, relative_path: str) -> bool:
        target_path = self._resolve_safe_path(relative_path)
        return os.path.exists(target_path)


class S3StorageProvider(StorageProvider):
    """Encrypted cloud object storage provider using Amazon S3 or Supabase Storage / MinIO."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.bucket = bucket_name or settings.S3_BUCKET_NAME or "heatledger-private-evidence"
        self.region = region_name or settings.S3_REGION_NAME or "ap-south-1"
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL

        import boto3
        from botocore.config import Config

        session_kwargs = {}
        if access_key or settings.S3_ACCESS_KEY_ID:
            session_kwargs["aws_access_key_id"] = access_key or settings.S3_ACCESS_KEY_ID
        if secret_key or settings.S3_SECRET_ACCESS_KEY:
            session_kwargs["aws_secret_access_key"] = secret_key or settings.S3_SECRET_ACCESS_KEY

        self.s3_client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            config=Config(signature_version="s3v4"),
            **session_kwargs,
        )

    def _clean_key(self, relative_path: str) -> str:
        return relative_path.replace("\\", "/").lstrip("/")

    def save_file(self, relative_path: str, content: bytes, content_type: Optional[str] = None) -> str:
        key = self._clean_key(relative_path)
        extra_args = {"ServerSideEncryption": "AES256"}
        if content_type:
            extra_args["ContentType"] = content_type

        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            **extra_args,
        )
        logger.info(f"S3StorageProvider uploaded {len(content)} bytes to s3://{self.bucket}/{key}")
        return f"s3://{self.bucket}/{key}"

    def read_file(self, relative_path: str) -> bytes:
        key = self._clean_key(relative_path)
        response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete_file(self, relative_path: str) -> bool:
        key = self._clean_key(relative_path)
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"S3StorageProvider deleted s3://{self.bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete s3://{self.bucket}/{key}: {e}")
            return False

    def exists(self, relative_path: str) -> bool:
        key = self._clean_key(relative_path)
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


_storage_singleton: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    """Return the configured storage provider singleton."""
    global _storage_singleton
    if _storage_singleton is None:
        if settings.STORAGE_BACKEND == "s3":
            _storage_singleton = S3StorageProvider()
        else:
            _storage_singleton = LocalStorageProvider()
    return _storage_singleton
