import streamlit as st
from openai import OpenAI
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_processor import extract_text_from_pdf, parse_wine_info_with_ai, deduplicate_wines

# Initialize OpenAI Client
client = OpenAI()

# Streamlit App
st.write("### PDF Wine List Import 📄")
st.write("")

st.write("#### Upload and Import Wine Lists from PDF")
st.write("Upload one or more PDF files containing wine list information. The system will automatically extract wine names and details.")

# Add threshold adjustment
threshold = st.slider(
    "Similarity threshold for merging duplicates", 
    min_value=0.1, 
    max_value=0.8, 
    value=0.2, 
    step=0.05,
    help="Lower values = more aggressive merging. Higher values = stricter matching. Try 0.2 for very loose matching."
)


# File uploader - now accepts multiple files
uploaded_files = st.file_uploader(
    "Choose PDF files", 
    type="pdf",
    accept_multiple_files=True,
    help="Upload one or more PDF files containing wine list information"
)


# Check if we have previously processed wines in session state
if 'processed_wines' in st.session_state and st.session_state['processed_wines']:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.info("📚 Using previously processed wines from this session")
    with col2:
        if st.button("🗑️ Clear", help="Clear processed wines and start over"):
            # Clear all session data
            for key in ['processed_wines', 'extracted_texts', 'deduplicated_wines', 'deduplication_complete', 'wine_library', 'imported_wines']:
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
        
        if all_wines:
            # Show deduplication options before processing
            original_count = len(all_wines)
            st.write(f"**Found {original_count} total wines from {len(uploaded_files)} PDF file(s)**")
            
            st.write("#### Deduplication Settings")
            
            # Debug option
            show_debug = st.checkbox("Show similarity debugging info", value=False)
            
            # Add buttons for deduplication control
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("🔄 Run Deduplication", type="primary"):
                    with st.spinner("Removing duplicates and merging similar wines..."):
                        deduplicated_wines = deduplicate_wines(all_wines.copy(), similarity_threshold=threshold, debug=show_debug)
                        
                    # Store deduplicated wines in session state
                    st.session_state['deduplicated_wines'] = deduplicated_wines
                    st.session_state['deduplication_complete'] = True
                    st.rerun()
            with col2:
                if st.session_state.get('deduplication_complete', False):
                    if st.button("🔄 Reset", help="Reset to run deduplication again with different settings"):
                        st.session_state['deduplication_complete'] = False
                        if 'deduplicated_wines' in st.session_state:
                            del st.session_state['deduplicated_wines']
                        st.rerun()
            
            # Use deduplicated wines if available
            if st.session_state.get('deduplication_complete', False) and 'deduplicated_wines' in st.session_state:
                all_wines = st.session_state['deduplicated_wines']
                
            # Show deduplication results and debug info only after processing
            if st.session_state.get('deduplication_complete', False):
                deduplicated_count = len(all_wines)
                duplicates_removed = original_count - deduplicated_count
                
                if duplicates_removed > 0:
                    st.success(f"✅ Removed {duplicates_removed} duplicate(s)! Now showing {deduplicated_count} unique wines.")
                else:
                    st.info(f"ℹ️ No duplicates found. Showing all {deduplicated_count} wines.")
                
                # Show debug information if requested
                if show_debug:
                    if hasattr(deduplicate_wines, '_debug_info'):
                        debug_info = deduplicate_wines._debug_info
                        if debug_info.get('similarities'):
                            with st.expander("🔍 Similarity Analysis (Debug)"):
                                for sim in debug_info['similarities']:
                                    st.write("**Comparing:**")
                                    st.write(f"- Wine 1: {sim['wine1']}")
                                    st.write(f"- Wine 2: {sim['wine2']}")
                                    st.write(f"- Similarity: {sim['similarity']:.3f}")
                                    st.write(f"- Merged: {'✅ Yes' if sim['merged'] else '❌ No'}")
                                    st.write("---")
                    
                    # Show merge debug information
                    from pdf_processor import merge_wine_info
                    if hasattr(merge_wine_info, '_debug_merges') and merge_wine_info._debug_merges:
                        with st.expander("🇯🇵 Japanese Priority Debug"):
                            for merge in merge_wine_info._debug_merges:
                                st.write("**Merging Process:**")
                                st.write(f"- Wine 1: {merge['wine1_name']}")
                                st.write(f"  - Japanese Score: {merge['wine1_jp_score']}")
                                st.write(f"  - Has Japanese Name: {'✅' if merge['wine1_has_jp_name'] else '❌'}")
                                st.write(f"- Wine 2: {merge['wine2_name']}")
                                st.write(f"  - Japanese Score: {merge['wine2_jp_score']}")
                                st.write(f"  - Has Japanese Name: {'✅' if merge['wine2_has_jp_name'] else '❌'}")
                                st.write(f"- **Primary Chosen:** {merge['primary_chosen']}")
                                st.write(f"- **Final Name:** {merge['final_name']}")
                                st.write("---")
                    
                    # Test Japanese detection
                    with st.expander("🧪 Test Japanese Detection"):
                        test_names = [
                            "Crémant de Loire Brut Zero NV",
                            "クレマン・ド・ロワール ブリュット・ゼロ NV",
                            "シャブリ",
                            "Chablis",
                            "ドメーヌ・ラロッシュ"
                        ]
                        
                        from pdf_processor import contains_japanese
                        for name in test_names:
                            has_jp = contains_japanese(name)
                            st.write(f"- '{name}': {'🇯🇵 Japanese' if has_jp else '🇫🇷 Non-Japanese'}")
            else:
                st.info("⚙️ Adjust the similarity threshold above and click 'Run Deduplication' to remove duplicates.")
        
        if all_wines:
            st.write(f"#### Total Extracted Wine Information ({len(all_wines)} wines)")
            
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
                    if ',' in source:
                        st.info(f"🔗 **Merged from:** {source}")
                    else:
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
            
            # Export options - always visible
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
                selected_wine_ids = []
                
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
        else:
            st.error("❌ No wines could be extracted from any of the uploaded files.")
    
    except Exception as e:
        st.error(f"❌ Error processing PDFs: {str(e)}")

else:
    # No files uploaded and no session data
    st.info("📤 Upload PDF files above to start importing wines")

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