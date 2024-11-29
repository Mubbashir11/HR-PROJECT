import streamlit as st
import PyPDF2
import re
import google.generativeai as genai
import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Database Connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )
    return conn

# Initialize the database (Run this once)
def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            skills TEXT,
            experience_years INT,
            retention_rate FLOAT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    try:
        text = ""
        pdf = PyPDF2.PdfReader(uploaded_file)
        for page in pdf.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return ""

def get_gemini_response(input_prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(input_prompt)
    return response.text

def extract_resume_data(resume_text):
    input_prompt = f"""
    Please extract key information from the following resume. The required details include the person's name, email, key skills, relevant work experience, and an estimated retention rate based on the average length of previous jobs. 
    Note that the resume format might not explicitly label these details.

    Resume:
    {resume_text}
    """
   
    response = get_gemini_response(input_prompt)

    # Extract data using regex
    name_match = re.search(r"Name: (.*)", response)
    email_match = re.search(r"Email: (.*)", response)
    skills_match = re.search(r"Skills: (.*)", response)
    work_experience_match = re.search(r"Work Experience: (.*)", response)
    retention_rate_match = re.search(r"Retention Rate: (.*)", response)

    data = {
        "name": name_match.group(1).strip() if name_match else "Not found",
        "email": email_match.group(1).strip() if email_match else "Not found",
        "skills": [skill.strip() for skill in skills_match.group(1).strip().split(",")] if skills_match else [],
        "work_experience": work_experience_match.group(1).strip() if work_experience_match else "Not found",
        "retention_rate": float(retention_rate_match.group(1).strip()) if retention_rate_match else 0.0
    }

    return data, response  # Return both data and response
def get_unique_job_details(job_role):
    conn = get_db_connection()
    jobs = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
        SELECT DISTINCT company_name, job_title, job_description
        FROM job_details
        WHERE job_title LIKE %s;
        """, (f"%{job_role}%",))
        jobs = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return jobs

# Streamlit app setup
st.title("Job Search Portal")

role = st.text_input("Please mention job position", key="job_position")
if st.button("Find Jobs", key="find_jobs_button"):
    jobs = get_unique_job_details(job_role=role)
    if jobs:
        for job in jobs:
            with st.expander(f"{job['title']} at {job['company']}"):
                st.text(job['description'])
    else:
        st.error("No jobs found for the specified role.")
# Optionally you can upload and process resumes here
# uploaded_file = st.file_uploader("Upload a PDF resume", type="pdf")
# if uploaded_file:
#     # Process your PDF and display results
#     st.write("Process and display resume details here.")

    
def insert_resume(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO candidates (name, email, skills, experience_years, retention_rate)
        VALUES (%s, %s, %s, %s, %s)
    ''', (
        data["name"],
        data["email"],
        ', '.join(data["skills"]),
        data.get("experience_years", 0),
        data.get("retention_rate", 0.0)
    ))
    conn.commit()
    cursor.close()
    conn.close()

uploaded_file = st.file_uploader("Upload a PDF resume", type="pdf")

if uploaded_file:
    resume_text = extract_text_from_pdf(uploaded_file)
    if st.button("Analyze Resume"):
        data, response = extract_resume_data(resume_text)  # Capture both data and response
        insert_resume(data)
        st.write(resume_text)
        st.write(f"**Name:** {data['name']}")
        st.write(f"**Email:** {data['email']}")
        st.write(f"**Skills:** {', '.join(data['skills'])}")
        st.write(f"**Work Experience:** {data['work_experience']}")
        st.write(f"**Estimated Retention Rate:** {data['retention_rate']} years")
        st.success("Resume data stored successfully in the database!")
        
        st.write("AI Response:")
        st.write(response)  # Display the AI response
    else:
        st.error("Please upload a PDF resume.")
