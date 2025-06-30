import pdfplumber
import re
from typing import List
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

def normalize_wine_name(name: str) -> str:
    """Normalize wine name for comparison by removing common variations."""
    if not name:
        return ""
    
    # Remove HTML tags if present
    normalized = re.sub(r'<[^>]+>', '', name)
    
    # Handle Japanese vs non-Japanese text differently
    if contains_japanese(name):
        # For Japanese text, only remove extra spaces - don't change characters
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        # Remove some common suffixes in Japanese
        japanese_suffixes = [
            r'\s*NV$', r'\s*[0-9]{4}$',  # Remove vintage years and NV
            r'\s*赤$', r'\s*白$', r'\s*ロゼ$',  # Remove color indicators
        ]
        for suffix in japanese_suffixes:
            normalized = re.sub(suffix, '', normalized)
    else:
        # For non-Japanese text, normalize accents and case
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        normalized = normalized.strip().lower()
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common wine type suffixes and descriptors
        wine_suffixes = [
            r'\s+(nv|non vintage|brut|sec|demi-sec|doux|rouge|blanc|rose|vin|wine)$',
            r'\s+(zero|dosage zero|extra brut|extra dry)$',
            r'\s+(reserve|reserva|gran reserva|riserva)$',
            r'\s+(cuvee|special|selection|premium|classic)$'
        ]
        for suffix in wine_suffixes:
            normalized = re.sub(suffix, '', normalized)
        
        # Remove years (2-4 digits)
        normalized = re.sub(r'\s+\d{2,4}$', '', normalized)
        
        # Remove common French/English articles and prepositions
        articles = [
            r'^(le|la|les|de|du|des|the|a|an|von|vom|zur|della|del|di|da)\s+',
            r'\s+(de|du|des|von|vom|zur|della|del|di|da)\s+',
        ]
        for article in articles:
            normalized = re.sub(article, ' ', normalized)
        
        # Remove common wine region indicators
        normalized = re.sub(r'\s+(aoc|aop|doc|docg|igp|vdp|appellation)\s*', ' ', normalized)
    
    # Clean up multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized.strip())
    
    # Handle special characters differently for Japanese vs non-Japanese
    if contains_japanese(normalized):
        # For Japanese, only remove minimal punctuation, keep ・ and ー
        normalized = re.sub(r'[()（）\[\]【】""\'""]', '', normalized)
    else:
        # For non-Japanese, remove all punctuation except hyphens and dots
        normalized = re.sub(r'[^\w\s\-\.]', '', normalized)
    
    return normalized

def extract_wine_identity(wine: WineInfo) -> dict:
    """Extract core wine identity components for matching."""
    
    # Main wine name processing
    name = wine.name or ""
    normalized_name = normalize_wine_name(name)
    
    # Extract wine type/style indicators
    wine_types = set()
    type_patterns = [
        r'(champagne|cremant|cava|prosecco|sparkling)',
        r'(chardonnay|sauvignon|pinot|merlot|cabernet|syrah|shiraz)',
        r'(rouge|blanc|rose|red|white|pink)',
        r'(brut|sec|demi|doux|dry|sweet)',
        r'(reserve|premium|grand|cuvee)',
    ]
    
    for pattern in type_patterns:
        matches = re.findall(pattern, normalized_name.lower())
        wine_types.update(matches)
    
    # Extract geographic indicators
    regions = set()
    if wine.region:
        regions.add(normalize_wine_name(wine.region))
    if wine.country:
        regions.add(normalize_wine_name(wine.country))
    
    # Extract key name components (remove common words)
    stop_words = {
        'de', 'du', 'des', 'le', 'la', 'les', 'the', 'and', 'et', 'von', 'vom', 'della', 'del', 'di', 'da',
        'wine', 'vin', 'vino', 'domaine', 'chateau', 'estate', 'winery', 'cave', 'maison'
    }
    
    name_words = set()
    for word in normalized_name.split():
        if len(word) > 2 and word not in stop_words:
            name_words.add(word)
    
    # Extract producer info
    producer_words = set()
    if wine.producer:
        producer_norm = normalize_wine_name(wine.producer)
        for word in producer_norm.split():
            if len(word) > 2 and word not in stop_words:
                producer_words.add(word)
    
    return {
        'name_words': name_words,
        'producer_words': producer_words,
        'wine_types': wine_types,
        'regions': regions,
        'grape_variety': normalize_wine_name(wine.grape_variety) if wine.grape_variety else None,
        'original_name': name,
        'normalized_name': normalized_name
    }

def calculate_identity_similarity(identity1: dict, identity2: dict) -> float:
    """Calculate similarity between two wine identities."""
    
    similarities = []
    
    # 1. Core name word overlap (most important)
    name_words1 = identity1['name_words']
    name_words2 = identity2['name_words']
    
    if name_words1 and name_words2:
        name_intersection = name_words1.intersection(name_words2)
        name_union = name_words1.union(name_words2)
        name_overlap = len(name_intersection) / len(name_union) if name_union else 0
        similarities.append(('name_words', name_overlap, 0.4))
        
        # Boost if most key words match
        if len(name_intersection) >= min(len(name_words1), len(name_words2)) * 0.7:
            similarities.append(('name_boost', 1.0, 0.2))
    
    # 2. Producer word overlap
    producer_words1 = identity1['producer_words']
    producer_words2 = identity2['producer_words']
    
    if producer_words1 and producer_words2:
        producer_intersection = producer_words1.intersection(producer_words2)
        producer_union = producer_words1.union(producer_words2)
        producer_overlap = len(producer_intersection) / len(producer_union) if producer_union else 0
        similarities.append(('producer', producer_overlap, 0.2))
    
    # 3. Wine type/style matching
    types1 = identity1['wine_types']
    types2 = identity2['wine_types']
    
    if types1 and types2:
        type_intersection = types1.intersection(types2)
        if type_intersection:
            similarities.append(('wine_types', 1.0, 0.15))
    
    # 4. Geographic matching
    regions1 = identity1['regions']
    regions2 = identity2['regions']
    
    if regions1 and regions2:
        region_intersection = regions1.intersection(regions2)
        if region_intersection:
            similarities.append(('regions', 1.0, 0.1))
    
    # 5. Grape variety matching
    grape1 = identity1['grape_variety']
    grape2 = identity2['grape_variety']
    
    if grape1 and grape2 and grape1 == grape2:
        similarities.append(('grape', 1.0, 0.05))
    
    # 6. Substring matching for different language versions
    name1 = identity1['normalized_name']
    name2 = identity2['normalized_name']
    
    if name1 and name2 and len(name1) > 5 and len(name2) > 5:
        # Check if significant portions of names are contained in each other
        longer, shorter = (name1, name2) if len(name1) > len(name2) else (name2, name1)
        if len(shorter) > 0:
            # Look for substring matches
            words_shorter = set(shorter.split())
            words_longer = set(longer.split())
            word_containment = len(words_shorter.intersection(words_longer)) / len(words_shorter)
            
            if word_containment > 0.5:
                similarities.append(('substring', word_containment, 0.1))
    
    # Calculate final score
    if not similarities:
        return 0.0
    
    total_weight = sum(weight for _, _, weight in similarities)
    weighted_sum = sum(score * weight for _, score, weight in similarities)
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0

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

def get_japanese_content_score(wine: WineInfo) -> int:
    """Calculate how much Japanese content a wine entry has with much higher priority for wine names."""
    score = 0
    
    # Check each field for Japanese content with VERY high priority for wine name
    fields_to_check = [
        (wine.name, 20),          # Wine name is EXTREMELY important - much higher weight
        (wine.producer, 3),       # Producer is important
        (wine.description, 3),    # Description is important
        (wine.region, 1),         # Region is somewhat important
        (wine.country, 1),        # Country is somewhat important
        (wine.grape_variety, 1),  # Grape variety is somewhat important
    ]
    
    for field_value, weight in fields_to_check:
        if field_value and contains_japanese(field_value):
            score += weight
    
    return score

def calculate_keyword_overlap(wine1: WineInfo, wine2: WineInfo) -> float:
    """Calculate keyword overlap between two wine names."""
    # Extract keywords from wine names using the identity extraction logic
    identity1 = extract_wine_identity(wine1)
    identity2 = extract_wine_identity(wine2)
    
    keywords1 = identity1['name_words']
    keywords2 = identity2['name_words']
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # Calculate Jaccard similarity (intersection over union)
    intersection = keywords1.intersection(keywords2)
    union = keywords1.union(keywords2)
    
    return len(intersection) / len(union) if union else 0.0

def calculate_wine_similarity(wine1: WineInfo, wine2: WineInfo) -> float:
    """Calculate similarity score between two wines (0.0 to 1.0) using enhanced matching."""
    
    # Extract wine identities
    identity1 = extract_wine_identity(wine1)
    identity2 = extract_wine_identity(wine2)
    
    # Use the identity-based similarity as base
    similarity = calculate_identity_similarity(identity1, identity2)
    
    # Enhanced Japanese/English matching
    name1 = identity1['normalized_name']
    name2 = identity2['normalized_name']
    
    # Check for transliteration matches
    transliteration_score = check_transliteration_similarity(wine1.name, wine2.name)
    similarity = max(similarity, transliteration_score)
    
    # ENHANCED: General substring matching for producer+wine vs wine-only cases
    substring_score = check_substring_similarity(wine1.name, wine2.name)
    similarity = max(similarity, substring_score)
    
    # Enhanced word-based matching
    if name1 and name2:
        # Split into words and check for significant overlap
        words1 = set(w for w in name1.split() if len(w) > 3)
        words2 = set(w for w in name2.split() if len(w) > 3)
        
        if words1 and words2:
            common_words = words1.intersection(words2)
            if common_words:
                word_similarity = len(common_words) / min(len(words1), len(words2))
                # Boost similarity for wine-specific terms
                key_wine_terms = {'cremant', 'loire', 'champagne', 'chablis', 'bordeaux', 'burgundy', 'sancerre', 'bonitura', 'tempranillo', 'cabernet', 'pinot', 'chardonnay'}
                if any(term in name1 or term in name2 for term in key_wine_terms):
                    if common_words:
                        similarity = max(similarity, word_similarity * 0.9)
    
    # Enhanced producer matching
    if wine1.producer and wine2.producer:
        prod1 = normalize_wine_name(wine1.producer)
        prod2 = normalize_wine_name(wine2.producer)
        
        if prod1 and prod2:
            prod_words1 = set(w for w in prod1.split() if len(w) > 2)
            prod_words2 = set(w for w in prod2.split() if len(w) > 2)
            
            if prod_words1.intersection(prod_words2):
                similarity = max(similarity, 0.7)
    
    return min(1.0, similarity)

def check_transliteration_similarity(name1: str, name2: str) -> float:
    """Check similarity between potentially transliterated names (Japanese/English)."""
    if not name1 or not name2:
        return 0.0
    
    # Common wine name transliterations
    transliteration_pairs = {
        # Exact matches
        'ボニトゥラ': ['bonitura'],
        'ピノ・グリージョ': ['pinot grigio', 'pinot gris'],
        'コート・ド・ガスコーニュ': ['cotes de gascogne', 'côtes de gascogne'],
        'モンテ・アラヤ・テンプラニーリョ・ブランコ': ['monte araya tempranillo blanco'],
        'プティ・シャブリ': ['petit chablis'],
        'トスカーナ・ロサート': ['toscana rosato'],
        'アルマ・デ・チリ': ['alma de chile'],
        'ピノ・ノワール': ['pinot noir'],
        'カベルネ・ソーヴィニヨン': ['cabernet sauvignon'],
        'ラソン': ['razon'],
        'シャルドネ': ['chardonnay'],
        'メルロー': ['merlot'],
        'リースリング': ['riesling'],
        'ソーヴィニヨン・ブラン': ['sauvignon blanc'],
        'シラー': ['syrah', 'shiraz'],
        
        # Partial matches for regions/terms
        'フランス': ['france', 'french'],
        'イタリア': ['italy', 'italian'],
        'スペイン': ['spain', 'spanish'],
        'ドイツ': ['germany', 'german'],
        'アメリカ': ['america', 'american', 'usa'],
        'カリフォルニア': ['california'],
        'ナパ・ヴァレー': ['napa valley'],
        'ソノマ': ['sonoma'],
        'ボルドー': ['bordeaux'],
        'ブルゴーニュ': ['burgundy', 'bourgogne'],
        'ロワール': ['loire'],
        'シャンパーニュ': ['champagne'],
        'プロヴァンス': ['provence'],
        'ピエモンテ': ['piemonte', 'piedmont'],
        'トスカーナ': ['toscana', 'tuscany'],
        'リオハ': ['rioja'],
    }
    
    # Normalize names for comparison
    norm1 = normalize_wine_name(name1)
    norm2 = normalize_wine_name(name2)
    
    # ENHANCED: Check substring/contains matching first
    # This handles cases like "CASA DE FONTE PEQUENA BONITURA NV" vs "ボニトゥラ"
    for jp_name, en_variants in transliteration_pairs.items():
        jp_norm = normalize_wine_name(jp_name)
        
        # Check substring contains (more loose matching)
        for en_var in en_variants:
            # Case 1: Japanese in name1, English in name2
            if jp_norm in norm1 and en_var in norm2:
                return 0.95
            # Case 2: English in name1, Japanese in name2  
            if en_var in norm1 and jp_norm in norm2:
                return 0.95
            # Case 3: One contains the other as substring
            if jp_norm in norm2 and en_var in norm1:
                return 0.95
            if en_var in norm2 and jp_norm in norm1:
                return 0.95
    
    # Check for partial matches with key wine terms
    wine_terms_jp = ['ピノ', 'シャルドネ', 'カベルネ', 'メルロー', 'シラー', 'リースリング', 'ソーヴィニヨン']
    wine_terms_en = ['pinot', 'chardonnay', 'cabernet', 'merlot', 'syrah', 'shiraz', 'riesling', 'sauvignon']
    
    for jp_term, en_term in zip(wine_terms_jp, wine_terms_en):
        if jp_term in name1 and en_term in norm2:
            return 0.8
        if jp_term in name2 and en_term in norm1:
            return 0.8
    
    # Check for phonetic similarities in romanized text
    if contains_japanese(name1) != contains_japanese(name2):
        # One is Japanese, one is not - check for romanization patterns
        romanized_similarity = check_romanization_similarity(name1, name2)
        if romanized_similarity > 0.7:
            return romanized_similarity
    
    return 0.0

def check_substring_similarity(name1: str, name2: str) -> float:
    """Check if one wine name is contained within another (handles producer+wine vs wine-only)."""
    if not name1 or not name2:
        return 0.0
    
    # Normalize both names
    norm1 = normalize_wine_name(name1)
    norm2 = normalize_wine_name(name2)
    
    # Split into words for more flexible matching
    words1 = set(word for word in norm1.split() if len(word) > 2)
    words2 = set(word for word in norm2.split() if len(word) > 2)
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate overlap ratio
    intersection = words1.intersection(words2)
    smaller_set = min(len(words1), len(words2))
    
    if not intersection:
        return 0.0
    
    overlap_ratio = len(intersection) / smaller_set
    
    # High similarity if significant overlap
    if overlap_ratio >= 0.8:  # 80% of smaller set matches
        return 0.9
    elif overlap_ratio >= 0.6:  # 60% of smaller set matches
        return 0.8
    elif overlap_ratio >= 0.4:  # 40% of smaller set matches
        return 0.7
    
    # Special case: Check if shorter name is completely contained in longer name
    shorter = norm1 if len(norm1) < len(norm2) else norm2
    longer = norm2 if len(norm1) < len(norm2) else norm1
    
    # Remove common words that don't help identification
    common_words = {'wine', 'vin', 'vino', 'casa', 'de', 'del', 'della', 'du', 'grand', 'petit', 'reserve', 'reserva'}
    shorter_words = [word for word in shorter.split() if word not in common_words and len(word) > 2]
    
    if shorter_words:
        # Check if all meaningful words from shorter name appear in longer name
        matches = sum(1 for word in shorter_words if word in longer)
        if matches == len(shorter_words) and len(shorter_words) >= 1:
            return 0.85  # Very high similarity for complete containment
    
    return 0.0

def check_romanization_similarity(name1: str, name2: str) -> float:
    """Check similarity based on romanization patterns."""
    # Simple romanization check - look for similar consonant patterns
    jp_name = name1 if contains_japanese(name1) else name2
    en_name = name2 if contains_japanese(name1) else name1
    
    # Extract romanized approximations
    romanization_map = {
        'ボニトゥラ': 'bonitura',
        'ピノ': 'pino',
        'シャルドネ': 'sharudone',
        'カベルネ': 'kaberune',
        'メルロー': 'meruro',
        'リースリング': 'riisuringu',
    }
    
    jp_norm = normalize_wine_name(jp_name)
    en_norm = normalize_wine_name(en_name)
    
    for jp_pattern, en_pattern in romanization_map.items():
        if jp_pattern in jp_norm and en_pattern in en_norm:
            return 0.9
    
    return 0.0

def merge_wine_info(wine1: WineInfo, wine2: WineInfo) -> WineInfo:
    """Merge information from two similar wines with VERY strong Japanese content priority."""
    
    # Calculate Japanese content scores
    jp_score1 = get_japanese_content_score(wine1)
    jp_score2 = get_japanese_content_score(wine2)
    
    # Debug: Store merge info for debugging
    merge_debug = {
        'wine1_name': wine1.name,
        'wine2_name': wine2.name,
        'wine1_jp_score': jp_score1,
        'wine2_jp_score': jp_score2,
        'wine1_has_jp_name': contains_japanese(wine1.name),
        'wine2_has_jp_name': contains_japanese(wine2.name)
    }
    
    # Helper function to count non-empty fields
    def count_fields(wine):
        return sum(1 for field in [wine.producer, wine.country, wine.region, wine.grape_variety, 
                                 wine.vintage, wine.price, wine.alcohol_content, wine.description] 
                  if field)
    
    # STRONGLY prioritize Japanese content - even a small amount beats non-Japanese
    # Only use completeness if Japanese scores are exactly equal (both 0 or both same positive value)
    if jp_score1 > 0 and jp_score2 == 0:
        # wine1 has Japanese, wine2 doesn't - always choose wine1
        primary, secondary = wine1, wine2
    elif jp_score2 > 0 and jp_score1 == 0:
        # wine2 has Japanese, wine1 doesn't - always choose wine2
        primary, secondary = wine2, wine1
    elif jp_score1 != jp_score2:
        # Both have Japanese but different amounts - choose higher score
        primary, secondary = (wine1, wine2) if jp_score1 > jp_score2 else (wine2, wine1)
    else:
        # Japanese content is exactly equal (both 0 or same score) - use completeness
        if count_fields(wine2) > count_fields(wine1):
            primary, secondary = wine2, wine1
        else:
            primary, secondary = wine1, wine2
    
    # Start with the more complete wine
    merged = WineInfo(
        name=primary.name,
        producer=primary.producer,
        country=primary.country,
        region=primary.region,
        grape_variety=primary.grape_variety,
        vintage=primary.vintage,
        price=primary.price,
        alcohol_content=primary.alcohol_content,
        description=primary.description,
        source_file=primary.source_file
    )
    
    # Fill in missing information from secondary wine, with VERY strong Japanese preference
    def prefer_japanese_or_fill(primary_val, secondary_val):
        """Choose between two values with ABSOLUTE preference for Japanese text."""
        if not primary_val and secondary_val:
            # Primary is empty - use secondary
            return secondary_val
        elif not secondary_val and primary_val:
            # Secondary is empty - use primary
            return primary_val
        elif primary_val and secondary_val:
            # Both exist - ALWAYS prefer Japanese text, no matter what
            primary_has_jp = contains_japanese(primary_val)
            secondary_has_jp = contains_japanese(secondary_val)
            
            if secondary_has_jp and not primary_has_jp:
                # Secondary has Japanese, primary doesn't - always use secondary
                return secondary_val
            elif primary_has_jp and not secondary_has_jp:
                # Primary has Japanese, secondary doesn't - always use primary
                return primary_val
            elif secondary_has_jp and primary_has_jp:
                # Both have Japanese - prefer the longer/more detailed one
                return secondary_val if len(secondary_val) > len(primary_val) else primary_val
            else:
                # Neither has Japanese - keep primary
                return primary_val
        return primary_val
    
    merged.producer = prefer_japanese_or_fill(merged.producer, secondary.producer)
    merged.country = prefer_japanese_or_fill(merged.country, secondary.country)
    merged.region = prefer_japanese_or_fill(merged.region, secondary.region)
    merged.grape_variety = prefer_japanese_or_fill(merged.grape_variety, secondary.grape_variety)
    
    # For these fields, just fill if missing (no Japanese preference needed)
    if not merged.vintage and secondary.vintage:
        merged.vintage = secondary.vintage
    if not merged.price and secondary.price:
        merged.price = secondary.price
    if not merged.alcohol_content and secondary.alcohol_content:
        merged.alcohol_content = secondary.alcohol_content
    
    # Merge descriptions
    descriptions = []
    if primary.description and primary.description.strip():
        descriptions.append(primary.description.strip())
    if secondary.description and secondary.description.strip() and secondary.description.strip() not in descriptions:
        descriptions.append(secondary.description.strip())
    merged.description = " | ".join(descriptions) if descriptions else None
    
    # Combine source files
    sources = []
    if wine1.source_file:
        sources.append(wine1.source_file)
    if wine2.source_file and wine2.source_file not in sources:
        sources.append(wine2.source_file)
    merged.source_file = ", ".join(sources)
    
    # Store debug info
    merge_debug['primary_chosen'] = 'wine1' if primary == wine1 else 'wine2'
    merge_debug['final_name'] = merged.name
    
    # Store debug info for access
    if not hasattr(merge_wine_info, '_debug_merges'):
        merge_wine_info._debug_merges = []
    merge_wine_info._debug_merges.append(merge_debug)
    
    # Choose the better name with EXTREMELY strong Japanese preference
    wine1_has_japanese = contains_japanese(wine1.name)
    wine2_has_japanese = contains_japanese(wine2.name)
    
    # ABSOLUTE Priority 1: Japanese text always wins - no exceptions!
    if wine1_has_japanese and not wine2_has_japanese:
        merged.name = wine1.name
    elif wine2_has_japanese and not wine1_has_japanese:
        merged.name = wine2.name
    elif wine1_has_japanese and wine2_has_japanese:
        # Both have Japanese - prefer the longer/more detailed Japanese name
        if len(wine1.name) > len(wine2.name):
            merged.name = wine1.name
        elif len(wine2.name) > len(wine1.name):
            merged.name = wine2.name
        else:
            # Same length - keep primary wine's name
            merged.name = primary.name
    else:
        # Neither has Japanese - use other factors
        # Prefer name with more information
        if len(wine2.name) > len(wine1.name) * 1.2:
            merged.name = wine2.name
        elif len(wine1.name) > len(wine2.name) * 1.2:
            merged.name = wine1.name
        else:
            # Similar lengths - prefer the one with more wine-specific terms
            wine_terms = ['cremant', 'brut', 'zero', 'blanc', 'rouge', 'reserve']
            wine1_terms = sum(1 for term in wine_terms if term in wine1.name.lower())
            wine2_terms = sum(1 for term in wine_terms if term in wine2.name.lower())
            
            if wine2_terms > wine1_terms:
                merged.name = wine2.name
            else:
                merged.name = wine1.name
    
    return merged

def deduplicate_wines(wines: List[WineInfo], similarity_threshold: float = 0.5, debug: bool = False) -> List[WineInfo]:
    """Remove duplicate wines and merge similar ones."""
    
    if not wines:
        return wines
    
    # Clear previous debug info
    if hasattr(merge_wine_info, '_debug_merges'):
        merge_wine_info._debug_merges = []
    
    deduplicated = []
    processed_indices = set()
    merge_info = []
    
    for i, wine1 in enumerate(wines):
        if i in processed_indices:
            continue
            
        # Find similar wines
        similar_wines = [wine1]
        similar_indices = {i}
        similarities_found = []
        
        for j, wine2 in enumerate(wines[i+1:], i+1):
            if j in processed_indices:
                continue
                
            similarity = calculate_wine_similarity(wine1, wine2)
            
            if debug and similarity > 0.3:  # Show potential matches for debugging
                similarities_found.append({
                    'wine1': wine1.name,
                    'wine2': wine2.name,
                    'similarity': similarity,
                    'merged': similarity >= similarity_threshold
                })
            
            if similarity >= similarity_threshold:
                similar_wines.append(wine2)
                similar_indices.add(j)
        
        # Merge all similar wines
        merged_wine = similar_wines[0]
        for similar_wine in similar_wines[1:]:
            merged_wine = merge_wine_info(merged_wine, similar_wine)
        
        if len(similar_wines) > 1:
            merge_info.append({
                'final_name': merged_wine.name,
                'merged_count': len(similar_wines),
                'original_names': [w.name for w in similar_wines]
            })
        
        deduplicated.append(merged_wine)
        processed_indices.update(similar_indices)
    
    # Store debug info as function attribute for access
    deduplicate_wines._debug_info = {
        'similarities': similarities_found,
        'merges': merge_info
    }
    
    return deduplicated

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