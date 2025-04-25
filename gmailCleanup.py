

import os.path
import time
from collections import Counter
from email.utils import parseaddr
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

#
# Get sender information so we can idetify it later
# if it's eligible to be cleaned up
#
def get_sender_email(service, msg_id):
    """Get sender's email from a message."""
    start_time = time.time()
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='metadata',
                                               metadataHeaders=['From']).execute()
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'From':
                # Extract email from the "From" field
                _, email = parseaddr(header['value'])
                end_time = time.time()
                return email.lower(), end_time - start_time  # normalize email addresses
    except Exception as e:
        print(f"Error getting sender for message {msg_id}: {e}")
    end_time = time.time()
    return None, (end_time - start_time)

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.

    client_secrets_file = "/Users/dpang/Downloads/client_secret_457806803690-7ngkde632rtsg4m16fub5h0k1hmng1g9.apps.googleusercontent.com.json"
    token_file = "token.json"

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
            #"credentials.json", SCOPES
            client_secrets_file, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    # Count senders
    sender_counts = Counter()
    total_time = 0
    pageToken=''
    total_messages_processed = 0
    max_messages = 2000
    query_string='is:unread and before:2020/01/01'

    try:
        # Call the Gmail API
        service = build("gmail", "v1", credentials=creds)
        
        while total_messages_processed < max_messages:
            # Query for unread messages
            results = service.users().messages().list(
                userId='me',
                q=query_string,  # Query for unread messages
                maxResults=1000,  # Limit to recent messages for faster processing
                pageToken=pageToken # Oldest to newest
            ).execute()
            
            messages = results.get('messages', [])
            pageToken = results.get('nextPageToken')
            print(f"Got {len(messages)}")
            if not messages:
                print("No unread messages found.")
                return

            slowest_call = {'time': 0, 'msg_id': None, 'email': None}
            fastest_call = {'time': float('inf'), 'msg_id': None, 'email': None}

            for message in messages:
                sender, call_time = get_sender_email(service, message['id'])
                total_time += call_time

                # Track timing statistics
                if call_time > slowest_call['time']:
                    slowest_call = {'time': call_time, 'msg_id': message['id'], 'email': sender}
                if call_time < fastest_call['time']:
                    fastest_call = {'time': call_time, 'msg_id': message['id'], 'email': sender}

                if sender:
                    sender_counts[sender] += 1
                if sender_counts[sender] % 50 == 0:
                    print(f"Cumulative time is {total_time}")
                    print(f"Counts for {sender}: {sender_counts[sender]}")

                total_messages_processed += 1
                if total_messages_processed >= max_messages:
                    break

        # Get top 10 senders
        print("\nTop 10 senders with unread emails:")
        print("Email\t\t\t\tUnread Count")
        print("-" * 50)

        top_10_senders = sender_counts.most_common(10)
        for email, count in top_10_senders:
            print(f"{email:<30} {count}")

        # Create and print the search string
        search_string = " OR ".join(f"from:{email}" for email, _ in top_10_senders)
        print("\nSearch string for these senders:")
        print(search_string)

        print("\nTiming Statistics:")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average time per call: {total_time/len(messages):.3f} seconds")
        print(f"Fastest call: {fastest_call['time']:.3f}s (ID: {fastest_call['msg_id']}, Email: {fastest_call['email']})")
        print(f"Slowest call: {slowest_call['time']:.3f}s (ID: {slowest_call['msg_id']}, Email: {slowest_call['email']})")
    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
  main()


