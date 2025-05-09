# -*- coding: utf-8 -*-
"""
Open emails and aggregate them together
"""

import json
import re
from datetime import datetime, timezone

import pandas as pd
from bs4 import BeautifulSoup
from typing_extensions import Self

get_datetime = lambda: datetime.now(timezone.utc).isoformat()

DATA_FOLDER = r'./data'
PAPERS_LABEL = 'Subscribe/Gscholar'
PREV_PAPERS_FILE = r'prev_papers.pickle'
ARCHIVE_TSV = r'archive.tsv'


def clean_text(st):
  if st[0] == '[':
    st = st[st.find(']')+1:]
  st = re.sub(r'(\\[xX]\w\w)+','', st)
  st = re.sub(r'(\\[uU]\w)+','', st)
  return st.strip()


class Paper:
  def __init__(self, email_title, link=''):
    self.title = ''
    self.data = ''
    self.authors = ''
    self.link = link
    self.idx = ''
    self.email_title = email_title
    self.year = None
    self.tldr = ''
    self.status = 0
    self.updated_at = None
    self.created_at = None

  def add_title(self,data):
    self.title = clean_text(data)
    self.idx = re.sub(r'[:;]', ' ', self.title.strip('. ').upper()) 

  def add_authors(self,data):
    self.authors = clean_text(data)
    try:
      self.year = int(data.replace(" ", "").split(",")[-1])
    except:
      pass

  def add_data(self,data):
    self.data = clean_text(data)

  def __eq__ (self, paper):
    return self.idx == paper.idx

  def __str__ (self):
    return json.dumps(self.__dict__, indent=2)

  def __repr__ (self):
    return self.__str__()

class PapersHTMLParser():
  def __init__ (self, email_title):
    self.email_title = email_title
    self.papers = []

  def parse(self, msg):
    soup = BeautifulSoup(msg, 'lxml')
    links = soup.find_all("a", class_='gse_alrt_title')
    for link in links:
      try:
        link_parent = link.parent
        if link_parent.name != 'h3':
          continue
        author = link_parent.next_sibling
        data_element = author.next_sibling
        if len(data_element.text) == 0 or len(author.text) == 0:
          print(f'Empty data or author: {link.text}')
          continue
        paper = Paper(self.email_title)
        paper.add_data(data_element.text)
        paper.add_title(link.text)
        paper.add_authors(author.text)
        paper.link = link['href']
        paper.created_at = get_datetime()
        paper.updated_at = get_datetime()
        self.papers.append(paper)      
      except AttributeError:
        pass

  def check_valid_papers(self):
    for paper in self.papers:
      assert paper.idx != '', f'Paper {paper.title} has no idx'
      assert paper.title != '', f'Paper {paper.idx} has no title'
      assert paper.link != '', f'Paper {paper.idx} has no link'
      assert paper.authors != '', f'Paper {paper.idx} has no authors'
      assert paper.data != '', f'Paper {paper.idx} has no data'
  
  def __str__ (self):
    return str(self.papers)
  
  def __repr__(self) -> str:
    return self.__str__()


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
    df = pd.read_excel(filename, dtype={'idx': str, 'status': int})
    df.fillna('', inplace=True)
    self.df_to_paper(df)

  def load_csv(self, filename):
    df = pd.read_csv(filename, sep=',')
    self.df_to_paper(df)
  
  def clean_missing_author(self):
    new_paper_list = [paper for paper in self.paper_list if paper.authors != '']
    self.paper_list = new_paper_list

  def df_to_paper(self, df):
    for idx, row in df.iterrows():
      paper = Paper(row['email_title'], row['link'])
      paper.title = row['title']
      paper.data = row['data']
      paper.authors = row['authors']
      paper.idx = row['idx']
      paper.year = row['year']
      paper.tldr = row['tldr']
      paper.status = int(row['status'])
      paper.created_at = row['created_at']
      paper.updated_at = row['updated_at']
      self.paper_list.append(paper)

  def to_dataframe(self):
    records = []
    for paper in self.paper_list:
      records.append([paper.title, paper.authors, paper.email_title, paper.link, paper.tldr, paper.year, paper.idx, paper.data, paper.status, paper.created_at, paper.updated_at])
    df = pd.DataFrame(records, columns=['title','authors','email_title','link','tldr','year','idx','data', 'status', 'created_at', 'updated_at'])
    df = df.astype({'status': 'object'})
    df.fillna('', inplace=True)
    return df

  def remove(self, paper):
    try:
      idx = self.paper_list.index(paper)
      self.paper_list.pop(idx)
    except ValueError: # Paper not in the list
      pass