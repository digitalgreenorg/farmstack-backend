
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

# st.header("Telegram BOT Dashboard")

query = """
WITH telegram_data AS (
    SELECT 
        details->'data'->'advisory_body'->>'value_chain' AS value_chain_id,
        details->'data'->'advisory_body'->>'sub_practice' AS sub_practice_id,
        COUNT(*) AS count
    FROM 
        core_telegraminteractionlog
    WHERE 
        action = 'ADVISORY_ACCESS_DA'
    GROUP BY 
        details->'data'->'advisory_body'->>'value_chain',
        details->'data'->'advisory_body'->>'sub_practice'
)
SELECT 
    da.id AS da_id, 
    da.name AS da_name,
    da.gender AS da_gender, 
    k.id AS kebele_id, 
    k.name AS kebele_name, 
    w.name AS woreda_name, 
    z.name AS zone_name, 
    rg.name AS region_name, 
    w.id AS woreda_id, 
    z.id AS zone_id, 
    rg.id AS region_id, 
    ofp.gender AS gender, 
    p.id AS practice_id, 
    a.id AS advisory_id, 
    r.id AS reach_id, 
    ofp.id AS farmer_id,
    a.label AS advisory_label,   
    p.name AS practice_name,
    s.name As subpractice_name,
    s.id AS subpractice_id,
    ad.id AS adoption_id,
    r.created_at AS created_at, 
    vc.id AS value_chain_id, 
    vc.name AS value_chain_name, 
    vcc.id AS value_chain_category_id, 
    vcc.name AS value_chain_category_name,
    tg.count AS access_count
FROM 
    integration_developmentagent da
INNER JOIN 
    integration_kebele k ON k.id = da.kebele_id
INNER JOIN 
    integration_woreda w ON w.id = k.woreda_id
INNER JOIN 
    integration_zone z ON z.id = w.zone_id
INNER JOIN 
    integration_region rg ON rg.id = z.region_id
INNER JOIN 
    core_outboundfarmerprofile ofp ON ofp.kebele_id = k.id
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
LEFT JOIN 
    telegram_data tg ON tg.value_chain_id::uuid = vc.id AND tg.sub_practice_id::uuid = s.id

"""

@st.cache_data
def cached_data(query):
    return fetch_data(query)


df = cached_data(query)
df['created_at'] = pd.to_datetime(df['created_at'])



df['created_at'] = pd.to_datetime(df['created_at'])
counts = st.selectbox('Select the number of top items to display:', ['Top 3', 'Top 5', 'Top 10'])

period = st.selectbox("Select period:", ["Past Week", "Past Month", "Past 3 Months", "Past 6 Months", "Past Year"])
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

# st.write(start_date)

import pytz

# Convert start_date to UTC timestamp
start_date_utc = pd.Timestamp(start_date, tz='UTC')

# Convert today's date to UTC timestamp
today_utc = pd.Timestamp(today, tz='UTC')

# Filter the DataFrame based on the UTC timestamps
filtered_df = df.copy() 
filtered_df = filtered_df[(filtered_df['created_at'] >= start_date_utc) & (filtered_df['created_at'] <= today_utc)]

# st.write(filtered_df)

n_top = int(counts.split()[1])
# st.write(n_top)
# FEMALE CHAMPION DA
female_das = filtered_df[filtered_df['da_gender'].str.lower() == 'female']
female_da_reach_count = female_das.groupby(['da_name', 'woreda_name']).apply(lambda x: pd.Series({
    'male_reach_count': x[x['gender'].str.lower() == 'male']['reach_id'].nunique(),
    'female_reach_count': x[x['gender'].str.lower() == 'female']['reach_id'].nunique()
})).reset_index()

female_da_reach_count['total_reach_count'] = female_da_reach_count['male_reach_count'] + female_da_reach_count['female_reach_count']
top_3_female_das = female_da_reach_count.sort_values(by='total_reach_count', ascending=False).head(n_top)
st.write("FEMALE CHAMPION DA: Top 3 Female DAs with the highest number of farmer reach")
st.dataframe(top_3_female_das)

############################

# FEMALE FARMER ADVOCATES
female_farmer_reach = filtered_df[filtered_df['gender'].str.lower() == 'female']
female_farmer_reach_count = female_farmer_reach.groupby([ 'da_name', 'woreda_name']).apply(lambda x: pd.Series({
    'female_reach_count': x[x['gender'].str.lower() == 'female']['reach_id'].nunique()
})).reset_index()

top_3_female_advocates = female_farmer_reach_count.sort_values(by='female_reach_count', ascending=False).head(n_top)
st.write("FEMALE FARMER ADVOCATES: Top 3 DAs with the highest number of female reach")
st.dataframe(top_3_female_advocates)
######################################################
female_das = filtered_df[filtered_df['da_gender'].str.lower() == 'female']
female_da_adoption_count = female_das.groupby([ 'da_name', 'woreda_name']).apply(lambda x: pd.Series({
    'male_adoption_count': x[x['gender'].str.lower() == 'male']['adoption_id'].nunique(),
    'female_adoption_count': x[x['gender'].str.lower() == 'female']['adoption_id'].nunique()
})).reset_index()

female_da_adoption_count['total_adoption_count'] = female_da_adoption_count['male_adoption_count'] + female_da_adoption_count['female_adoption_count']
top_3_adoption_female_das = female_da_adoption_count.sort_values(by='total_adoption_count', ascending=False).head(n_top)
st.write("FEMALE CHAMPION DA: Top 3 Female DAs with the highest number of farmer adoption")
st.dataframe(top_3_adoption_female_das)
######################################################
female_da_female_adoption_count = female_das.groupby([ 'da_name', 'woreda_name']).apply(lambda x: pd.Series({
    'female_adoption_count': x[x['gender'].str.lower() == 'female']['adoption_id'].nunique()
})).reset_index()

top_3_advocates = female_da_female_adoption_count.sort_values(by='female_adoption_count', ascending=False).head(n_top)
st.write("FEMALE FARMER ADVOCATES: Top 3 Female DAs with the highest number of farmer adoption")
st.dataframe(top_3_advocates)

#############################
reach_count_sau = filtered_df.groupby(['kebele_id', 'kebele_name']).apply(lambda x: pd.Series({
    'male_reach_count': x[x['gender'].str.lower() == 'male']['reach_id'].nunique(),
    'female_reach_count': x[x['gender'].str.lower() == 'female']['reach_id'].nunique()
})).reset_index()
reach_count_sau['total_reach_count'] = reach_count_sau['male_reach_count'] + reach_count_sau['female_reach_count']
top_3_sau = reach_count_sau.sort_values(by='total_reach_count', ascending=False).head(n_top)
# st.write("SAU------->")
st.dataframe(top_3_sau)
###############################
reach_count_sau_female_only = filtered_df.groupby(['kebele_id', 'kebele_name']).apply(lambda x: pd.Series({
    'female_reach_count': x[x['gender'].str.lower() == 'female']['reach_id'].nunique()
})).reset_index()
reach_count_sau_female_only['female_reach_count'] = reach_count_sau_female_only['female_reach_count'] 
top_3_sau_advocates= reach_count_sau_female_only.sort_values(by='female_reach_count', ascending=False).head(n_top)
# st.write("SAU advocates------->")
st.dataframe(top_3_sau_advocates)
################################

practice_reach_count = filtered_df.groupby(['value_chain_name', 'practice_name']).apply(lambda x: pd.Series({
    'male_reach_count': x[x['gender'].str.lower() == 'male']['reach_id'].nunique(),
    'female_reach_count': x[x['gender'].str.lower() == 'female']['reach_id'].nunique()
})).reset_index()

practice_reach_count['total_reach_count'] = practice_reach_count['male_reach_count'] + practice_reach_count['female_reach_count']

# Top 3 practices with the highest total reach count
top_3_practices = practice_reach_count.sort_values(by='total_reach_count', ascending=False).head(n_top)

# Display the result
st.write("High Farmer Reach Practices: Top 3 Practices with the highest reach count")
st.dataframe(top_3_practices[['value_chain_name', 'practice_name', 'male_reach_count', 'female_reach_count', 'total_reach_count']])

################################

practice_adoption_count = filtered_df.groupby(['value_chain_name', 'practice_name']).apply(lambda x: pd.Series({
    'male_adoption_count': x[x['gender'].str.lower() == 'male']['adoption_id'].nunique(),
    'female_adoption_count': x[x['gender'].str.lower() == 'female']['adoption_id'].nunique()
})).reset_index()

practice_adoption_count['total_adoption_count'] = practice_adoption_count['male_adoption_count'] + practice_adoption_count['female_adoption_count']

# Top 3 practices with the highest total adoption count
top_3_practices = practice_adoption_count.sort_values(by='total_adoption_count', ascending=False).head(n_top)

# Display the result
st.write("High Farmer Reach Practices: Top 3 Practices with the highest adoption count")
st.dataframe(top_3_practices[['value_chain_name', 'practice_name', 'male_adoption_count', 'female_adoption_count', 'total_adoption_count']])


# Sort the DataFrame by access count in descending order
sorted_df = filtered_df.sort_values(by='access_count', ascending=False)

# Select the top 10 rows
top_10_access_counts = sorted_df[['value_chain_name', 'practice_name', 'access_count']]
top_10_unique_access_counts = top_10_access_counts.drop_duplicates(subset=['value_chain_name', 'practice_name']).head(n_top)

# Display the DataFrame with unique combinations
st.write(top_10_unique_access_counts)





