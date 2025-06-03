import pdfplumber
import re
from typing import List, Dict, Optional
from openai import OpenAI
from .type_schema import WineInfo, ParsedWineList

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from uploaded PDF file."""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def parse_wine_info_with_ai(text: str, client: OpenAI) -> ParsedWineList:
    """Use OpenAI to parse wine information from extracted text."""
    
    system_prompt = """
    You are a wine expert. Extract wine information from the provided Japanese wine list text.
    
    For each wine, extract:
    - name (ワイン名)
    - producer (生産者)
    - country (国)
    - region (地域)
    - grape_variety (ブドウ品種)
    - vintage (ヴィンテージ)
    - price (価格)
    - alcohol_content (アルコール度数)
    - description (説明・特徴)
    
    Return the data in JSON format as an array of wine objects.
    If some information is not available, omit those fields.
    """
    
    user_prompt = f"""
    Please extract wine information from this Japanese wine list text:
    
    {text}
    
    Return only valid JSON array format like this:
    [
        {{
            "name": "ワイン名",
            "producer": "生産者名",
            "country": "国名",
            "region": "地域名",
            "grape_variety": "ブドウ品種",
            "vintage": "年",
            "price": "価格",
            "alcohol_content": "アルコール度数",
            "description": "説明"
        }}
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        # Parse the JSON response
        import json
        wines_data = json.loads(response.choices[0].message.content)
        
        # Convert to WineInfo objects
        wines = []
        for wine_data in wines_data:
            wine = WineInfo(**wine_data)
            wines.append(wine)
        
        return ParsedWineList(wines=wines, raw_text=text)
        
    except Exception as e:
        # Fallback: create a basic wine entry with the raw text
        fallback_wine = WineInfo(
            name="Extracted from PDF",
            description=f"Error parsing: {str(e)}\n\nRaw text:\n{text[:500]}..."
        )
        return ParsedWineList(wines=[fallback_wine], raw_text=text)

def format_wines_for_display(parsed_wines: ParsedWineList) -> str:
    """Format parsed wines for display in Streamlit."""
    if not parsed_wines.wines:
        return "No wines found in the PDF."
    
    formatted_text = f"Found {len(parsed_wines.wines)} wines:\n\n"
    
    for i, wine in enumerate(parsed_wines.wines, 1):
        formatted_text += f"**Wine {i}: {wine.name}**\n"
        if wine.producer:
            formatted_text += f"- Producer: {wine.producer}\n"
        if wine.country:
            formatted_text += f"- Country: {wine.country}\n"
        if wine.region:
            formatted_text += f"- Region: {wine.region}\n"
        if wine.grape_variety:
            formatted_text += f"- Grape Variety: {wine.grape_variety}\n"
        if wine.vintage:
            formatted_text += f"- Vintage: {wine.vintage}\n"
        if wine.price:
            formatted_text += f"- Price: {wine.price}\n"
        if wine.alcohol_content:
            formatted_text += f"- Alcohol: {wine.alcohol_content}\n"
        if wine.description:
            formatted_text += f"- Description: {wine.description}\n"
        formatted_text += "\n"
    
    return formatted_text