# from langchain.document_loaders import PdfLoader
import argparse
import json
import logging
import os
import re
import subprocess
import time
from urllib.parse import quote_plus
from uuid import UUID

import certifi
import openai
import pytz
import requests
from django.db import models
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Cast

# from langchain.vectorstores import Chroma
from dotenv import load_dotenv

# from langchain import PromptTemplate
from langchain.docstore.document import Document
from langchain.document_loaders import PyMuPDFLoader

# from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain.vectorstores.pgvector import DistanceStrategy, PGVector

# from openai import OpenAI
from pgvector.django import CosineDistance, L2Distance
from psycopg.conninfo import make_conninfo
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate

# import fitz
from requests import Request, Session
from requests.adapters import HTTPAdapter
from sqlalchemy.dialects.postgresql import dialect
from urllib3.util import Retry

from core import settings
from core.constants import Constants
from datahub.models import LangchainPgCollection, LangchainPgEmbedding, ResourceFile

LOGGING = logging.getLogger(__name__)

load_dotenv()

os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

openai.api_key = settings.OPENAI_API_KEY

embedding_model = "text-embedding-ada-002"
embeddings = OpenAIEmbeddings(model=embedding_model)

db_settings = settings.DATABASES['default']
encoded_user = quote_plus(db_settings['USER'])
encoded_password = quote_plus(db_settings['PASSWORD'])

# Construct the connection string
connectionString = f"postgresql://{encoded_user}:{encoded_password}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"

def send_request(file_url):
    response = None
    try:
        request_obj = Request("GET", file_url)
        session = Session()
        request_prepped = session.prepare_request(request_obj)
        retries = Retry(
            total=10,
            backoff_factor=0.1,
            status_forcelist=[403, 502, 503, 504],
            allowed_methods={"GET"},
        )
        session.mount(file_url, HTTPAdapter(max_retries=retries))
        response = session.send(
            request_prepped,
            stream=True,
            verify=certifi.where(),
            # verify=False,
        )
        print({"function": "send_request", "response_status": response.status_code, "url": file_url})

    except Exception as error:
        LOGGING.error(error, exc_info=True)

    return response

def get_embeddings(embeddings, docs, collection_name, connection_string, resource):
    for document in docs:
        document.metadata["url"] = resource.get("url")
    db = PGVector.from_documents(
    embedding=embeddings,
    documents=docs,
    collection_name=collection_name,
    connection_string=connection_string,
)

def download_file(file_url, local_file_path):
    try:
        with open(local_file_path, 'w'):
            pass 
        if re.match(r"(https?://|www\.)", file_url) is None:
            "https" + file_url

        if Constants.GOOGLE_DRIVE_DOMAIN in file_url:
            # remove the trailing "/"
            ends_with_slash = r"/$"
            re.search(ends_with_slash, file_url)
            if "/file/d/" in file_url:
                # identify file & build only the required URL
                pattern = r"/file/d/([^/]+)"
                match = re.search(pattern, file_url)
                file_id = match.group(1) if match else None
                file_url = f"{Constants.GOOGLE_DRIVE_DOWNLOAD_URL}={file_id}" if file_id else file_url

        response = send_request(file_url)
        if response and response.status_code == 200:
            with open(local_file_path, "wb") as local_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        local_file.write(chunk)

            LOGGING.info({"function": "download_file", "response_status": response.status_code, "file_path": local_file_path})
            return local_file_path

        else:
            LOGGING.info({"function": "download_file", "response_status": response.status_code, "file_path": local_file_path})

    except requests.exceptions.RequestException as request_error:
        LOGGING.info({"function": "download_file", "status": "failed to download"})
        LOGGING.error(request_error, exc_info=True)

    return None

def build_pdf(transcript, local_file_path):
    try:
        with open(local_file_path, 'w'):
            pass 
        doc = SimpleDocTemplate(local_file_path, pagesize=letter)
        story = []

        # Split the transcript into paragraphs based on line breaks
        paragraphs = transcript.split("\n")
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.textColor = colors.black

        # Create a Paragraph object for each paragraph and add them to the story
        for paragraph_text in paragraphs:
            story.append(Paragraph(paragraph_text, style=style))

        if doc and len(story) > 0:
            doc.build(story)
            LOGGING.info({"function": "build_pdf", "status": "created", "file_path": local_file_path})
            return local_file_path
        else:
            LOGGING.info({"function": "build_pdf", "status": "transcript is empty or null", "file_path": local_file_path})

    except Exception as error:
        LOGGING.error({"function": "build_pdf", "status": "failed to create", "file_path": local_file_path})
        LOGGING.error(error, exc_info=True)

    return None

def load_documents(url, file, type, id, transcription=""):
    documents = []
    # for pdf_path in pdf_paths:
    try:
        removed = os.remove("temp.pdf") if os.path.exists("temp.pdf") else 'pass'
        if type == 'youtube':
            build_pdf(transcription, "temp.pdf")
            loader = PyMuPDFLoader("temp.pdf")
        elif type == 'pdf':
            download_file(url, "temp.pdf")
            loader = PyMuPDFLoader("temp.pdf")
        else: 
            # file_path = os.path.join(settings.MEDIA_ROOT, file)
            # print(file_path)
            
            domain = os.environ.get('DATAHUB_SITE', "http://localhost:8000")
            file = file if file.startswith(domain) else domain+file
            loader = PyMuPDFLoader(file)
        return loader.load()

    except requests.exceptions.RequestException as e:
        LOGGING.error(f"Error downloading PDF from {url} or {file}: {e}", exc_info=True)
    except Exception as e:
        LOGGING.error(f"Error downloading PDF from {url} or {file}: {e}", exc_info=True)

    return documents

def split_documents(documents, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators="\n",
    )
    return text_splitter.split_documents(documents)

def genrate_embeddings_from_text(text):
    response = openai.Embedding.create(input=text, model=embedding_model)
    embedding = response['data'][0]['embedding']
    return embedding

def find_similar_chunks(input_embedding, resource_id,  top_n=5,):
    # Assuming you have a similarity function or custom SQL to handle vector comparison
    if resource_id:
        LOGGING.info("Looking into resource: {resource_id} embeddings")
        collection_ids = LangchainPgCollection.objects.filter(
            name__in=Subquery(
                ResourceFile.objects.filter(resource=resource_id)
                .annotate(string_id=Cast('id', output_field=models.CharField()))
                .values('string_id')
            )
        ).values_list('uuid', flat=True)
        # Use these IDs to filter LangchainPgEmbedding objects
        similar_chunks = LangchainPgEmbedding.objects.annotate(
            similarity=L2Distance("embedding", input_embedding)
        ).order_by("similarity").filter(similarity__lt=0.55, collection_id__in=collection_ids).all()[:top_n]
        return similar_chunks
    else:
        LOGGING.info("Looking into all embeddings")
        similar_chunks = LangchainPgEmbedding.objects.annotate(
            similarity=L2Distance("embedding", input_embedding)
        ).order_by("similarity").filter(similarity__lt=0.55).defer('cmetadata').all()[:top_n]
        # import pdb; pdb.set_trace()
        return similar_chunks

def format_prompt(user_name, context_chunks, user_input, chat_history):
    if context_chunks:
        print("chunks availabe")
        return Constants.SYSTEM_MESSAGE.format(name_1=user_name, input=user_input, context=context_chunks, chat_history=chat_history)
    else:
        print("chunks not availabe")
        return Constants.NO_CUNKS_SYSTEM_MESSAGE.format(name_1=user_name, input=user_input, chat_history=chat_history)
def generate_response(prompt):
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",  # Use an appropriate engine
        prompt=prompt,
        max_tokens=2000  # Adjust as necessary
    )
    return response.choices[0].text.strip()

class VectorDBBuilder:
    def create_vector_db(resource, chunk_size=1000, chunk_overlap=200):
        # resource = ResourceFile(resource)
        documents = load_documents(resource.get("url"), resource.get("file"), resource.get("type"), resource.get("id"), resource.get("transcription"))
        if documents:
            texts = split_documents(documents, chunk_size, chunk_overlap)
            embeddings = OpenAIEmbeddings()
            vectordb = get_embeddings(embeddings, texts, str(resource.get("id")), connectionString, resource)
        return None

    
    def get_input_embeddings(text, user_name=None, resource_id=None, chat_history=None):
        text=text.replace("\n", " ") # type: ignore
        try:
            embedding = genrate_embeddings_from_text(text)
            chunks = find_similar_chunks(embedding, resource_id)
            documents =  " ".join([row.document for row in chunks])
            LOGGING.info(f"Similarity score for the query: {text}. Score: {' '.join([str(row.similarity) for row in chunks])} ")
            formatted_message = format_prompt(user_name, documents, text, chat_history)
            # print(formatted_message)
            response = generate_response(formatted_message)
            return response, chunks
        except Exception as e:
            LOGGING.error(f"Error while generating response for query: {text}: Error {e}", exc_info=True)
            return str(e)
   