import fitz


async def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """
    Extracts text content and page count from a PDF file.
    
    Uses a context manager to ensure the document is properly closed
    even if an error occurs during processing.
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        A tuple containing (extracted_text, page_count).
        
    Raises:
        fitz.FileDataError: If the file is not a valid PDF.
        FileNotFoundError: If the file does not exist.
    """
    with fitz.open(file_path) as doc:
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        page_count = len(doc)
    return "".join(text_parts), page_count
