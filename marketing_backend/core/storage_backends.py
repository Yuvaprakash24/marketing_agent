import os

from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

SUPABASE_URL = os.getenv("SUPABASE_URL")


class PublicMediaStorage(S3Boto3Storage):
    bucket_name = "media"
    default_acl = "public-read"

    def url(self, name):
        return f"{SUPABASE_URL}/storage/v1/object/public/media/{name}"


class PublicStaticStorage(S3Boto3Storage):
    bucket_name = "static"
    default_acl = "public-read"

    def url(self, name):
        return f"{SUPABASE_URL}/storage/v1/object/public/static/{name}"


# Scratch space for documents being parsed during business onboarding. Deliberately
# local rather than the default storage: the files are read back and deleted within a
# single request, and object stores have no directories to remove afterwards.
staging_storage = FileSystemStorage()
