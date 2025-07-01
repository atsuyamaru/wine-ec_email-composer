import streamlit as st
from openai import OpenAI
import sys
import os
from pathlib import Path

# Import authentication
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from auth import auth

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_processor import extract_text_from_pdf, parse_wine_info_with_ai

# Require authentication before accessing the app
auth.require_auth()

# Add logout button to sidebar
auth.add_logout_button()

# Initialize OpenAI Client
client = OpenAI()

# Streamlit App
st.write("### PDF Wine List Import 📄")
st.write("")

st.write("#### Select Pre-uploaded PDFs or Upload Your Own")

# Tab selection for PDF source
tab1, tab2 = st.tabs(["📁 Pre-uploaded PDFs", "📤 Upload Your Own"])

with tab1:
    st.write("Select from the wine list PDFs already in the repository:")
    
    # Get the PDF directory path
    pdf_dir = Path(__file__).parent.parent / "src" / "wine-list-pdf"
    
    # Find all PDF files recursively
    pdf_files = list(pdf_dir.rglob("*.pdf"))
    
    if pdf_files:
        # Group PDFs by directory
        pdf_groups = {}
        for pdf_file in pdf_files:
            # Get relative path from wine-list-pdf directory
            rel_path = pdf_file.relative_to(pdf_dir)
            group = rel_path.parent.name if rel_path.parent.name != "." else "Root"
            
            if group not in pdf_groups:
                pdf_groups[group] = []
            pdf_groups[group].append(pdf_file)
        
        # Sort groups for consistent display
        sorted_groups = sorted(pdf_groups.items(), reverse=True)  # Newest first
        
        # Multi-select for PDFs
        selected_pdfs = []
        for group_name, group_files in sorted_groups:
            st.write(f"**{group_name}:**")
            for pdf_file in sorted(group_files):
                # Create a more user-friendly display name
                display_name = pdf_file.name
                if st.checkbox(display_name, key=f"pdf_{pdf_file}"):
                    selected_pdfs.append(pdf_file)
        
        if selected_pdfs:
            st.write(f"\n**Selected {len(selected_pdfs)} PDF(s) for processing**")
            
            # Process selected PDFs when button is clicked
            if st.button("🔄 Process Selected PDFs", type="primary", key="process_preloaded"):
                # Clear any existing upload data
                uploaded_files = []
                
                # Convert Path objects to file-like objects for processing
                for pdf_path in selected_pdfs:
                    with open(pdf_path, 'rb') as f:
                        # Create a file-like object with name attribute
                        class PDFFile:
                            def __init__(self, content, name):
                                self.content = content
                                self.name = name
                                self.position = 0
                            
                            def read(self, size=-1):
                                if size == -1:
                                    data = self.content[self.position:]
                                    self.position = len(self.content)
                                else:
                                    data = self.content[self.position:self.position + size]
                                    self.position += len(data)
                                return data
                            
                            def seek(self, pos, whence=0):
                                if whence == 0:  # SEEK_SET
                                    self.position = pos
                                elif whence == 1:  # SEEK_CUR
                                    self.position += pos
                                elif whence == 2:  # SEEK_END
                                    self.position = len(self.content) + pos
                                return self.position
                            
                            def tell(self):
                                return self.position
                        
                        pdf_content = f.read()
                        pdf_file = PDFFile(pdf_content, pdf_path.name)
                        uploaded_files.append(pdf_file)
                
                # Store in session state to trigger processing
                st.session_state['pdf_files_to_process'] = uploaded_files
                st.rerun()
    else:
        st.warning("No pre-uploaded PDFs found in the repository.")

with tab2:
    st.write("Upload one or more PDF files containing wine list information. The system will automatically extract wine names and details.")
    
    # File uploader - now accepts multiple files
    uploaded_files = st.file_uploader(
        "Choose PDF files", 
        type="pdf",
        accept_multiple_files=True,
        help="Upload one or more PDF files containing wine list information",
        key="pdf_uploader"
    )

# Check if we have files to process from pre-uploaded selection
if 'pdf_files_to_process' in st.session_state:
    uploaded_files = st.session_state['pdf_files_to_process']
    del st.session_state['pdf_files_to_process']  # Clear after use

# Check if we have previously processed wines in session state
if 'processed_wines' in st.session_state and st.session_state['processed_wines']:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.info("📚 Using previously processed wines from this session")
    with col2:
        if st.button("🗑️ Clear", help="Clear processed wines and start over"):
            # Clear all session data
            for key in ['processed_wines', 'extracted_texts', 'wine_library', 'imported_wines']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    all_wines = st.session_state['processed_wines'].copy()
    all_extracted_texts = st.session_state.get('extracted_texts', {})

elif uploaded_files:
    st.write(f"#### Processing {len(uploaded_files)} PDF file(s)...")
    
    all_wines = []
    all_extracted_texts = {}
    
    try:
        # Process each uploaded file
        for file_idx, uploaded_file in enumerate(uploaded_files):
            st.write(f"**Processing: {uploaded_file.name}**")
            
            # Extract text from PDF
            with st.spinner(f"Extracting text from {uploaded_file.name}..."):
                extracted_text = extract_text_from_pdf(uploaded_file)
            
            if extracted_text.strip():
                st.success(f"✅ Text successfully extracted from {uploaded_file.name}!")
                all_extracted_texts[uploaded_file.name] = extracted_text
                
                # Parse wine information
                with st.spinner(f"Parsing wine information from {uploaded_file.name}..."):
                    parsed_wines = parse_wine_info_with_ai(extracted_text, client)
                
                st.success(f"✅ Found {len(parsed_wines.wines)} wine(s) in {uploaded_file.name}!")
                
                # Add source file to each wine
                for wine in parsed_wines.wines:
                    wine.source_file = uploaded_file.name
                
                all_wines.extend(parsed_wines.wines)
            else:
                st.error(f"❌ No text could be extracted from {uploaded_file.name}")
        
        # Store processed wines and texts in session state for persistence
        if all_wines:
            st.session_state['processed_wines'] = all_wines.copy()
            st.session_state['extracted_texts'] = all_extracted_texts
            st.write(f"**Found {len(all_wines)} total wines from {len(uploaded_files)} PDF file(s)**")

    except Exception as e:
        st.error(f"❌ Error processing PDFs: {str(e)}")

else:
    # No files uploaded and no session data
    st.info("📤 Upload PDF files above to start importing wines")

# WINE DISPLAY AND LIBRARY MANAGEMENT
if 'processed_wines' in st.session_state and st.session_state['processed_wines']:
    all_wines = st.session_state.get('processed_wines', [])
    all_extracted_texts = st.session_state.get('extracted_texts', {})
    
    if all_wines:
        st.write(f"#### Extracted Wine Information ({len(all_wines)} wines)")
        
        # Display all wines with source information
        for i, wine in enumerate(all_wines, 1):
            with st.expander(f"Wine {i}: {wine.name}"):
                if wine.producer:
                    st.write(f"**Producer:** {wine.producer}")
                if wine.country:
                    st.write(f"**Country:** {wine.country}")
                if wine.region:
                    st.write(f"**Region:** {wine.region}")
                if wine.grape_variety:
                    st.write(f"**Grape Variety:** {wine.grape_variety}")
                if wine.vintage:
                    st.write(f"**Vintage:** {wine.vintage}")
                if wine.price:
                    st.write(f"**Price:** {wine.price}")
                if wine.alcohol_content:
                    st.write(f"**Alcohol:** {wine.alcohol_content}")
                if wine.description:
                    st.write(f"**Description:** {wine.description}")
                
                # Show source file(s)
                source = getattr(wine, 'source_file', 'Unknown')
                st.info(f"📄 **Source:** {source}")
        
        # Show raw extracted text for each file
        with st.expander("View Raw Extracted Text from All Files"):
            for file_name, text in all_extracted_texts.items():
                st.write(f"**{file_name}:**")
                st.text_area(f"Text from {file_name}", text, height=150, disabled=True, key=f"text_{file_name}")
        
        # Store wines in session state automatically
        if 'wine_library' not in st.session_state:
            st.session_state['wine_library'] = {}
        
        # Add all wines to the library with unique IDs
        wines_added = 0
        for wine in all_wines:
            # Create unique ID for wine
            wine_id = f"{wine.name}_{getattr(wine, 'source_file', 'unknown')}"
            if wine_id not in st.session_state['wine_library']:
                st.session_state['wine_library'][wine_id] = wine
                wines_added += 1
        
        # Also store in imported_wines format for compatibility with 6bottles page
        st.session_state['imported_wines'] = {
            'names': [wine.name for wine in all_wines],
            'full_info': all_wines
        }
        
        if wines_added > 0:
            st.success(f"✅ Added {wines_added} wines to your wine library!")
        
        # Export options
        st.write("#### Export Options")
        col1, col2 = st.columns(2)
        
        with col1:
            # Export all wines as CSV
            if st.button("📊 Export All as CSV"):
                import pandas as pd
                
                # Convert wines to DataFrame
                wines_data = []
                for wine in all_wines:
                    wine_dict = wine.model_dump()
                    wines_data.append(wine_dict)
                
                df = pd.DataFrame(wines_data)
                
                # Convert to CSV
                csv = df.to_csv(index=False)
                
                # Create filename with timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Download button
                st.download_button(
                    label="Download Combined CSV",
                    data=csv,
                    file_name=f"wine_list_combined_{timestamp}.csv",
                    mime="text/csv"
                )
        
        with col2:
            # Show wine library status
            total_wines_in_library = len(st.session_state.get('wine_library', {}))
            st.info(f"📚 Wine Library: {total_wines_in_library} wines stored")
            
            if st.button("🗑️ Clear Wine Library"):
                st.session_state['wine_library'] = {}
                st.success("Wine library cleared!")
                st.rerun()
        
        # Wine Library Management
        st.write("#### Wine Library")
        
        if st.session_state.get('wine_library'):
            st.write("Select wines to use for email generation:")
            
            # Create columns for better layout
            cols = st.columns(3)
            
            for i, (wine_id, wine) in enumerate(st.session_state['wine_library'].items()):
                col_idx = i % 3
                with cols[col_idx]:
                    source = getattr(wine, 'source_file', 'Unknown')
                    label = f"{wine.name}"
                    if wine.producer:
                        label += f" ({wine.producer})"
                    
                    if st.button(f"🍷 Use: {label}", key=f"use_{wine_id}"):
                        # Store selected wine for single wine page
                        st.session_state['selected_wine_for_email'] = wine
                        st.success(f"✅ Selected: {wine.name}")
                        st.info("💡 Go to the 'Single Wine' page to generate email with this wine.")
            
            st.divider()
            
            # Show current selection
            if 'selected_wine_for_email' in st.session_state:
                selected = st.session_state['selected_wine_for_email']
                st.write("**Currently Selected Wine:**")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"🍷 **{selected.name}**")
                    if selected.producer:
                        st.write(f"Producer: {selected.producer}")
                    if selected.country:
                        st.write(f"Country: {selected.country}")
                with col2:
                    if st.button("❌ Clear Selection"):
                        del st.session_state['selected_wine_for_email']
                        st.rerun()
            
        else:
            st.info("📚 No wines in library yet. Upload PDFs above to add wines.")

# Display stored wines if any (legacy compatibility)
if 'imported_wines' in st.session_state and not st.session_state.get('processed_wines'):
    st.write("#### Previously Imported Wines")
    st.write("The following wines are stored and can be used in email generation:")
    for name in st.session_state['imported_wines']['names']:
        st.write(f"- {name}")
    
    if st.button("Clear Stored Wines"):
        del st.session_state['imported_wines']
        st.success("✅ Stored wines cleared!")
        st.rerun()