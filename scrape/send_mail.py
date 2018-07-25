import smtplib
import sys, os
from config import EMAIL_USER, EMAIL_PASS
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
COMMASPACE = ', '



def send_email(recipient, subject, attachment):

    FROM = EMAIL_USER
    TO = recipient if type(recipient) is list else [recipient]

    # Create the enclosing (outer) message
    outer = MIMEMultipart()
    outer['Subject'] = subject
    outer['To'] = recipient
    outer['From'] = FROM
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'

    attachments = [attachment]

    #text = "EMAIL MESSAGE"
    #outer.attach(MIMEText(text, 'plain')) # or 'html'

    for file in attachments:
        try:
            with open(file, 'rb') as fp:
                msg = MIMEBase('application', "octet-stream")
                msg.set_payload(fp.read())
            encoders.encode_base64(msg)
            msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
            outer.attach(msg)
        except:
            print("Unable to open one of the attachments. Error: ", sys.exc_info()[0])
            raise

    composed = outer.as_string()

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(FROM, TO, composed)
    server.close()
