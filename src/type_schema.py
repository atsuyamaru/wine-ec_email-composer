from pydantic import BaseModel
from typing import Optional, List

class EmailContents(BaseModel):
    email_title: str
    preview_text: str
    introduction_latter_part: str
    editor_note: str

class WineInfo(BaseModel):
    name: str
    producer: Optional[str] = None
    country: Optional[str] = None
    cepage: Optional[str] = None
    price: Optional[str] = None
    vintage: Optional[str] = None
    description: Optional[str] = None
    source: str  # "wine_list" or "wine_menu" to identify which PDF
    page_number: Optional[int] = None

class ParsedWines(BaseModel):
    wines: List[WineInfo]
    duplicates: List[str]  # List of wine names that appear in both PDFs
