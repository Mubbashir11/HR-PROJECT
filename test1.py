
from flask import Flask, render_template, request, redirect, url_for
import PyPDF2
import re
import google.generativeai as genai
import os
import mysql.connector
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Database Connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database="job_database"
    )
    return conn

@app.route("/upload", methods=["GET", "POST"])
def upload_resume():
    if request.method == "POST":
        uploaded_file = request.files.get("resume")
        if uploaded_file and uploaded_file.filename.endswith('.pdf'):
            resume_text = extract_text_from_pdf(uploaded_file)
            if resume_text:
                resume_data, response = extract_resume_data(resume_text)
                insert_resume(resume_data)
                return render_template("resume_analysis.html", data=resume_data, response=response)
            else:
                return "Failed to extract text from the resume.", 400
        else:
            return "Invalid file format or no file uploaded.", 400
    return render_template("upload.html")

# Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file.stream)
        text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
        if not text:
            print("No text extracted from PDF.")
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None


def get_gemini_response(input_prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(input_prompt)
    return response.text

def extract_resume_data(resume_text):
    input_prompt = f"""
    Given the resume text below, please extract and format the key information as follows, ensuring high accuracy and adherence to the specified formats:

    - Name: [Full Name in Title Case]
    - Email: [Valid Email Address]
    - Skills: Please list each skill separated by commas, with each skill starting with a capital letter and no trailing comma at the end.
        Example Format: "Skill One, Skill Two, Skill Three"
    - Work Experience: Provide a list of recent positions held, starting each position with a dash and including the position title, company name, and the inclusive years worked.
        Example Format: 
        - Position One Title, Company Name (Year Started - Year Ended)
        - Position Two Title, Company Name (Year Started - Year Ended)
    - Retention Rate: Calculate the retention rate as the average number of years on job (devide total years of experience by no of jobs), presented as a single decimal number followed by 'years'. Assume the current year is 2024 for ongoing positions.
        Example Format: "X.Y years"


    Please use the following resume content to extract the information:
    {resume_text}

    Note: Ensure all outputs strictly follow the provided formats for uniformity and ease of data processing.
    """
    response = get_gemini_response(input_prompt)
    print(response)

    # Extract data using regex
    name_match = re.search(r"Name: (.+)", response)
    email_match = re.search(r"Email: (.+)", response)
    skills_match = re.search(r"Skills:(.*?)(?=- [A-Z]|\Z)", response, re.DOTALL)
    work_experience_match = re.search(r"- Work Experience:\s*(.+?)(?=\n- [A-Z]|$)", response, re.DOTALL)
    retention_rate_match = re.search(r"- Retention Rate: (\d+\.\d+) years", response)

    data = {
        "name": name_match.group(1).strip() if name_match else "Not found",
        "email": email_match.group(1).strip() if email_match else "Not found",
        "skills": [skill.strip() for skill in skills_match.group(1).strip().split(",")] if skills_match else [],
        "work_experience": [work_exp.strip() for work_exp in work_experience_match.group(1).strip().split(",")] if work_experience_match else [],
        "retention_rate": retention_rate_match.group(1) if retention_rate_match else 0.0
    }

    return data, response

# Get unique job details
def get_unique_job_details(job_role):
    conn = get_db_connection()
    jobs = []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT DISTINCT id, company_name, job_title, job_description, sentiment_analysis
        FROM job_details
        WHERE job_title LIKE %s;
        """
        print("Searching for job role:", job_role)
        cursor.execute(query, (f"%{job_role}%",))
        jobs = cursor.fetchall()
        print("Jobs found:", len(jobs))
    except Exception as e:
        print("SQL Error:", e)
    finally:
        cursor.close()
        conn.close()
    return jobs


def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    skills TEXT,
    experience_years TEXT,
    retention_rate TEXT
    )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Insert resume data into the database
def insert_resume(data):
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database="resume_db"
    )
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO candidates (name, email, skills, experience_years, retention_rate)
    VALUES (%s, %s, %s, %s, %s)
    ''', (
        data["name"],
        data["email"],
        ', '.join(data["skills"]),
        ', '.join(data["work_experience"]),
        data.get("retention_rate")
    ))
    conn.commit()
    cursor.close()
    conn.close()

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/find_jobs", methods=["POST"])
def find_jobs():
    job_title = request.form.get('job_title')
    jobs = get_unique_job_details(job_title)
    return render_template('jobs.html', jobs=jobs)

@app.route("/job/<int:job_id>")
def job_details(job_id):
    job = get_job_by_id(job_id)
    if job:
        return render_template('job_details.html', job=job)
    else:
        return "Job not found", 404

@app.route('/apply/<int:job_id>', methods=['POST'])
def apply(job_id):
    uploaded_file = request.files['resume']
    if uploaded_file and uploaded_file.filename.endswith('.pdf'):
        resume_text = extract_text_from_pdf(uploaded_file)
        data, response = extract_resume_data(resume_text)
        insert_resume(data)
        return "Resume submitted successfully! Thank you for applying."
    return redirect(url_for('job_details', job_id=job_id))

def get_job_by_id(job_id):
    conn = get_db_connection()
    job = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM job_details WHERE id = %s", (job_id,))
        job = cursor.fetchone()
    except Exception as e:
        print(f"Error retrieving job by ID: {e}")
    finally:
        cursor.close()
        conn.close()
    return job

if __name__ == "__main__":
    initialize_database()  # Initialize the database when the app starts
    app.run(debug=True)

