from openai import OpenAI
import streamlit as st
import sys
import os

# Import authentication
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from auth import auth

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from src.models_config import get_model_options, get_model_id, DEFAULT_MODEL, is_reasoning_model
    from src.wine_merger import merge_wines, format_wine_preview, get_wine_summary
except ImportError:
    # Fallback import
    sys.path.append('../src')
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
past_email_contents_path = "./src/6bottles-mail-contents_2025-06-29.csv"

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

# Wine Selection Section
st.write("#### Wine Selection for 6-Bottle Package")

# Check for available wine sources
wine_library_available = 'wine_library' in st.session_state and st.session_state['wine_library']
imported_wines_available = 'imported_wines' in st.session_state and st.session_state['imported_wines']['full_info']

# Initialize
all_wines = []
selected_wine_packages = []

# Collect all available wines
if wine_library_available:
    for wine_id, wine in st.session_state['wine_library'].items():
        all_wines.append(wine)

if imported_wines_available and 'wine_library' not in st.session_state:
    for wine in st.session_state['imported_wines']['full_info']:
        all_wines.append(wine)

# Wine selection logic
if all_wines:
    # Selection mode toggle
    use_library = st.radio(
        "Wine source:", 
        ["From Wine Library", "Manual Input"], 
        horizontal=True,
        key="wine_source_mode"
    )
    
    if use_library == "From Wine Library":
        st.info("Select 6 wines for the package. Each wine can be a single wine or combination of two wines.")
        
        # Add option numbers to wine labels
        numbered_wine_options = [f"{i+1}. {wine.name} ({wine.producer or 'Unknown'})" for i, wine in enumerate(all_wines)]
        
        # Initialize session state for wine selections
        if 'package_wines' not in st.session_state:
            st.session_state['package_wines'] = [{} for _ in range(6)]
        
        # Selection for each of the 6 wine positions
        for i in range(6):
            with st.expander(f"🍷 Wine {i+1}", expanded=True):
                # Wine count selection for this position
                wine_count_key = f"wine_count_{i}"
                selection_mode = st.radio(
                    f"Number of wines for position {i+1}:",
                    ["Single Wine", "Two Wines"],
                    horizontal=True,
                    key=wine_count_key
                )
                
                if selection_mode == "Single Wine":
                    # Single wine selection
                    wine_key = f"wine_single_{i}"
                    selected_idx = st.selectbox(
                        f"Select wine for position {i+1}:", 
                        range(len(all_wines)), 
                        format_func=lambda x: numbered_wine_options[x],
                        key=wine_key
                    )
                    st.session_state['package_wines'][i] = {
                        'wines': [all_wines[selected_idx]],
                        'type': 'single'
                    }
                    
                    # Display selection
                    wine = all_wines[selected_idx]
                    st.success(f"Selected: {wine.name} ({wine.producer or 'Unknown'})")
                    
                else:
                    # Two wine selection
                    first_key = f"wine_first_{i}"
                    second_key = f"wine_second_{i}"
                    
                    first_idx = st.selectbox(
                        f"First wine for position {i+1}:", 
                        range(len(all_wines)), 
                        format_func=lambda x: numbered_wine_options[x],
                        key=first_key
                    )
                    
                    # Filter out the first selected wine from second dropdown
                    available_second = [j for j in range(len(all_wines)) if j != first_idx]
                    if available_second:
                        second_idx_pos = st.selectbox(
                            f"Second wine for position {i+1}:", 
                            range(len(available_second)), 
                            format_func=lambda x: numbered_wine_options[available_second[x]],
                            key=second_key
                        )
                        second_idx = available_second[second_idx_pos]
                        
                        selected_wines = [all_wines[first_idx], all_wines[second_idx]]
                        st.session_state['package_wines'][i] = {
                            'wines': selected_wines,
                            'type': 'merged'
                        }
                        
                        # Merge and display
                        merged_wine = merge_wines(selected_wines)
                        st.success(get_wine_summary(merged_wine))
                        st.caption(f"📍 {format_wine_preview(merged_wine)}")
                    else:
                        st.warning("Need at least 2 wines in library for two-wine selection")
                        st.session_state['package_wines'][i] = {
                            'wines': [all_wines[first_idx]],
                            'type': 'single'
                        }
        
        # Package summary
        if all(pkg.get('wines') for pkg in st.session_state['package_wines']):
            st.write("#### Package Summary")
            wine_names = []
            for i, pkg in enumerate(st.session_state['package_wines']):
                if pkg['type'] == 'merged':
                    merged = merge_wines(pkg['wines'])
                    wine_names.append(f"{i+1}. {merged.names}")
                else:
                    wine = pkg['wines'][0]
                    wine_names.append(f"{i+1}. {wine.name}")
            
            st.success("📦 **6-Bottle Package Selection Complete**")
            for name in wine_names:
                st.write(f"  {name}")
        
else:
    st.info("💡 No wines in library. Enter wine information manually below.")

# Input Form
st.write("#### Email Generation")
with st.form(key='ask_input_form'):
    # Key Comments and Date
    st.write("##### Key Comments and Distribute Date")
    monthly_concept = st.text_input("Monthly Concept")
    key_comments = st.text_area("Key Comments in the tasting party")
    distribute_date = st.date_input("Email Distribute Date")
    
    st.divider()
    
    # Wine Information Section
    st.write("##### Wine Information")
    
    # Determine if we should use manual input or wine library
    manual_input = False
    if all_wines and 'wine_source_mode' in st.session_state:
        manual_input = st.session_state['wine_source_mode'] == "Manual Input"
    elif not all_wines:
        manual_input = True
    
    if manual_input:
        # Manual wine input - single comprehensive text area
        st.write("**Manual Wine Package Input:**")
        st.info("💡 Enter all wine information in the text area below. You can organize it however you prefer - by wine name, with details, etc.")
        
        wine_package_info = st.text_area(
            "Wine Package Information:",
            placeholder="""Enter your 6-wine package information here. You can format it however you like, for example:

Wine 1: [Name] - [Producer] - [Country] - [Grape Variety]
Wine 2: [Name] - [Producer] - [Country] - [Grape Variety]
...

Or simply list the wine names:
1. Wine Name 1
2. Wine Name 2
...

Include any additional details, tasting notes, or comments about the wines.""",
            height=300,
            help="Enter all wine information in your preferred format"
        )
        
        # Set default values for backward compatibility (these will be used in the combined format)
        wine_bottles_name = wine_package_info  # Use the full text for wine names
        producers = ""
        wine_countries = ""
        wine_cepages = ""
        package_comments = ""
        
        # For manual input, we'll format as grouped information in the prompt
        use_grouped_format = False
    else:
        # Use selected wines from library
        if 'package_wines' in st.session_state and all(pkg.get('wines') for pkg in st.session_state['package_wines']):
            # Store individual wine details for grouped format
            wine_details = []
            wine_names = []
            
            for i, pkg in enumerate(st.session_state['package_wines']):
                if pkg['type'] == 'merged':
                    merged = merge_wines(pkg['wines'])
                    wine_details.append({
                        'position': i + 1,
                        'name': merged.names,
                        'producer': merged.producers,
                        'country': merged.countries,
                        'cepage': merged.grape_varieties,
                        'description': merged.descriptions or ""
                    })
                    wine_names.append(merged.names)
                else:
                    wine = pkg['wines'][0]
                    wine_details.append({
                        'position': i + 1,
                        'name': wine.name or "",
                        'producer': wine.producer or "",
                        'country': wine.country or "",
                        'cepage': wine.grape_variety or "",
                        'description': getattr(wine, 'description', "") or ""
                    })
                    wine_names.append(wine.name or "")
            
            # Store wine details in session state for use in prompt
            st.session_state['wine_details_for_prompt'] = wine_details
            use_grouped_format = True
            
            # Display grouped wine information
            st.write("**Wine Package Details:**")
            
            # Create two columns for better layout
            col1, col2 = st.columns(2)
            
            for i, detail in enumerate(wine_details):
                # Alternate between columns
                with col1 if i % 2 == 0 else col2:
                    with st.expander(f"🍷 Wine {detail['position']}: {detail['name']}", expanded=False):
                        st.write(f"**Producer:** {detail['producer'] or 'Not specified'}")
                        st.write(f"**Country:** {detail['country'] or 'Not specified'}")
                        st.write(f"**Cépage:** {detail['cepage'] or 'Not specified'}")
                        if detail['description']:
                            st.write(f"**Description:**")
                            st.write(detail['description'])
                        else:
                            st.write("**Description:** Not available")
            
            # Also provide the simple text area for editing if needed
            with st.expander("📝 Edit Wine Names (if needed)", expanded=False):
                wine_bottles_name = st.text_area(
                    "Wine Bottles Name: Separate by comma or a line break.",
                    value="\n".join(wine_names),
                    help="You can edit the wine names here if needed"
                )
            
            # Set default values for the variables (they won't be used in grouped format but needed for form submission)
            producers = " / ".join([detail['producer'] for detail in wine_details if detail['producer']])
            wine_countries = " / ".join(list(set([detail['country'] for detail in wine_details if detail['country']])))
            wine_cepages = " / ".join([detail['cepage'] for detail in wine_details if detail['cepage']])
            package_comments = "\n".join([f"Wine {detail['position']}: {detail['description']}" for detail in wine_details if detail['description']])
        else:
            wine_bottles_name = st.text_area(
                "Wine Bottles Name: Separate by comma or a line break.",
                placeholder="Complete wine selection above or enter manually"
            )
            producers = st.text_input("Producers", placeholder="Producers for the 6 wines")
            wine_countries = st.text_input("Wine Countries", placeholder="e.g., France, Italy, Spain")
            wine_cepages = st.text_input("Wine Cépages", placeholder="Grape varieties for the wines")
            package_comments = st.text_area("Package Comments", placeholder="Overall package tasting notes, wine characteristics, vintage details, etc.", height=250)
            use_grouped_format = False
    
    submit = st.form_submit_button("🚀 Generate Email", type="primary")

if submit:
    # Read the past email contents from CSV file
    with open(past_email_contents_path, "r") as f:
        # Skip the header, which is written in Japanese on the first line
        next(f)
        previous_email_contents = f.read()

    # * Monthly Concept
    if monthly_concept:
        monthly_concept_prompt = f"""
      ======
      ### Monthly Concept
      {monthly_concept}
      """
    else:
        monthly_concept_prompt = ""

    # Define the Prompt
    system_prompt = """
    ## System Prompt
    You are a wine sommelier. Write the following four email contents in Japanese as a email marketing for wine EC: email-title, preview-text, introduction-latter-part, editor's-note.
    """

    # Generate wine information section based on format
    if 'wine_details_for_prompt' in st.session_state and st.session_state['wine_details_for_prompt']:
        # Use grouped format with individual wine details
        wine_info_section = "### Wine Package Information (6 bottles)\n"
        for detail in st.session_state['wine_details_for_prompt']:
            wine_info_section += f"""
Wine {detail['position']}: {detail['name']}
- Producer: {detail['producer']}
- Country: {detail['country']}
- Cépage: {detail['cepage']}
- Description: {detail['description']}
"""
    else:
        # Use combined format for manual input
        wine_info_section = f"""### Wine Package Information
This month, we are selling a special package of 6 bottles of wine.
The wine package information provided by the user is:

{wine_bottles_name}"""

    # * User Prompt recommending for a 6 bottles bundle monthly set
    user_prompt = f"""
    ## Special Monthly Set Package selected by our leading sommelier
    We are selling a special package of 6 bottles of wine. 
    The special package service name is "佐々布セレクション" because our leading sommelier's Sir name is "佐々布".
    This special package is free on sending fee. Appeal to the customers free on sending fee for this special package.
    
    {wine_info_section}
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
    Now, Write the email contents in Japanese. Use Emoji in the email contents, but not too many. You do not need to explain what the "佐々布セレクション" is. It's better to mention the season, or about the specialities of the month: Distribution Date is {distribute_date}.
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