import logging
from io import BytesIO

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from src.core.config import settings

logger = logging.getLogger(__name__)


s3: BaseClient = boto3.client(
    "s3",
    endpoint_url=f"http://{settings.MINIO_HOST}:{settings.MINIO_PORT}",
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    region_name="us-east-1",
)


def create_bucket(bucket_name: str):
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)


def upload_to_minio(file: BytesIO, filename: str, bucket_name: str) -> bool:
    try:
        file.seek(0)
        s3.upload_fileobj(file, bucket_name, filename)
        return True
    except ClientError as e:
        logger.error("Minio error while uploading file:", e)
        return False


def remove_from_minio(filename: str, bucket_name: str):
    try:
        s3.delete_object(Bucket=bucket_name, Key=filename)
        return True
    except ClientError as e:
        logger.error("Minio error while removing file:", e)
        return False
