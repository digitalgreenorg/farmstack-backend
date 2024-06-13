# from langchain.document_loaders import PdfLoader
import argparse
import concurrent.futures
import csv
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from urllib.parse import quote_plus
from uuid import UUID

import certifi
import openai
import pytube
import pytz
import requests
from bs4 import BeautifulSoup
from django.db import models
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Cast
from docx import Document

# from langchain.vectorstores import Chroma
from dotenv import load_dotenv

# from langchain import PromptTemplate
# from langchain.docstore.document import Document
from langchain.document_loaders import (
    BSHTMLLoader,
    CSVLoader,
    JSONLoader,
    PyMuPDFLoader,
    UnstructuredHTMLLoader,
)

# from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain.vectorstores.pgvector import DistanceStrategy
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

from celery import shared_task
from core import settings
from core.constants import Constants
from datahub.models import LangchainPgCollection, LangchainPgEmbedding, ResourceFile
from utils.chain_builder import ChainBuilder
from langchain.prompts import PromptTemplate
from utils.pgvector import PGVector
from pydub import AudioSegment

# from openai import OpenAI
LOGGING = logging.getLogger(__name__)

load_dotenv()
open_ai=openai.Audio()
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

openai.api_key = settings.OPENAI_API_KEY

embedding_model = "text-embedding-ada-002"
embeddings = OpenAIEmbeddings(model=embedding_model)
# client = OpenAI(api_key=settings.OPENAI_API_KEY)

db_settings = settings.DATABASES['default']
encoded_user = quote_plus(db_settings['USER'])
encoded_password = quote_plus(db_settings['PASSWORD'])
retriever = ''


# Construct the connection string
connectionString = f"postgresql://{encoded_user}:{encoded_password}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"


def load_vector_db(resource_id):
    embeddings = OpenAIEmbeddings(model=embedding_model)

    LOGGING.info("Looking into resource: {resource_id} embeddings")
    collection_ids = LangchainPgCollection.objects.filter(
        name__in=Subquery(
            ResourceFile.objects.filter(resource=resource_id)
            .annotate(string_id=Cast('id', output_field=models.CharField()))
            .values('string_id')
        )
    ).values_list('uuid', flat=True)
    vector_db = PGVector(
            collection_name=str("2a24e282-969a-49f7-8a27-c588c4244ac4"),
            connection_string=connectionString,
            embedding_function=embeddings,
        )
    print("2a24e282-969a-49f7-8a27-c588c4244ac4")
    # retriever = vector_db.as_retriever(search_type="similarity_score_threshold")
    # docs = retriever.get_relevant_documents("tell me about Sorghum Advanced Farming")
    # print(docs)
    # retrival = Retrival()

    # similar_chunks = LangchainPgEmbedding.objects.annotate(
    #             similarity=CosineDistance("embedding", embedding)
    #         ).order_by("similarity").filter(similarity__lt=0.17, collection_id=str(collection_ids[6])).defer("cmetadata").all()[:5]
    import pdb; pdb.set_trace()
    return vector_db

def transcribe_audio(audio_bytes, language="en-US"):
    try:
        transcript = openai.Audio.translate(file=audio_bytes, model="whisper-1")
        return transcript
    except Exception as e:
        print("Transcription error:", str(e))
        return str(e)


class VectorBuilder:
    
    def send_request(self, file_url):
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

    def get_embeddings(self, embeddings, docs, collection_name, connection_string, resource):
        for document in docs:
            document.metadata["url"] = resource.get("url")
        retriever = PGVector.from_documents(
        embedding=embeddings,
        documents=docs,
        collection_name=collection_name,
        connection_string=connection_string,
    )

    def download_file(self, file_url, local_file_path):
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

            response = self.send_request(file_url)
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

    def build_pdf(self, transcript, local_file_path):
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
    def get_file_size(self, file_path):
        return os.path.getsize(file_path)

    def split_audio(self, file_path, segment_duration_ms=1000000):  # Default is 1800,000 ms (30 minutes)
        audio = AudioSegment.from_file(file_path)
        length_ms = len(audio)
        return [audio[i:i + segment_duration_ms] for i in range(0, length_ms, segment_duration_ms)]

   
    def generate_transcriptions_summary(self, url):
        regex_patterns = [
        r"(?<=v=)[^&#]+",      # Pattern for "watch" URLs
        r"(?<=be/)[^&#]+",     # Pattern for "youtu.be" short URLs
        r"(?<=embed/)[^&#]+"   # Pattern for "embed" URLs
        ]
        
        for pattern in regex_patterns:
            match = re.search(pattern, url)
            if match:
                file_id =  match.group(0)
        output_audio_file_mp3 = f"{settings.RESOURCES_AUDIOS}{file_id}.mp3"
        output_audio_compress_mp3 = f"{settings.RESOURCES_AUDIOS}{file_id}_compressed.mp3"

        if not os.path.exists(output_audio_file_mp3):
            LOGGING.info(f"Audio file not available for url: {url}")
            video = pytube.YouTube(url)
            video_stream = video.streams.filter(only_audio=True).first()

            video_stream.download(filename=output_audio_file_mp3)
            LOGGING.info(f"Audio file downloaded for url: {url}")
        LOGGING.info(os.path.getsize(output_audio_file_mp3))
        max_size_bytes = 25 * 1024 * 1024  # 25 MB
        file_size = self.get_file_size(output_audio_file_mp3)
        # import pdb; pdb.set_trace()
        if file_size > max_size_bytes:
            audio_segments = self.split_audio(output_audio_file_mp3)
            LOGGING.info(f"Audio file splited for url: {url}")
            import io

            transcriptions = []
            for segment in audio_segments:
                # Assuming your transcribe_audio function can take an AudioSegment directly
                # If not, you may need to export the segment to a file first and then pass the file path
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_file:
                    segment.export(tmp_file.name, format="mp3")
                    tmp_file.flush() 
                    with open(tmp_file.name, 'rb') as f:
                        transcription = transcribe_audio(f)
                        print("segment transcription completed")
                        transcriptions.append(transcription.text)
            
            # Combine all transcriptions into a single text
            final_transcription = " ".join(transcriptions)
        else:
            # Process the whole file directly if it's not larger than 25 MB
            final_transcription = transcribe_audio(output_audio_file_mp3)
        
            # chunks = [words[i:i + 1500] for i in range(0, len(words), 1500)]
            # summary = ''
            # LOGGING.info(f"youtube Video url:{url} transcriptions splited into: {len(chunks)}")
            # for chunk in chunks:
            #     text_chunks = ' '.join(chunk)
            #     summary_chunk, tokens_uasage = Retrival().generate_response(Constants.TRANSCTION_PROMPT.format(transcription=text_chunks, youtube_url=url))
            #     summary=summary+" "+summary_chunk
        if len(final_transcription) < 3000:
            summary_chunk, tokens_uasage = Retrival().generate_response(Constants.TRANSCTION_PROMPT.format(transcription=final_transcription, youtube_url=url))
            summary=summary_chunk
        else:
            summary=final_transcription
        return summary, file_id
    
    def load_documents(self, url, file, type, id, transcription=""):
        try:
            if type == 'api':
                absolute_path = os.path.join(settings.MEDIA_ROOT, file.replace("/media/", ''))
                loader = JSONLoader(file_path=absolute_path,  jq_schema='.', text_content=False)
                return loader.load(), "completed"
            elif type in ['youtube', 'pdf', 'website', "file"]:
                with self.temporary_file(suffix=".pdf") as temp_pdf_path:
                    if type == 'youtube':
                        summary, file_id = self.generate_transcriptions_summary(url)
                        file_path = f"{settings.RESOURCES_AUDIOS}{file_id}.pdf"
                        self.build_pdf(summary, file_path)
                        ResourceFile.objects.filter(id=id).update(file=file_path)
                        loader = PyMuPDFLoader(file_path)  # Assuming PyMuPDFLoader is defined elsewhere
                    elif type == 'pdf':
                        self.download_file(url, temp_pdf_path)
                        loader = PyMuPDFLoader(temp_pdf_path)  # Assuming PyMuPDFLoader is defined elsewhere
                    elif type == 'file':
                        file_path = self.resolve_file_path(file)
                        loader, format = self.load_by_file_extension(file_path, temp_pdf_path)
                    elif type == "website":
                        doc_text = ""
                        main_content, web_links = self.process_website_content(url)
                        doc_text = self.aggregate_links_content(web_links, doc_text)
                        all_content = main_content + "\n" + doc_text
                        self.build_pdf(all_content.replace("\n", " "), temp_pdf_path)
                        loader = PyMuPDFLoader(temp_pdf_path)  # Assuming PyMuPDFLoader is defined elsewhere
                    return loader.load(), "completed"
            else:
                LOGGING.error(f"Unsupported input type: {type}")
                return f"Unsupported input type: {type}", "failed"
        except Exception as e:
            LOGGING.error(f"Faild lo load the documents: {str(e)}")
            return str(e), "failed"

    @contextmanager
    def temporary_file(self, suffix=""):
        """Context manager for creating and automatically deleting a temporary file."""
        """Context manager for creating and automatically deleting a temporary file."""
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            os.close(fd)  # Close file descriptor
            print(f"Temporary file created at {path}")
            yield path
        finally:
            # Check if the file still exists before attempting to delete
            if os.path.exists(path):
                os.remove(path)
                print(f"Temporary file {path} deleted.")

    def process_website_content(self, url):
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()  # Raises a HTTPError for bad responses
            soup = BeautifulSoup(response.text, 'html.parser')
            main_content = soup.get_text(separator="\n", strip=True)
            web_links = set([a['href'] for a in soup.find_all('a', href=True)])
            return main_content, web_links
        except Exception as e:
            logging.error(f"Failed to retrieve website content: {url} - {e}")
            return "", ""

    def aggregate_links_content(self, links, doc_text):
        def fetch_content(link):
            main_content, web_links = self.process_website_content(link)
            return main_content, link

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_content, link) for link in set(links)]
            for future in as_completed(futures):
                main_content, link = future.result()
                doc_text +=  f" Below content related to link: {link} \n"+ main_content
        return doc_text

    def resolve_file_path(self, file):
        domain = os.environ.get('DATAHUB_SITE', "http://localhost:8000")
        return file if file.startswith(domain) else domain + file

    def load_by_file_extension(self, file, temp_pdf):
        if file.endswith(".pdf"):
            logging.info(f"pdf file loader started for file: {file}")
            return PyMuPDFLoader(file.replace('http://localhost:8000/', "")), 'pdf'
        elif file.endswith(".csv"):
            return CSVLoader(file_path=file.replace('http://localhost:8000/', ""), source_column="Title"), 'csv'
        elif file.endswith(".html"):
            return self.handle_html_file(file.replace('http://localhost:8000/', ""), temp_pdf), 'pdf'
        elif file.endswith(".docx"):
            return self.handle_docx_file(file), 'docx'
        elif file.endswith(".txt"):
            return self.handle_text_file(file), 'txt'

    def handle_text_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text

    def handle_docx_file(self, file_path):
        # Load the .docx file
        doc = Document(file_path)
        # Extract text from each paragraph in the document
        text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
        return text

    def handle_html_file(self, file, temp_pdf):
        text = ""
        loader = UnstructuredHTMLLoader(file)  # Assuming this loader is preferred for HTML
        for paragraph in loader.load():
            text += paragraph.page_content + "\n"
        self.build_pdf(text, temp_pdf)
        return PyMuPDFLoader(temp_pdf)

    def split_documents(self, documents, chunk_size, chunk_overlap):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators="\n",
        )
        return text_splitter.split_documents(documents)

class Retrival:

    def genrate_embeddings_from_text(self, text):
        response = openai.Embedding.create(input=text, model=embedding_model)
        embedding = response['data'][0]['embedding']
        return embedding

    def find_similar_chunks(self, input_embedding, resource_id,  top_n=5):
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
                similarity=CosineDistance("embedding", input_embedding)
            ).order_by("similarity").filter(similarity__lt=0.17, collection_id__in=collection_ids).defer("cmetadata").all()[:top_n]
            return similar_chunks
        else:
            LOGGING.info("Looking into all embeddings")
            similar_chunks = LangchainPgEmbedding.objects.annotate(
                similarity=CosineDistance("embedding", input_embedding)
            ).order_by("similarity").filter(similarity__lt=0.17).defer('cmetadata').all()[:top_n]
            return similar_chunks

    def format_prompt(self, user_name, context_chunks, user_input, chat_history):
        # if context_chunks:
        #     LOGGING.info("chunks availabe")
        return Constants.LATEST_PROMPT.format(name_1=user_name, input=user_input, context=context_chunks, chat_history=chat_history)
        # else:
        #     LOGGING.info("chunks not availabe")
        #     return Constants.NO_CUNKS_SYSTEM_MESSAGE.format(name_1=user_name, input=user_input)

    def condensed_question_prompt(self, chat_history, current_question):
        # greetings = ["hello", "hi", "greetings", "hey"]
        # if any(greeting in current_question.lower() for greeting in greetings):
        #     return current_question, False
        return Constants.CONDESED_QUESTION.format(chat_history=chat_history, current_question=current_question), True

    def generate_response(self, prompt, tokens=2000):
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",  # Use an appropriate engine
            prompt=prompt,
            temperature=0.1,
            max_tokens=tokens  # Adjust as necessary
        )
        return response.choices[0].text.strip(), response.get("usage")

    def chat_history_formated(self, chat_history):
            complete_chat_history =(f""" 
            Human: {chat_history.query or ''} 
            Assistant: {chat_history.query_response or 'No response'}""" 
            ) if chat_history else ""

            questions_chat_history = (f"""
            Human: {chat_history.query or ''}\n 
            """ 
            ) if chat_history else ""
            return complete_chat_history, questions_chat_history

class VectorDBBuilder:

    @shared_task
    def create_vector_db(resource_file, chunk_size=1000, chunk_overlap=200):
        # resource = ResourceFile(resource)
        status = "failed"
        resource_id = resource_file.get('id')
        try:
            vector = VectorBuilder()
            documents, status = vector.load_documents(
                resource_file.get("url"), resource_file.get("file"), resource_file.get("type"),
                resource_file.get("id"), resource_file.get("transcription"))
            LOGGING.info(f"Documents loaded for Resource ID: {resource_id}")
            if status == "completed":
                texts = vector.split_documents(documents, chunk_size, chunk_overlap)
                LOGGING.info(f"Documents splict completed for Resource ID: {resource_id}")
                embeddings = OpenAIEmbeddings()
                vector.get_embeddings(embeddings, texts, str(resource_file.get("id")), connectionString, resource_file)
                LOGGING.info(f"Embeddings creation completed for Resource ID: {resource_id}")
                documents="Embeddings Created Sucessfully"
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

    def get_input_embeddings(text, user_name=None, resource_id=None, chat_history=None):
        text=text.replace("\n", " ") # type: ignore
        documents, chunks = "", []
        retrival = Retrival()
        complete_history, history_question = retrival.chat_history_formated(chat_history)
        try:
            text, status = retrival.condensed_question_prompt(history_question, text)
            if status:
                text, tokens_uasage = retrival.generate_response(text)
            embedding = retrival.genrate_embeddings_from_text(text)
            chunks = retrival.find_similar_chunks(embedding, resource_id)
            documents =  " ".join([row.document for row in chunks])
            LOGGING.info(f"Similarity score for the query: {text}. Score: {' '.join([str(row.similarity) for row in chunks])} ")
            formatted_message = retrival.format_prompt(user_name, documents, text, complete_history)
            response, tokens_uasage =retrival.generate_response(formatted_message)
            return response, chunks, text, tokens_uasage
        except openai.error.InvalidRequestError as e:
            try:
                LOGGING.error(f"Error while generating response for query: {text}: Error {e}", exc_info=True)
                LOGGING.info(f"Retrying without chat history")
                formatted_message = retrival.format_prompt(user_name, documents, text, "")
                response, tokens_uasage = retrival.generate_response(formatted_message)
                return response, chunks, text, tokens_uasage
            except openai.error.InvalidRequestError as e:
                for attempt in range(3, 1, -1):  # Try with 3, then 2 chunks if errors continue
                    try:
                        documents = " ".join([row.document for row in chunks[:attempt]])
                        formatted_message = retrival.format_prompt(user_name, documents, text, "")
                        response,tokens_uasage = retrival.generate_response(formatted_message)
                        return response, chunks, text, tokens_uasage
                    except openai.error.InvalidRequestError as e:
                        LOGGING.info(f"Retrying with {attempt-1} chunks due to error: {e}")
                        continue  # Continue to the next attempt with fewer chunks

        except Exception as e:
            LOGGING.error(f"Error while generating response for query: {text}: Error {e}", exc_info=True)
            return str(e)
    
    # def get_input_embeddings_using_chain(text, user_name=None, resource_id=None, chat_history=None):
    #     retrival = Retrival()
    #     prompt_template = PromptTemplate(input_variables=["name_1", "context",  "input"],
    #         template=Constants.SYSTEM_MESSAGE_CHAIN,
    #         )
    #     complete_history, history_question = retrival.chat_history_formated(chat_history)
    #     complete_history=[] 
    #     complete_history.append((chat_history.condensed_question, chat_history.query_response))

    #     qa, retriver = ChainBuilder.create_qa_chain(
    #             vector_db = load_vector_db(resource_id),
    #             retriever_count=5,
    #             model_name=Constants.GPT_3_5_TURBO,
    #             temperature=Constants.TEMPERATURE,
    #             max_tokens=Constants.MAX_TOKENS,
    #             chain_type="stuff",
    #             prompt_template=prompt_template,
    #         )
    #     import asyncio

    #     def sync_async(coroutine):
    #         try:
    #             loop = asyncio.get_running_loop()
    #         except RuntimeError:  # No running event loop
    #             loop = asyncio.new_event_loop()
    #             asyncio.set_event_loop(loop)
    #             result = loop.run_until_complete(coroutine)
    #             loop.close()
    #         else:
    #             result = asyncio.run_coroutine_threadsafe(coroutine, loop).result()
    #         return result
    #     task = qa.ainvoke(
    #             {
    #                 "question": text,
    #                 "chat_history": complete_history,
    #                 "input": text,
    #                 "name_1": user_name,
    #             }
    #         )
    #     result = sync_async(task)
    #     import pdb; pdb.set_trace()

    #     for item in result['items']:  # Hypothetical structure; adjust based on actual structure
    #         # document = item['document']
    #         # metadata = item['metadata']
    #         uuid = item['uuid'] 
    #         print(uuid)
    #     return result["answer"], result["source_documents"], result["generated_question"], {}

    