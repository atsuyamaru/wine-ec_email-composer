import streamlit as st
from openai import OpenAI
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_processor import extract_text_from_pdf, parse_wine_info_with_ai, format_wines_for_display, deduplicate_wines

# Initialize OpenAI Client
client = OpenAI()

# Streamlit App
st.write("### PDF Wine List Import 📄🍷")
st.write("")

st.write("#### Upload and Import Wine Lists from PDF")
st.write("Upload one or more PDF files containing wine list information. The system will automatically extract wine names and details.")

# File uploader - now accepts multiple files
uploaded_files = st.file_uploader(
    "Choose PDF files", 
    type="pdf",
    accept_multiple_files=True,
    help="Upload one or more PDF files containing wine list information"
)

if uploaded_files:
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
        
        if all_wines:
            # Deduplicate wines before displaying
            original_count = len(all_wines)
            st.write(f"**Deduplicating wines... (Found {original_count} total wines)**")
            
            # Add threshold adjustment
            threshold = st.slider(
                "Similarity threshold for merging duplicates", 
                min_value=0.1, 
                max_value=0.8, 
                value=0.2, 
                step=0.05,
                help="Lower values = more aggressive merging. Higher values = stricter matching. Try 0.2 for very loose matching."
            )
            
            # Debug option
            show_debug = st.checkbox("Show similarity debugging info", value=False)
            
            with st.spinner("Removing duplicates and merging similar wines..."):
                all_wines = deduplicate_wines(all_wines, similarity_threshold=threshold, debug=show_debug)
                
            # Show debug information if requested
            if show_debug:
                if hasattr(deduplicate_wines, '_debug_info'):
                    debug_info = deduplicate_wines._debug_info
                    if debug_info.get('similarities'):
                        with st.expander("🔍 Similarity Analysis (Debug)"):
                            for sim in debug_info['similarities']:
                                st.write(f"**Comparing:**")
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
                            st.write(f"**Merging Process:**")
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
            
            deduplicated_count = len(all_wines)
            duplicates_removed = original_count - deduplicated_count
            
            if duplicates_removed > 0:
                st.success(f"✅ Removed {duplicates_removed} duplicate(s)! Now showing {deduplicated_count} unique wines.")
            else:
                st.info(f"ℹ️ No duplicates found. Showing all {deduplicated_count} wines.")
        
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
            
            # Option to export as CSV
            if st.button("Export All to CSV"):
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
            
            # Option to use wines for email generation
            st.write("#### Use for Email Generation")
            st.write("Select wines to use for generating marketing emails:")
            
            selected_wines = []
            for i, wine in enumerate(all_wines):
                source = getattr(wine, 'source_file', 'Unknown')
                label = f"{wine.name} (from {source})"
                if st.checkbox(f"Use {label}", key=f"wine_{i}"):
                    selected_wines.append(wine)
            
            if selected_wines and st.button("Store Selected Wines for Email Generation"):
                # Create wine names list for email generation
                wine_names = [wine.name for wine in selected_wines]
                wine_details = []
                
                for wine in selected_wines:
                    details = f"Wine: {wine.name}"
                    if wine.producer:
                        details += f", Producer: {wine.producer}"
                    if wine.country:
                        details += f", Country: {wine.country}"
                    if wine.grape_variety:
                        details += f", Grape: {wine.grape_variety}"
                    source = getattr(wine, 'source_file', 'Unknown')
                    details += f" (Source: {source})"
                    wine_details.append(details)
                
                # Store in session state for use in other pages
                st.session_state['imported_wines'] = {
                    'names': wine_names,
                    'details': wine_details,
                    'full_info': selected_wines
                }
                
                st.success(f"✅ {len(selected_wines)} selected wines stored! You can now use them in the email generation pages.")
                st.info("💡 Go to the 'Single Wine' or '6 bottles bundle' pages to generate emails with the imported wine data.")
        else:
            st.error("❌ No wines could be extracted from any of the uploaded files.")
    
    except Exception as e:
        st.error(f"❌ Error processing PDFs: {str(e)}")

# Display stored wines if any
if 'imported_wines' in st.session_state:
    st.write("#### Previously Imported Wines")
    st.write("The following wines are stored and can be used in email generation:")
    for name in st.session_state['imported_wines']['names']:
        st.write(f"- {name}")
    
    if st.button("Clear Stored Wines"):
        del st.session_state['imported_wines']
        st.success("✅ Stored wines cleared!")
        st.rerun()