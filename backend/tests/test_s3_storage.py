import boto3
import pytest
from botocore.config import Config as BotoConfig
from moto import mock_aws

from app.core.image_storage import S3ImageStorage
from app.storage_maintenance import _s3_candidates


@pytest.fixture
def s3_storage():
    with mock_aws():
        access_key = "test-access-key"
        secret_key = "test-secret-key"
        bucket = "south-omo-market-contract-test"
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(s3={"addressing_style": "path"}),
        )
        client.create_bucket(Bucket=bucket)
        storage = S3ImageStorage(
            bucket=bucket,
            access_key_id=access_key,
            secret_access_key=secret_key,
            region="us-east-1",
            client=client,
        )
        yield storage, client, bucket


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
    assert all(
        grant["Grantee"].get("URI") != "http://acs.amazonaws.com/groups/global/AllUsers"
        for grant in acl["Grants"]
    )
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.read(key)


def test_s3_adapter_rejects_path_traversal(s3_storage):
    storage, _, _ = s3_storage
    with pytest.raises(ValueError):
        storage.read("listings/../../private/secret.jpg")

def test_s3_orphan_scanner_enumerates_listing_objects(s3_storage):
    storage, client, bucket = s3_storage
    client.put_object(Bucket=bucket, Key="listings/orphan/image.jpg", Body=b"synthetic")
    candidates = _s3_candidates(storage)
    assert len(candidates) == 1
    assert candidates[0][0] == "listings/orphan/image.jpg"
    assert candidates[0][1].tzinfo is not None
