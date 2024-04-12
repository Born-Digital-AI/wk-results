import streamlit as st
import psycopg2
import pandas as pd
import datetime
import plotly.express as px
import yaml
import streamlit_authenticator as stauth
import os

from yaml.loader import SafeLoader

with open('auth.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

st.set_page_config(page_title="Digital Lawyer Data", page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
)

authenticator.login()

# Connect to the PostgreSQL database
def get_connection():
    conn = psycopg2.connect(host=os.environ.get('DATABASE_HOST'), 
                            database=os.environ.get('DATABASE_NAME'), 
                            user=os.environ.get('DATABASE_USER'), 
                            password=os.environ.get('DATABASE_PASSWORD')
                            )
    return conn
 

def fetch_data(email_filter, date_from, date_to):
    conn = get_connection()
    query = """
    SELECT i.created_at, i.input, i.output, i.token_count, i.total_cost_usd, i.email, e.stars, e.text, i.id
    FROM wk_interaction i
    LEFT JOIN wk_evaluation e ON i.id = e.interaction_id
    WHERE i.email LIKE %s AND
          i.created_at BETWEEN %s AND %s
    """
    with conn.cursor() as cur:
        # Use placeholders and parameters to prevent SQL injection
        cur.execute(query, ('%' + email_filter + '%', date_from, date_to))
        data = cur.fetchall()
    conn.close()
    return data

# Streamlit app
def main():
    st.title("Digital Lawyer - Data Visualization of User Interactions and Evaluations")

    # Add filters
    st.sidebar.header("Filters")
    email_filter = st.sidebar.text_input("Email", "")
    date_from = st.sidebar.date_input("From Date", value=datetime.date(2024, 1, 1))
    date_to = st.sidebar.date_input("To Date", value=pd.to_datetime("today"))

    # Fetch data from the database
    data = fetch_data(email_filter, date_from, date_to)

    # Convert the data to a pandas DataFrame and reorder columns
    columns = ["created_at", "input", "output", "token_count", "total_cost_usd", "email", "stars", "text", "id"]
    df = pd.DataFrame(data, columns=columns)

    # Sort the DataFrame by 'created_at' in descending order
    df = df.sort_values(by='created_at', ascending=False)    

    # Extract emails for the multiselect after fetching the data
    available_emails = df['email'].unique().tolist()
    excluded_emails = st.sidebar.multiselect(
        "Exclude Emails",
        options=available_emails,
        default=[]
    )

    # Apply email exclusion filter to the dataframe
    if excluded_emails:
        df = df[~df['email'].isin(excluded_emails)]

    col1, col2 = st.columns(2)
    with col1:
        # Pie chart visualization for top 10 emails
        if not df.empty:
            email_counts = df['email'].value_counts().nlargest(10)
            top_emails = df[df['email'].isin(email_counts.index)]
            fig = px.pie(top_emails, names='email', title='Top 10 Emails by Record Count')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No data available for the selected filters to display the pie chart.")
    with col2:
        # Bar chart for evaluation stars
        if not df.empty and 'stars' in df.columns:
            star_counts = df['stars'].value_counts().reindex(range(6), fill_value=0)
            fig_stars = px.bar(star_counts, x=star_counts.index, y=star_counts.values, labels={'x': 'Stars', 'y': 'Count'}, title='Distribution of Evaluation Stars')
            fig_stars.update_layout(xaxis_type='category')
            st.plotly_chart(fig_stars, use_container_width=True)
        else:
            st.write("No evaluations available to display the bar chart.")

    interaction_count = len(df)  # Count the number of rows in the DataFrame
    st.subheader(f"Interaction and Evaluation Details - {interaction_count} Interactions")  # Display count in the subheader
    st.dataframe(df, height=600)


if st.session_state["authentication_status"]:
    st.write(f'Welcome *{st.session_state["name"]}*')
    main()
    authenticator.logout()
elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')