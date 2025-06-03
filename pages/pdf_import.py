import streamlit as st
import fitz  # PyMuPDF
import re
from typing import List, Dict, Tuple
from src.type_schema import WineInfo, ParsedWines

st.write("### PDF Wine List Import 📄")
st.write("Import wine information from Japanese wine list PDFs")

class PDFWineParser:
    def __init__(self):
        self.wine_patterns = {
            # Common patterns for Japanese wine lists
            'wine_name': r'([ア-ヴー]+\s*[・\s]*[ア-ヴー]*|[A-Za-zÀ-ÿ\s\-\.\']+)',
            'price': r'¥?(\d{1,3}(?:,\d{3})*)',
            'vintage': r'(19|20)\d{2}',
            'producer': r'([A-Za-zÀ-ÿ\s\-\.\']+)',
        }
    
    def extract_text_from_pdf(self, pdf_bytes: bytes, source: str) -> List[WineInfo]:
        """Extract text from PDF and parse wine information"""
        wines = []
        
        try:
            # Open PDF from bytes
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text = page.get_text()
                
                # Parse wines from this page
                page_wines = self._parse_wines_from_text(text, source, page_num + 1)
                wines.extend(page_wines)
            
            pdf_document.close()
            
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            
        return wines
    
    def _parse_wines_from_text(self, text: str, source: str, page_number: int) -> List[WineInfo]:
        """Parse wine information from extracted text"""
        wines = []
        
        # Split text into lines and process
        lines = text.split('\n')
        current_wine = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to identify wine name (usually longer text with wine characteristics)
            if self._looks_like_wine_name(line):
                # Save previous wine if exists
                if current_wine:
                    wines.append(current_wine)
                
                # Start new wine
                current_wine = WineInfo(
                    name=line,
                    source=source,
                    page_number=page_number
                )
            
            elif current_wine:
                # Try to extract other information
                self._extract_wine_details(line, current_wine)
        
        # Don't forget the last wine
        if current_wine:
            wines.append(current_wine)
            
        return wines
    
    def _looks_like_wine_name(self, text: str) -> bool:
        """Heuristic to identify if text looks like a wine name"""
        # Skip if it's just a price or year
        if re.match(r'^¥?\d+', text) or re.match(r'^(19|20)\d{2}$', text):
            return False
            
        # Check if it contains wine-like characteristics
        wine_indicators = [
            r'[A-Za-zÀ-ÿ]{3,}',  # Latin characters (French, Italian names)
            r'[ア-ヴー]{2,}',      # Katakana (Japanese wine names)
            r'シャトー|ドメーヌ|ワイナリー',  # Wine-related Japanese terms
            r'赤|白|ロゼ|スパークリング',      # Color/type terms
        ]
        
        for pattern in wine_indicators:
            if re.search(pattern, text):
                return True
                
        return False
    
    def _extract_wine_details(self, text: str, wine: WineInfo):
        """Extract details like price, vintage, etc. from text"""
        # Extract price
        price_match = re.search(self.wine_patterns['price'], text)
        if price_match and not wine.price:
            wine.price = f"¥{price_match.group(1)}"
        
        # Extract vintage
        vintage_match = re.search(self.wine_patterns['vintage'], text)
        if vintage_match and not wine.vintage:
            wine.vintage = vintage_match.group(0)
        
        # Add to description if it's additional info
        if not re.match(r'^¥?\d+', text) and len(text) > 3:
            if wine.description:
                wine.description += f" | {text}"
            else:
                wine.description = text

def find_duplicate_wines(wines: List[WineInfo]) -> Tuple[List[WineInfo], List[str]]:
    """Find wines that appear in both PDFs"""
    wine_names = {}
    duplicates = []
    
    for wine in wines:
        name_key = wine.name.lower().strip()
        if name_key in wine_names:
            if wine_names[name_key].source != wine.source:
                duplicates.append(wine.name)
        else:
            wine_names[name_key] = wine
    
    return wines, list(set(duplicates))

# Main UI
st.write("#### Upload Wine List PDFs")
st.write("Upload both the wine list and wine menu PDFs to extract wine information.")

col1, col2 = st.columns(2)

with col1:
    st.write("**Wine List PDF (路地裏ワインリスト)**")
    wine_list_file = st.file_uploader(
        "Choose wine list PDF",
        type="pdf",
        key="wine_list"
    )

with col2:
    st.write("**Wine Menu PDF (路地裏ワインメニュー)**")
    wine_menu_file = st.file_uploader(
        "Choose wine menu PDF", 
        type="pdf",
        key="wine_menu"
    )

if st.button("Extract Wine Information", type="primary"):
    if not wine_list_file and not wine_menu_file:
        st.error("Please upload at least one PDF file.")
    else:
        parser = PDFWineParser()
        all_wines = []
        
        with st.spinner("Processing PDFs..."):
            # Process wine list PDF
            if wine_list_file:
                st.info("Processing wine list PDF...")
                wine_list_bytes = wine_list_file.read()
                wines_from_list = parser.extract_text_from_pdf(wine_list_bytes, "wine_list")
                all_wines.extend(wines_from_list)
                st.success(f"Extracted {len(wines_from_list)} wines from wine list")
            
            # Process wine menu PDF
            if wine_menu_file:
                st.info("Processing wine menu PDF...")
                wine_menu_bytes = wine_menu_file.read()
                wines_from_menu = parser.extract_text_from_pdf(wine_menu_bytes, "wine_menu")
                all_wines.extend(wines_from_menu)
                st.success(f"Extracted {len(wines_from_menu)} wines from wine menu")
        
        # Find duplicates
        processed_wines, duplicates = find_duplicate_wines(all_wines)
        
        # Store in session state
        st.session_state.parsed_wines = ParsedWines(
            wines=processed_wines,
            duplicates=duplicates
        )
        
        st.success(f"Successfully processed {len(processed_wines)} wines total!")
        
        if duplicates:
            st.warning(f"Found {len(duplicates)} wines that appear in both PDFs:")
            for dup in duplicates:
                st.write(f"- {dup}")

# Display results
if hasattr(st.session_state, 'parsed_wines'):
    st.write("#### Extracted Wine Information")
    
    parsed_wines = st.session_state.parsed_wines
    
    # Filter options
    source_filter = st.selectbox(
        "Filter by source:",
        ["All", "Wine List Only", "Wine Menu Only", "Duplicates Only"]
    )
    
    # Filter wines based on selection
    filtered_wines = parsed_wines.wines
    
    if source_filter == "Wine List Only":
        filtered_wines = [w for w in parsed_wines.wines if w.source == "wine_list"]
    elif source_filter == "Wine Menu Only":
        filtered_wines = [w for w in parsed_wines.wines if w.source == "wine_menu"]
    elif source_filter == "Duplicates Only":
        filtered_wines = [w for w in parsed_wines.wines if w.name in parsed_wines.duplicates]
    
    # Display wines in a table
    if filtered_wines:
        for i, wine in enumerate(filtered_wines):
            with st.expander(f"{wine.name} ({wine.source})", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Source:** {wine.source}")
                    st.write(f"**Page:** {wine.page_number}")
                    if wine.price:
                        st.write(f"**Price:** {wine.price}")
                    if wine.vintage:
                        st.write(f"**Vintage:** {wine.vintage}")
                
                with col2:
                    if wine.producer:
                        st.write(f"**Producer:** {wine.producer}")
                    if wine.country:
                        st.write(f"**Country:** {wine.country}")
                    if wine.cepage:
                        st.write(f"**Cepage:** {wine.cepage}")
                
                if wine.description:
                    st.write(f"**Description:** {wine.description}")
                
                # For duplicates, show option to use this version
                if wine.name in parsed_wines.duplicates:
                    if st.button(f"Use this version for {wine.name}", key=f"use_{i}"):
                        st.success(f"Selected version from {wine.source}")
    
    # Export options
    st.write("#### Export Options")
    
    if st.button("Generate Email Content"):
        # Create a summary for email generation
        wine_names = [w.name for w in filtered_wines]
        wine_list_text = "\n".join(wine_names)
        
        st.write("**Wine names for email generation:**")
        st.text_area("Copy this list:", wine_list_text, height=200)
        
        # Link to other pages
        st.write("Use this list in:")
        st.write("- [Single Wine Generator](/) for individual wines")
        st.write("- [6 Bottles Package Generator](/packages_6bottles) for package deals")

else:
    st.info("Upload and process PDF files to see extracted wine information.")