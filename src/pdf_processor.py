import pdfplumber
import re
from typing import List, Dict, Tuple, Optional, Union
from openai import OpenAI
from type_schema import WineInfo, ParsedWineList
import unicodedata

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
    You are a wine expert specializing in parsing Japanese wine lists. Extract ONLY wine information from the provided text.
    
    CRITICAL RULES:
    1. Extract ONLY actual wines - ignore store information, addresses, contact details, or promotional text
    2. Each wine must be treated as a SEPARATE entity - do NOT mix information between different wines
    3. WINE NAME PRIORITY: If both Japanese (katakana/hiragana) and English/French names exist for the same wine, ALWAYS use the Japanese name as the primary wine name
    4. ONLY assign producer/details to a wine if they appear DIRECTLY associated with that specific wine
    5. If a producer name appears elsewhere in the text but not clearly linked to the wine, leave producer field empty
    6. When in doubt about producer association, leave it blank rather than guess
    
    WINE NAME EXTRACTION PRIORITY:
    - FIRST PRIORITY: Japanese wine names in katakana/hiragana (e.g., "ボニトゥラ NV", "プティ・シャブリ")
    - SECOND PRIORITY: Only use English/French names if no Japanese name is available
    - If you see both "CASA DE FONTE PEQUENA BONITURA NV" and "ボニトゥラ NV" for the same wine, use "ボニトゥラ NV"
    
    For each wine, extract ONLY information that is CLEARLY associated with that specific wine:
    - name (ワイン名) - REQUIRED, prefer Japanese names over English/French
    - producer (生産者) - ONLY if explicitly linked to this wine
    - country (国) - ONLY if explicitly linked to this wine  
    - region (地域) - ONLY if explicitly linked to this wine
    - grape_variety (ブドウ品種) - ONLY if explicitly linked to this wine
    - vintage (ヴィンテージ) - ONLY if explicitly linked to this wine
    - price (価格) - ONLY if explicitly linked to this wine
    - alcohol_content (アルコール度数) - ONLY if explicitly linked to this wine
    - description (説明・特徴) - ONLY if explicitly linked to this wine
    
    IMPORTANT: Prioritize Japanese wine names to make duplicate detection easier across different PDFs.
    
    Return ONLY valid JSON array format. If no wines can be identified, return an empty array [].
    """
    
    user_prompt = f"""
    Analyze this text and extract wine information. PRIORITIZE JAPANESE WINE NAMES over English/French names.
    
    {text}
    
    Rules for extraction:
    1. ALWAYS prefer Japanese wine names (katakana/hiragana) over English/French names
    2. If you see both "CASA DE FONTE PEQUENA BONITURA NV" and "ボニトゥラ NV", use "ボニトゥラ NV"
    3. Only include producer if it's clearly stated for that specific wine
    4. Do NOT assume producer information from other parts of the text
    5. If multiple wines appear, keep their information completely separate
    6. When in doubt about any field, leave it empty rather than guess
    
    Return only valid JSON array format. Example (showing Japanese name priority):
    [
        {{
            "name": "ボニトゥラ NV",
            "producer": "",
            "country": "ポルトガル",
            "region": "",
            "grape_variety": "ロウレイロ主体",
            "vintage": "NV",
            "price": "",
            "alcohol_content": "",
            "description": "繊細な泡が美しく立ち上り..."
        }}
    ]
    
    If no clear wines are found, return: []
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        # Parse the JSON response
        import json
        response_content = response.choices[0].message.content
        if response_content:
            wines_data = json.loads(response_content)
        else:
            wines_data = []
        
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

def normalize_wine_name(name: str) -> str:
    """Normalize wine name for basic text processing."""
    if not name:
        return ""
    
    # Remove HTML tags if present
    normalized = re.sub(r'<[^>]+>', '', name)
    
    # Handle Japanese vs non-Japanese text differently
    if contains_japanese(name):
        # For Japanese text, basic normalization
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        
        # Normalize Japanese punctuation variations
        normalized = normalized.replace('・', '').replace('･', '')  # Remove middle dots
        normalized = normalized.replace('　', ' ')  # Replace full-width space with regular space
        
    else:
        # For non-Japanese text, normalize accents and case
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        normalized = normalized.strip().lower()
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
    
    # Clean up multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized.strip())
    
    return normalized.strip()

def contains_japanese(text: str) -> bool:
    """Check if text contains Japanese characters (hiragana, katakana, kanji)."""
    if not text:
        return False
    
    # Clean the text first - remove HTML entities and normalize
    import html
    text = html.unescape(text)  # Convert HTML entities like &nbsp; 
    
    # Japanese Unicode ranges - expanded for better coverage
    japanese_ranges = [
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
        (0x4E00, 0x9FAF),  # CJK Unified Ideographs (Kanji)
        (0x3400, 0x4DBF),  # CJK Extension A
        (0xFF66, 0xFF9F),  # Half-width Katakana
        (0x3000, 0x303F),  # CJK Symbols and Punctuation
        (0xFF01, 0xFF60),  # Full-width ASCII variants
    ]
    
    # Count Japanese characters
    japanese_char_count = 0
    total_chars = 0
    
    for char in text:
        if char.isspace():
            continue
        total_chars += 1
        char_code = ord(char)
        for start, end in japanese_ranges:
            if start <= char_code <= end:
                japanese_char_count += 1
                break
    
    # Return True if any Japanese characters found
    return japanese_char_count > 0

def format_wines_to_markdown(wines: List[WineInfo]) -> str:
    """Convert wine information to markdown format."""
    if not wines:
        return "# Wine Information\n\nNo wines selected."
    
    markdown_content = "# Selected Wines Information\n\n"
    
    for i, wine in enumerate(wines, 1):
        markdown_content += f"## Wine {i}: {wine.name}\n\n"
        
        # Basic Information
        if wine.producer:
            markdown_content += f"**Producer:** {wine.producer}\n\n"
        
        if wine.country:
            markdown_content += f"**Country:** {wine.country}\n\n"
        
        if wine.region:
            markdown_content += f"**Region:** {wine.region}\n\n"
        
        if wine.grape_variety:
            markdown_content += f"**Grape Variety:** {wine.grape_variety}\n\n"
        
        if wine.vintage:
            markdown_content += f"**Vintage:** {wine.vintage}\n\n"
        
        if wine.price:
            markdown_content += f"**Price:** {wine.price}\n\n"
        
        if wine.alcohol_content:
            markdown_content += f"**Alcohol Content:** {wine.alcohol_content}\n\n"
        
        if wine.description:
            markdown_content += f"**Description:**\n{wine.description}\n\n"
        
        # Source information
        if wine.source_file:
            markdown_content += f"**Source File(s):** {wine.source_file}\n\n"
        
        # Separator between wines
        if i < len(wines):
            markdown_content += "---\n\n"
    
    return markdown_content

def parse_wine_markdown(markdown_content: str) -> dict:
    """Parse markdown content and extract wine information."""
    wine_data = {
        'name': '',
        'producer': '',
        'country': '',
        'region': '',
        'grape_variety': '',
        'vintage': '',
        'price': '',
        'alcohol_content': '',
        'description': ''
    }
    
    lines = markdown_content.split('\n')
    current_field = None
    description_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Extract wine name from header
        if line.startswith('# ') or line.startswith('## '):
            # Try to extract wine name from headers like "# Wine 1: Wine Name" or "## Wine Name"
            if ':' in line:
                wine_data['name'] = line.split(':', 1)[1].strip()
            else:
                # Remove header markers and use as name
                wine_data['name'] = line.replace('#', '').strip()
        
        # Extract field information
        elif line.startswith('**') and line.endswith('**') and ':' not in line:
            # This is a field header like "**Description:**"
            current_field = line.replace('*', '').replace(':', '').lower().replace(' ', '_')
            if current_field == 'grape_variety':
                current_field = 'grape_variety'
            elif current_field == 'alcohol_content':
                current_field = 'alcohol_content'
        
        elif line.startswith('**') and ':**' in line:
            # This is a field with value like "**Producer:** Domain Name"
            field_and_value = line.replace('*', '').split(':', 1)
            if len(field_and_value) == 2:
                field_name = field_and_value[0].strip().lower().replace(' ', '_')
                field_value = field_and_value[1].strip()
                
                # Map field names
                field_mapping = {
                    'producer': 'producer',
                    'country': 'country',
                    'region': 'region',
                    'grape_variety': 'grape_variety',
                    'vintage': 'vintage',
                    'price': 'price',
                    'alcohol_content': 'alcohol_content'
                }
                
                if field_name in field_mapping:
                    wine_data[field_mapping[field_name]] = field_value
            current_field = None
        
        elif current_field == 'description' and line and not line.startswith('**'):
            # Collect description lines
            description_lines.append(line)
        
        elif line and not line.startswith('**') and not line.startswith('#') and not line.startswith('---'):
            # If we're in description mode, collect the line
            if current_field == 'description':
                description_lines.append(line)
    
    # Join description lines
    if description_lines:
        wine_data['description'] = '\n'.join(description_lines).strip()
    
    return wine_data