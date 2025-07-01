from openai import OpenAI
import streamlit as st
import sys
import os

# Import authentication
from auth import auth

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.models_config import get_model_options, get_model_id, DEFAULT_MODEL, is_reasoning_model
    from src.wine_merger import merge_wines, format_wine_preview, get_wine_summary
except ImportError:
    # Fallback import
    sys.path.append('./src')
    from models_config import get_model_options, get_model_id, DEFAULT_MODEL, is_reasoning_model
    from wine_merger import merge_wines, format_wine_preview, get_wine_summary


# Require authentication before accessing the app
auth.require_auth()

# Add logout button to sidebar
auth.add_logout_button()

# Initialize OpenAI Client
client = OpenAI()

## * Settings
# File Path
past_email_contents_path = "./src/backstreet-mail-contents_2024-07-01.csv"

## OpenAI
# Model and temperature will be set via UI controls

## * Streamlit App
# Tool Title
st.write("### Email Generator: Wine Selection 🍷")
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

# Wine Selection Section
st.write("#### Wine Selection")

# Check for available wine sources
wine_library_available = 'wine_library' in st.session_state and st.session_state['wine_library']
selected_wine_available = 'selected_wine_for_email' in st.session_state
imported_wines_available = 'imported_wines' in st.session_state and st.session_state['imported_wines']['full_info']

# Initialize
current_selected_wine = None
selected_wines = []
all_wines = []

# Collect all available wines
if wine_library_available:
    for wine_id, wine in st.session_state['wine_library'].items():
        all_wines.append(wine)

if imported_wines_available and 'wine_library' not in st.session_state:
    for wine in st.session_state['imported_wines']['full_info']:
        all_wines.append(wine)

# Wine selection mode
if selected_wine_available:
    # Pre-selected wine from PDF import
    current_selected_wine = st.session_state['selected_wine_for_email']
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"🍷 **{current_selected_wine.name}** ({current_selected_wine.producer or 'Unknown'})")
    with col2:
        if st.button("Clear", type="secondary"):
            del st.session_state['selected_wine_for_email']
            st.rerun()
elif all_wines:
    # Selection mode toggle
    use_library = st.radio(
        "Wine source:", 
        ["From Wine Library", "Manual Input"], 
        horizontal=True,
        key="wine_source_mode"
    )
    
    if use_library == "From Wine Library":
        # Wine selection mode
        selection_mode = st.radio(
            "Number of wines:",
            ["Single Wine", "Two Wines"],
            index=1,  # Default to "Two Wines"
            horizontal=True,
            key="wine_count_mode"
        )
        
        # Add option numbers to wine labels
        numbered_wine_options = [f"{i+1}. {wine.name} ({wine.producer or 'Unknown'})" for i, wine in enumerate(all_wines)]
        
        if selection_mode == "Single Wine":
            # Single wine selection
            selected_idx = st.selectbox(
                "🍷 Select wine:", 
                range(len(all_wines)), 
                format_func=lambda x: numbered_wine_options[x],
                key="wine_dropdown_single"
            )
            selected_wines = [all_wines[selected_idx]]
        else:
            # Two wine selection - single column, two rows
            first_idx = st.selectbox(
                "1️⃣ First wine:", 
                range(len(all_wines)), 
                format_func=lambda x: numbered_wine_options[x],
                key="wine_dropdown_first"
            )
            
            # Filter out the first selected wine from second dropdown
            available_second = [i for i in range(len(all_wines)) if i != first_idx]
            if available_second:
                second_idx_pos = st.selectbox(
                    "2️⃣ Second wine:", 
                    range(len(available_second)), 
                    format_func=lambda x: numbered_wine_options[available_second[x]],
                    key="wine_dropdown_second"
                )
                second_idx = available_second[second_idx_pos]
                selected_wines = [all_wines[first_idx], all_wines[second_idx]]
            else:
                st.warning("Need at least 2 wines in library for two-wine selection")
                selected_wines = [all_wines[first_idx]]
        
        # Merge wine information
        if selected_wines:
            merged_wine = merge_wines(selected_wines)
            current_selected_wine = selected_wines[0]  # For backward compatibility
            
            # Display wine summary
            st.success(get_wine_summary(merged_wine))
            st.caption(f"📍 {format_wine_preview(merged_wine)}")
else:
    st.info("💡 No wines in library. Enter wine information manually below.")

# Input Form
st.write("#### Email Generation")
with st.form(key='ask_input_form'):
    # Key Comments and Date
    key_comments = st.text_area("Key Comments from Tasting Party")
    distribute_date = st.date_input("Email Distribution Date")
    
    st.divider()
    
    # Wine Information Section
    st.write("##### Wine Information")
    

    
    # Determine if we should use manual input or wine library
    manual_input = False
    if all_wines and 'wine_source_mode' in st.session_state:
        manual_input = st.session_state['wine_source_mode'] == "Manual Input"
    elif not current_selected_wine:
        manual_input = True
    
    if manual_input:
        # Manual wine input
        wine_name = st.text_input("Wine Name")
        producer = st.text_input("Producer")
        wine_country = st.text_input("Wine Country", placeholder="e.g., France, Italy, Spain")
        wine_cepage = st.text_input("Wine Cépage")
        product_comments = st.text_area("Product Comments", placeholder="Tasting notes, wine characteristics, vintage details, etc.", height=250)
    else:
        # Use merged wine information
        if selected_wines:
            merged_wine = merge_wines(selected_wines)
            wine_name = st.text_input("Wine Name(s)", value=merged_wine.names)
            producer = st.text_input("Producer(s)", value=merged_wine.producers)
            
            # For countries, directly use the merged country information
            merged_countries = merged_wine.countries
            wine_country = st.text_input("Wine Country", value=merged_countries or "", 
                                       help="Automatically populated from selected wines")
            
            wine_cepage = st.text_input("Wine Cépage", value=merged_wine.grape_varieties)
            product_comments = st.text_area("Product Comments", value=merged_wine.descriptions or "", 
                                           help="Automatically populated from wine library", height=250)
        elif current_selected_wine:
            # Fallback for backward compatibility
            wine_name = st.text_input("Wine Name", value=current_selected_wine.name or "")
            producer = st.text_input("Producer", value=current_selected_wine.producer or "")
            wine_country = st.text_input("Wine Country", value=current_selected_wine.country or "")
            wine_cepage = st.text_input("Wine Cépage", value=current_selected_wine.grape_variety or "")
            product_comments = st.text_area("Product Comments", value=current_selected_wine.description or "", 
                                           help="Automatically populated from wine library", height=250)
        else:
            # Fallback to manual input if no wine selected
            wine_name = st.text_input("Wine Name")
            producer = st.text_input("Producer")
            wine_country = st.text_input("Wine Country", placeholder="e.g., France, Italy, Spain")
            wine_cepage = st.text_input("Wine Cépage")
            product_comments = st.text_area("Product Comments", placeholder="Tasting notes, wine characteristics, vintage details, etc.", height=250)
    
    submit = st.form_submit_button("🚀 Generate Email", type="primary")


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

    # Determine wine count for prompt
    wine_count_text = "single wine" if not selected_wines or len(selected_wines) == 1 else "two wines"
    
    # * User Prompt recommending for wine(s)
    user_prompt = f"""
    ## Past Email Contents
    When writing, You can refer to the past email contents as below:
    {previous_email_contents}
    ------

    ## Wine Information in this time
    This email will be distributed at {distribute_date}.
    The wine information that you will recommend in this email is for {wine_count_text}. Especially, the key comments by our sommelier are important because these comments come from our sommelier in tasting party.
    ======
    ### Key Comments By Our Sommelier
    Key Comments By Our Sommelier: {key_comments}

    ### Wine Information
    Wine Name(s): {wine_name},
    Producer(s): {producer},
    Wine Country: {wine_country},
    Wine Cépage: {wine_cepage},
    Product Comments: {product_comments},
    ======

    ## Output Language: Japanese
    Now, Write the email contents in Japanese. Use emoji following the previous reference.
    {"If recommending two wines, please structure the content to highlight both wines appropriately." if wine_count_text == "two wines" else ""}
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