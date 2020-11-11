from getpass import getpass
from modules.common import MD5

def ReadPasswordHash(server, user):
    pwdInputPrompt = str(u'Please enter password for user %s on server %s: ' % (server, user))
    pwdUserInput = getpass(pwdInputPrompt)
    while pwdUserInput == '':
        pwdUserInput = getpass(pwdInputPrompt)
    return MD5(pwdUserInput)
