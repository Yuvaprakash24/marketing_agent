import tempfile
from pathlib import Path
from typing import Union

from core.storage_backends import staging_storage
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentToKnowledgeBase:
    """Turns an uploaded PDF, DOCX or TXT file into knowledge base text."""

    SUPPORTED_EXTENSIONS = ('.pdf', '.txt', '.docx')

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    def process_document(self, file_path: Union[str, Path]) -> str:
        temp_path = None

        # The path may be relative to the staging directory rather than the cwd.
        if not Path(file_path).exists():
            with staging_storage.open(str(file_path), "rb") as remote_file:
                suffix = Path(str(file_path)).suffix
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(remote_file.read())
                tmp.close()
                temp_path = tmp.name
                file_path = tmp.name

        try:
            ext = Path(str(file_path)).suffix.lower()
            if ext == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif ext == ".txt":
                loader = TextLoader(str(file_path), encoding="utf-8", autodetect_encoding=True)
            elif ext == ".docx":
                loader = Docx2txtLoader(str(file_path))
            else:
                raise ValueError(
                    f"Unsupported file type: {ext}. "
                    f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
                )

            documents = loader.load()
            chunks = self.text_splitter.split_documents(documents)
            return "\n".join(chunk.page_content for chunk in chunks)

        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
