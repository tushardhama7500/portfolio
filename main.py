# main.py
# Simplified FastAPI application for Render deployment

import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Configure CORS for Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")
templates = Jinja2Templates(directory=".")

# OpenRouter API configuration (hardcoded as in your original code)
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"
FALLBACK_MODEL = "meta/llama-3.1-8b-instruct:free"

# Email configuration (hardcoded as in your original code)
SENDER_EMAIL = "tushardhama3@gmail.com"
SENDER_PASSWORD = "npqp yvps xgvj dtst"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Resume content - Updated with actual experience
RESUME_CONTENT = """
Tushar Dhama is a skilled Software Developer and Data Engineer with a B.Tech in Computer Science 
(8.5 CGPA) from Dr. Shakuntala Misra National Rehabilitation University.

EXPERIENCE:
C-Zentrix - Software Developer:
- Designed and maintained RESTful APIs using FastAPI for ERP and billing platforms, implementing RBAC and encryption for secure, high-availability services.
- Optimized MySQL queries and DB connection pooling in FastAPI, improving throughput for 80,000+ event packets/day from the Telephony Engine.
- Developed an intelligent VoiceBot system leveraging PipCat, STT, TTS, and LLMs to enhance customer support; automated deployments via GitLab CI/CD pipelines.
- Tech Stack: Python, RabbitMQ, FastAPI, Boto, AWS, GCS, MySQL, Pandas, OOPs, MongoDB, Redis.

Spinny - Data Engineer Intern:
- Built a real-time CDC pipeline using Docker, Zookeeper, Kafka, MongoDB, and Debezium, achieving near-zero latency for continuous data sync.
- Deployed and managed containerized services on AWS ECS and Lambda with RDS integration, enabling scalable and fault-tolerant data processing.
- Engineered PySpark pipelines for large-scale data transformation and analytics, storing outputs in AWS S3 for BI reporting.
- Tech Stack: Python, Docker, Debezium, Apache Kafka, AWS, PySpark, MongoDB.

PROJECTS:
Email AI Classifier Bot:
- Developed a FastAPI backend to serve ML models via REST APIs, classifying Gmail emails into categories.
- Built a spam detection model with 96.4% accuracy using Naive Bayes and Logistic Regression, containerized with Docker.
- Integrated with Telegram Bot API for real-time email notifications with actions like Archive, Delete, Snooze, and AI Reply.

Weatherapp:
- Implemented a high-throughput data ingestion system handling 30k+ messages/sec with Kafka from multiple weather sources.
- Designed REST APIs with FastAPI to deliver aggregated weather insights from PostgreSQL.
- Deployed on AWS ECS with containerization for real-time weather data delivery.

SKILLS:
Backend Development: Python, FastAPI, REST API Design, SQL, Docker
Databases: MySQL, PostgreSQL, MongoDB, Redis, RDS
Cloud: AWS (Lambda, ECS, RDS, EC2, S3), Azure, GCS
DevOps: GitLab CI/CD, GitHub, Linux
Messaging/Streaming: Apache Kafka, RabbitMQ, Zookeeper
Others: Pandas, PySpark, Machine Learning, LLMs

EDUCATION:
B.Tech Computer Science - Dr. Shakuntala Misra National Rehabilitation University (8.5 CGPA)
"""

# Prompt template for AI
PROMPT_TEMPLATE = """
You are Tushar Dhama, a Software Developer and Data Engineer. Your goal is to provide helpful, engaging, and concise responses to user questions based on your resume and experience. Respond as if you are personally addressing the user.

User details:
- Name: {name}
- Email: {email}

Question: {question}

About Tushar Dhama:
{resume}

Respond as Tushar Dhama himself, addressing the user by name and signing off with 'Best regards, Tushar Dhama'. Use your actual experience from the resume to provide specific, relevant answers. Be professional but friendly.
"""

# Response for invalid questions
INVALID_QUESTION_RESPONSE = """
Dear {name},

Thank you for reaching out! It seems like your question might not be clear or relevant to my portfolio. Could you please provide a more specific question related to my experience, projects, or skills? I'm happy to assist with details about my work in Python, FastAPI, data engineering, or any other topic from my resume.

Best regards,
Tushar Dhama
"""

# Cache for AI responses
response_cache = {}

class QueryInput(BaseModel):
    name: str
    email: str
    question: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("main.html", {"request": request})

# Serve profile image directly
@app.get("/profile.jpeg")
async def get_profile_image():
    """Serve the profile image"""
    return FileResponse("profile.jpeg")

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "message": "Portfolio API is running"}

def is_valid_question(question: str) -> bool:
    """Validate if the question is meaningful."""
    question = question.strip()
    if len(question) < 5:
        return False
    if not re.search(r'[a-zA-Z]', question):
        return False
    words = question.split()
    if len(words) < 2 and len(question) > 10 and not re.search(r'[aeiou]', question.lower()):
        return False
    return True

def generate_ai_response(name: str, email: str, question: str) -> str:
    """Generate AI response with caching and model fallback for reliability."""
    cache_key = f"{name.lower()}:{question.lower()[:50]}"
    if cache_key in response_cache:
        print(f"Using cached response for key: {cache_key}")
        return response_cache[cache_key]
    
    prompt = PROMPT_TEMPLATE.format(name=name, email=email, question=question, resume=RESUME_CONTENT)
    
    models_to_try = [MODEL, FALLBACK_MODEL]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300
        }
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"Attempting AI generation with model: {model}")
            response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
            print(f"API Response Status: {response.status_code}")
            if response.status_code != 200:
                print(f"API Error Response: {response.text}")
            response.raise_for_status()
            data = response.json()
            ai_response = data['choices'][0]['message']['content'].strip()
            response_cache[cache_key] = ai_response
            if len(response_cache) > 100:
                response_cache.pop(next(iter(response_cache)))
            print(f"AI generation successful using model: {model}")
            return ai_response
        except requests.exceptions.RequestException as e:
            print(f"Request failed for model {model}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Full error response: {e.response.text}")
        except Exception as e:
            print(f"Unexpected error for model {model}: {str(e)}")
            if model == FALLBACK_MODEL:
                break
    
    # Fallback static response if all models fail
    print("All AI models failed; using static fallback response")
    return f"""Dear {name},

Thank you for reaching out! I'm Tushar Dhama, a Software Developer and Data Engineer with experience in building scalable backend systems and data pipelines. At C-Zentrix, I worked on RESTful APIs for ERP platforms and developed intelligent VoiceBot systems. At Spinny, I built real-time CDC pipelines handling massive data streams.

If you have specific questions about my projects like the Email AI Classifier Bot (96.4% accuracy) or my experience with FastAPI, Kafka, or AWS, feel free to ask—I'm happy to connect!

Best regards,
Tushar Dhama"""

def send_email(to_email: str, subject: str, body: str):
    """Send email synchronously."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False

def process_valid_query_background(name: str, email: str, question: str):
    """Background task for valid questions: generate AI response and send email."""
    try:
        ai_response = generate_ai_response(name, email, question)
        email_sent = send_email(email, "Response to Your Query on My Portfolio", ai_response)
        if email_sent:
            print(f"Background task completed: Email sent to {email}")
        else:
            print(f"Background task failed: Could not send email to {email}")
    except Exception as e:
        print(f"Background task failed for {email}: {str(e)}")

@app.post("/ask")
async def handle_query(input: QueryInput, background_tasks: BackgroundTasks):
    """Handle form submission: validate question, respond immediately, process in background."""
    try:
        # Validate the question
        if not is_valid_question(input.question):
            body = INVALID_QUESTION_RESPONSE.format(name=input.name)
            email_sent = send_email(input.email, "Response to Your Query on My Portfolio", body)
            if email_sent:
                return {
                    "status": "success",
                    "message": "Your question seems unclear. A response has been sent to your email asking for a more relevant question."
                }
            else:
                return {
                    "status": "error",
                    "message": "There was an issue sending the email. Please try again later."
                }
        
        # For valid questions, add to background task and return immediately
        background_tasks.add_task(process_valid_query_background, input.name, input.email, input.question)
        return {"status": "success", "message": "Thank you for your message! I'll respond to your email shortly."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)