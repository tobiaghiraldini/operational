"""Aggregate parts, API keys, and credentials for a project or system parent."""

from django.contrib.contenttypes.models import ContentType

from apps.parts.models import ApiKey, Credential, Part
from apps.services.models import ServiceCredential


def parts_aggregate(content_object):
    """
    Return dict with parts, api_keys, credentials, and service_credentials for a parent.

    ``content_object`` must be a Project or System instance.
    """
    ct = ContentType.objects.get_for_model(content_object)
    oid = content_object.pk
    project_id = content_object.pk if content_object.__class__.__name__ == "Project" else None

    service_credentials = ServiceCredential.objects.none()
    if project_id is not None:
        service_credentials = ServiceCredential.objects.filter(
            project_id=project_id
        ).select_related("external_service")

    return {
        "parts": Part.objects.filter(content_type=ct, object_id=oid),
        "api_keys": ApiKey.objects.filter(content_type=ct, object_id=oid),
        "credentials": Credential.objects.filter(content_type=ct, object_id=oid),
        "service_credentials": service_credentials,
    }
