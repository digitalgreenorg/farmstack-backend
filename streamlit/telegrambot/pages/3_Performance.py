
import math
import psycopg2
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
st.set_page_config(
        layout="wide",
        initial_sidebar_state="auto",
        page_title="Telegram BOT Dashboard",
        page_icon=None,
    )
st.header('Performance')
# tab1, tab2, tab3 = st.tabs(["Administrative unit performance","DA performance(Woreda level only)","Value chain reports"])


def connect_to_database():
    """Connect to the PostgreSQL database."""
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )

    return conn

def fetch_data(query):
    """Fetch data from the database and return as a DataFrame."""
    conn = connect_to_database()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


queries={
    "query_1":"""
    SELECT 
        da.details->'data'->>'da' AS da_id,
        da.details->'data'->'advisory_body'->'location'->>'id' AS location_id,
        da.details->'data'->'advisory_body'->'location'->>'name' AS location_level,
        da.created_at as created_at,
        ofp.gender AS gender, 
        dev.id AS dev_id,
        dev.name AS da_name,
        keb.id AS kebele_id,
        keb.name AS kebele_name,
        wor.name AS woreda_name,
        wor.id AS woreda_id,
        zon.name AS zone_name,
        zon.id AS zone_id,
        reg.name AS region_name,
        reg.id AS region_id,
        vc.id AS value_chain_id, 
        vc.name AS value_chain_name, 
        vcc.id AS value_chain_category_id, 
        vcc.name AS value_chain_category_name,
        p.name AS practice_name,
        p.id AS practice_id,
        r.id AS reach_id,
        ad.id AS adoption_id

    FROM 
        core_telegraminteractionlog AS da
    JOIN 
        integration_developmentagent AS dev
    ON 
        da.details->'data'->>'da' = dev.id::text
    INNER JOIN 
        integration_kebele AS keb
    ON 
        dev.kebele_id = keb.id
    INNER JOIN 
        integration_woreda AS wor
    ON 
        keb.woreda_id = wor.id
    INNER JOIN 
        integration_zone AS zon
    ON 
        wor.zone_id = zon.id
    INNER JOIN 
        integration_region AS reg
    ON 
        zon.region_id = reg.id
    INNER JOIN 
    core_outboundfarmerprofile ofp ON ofp.kebele_id = keb.id
	INNER JOIN 
	    core_reach r ON r.farmer_id = ofp.id
	INNER JOIN 
	    core_advisory a ON r.advisory_id = a.id
	INNER JOIN 
	    core_valuechain vc ON a.value_chain_id = vc.id
	INNER JOIN 
	    core_valuechaincategory vcc ON vc.category_id = vcc.id
	INNER JOIN 
	    core_subpractice s ON a.sub_practice_id = s.id
	INNER JOIN 
	    core_practice p ON s.practice_id = p.id
	LEFT JOIN 
	    core_adoption ad ON ad.farmer_id = ofp.id AND ad.advisory_id = r.advisory_id

    WHERE 
        da.action = 'ADVISORY_ACCESS_DA';
""",
"query_2":"""
    SELECT 
        da.details->'data'->>'da' AS da_id,
        da.details->'data'->'advisory_body'->'location'->>'id' AS location_id,
        da.details->'data'->'advisory_body'->'location'->>'name' AS location_level,
        da.created_at as created_at,
        ofp.gender AS gender, 
        dev.id AS dev_id,
        dev.first_name AS da_name,
        keb.id AS kebele_id,
        keb.name AS kebele_name,
        wor.name AS woreda_name,
        wor.id AS woreda_id,
        zon.name AS zone_name,
        zon.id AS zone_id,
        reg.name AS region_name,
        reg.id AS region_id,
        vc.id AS value_chain_id, 
        vc.name AS value_chain_name, 
        vcc.id AS value_chain_category_id, 
        vcc.name AS value_chain_category_name,
        p.name AS practice_name,
        p.id AS practice_id,
        r.id AS reach_id,
        ad.id AS adoption_id

    FROM 
        core_telegraminteractionlog AS da
    JOIN 
        core_outbounddaprofile AS dev
    ON 
        da.details->'data'->>'da' = dev.id::text
    INNER JOIN 
        integration_kebele AS keb
    ON 
        dev.kebele_id = keb.id
    INNER JOIN 
        integration_woreda AS wor
    ON 
        keb.woreda_id = wor.id
    INNER JOIN 
        integration_zone AS zon
    ON 
        wor.zone_id = zon.id
    INNER JOIN 
        integration_region AS reg
    ON 
        zon.region_id = reg.id
    INNER JOIN 
        core_outboundfarmerprofile ofp ON ofp.kebele_id = keb.id
	INNER JOIN 
	    core_reach r ON r.farmer_id = ofp.id
	INNER JOIN 
	    core_advisory a ON r.advisory_id = a.id
	INNER JOIN 
	    core_valuechain vc ON a.value_chain_id = vc.id
	INNER JOIN 
	    core_valuechaincategory vcc ON vc.category_id = vcc.id
	INNER JOIN 
	    core_subpractice s ON a.sub_practice_id = s.id
	INNER JOIN 
	    core_practice p ON s.practice_id = p.id
	LEFT JOIN 
	    core_adoption ad ON ad.farmer_id = ofp.id AND ad.advisory_id = r.advisory_id

    WHERE 
        da.action = 'ADVISORY_ACCESS_DA'
"""
}

@st.cache_data
def cached_data(query):
    return fetch_data(query)
query_one_output = cached_data(queries["query_1"])
query_two_output = cached_data(queries["query_2"])


concatenated_output = pd.concat([query_one_output, query_two_output], ignore_index=True)
concatenated_output=concatenated_output.reset_index(drop=True)

######################################

# min_created_at = df['created_at'].min()
# max_created_at = df['created_at'].max()

## Kebeles
unique_kebele=concatenated_output.groupby(['woreda_id','kebele_id', 'kebele_name']).size().reset_index(name='count')
unique_kebele = unique_kebele.drop(columns=['count'])
kebele_list = unique_kebele.to_dict(orient='records')

## DAs
unique_da=concatenated_output.groupby(['da_id', 'da_name']).size().reset_index(name='count')
unique_da = unique_da.drop(columns=['count'])
# st.write(len(unique_da))
da_list = unique_da.to_dict(orient='records')

## Practice
unique_practice=concatenated_output.groupby(['practice_id', 'practice_name']).size().reset_index(name='count')
unique_practice = unique_practice.drop(columns=['count'])
# st.write(len(unique_practice))
practice_list = unique_practice.to_dict(orient='records')

#unique value chain
unique_value_chain=concatenated_output.groupby(['value_chain_id', 'value_chain_name']).size().reset_index(name='count')
unique_value_chain = unique_value_chain.drop(columns=['count'])
# st.write(len(unique_value_chain))
value_chain_list = unique_value_chain.to_dict(orient='records')

#unique value chain category 
unique_value_chain_category=concatenated_output.groupby(['value_chain_category_id', 'value_chain_category_name']).size().reset_index(name='count')
unique_value_chain_category = unique_value_chain_category.drop(columns=['count'])
# st.write(len(unique_value_chain_category))
unique_value_chain_category_list = unique_value_chain_category.to_dict(orient='records')

placeholders = {
    "Region": "Select Region",
    "Zone": "Select Zone",
    "Woreda": "Select Woreda",
    "Kebele": "Select Kebele",
    "DA": "Select DA",
    "Advisory": "Select Advisory",
    "Practice": "Select Practice",
    "Value Chain":"Select Value Chain",
    "Value Chain Category":"Select Value Chain Category"
}

filters = {
    "Kebele": kebele_list,
    "DA": da_list,
    "Practice": practice_list
}


# selected_kebele = st.selectbox("Select Kebele", options=[placeholders["Kebele"]] + [kebele['kebele_name'] for kebele in filters['Kebele']])
def select_period(index):
    period = st.selectbox("Select period:", ["Past Week", "Past Month", "Past 3 Months", "Past 6 Months", "Past Year"],key=f"period_{index}")
    today = datetime.date.today()

    if period == "Past Week":
        start_date = today - datetime.timedelta(days=7)
    elif period == "Past Month":
        start_date = today - datetime.timedelta(days=30)
    elif period == "Past 3 Months":
        start_date = today - datetime.timedelta(days=90)
    elif period == "Past 6 Months":
        start_date = today - datetime.timedelta(days=180)
    elif period == "Past Year":
        start_date = today - datetime.timedelta(days=365)

    return start_date

col1,col2,col3,col4,col5,col6=st.columns(6)
kebele_da_mapping = concatenated_output.groupby(['kebele_id'])[['da_id', 'da_name']].apply(lambda x: x.drop_duplicates().to_dict(orient='records')).to_dict()
kebele_practice_mapping = concatenated_output.groupby(['kebele_id'])[['practice_id', 'practice_name']].apply(lambda x: x.drop_duplicates().to_dict(orient='records')).to_dict()
kebele_value_chain_mapping=concatenated_output.groupby(['kebele_id'])[['value_chain_id', 'value_chain_name']].apply(lambda x: x.drop_duplicates().to_dict(orient='records')).to_dict()
kebele_value_chain_category_mapping=concatenated_output.groupby(['kebele_id'])[['value_chain_category_id', 'value_chain_category_name']].apply(lambda x: x.drop_duplicates().to_dict(orient='records')).to_dict()
tab1, tab2, tab3 = st.tabs(["Administrative unit performance","DA performance(Woreda level only)","Value chain reports"])
with col1:
    selected_kebele = st.selectbox('Select a Kebele', ['All'] + [kebele['kebele_name'] for kebele in kebele_list])

# Filter DAs based on the selected kebele
if selected_kebele == 'All':
    filtered_da_list = da_list
    filtered_practice_list=practice_list
    filtered_value_chain_list=value_chain_list
    filtered_value_chain_category_list=unique_value_chain_category_list
else:
    selected_kebele_id = [kebele['kebele_id'] for kebele in kebele_list if kebele['kebele_name'] == selected_kebele][0]
    filtered_da_list = kebele_da_mapping.get(selected_kebele_id, [])
    filtered_practice_list=kebele_practice_mapping.get(selected_kebele_id,[])
    filtered_value_chain_list=kebele_value_chain_mapping.get(selected_kebele_id,[])
    filtered_value_chain_category_list=kebele_value_chain_category_mapping.get(selected_kebele_id,[])

    # st.write(f"DAs in the selected kebele '{selected_kebele}':", len(filtered_da_list))

filters = {
    "Kebele": kebele_list,
    "DA": filtered_da_list,
    "Practice": filtered_practice_list,
    "Value Chain":filtered_value_chain_list,
    "Value Chain Category":filtered_value_chain_category_list
}
with col2:
    selected_da = st.selectbox("Select DA", options=[placeholders["DA"]] + [da['da_name'] for da in filters['DA']])
with col3:
    selected_practice = st.selectbox("Select Practice", options=[placeholders["Practice"]] + [practice['practice_name'] for practice in filters['Practice']])
with col4:
    selected_value_chain = st.selectbox("Select Value Chain", options=[placeholders["Value Chain"]] + [valuechain['value_chain_name'] for valuechain in filters['Value Chain']])
with col5:
    selected_value_chain_category = st.selectbox("Select Category", options=[placeholders["Value Chain Category"]] + [valuechaincat['value_chain_category_name'] for valuechaincat in filters['Value Chain Category']])
with col6:
    select_period(1)



with tab1:
    
    distinct_das_df = concatenated_output.drop_duplicates(subset="da_id")


    grouped_output = concatenated_output.groupby(
        ["kebele_id", "kebele_name", 
        "practice_id", "practice_name", 
        "value_chain_id", "value_chain_name", 
        "value_chain_category_id", "value_chain_category_name"
    ]
    ).agg(
        distinct_das=("da_id", "nunique"),
        access_count=("da_id", "count")
    ).reset_index()


    # column_to_show=['DA Name','Kebele Name','Woreda Name','Practice','Value Chain Category','Value Chain']
    column_to_show=['kebele_name','value_chain_category_name','value_chain_name','practice_name','distinct_das','access_count']
    st.subheader('Advisory Access')
    st.dataframe(grouped_output[column_to_show])



    st.subheader("Advisory Access Graph")
    # column_to_show=['kebele_name','access_count','created_at']
    # df = pd.DataFrame(grouped_output[column_to_show])

    # start_date = select_period(1)
    # df['created_at'] = pd.to_datetime(df['created_at'])
    # filtered_df = df[df['created_at'] >= pd.to_datetime(start_date)]

    # # Select top 5 kebeles based on access count within the filtered period
    # top_kebeles = filtered_df.groupby('kebele_name')['access_count'].sum().nlargest(5).index
    # filtered_df = filtered_df[filtered_df['kebele_name'].isin(top_kebeles)]

    # # Create the Plotly line chart
    # fig = px.line(filtered_df, x='created_at', y='access_count', color='kebele_name', title='Access Count per Kebele', markers=True)

    # # Display the chart in Streamlit
    # st.plotly_chart(fig)

    ###########
    print("col------>",concatenated_output.columns)
    def reach_counts(df):
        male_reach_count = df[df['gender'].str.lower() == 'male']['reach_id'].nunique()
        female_reach_count = df[df['gender'].str.lower() == 'female']['reach_id'].nunique()
        return pd.Series({
            'male_reach_count': male_reach_count,
            'female_reach_count': female_reach_count
        })

    # Group by kebele, practice, value chain, and category, and apply the custom aggregation function
    grouped_reach_data = concatenated_output.groupby(
        ["kebele_id", "kebele_name", 
        "practice_id", "practice_name", 
        "value_chain_id", "value_chain_name", 
        "value_chain_category_id", "value_chain_category_name"]
    ).apply(reach_counts).reset_index()

    print("dataframe----->",grouped_reach_data)
    st.subheader("Reach Recorded")
    st.dataframe(grouped_reach_data)
#####Graph



    def adoption_counts(df):
        male_adoption_count = df[df['gender'].str.lower() == 'male']['adoption_id'].nunique()
        female_adoption_count = df[df['gender'].str.lower() == 'female']['adoption_id'].nunique()
        return pd.Series({
            'male_adoption_count': male_adoption_count,
            'female_adoption_count': female_adoption_count
        })

    # Group by kebele, practice, value chain, and category, and apply the custom aggregation function
    grouped_adoption_data = concatenated_output.groupby(
        ["kebele_id", "kebele_name", 
        "practice_id", "practice_name", 
        "value_chain_id", "value_chain_name", 
        "value_chain_category_id", "value_chain_category_name"]
    ).apply(adoption_counts).reset_index()

    print("grouped_adoption_data----->",grouped_adoption_data)
    st.subheader("Adoption Recorded")
    st.dataframe(grouped_adoption_data)

####Graph

    # grouped_reach_data=grouped_reach_data.fillna(0, inplace=True)
    df_top5 = grouped_reach_data.head(5)
    fig = px.bar(
        df_top5,
        x='kebele_name',
        y=['male_reach_count', 'female_reach_count'],
        title='Reach Recorded Tab1',
        # labels={'value': 'Reach Count', 'variable': 'Gender'},
        barmode='group',
        # color_discrete_map=color_discrete_map
    )



    # Customize the layout
    fig.update_layout(
        xaxis_title='Kebele Name',
        yaxis_title='Reach Count',
        legend_title='Gender',
        legend=dict(
            x=1.0,
            y=1.0
        )
    )

    # Display the chart in Streamlit
    st.plotly_chart(fig)

    df_top5 = grouped_adoption_data.head(10)
    fig = px.bar(
        df_top5,
        x='kebele_name',
        y=['male_adoption_count', 'female_adoption_count'],
        title='Adoption Recorded Tab1',
        # labels={'value': 'Reach Count', 'variable': 'Gender'},
        barmode='group',
        # color_discrete_map=color_discrete_map
    )



    # Customize the layout
    fig.update_layout(
        xaxis_title='Kebele Name',
        yaxis_title='Adoption Count',
        legend_title='Gender',
        legend=dict(
            x=1.0,
            y=1.0
        )
    )

    # Display the chart in Streamlit
    st.plotly_chart(fig)

#######################



# tab 2
with tab2:
    def gender_counts(df):
        male_reach_count = df[df['gender'].str.lower() == 'male']['reach_id'].nunique()
        female_reach_count = df[df['gender'].str.lower() == 'female']['reach_id'].nunique()
        male_adoption_count = df[df['gender'].str.lower() == 'male']['adoption_id'].nunique()
        female_adoption_count = df[df['gender'].str.lower() == 'female']['adoption_id'].nunique()
        access_count = df['da_id'].count()
        return pd.Series({
            'male_reach_count': male_reach_count,
            'female_reach_count': female_reach_count,
            'male_adoption_count': male_adoption_count,
            'female_adoption_count': female_adoption_count,
            'access_count': access_count
        })

    grouped_data = concatenated_output.groupby(['da_name', 'kebele_name']).apply(gender_counts).reset_index()

    # Display the result
    import streamlit as st
    st.subheader("da performance")
    print("grouped_data------>",grouped_data)
    st.dataframe(grouped_data)

    df_top5 = grouped_data.head(5)

    # Create a stacked bar chart using Plotly

    color_discrete_map = {
        'male_reach_count': '#34AF16',
        'female_reach_count': '#1F3BB3',
        'male_adoption_count': '#80D7D9',
        'female_adoption_count': '#A155B9',
        'access_count':'#FF6BF9'
    }
    fig = px.bar(
        df_top5,
        x='kebele_name',
        y=['male_reach_count', 'female_reach_count','male_adoption_count','female_adoption_count','access_count'],
        title='Reach Counts by Kebele and Gender (Top 5)',
        # labels={'value': 'Reach Count', 'variable': 'Gender'},
        barmode='group',
        color_discrete_map=color_discrete_map
    )



    # Customize the layout
    fig.update_layout(
        xaxis_title='Kebele Name',
        yaxis_title='Reach Count',
        legend_title='Gender',
        legend=dict(
            x=1.0,
            y=1.0
        )
    )

    # Display the chart in Streamlit
    st.plotly_chart(fig)


# tab 3
with tab3:

    value_chain_report_reach_data = concatenated_output.groupby(['kebele_name', 'region_name', 'zone_name', 'woreda_name', 'practice_name']).apply(
        lambda x: pd.Series({
            'male_reach_count': x[x['gender'].str.lower() == 'male']['reach_id'].nunique(),
            'female_reach_count': x[x['gender'].str.lower() == 'female']['reach_id'].nunique()
        })
    ).reset_index()

    # Display the grouped data (for verification)
    st.subheader("Reach Count in Value Chain")
    st.dataframe(value_chain_report_reach_data)


    value_chain_report_adoption_data = concatenated_output.groupby(['kebele_name', 'region_name', 'zone_name', 'woreda_name', 'practice_name']).apply(
        lambda x: pd.Series({
            'male_adoption_count': x[x['gender'].str.lower() == 'male']['adoption_id'].nunique(),
            'female_adoption_count': x[x['gender'].str.lower() == 'female']['adoption_id'].nunique()
        })
    ).reset_index()

    # Display the grouped data (for verification)
    st.subheader("Adoption Count in Value Chain")
    st.dataframe(value_chain_report_adoption_data)


    st.subheader("chart for reach")


    df_top5 = value_chain_report_reach_data.head(8)
    fig = px.bar(
        df_top5,
        x='kebele_name',
        y=['male_reach_count', 'female_reach_count'],
        title='Reach Counts by Kebele and Gender (Top 5)',
        # labels={'value': 'Reach Count', 'variable': 'Gender'},
        barmode='group',
        color_discrete_map=color_discrete_map
    )



    # Customize the layout
    fig.update_layout(
        xaxis_title='Kebele Name',
        yaxis_title='Reach Count',
        legend_title='Gender',
        legend=dict(
            x=1.0,
            y=1.0
        )
    )

    # Display the chart in Streamlit
    st.plotly_chart(fig)

    ###################################################
    df_top5 = value_chain_report_adoption_data.head(8)
    fig = px.bar(
        df_top5,
        x='kebele_name',
        y=['male_adoption_count', 'female_adoption_count'],
        title='Adoption Counts by Kebele and Gender (Top 5)',
        # labels={'value': 'Reach Count', 'variable': 'Gender'},
        barmode='group',
        color_discrete_map=color_discrete_map
    )



    # Customize the layout
    fig.update_layout(
        xaxis_title='Kebele Name',
        yaxis_title='Adoption Count',
        legend_title='Gender',
        legend=dict(
            x=1.0,
            y=1.0
        )
    )

    # Display the chart in Streamlit
    st.plotly_chart(fig)