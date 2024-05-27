# from langchain.document_loaders import PdfLoader
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
from uuid import UUID
import openai
from django.db import models
from django.db.models import Subquery
from django.db.models.functions import Cast
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Batch, PointStruct, OptimizersConfigDiff, HnswConfigDiff, PayloadSchemaType, SearchParams, Filter, FieldCondition, MatchValue
from dotenv import load_dotenv
from langchain.embeddings.openai import OpenAIEmbeddings
from pgvector.django import CosineDistance
from core import settings
from core.constants import Constants
from datahub.models import LangchainPgCollection, LangchainPgEmbedding, ResourceFile
from utils.pgvector import PGVector
from langchain.retrievers.merger_retriever import MergerRetriever

LOGGING = logging.getLogger(__name__)
load_dotenv()

db_settings = settings.DATABASES["default"]
qdrant_settings = settings.DATABASES["vector_db"]
encoded_user = quote_plus(db_settings[Constants.USER.upper()])
encoded_password = quote_plus(db_settings[Constants.PASSWORD])


def get_embeddings(docs, resource, file_id):
    embedded_data = {}
    document_text_list = [document.page_content for document in docs]
    openai_client = openai.Client(api_key=settings.OPENAI_API_KEY)
    embedding_model = Constants.TEXT_EMBEDDING_3_SMALL
    try:
        result = []
        if len(document_text_list) > 2000:
            loop_number = len(document_text_list)//2000
            start_point = 0
            for num in range(loop_number+1):
                response = openai_client.embeddings.create(
                    input=document_text_list[start_point:(2000*(num+1))], model=embedding_model)
                start_point = (2000*(num+1))
                result.append(response)
        else:
            response = openai_client.embeddings.create(
                input=document_text_list, model=embedding_model)
            result.append(response)
    except Exception as e:
        result = None
        LOGGING.error(f"Exception occurred in creating embedding {str(e)}")
        return embedded_data
    if result != []:
        LOGGING.info(
            f"Creating the embedding dictonary, length is  {len(result)}")
        start = 0
        for embedd_data in result:
            for idx, (data, text) in enumerate(zip(embedd_data.data, document_text_list)):
                embedded_data[idx+start] = {}
                embedded_data[idx+start]['text'] = text
                embedded_data[idx+start]['vector'] = data.embedding
                embedded_data[idx+start]["source"] =  resource.get("url") if resource.get("url") else resource.get("file")
                embedded_data[idx+start]["context-type"] = "video/pdf" if resource.get("type") =="youtube" else "text/pdf"
                embedded_data[idx+start]["country"] = resource.get("country",'').lower().strip()
                embedded_data[idx+start]["state"] = resource.get("state", '').lower().strip()
                embedded_data[idx+start]["distict"] = resource.get("district", '').lower().strip()
                embedded_data[idx+start]["category"] = resource.get("category", '').lower().strip()
                embedded_data[idx+start]["sub_category"] = resource.get("sub_category",'').lower().strip()
                embedded_data[idx+start]["resource_file"] = file_id
                embedded_data[idx+start][Constants.URL] = resource.get(Constants.URL)
            start += idx+1
    return embedded_data

def create_qdrant_client(collection_name: str):
    client = QdrantClient(url=qdrant_settings.get('HOST'), port=qdrant_settings.get(
        'QDRANT_PORT_HTTP'), grpc_port=qdrant_settings.get('PORT_GRPC'), prefer_grpc=qdrant_settings.get('GRPC_CONNECT'))
    try:
        client.get_collection(collection_name=collection_name)
        points_count = client.count(collection_name=collection_name).count + 1
    except:
        points_count = 1
        client.create_collection(
            collection_name,
            vectors_config=VectorParams(
                size=1536,
                distance=Distance.COSINE,
            ),
            hnsw_config=HnswConfigDiff(
                ef_construct=200,
                payload_m=16,
                m=0,
            ),
            # optimizers_config= OptimizersConfigDiff(indexing_threshold=0)
        )
        LOGGING.info(
            f"===========Created a new collection with metadata {collection_name}")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="category",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="sub_category",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    return client, points_count


def insert_chunking_in_db(documents: dict):
    collection_name = qdrant_settings.get('COLLECTION_NAME')
    qdrant_client, points = create_qdrant_client(collection_name)
    try:
        points = [
            PointStruct(
                id=idx + points,
                vector=data['vector'],
                payload={"text": data['text'], 
                        "category": data.get('category', ''), 
                        "sub_category": data.get('sub_category'), 
                        "state": data.get('state', ''),
                        "resource_file":data.get('resource_file',''),
                        "distict":data.get('distict',''),
                        "country":data.get('country',''),
                        "resource_file":data.get('resource_file','')
                        },
            )
            for idx, data in enumerate(documents.values())
        ]
        qdrant_client.upsert(collection_name, points)
        return True
    except Exception as e:
        LOGGING.error(f"Exception occured in inserting in collection {str(e)}")
        return False


def transcribe_audio(self, audio_bytes, language="en-US"):
    try:
        transcript = openai.Audio.translate(
            file=audio_bytes, model=Constants.WISHPER_1)
        return transcript
    except Exception as e:
        print("Transcription error:", str(e))
        return str(e)


def generate_response(prompt, tokens=2000):
    response = openai.Completion.create(
        engine=Constants.GPT_TURBO_INSTRUCT,  # Use an appropriate engine
        prompt=prompt,
        temperature=0.1,
        max_tokens=tokens  # Adjust as necessary
    )
    return response.choices[0].text.strip(), response.get(Constants.USAGE)


# Commentend out Not required

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
    retrievals = []
    vector_db = PGVector(
            collection_name=str("e7d810ae-3fee-4412-b9a8-04f0935e7acf"),
            connection_string=connectionString,
            embedding_function=embeddings,
        )
    print(LangchainPgEmbedding.objects.filter(collection_id='e7d810ae-3fee-4412-b9a8-04f0935e7acf').values('document'))
    retriever = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 5, "score_threshold":0.5})
    return retriever
    def setup_retriever(collection_id):
        vector_db = PGVector(
            collection_name=str(collection_id),
            connection_string=connectionString,
            embedding_function=embeddings,
        )
        retriever = vector_db.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5, "k": 5})
        return retriever

    # Use ThreadPoolExecutor to run setup_retriever concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Create a future for each setup_retriever call
        future_to_collection_id = {executor.submit(setup_retriever, collection_id): collection_id for collection_id in collection_ids}

        for future in as_completed(future_to_collection_id):
            collection_id = future_to_collection_id[future]
            try:
                retriever = future.result()  # Retrieve the result from the future
                retrievals.append(retriever)  # Add the successfully created retriever to the list
            except Exception as exc:
                print(f'{collection_id} generated an exception: {exc}')
    # import pdb; pdb.set_trace()
    # lotr = MergerRetriever(retrievers=retrievals)
    # lotr = CustomRetriever(retrievals)
    custom_retriever = MergerRetriever(retrievers = retrievals)

    return retrievals

# Older OpenAI version
def genrate_embeddings_from_text(text):
    response = openai.Embedding.create(input=text, model=embedding_model)
    embedding = response['data'][0]['embedding']
    return embedding


# Need To confirm why it is required

def find_similar_chunks(input_embedding, resource_id,  top_n=5):
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
            similarity=CosineSimilarity("embedding", input_embedding)
        ).order_by("similarity").filter(similarity__lt=0.17).defer('cmetadata').all()[:top_n]
        return similar_chunks

def query_qdrant_collection(query, category, sub_category, state, k, threshold=0.4):
    collection_name = qdrant_settings.get('COLLECTION_NAME')
    qdrant_client, points = create_qdrant_client(collection_name)
    openai_client = openai.Client(api_key=settings.OPENAI_API_KEY)
    vector = openai_client.embeddings.create(
        input=[query],
        model=Constants.TEXT_EMBEDDING_3_SMALL,
    ).data[0].embedding
    sub_category = re.sub(r'[^a-zA-Z0-9_]', '-', sub_category)
    qdrant_filter = Filter(must=[FieldCondition(key="category", match=MatchValue(value=category,),), FieldCondition(key="sub_category", match=MatchValue(
        value=sub_category,),), FieldCondition(key="state", match=MatchValue(value=state,),),])
    if sub_category is None or sub_category == "":
        qdrant_filter = Filter(must=[FieldCondition(
            key="state", match=MatchValue(value=state,),),])
    LOGGING.info(
        f"Collection and filter name for qdrant is {state},  {sub_category}, {category}, {k}, {threshold}")
    try:
        search_data = qdrant_client.search(
            collection_name=state,
            query_vector=vector,
            query_filter=qdrant_filter,
            score_threshold=threshold,
            limit=k
        )
    except Exception as e:
        LOGGING.error(f"Exception occured in qdrant db connection {str(e)}")
        return []
    return search_data
