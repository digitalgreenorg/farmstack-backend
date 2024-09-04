import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from queries.video_queries import (
    getVideosList,
    getNumberOfTotalVideosProducedQuery,
    getVideosListForExport,
    getNumberOfLanguagesUsedInVideoProductionQuery
)
from utils.db_utils import fetch_data
from queries.data import default_start_date, default_end_date
from utils.common_utils import populate_dropdown, to_excel, get_excel_filename
from queries.location_queries import getRegions, getWoredas, getVillages, getKebeles

# Streamlit app configuration
st.set_page_config(layout='wide')

# Function to generate Excel file data
def generate_excel_data(start_date, end_date, selected_state, selected_district, selected_block, selected_village):
    query = getVideosListForExport(start_date, end_date, selected_state, selected_district, selected_block, selected_village)
    data = fetch_data(query)
    df = pd.DataFrame(
        data,
        columns=['Video ID', 'Video Title', 'Video Created', 'Youtube ID', 'Region Name', 'Woreda Name', 'Kebele Name', 'Village Name', 'Language']
    )
    return to_excel(df)

def videos_list():
    try:
        with open("./style.css", "r") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Custom CSS file not found.")
        
    st.markdown('#### Videos Stat list')

    if 'page' not in st.session_state:
        st.session_state.page = 1
        
    col1, col2, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1])
    selected_state = 'none'
    selected_district = 'none'
    selected_block = 'none'
    selected_village = 'none'

    # Date range selection
    start_date = col1.date_input("Start Date", value=default_start_date)
    end_date = col2.date_input("End Date", value=default_end_date)

    # Dropdown selections
    state_data = fetch_data(getRegions())
    state_options = populate_dropdown(state_data)
    selected_state = col4.selectbox("Region", state_options)

    if selected_state:
        district_data = fetch_data(getWoredas(selected_state))
        district_options = populate_dropdown(district_data)
        selected_district = col5.selectbox("Woreda", district_options)

        if selected_district:
            block_data = fetch_data(getKebeles(selected_district))
            block_options = populate_dropdown(block_data)
            selected_block = col6.selectbox("Kebele", block_options)

            if selected_block:
                village_data = fetch_data(getVillages(selected_block))
                village_options = populate_dropdown(village_data)
                selected_village = col7.selectbox("Village", village_options)

    # Fetch statistics
    items_per_page = 20
    total_videos = fetch_data(getNumberOfTotalVideosProducedQuery(start_date, end_date, selected_state, selected_district, selected_block, selected_village))
    total_languages = fetch_data(getNumberOfLanguagesUsedInVideoProductionQuery(start_date, end_date, selected_state, selected_district, selected_block, selected_village))

    number_of_videos_col, number_of_languages_col = st.columns([1, 1])

    if total_videos and len(total_videos) > 0:
        total_videos_count = total_videos[0][0]
    else:
        total_videos_count = 0

    if total_languages and len(total_languages) > 0:
        total_languages_count = total_languages[0][0]
    else:
        total_languages_count = 0

    with number_of_videos_col:
        st.markdown(f'<div class="card"><div class="title">Total Videos Produced</div><div class="sub-title"><span class="bullet_green">&#8226;</span> {total_videos_count:,}</div></div>', unsafe_allow_html=True)

    with number_of_languages_col:
        st.markdown(f'<div class="card"><div class="title">Total Languages Used In Video Production</div><div class="sub-title"><span class="bullet_green">&#8226;</span> {total_languages_count:,}</div></div>', unsafe_allow_html=True)

    # Fetch video data
    query = getVideosList(start_date, end_date, selected_state, selected_district, selected_block, selected_village, page=st.session_state.page, items_per_page=items_per_page)
    videos_data = fetch_data(query)

    # Header and download button
    header_col, button_col = st.columns([3, 1])
    with header_col:
        st.markdown('#### Videos list')
    with button_col:
        if st.button("Generate and Download Excel File"):
            excel_data = generate_excel_data(start_date, end_date, selected_state, selected_district, selected_block, selected_village)
            st.download_button(
                label="Download Excel File",
                data=excel_data,
                file_name=get_excel_filename('Total Videos', selected_state, selected_district, selected_block, selected_village),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    if videos_data:
        df_videos_data = pd.DataFrame(
            videos_data,
            columns=['Video ID', 'Video Title', 'Video Created', 'Youtube ID', 'Region Name', 'Woreda Name', 'Kebele Name', 'Village Name', 'Language']
        )

        grid_options = GridOptionsBuilder.from_dataframe(df_videos_data)
        grid_options.configure_default_column(resizable=True, autoWidth=True)
        grid_options.configure_column('Youtube ID', cellRenderer='htmlRenderer')
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
            width=300,
        )
        grid_options = grid_options.build()

        AgGrid(df_videos_data, gridOptions=grid_options, enable_enterprise_modules=True, width='100%', allow_unsafe_jscode=True)

        # Pagination controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.session_state.page > 1:
                if st.button('Previous', key='prev', help="Go to the previous page"):
                    st.session_state.page -= 1
                    st.rerun()
        with col2:
            st.write(f"**Page {st.session_state.page}**")
        with col3:
            if len(videos_data) == items_per_page:
                if st.button('Next', key='next', help="Go to the next page"):
                    st.session_state.page += 1
                    st.rerun()

    st.markdown("<div style='padding-bottom: 50px;'></div>", unsafe_allow_html=True)

videos_list()
