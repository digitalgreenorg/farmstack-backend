
import logging
from ai.open_ai_utils import find_similar_chunks, generate_response, genrate_embeddings_from_text
import openai
from ai.utils import chat_history_formated, condensed_question_prompt, format_prompt

LOGGING = logging.getLogger(__name__)

class Retrival:

    def get_input_embeddings(text, user_name=None, resource_id=None, chat_history=None):
        text=text.replace("\n", " ") # type: ignore
        documents, chunks = "", []
        retrival = Retrival()
        complete_history, history_question = chat_history_formated(chat_history)
        try:
            text, status = condensed_question_prompt(history_question, text)
            if status:
                text, tokens_uasage = generate_response(text)
            embedding = genrate_embeddings_from_text(text)
            chunks = find_similar_chunks(embedding, resource_id)
            documents =  " ".join([row.document for row in chunks])
            LOGGING.info(f"Similarity score for the query: {text}. Score: {' '.join([str(row.similarity) for row in chunks])} ")
            formatted_message = format_prompt(user_name, documents, text, complete_history)
            print(formatted_message)
            response, tokens_uasage =generate_response(formatted_message, 500)
            return response, chunks, text, tokens_uasage
        except openai.error.InvalidRequestError as e:
            try:
                LOGGING.error(f"Error while generating response for query: {text}: Error {e}", exc_info=True)
                LOGGING.info(f"Retrying without chat history")
                formatted_message = format_prompt(user_name, documents, text, "")
                response, tokens_uasage = generate_response(formatted_message, 500)
                return response, chunks, text, tokens_uasage
            except openai.error.InvalidRequestError as e:
                for attempt in range(3, 1, -1):  # Try with 3, then 2 chunks if errors continue
                    try:
                        documents = " ".join([row.document for row in chunks[:attempt]])
                        formatted_message = format_prompt(user_name, documents, text, "")
                        response,tokens_uasage = generate_response(formatted_message, 500)
                        return response, chunks, text, tokens_uasage
                    except openai.error.InvalidRequestError as e:
                        LOGGING.info(f"Retrying with {attempt-1} chunks due to error: {e}")
                        continue  # Continue to the next attempt with fewer chunks
        except Exception as e:
            LOGGING.error(f"Error while generating response for query: {text}: Error {e}", exc_info=True)
            return str(e)
    

    def get_chunks(text, user_name=None, resource_id=None, chat_history=None):
        text=text.replace("\n", " ") # type: ignore
        documents, chunks = "", []
        retrival = Retrival()
        try:
            response = get_quadrant_db_chunks(text)
            return response, chunks, text, tokens_uasage
        except Exception as e:
            LOGGING.error(f"Error while generating response for query: {text}: Error {e}", exc_info=True)
            return str(e)
    
