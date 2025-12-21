from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple
from google.cloud import storage


@dataclass(frozen=True)
class GcsObjectRef:
    gcs_uri: str
    sha256: str


def _parse_gs_uri(gs_uri: str) -> Tuple[str, str]:
    if not gs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gs_uri}")
    parts = gs_uri[5:].split("/", 1)
    bucket = parts[0]
    path = parts[1] if len(parts) > 1 else ""
    return bucket, path


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


class GcsClient:
    
    def __init__(self, project: Optional[str] = None):
        self._client = storage.Client(project=project)

    def upload_bytes(
        self,
        bucket_name: str,
        object_path: str,
        data: bytes,
        content_type: str = "video/mp4",
        metadata: Optional[dict] = None,
    ) -> GcsObjectRef:
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(object_path)
        if metadata:
            blob.metadata = metadata
        blob.upload_from_string(data, content_type=content_type)
        uri = f"gs://{bucket_name}/{object_path}"
        return GcsObjectRef(gcs_uri=uri, sha256=sha256_bytes(data))

    def download_bytes(self, gs_uri: str) -> bytes:
        bucket_name, object_path = _parse_gs_uri(gs_uri)
        blob = self._client.bucket(bucket_name).blob(object_path)
        return blob.download_as_bytes()