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

@app.post("/email/send")
def send_email(request: EmailRequest):
    try:
        email = generate_response(
            """You are an AI Sales Development Representative who is trying to write a personalized sales email for the user based on their intent.""",
            request.prompt,
        )
        subject, content = stripper(email)
        mail_sender(request.recipient, subject, content)
        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
