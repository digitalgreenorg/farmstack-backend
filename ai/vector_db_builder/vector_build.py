import tempfile
import logging
from ai.open_ai_utils import get_embeddings, insert_chunking_in_db
from ai.vector_db_builder.load_audio_and_video import LoadAudioAndVideo
from ai.utils import build_pdf, download_file, resolve_file_path
from ai.vector_db_builder.load_documents import LoadDocuments
from ai.vector_db_builder.load_website import WebsiteLoader
from core import settings
from datahub.models import ResourceFile
import logging
import os
from langchain.document_loaders import (
    BSHTMLLoader,
    CSVLoader,
    JSONLoader,
    PyMuPDFLoader,
    UnstructuredHTMLLoader,
)

from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
)
from contextlib import contextmanager
from celery import shared_task

LOGGING = logging.getLogger(__name__)


# @shared_task
def create_vector_db(resource_file, chunk_size=1000, chunk_overlap=200):
    status = "failed"
    resource_id = resource_file.get('id')
    try:
        documents, status = load_documents(
            resource_file.get("url"), resource_file.get("file"), resource_file.get("type"),
            resource_file.get("id"), resource_file.get("transcription"))
        LOGGING.info(f"Documents loaded for Resource ID: {resource_id}")
        if status == "completed":
            texts = split_documents(documents, chunk_size, chunk_overlap)
            LOGGING.info(f"Documents split completed for Resource ID: {resource_id}")
            embedded_chunk = get_embeddings(texts, resource_file, str(resource_id))
            # One more step is added to parse insertation error
            if embedded_chunk != {}:
                LOGGING.info(f"Embeddings creation completed for Resource ID: {resource_id}")
                # inserting embedding in vector db
                chunk_insertation = insert_chunking_in_db(embedded_chunk)
                if chunk_insertation:
                    documents="Embeddings Created Sucessfully"
                else:
                    documents="Unable to update Embeddings"
            else:
                documents="Unable to create Embeddings"
        data = ResourceFile.objects.filter(id=resource_id).update(
        embeddings_status=status,
        embeddings_status_reason=documents
        )
        LOGGING.info(f"Resource file ID: {resource_id} and updated with: {documents}")
    except Exception as e:
        LOGGING.error(f"Faild lo create embeddings for Resource ID: {resource_id} and ERROR: {str(e)}")
        documents = str(e)
        data = ResourceFile.objects.filter(id=resource_id).update(
            embeddings_status=status,
            embeddings_status_reason=documents
        )
        LOGGING.info(f"Resource file ID: {resource_id} and updated with: {documents}")
    return data

def load_documents(url, file, doc_type, id, transcription=""):
    try:
        
        if doc_type == 'api':
            absolute_path = os.path.join(settings.MEDIA_ROOT, file.replace("/media/", ''))
            loader = JSONLoader(file_path=absolute_path,  jq_schema='.', text_content=False)
            return loader.load(), "completed"
        elif doc_type in ['youtube', 'pdf', 'website', "file"]:
            with temporary_file(suffix=".pdf") as temp_pdf_path:
                if doc_type == 'youtube':
                    if not transcription:
                        summary = LoadAudioAndVideo().generate_transcriptions_summary(url)
                        build_pdf(summary, temp_pdf_path)
                        ResourceFile.objects.filter(id=id).update(transcription=summary)
                        loader = PyMuPDFLoader(temp_pdf_path)  # Assuming PyMuPDFLoader is defined elsewhere
                    else:
                        build_pdf(transcription, temp_pdf_path)
                        loader = PyMuPDFLoader(temp_pdf_path)  # Assuming PyMuPDFLoader is defined elsewhere
                elif doc_type == 'pdf':
                    download_file(url, temp_pdf_path)
                    loader = PyMuPDFLoader(temp_pdf_path)  # Assuming PyMuPDFLoader is defined elsewhere
                elif doc_type == 'file':
                    file_path = resolve_file_path(file)
                    loader, format = LoadDocuments().load_by_file_extension(file_path, temp_pdf_path)
                elif doc_type == "website":
                    doc_text = ""
                    web_site_loader = WebsiteLoader()
                    main_content, web_links = web_site_loader.process_website_content(url)
                    doc_text = web_site_loader.aggregate_links_content(web_links, doc_text)
                    all_content = main_content + "\n" + doc_text
                    build_pdf(all_content.replace("\n", " "), temp_pdf_path)
                    loader = PyMuPDFLoader(temp_pdf_path)  # Assuming PyMuPDFLoader is defined elsewhere
                return loader.load(), "completed"
        else:
            LOGGING.error(f"Unsupported input type: {doc_type}")
            return f"Unsupported input type: {doc_type}", "failed"
    except Exception as e:
        LOGGING.error(f"Faild lo load the documents: {str(e)}")
        return str(e), "failed"

def split_documents(documents, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators="\n",
    )
    return text_splitter.split_documents(documents)


@contextmanager
def temporary_file(suffix=""):
    """Context manager for creating and automatically deleting a temporary file."""
    """Context manager for creating and automatically deleting a temporary file."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.close(fd)  # Close file descriptor
        LOGGING.info(f"Temporary file created at {path}")
        yield path
    finally:
        # Check if the file still exists before attempting to delete
        if os.path.exists(path):
            os.remove(path)
            LOGGING.info(f"Temporary file {path} deleted.")
