# from langchain.document_loaders import PdfLoader
import json
import os

# import fitz
import openai
import requests

# from langchain.vectorstores import Chroma
from dotenv import load_dotenv
from langchain.docstore.document import Document
from langchain.document_loaders import PyMuPDFLoader

# from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain.vectorstores.pgvector import DistanceStrategy, PGVector
from pgvector.django import CosineDistance, L2Distance
from psycopg.conninfo import make_conninfo

from core import settings
from datahub.models import ResourceFile

# from datahub.models import LangchainPgEmbedding

# from langchain.embeddings import OpenAIEmbeddings
# from dotenv import load_dotenv

# def lod_embeddings(file_path):
#     loader = PdfLoader(file_path, encoding='utf-8')
#     documents = loader.load()
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
#     texts = text_splitter.split_documents(documents)
#     embeddings = OpenAIEmbeddings()
#     doc_vectors = embeddings.embed_documents([t.page_content for t in texts[:5]])









load_dotenv()

os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

# os.environ["allow_reuse"] = "True" # type: ignore

embeddings = OpenAIEmbeddings()
from sqlalchemy.dialects.postgresql import dialect

embedding_model = "text-embedding-ada-002"

db_settings = settings.DATABASES['default']
from urllib.parse import quote_plus

# URL-encode the username and password
encoded_user = quote_plus(db_settings['USER'])
encoded_password = quote_plus(db_settings['PASSWORD'])

# Construct the connection string
connectionString = f"postgresql://{encoded_user}:{encoded_password}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"

print(connectionString)

def get_embeddings(embeddings, docs, collection_name, connection_string, resource):
    db = PGVector.from_documents(
    embedding=embeddings,
    documents=docs,
    collection_name=collection_name,
    connection_string=connection_string,
    # collection_metadata=json.dumps(resource)
)

def load_documents(url, file, type, id):
    documents = []
    # for pdf_path in pdf_paths:
    try:
        if type == 'pdf':
            response = requests.get(url, verify=False)
            with open('temp.pdf', 'wb') as temp_file:
                temp_file.write(response.content)
            loader = PyMuPDFLoader("temp.pdf")
            # documents.extend(loader.load())
        else: 
            loader = PyMuPDFLoader(file)
        return loader.load()

    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF from {url} or {file}: {e}")

    return documents

def split_documents(documents, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators="\n",
    )
    return text_splitter.split_documents(documents)


class VectorDBBuilder:
    def create_vector_db(resource, chunk_size=1000, chunk_overlap=200):
        # resource = ResourceFile(resource)
        print(resource)
        if ResourceFile(resource).type == 'video':
            pass
        else:
            documents = load_documents(resource.get("url"), resource.get("file"), resource.get("type"), resource.get("id"))
            texts = split_documents(documents, chunk_size, chunk_overlap)
            embeddings = OpenAIEmbeddings()
            vectordb = get_embeddings(embeddings, texts, resource.get("id"), connectionString, resource)
            return None

    # def create_vector_db_for_video_data(
    #     pdf_paths, persist_directory, chunk_size, chunk_overlap
    # ):
    #     documents = load_documents(pdf_paths)
    #     texts = split_documents(documents, chunk_size, chunk_overlap)
    #     tfidf_video_retriever = TFIDFRetriever.from_documents(texts)

    #     embeddings = OpenAIEmbeddings()
    #     vectordb = get_embeddings(embeddings, documents, chunk_size, chunk_overlap)

    #     return vectordb, tfidf_video_retriever

    # Function to process input with retrieval of most similar documents from the database
    
    
    
    # def get_input_embeddings(text: str):
    #     text=text.replace("\n", " ")
    #     response = openai.Embedding.create(input=text, model=embedding_model, api_key=settings.OPENAI_API_KEY)
    #     embedding = response["data"][0]["embedding"]
    #     documents = LangchainPgEmbedding.objects.values("document").order_by(CosineDistance("embedding", embedding))[:5]
    #     print(documents)
    #     import pdb; pdb.set_trace()
    #     return documents


