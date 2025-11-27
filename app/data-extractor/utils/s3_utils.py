import json
import io
import gzip
import uuid
import boto3
from datetime import datetime, timezone
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, Dict
from config.settings import S3_BUCKET, PREFIX, COMPRESS

def save_to_s3(
    data: Any,
    source_name: str,
    compress: bool = COMPRESS,
) -> Dict[str, Any]:
    """Uploads JSON data to S3 with optional gzip compression."""
    cfg = Config(retries={"max_attempts": 10, "mode": "standard"})
    s3_client = boto3.client("s3", config=cfg)

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d_%H-%M-%S")
    ms = f"{int(now.microsecond/1000):03d}"
    rand = uuid.uuid4().hex[:8]
    date_path = f"{now.year:04d}/{now.month:02d}/{now.day:02d}/{now.hour:02d}"
    ext = "json.gz" if compress else "json"
    key = f"{PREFIX}/{source_name}/{date_path}/{ts}-{ms}-{rand}.{ext}"

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if compress:
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(payload.encode("utf-8"))
        body_bytes = buf.getvalue()
    else:
        body_bytes = payload.encode("utf-8")

    put_kwargs = {
        "Bucket": S3_BUCKET,
        "Key": key,
        "Body": body_bytes,
        "ContentType": "application/json; charset=utf-8",
    }
    if compress:
        put_kwargs["ContentEncoding"] = "gzip"

    try:
        s3_client.put_object(**put_kwargs)
        print(f"✅ Uploaded to s3://{S3_BUCKET}/{key}")
        return {"bucket": S3_BUCKET, "key": key, "size_bytes": len(body_bytes)}
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Failed to upload to S3: {e}")
