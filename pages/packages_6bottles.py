from openai import OpenAI
import streamlit as st
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from src.models_config import get_model_options, get_model_id, DEFAULT_MODEL, is_reasoning_model
except ImportError:
    # Fallback import
    sys.path.append('../src')
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
st.write("### Email Generator: 6 bottles bundle monthly set 📦")
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

# Check for imported wines
imported_wines_available = 'imported_wines' in st.session_state and st.session_state['imported_wines']['full_info']

if imported_wines_available:
    st.info("🍷 You have imported wines available! You can use them below or enter manually.")

# Input Form
st.write("#### Input Form to Generate Email Contents")
with st.form(key='ask_input_form'):
    st.write("##### Key Comments and Distribute Date")
    monthly_concept = st.text_input(label="Monthly Concept")
    key_comments = st.text_area(label="Key Comments in the tasting party")
    distribute_date = st.date_input(label="Email Distribute Date")
    st.divider()
    
    st.write("##### Wine Information")
    
    # Option to use imported wines
    use_imported = False
    if imported_wines_available:
        use_imported = st.checkbox("Use imported wines from PDF")
        if use_imported:
            st.write("Select wines from imported PDF:")
            selected_wines = []
            for i, wine in enumerate(st.session_state['imported_wines']['full_info']):
                if st.checkbox(f"{wine.name} ({wine.producer or 'Unknown producer'})", key=f"pkg_wine_{i}"):
                    selected_wines.append(wine.name)
            
            if selected_wines:
                wine_bottles_name = st.text_area(
                    label="Wine Bottles Name: Separate by comma or a line break.",
                    value="\n".join(selected_wines)
                )
            else:
                wine_bottles_name = st.text_area(
                    label="Wine Bottles Name: Separate by comma or a line break.",
                    placeholder="Select wines above or enter manually"
                )
        else:
            wine_bottles_name = st.text_area(label="Wine Bottles Name: Separate by comma or a line break.")
    else:
        wine_bottles_name = st.text_area(label="Wine Bottles Name: Separate by comma or a line break.")
    
    submit = st.form_submit_button(label='Generate')


if submit:
    # Read the past email contents from CSV file
    with open(past_email_contents_path, "r") as f:
      # Skip the header, which is written in Japanese on the first line
      next(f)
      previous_email_contents = f.read()

    # * Monthly Concept
    if monthly_concept is not None or monthly_concept != "":
      monthly_concept_prompt = f"""
      ======
      ### Monthly Concept
      {monthly_concept}
      """
    else:
       monthly_concept_prompt = ""

    # * User Prompt reommending for a 6 bottles bundle monthly set
    system_prompt = f"""
    ## System Prompt
    You are a wine sommelier. Write the following four email contents in Japanese as a email marketing for wine EC: email-title, preview-text, introduction-latter-part, editor's-note.

    """
    user_prompt = f"""
    ## Special Monthly Set Package selected by our leading sommelier
    We are selling a special package of 6 bottles of wine. 
    The special package service name is "佐々布セレクション" because our leading sommelier's Sir name is "佐々布".
    This special package is free on sending fee. Appeal to the customers free on sending fee for this special package.
    
    ### Wine Package Information
    This month, we are selling a special package of 6 bottles of wine.
    The wine 6 bottles contents of the package are as follows. Each wine are separated by a comma or a line break.:
    {wine_bottles_name}
    --------

    ## Past Email Contents
    When writing, You can refer to the past email contents as below:
    {previous_email_contents}
    ------

    ## Wine Information in this time
    This email will be distributed at {distribute_date}.
    The wine information that you will recommend in this email is below. Especially, the key comments by our sommelier are important because these comments come from our sommelier in tasting party.

    {monthly_concept_prompt}
    ======
    ### Key Comments By Our Sommelier
    Comments are grouped by the wine bottles name. Not given all comments for each wine bottles, sometimes lack of comments for some wine bottles.
    Key Comments By Our Sommelier: {key_comments}
    ======

    ## Output Language: Japanese

    ## Instructions
    Now, Write the email contents in Japanese. You do not need to explain what the "笹麩セレクション" is. It's better to mention the season, or about the specialities of the month: Distribution Date is {distribute_date}.
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