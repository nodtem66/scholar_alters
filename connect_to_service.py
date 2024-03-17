# -*- coding: utf-8 -*-
"""
Open emails and aggregate them together
"""

from __future__ import print_function
import pickle
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.pickle.
SCOPES = [
  'https://www.googleapis.com/auth/spreadsheets',
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/gmail.modify',
]
CLIENTSECRETS_LOCATION = r'./credentials.json'


def get_creds(data_folder='.'):
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  # The file token.pickle stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  token_filename = os.path.join(data_folder,'token.json')
  if os.path.exists(token_filename):
    creds = Credentials.from_authorized_user_file(token_filename, SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
        CLIENTSECRETS_LOCATION, SCOPES)
      creds = flow.run_local_server(port=0)
  # Save the credentials for the next run
  with open(token_filename, 'w') as token:
    token.write(creds.to_json())
  return creds

def get_gmail_service(credentials):
  return build('gmail', 'v1', credentials=credentials)

def get_drive_service(credentials):
  return build('drive', 'v3', credentials=credentials)

def get_sheets_service(credentials):
  return build('sheets', 'v4', credentials=credentials)

# Gmail service
def ListMessagesWithLabels(service, user_id, label_ids=[]):
  """List all Messages of the user's mailbox with label_ids applied.

  Args:
  service: Authorized Gmail API service instance.
  user_id: User's email address. The special value "me"
  can be used to indicate the authenticated user.
  label_ids: Only return Messages with these labelIds applied.

  Returns:
  List of Messages that have all required Labels applied. Note that the
  returned list contains Message IDs, you must use get with the
  appropriate id to get the details of a Message.
  """
  try:
    response = service.users().messages().list(userId=user_id, labelIds=label_ids).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = service.users().messages().list(userId=user_id,
                          labelIds=label_ids,
                          pageToken=page_token).execute()
      messages.extend(response['messages'])

    return messages
  except Exception as error:
    print ('An error occurred: %s' % error)


def GetLabelsId (service, user_id, label_names=[]):
  results = service.users().labels().list(userId=user_id).execute()
  labels = results.get('labels', [])

  label_ids = []
  for name in label_names:
    for label in labels:
      if label['name']==name:
        label_ids.append(label['id'])
  return label_ids


def GetMessage(service, user_id, msg_id):
  """Get a Message with given ID.

  Args:
  service: Authorized Gmail API service instance.
  user_id: User's email address. The special value "me"
  can be used to indicate the authenticated user.
  msg_id: The ID of the Message required.

  Returns:
  A Message.
  """
  try:
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()
    return message
  except Exception as error:
    print ('An error occurred: %s' % error)

# Drive service
def DownloadSheetFile(drive_service, file_id, destination_path):
  file_metadata = drive_service.files().get(fileId=file_id).execute()
  assert file_metadata['mimeType'] == 'application/vnd.google-apps.spreadsheet', "File is not a Google Sheet"

  # Download a file from Google Drive by its ID."""
  request_file = drive_service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet').execute()
  with open(destination_path, 'wb') as f:
    f.write(request_file)

def PrepareDataforUpdateSheet(service, file_id, df, sheet_name='Sheet1'):
  sheet = service.spreadsheets().values().get(spreadsheetId=file_id, range='Sheet1').execute()
  #assert(df.columns.values == result['values'][0], 'Columns do not match')
  num_rows_df = len(df)
  num_rows_sheet = len(sheet['values']) - 1
  num_mismatches = 0
  write_data = []
  assert num_rows_df >= num_rows_sheet, 'Sheet has more rows than the dataframe'

  for i in range(num_rows_sheet):
    idx = sheet['values'][i+1][6]
    if idx == df.iloc[i].idx:
      status = int(sheet['values'][i+1][8])
      if df.at[i, 'status'] != status:
        df.at[i,'status'] = status
    else:
      write_data.append({
        'range': f'A{i+2}', # i=0 -> A2
        'values': [df.iloc[i].tolist()]
      })
      #print(f"Row {i+1} does not match: {idx} != {df.iloc[i].idx}")
      num_mismatches += 1
  append_data = []
  if num_rows_sheet < num_rows_df:
    for i in range(num_rows_sheet, num_rows_df):
      append_data.append(df.iloc[i].tolist())

  return {'write_data': write_data, 'append_data': append_data}

def UpdateSheet(service, file_id, write_data):
  try:
    result = (
        service.spreadsheets()
        .values()
        .batchUpdate(
          spreadsheetId=file_id,
          #valueInputOption='USER_ENTERED',
          body={'valueInputOption': 'USER_ENTERED', 'data': write_data}
        )
    .execute())
    print(f"{(result.get('totalUpdatedCells'))} cells updated.")
  except HttpError as error:
    print(f"An error occurred: {error}")

def AppendSheet(service, file_id, append_data):
  try:
    result = (
        service.spreadsheets()
        .values()
        .append(
          spreadsheetId=file_id,
          range='Sheet1',
          valueInputOption='USER_ENTERED',
          body={'values': append_data}
        )
    .execute())
    print(f"{(result.get('updates').get('updatedCells'))} cells appended.")
  except HttpError as error:
    print(f"An error occurred: {error}")

if __name__ == '__main__':
  # Call the Gmail API
  creds = get_creds()
  service = get_gmail_service(credentials=creds)

  # Get all the messages with labels
  labels = GetLabelsId(service,'me',['Subscribe/Gscholar'])
  messages = ListMessagesWithLabels(service,"me",labels)
  print (f'Found {len(messages)} messages')