from langchain.chains.question_answering import load_qa_chain
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
import google.generativeai as genai
import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error 
from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))




def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database="job_database"  # Specify your database name here
    )
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS  job_details(
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_name VARCHAR(255),
            job_title VARCHAR(255),
            job_description TEXT, 
            sentiment_analysis TEXT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

initialize_database()


# Ensure the environment variable is loaded correctly
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ API key is not set. Please check your environment variables.")

def save_job_details(company_name, job_title, job_description, sentiment_analysis):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO job_details (company_name, job_title, job_description, sentiment_analysis)
            VALUES (%s, %s, %s, %s)
        """, (company_name, job_title, job_description, sentiment_analysis))
        conn.commit()
    except mysql.connector.Error as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

def load_data(filepath):
    return pd.read_csv(filepath)
data= load_data("REVIEWS.csv")

# Set up the conversational chain
def get_company_data(company_name, data):
    company_data = data[data['Company'].str.lower() == company_name.lower()]
    return company_data

def generate_response(company_data):
    if company_data.empty:
        return "Company not found."

    company_name = company_data['Company'].values[0]
    rating = company_data['Rating'].values[0]
    avg_salary = company_data['Salaries'].values[0]
    total_employees = company_data['Company_Size'].values[0]


    # Sentiment Analysis
    if rating > 4:
        sentiment = "Exeptional"
    elif 3.5< rating <= 4:
        sentiment = "Positive"
    elif 3 <= rating <3.4:
        sentiment = "Neutral"
    else:
        sentiment = "Negative"

    # Structured Response
    response = (f"**{company_name}** has a rating of {rating}, indicating a {sentiment} sentiment. "
                f"The average salary at {company_name} is ${avg_salary}, "
                f"and the company employs around {total_employees} individuals.")

    return response, sentiment
st.title("Welcome to AI HR Solution")

# User input for company name
company_name = st.text_input("Enter the company name:")
job_title = st.text_input("Enter Job Title")
job_description = st.text_area("Enter job description")
submit = st.button("Submit")

if submit:
    if company_name and job_title and job_description:
        company_data = get_company_data(company_name, data)
        response, sentiment = generate_response(company_data)
        if response:
            # st.markdown(response)
            input_prompt = f"""You are supposed to be an analyzer of company reviews of thier employees. Your task is to generate responses on provided sentiments to show other applicants applying in this company.
            Dont't build up positive, negative and neutral sentiments just show what data told you!. I want you to also told applicant what data says. Your sentiment should be a one paragraph
            Response:
            {sentiment}
            """
            response1 = genai.GenerativeModel('gemini-pro').generate_content(input_prompt).text
            st.markdown(response1)
            save_job_details(company_name, job_title, job_description, response1)
            st.success("Job details saved successfully!")
