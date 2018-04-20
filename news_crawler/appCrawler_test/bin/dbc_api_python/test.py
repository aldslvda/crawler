import deathbycaptcha
import traceback
import json

# Put your DBC account username and password here.
# Use deathbycaptcha.HttpClient for HTTP API.
client = deathbycaptcha.SocketClient('bm0546', 'vobile123')
try:
    balance = client.get_balance()

    # Put your CAPTCHA file name or file-like object, and optional
    # solving timeout (in seconds) here:
    captcha = client.decode('vcode_cut.jpg', 10)
    if captcha:
        # The CAPTCHA was solved; captcha["captcha"] item holds its
        # numeric ID, and captcha["text"] item its text.
        print json.dumps(captcha)
        print "CAPTCHA %s solved: %s" % (captcha["captcha"], captcha["text"])

        #if ...:  # check if the CAPTCHA was incorrectly solved
        #    client.report(captcha["captcha"])
except deathbycaptcha.AccessDeniedException:
    traceback.print_exc()
    # Access to DBC API denied, check your credentials and/or balance