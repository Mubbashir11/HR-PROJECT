from flask import Flask, render_template, request
import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()

# Configure Google Generative AI and Langchain Groq
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize ChatGroq with the correct method (assuming you configure the API key elsewhere)
chat_groq_model = ChatGroq(model_name="llama3-8b-8192")

app = Flask(__name__)

# MySQL connection setup
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database="job_database"
    )

def get_resume_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_db"
    )

# Initialize the database
def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_details(
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

# Save job details to the database
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

# Load CSV data
def load_data(filepath):
    return pd.read_csv(filepath)

data = load_data("REVIEWS.csv")

# Get company data from CSV
def get_company_data(company_name, data):
    company_data = data[data['Company'].str.lower() == company_name.lower()]
    return company_data

# Generate response based on company data
def generate_response(company_data):
    if company_data.empty:
        return "Company not found.", None

    company_name = company_data['Company'].values[0]
    rating = company_data['Rating'].values[0]
    avg_salary = company_data['Salaries'].values[0]
    total_employees = company_data['Company_Size'].values[0]

    # Sentiment Analysis
    if rating > 4:
        sentiment = "Exceptional"
    elif 3.5 < rating <= 4:
        sentiment = "Positive"
    elif 3 <= rating < 3.4:
        sentiment = "Neutral"
    else:
        sentiment = "Negative"

    response = (f"**{company_name}** has a rating of {rating}, indicating a {sentiment} sentiment. "
                f"The average salary at {company_name} is ${avg_salary}, "
                f"and the company employs around {total_employees} individuals.")

    return response, sentiment

# Fetch top candidates using RAG (LLM to analyze and rank candidates)
def fetch_top_candidates_using_rag(job_description):
    conn = get_resume_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch all candidate data from the database
        query = """
        SELECT name, email, skills, experience_years, retention_rate
        FROM candidates
        """
        cursor.execute(query)
        candidates = cursor.fetchall()

        # Format the candidate data into a readable form for the LLM
        formatted_candidates = ""
        for candidate in candidates:
            formatted_candidates += f"Name: {candidate['name']}, Skills: {candidate['skills']}, Experience: {candidate['experience_years']} years, Retention Rate: {candidate['retention_rate']}\n"

        # Use LLM (Langchain with ChatGroq) to rank and summarize the top 5 candidates based on job description
        input_prompt = """
        You are a recruitment AI assistant and you have knowledge of all technical domains. Based on the following job description:

        {job_description}

        Here is the data of the candidates in the database:

        {formatted_candidates}

        Please select the top 5 most relevant candidates based on the job description, considering their skills, experience, and retention rate. Return the top 5 candidates in a summarized form, including their names, skills, experience and retention rate.
        If you dont have enough candidates for the relevent job please dont mention other candidates whose profile did not match the job description. 
        Accuracy is key first analyze the candidated and then fetch them.
        """

        # Define the LLM chain with Langchain and Groq
        prompt = PromptTemplate(template=input_prompt, input_variables=["job_description", "formatted_candidates"])
        groq_chain = LLMChain(llm=chat_groq_model, prompt=prompt)

        # Generate response using Groq
        result = groq_chain.run({"job_description": job_description, "formatted_candidates": formatted_candidates})
        return result

    except mysql.connector.Error as e:
        print(f"Error fetching candidates: {e}")
        return "An error occurred while fetching candidates."
    finally:
        cursor.close()
        conn.close()

# Main routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/submit', methods=['POST'])
def submit():
    company_name = request.form['company_name']
    job_title = request.form['job_title']
    job_description = request.form['job_description']
    
    if company_name and job_title and job_description:
        company_data = get_company_data(company_name, data)
        response, sentiment = generate_response(company_data)

        if response:
            input_prompt = f"""You are supposed to be an analyzer of company reviews of their employees. Your task is to generate responses on provided sentiments to show other applicants applying in this company.
            Don't build up positive, negative, and neutral sentiments, just show what the data tells you! Your sentiment should be a one-paragraph response:
            {sentiment}
            """
            response1 = genai.GenerativeModel('gemini-pro').generate_content(input_prompt).text
            save_job_details(company_name, job_title, job_description, response1)
            return render_template('result.html', response1=response1)
    return render_template('index.html', error="Please fill in all fields.")

@app.route('/top_candidates', methods=['GET', 'POST'])
def top_candidates():
    return render_template('top_candidates.html')

@app.route('/fetch_candidates', methods=['POST'])
def fetch_candidates():
    job_description = request.form['job_description']
    
    if job_description:
        top_candidates = fetch_top_candidates_using_rag(job_description)
        return render_template('candidates_result.html', candidate_response=top_candidates)
        
    return render_template('top_candidates.html', error="Please enter a job description.")

if __name__ == '__main__':
    app.run(debug=True)
