'''
Configuration Settings
'''

# Begin Heroku configuration - configured through environment variables.
import os
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)
TWILIO_CALLER_ID = os.environ.get('TWILIO_CALLER_ID', None)
TWILIO_PLAYER = os.environ.get('TWILIO_PLAYER', None)
TWILIO_GM = os.environ.get('TWILIO_GM', None)
