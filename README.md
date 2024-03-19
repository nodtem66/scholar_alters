# Google scholar alert automation
Ingest the email with the tag, merge the duplicated papers, and update the list to google sheet (for appsheet)

## Workflow
 1. Parse unread emails labeled as Google Scholar
 2. Aggregate papers with the same name and remove papers that was seen on the previous run

## Setting for first use
You should need to use [Gmail API Client Library](https://developers.google.com/gmail/api/quickstart/python) and create
credentials.json as explained in the link.

## Google console
[Console](https://console.cloud.google.com/apis/dashboard?project=gscholar-alert)

Need:
- Gmail API
- Google Sheet API

URL: https://www.appsheet.com/start/7402d751-abe0-425d-891a-50971b51147c