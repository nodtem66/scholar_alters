# Query TLDR from semantic scholar
import re
import time
import urllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

# Quick function to get datetime
get_datetime = lambda: datetime.now(timezone.utc).isoformat()

SEMANTIC_SCHOLAR_API_KEY = Path('./semantic_scholar_api_key.txt').read_text().strip()

def query_tldr_all_papers(df):
  
  #
  query_df = df[(df['tldr'].eq('') | df['tldr'].isnull()) & (df['status'] == 0)]
  new_papers = [
    # Created less than 2 weeks ago and updated more than 1 week ago
    (datetime.now(timezone.utc) - datetime.fromisoformat(d1)) < timedelta(days=14) and
    (datetime.now(timezone.utc) - datetime.fromisoformat(d2)) > timedelta(days=7) for (_, d1, d2) in query_df[['created_at', 'updated_at']].itertuples() ]
  new_papers = pd.Series(new_papers)
  #query_df = query_df[datetime.now(timezone.utc) - datetime.fromisoformat(query_df['created_at']) < timedelta(days=14)]
  #query_df = query_df[datetime.now(timezone.utc) - datetime.fromisoformat(query_df['updated_at']) > timedelta(days=7)]
  print(f"Querying TLDR for {query_df.shape[0]} papers")
  titles = [
    re.sub('[^A-Za-z0-9 ]+', ' ', title.strip())
    for title in query_df.title
  ]
  urls = [
    f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote_plus(title)}&fields=tldr,abstract&limit=1"
    for title in titles
  ]
  
  index_loc = query_df.index.to_list()
  assert len(index_loc) == len(urls), 'Index length mismatch'
  
  for i in tqdm(range(len(urls))):
    tstart = time.time()
    response = requests.get(urls[i], headers={'x-api-key': SEMANTIC_SCHOLAR_API_KEY})
    tend = time.time()
    if response.status_code == 200:
      response = response.json()
      if response.get('total') > 0:
        data = response.get('data')
        if data and len(data) > 0:
          result = data[0]
          tldr = result.get('tldr')
          if tldr and tldr.get('text'):
            df.loc[index_loc[i], 'tldr'] = tldr.get('text')
    # Update the time
    df.loc[index_loc[i], 'updated_at'] = get_datetime()

    # # Sleep for 1 second to avoid rate limit
    time.sleep(max(0, 1 - (tend - tstart)))