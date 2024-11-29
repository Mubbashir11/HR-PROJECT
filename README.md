**Resume Analysis and Job Matching System**
This project is a comprehensive application designed for both employers and job seekers. It features two portals: an Employer Portal for job postings and sentiment analysis, and an Employee Portal for resume submission and job application tracking. The backend uses Flask, while Streamlit powers interactive interfaces for both portals.

Features
Employer Portal
Job Posting: Employers can post jobs by providing a job title and description.
Sentiment Analysis: The system performs sentiment analysis on the employer's organization and stores the sentiment along with the job posting details in a database.
Fetch Top Candidates: Employers can view a list of top candidates from the database based on job requirements and resume data.
Employee Portal
Resume Submission: Employees can upload their resumes (PDF format), which are processed to extract key details such as:
Name
Email
Skills
Work Experience
Retention Rate
Job Listings: Employees can view jobs posted by employers, including sentiment analysis data for each employer.
Backend
Flask Framework: Manages API endpoints and handles database operations.
AI-Powered Analysis: Google Gemini Generative AI extracts key details from resumes and calculates retention rates.
File Structure
bash
Copy code
resume-analysis-job-matching/
│
├── __pycache__/         # Cache files
├── env/                 # Environment configuration files
├── static/              # Static assets (CSS, JavaScript, etc.)
├── templates/           # HTML templates for Flask
│
├── .env                 # Environment variables (API keys, database credentials)
├── app.py               # Streamlit-based Employee Portal
├── main.py              # Streamlit-based Employer Portal
├── test.py              # Flask backend for Employee Portal
├── test1.py             # Flask backend for Employer Portal
│
├── REVIEWS.csv          # Sample Glassdoor/employee review data
├── temp_AI Engineer.pdf # Sample resume for testing
└── README.md            # Project documentation
Prerequisites
Ensure the following are installed on your system:

Python 3.9 or higher
MySQL Server
Required Python libraries (see below)
Installation
Clone the Repository:

bash
Copy code
git clone https://github.com/your-username/resume-analysis-job-matching.git
cd resume-analysis-job-matching
Set Up Environment Variables: Create a .env file in the project root with the following content:

env
Copy code
GOOGLE_API_KEY=your_google_api_key
MYSQL_HOST=localhost
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
Install Dependencies: Install Python libraries:

bash
Copy code
pip install -r requirements.txt
Set Up the Database:

Create a MySQL database named job_database.
Run the Flask application once to initialize the database schema.
Run the Applications:

Streamlit Portals:
Run the Employee Portal:
bash
Copy code
streamlit run app.py
Run the Employer Portal:
bash
Copy code
streamlit run main.py
Flask Backend:
For Employee Portal:
bash
Copy code
python test.py
For Employer Portal:
bash
Copy code
python test1.py
Access the Applications:

Employee Portal: http://localhost:8501
Employer Portal: http://localhost:8502
Features by Module
Streamlit Employee Portal (app.py)
Upload resumes for processing and storage.
View available jobs and apply directly through the interface.
Streamlit Employer Portal (main.py)
Post job openings with sentiment analysis.
Fetch top candidates based on job descriptions.
Flask Employee Backend (test.py)
Handles API requests for resume uploads and processing.
Extracts and stores candidate details in the database.
Flask Employer Backend (test1.py)
Manages API requests for job postings and sentiment analysis.
Retrieves top candidates based on job requirements.
Database Schema
Tables
candidates:

id: Primary Key
name: Candidate's name
email: Candidate's email
skills: Candidate's skills (comma-separated)
experience_years: Work experience details
retention_rate: Calculated retention rate
job_details:

id: Primary Key
company_name: Employer's organization name
job_title: Title of the job
job_description: Description of the job
sentiment_analysis: Sentiment score of the organization
Future Enhancements
Add email notifications for job applications and postings.
Implement a recommendation engine to suggest jobs to employees.
Add filtering and sorting for job listings (e.g., by sentiment score or location).
Support multiple file formats for resumes (e.g., DOCX).
