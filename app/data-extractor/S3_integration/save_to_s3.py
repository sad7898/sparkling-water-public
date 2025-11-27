import json
import os
import io
import gzip
import uuid
import boto3
from datetime import datetime, timezone
from typing import Any, Optional, Dict
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

def save_to_s3(
    data: Any,
    source_name: str = "api_data",
    bucket: Optional[str] = None,
    prefix: str = "raw-data",
    region_name: Optional[str] = None,
    compress: bool = True,
    kms_key_id: Optional[str] = None,
    s3_client: Optional[Any] = None,
) -> Dict[str, Any]:
    if bucket is None:
        bucket = os.getenv("S3_BUCKET", "BUCKET_NAME")
    if region_name is None:
        region_name = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if s3_client is None:
        cfg = Config(retries={"max_attempts": 10, "mode": "standard"})
        if region_name:
            s3_client = boto3.client("s3", region_name=region_name, config=cfg)
        else:
            s3_client = boto3.client("s3", config=cfg)

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d_%H-%M-%S")
    ms = f"{int(now.microsecond/1000):03d}"
    rand = uuid.uuid4().hex[:8]
    date_path = f"{now.year:04d}/{now.month:02d}/{now.day:02d}/{now.hour:02d}"
    ext = "json.gz" if compress else "json"
    key = f"{prefix}/{source_name}/{date_path}/{ts}-{ms}-{rand}.{ext}"

    payload_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if compress:
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(payload_str.encode("utf-8"))
        body_bytes = buf.getvalue()
    else:
        body_bytes = payload_str.encode("utf-8")

    put_kwargs: Dict[str, Any] = {
        "Bucket": bucket,
        "Key": key,
        "Body": body_bytes,
        "ContentType": "application/json; charset=utf-8",
    }
    if compress:
        put_kwargs["ContentEncoding"] = "gzip"
    if kms_key_id:
        put_kwargs["ServerSideEncryption"] = "aws:kms"
        put_kwargs["SSEKMSKeyId"] = kms_key_id

    try:
        s3_client.put_object(**put_kwargs)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Failed to write s3://{bucket}/{key}: {e}") from e

    return {"bucket": bucket, "key": key, "size_bytes": len(body_bytes)}