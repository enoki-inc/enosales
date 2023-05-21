import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from requests import HTTPError
import sys
import os
import ast
from time import sleep
import re

generatedDir = "generated"
openai_model = "gpt-3.5-turbo"  # or 'gpt-4',
openai_model_max_tokens = 500  # i wonder how to tweak this properly

def generate_response(system_prompt, user_prompt, *args):
    import openai
    import tiktoken

    def reportTokens(prompt):
        encoding = tiktoken.encoding_for_model(openai_model)
        # print number of tokens in light gray, with first 10 characters of prompt in green
        print(
            "\033[37m"
            + str(len(encoding.encode(prompt)))
            + " tokens\033[0m"
            + " in prompt: "
            + "\033[92m"
            + prompt[:50]
            + "\033[0m"
        )

    # Set up your OpenAI API credentials
    openai.api_key = os.environ["OPENAI_API_KEY"]

    messages = []
    messages.append({"role": "system", "content": system_prompt})
    reportTokens(system_prompt)
    messages.append({"role": "user", "content": user_prompt})
    reportTokens(user_prompt)
    # loop thru each arg and add it to messages alternating role between "assistant" and "user"
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

    # Send the API request
    keep_trying = True
    while keep_trying:
        try:
            response = openai.ChatCompletion.create(**params)
            keep_trying = False
        except Exception as e:
            # e.g. when the API is too busy, we don't want to fail everything
            print("Failed to generate response. Error: ", e)
            sleep(30)
            print("Retrying...")

    # Get the reply from the API response
    reply = response.choices[0]["message"]["content"]
    return reply


def main(prompt):
    # read file from prompt if it ends in a .md filetype
    if prompt.endswith(".md"):
        with open(prompt, "r") as promptfile:
            prompt = promptfile.read()

    print("hi its me, 🐣EnoSales🐣! you said you wanted:")
    # print the prompt in green color
    print("\033[92m" + prompt + "\033[0m")

    # call openai api with this prompt
    output = generate_response(
        """You are an AI Sales Development Representative who is trying to write a personalized sales email for the user based on their intent.
        """,
        prompt,
    )

    return output

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
        message = (service.users().messages().send(userId="me", body=create_message).execute())
        print(F'sent message to {message} Message Id: {message["id"]}')
    except HTTPError as error:
        print(F'An error occurred: {error}')
        message = None

def stripper(email_text):
    lines = email_text.split('\n')

    # Extract the subject
    subject = lines[0].replace("Subject: ", "").strip()

    # Extract the content
    content = '\n'.join(lines[2:]).strip()

    return subject, content


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a prompt")
        sys.exit(1)
    prompt = sys.argv[1]
    email = main(prompt)
    print(email)
    subject, content = stripper(email)
    print("SUBJECT: ", subject)
    print("CONTENT: ", content)
    mail_sender("rohan@enoki.so", subject, content)


