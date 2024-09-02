import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from queries.data import default_start_date, default_end_date
from queries.farmer_queries import (
    getUniqueFarmersAttendedScreeningsQuery,
    getUniqueFarmersAttendedScreeningsExportQuery,
    getUniqueFarmersAttendedScreeningsCountQuery,
    getTotalFarmersParticipationCountQuery
)
from queries.location_queries import (
    getRegions,
    getWoredas,
    getVillages,
    getKebeles
)

from utils.db_utils import fetch_data
from utils.common_utils import populate_dropdown, to_excel, get_excel_filename

st.set_page_config(layout='wide')

def generate_excel_data(start_date, end_date, selected_state, selected_district, selected_block, selected_village):

    query = getUniqueFarmersAttendedScreeningsExportQuery(
        start_date, end_date, "Ethiopia", selected_state, selected_district, selected_block, selected_village
    )
    
    data = fetch_data(query)
    
    columns = [
        'ID', 'Person Name', 'Father Name', 'Age', 'Gender', 'Phone Number',
        'Video Title', 'Youtube ID', 'Region', 'Woreda', 'Kebele', 'Village'
    ]
    
    df = pd.DataFrame(data, columns=columns)
    
    excel_data = to_excel(df)
    
    return excel_data

def farmers_list():
    """
    Display a list of farmers based on user input and filters.
    """
    st.markdown('#### Farmers who participated in advisory sessions')

    css_path = "./style.css"
    try:
        with open(css_path, "r") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Custom CSS file not found.")

    col1, col2, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1])
    unique_number_of_farmers_col, total_number_of_farmers_participation_col = st.columns([1, 1])

    start_date = col1.date_input("Start Date", value=default_start_date)
    end_date = col2.date_input("End Date", value=default_end_date)

    selected_state = st.session_state.get('selected_state', 'none')
    selected_district = st.session_state.get('selected_district', 'none')
    selected_block = st.session_state.get('selected_block', 'none')
    selected_village = st.session_state.get('selected_village', 'none')

    page_size = 100 
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0
    page_number = st.session_state.page_number

    # Initialize download state
    if 'download_data' not in st.session_state:
        st.session_state.download_data = None

    try:
        # Fetch and populate regions
        state_data = fetch_data(getRegions())
        state_options = populate_dropdown(state_data)
        selected_state = col4.selectbox("Region", state_options, index=state_options.index(selected_state))
        st.session_state.selected_state = selected_state

        if selected_state:
            # Reset pagination and download state
            st.session_state.page_number = 0
            st.session_state.download_data = None

            # Fetch and populate woredas
            district_data = fetch_data(getWoredas(selected_state))
            district_options = populate_dropdown(district_data)
            selected_district = col5.selectbox("Woreda", district_options, index=district_options.index(selected_district))
            st.session_state.selected_district = selected_district

            if selected_district:
                # Fetch and populate kebeles
                block_data = fetch_data(getKebeles(selected_district))
                block_options = populate_dropdown(block_data)
                selected_block = col6.selectbox("Kebele", block_options, index=block_options.index(selected_block))
                st.session_state.selected_block = selected_block

                if selected_block:
                    # Fetch and populate villages
                    village_data = fetch_data(getVillages(selected_block))
                    village_options = populate_dropdown(village_data)
                    selected_village = col7.selectbox("Village", village_options, index=village_options.index(selected_village))
                    st.session_state.selected_village = selected_village

        # Query to get the count of unique farmers who attended screenings
        unique_farmers_count_query = getUniqueFarmersAttendedScreeningsCountQuery(
            start_date, end_date, "Ethiopia", selected_state, selected_district, selected_block, selected_village
        )
        unique_farmers_count_data = fetch_data(unique_farmers_count_query)

        total_unique_farmers = 0
        if unique_farmers_count_data and len(unique_farmers_count_data) > 0 and len(unique_farmers_count_data[0]) > 0:
            total_unique_farmers = unique_farmers_count_data[0][0]

        # Display the total number of farmers
        with unique_number_of_farmers_col:
            st.markdown(
                f'<div class="card">'
                f'<div class="title">Number Of Unique Farmers Participated</div>'
                f'<div class="sub-title"><span class="bullet_green">&#8226;</span> {total_unique_farmers:,}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
        unique_farmers_count_query = getTotalFarmersParticipationCountQuery(
            start_date, end_date, "Ethiopia", selected_state, selected_district, selected_block, selected_village
        )
        
        unique_farmers_count_data = fetch_data(unique_farmers_count_query)

        total_farmers_participations = 0
        if unique_farmers_count_data and len(unique_farmers_count_data) > 0 and len(unique_farmers_count_data[0]) > 0:
            total_farmers_participations = unique_farmers_count_data[0][0]

        # Display the total number of farmers
        with total_number_of_farmers_participation_col:
            st.markdown(
                f'<div class="card">'
                f'<div class="title">Total Number of Farmers Participations</div>'
                f'<div class="sub-title"><span class="bullet_green">&#8226;</span> {total_farmers_participations:,}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
        # Fetch farmer screening data
        query = getUniqueFarmersAttendedScreeningsQuery(
            start_date, end_date, "Ethiopia", selected_state, selected_district, selected_block, selected_village,
            page_number * page_size, page_size
        )
        farmer_screening_data = fetch_data(query)

        if farmer_screening_data:
            # Create DataFrame and configure AgGrid
            df = pd.DataFrame(
                farmer_screening_data,
                columns=['ID', 'Person Name', 'Father Name', 'Age', 'Gender', 'Phone Number', 'Youtube ID', 'Video Title', 'Region', 'Woreda', 'Kebele', 'Village']
            )

            # Grid options configuration
            grid_options = GridOptionsBuilder.from_dataframe(df)
            grid_options.configure_default_column(resizable=True, autoWidth=True)
            grid_options.configure_column(
                "Youtube ID",
                headerName="Youtube ID",
                cellRenderer=JsCode(
                    """
                    class UrlCellRenderer {
                        init(params) {
                            this.eGui = document.createElement('a');
                            this.eGui.innerText = params.value;
                            this.eGui.setAttribute('href', 'https://www.youtube.com/watch?v=' + params.value);
                            this.eGui.setAttribute('style', "text-decoration:none");
                            this.eGui.setAttribute('target', "_blank");
                        }
                        getGui() {
                            return this.eGui;
                        }
                    }
                    """
                ),
                width=300
            )
            grid_options = grid_options.build()

            # Render table with AgGrid
            AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True, width='100%', allow_unsafe_jscode=True)

            # Generate and download Excel file
            if st.button("Generate and Download Excel File"):
                excel_data = generate_excel_data(
                    start_date, end_date, selected_state, selected_district, selected_block, selected_village, 
                )
                st.download_button(
                    label="Download Excel File",
                    data=excel_data,
                    file_name=get_excel_filename(
                        'Farmers who participated in advisory sessions', selected_state, selected_district, selected_block, selected_village
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Pagination controls
            col1, col2, col3, col4 = st.columns([7, 1, 1, 1])  # Adjust column ratios as needed
            with col2:
                st.write(f"Page {st.session_state.page_number + 1}")

            with col3:
                if st.button('Previous Page') and st.session_state.page_number > 0:
                    st.session_state.page_number -= 1
                    st.session_state.download_data = None  # Reset download data
                    st.experimental_rerun()

            with col4:
                if len(df) == page_size and st.button('Next Page'):
                    st.session_state.page_number += 1
                    st.session_state.download_data = None  # Reset download data
                    st.experimental_rerun()

        else:
            st.write("No data available.")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Run the farmers list function
farmers_list()