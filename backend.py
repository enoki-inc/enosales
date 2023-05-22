#  to run fastapi server, do uvicorn fastapi:app --reload and can start interacting with the endpoints

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import os
from requests import HTTPError
from time import sleep

app = FastAPI()

class EmailRequest(BaseModel):
    recipient: str
    prompt: str

class SalesData(BaseModel):
    email: str
    context: str
    sell_product: str
    example_emails: str

class ReplyData(BaseModel):
    email: str
    email_address: str
    
def generate_response(system_prompt, user_prompt, *args):
    import openai
    import tiktoken

    def reportTokens(prompt):
        encoding = tiktoken.encoding_for_model(openai_model)
        print(
            "\033[37m"
            + str(len(encoding.encode(prompt)))
            + " tokens\033[0m"
            + " in prompt: "
            + "\033[92m"
            + prompt[:50]
            + "\033[0m"
        )

    openai_model = "gpt-3.5-turbo"
    openai_model_max_tokens = 500
    openai.api_key = os.environ["OPENAI_API_KEY"]

    messages = []
    messages.append({"role": "system", "content": system_prompt})
    reportTokens(system_prompt)
    messages.append({"role": "user", "content": user_prompt})
    reportTokens(user_prompt)

    role = "assistant"
    for value in args:
        messages.append({"role": role, "content": value})
        reportTokens(value)
        role = "user" if role == "assistant" else "assistant"

    params = {
        "model": openai_model,
        "messages": messages,
        "max_tokens": openai_model_max_tokens,
        "temperature": 0,
    }

    keep_trying = True
    while keep_trying:
        try:
            response = openai.ChatCompletion.create(**params)
            keep_trying = False
        except Exception as e:
            print("Failed to generate response. Error: ", e)
            sleep(30)
            print("Retrying...")

    reply = response.choices[0]["message"]["content"]
    return reply

def mail_sender(recipient, subject, content):
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send"
    ]
    flow = InstalledAppFlow.from_client_secrets_file('tmp.json', SCOPES)
    creds = flow.run_local_server(port=50799)

    service = build('gmail', 'v1', credentials=creds)
    message = MIMEText(content, 'html')
    message['to'] = recipient
    message['subject'] = subject
    create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    try:
        message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f"Sent message to {message} Message Id: {message['id']}")
    except HTTPError as error:
        print(f"An error occurred: {error}")
        message = None

def stripper(email_text):
    lines = email_text.split('\n')
    subject = lines[0].replace("Subject: ", "").strip()
    content = '\n'.join(lines[2:]).strip()
    return subject, content

def generate_sales_prompt(data):
    email = data.email_address
    context = data.context
    sell_product = data.sell_product
    example_emails = data.example_emails
    
    prompt = f"The email address is {email_address}. \
               Here is the context: {context}. \
               This is what I am trying to sell: {sell_product} \
               Here are examples of emails that have been successful at getting replies: {example_emails}. \
               Always specify the Email subject line in the first line of your response with the following format: Subject: <INSERT_SUBJECT_HERE>. \
               an example of spacing would be this: \
               Dear Bob, <br><br> \
               I hope this email finds you well. \
               I came across your profile and noticed your passion for playing the piano and finding a fun job. As an AI Sales Development Representative, I have the perfect solution for you. <br><br> \
               I believe our AI tool can help you find your dream job and make your job search process more efficient. If you're interested, I would love to schedule a demo and show you how our tool works. <br><br> \
               Best regards, <br><br> \
               Steve Joseph <br><br>"
    
    return prompt

@app.post("/sales/generate")
def generate_sales_response(sales_data: SalesData):
    prompt = generate_sales_prompt(sales_data)
    response = generate_response(
        """You are an AI Sales Development Representative who is trying to write a personalized sales email for the user based on their intent.""",
        prompt,
    )
    return {"email": response, "email_address": sales_data.email_address}
       
@app.post("/sales/send")
def send_email(reply_dict: ReplyData):
    try:
        subject, content = stripper(reply_dict.email)
        mail_sender(reply_dict.email_address, subject, content)
        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
