# -*- coding: utf-8 -*-
"""
Open emails and aggregate them together
"""

from connect_to_gmail import  *
from html.parser import HTMLParser
from os import path as ospath
from os import makedirs
import pickle
import re
import pandas as pd

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
    self.year = None
    self.tldr = ''
    self.status = 0

  def add_title(self,data):
    self.title += clean_text(data) + " "
    self.idx = re.sub(r'[:;]', ' ', self.title.strip('. ').upper())

  def add_authors(self,data):
    self.authors += clean_text(data) + " "
    self.year = data.replace(" ", "").split(",")[-1]

  def add_data(self,data):
    self.data += clean_text(data) + " "

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

from typing_extensions import Self

class PaperAggregator:
  def __init__ (self):
    self.paper_list = []

  def add(self, paper):
    try:
      idx = self.paper_list.index(paper)
    except ValueError: # Paper not in the list
      self.paper_list.append(paper)

  def merge(self, new_papers: Self):
    for paper in new_papers.paper_list:
      self.add(paper)

  def load_excel(self, filename):
    df = pd.read_excel(filename)
    for idx, row in df.iterrows():
      paper = Paper(row['email_title'], row['link'])
      paper.title = row['title']
      paper.data = row['data']
      paper.authors = row['authors']
      paper.idx = row['idx']
      paper.year = row['year']
      paper.tldr = row['tldr']
      paper.status = row['status']
      self.paper_list.append(paper)

  def to_dataframe(self):
    records = []
    for paper in self.paper_list:
      records.append([paper.title, paper.authors, paper.email_title, paper.link, paper.tldr, paper.year, paper.idx, paper.data, paper.status])
    return pd.DataFrame(records, columns=['title','authors','email_title','link','tldr','year','idx','data', 'status'])

  def remove(self, paper):
    try:
      idx = self.paper_list.index(paper)
      self.paper_list.pop(idx)
    except ValueError: # Paper not in the list
      pass