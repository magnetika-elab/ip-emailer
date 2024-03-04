import socket
import psutil
import os
import http.client as httplib
import pickle
import base64
import time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import subprocess
from premailer import transform

def have_internet():
    conn = httplib.HTTPSConnection("8.8.8.8", timeout=5)
    try:
        conn.request("HEAD", "/")
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_gmail_service():
    creds = None
    TOKEN_PATH = os.path.join(os.getcwd(), 'email_token.pickle')
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(os.getcwd(), 'client_secret_91846246009-qforo9v6g7421i8k1k4ltm1tbkoqq7b1.apps.googleusercontent.com.json'),  
                ['https://www.googleapis.com/auth/gmail.send']
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def send_email(to, subject, body):
    service = get_gmail_service()
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(body, 'html'))
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    retries = 0
    while retries <= 5:
        try:
            sent_message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            print(f'Message Id: {sent_message["id"]}')
            return True
        except Exception as error:
            print(f'An error occurred: {error}')
            retries += 1
            time.sleep(10 if retries == 3 else 1)
    return False


def get_interfaces_and_ips():
    interface_ips = {}
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                interface_ips[interface] = addr.address
    return interface_ips

def make_table_html(headers, table_items):
    hostname = socket.gethostname()
    header_row = (
        f'\t<tr>\n'
        f'\t\t<th colspan="2" style="text-align: center; "><h2><span id="hostname_text">hostname: </span>{hostname}</h2></th>\n'
        f'\t</tr>\n'
        f'\t<tr>\n'
        + '\n'.join([f'\t\t<th>{header}</th>' for header in headers])
        + '\n\t</tr>'
    )
    interface_rows = '\n'.join([
        '\t<tr>\n' + '\n'.join([f'\t\t<td>{item}</td>' for item in entry]) + '\n\t</tr>'
        for entry in table_items
    ])
    table_html = (
        '<table style="width:100%">\n'
        f'{header_row}\n'
        f'{interface_rows}\n'
        '</table>'
    )
    return table_html

def make_email_html(headers, table_items):
    table_html = make_table_html(headers, table_items)
    with open('style.html', 'r') as file:
        html_style = file.read()
    page_html = '''
<!DOCTYPE html>
<html>
    <head>
{html_style}
    </head>
    <body>
        <div id="tablestuff">
{table_html}
        </div>
    </body>
</html>'''.format(
    hostname = socket.gethostname(), 
    html_style='\t\t'+'\n\t\t'.join(html_style.splitlines()), 
    table_html='\t\t\t'+'\n\t\t\t'.join(table_html.splitlines())
    )
    inline_html = transform(page_html)
    return inline_html


def get_email_list(filename=None):
    filename = filename if filename else os.path.join(os.getcwd(), 'ip_email_list.txt')
    with open(filename, 'r') as file:
        email_addresses = file.read().strip().splitlines()
    return email_addresses


def run_check_loop():
    last_interfaces_and_ips = None
    while True:
        interfaces_and_ips = get_interfaces_and_ips().items()
        if have_internet() and (interfaces_and_ips != last_interfaces_and_ips):
            subject = f'{socket.gethostname()} Ips'
            email_html = make_email_html(('interface','ip address'), interfaces_and_ips)
            exit()
            email_addresses = get_email_list()
            for email_address in email_addresses:
                send_email(
                    email_address,
                    subject,
                    email_html
                )
            last_interfaces_and_ips = interfaces_and_ips
        time.sleep(1)

if __name__ == "__main__":  
    run_check_loop()