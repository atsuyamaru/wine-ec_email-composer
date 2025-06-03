import streamlit as st
from openai import OpenAI
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_processor import extract_text_from_pdf, parse_wine_info_with_ai, format_wines_for_display

# Initialize OpenAI Client
client = OpenAI()

# Streamlit App
st.write("### PDF Wine List Import 📄🍷")
st.write("")

st.write("#### Upload and Import Wine Lists from PDF")
st.write("Upload a PDF file containing wine list information. The system will automatically extract wine names and details.")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a PDF file", 
    type="pdf",
    help="Upload a PDF file containing wine list information"
)

if uploaded_file is not None:
    st.write("#### Processing PDF...")
    
    try:
        # Extract text from PDF
        with st.spinner("Extracting text from PDF..."):
            extracted_text = extract_text_from_pdf(uploaded_file)
        
        if extracted_text.strip():
            st.success("✅ Text successfully extracted from PDF!")
            
            # Show extracted text in expandable section
            with st.expander("View Raw Extracted Text"):
                st.text_area("Extracted Text", extracted_text, height=200, disabled=True)
            
            # Parse wine information
            with st.spinner("Parsing wine information with AI..."):
                parsed_wines = parse_wine_info_with_ai(extracted_text, client)
            
            st.success(f"✅ Found {len(parsed_wines.wines)} wine(s) in the PDF!")
            
            # Display parsed wines
            st.write("#### Extracted Wine Information")
            formatted_output = format_wines_for_display(parsed_wines)
            st.markdown(formatted_output)
            
            # Option to export as CSV
            if st.button("Export to CSV"):
                import pandas as pd
                
                # Convert wines to DataFrame
                wines_data = []
                for wine in parsed_wines.wines:
                    wine_dict = wine.model_dump()
                    wines_data.append(wine_dict)
                
                df = pd.DataFrame(wines_data)
                
                # Convert to CSV
                csv = df.to_csv(index=False)
                
                # Download button
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"wine_list_{uploaded_file.name.replace('.pdf', '.csv')}",
                    mime="text/csv"
                )
            
            # Option to use wines for email generation
            st.write("#### Use for Email Generation")
            st.write("Select wines to use for generating marketing emails:")
            
            selected_wines = []
            for i, wine in enumerate(parsed_wines.wines):
                if st.checkbox(f"Use {wine.name}", key=f"wine_{i}"):
                    selected_wines.append(wine)
            
            if selected_wines and st.button("Generate Email Content"):
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
                    wine_details.append(details)
                
                # Store in session state for use in other pages
                st.session_state['imported_wines'] = {
                    'names': wine_names,
                    'details': wine_details,
                    'full_info': selected_wines
                }
                
                st.success("✅ Selected wines stored! You can now use them in the email generation pages.")
                st.info("💡 Go to the 'Single Wine' or '6 bottles bundle' pages to generate emails with the imported wine data.")
        
        else:
            st.error("❌ No text could be extracted from the PDF. Please check if the PDF contains readable text.")
    
    except Exception as e:
        st.error(f"❌ Error processing PDF: {str(e)}")

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