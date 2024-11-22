from hashlib import sha256
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from google.oauth2 import service_account
from google.auth.credentials import Credentials
from google.cloud import storage
from google.cloud import datastore

__slots__ = ["storage_service_client", "datastore_service_client"]
__all__ = __slots__


def __get_credentials() -> Credentials:
    """
    Retrieves Google Cloud service account credentials from Streamlit secrets.

    This function reads the service account information stored in the Streamlit
    secrets configuration and uses it to create and return a `Credentials` object
    from the `google.oauth2.service_account` module.

    Returns:
        Credentials: A `Credentials` object that can be used to authenticate
        with Google Cloud services.
    """
    return service_account.Credentials.from_service_account_info(
        st.secrets.google_cloud_api
    )


def storage_service_client() -> storage.Client:
    """
    Creates a Google Cloud Storage service client.

    This function uses the `get_credentials` function to retrieve the Google Cloud
    service account credentials and uses them to create a Google Cloud Storage
    service client.

    Returns:
        storage.Client: A Google Cloud Storage service client that can be used to
        interact with Google Cloud Storage.
    """

    return storage.Client(credentials=__get_credentials())


def storage_create_object(file: UploadedFile) -> dict:
    """
    Uploads a file to Google Cloud Storage if it does not already exist, and updates the metadata
    of the blob with the file's name and size.

    Args:
        file (UploadedFile): The file to be uploaded.

    Returns:
        google.cloud.storage.blob.Blob: The blob object representing the uploaded file.
    """

    # 1. Read the file content and calculate the hash value
    file_content = file.getvalue()
    file_hash_value = sha256(file_content).hexdigest()

    # 2.Create a Google Cloud Storage client and get the bucket
    client = storage_service_client()
    bucket_name = st.secrets.google_cloud_storage.bucket_name
    bucket = client.bucket(bucket_name)

    # 3. Check if the file already exists in the bucket
    # If it does not exist, upload the file to the bucket
    blob = bucket.blob(file_hash_value)
    if not blob.exists():
        blob.upload_from_string(file_content, content_type="")
        blob.reload()

    # 4. Update the metadata of the blob with the file names and size
    metageneration_match_precondition = blob.metageneration
    current_file_names = []
    if blob.metadata is not None:
        current_file_names = blob.metadata.get("filenames", [])
    new_file_names = current_file_names + [file.name]
    new_file_names = list(set(new_file_names))
    blob.metadata = {"filenames": new_file_names}
    try:
        blob.patch(if_metageneration_match=metageneration_match_precondition)
    except:
        pass

    return {
        "file_names": new_file_names,
        "file_size": len(file_content),
        "file_hash": file_hash_value,
    }


def datastore_service_client() -> datastore.Client:
    """
    Creates a Google Cloud Datastore service client.

    This function uses the `get_credentials` function to retrieve the Google Cloud
    service account credentials and uses them to create a Google Cloud Datastore
    service client.

    Returns:
        datastore.Client: A Google Cloud Datastore service client that can be used to
        interact with Google Cloud Datastore.
    """
    return datastore.Client(credentials=__get_credentials())


def datastore_create_document(
    document: dict,
    assistant_id: str,
    gpt_model: str,
) -> tuple[datastore.Entity, bool]:
    """
    Creates a new document in Google Cloud Datastore.

    Args:
        document (dict): A dictionary representing the document to be created.

    Returns:
        datastore.Entity: The entity representing the document in Google Cloud Datastore.
        bool: A boolean indicating whether the document was created or not.
    """
    client = datastore_service_client()
    doc_key = client.key("documents", f'{document["file_hash"]}-{assistant_id}-{gpt_model}')

    # 1. Check if the document already exists in the datastore
    # If it does not exist, create a new document entity
    if (doc_entity := client.get(doc_key)) is not None:
        return doc_entity, False

    # 2. Create a new document entity with the provided data
    doc_entity = client.entity(key=doc_key)
    doc_entity.update(
        {
            "file_size": document["file_size"],
            "file_names": document["file_names"],
        }
    )
    client.put(doc_entity)
    return doc_entity, True
