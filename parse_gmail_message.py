# -*- coding: utf-8 -*-
"""
Open emails and aggregate them together
"""

from connect_to_gmail import  *
import base64
from html.parser import HTMLParser
import webbrowser
from os import path as ospath
from os import makedirs
import pickle
import re

DATA_FOLDER = r'./data'
PAPERS_LABEL = 'Subscribe/Gscholar'
PREV_PAPERS_FILE = r'prev_papers.pickle'
ARCHIVE_TSV = r'archive.tsv'


def clean_text(st):
  if st[0] == '[':
    st = st[st.find(']')+1:]
  st = re.sub(r'(\\[xX]\w\w)+','', st)
  return st.strip()


class Paper:
  def __init__(self, email_title, link):
    self.title = ''
    self.data = ''
    self.authors = ''
    self.link = link
    self.idx = ''
    self.email_title = email_title
    self.chosen = 0

  def add_title(self,data):
    self.title += clean_text(data) + " "
    self.idx = self.title.strip().upper()

  def add_authors(self,data):
    self.authors += clean_text(data) + " "

  def add_data(self,data):
    self.data += clean_text(data) + " "

  def set_chosen(self):
    self.chosen = 1

  def __eq__ (self, paper):
    return self.idx == paper.idx

  def __str__ (self):
    return f'{self.title}\nAuthors: {self.authors}\nEmail: {self.email_title}\n'

  def __repr__ (self):
    return self.title


class PapersHTMLParser(HTMLParser):
  STATE_DEFAULT = 0
  STATE_COLLECTED_TITLE = 1
  STATE_COLLECTED_AUTHORS = 2
  STATE_COLLECTED_DATA = 3

  def __init__ (self, email_title):
    HTMLParser.__init__(self)
    self.is_title = False
    self.is_data = False
    self.is_authors = False
    self.state = self.STATE_DEFAULT
    self.email_title = email_title
    self.papers = []

  def handle_starttag(self, tag, attrs):
    if tag == 'a':
      link = ''
      for attr in attrs:
        key = attr[0].lower()
        if key == 'href':
          link = attr[1]
        elif key == 'class' and attr[1] == 'gse_alrt_title':
          self.is_title = True
      if len(link) > 0 and self.is_title: 
        self.papers.append(Paper(self.email_title, link))

    elif tag == 'div':
      for attr in attrs:
        key = attr[0].lower()
        if key == 'class' and attr[1] == 'gse_alrt_sni':
          self.is_data = True
      if self.state == self.STATE_COLLECTED_TITLE and not self.is_data:
        self.is_authors = True

  def handle_endtag(self, tag):
    if tag == 'a' and self.is_title:
      self.is_title = False
      self.state = self.STATE_COLLECTED_TITLE
    elif tag == 'div':
      if self.is_authors:
        self.is_authors = False
        self.state = self.STATE_COLLECTED_AUTHORS
      elif self.is_data:
        self.is_data = False
        self.state = self.STATE_COLLECTED_DATA

  def handle_data(self, data):
    if len(self.papers) > 0:
      if self.is_title:
        self.papers[-1].add_title(data)
      elif self.is_authors:
        self.papers[-1].add_authors(data)
      elif self.is_data:
        self.papers[-1].add_data(data)


class PaperAggregator:
  def __init__ (self):
    self.paper_list = []

  def add(self, paper):
    try:
      idx = self.paper_list.index(paper)
    except ValueError: # Paper not in the list
      self.paper_list.append(paper)

  def remove(self, paper):
    try:
      idx = self.paper_list.index(paper)
      self.paper_list.pop(idx)
    except ValueError: # Paper not in the list
      pass


if __name__ == '__main__':
  # Create data folder if not exists
  if not ospath.exists(DATA_FOLDER):
    makedirs(DATA_FOLDER)

  # Call the Gmail API
  service = get_service(DATA_FOLDER)

  # Get all the messages with labels
  labels = GetLabelsId(service,'me',[PAPERS_LABEL,'UNREAD'])
  messages = ListMessagesWithLabels(service,"me",labels)
  print (f'Found {len(messages)} messages')

  # Parse the mails
  pa = PaperAggregator()

  for msg in messages:
    msg_content = GetMessage(service, "me", msg['id'])
    try:
      msg_str = base64.urlsafe_b64decode(msg_content['payload']['body']['data'].encode('utf-8'))
    except KeyError:
      continue

    msg_title = ''
    for h in msg_content['payload']['headers']:
      if h['name'] == 'Subject':
        msg_title = h['value']
    parser = PapersHTMLParser(msg_title)
    parser.feed(str(msg_str))

    for paper in parser.papers:
      pa.add(paper)

  # Remove previously seen papers
  pickle_file = ospath.join(DATA_FOLDER, PREV_PAPERS_FILE)
  if ospath.exists(pickle_file):
    with open(pickle_file,'rb') as pkl:
      old_pa = pickle.load(pkl)
      for paper in old_pa.paper_list:
        pa.remove(paper)

  # Sort by number of refernece mails
  print (f'Found {len(pa.paper_list)} papers')

  # User Input
  counter = 1
  good_papers = []
  web = webbrowser.get()
  for paper in pa.paper_list:
    print ('\n\n' + '-'*100 + '\n\n')
    print(f'Paper {counter} / {len(pa.paper_list)}\n')
    print(paper)
    response = input("Interesting? (y/n) ")
    if response.strip()[:1].lower() == 'y':
      good_papers.append(paper)
      paper.set_chosen()
      web.open(paper.link)
    counter+=1

  print("\n\nNow processing...")

  #Write current papers
  with open(pickle_file,'wb') as pkl:
    pickle.dump(pa,pkl)

  # Mark all as read
  body = {"addLabelIds": [], "removeLabelIds": ["UNREAD","INBOX"]}
  for msg in messages:
    service.users().messages().modify(userId="me", id=msg['id'], body=body).execute()

  # Archive the results for later learning
  with open(ospath.join(DATA_FOLDER, ARCHIVE_TSV),'a', encoding="utf-8") as f:
    for paper in pa.paper_list:
      f.write(f'{paper.title}\t{paper.authors}\t{paper.chosen}\n')


