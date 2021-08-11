from unittest import mock
from unittest import TestCase

from .context import app
from .context import send_gm_message
from .context import send_player_message

app.config['TWILIO_ACCOUNT_SID'] = 'ACxxxxxx'
app.config['TWILIO_AUTH_TOKEN'] = 'yyyyyyyyy'
app.config['TWILIO_CALLER_ID'] = '+15558675309'
app.config['TWILIO_PLAYER'] = '15559990000'
app.config['TWILIO_GM'] = '+15556667777'


class TwiMLTest(TestCase):
    def setUp(self):
        self.app = app.test_client()

    def assertTwiML(self, response):
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
            params = {**params, **extra_params}

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
            params = {**params, **extra_params}
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

    def test_gm_admin_command(self):
        response = self.sms("ADMIN 2", url="/gm")

        self.assertTwiML(response)
        self.assertTrue("Redirect" in str(response.data))
        self.assertTrue("/gm/admin" in str(response.data))


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

        assert 'Stop=Fish; Path=/' in response.headers.getlist('Set-Cookie')
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

    def test_player_game_redirect(self):
        self.app.set_cookie('localhost', 'Stop', 'Fish')
        response = self.sms("YES", url="/player")

        self.assertTwiML(response)
        self.assertTrue("Redirect" in str(response.data))
        self.assertTrue("/player/Fish" in str(response.data))

    def test_video_404(self):
        response = self.app.get('/video/doesnotexist')

        self.assertEqual(response.status_code, 404)
        self.assertTrue("File Not Found" in str(response.data))

    def test_player_admin_command(self):
        response = self.sms("ADMIN 2", url="/player")

        self.assertTwiML(response)
        self.assertTrue("Redirect" in str(response.data))
        self.assertTrue("/gm/admin" in str(response.data))


class PlayerTestGame(TwiMLTest):
    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_game_start(self, create_message_mock):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            create_message_mock.return_value.sid = "SM718"

            response = self.sms("YES", url="/player/{0}".format(stop))

            self.assertTwiML(response)
            self.assertTrue("Message" in str(response.data))
            self.assertTrue("click" in str(response.data).lower())
            self.assertTrue("link" in str(response.data).lower())

            create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                        to=app.config['TWILIO_GM'],
                                                        body="Video for {0} "
                                                             "delivered."
                                                             "".format(stop))
            create_message_mock.reset_mock()

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_game_start_negative(self, create_message_mock):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            create_message_mock.return_value.sid = "SM718"

            response=self.sms("NO", url="/player/{0}".format(stop))

            self.assertTrue("<Response />" in str(response.data))
            self.assertFalse("well done" in str(response.data).lower())

            create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                        to=app.config['TWILIO_GM'],
                                                        body="NO")

            create_message_mock.reset_mock()

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_game_clue_0(self, create_message_mock):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            create_message_mock.return_value.sid = "SM718"
            self.app.set_cookie('localhost', 'Clue', '0')
            response = self.sms("CLUE", url="/player/{0}".format(stop))

            self.assertTwiML(response)
            self.assertTrue("Message" in str(response.data))

            assert 'Clue=1; Path=/' in response.headers.getlist('Set-Cookie')
            create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                        to=app.config['TWILIO_GM'],
                                                        body="Clue 0 for {0} "
                                                             "requested."
                                                             "".format(stop))
            create_message_mock.reset_mock()

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_game_clue_1(self, create_message_mock):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            create_message_mock.return_value.sid = "SM718"
            self.app.set_cookie('localhost', 'Clue', '1')
            response = self.sms("CLUE", url="/player/{0}".format(stop))

            self.assertTwiML(response)
            self.assertTrue("Message" in str(response.data))

            assert 'Clue=2; Path=/' in response.headers.getlist('Set-Cookie')
            create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                        to=app.config['TWILIO_GM'],
                                                        body="Clue 1 for {0} "
                                                             "requested."
                                                             "".format(stop))

            create_message_mock.reset_mock()

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_game_clue_2(self, create_message_mock):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            create_message_mock.return_value.sid = "SM718"
            self.app.set_cookie('localhost', 'Clue', '2')
            response = self.sms("CLUE", url="/player/{0}".format(stop))

            self.assertTwiML(response)
            self.assertTrue("Message" in str(response.data))

            assert 'Clue=0; Path=/' in response.headers.getlist('Set-Cookie')
            create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                        to=app.config['TWILIO_GM'],
                                                        body="Clue 2 for {0} "
                                                             "requested."
                                                             "".format(stop))

            create_message_mock.reset_mock()

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_game_relay(self, create_message_mock):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            create_message_mock.return_value.sid = "SM718"
            response = self.sms("Testing relay.",
                                url="/player/{0}".format(stop))

            self.assertTrue("<Response />" in str(response.data))

            create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                        to=app.config['TWILIO_GM'],
                                                        body="Testing relay.")

            create_message_mock.reset_mock()

    def test_game_video(self):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            response = self.app.get('/video/{0}'.format(stop))

            self.assertEqual(response.status_code, 200)

        response = self.app.get('/video/Final')

        self.assertEqual(response.status_code, 200)

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_game_victory(self, create_message_mock):
        for stop in [n[0] for n in app.config['Game']['Stop'].items()]:
            create_message_mock.return_value.sid = "SM718"
            self.app.set_cookie('localhost', 'Stop', stop)

            response = self.sms("Testing image.",
                                url="/player/{0}".format(stop),
                                extra_params={'NumMedia': '1',
                                              'MediaUrl0':
                                              'https://booger.com/booger.jpg'})

            self.assertTwiML(response)
            self.assertTrue("Message" in str(response.data))
            create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                        to=app.config['TWILIO_GM'],
                                                        body="Photo received "
                                                             "for {0}."
                                                             "".format(stop),
                                                        media_url='https://booger.com/'
                                                                  'booger.jpg')
            next_stop = app.config['Game']['Stop'][stop]['Victory']['Next']
            assert 'Stop={0}; Path=/'.format(next_stop) in response.headers.getlist('Set-Cookie')

            create_message_mock.reset_mock()


class TestPlayerEdges(TwiMLTest):
    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_clue_counter_reset_between_rounds(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        self.app.set_cookie('localhost', 'Stop', "Fish")

        self.sms("CLUE", url="/player/Fish")

        self.sms("Testing image.",
                 url="/player/Fish",
                 extra_params={'NumMedia': '1',
                               'MediaUrl0':
                               'https://booger.com/booger.jpg'})

        response = self.sms("CLUE", url="player/Fish")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Willow" in str(response.data))
        assert 'Clue=1; Path=/' in response.headers.getlist('Set-Cookie')

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_admin_restart(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        self.app.set_cookie('localhost', 'Stop', "Fish")

        response = self.sms("ADMIN RESTART", url="/gm/admin")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Restarting game" in str(response.data))
        assert 'Clue=0; Path=/' not in response.headers.getlist('Set-Cookie')
        assert 'Stop=Fish; Path=/' not in response.headers.getlist('Set-Cookie')

        create_message_mock.assert_called_once_with(to=app.config['TWILIO_GM'],
                                                    from_=app.config['TWILIO_CALLER_ID'],
                                                    body="Player restarted "
                                                         "game.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_admin_change_stop(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"
        self.app.set_cookie('localhost', 'Stop', "Fish")

        response = self.sms("ADMIN 1", url="/gm/admin")

        self.assertTwiML(response)
        self.assertTrue("Message" in str(response.data))
        self.assertTrue("Game reset to Bridge." in str(response.data))
        assert 'Clue=0; Path=/' in response.headers.getlist('Set-Cookie')
        assert 'Stop=Bridge; Path=/' in response.headers.getlist('Set-Cookie')

        create_message_mock.assert_called_once_with(to=app.config['TWILIO_GM'],
                                                    from_=app.config['TWILIO_CALLER_ID'],
                                                    body="Player reset game to "
                                                         "Bridge.")


class UtilitiesTest(TwiMLTest):
    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_send_player_message(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"

        msg = send_player_message("Testing player message.")

        self.assertEqual(msg.sid, "SM718")
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_PLAYER'],
                                                    body="Testing player "
                                                         "message.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_send_player_message_with_media(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"

        msg = send_player_message("Testing player message.",
                                  media_url="/booger.jpg")

        self.assertEqual(msg.sid, "SM718")
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_PLAYER'],
                                                    body="Testing player "
                                                         "message.",
                                                    media_url="/booger.jpg")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_send_gm_message(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"

        msg = send_gm_message("Testing GM message.")

        self.assertEqual(msg.sid, "SM718")
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Testing GM "
                                                         "message.")

    @mock.patch('twilio.rest.api.v2010.account.message.MessageList.create')
    def test_send_gm_message_with_media(self, create_message_mock):
        create_message_mock.return_value.sid = "SM718"

        msg = send_gm_message("Testing GM message.",
                              media_url="/booger.jpg")

        self.assertEqual(msg.sid, "SM718")
        create_message_mock.assert_called_once_with(from_=app.config['TWILIO_CALLER_ID'],
                                                    to=app.config['TWILIO_GM'],
                                                    body="Testing GM "
                                                         "message.",
                                                    media_url="/booger.jpg")
