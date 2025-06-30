import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Streamlit App
st.write("### Wine Library 🍷")
st.write("")

# Check for available wine data
wine_library_available = 'wine_library' in st.session_state and st.session_state['wine_library']
imported_wines_available = 'imported_wines' in st.session_state and st.session_state['imported_wines']['full_info']
processed_wines_available = 'processed_wines' in st.session_state and st.session_state['processed_wines']

# Collect all wines from different sources
all_wines = []
wine_sources = []

if processed_wines_available:
    for wine in st.session_state['processed_wines']:
        all_wines.append(wine)
        wine_sources.append("PDF Import (Latest)")

if wine_library_available:
    for wine_id, wine in st.session_state['wine_library'].items():
        # Avoid duplicates from processed wines
        if not any(w.name == wine.name and getattr(w, 'source_file', '') == getattr(wine, 'source_file', '') for w in all_wines):
            all_wines.append(wine)
            wine_sources.append("Wine Library")

if imported_wines_available and not wine_library_available:
    # Legacy imported wines (only if wine_library doesn't exist)
    for wine in st.session_state['imported_wines']['full_info']:
        if not any(w.name == wine.name for w in all_wines):
            all_wines.append(wine)
            wine_sources.append("Legacy Import")

if not all_wines:
    st.info("📦 No wines in your library yet!")
    st.write("Import wines from PDFs using the **PDF Import** page.")
    
    # Add link/button to PDF import page
    if st.button("📄 Go to PDF Import", type="primary"):
        st.switch_page("pages/pdf_import.py")
else:
    st.write(f"#### Total Wines in Library: {len(all_wines)}")
    
    # Library management
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        # Search functionality
        search_term = st.text_input("🔍 Search wines", placeholder="Search by name, producer, country...")
    
    with col2:
        # Filter by source
        unique_sources = list(set(wine_sources))
        if len(unique_sources) > 1:
            selected_source = st.selectbox("Filter by source", ["All"] + unique_sources)
        else:
            selected_source = "All"
    
    with col3:
        # Sort options
        sort_by = st.selectbox("Sort by", ["Name", "Producer", "Country", "Source File"])
    
    # Filter wines based on search and source
    filtered_wines = []
    filtered_sources = []
    
    for i, wine in enumerate(all_wines):
        # Apply source filter
        if selected_source != "All" and wine_sources[i] != selected_source:
            continue
            
        # Apply search filter
        if search_term:
            searchable_text = f"{wine.name} {wine.producer or ''} {wine.country or ''} {wine.grape_variety or ''} {wine.description or ''}".lower()
            if search_term.lower() not in searchable_text:
                continue
        
        filtered_wines.append(wine)
        filtered_sources.append(wine_sources[i])
    
    # Sort wines
    if sort_by == "Name":
        sorted_data = sorted(zip(filtered_wines, filtered_sources), key=lambda x: x[0].name.lower())
    elif sort_by == "Producer":
        sorted_data = sorted(zip(filtered_wines, filtered_sources), key=lambda x: (x[0].producer or "").lower())
    elif sort_by == "Country":
        sorted_data = sorted(zip(filtered_wines, filtered_sources), key=lambda x: (x[0].country or "").lower())
    else:  # Source File
        sorted_data = sorted(zip(filtered_wines, filtered_sources), key=lambda x: getattr(x[0], 'source_file', '').lower())
    
    filtered_wines, filtered_sources = zip(*sorted_data) if sorted_data else ([], [])
    
    if not filtered_wines:
        st.warning("🔍 No wines match your search criteria.")
    else:
        st.write(f"**Showing {len(filtered_wines)} wine(s)**")
        
        # Display options
        col1, col2 = st.columns([3, 1])
        with col1:
            view_mode = st.radio("Display mode:", ["Cards", "Table"], horizontal=True)
        with col2:
            if st.button("📊 Export to CSV"):
                # Create DataFrame for export
                export_data = []
                for wine in filtered_wines:
                    wine_dict = {
                        'Name': wine.name,
                        'Producer': wine.producer or '',
                        'Country': wine.country or '',
                        'Region': wine.region or '',
                        'Grape Variety': wine.grape_variety or '',
                        'Vintage': wine.vintage or '',
                        'Price': wine.price or '',
                        'Alcohol Content': wine.alcohol_content or '',
                        'Description': wine.description or '',
                        'Source File': getattr(wine, 'source_file', '')
                    }
                    export_data.append(wine_dict)
                
                df = pd.DataFrame(export_data)
                csv = df.to_csv(index=False)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="Download Wine Library CSV",
                    data=csv,
                    file_name=f"wine_library_{timestamp}.csv",
                    mime="text/csv"
                )
        
        st.divider()
        
        # Display wines
        if view_mode == "Cards":
            # Card view
            for i, wine in enumerate(filtered_wines):
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        # Wine card
                        with st.expander(f"🍷 {wine.name}", expanded=False):
                            col_left, col_right = st.columns(2)
                            
                            with col_left:
                                if wine.producer:
                                    st.write(f"**Producer:** {wine.producer}")
                                if wine.country:
                                    st.write(f"**Country:** {wine.country}")
                                if wine.region:
                                    st.write(f"**Region:** {wine.region}")
                                if wine.grape_variety:
                                    st.write(f"**Grape Variety:** {wine.grape_variety}")
                            
                            with col_right:
                                if wine.vintage:
                                    st.write(f"**Vintage:** {wine.vintage}")
                                if wine.price:
                                    st.write(f"**Price:** {wine.price}")
                                if wine.alcohol_content:
                                    st.write(f"**Alcohol:** {wine.alcohol_content}")
                                
                                # Source info
                                source_file = getattr(wine, 'source_file', 'Unknown')
                                if ',' in source_file:
                                    st.info(f"🔗 **Merged from:** {source_file}")
                                else:
                                    st.info(f"📄 **Source:** {source_file}")
                            
                            if wine.description:
                                st.write("**Description:**")
                                st.write(wine.description)
                    
                    with col2:
                        # Action buttons
                        if st.button("📧 Use for Email", key=f"email_{i}"):
                            st.session_state['selected_wine_for_email'] = wine
                            st.success("✅ Wine selected for email generation!")
                            st.info("💡 Go to 'Single Wine' page to create email.")
                
                st.write("")  # Add spacing
        
        else:
            # Table view
            table_data = []
            for i, wine in enumerate(filtered_wines):
                table_data.append({
                    "Name": wine.name,
                    "Producer": wine.producer or "-",
                    "Country": wine.country or "-", 
                    "Grape Variety": wine.grape_variety or "-",
                    "Source": filtered_sources[i],
                    "Action": f"Use_{i}"  # For button reference
                })
            
            df = pd.DataFrame(table_data)
            
            # Display table
            st.dataframe(
                df.drop('Action', axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # Action buttons below table
            st.write("**Quick Actions:**")
            cols = st.columns(min(5, len(filtered_wines)))
            for i, wine in enumerate(filtered_wines):
                with cols[i % 5]:
                    if st.button(f"📧 {wine.name[:15]}...", key=f"table_email_{i}"):
                        st.session_state['selected_wine_for_email'] = wine
                        st.success("✅ Wine selected!")

# Library management section
if all_wines:
    st.divider()
    st.write("#### Library Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_wines_in_library = len(st.session_state.get('wine_library', {}))
        st.metric("Wine Library", total_wines_in_library)
    
    with col2:
        total_processed = len(st.session_state.get('processed_wines', []))
        st.metric("Latest Import", total_processed)
    
    with col3:
        # Selected wine status
        if 'selected_wine_for_email' in st.session_state:
            st.metric("Selected Wine", "1")
            selected = st.session_state['selected_wine_for_email']
            st.caption(f"Selected: {selected.name}")
            if st.button("❌ Clear Selection"):
                del st.session_state['selected_wine_for_email']
                st.rerun()
        else:
            st.metric("Selected Wine", "0")
    
    # Danger zone
    with st.expander("🗑️ Clear Library Data", expanded=False):
        st.warning("⚠️ **Danger Zone** - These actions cannot be undone!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Wine Library", type="secondary"):
                if 'wine_library' in st.session_state:
                    del st.session_state['wine_library']
                st.success("Wine library cleared!")
                st.rerun()
        
        with col2:
            if st.button("Clear All Wine Data", type="secondary"):
                keys_to_clear = ['wine_library', 'imported_wines', 'processed_wines', 'selected_wine_for_email']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("All wine data cleared!")
                st.rerun()