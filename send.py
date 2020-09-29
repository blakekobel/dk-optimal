from Google import Create_Service
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CLIENT_SECRET_FILE = 'client_secret.json'
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://mail.google.com/']

service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

emailMsg = """Variables:

QB Kyler Murray = 1.0
RB Jerick McKinnon = 1.0
RB Miles Sanders = 1.0
TE Chris Herndon = 1.0
WR Amari Cooper = 1.0
WR Curtis Samuel = 1.0
WR DeAndre Hopkins = 1.0
WR Tyler Lockett = 1.0
---------------------------------------
Constraints: 6800*1.0 + 4900*1.0 + 6400*1.0 + 3400*1.0 + 6500*1.0 + 4000*1.0 + 7900*1.0 + 6400*1.0 = 46300.0
---------------------------------------
Score: 23.6*1.0 + 14.0*1.0 + 17.2*1.0 + 9.8*1.0 + 16.9*1.0 + 10.9*1.0 + 21.2*1.0 + 16.8*1.0 = 130.4
"""

mimeMessage = MIMEMultipart()
mimeMessage['to'] = 'Blakekobel@gmail.com'
mimeMessage['subject'] = 'Draft Kings Helper'
mimeMessage.attach(MIMEText(emailMsg, 'plain'))
raw_string = base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()

message = service.users().messages().send(
    userId='me', body={'raw': raw_string}).execute()
print(message)
