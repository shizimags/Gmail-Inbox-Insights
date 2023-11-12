from email.mime.text import MIMEText
from httpx import HTTPError
from src import gmail
from src import gmailEmails
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from resources import initializers
from src import onepassword_api
import base64
import textwrap
from datetime import datetime, timedelta
import openai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64

email_categories = initializers.email_categories

# Replace 'your_api_key' with your actual OpenAI API key
openai.api_key = onepassword_api.fetchMetabaseCredentials("openAIAPi",'Hackathon')

def main():

    # gmail authentication
    if(gmail.gmailAuthenticate()):
        print("Gmail API authenticated successfully")
        creds = gmail.gmailAuthenticate()
    else:
        print("Gmail API authentication failed")

    # Create a service object for interacting with the API
    service = build("gmail", "v1", credentials=creds)

    # Get the last two days emails- This will assign the labels to the emails
    get_emails_last_days(5)

    # getemails_today()
    # list 
    get_emails_by_label("Task Assignments",service)

    get_emails_by_label("Security Alerts",service)

    get_emails_by_label("Deadline Reminders",service)
    
def assignLabels(input_data,service):
    # Construct a prompt using the input data
    prompt = f"Classify the email category for the following message:\n\nSubject: {input_data['subject']}\nFrom: {input_data['from']}\nDate: {input_data['date']}\nLabels: {', '.join(input_data['labels'])}\n\nBody: {input_data['body']}"


    # Combine relevant fields from the example email into a single string for processing
    email_content = f"Subject: {input_data['subject']} {input_data['body']}"

    # Create a prompt for GPT-3
    prompt = f"Determine the category for the following email:\n\n{email_content}\n\nPossible categories: {', '.join(email_categories.keys())}"

    # Use the OpenAI API to generate a response
    response = openai.Completion.create(
        engine="text-davinci-003",  # You may need to use the appropriate engine
        prompt=prompt,
        max_tokens=200  # Adjust as needed
    )

    # Extract and print the generated output
    generated_text = response['choices'][0]['text'].strip()
    # print(f"GPT-3 Response:\n{generated_text}")
    
    # only print the keys of the email categories
    email_categories_keys = list(email_categories.keys())
    for i in range(len(email_categories_keys)):
        if email_categories_keys[i] in generated_text:
            print("Message ID: ")
            print(input_data['message_id'])
            print("Subject: ")
            print(input_data['subject'])
            print("From: ")
            print(input_data['from'])
            print("Labels: ")
            print(input_data['labels'])

            # If labels include nonAccessibleLabels then do not change the label
            if set(input_data['labels']).intersection(initializers.nonAccessibleLabels):
                print("Non Accessible Labels")
                break
            print("GPT-3 Response: " + email_categories_keys[i])
            change_label(service, input_data['message_id'], email_categories_keys[i])
            print("Label "+ email_categories_keys[i] +" assigned to "+ input_data['message_id'] +" successfully")
            break



def get_emails_last_days(dd):
    creds = gmail.gmailAuthenticate()
    service = build('gmail', 'v1', credentials=creds)

   # Calculate the date two days ago
    two_days_ago = datetime.utcnow() - timedelta(days=dd)
    
    # Format the date in YYYY/MM/DD format
    formatted_date = two_days_ago.strftime('%Y/%m/%d')
    
    # Use the formatted date in the search query
    query = f"after:{formatted_date}"

    results = service.users().messages().list(userId='me', q=query).execute()

    # Get messages from the last two days
    # results = service.users().messages().list(userId='me', q=f'after:{two_days_ago_timestamp}').execute()
    messages = results.get('messages', [])

    if not messages:
        print('No messages found.')
    else:
        for message in messages:
            input_data = gmailEmails.get_email_details(service, message['id'])
            assignLabels(input_data,service)
            print('------------------------------------------------------------------------------------------')

def get_emails():
    creds = gmail.gmailAuthenticate()
    service = build('gmail', 'v1', credentials=creds)

    # Call the Gmail API
    results = service.users().messages().list(userId='me').execute()
    messages = results.get('messages', [])

    if not messages:
        print('No messages found.')
    else:
        print('Messages:')
        for message in messages:
            input_data = gmailEmails.get_email_details(service, message['id'])
            assignLabels(input_data,service)
            print('------------------------------------------------------------------------------------------')




def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text()

def compact_text_lines(text):
    # Remove extra spaces and newlines and wrap the text
    return ' '.join(textwrap.wrap(text.strip(), width=80))

def change_label(service, message_id, new_label_name):

    
    # Check if the label exists, and create it if not
    labels = service.users().labels().list(userId='me').execute()
    label_names = [label['name'] for label in labels.get('labels', [])]

    if new_label_name not in label_names:
        create_label(service, new_label_name)

    # Modify labels for the specific message
    new_label_id = get_label_id(service, new_label_name)
    labels = {'removeLabelIds': [], 'addLabelIds': [new_label_id]}
    service.users().messages().modify(userId='me', id=message_id, body=labels).execute()

def create_label(service, label_name):
    # Create a new label
    label = {'name': label_name}
    created_label = service.users().labels().create(userId='me', body=label).execute()
    print(f"Label '{label_name}' created with ID: {created_label['id']}")

def get_label_id(service, label_name):
    # Get the ID of a label by name
    labels = service.users().labels().list(userId='me').execute()
    matching_labels = [label['id'] for label in labels.get('labels', []) if label['name'] == label_name]

    if matching_labels:
        return matching_labels[0]
    else:
        raise ValueError(f"Label '{label_name}' not found.")

def get_emails_by_label(label,service):
    LabelID = getLabelID(label,service)
    print(LabelID)
    response = []
    response= get_email_details_by_label(service,LabelID)

    ## collect the reponse in  numbered list for email body
    email_body = ""
    for i in range(len(response)):
        email_body += str(i+1) + ". " + response[i] + "\n\n"
    print(email_body)

    # Example email details
    sender_email = "shahzan.magray@gmail.com"
    recipient_email = "shahzan.magray@gmail.com"
    email_subject = "Notifications.AI for"+ label


    # Send the email
    send_message(service, sender_email, recipient_email, email_subject, email_body)
    print("Summary Email sent successfully for label" + label)

def createTODOemail(input_data,service):
    message_text = (summarize_email(input_data['body']))
    return message_text
    
    


def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}

def send_message(service, sender, to, subject, message_text):
    """Send an email message."""
    try:
        message = create_message(sender, to, subject, message_text)
        sent_message = service.users().messages().send(userId="me", body=message).execute()
        print(f"Message sent: {sent_message['id']}")
    except HttpError as error:
        print(f"An error occurred: {error}")

def getLabelID(labelidentifier,service):
    """List all labels and their IDs."""
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    labelid = ""
    if not labels:
        print('No labels found.')
    else:
        print('Labels:')
        for label in labels:
            if label['name'] == labelidentifier:
                # print(f"Label: {label['name']}, ID: {label['id']}")
                labelid = label['id']
                break

    return labelid


def get_email_details_by_label(service, label_id):
    # Get the full message details
    # print(f'Message ID: {message_id}')
    results = service.users().messages().list(userId='me', labelIds=label_id).execute()
    messages = results.get('messages', [])
    response = []
    if not messages:
        print('No messages found.')
    else:
        for message in messages:
            input_data = gmailEmails.get_email_details(service, message['id'])
            createTODOemail(input_data,service)

            # collect the createtodo in a reponse list
            
            response.append(createTODOemail(input_data,service))
            
    return response


def summarize_email(email_body):
    prompt = f"Summarise this email as a task assignment that may be needed for you to complete\":\n\n{email_body}\""
    
    # Make a call to OpenAI API
    response = openai.Completion.create(
        engine="text-davinci-003",  # You may need to use the appropriate engine
        prompt=prompt,
        max_tokens=150  # Adjust as needed
    )
    
    # Extract and return the generated summary
    return response['choices'][0]['text'].strip()


if __name__ == "__main__":
    main()
