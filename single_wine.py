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
except ImportError:
    # Fallback import
    sys.path.append('./src')
    from models_config import get_model_options, get_model_id, DEFAULT_MODEL, is_reasoning_model


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

# Manual wine merging section (only show if we have wines but no pre-selection)
if (wine_library_available or imported_wines_available) and not selected_wine_available:
    st.write("#### Wine Management")
    
    # Get all available wines
    all_available_wines = []
    wine_sources = []
    
    if wine_library_available:
        for wine_id, wine in st.session_state['wine_library'].items():
            all_available_wines.append(wine)
            wine_sources.append("Wine Library")
    
    if imported_wines_available and not wine_library_available:
        for wine in st.session_state['imported_wines']['full_info']:
            all_available_wines.append(wine)
            wine_sources.append("Legacy Import")
    
    if len(all_available_wines) > 1:
        tab1, tab2 = st.tabs(["🔗 Merge Duplicates", "📋 Wine List"])
        
        with tab1:
            st.info("💡 Found duplicates? Select two similar wines to merge them manually.")
            
            # Quick suggestions for potential duplicates
            if st.checkbox("🔍 Show potential duplicate suggestions"):
                st.write("**Potential duplicates based on similar names:**")
                suggestions = []
                for i, wine1 in enumerate(all_available_wines):
                    for j, wine2 in enumerate(all_available_wines[i+1:], i+1):
                        # Import here to avoid issues
                        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
                        from pdf_processor import calculate_wine_similarity
                        similarity = calculate_wine_similarity(wine1, wine2)
                        if similarity > 0.3:  # Show potential matches
                            suggestions.append((i, j, wine1.name, wine2.name, similarity))
                
                if suggestions:
                    # Sort by similarity score
                    suggestions.sort(key=lambda x: x[4], reverse=True)
                    for i, j, name1, name2, sim in suggestions[:5]:  # Show top 5
                        color = "🟢" if sim > 0.7 else "🟡" if sim > 0.5 else "🔵"
                        st.write(f"{color} **{sim:.3f}** - Wine {i}: _{name1}_ ↔ Wine {j}: _{name2}_")
                else:
                    st.write("No potential duplicates found with current algorithm.")
            
            # Create two columns for wine selection
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Wine 1:**")
                wine1_options = [f"{i}: {wine.name}" for i, wine in enumerate(all_available_wines)]
                wine1_idx = st.selectbox("Select first wine", range(len(all_available_wines)), 
                                       format_func=lambda x: wine1_options[x], key="merge_wine1")
                
                if wine1_idx is not None:
                    wine1 = all_available_wines[wine1_idx]
                    with st.expander(f"📝 Preview: {wine1.name}", expanded=True):
                        if wine1.producer:
                            st.write(f"**Producer:** {wine1.producer}")
                        if wine1.country:
                            st.write(f"**Country:** {wine1.country}")
                        if wine1.grape_variety:
                            st.write(f"**Grape:** {wine1.grape_variety}")
                        if wine1.description:
                            st.write(f"**Description:** {wine1.description[:100]}...")
            
            with col2:
                st.write("**Wine 2:**")
                wine2_options = [f"{i}: {wine.name}" for i, wine in enumerate(all_available_wines)]
                wine2_idx = st.selectbox("Select second wine", range(len(all_available_wines)), 
                                       format_func=lambda x: wine2_options[x], key="merge_wine2")
                
                if wine2_idx is not None:
                    wine2 = all_available_wines[wine2_idx]
                    with st.expander(f"📝 Preview: {wine2.name}", expanded=True):
                        if wine2.producer:
                            st.write(f"**Producer:** {wine2.producer}")
                        if wine2.country:
                            st.write(f"**Country:** {wine2.country}")
                        if wine2.grape_variety:
                            st.write(f"**Grape:** {wine2.grape_variety}")
                        if wine2.description:
                            st.write(f"**Description:** {wine2.description[:100]}...")
            
            # Show similarity score and merge button
            if wine1_idx is not None and wine2_idx is not None and wine1_idx != wine2_idx:
                wine1 = all_available_wines[wine1_idx]
                wine2 = all_available_wines[wine2_idx]
                from pdf_processor import calculate_wine_similarity
                similarity = calculate_wine_similarity(wine1, wine2)
                
                st.write(f"**Similarity Score:** {similarity:.3f}")
                if similarity > 0.7:
                    st.success("✅ High similarity - these wines likely match!")
                elif similarity > 0.4:
                    st.warning("⚠️ Moderate similarity - check carefully")
                else:
                    st.info("ℹ️ Low similarity - different wines or need manual review")
                
                # Merge button
                if st.button("🔗 Merge These Wines", type="primary"):
                    # Perform the merge
                    from pdf_processor import merge_wine_info
                    merged_wine = merge_wine_info(wine1, wine2)
                    
                    # Update wine library by removing both wines and adding merged one
                    if 'wine_library' in st.session_state:
                        # Find and remove the original wines
                        wine_library = st.session_state['wine_library'].copy()
                        keys_to_remove = []
                        for key, wine in wine_library.items():
                            if wine == wine1 or wine == wine2:
                                keys_to_remove.append(key)
                        
                        for key in keys_to_remove:
                            del wine_library[key]
                        
                        # Add merged wine
                        merged_key = f"{merged_wine.name}_merged"
                        wine_library[merged_key] = merged_wine
                        st.session_state['wine_library'] = wine_library
                    
                    # Also update imported_wines if it exists
                    if 'imported_wines' in st.session_state:
                        imported_wines = []
                        for wine in st.session_state['imported_wines']['full_info']:
                            if wine != wine1 and wine != wine2:
                                imported_wines.append(wine)
                        imported_wines.append(merged_wine)
                        st.session_state['imported_wines'] = {
                            'names': [wine.name for wine in imported_wines],
                            'full_info': imported_wines
                        }
                    
                    st.success(f"✅ Successfully merged '{wine1.name}' and '{wine2.name}'!")
                    st.info("🔄 Page will refresh to show updated wine list.")
                    st.rerun()
            elif wine1_idx == wine2_idx:
                st.warning("⚠️ Please select two different wines to merge.")
        
        with tab2:
            st.write(f"**Total wines available: {len(all_available_wines)}**")
            for i, wine in enumerate(all_available_wines):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{i}: {wine.name}**")
                    if wine.producer:
                        st.caption(f"Producer: {wine.producer}")
                with col2:
                    if st.button("📧 Use", key=f"use_wine_{i}"):
                        st.session_state['selected_wine_for_email'] = wine
                        st.success("✅ Wine selected!")
                        st.rerun()

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