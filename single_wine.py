from openai import OpenAI
import streamlit as st


# Initialize OpenAI Client
client = OpenAI()

## * Settings
# File Path
past_email_contents_path = "./src/backstreet-mail-contents_2024-07-01.csv"

## OpenAI
model = "gpt-4.1"
temperature = 0.3

## * Streamlit App
# Tool Title
st.write("### Email Generator: Single Wine 🍷")
st.write("")

# Input Form
st.write("#### Input Form to Generate Email Contents")
with st.form(key='ask_input_form'):
    st.write("##### Key Comments and Distribute Date")
    key_comments = st.text_area(label="Key Comments in the tasting party")
    distribute_date = st.date_input(label="Email Distribute Date")
    st.divider()
    # Wine Information
    st.write("##### Wine Information")
    wine_name = st.text_input(label="Wine Name")
    producer = st.text_input(label="Producer")
    # wine_info = st.text_area(label="Wine Information")
    wine_country = st.selectbox(label="Wine Country", options=[
    "France", 
    "Italy", 
    "Spain", 
    "Germany", 
    "Portugal",
    "America",
    "South Africa"
    ])
    wine_cepage = st.text_input(label="Wine Cépage")
    # tasting_comments_onpage = st.text_area(label="Tasting Comments on the webpage")
    submit = st.form_submit_button(label='Generate')


if submit:
    # Read the past email contents from CSV file
    with open(past_email_contents_path, "r") as f:
        # Skip the header, which is written in Japanese on the first line
        next(f)
        previous_email_contents = f.read()

    
    # Define the Prompt
    system_prompt = f"""
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
    response = client.chat.completions.create(
    model=model,
    messages=[
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt}
      ],
      temperature=temperature
    )

    # Display the response
    st.write(response.choices[0].message.content)
    # st.divider()
    # st.code(response.choices[0].message.content)