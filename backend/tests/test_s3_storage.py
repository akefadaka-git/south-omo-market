import os
import time

import boto3
import pytest
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.image_storage import S3ImageStorage


@pytest.fixture
def s3_storage():
    endpoint = os.getenv("TEST_S3_ENDPOINT_URL")
    if not endpoint:
        pytest.skip("TEST_S3_ENDPOINT_URL is not configured")
    access_key = os.environ["TEST_S3_ACCESS_KEY_ID"]
    secret_key = os.environ["TEST_S3_SECRET_ACCESS_KEY"]
    bucket = os.environ["TEST_S3_BUCKET"]
    region = os.getenv("TEST_S3_REGION", "us-east-1")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=BotoConfig(s3={"addressing_style": "path"}),
    )
    last_error = None
    for _ in range(30):
        try:
            client.list_buckets()
            break
        except Exception as error:  # service startup race; bounded retry
            last_error = error
            time.sleep(2)
    else:
        raise AssertionError(f"MinIO did not become ready: {last_error}")
    try:
        client.create_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") not in {
            "BucketAlreadyOwnedByYou", "BucketAlreadyExists"
        }:
            raise
    storage = S3ImageStorage(
        bucket=bucket,
        access_key_id=access_key,
        secret_access_key=secret_key,
        region=region,
        endpoint_url=endpoint,
        use_ssl=False,
        client=client,
    )
    yield storage, client, bucket
    remaining = client.list_objects_v2(Bucket=bucket).get("Contents", [])
    if remaining:
        client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": item["Key"]} for item in remaining]},
        )
    client.delete_bucket(Bucket=bucket)


def test_s3_compatible_adapter_round_trip_metadata_and_delete(s3_storage):
    storage, client, bucket = s3_storage
    payload = b"synthetic-normalized-jpeg-bytes"
    key = storage.save_jpeg("listing-integration-001", payload)
    assert key.startswith("listings/listing-integration-001/")
    assert storage.read(key) == payload
    head = client.head_object(Bucket=bucket, Key=key)
    assert head["ContentType"] == "image/jpeg"
    assert head["Metadata"]["listing-id"] == "listing-integration-001"
    acl = client.get_object_acl(Bucket=bucket, Key=key)
    assert all(grant["Grantee"].get("URI") != "http://acs.amazonaws.com/groups/global/AllUsers"
               for grant in acl["Grants"])
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.read(key)


def test_s3_adapter_rejects_path_traversal(s3_storage):
    storage, _, _ = s3_storage
    with pytest.raises(ValueError):
        storage.read("listings/../../private/secret.jpg")
