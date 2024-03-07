import logging
from langchain.document_loaders import (
    CSVLoader,
    PyMuPDFLoader,
    UnstructuredHTMLLoader,
)
from docx import Document

LOGGING = logging.getLogger(__name__)

class LoadDocuments:

    def load_by_file_extension(self, file, temp_pdf):
        if file.endswith(".pdf"):
            LOGGING.info(f"pdf file loader started for file: {file}")
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
