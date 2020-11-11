import urllib, urllib2
import logging
import re
from contextlib import closing
from collections import OrderedDict
import os
from uuid import uuid4
import ssl

import common

class Connection:

    def __init__(self, timeoutSeconds, userAgent):
        self.timeoutSeconds = timeoutSeconds
        self.onExceptionRepeatCount = 3
        self.userAgent = userAgent
        self.excludeParametersFromLog = ['auth_challenge', 'auth_response']
        self.excludeHeadersFromLog = {'Cookie': '^(ljsession\s*=)'}
        self.secretWord = 'SECRET'
        self.interfacePath = '/interface/flat'
        self.largeFilesChunkSize = 16 * 1024
        self.imageContentTypeRegex = re.compile('^image\/(\w+)$', re.I)
        self.logger = logging.getLogger('log')
        
    def MakeRequest(self, url, params, hdrs = {}, type = 'POST'):
        """Makes request of type (POST or GET) to url with parameters and headers"""
        requestUrl = None
        requestParameters = None
        if type == 'POST':
            requestUrl = url
            requestParameters = self.UrlEncode(params)
        elif type == 'GET':
            requestUrl = '%s?%s' %(url, self.UrlEncode(params))
        else:
            raise ValueError(u'Invalid request type %s, only POST and GET are allowed' % type)
        hdrs['User-Agent'] = self.userAgent

        request = urllib2.Request(requestUrl, data = requestParameters, headers = hdrs)
        result = None
        repeatCount = 0
        while repeatCount < self.onExceptionRepeatCount:
            try:
                ctx = ssl.create_default_context(purpose = ssl.Purpose.SERVER_AUTH) # in case we're connecting to https
                with closing(urllib2.urlopen(request, timeout = self.timeoutSeconds, context = ctx)) as response:
                    result = response.read()
                break
            except Exception as e:
                filteredParams = self.__stripSensitiveInfoFromParams(params)
                filteredHeaders = self.__stripSensitiveInfoFromHeaders(hdrs)
                self.logger.debug(u'Exception on connect attempt #%d to %s with params = %s and headers %s' % ((repeatCount + 1), url, str(filteredParams), str(filteredHeaders)), exc_info = True)
                repeatCount = repeatCount + 1
                    
        if repeatCount == self.onExceptionRepeatCount:
            raise IOError(u'Could not read response from %s after %d attempts' % (url, repeatCount))
                    
        return result.decode("utf8")

    def ReadServerAnswer(self, answer):
        """Reads result of API call by flat protocol and returns properties and values as dictionary.
            Raises an exception in case server response contains error information
        """
        parsedAnswer = OrderedDict()

        #get rid of starting/ending mess that is sent by old API versions:
        #9e <- GETS DELETED
        #auth_scheme
        #c0
        #success
        #OK
        #   <- GETS DELETED
        #0  <- GETS DELETED
        #
        #In this case we don't need to cut anything:
        #errmsg
        #Client error: No mode specified.
        #success
        #FAIL
        regexStart = re.compile('^.*\n', re.I) #matches first line, has i flag
        regexEnd = re.compile('\n{2}0$', re.I | re.M) #matches a blank line (two newline chars) and 0, has im flags
        if regexEnd.search(answer):
            answer = regexStart.sub('', answer)
            answer = regexEnd.sub('', answer)

        answerLines = answer.splitlines()
        for i, line in enumerate(answerLines):
            if i % 2 == 0:
                parsedAnswer[line] = None
            else:
                lastKey = next(reversed(parsedAnswer))
                parsedAnswer[lastKey] = line

        if 'success' not in parsedAnswer or parsedAnswer['success'] == 'FAIL':
            if 'errmsg' in parsedAnswer:
                raise RuntimeError(unicode(parsedAnswer['errmsg']))
            else:
                raise RuntimeError(u'Unspecified server error: server returned an error flag but there was no error message associated with it')
        else:
            del parsedAnswer['success'] #no need to carry it over

        return parsedAnswer

    def GetServerAuthResponse(self, interfaceUrl, md5Password):
        """Gets server challenge token and returns a pair of challenge token and password hashed using this token as salt"""
        challengeData = self.ReadServerAnswer(self.MakeRequest(interfaceUrl, {'mode': 'getchallenge', 'ver': 1}))
        return {'auth_challenge': challengeData['challenge'], 'auth_response': common.MD5(challengeData['challenge'] + md5Password)}

    def MakeServerRequestWithAuthentication(self, connParams, mode, modeParams):
        """Makes two-step call to server, one to retrieve authentication token, another to actually load data"""
        interfaceUrl = connParams['server'] + self.interfacePath
        challengeAndResponse = self.GetServerAuthResponse(interfaceUrl, connParams['pwdhash'])
        params = common.MergeDicts({'mode': mode, 'auth_method': 'challenge', 'user': connParams['user'], 'ver': 1}, modeParams)
        return self.ReadServerAnswer(self.MakeRequest(interfaceUrl, common.MergeDicts(params, challengeAndResponse)))

    def GetSessionToken(self, connParams):
        """Get session token to use in cookies"""
        params = {'expiration': 'short'}
        postData = self.MakeServerRequestWithAuthentication(connParams, 'sessiongenerate', params)
        return postData['ljsession']
            
    def ExpireSession(self, connParams, sessionToken):
        """Expires session started by getting session token"""
        if sessionToken is not None:
            tokenParts = sessionToken.split(':') # session token looks like "v2:u12345:s123:abcdefg:abcdefghijklmnopqrstuvwxyz//1", session id is the 3rd part of it
            if len(tokenParts) >= 2:
                sessionId = re.sub('^s', '', tokenParts[2]) # gets 123 out of s123
                params = {'expire_id_%s' % sessionId: 1}
                self.MakeServerRequestWithAuthentication(connParams, 'sessionexpire', params)
				
    def DownloadImage(self, url, filePath, fromLink = False):
        """Downloads image into file with provided path & name, assigns proper extension to it and returns full path with extension or None if download fails"""
        fileFullPathWithExtension = None
        request = urllib2.Request(url)
        repeatCount = 0
        while repeatCount < self.onExceptionRepeatCount:
            try:
                ctx = ssl.create_default_context(purpose = ssl.Purpose.SERVER_AUTH)
                with closing(urllib2.urlopen(request, timeout = self.timeoutSeconds, context = ctx)) as response:
                    responseLowercaseHeaders = {k.lower():v for k, v in response.info().items()}
                    if 'content-type' in responseLowercaseHeaders:
                        matches = self.imageContentTypeRegex.search(responseLowercaseHeaders['content-type'])
                        if matches:
                            contentType = matches.group(1) # I'd use Python's imghdr, but is't very unreliable on jpegs, so let's rely on what server gives us
                            fileFullPath = os.path.join(filePath, '%s.tmp' % uuid4())
                            common.CreatePathIfNotExists(fileFullPath)
                            with open(fileFullPath, 'wb') as imageFile:
                                while True:
                                    chunk = response.read(self.largeFilesChunkSize)
                                    if not chunk:
                                        break
                                    imageFile.write(chunk)
                            trueFileName = common.GetUnicodeFileNameFromUrl(url, contentType, 'linked') if fromLink else common.GetUnicodeFileNameFromUrl(url, contentType) 
                            fileFullPathWithExtension = common.RenameFile(fileFullPath, os.path.join(filePath, trueFileName))
                        else:
                            self.logger.debug(u'Content-type header %s for url %s is not one of an image' % (responseLowercaseHeaders['content-type'], url))
                    else:
                        self.logger.debug(u'No content-type header for url %s' % url)
                break # break the WHILE cycle
            except Exception as e:
                codes400 = [403, 404, 410]
                if isinstance(e, urllib2.HTTPError) and e.code in codes400:
                    self.logger.debug(u'Error %d on downloading from url %s, stopping download attempts' % (e.code, url))
                    break # break the WHILE cycle
                self.logger.debug(u'Exception on downloading attempt #%d from url %s' % ((repeatCount + 1), url), exc_info = True)
                repeatCount = repeatCount + 1

        if repeatCount == self.onExceptionRepeatCount:
            self.logger.warning(u'Couldn\'t download image from url %s after %d attempts' % (url, repeatCount))
        return fileFullPathWithExtension
		
    def UrlEncode(self, params):
        """The urlencode library expects data in str format, and doesn't deal well with Unicode data since it doesn't provide a way to specify an encoding"""
        stringifiedAndEncodedParams = {}
        for key, value in params.iteritems():
            stringifiedAndEncodedParams[key] = unicode(value).encode('utf-8')
        return urllib.urlencode(stringifiedAndEncodedParams)

    def __stripSensitiveInfoFromParams(self, params):
        """Substitutes sensitive information in parameters with innocuous strings"""
        filteredParams = {}
        for key in params:
            filteredParams[key] = self.secretWord if key in self.excludeParametersFromLog else params[key]
        return filteredParams
		
    def __stripSensitiveInfoFromHeaders(self, headers):
        """Substitutes sensitive information in headers with innocuous strings"""
        filteredHeaders = {}
        for key in headers:
            if key in self.excludeHeadersFromLog:
                matches = re.match(self.excludeHeadersFromLog[key], headers[key], re.I)
                if matches:
                    filteredHeaders[key] = matches.group(1) + self.secretWord
            else:
                filteredHeaders[key] = headers[key]
        return filteredHeaders