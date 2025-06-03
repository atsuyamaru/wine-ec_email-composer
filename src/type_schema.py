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
    region: Optional[str] = None
    grape_variety: Optional[str] = None
    vintage: Optional[str] = None
    price: Optional[str] = None
    alcohol_content: Optional[str] = None
    description: Optional[str] = None
    source_file: Optional[str] = None

class ParsedWineList(BaseModel):
    wines: List[WineInfo]
    raw_text: str
