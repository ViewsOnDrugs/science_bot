import smtplib
import ssl
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

smtp_server= 'smtp.gmail.com'
port = 465
sender=os.getenv('GUSERNAME')
password=os.getenv('GMAIL_PASS')

context= ssl.create_default_context()


# try:
#     server=smtplib.SMTP(smtp_server,port)
#     server.ehlo()
#     server.starttls(context=context)
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
  server.login(sender,password)
  #send email
  receiver ='otrousuariomas@outlook.de'
  message="failed with {error_report}"
  server.sendmail(sender,receiver,message)
  print('works')
