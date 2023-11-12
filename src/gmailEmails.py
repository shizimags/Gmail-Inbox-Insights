import base64
from datetime import datetime, timedelta
import email

from main import compact_text_lines, extract_text_from_html

def get_email_details(service, message_id):
    # Get the full message details
    # print(f'Message ID: {message_id}')
    message = service.users().messages().get(userId='me', id=message_id).execute()

    subject = message.get('subject', 'No Subject')
    # print(f'Subject: {subject}')

    from_header = next((header['value'] for header in message['payload']['headers'] if header['name'].lower() == 'from'), 'Unknown Sender')
    # print(f'From: {from_header}')

    timestamp = int(message["internalDate"]) / 1000  # Convert milliseconds to seconds
    date_object = datetime.utcfromtimestamp(timestamp)
    formatted_date = date_object.strftime('%m/%d/%Y')
    # print(f'Date: {formatted_date}')

    # Fetch and print the labels
    labels = message.get('labelIds', [])
    # print(f'Labels: {", ".join(labels)}')

    compact_text = "No Body"
    # Check for multipart messages
    if 'multipart' in message['payload']['mimeType']:
        for part in message['payload']['parts']:
            if 'data' in part['body']:
                data = part['body']['data']
                decoded_data = base64.urlsafe_b64decode(data).decode("utf-8")
                text_content = extract_text_from_html(decoded_data)
                compact_text = compact_text_lines(text_content)
                # print(f'Body: {compact_text}')
    else:
        # If not multipart, try to decode the main body
        if 'data' in message['payload']['body']:
            data = message['payload']['body']['data']
            decoded_data = base64.urlsafe_b64decode(data).decode("utf-8")
            text_content = extract_text_from_html(decoded_data)
            compact_text = compact_text_lines(text_content)
            # print(f'Body: {compact_text}')

    #case when any of the aboce items are null or empty then pass null
    if subject == None:
        subject = 'No Subject'
    if from_header == None:
        from_header = 'Unknown Sender'
    if formatted_date == None:  
        formatted_date = 'No Date'
    if labels == None:
        labels = 'No Labels'
    if compact_text == None:
        compact_text = 'No Body'

    # Create a dictionary to store all the values
    email_details = {
        'message_id': message_id,
        'subject': subject,
        'from': from_header,
        'date': formatted_date,
        'labels': labels,
        'body': compact_text
    }

    print

    
    return email_details

