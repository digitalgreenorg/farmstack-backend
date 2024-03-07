from langchain.chains import ConversationalRetrievalChain
from langchain_community.chat_models import ChatOpenAI

from core import settings


class ChainBuilder:
    def create_qa_chain(
        vector_db,
        retriever_count,
        model_name,
        temperature,
        max_tokens,
        chain_type,
        prompt_template,
    ):
        import pdb; pdb.set_trace()

        retriever = vector_db.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.5, "k": 5})
        llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=True,
        )
        qa = ConversationalRetrievalChain.from_llm(
            llm=llm,
            chain_type=chain_type,
            retriever=retriever,
            verbose=True,
            combine_docs_chain_kwargs={"prompt": prompt_template},
        )
        qa.return_source_documents = True
        qa.return_generated_question = True
        # qa.return_source
        return qa, retriever
