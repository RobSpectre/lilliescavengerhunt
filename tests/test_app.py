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

    def test_player_help(self):
        response = self.sms("HELP", url="/player")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("CLUE" in str(response.data))

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_player_stuck(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"

        response = self.sms("STUCK", url="/player")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))

        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Player is indicating "
                                                         "she is stuck.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_player_start(self, create_message_mock):
        response = self.sms("YES!!!!", url="/player")

        create_message_mock.return_value.sid = "SM718"

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Awesome" in str(response.data))

        assert 'Stop=Creek; Path=/' in response.headers.getlist('Set-Cookie')
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Game started.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_player_start_negative(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"

        response = self.sms("NO", url="/player")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Text YES to get going" in str(response.data))

        create_message_mock.assert_not_called()

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_player_start_unknown(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"

        response = self.sms("Unknown", url="/player")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("HELP" in str(response.data))

        create_message_mock.assert_not_called()

    def test_player_creek_redirect(self):
        self.app.set_cookie('localhost', 'Stop', 'Creek')
        response = self.sms("YES", url="player")

        self.assertTwiML(response)
        self.assertTrue("Redirect" in str(response.data))
        self.assertTrue("/player/creek" in str(response.data))


class PlayerTestCreek(TwiMLTest):
    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_creek_start(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        response = self.sms("YES", url="/player/creek")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Click this link" in str(response.data))

        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Video for Creek "
                                                         "delivered.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_creek_clue_0(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        response = self.sms("CLUE", url="/player/creek")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Willow" in str(response.data))

        assert 'Clue=1; Path=/' in response.headers.getlist('Set-Cookie')
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Clue 0 for Creek "
                                                         "requested.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_creek_clue_1(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        self.app.set_cookie('localhost', 'Clue', '1')
        response = self.sms("CLUE", url="/player/creek")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Museum" in str(response.data))

        assert 'Clue=2; Path=/' in response.headers.getlist('Set-Cookie')
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Clue 1 for Creek "
                                                         "requested.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_creek_clue_2(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        self.app.set_cookie('localhost', 'Clue', '2')
        response = self.sms("CLUE", url="/player/creek")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Google" in str(response.data))

        assert 'Clue=0; Path=/' in response.headers.getlist('Set-Cookie')
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Clue 2 for Creek "
                                                         "requested.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_creek_relay(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        response = self.sms("Testing relay.", url="/player/creek")

        self.assertTrue("<Response />" in str(response.data))

        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Testing relay.")
