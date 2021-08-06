from unittest import TestCase
from unittest import mock

from .context import app

app.config['TWILIO_ACCOUNT_SID'] = 'ACxxxxxx'
app.config['TWILIO_AUTH_TOKEN'] = 'yyyyyyyyy'
app.config['TWILIO_CALLER_ID'] = '+15558675309'
app.config['TWILIO_PLAYER'] = '15559990000'
app.config['TWILIO_GM'] = '+15556667777'


class TwiMLTest(TestCase):
    def setUp(self):
        self.app = app.test_client()

    def assertTwiML(self, response):
        app.logger.info(response.data)
        self.assertTrue(b"</Response>" in response.data, "Did not find "
                        "</Response>: {0}".format(response.data))
        self.assertEqual("200 OK", response.status)

    def sms(self, body, url='/sms', to=app.config['TWILIO_CALLER_ID'],
            from_='+15558675309', extra_params=None):
        params = {
            'SmsSid': 'SMtesting',
            'AccountSid': app.config['TWILIO_ACCOUNT_SID'],
            'To': to,
            'From': from_,
            'Body': body,
            'FromCity': 'BROOKLYN',
            'FromState': 'NY',
            'FromCountry': 'US',
            'FromZip': '55555'}
        if extra_params:
            params = dict(params.items() + extra_params.items())
        return self.app.post(url, data=params)

    def call(self, url='/voice', to=app.config['TWILIO_CALLER_ID'],
             from_='+15558675309', digits=None, extra_params=None):
        params = {
            'CallSid': 'CAtesting',
            'AccountSid': app.config['TWILIO_ACCOUNT_SID'],
            'To': to,
            'From': from_,
            'CallStatus': 'ringing',
            'Direction': 'inbound',
            'FromCity': 'BROOKLYN',
            'FromState': 'NY',
            'FromCountry': 'US',
            'FromZip': '55555'}
        if digits:
            params['Digits'] = digits
        if extra_params:
            params = dict(params.items() + extra_params.items())
        return self.app.post(url, data=params)


class VoiceTest(TwiMLTest):
    def test_voice(self):
        response = self.call()

        self.assertTwiML(response)
        self.assertTrue("</Say>" in str(response.data))


class GMTest(TwiMLTest):
    def test_sms(self):
        response = self.sms("Test.", from_="+15556667777")

        self.assertTwiML(response)
        self.assertTrue("Redirect" in str(response.data))
        self.assertTrue("/gm" in str(response.data))

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_start(self, create_message_mock):
        response = self.sms("START", from_="+15556667777", url="/gm")

        create_message_mock.return_value.sid = "SM718"

        self.assertTwiML(response)
        self.assertTrue("Message sent" in str(response.data))

        create_message_mock.assert_called_once()

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_reply(self, create_message_mock):
        response = self.sms("Testing a reply.", from_="+15556667777", url="/gm")

        create_message_mock.return_value.sid = "SM718"

        self.assertTrue("<Response />" in str(response.data))

        create_message_mock.assert_called_once()
        create_message_mock.assert_called_with(from_=app.config['TWILIO_CALLER_ID'],
                                               to=app.config['TWILIO_PLAYER'],
                                               body="Testing a reply.")


class PlayerTest(TwiMLTest):
    def test_sms(self):
        response = self.sms("Test")
        self.assertTwiML(response)
        self.assertTrue("Redirect" in str(response.data))
        self.assertTrue("/player" in str(response.data))
