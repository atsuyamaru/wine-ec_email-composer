from openai import OpenAI
import streamlit as st
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.models_config import get_model_options, get_model_id, DEFAULT_MODEL, is_reasoning_model
except ImportError:
    # Fallback import
    sys.path.append('./src')
    from models_config import get_model_options, get_model_id, DEFAULT_MODEL, is_reasoning_model


# Initialize OpenAI Client
client = OpenAI()

## * Settings
# File Path
past_email_contents_path = "./src/backstreet-mail-contents_2024-07-01.csv"

## OpenAI
# Model and temperature will be set via UI controls

## * Streamlit App
# Tool Title
st.write("### Email Generator: Single Wine 🍷")
st.write("")

# Model Selection
st.write("#### Settings")
selected_model_display = st.selectbox(
    "Select LLM Model:",
    options=get_model_options(),
    index=get_model_options().index(DEFAULT_MODEL),
    help="Choose the language model for generating email content"
)
selected_model = get_model_id(selected_model_display)

# Temperature slider
# Check if selected model is a reasoning model
if is_reasoning_model(selected_model):
    st.info("⚠️ Reasoning models (O3, O3-mini, O4-mini-deep-research) only support temperature=1.0")
    temperature = 1.0
    st.text("Temperature: 1.0 (fixed for reasoning models)")
else:
    temperature = st.slider(
        "Temperature:",
        min_value=0.0,
        max_value=2.0,
        value=0.4,
        step=0.1,
        help="Controls randomness: 0 = focused and deterministic, 2 = very creative and random"
    )
st.write("")

# Check for wine library and selected wine
wine_library_available = 'wine_library' in st.session_state and st.session_state['wine_library']
selected_wine_available = 'selected_wine_for_email' in st.session_state
imported_wines_available = 'imported_wines' in st.session_state and st.session_state['imported_wines']['full_info']

# Wine Selection Section (outside form for immediate updates)
st.write("#### Wine Selection")

# Initialize selected wine
current_selected_wine = None

# Determine which selection method to use
if selected_wine_available:
    # Use pre-selected wine from PDF import page
    current_selected_wine = st.session_state['selected_wine_for_email']
    st.info(f"Using selected wine: **{current_selected_wine.name}**")
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("❌ Clear Selection"):
            del st.session_state['selected_wine_for_email']
            st.rerun()
    
    # Show preview of selected wine
    with st.expander("📝 Selected Wine Preview", expanded=True):
        st.write(f"**Name:** {current_selected_wine.name}")
        if current_selected_wine.producer:
            st.write(f"**Producer:** {current_selected_wine.producer}")
        if current_selected_wine.country:
            st.write(f"**Country:** {current_selected_wine.country}")
        if current_selected_wine.grape_variety:
            st.write(f"**Grape Variety:** {current_selected_wine.grape_variety}")
        if current_selected_wine.description:
            st.write(f"**Description:** {current_selected_wine.description}")
            
elif wine_library_available or imported_wines_available:
    # Show wine selection dropdown
    all_wines = []
    wine_labels = []
    
    # Add wines from wine library
    if wine_library_available:
        for wine_id, wine in st.session_state['wine_library'].items():
            label = f"{wine.name}"
            if wine.producer:
                label += f" ({wine.producer})"
            wine_labels.append(label)
            all_wines.append(wine)
    
    # Add wines from imported_wines (legacy)
    if imported_wines_available and 'wine_library' not in st.session_state:
        for wine in st.session_state['imported_wines']['full_info']:
            label = f"{wine.name} ({wine.producer or 'Unknown producer'})"
            wine_labels.append(label)
            all_wines.append(wine)
    
    if all_wines:
        selected_idx = st.selectbox(
            "Select wine from library:", 
            range(len(all_wines)), 
            format_func=lambda x: wine_labels[x], 
            key="wine_selection"
        )
        current_selected_wine = all_wines[selected_idx]
        
        # Show preview of selected wine
        with st.expander("📝 Selected Wine Preview", expanded=True):
            st.write(f"**Name:** {current_selected_wine.name}")
            if current_selected_wine.producer:
                st.write(f"**Producer:** {current_selected_wine.producer}")
            if current_selected_wine.country:
                st.write(f"**Country:** {current_selected_wine.country}")
            if current_selected_wine.grape_variety:
                st.write(f"**Grape Variety:** {current_selected_wine.grape_variety}")
            if current_selected_wine.description:
                st.write(f"**Description:** {current_selected_wine.description}")
else:
    st.info("💡 Enter wine information manually below, or go to PDF Import page to import wines from a PDF.")

# Input Form
st.write("#### Input Form to Generate Email Contents")
with st.form(key='ask_input_form'):
    st.write("##### Key Comments and Distribute Date")
    key_comments = st.text_area(label="Key Comments in the tasting party")
    distribute_date = st.date_input(label="Email Distribute Date")
    st.divider()
    
    # Wine Information
    st.write("##### Wine Information")
    
    # Helper function to map country
    def get_country_index(country_name, countries):
        if not country_name:
            return 0
        for i, country in enumerate(countries):
            if country_name.lower() in country.lower() or country.lower() in country_name.lower():
                return i
        return 0
    
    countries = ["France", "Italy", "Spain", "Germany", "Portugal", "America", "South Africa"]
    
    if current_selected_wine:
        # Pre-fill with selected wine data
        wine_name = st.text_input(label="Wine Name", value=current_selected_wine.name or "")
        producer = st.text_input(label="Producer", value=current_selected_wine.producer or "")
        default_country_idx = get_country_index(current_selected_wine.country, countries)
        wine_country = st.selectbox(label="Wine Country", options=countries, index=default_country_idx)
        wine_cepage = st.text_input(label="Wine Cépage", value=current_selected_wine.grape_variety or "")
        
        # Show additional imported info
        if current_selected_wine.description:
            st.text_area("Additional Wine Information (from Wine Library)", value=current_selected_wine.description, disabled=True)
    else:
        # Manual input
        wine_name = st.text_input(label="Wine Name")
        producer = st.text_input(label="Producer")
        wine_country = st.selectbox(label="Wine Country", options=countries)
        wine_cepage = st.text_input(label="Wine Cépage")
    
    submit = st.form_submit_button(label='Generate')


if submit:
    # Read the past email contents from CSV file
    with open(past_email_contents_path, "r") as f:
        # Skip the header, which is written in Japanese on the first line
        next(f)
        previous_email_contents = f.read()

    
    # Define the Prompt
    system_prompt = """
    ## System Prompt
    You are a wine sommelier. Write the following four email contents in Japanese as a email marketing for wine EC: email-title, preview-text, introduction-latter-part, editor's-note.
    """

    # * User Prompt reommending for a single wine
    user_prompt = f"""
    ## Past Email Contents
    When writing, You can refer to the past email contents as below:
    {previous_email_contents}
    ------

    ## Wine Information in this time
    This email will be distributed at {distribute_date}.
    The wine information that you will recommend in this email is below. Especially, the key comments by our sommelier are important because these comments come from our sommelier in tasting party.
    ======
    ### Key Comments By Our Sommelier
    Key Comments By Our Sommelier: {key_comments}

    ### Wine Information
    Wine Name: {wine_name},
    Producer: {producer},
    Wine Country: {wine_country},
    Wine Cépage: {wine_cepage},
    ======

    ## Output Language: Japanese
    Now, Write the email contents in Japanese. Use emoji following the previous reference.
    """

    # Execute the prompt
    response = client.responses.create(  # type: ignore[attr-defined]
        model=selected_model,
        instructions=system_prompt,
        input=user_prompt,
        temperature=temperature,
    )

    # Display the generated email content
    st.write(response.output_text)