from concurrent.futures import ThreadPoolExecutor
import json
import streamlit as st
import pandas as pd

# Import queries
from queries.data import default_start_date, default_end_date, daas_woreda_ids
from queries.home_queries import (
    get_unique_farmers_attended_screenings_query,
    get_unique_farmers_adopting_practice_query,
    get_unique_screenings_query,
    get_videos_shown_in_screenings_query,
    get_videos_produced_query,
    getFarmerGroupReached,
    getAdoptionQuery,
    getScreeningQuery,
    getAdoptionQueryByYear,
    getScreeningQueryByYear,
    getFarmersAttendingVideoScreeningByGender,
    getFarmersAdoptRateByGender,
    getUniqueFarmersUsingMonthAndYearForScreeningAndAdoptionGraph,
    getUniqueFarmersUsingYearForScreeningAndAdoptionGraph
)
from queries.location_queries import (
    getRegions,
    getWoredas,
    getVillages,
    getKebeles
)
from utils.db_utils import fetch_data
from utils.common_utils import populate_dropdown

# Set up Streamlit page configuration
st.set_page_config(
    layout="wide",  
    initial_sidebar_state="auto",
    page_title="COCO Dashboard",
    page_icon=None
)

# Set page title and custom CSS
st.title("COCO Dashboard")
st.markdown(
    r"""
    <style>
        .stDeployButton {
            visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True
)

# Prepare Woreda IDs for queries
daas_woreda_ids_str = ', '.join(map(str, daas_woreda_ids))

# Function to calculate gender percentage
def calculate_gender_percentage(df):
    # Filter gender column to include only 'M' and 'F'
    df = df[df['gender'].isin(['M', 'F'])]
    
    if df.empty:
        return 0.0, 0.0

    # Calculate total attendance count
    total_attendance = df['attendance_count'].sum()

    # Calculate percentage attendance for each gender
    df = df.copy()  # Creates a deep copy to avoid modifying the original DataFrame
    df['percentage'] = (df['attendance_count'] / total_attendance) * 100

    # Access male and female percentages
    male_percentage = df.loc[df['gender'] == 'M', 'percentage'].iloc[0] if not df[df['gender'] == 'M'].empty else 0.0
    female_percentage = df.loc[df['gender'] == 'F', 'percentage'].iloc[0] if not df[df['gender'] == 'F'].empty else 0.0
    
    return round(male_percentage, 2), round(female_percentage, 2)

def create_card(title, value):
    st.markdown(
        f'''
        <div class="card">
            <div class="title">{title}</div>
            <div class="sub-title">
                <span class="bullet_green">&#8226;</span> {value:,}
            </div>
        </div>
        ''', unsafe_allow_html=True
        )
    
# Main function to create the dashboard
def main():
    # Link to external CSS file
    with open("./style.css", "r") as f:
        css = f.read()
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

    # Define columns for layout
    col1, col2, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1])
    col8, col10, col11 = st.columns([1, 1, 1])
    col12, col13, col14, col15 = st.columns([1, 1, 1, 1])
    col16, col17, col18 = st.columns([1, 1, 1])
    col21, col22 = st.columns([1, 1])

    # Create date range selection
    start_date = col1.date_input("Start Date", value=default_start_date)
    end_date = col2.date_input("End Date", value=default_end_date)

    # Initialize variables with default values
    selected_state = 'none'
    selected_district = 'none'
    selected_block = 'none'
    selected_village = 'none'

    unique_farmers_attended_screenings_query = 0
    total_screening_farmers_query = 0
    unique_farmers_adopting_practice_query = 0
    adoption_by_farmers_query = 0
    unique_screenings_query = 0
    videos_shown_in_screenings_query = 0
    videos_produced_query = 0
    farmer_group_reached_query = 0
    adoption_data = 0
    screening_data = 0
    adoption_year_data = 0
    screening_year_data = 0

    # profiler.enable()
    state_data = fetch_data(getRegions())
    state_options = populate_dropdown(state_data)
    selected_state = col4.selectbox("Region", state_options)
    # profiler.disable()
    # print_function_profile_stat(profiler=profiler, print_title="Profile for fetch_district_data:")
    if selected_state != None:
        district_data = fetch_data(getWoredas(selected_state))
        district_options = populate_dropdown(district_data)
        selected_district = col5.selectbox("Woreda", district_options)

        if selected_district != None:
            block_data = fetch_data(getKebeles(selected_district))
            block_options = populate_dropdown(block_data)
            selected_block = col6.selectbox("Kebele", block_options)

            if selected_block != None:
                village_data = fetch_data(getVillages(selected_block))
                village_options = populate_dropdown(village_data)
                selected_village = col7.selectbox("Village", village_options)


    # Create query parameters
    query_params =  (start_date, end_date, "Ethiopia", selected_state, selected_district, selected_block, selected_village)

    # Use ThreadPoolExecutor to fetch data concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(fetch_data, get_unique_farmers_attended_screenings_query(*query_params)),
            executor.submit(fetch_data, get_unique_farmers_adopting_practice_query(*query_params)),
            executor.submit(fetch_data, get_unique_screenings_query(*query_params)),
            executor.submit(fetch_data, get_videos_shown_in_screenings_query(*query_params)),
            executor.submit(fetch_data, get_videos_produced_query(*query_params)),
            executor.submit(fetch_data, getFarmerGroupReached(*query_params)),
            executor.submit(fetch_data, getAdoptionQuery(*query_params)),
            executor.submit(fetch_data, getScreeningQuery(*query_params)),
            executor.submit(fetch_data, getAdoptionQueryByYear(*query_params)),
            executor.submit(fetch_data, getScreeningQueryByYear(*query_params)),
            executor.submit(fetch_data, getFarmersAttendingVideoScreeningByGender(*query_params)),
            executor.submit(fetch_data, getFarmersAdoptRateByGender(*query_params)),
            executor.submit(fetch_data, getUniqueFarmersUsingMonthAndYearForScreeningAndAdoptionGraph(*query_params)),
            executor.submit(fetch_data, getUniqueFarmersUsingYearForScreeningAndAdoptionGraph(*query_params))
        ]

        # Retrieve results from futures
        (
            farmer_screening_data, # get_unique_farmers_attended_screenings_query
            adoption_by_farmers_data, # get_unique_farmers_adopting_practice_query
            unique_screenings_query, # get_unique_screenings_query
            videos_shown_in_screenings_query, # get_videos_shown_in_screenings_query
            videos_produced_query, # get_videos_produced_query
            farmer_group_reached_query, # getFarmerGroupReached 
            adoption_data, # getAdoptionQuery 
            screening_data, # getScreeningQuery 
            adoption_year_data, # getAdoptionQueryByYear 
            screening_year_data, # getScreeningQueryByYear 
            table_data_1, # getFarmersAttendingVideoScreeningByGender
            table_data_2, # getFarmersAdoptRateByGender
            unique_farmers_using_month_year_graph, # getUniqueFarmersUsingMonthAndYearForScreeningAndAdoptionGraph
            unique_farmers_using_year_graph # getUniqueFarmersUsingYearForScreeningAndAdoptionGraph
        ) = [future.result() for future in futures]

    # Unpack specific data from fetched results
    unique_farmers_attended_screenings_query, total_screening_farmers_query = farmer_screening_data[0]
    unique_farmers_adopting_practice_query, adoption_by_farmers_query = adoption_by_farmers_data[0]

    # Table 1
    df_table_1 = pd.DataFrame(table_data_1, columns=['gender', 'attendance_count'])
    male_percentage_rounded, female_percentage_rounded = calculate_gender_percentage(df_table_1)

    data_1 = {
        'Gender': ['M', 'F'],
        'Percentage': [male_percentage_rounded, female_percentage_rounded]
    }
    df_1 = pd.DataFrame(data_1)
    sorted_df_1 = df_1.sort_values(by='Percentage', ascending=False)

    # Table 2
    df_table_2 = pd.DataFrame(table_data_2, columns=['gender', 'attendance_count'])
    male_adopt_percentage_rounded, female_adopt_percentage_rounded = calculate_gender_percentage(df_table_2)

    data_2 = {
        'Gender': ['M', 'F'],
        'Percentage': [male_adopt_percentage_rounded, female_adopt_percentage_rounded]
    }
    df_2 = pd.DataFrame(data_2)
    sorted_df_2 = df_2.sort_values(by='Percentage', ascending=False)
    
    # screening with years
    adoption_year_counts = {}
    screening_year_counts = {}

    # Aggregate counts for each year
    for row in adoption_year_data:
        year = str(row[1])
        if year in adoption_year_counts:
            adoption_year_counts[year] += row[0]
        else:
            adoption_year_counts[year] = row[0]

    for row in screening_year_data:
        year = str(row[1])
        if year in screening_year_counts:
            screening_year_counts[year] += row[0]
        else:
            screening_year_counts[year] = row[0]
    
    adoption_counts = [0] * 12  # Initialize counts for each month with zeros
    screening_counts = [0] * 12  # Initialize counts for each month with zeros

    for row in adoption_data:
        month_index = int(row[1]) - 1  # Convert month number to index
        adoption_counts[month_index] = row[0]  # Update adoption count for the month

    for row in screening_data:
        month_index = int(row[1]) - 1  # Convert month number to index
        screening_counts[month_index] = row[0]  # Update screening count for the month

        
    with col10:
        st.write("% of Farmers Attending Video Screenings, by Gender")
        st.dataframe(sorted_df_1, hide_index=True, use_container_width=True)

    with col11:
        st.write("Adoption Rate by Gender")
        st.dataframe(sorted_df_2, hide_index=True, use_container_width=True)


    # Data to display in the cards
    if unique_screenings_query and len(unique_screenings_query) > 0 and len(unique_screenings_query[0]) > 0:
        unique_screenings_query_number = unique_screenings_query[0][0]
    if videos_shown_in_screenings_query and len(videos_shown_in_screenings_query) > 0 and len(videos_shown_in_screenings_query[0]) > 0:
        videos_shown_in_screenings_query_number = videos_shown_in_screenings_query[0][0]
    if videos_produced_query and len(videos_produced_query) > 0 and len(videos_produced_query[0]) > 0:
        videos_produced_query_number = videos_produced_query[0][0]
    if farmer_group_reached_query and len(farmer_group_reached_query) > 0 and len(farmer_group_reached_query[0]) > 0:
        farmer_group_reached_query_number = farmer_group_reached_query[0][0]

    card_data = [
        ("Unique Farmers Who Attended Video Screenings", unique_farmers_attended_screenings_query),
        ("Total Number of Farmers Who Attended Video Screenings", total_screening_farmers_query),
        ("Unique Farmers Adopting At Least One Practice", unique_farmers_adopting_practice_query),
        ("Total Number of Adoptions by Farmers", adoption_by_farmers_query),
        ("Total Number of Unique Screenings", unique_screenings_query_number),
        ("Total Number of Videos Shown in Screenings", videos_shown_in_screenings_query_number),
        ("Total Number of Videos Produced in Selected Period and Location", videos_produced_query_number),
        ("Total Number of Farmers Groups Reached", farmer_group_reached_query_number)
    ]

    # Display cards in card_columns
    card_columns = [col8, col12, col13, col14, col15, col16, col17, col18]
    for col, (title, value) in zip(card_columns, card_data):
        with col:
            create_card(title, value)
            
    # Process data for screening and adoption by year and month
    data_by_year_and_month = {}

    for entry in unique_farmers_using_month_year_graph:
        if len(entry) != 4:
            continue

        year, month, adoption_count, screening_count = entry
        year_str = str(year)
        month_index = month - 1  # Convert month to zero-based index

        if year_str not in data_by_year_and_month:
            data_by_year_and_month[year_str] = {
                'screeningData': [0] * 12,
                'adoptionData': [0] * 12
            }

        data_by_year_and_month[year_str]['screeningData'][month_index] = screening_count
        data_by_year_and_month[year_str]['adoptionData'][month_index] = adoption_count

    # Convert processed data to JSON
    data_by_year_and_month_json = json.dumps(data_by_year_and_month)

    # HTML and JavaScript for monthly data chart
    with col21:
        html_content = f"""
        <style>
            body {{ color: #333; }}
            select {{ color: inherit; background-color: inherit; border: 1px solid #ccc; padding: 5px; }}
            @media (prefers-color-scheme: dark) {{
                body {{ color: #fff; }}
                select {{ background-color: #333; color: #fff; border: 1px solid #666; }}
            }}
        </style>
        <div style="margin-bottom: 10px; height: 30px;">
            <label for="yearSelect">Select Year: </label>
            <select id="yearSelect"></select>
        </div>
        <div id="main" style="width: 100%; height: 300px; background-color: #f0f0f0;"></div>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.1.2/dist/echarts.min.js"></script>
        <script>
            var chartDom = document.getElementById('main');
            var myChart = echarts.init(chartDom);
            var data = {data_by_year_and_month_json};
            var monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

            function updateChart(year) {{
                var screeningData = data[year].screeningData;
                var adoptionData = data[year].adoptionData;
                var maxValue = Math.ceil(Math.max(...screeningData, ...adoptionData) / 100) * 100;
                var yAxisInterval = Math.ceil(maxValue / 5);

                myChart.setOption({{
                    title: {{ text: 'Unique Farmers in Screening and Adoption by Month', top: '3%', left: '1%' }},
                    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross', label: {{ backgroundColor: '#6a7985' }} }} }},
                    legend: {{ data: ['Screening', 'Adoption'], x: 'right', left: '80%', top: '3%' }},
                    grid: {{ left: '5%', right: '5%', bottom: '10%', containLabel: true }},
                    xAxis: {{ type: 'category', data: monthNames, name: 'Month', nameLocation: 'center', nameGap: 30 }},
                    yAxis: {{ type: 'value', max: maxValue, interval: yAxisInterval, name: 'Number', nameLocation: 'center', nameGap: 60 }},
                    series: [
                        {{ name: 'Screening', type: 'line', areaStyle: {{}}, emphasis: {{ focus: 'series' }}, data: screeningData }},
                        {{ name: 'Adoption', type: 'line', areaStyle: {{}}, emphasis: {{ focus: 'series' }}, data: adoptionData }}
                    ]
                }});
            }}

            const yearSelect = document.getElementById('yearSelect');
            Object.keys(data).forEach(year => {{
                var option = document.createElement('option');
                option.value = year;
                option.text = year;
                yearSelect.appendChild(option);
            }});

            yearSelect.addEventListener('change', function() {{ updateChart(this.value); }});
            updateChart(yearSelect.value);
            window.addEventListener('resize', function() {{ myChart.resize(); }});
        </script>
        """
        st.components.v1.html(html_content, height=400)

    # HTML and JavaScript for yearly data chart
    with col22:
        data_by_year_json = json.dumps([
            {"year": year, "adoption": adoption, "screening": screening}
            for year, adoption, screening in unique_farmers_using_year_graph
        ])

        html_content = f"""
        <div style="margin-bottom: 10px; height: 30px;">
        </div>
        <div id="main_year" style="width: 100%; height: 300px; background-color: #f0f0f0;"></div>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.1.2/dist/echarts.min.js"></script>
        <script>
            var chartDom = document.getElementById('main_year');
            var myChart = echarts.init(chartDom);
            var data = {data_by_year_json};
            var yearNames = data.map(item => item.year.toString());
            var screeningData = data.map(item => item.screening);
            var adoptionData = data.map(item => item.adoption);
            var maxValue = Math.ceil(Math.max(...screeningData, ...adoptionData) / 100) * 100;
            var yAxisInterval = Math.ceil(maxValue / 5);

            myChart.setOption({{
                title: {{ text: 'Unique Farmers in Screening and Adoption by Year', top: '3%', left: '1%' }},
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross', label: {{ backgroundColor: '#6a7985' }} }} }},
                legend: {{ data: ['Screening', 'Adoption'], x: 'right', left: '80%', top: '3%' }},
                grid: {{ left: '5%', right: '5%', bottom: '10%', containLabel: true }},
                xAxis: {{ type: 'category', data: yearNames, name: 'Year', nameLocation: 'center', nameGap: 30 }},
                yAxis: {{ type: 'value', max: maxValue, interval: yAxisInterval, name: 'Number', nameLocation: 'center', nameGap: 60 }},
                series: [
                    {{ name: 'Screening', type: 'line', areaStyle: {{}}, emphasis: {{ focus: 'series' }}, data: screeningData }},
                    {{ name: 'Adoption', type: 'line', areaStyle: {{}}, emphasis: {{ focus: 'series' }}, data: adoptionData }}
                ]
            }});

            window.addEventListener('resize', function() {{ myChart.resize(); }});
        </script>
        """
        st.components.v1.html(html_content, height=400)
    
if __name__ == "__main__":
    main()