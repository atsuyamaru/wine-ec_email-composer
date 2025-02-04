from pydantic import BaseModel

class EmailContents(BaseModel):
    email_title: str
    preview_text: str
    introduction_latter_part: str
    editor_note: str
