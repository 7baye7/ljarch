import os
import sys
import urllib, urllib2
import httplib
from collections import OrderedDict
from cStringIO import StringIO
import unittest
import mock

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
import connection
import common

class ConnectionTestCase(unittest.TestCase):

    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    def test_MakeRequest_Post(self, mock_urlopen, mock_request):
        # Arrange
        url = 'http://a.com'
        returnValue = u'\u4e00'
        userAgent = 'Foo'
        params = {'param1': 1, 'param2': 2}
        headers = {'header1': 'HeaderValue'}
        mock_urlopen.return_value.read.return_value = returnValue.encode('utf8')
        cnn = connection.Connection(1, userAgent)

        # Act
        result = cnn.MakeRequest(url, params, hdrs = headers)

        # Assert
        self.assertEqual(result, returnValue)
        mock_request.assert_called_with(url, data = cnn.UrlEncode(params), headers = {'User-Agent': userAgent, 'header1': 'HeaderValue'})
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    def test_MakeRequest_Get(self, mock_urlopen, mock_request):
        # Arrange
        url = 'http://a.com'
        returnValue = u'\u4e00'
        userAgent = 'Foo'
        params = {'param1': 1, 'param2': 2}
        headers = {'header1': 'HeaderValue'}
        mock_urlopen.return_value.read.return_value = returnValue.encode('utf8')
        cnn = connection.Connection(1, userAgent)

        # Act
        result = cnn.MakeRequest(url, params, hdrs = headers, type = 'GET')

        # Assert
        self.assertEqual(result, returnValue)
        mock_request.assert_called_with('%s?%s' %(url, cnn.UrlEncode(params)), data = None, headers = {'User-Agent': userAgent, 'header1': 'HeaderValue'})
		
    def test_MakeRequest_ExceptionOnRequestType(self):
        # Arrange
        url = 'http://a.com'
        params = {'param1': 1, 'param2': 2}
        type = 'PUT'
        cnn = connection.Connection(1, 'Foo')

        # Act
        with self.assertRaises(ValueError) as assertEx:
            cnn.MakeRequest(url, params, type = type)

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Invalid request type %s, only POST and GET are allowed' % type)
		
    @mock.patch('common.logging', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    def test_MakeRequest_ExceptionAfterMultipleReads(self, mock_urlopen, mock_logging):
        # Arrange
        url = 'http://a.com'
        params = {'param1': 1, 'param2': 2}
        mock_urlopen.return_value.read.side_effect = httplib.BadStatusLine('URGH!')
        cnn = connection.Connection(1, 'Foo')

        # Act
        with self.assertRaises(IOError) as assertEx:
            cnn.MakeRequest(url, params)

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Could not read response from %s after 3 attempts' % url)
		
    def test_ReadServerAnswer_New(self):
        # Arrange
        input = 'auth_scheme\nc0\nsuccess\nOK\nsync_items\n0'
        expectedOutput = OrderedDict()
        expectedOutput['auth_scheme'] = 'c0'
        expectedOutput['sync_items'] = '0'
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.ReadServerAnswer(input)

        # Assert
        self.assertEqual(result, expectedOutput)
		
    def test_ReadServerAnswer_Old(self):
        # Arrange
        input = '9e\nauth_scheme\nc0\nsuccess\nOK\nsync_items\n0\n\n0'
        expectedOutput = OrderedDict()
        expectedOutput['auth_scheme'] = 'c0'
        expectedOutput['sync_items'] = '0'
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.ReadServerAnswer(input)

        # Assert
        self.assertEqual(result, expectedOutput)
		
    def test_ReadServerAnswer_ExceptionOnErrorMsg(self):
        # Arrange
        input = 'errmsg\nClient error: No mode specified.\nsuccess\nFAIL'
        cnn = connection.Connection(1, 'Foo')

        # Act
        with self.assertRaises(RuntimeError) as assertEx:
            cnn.ReadServerAnswer(input)

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Client error: No mode specified.')
		
    def test_ReadServerAnswer_UnknownException(self):
        # Arrange
        input = 'success\nFAIL'
        cnn = connection.Connection(1, 'Foo')

        # Act
        with self.assertRaises(RuntimeError) as assertEx:
            cnn.ReadServerAnswer(input)

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Unspecified server error: server returned an error flag but there was no error message associated with it')
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    def test_GetServerAuthResponse(self, mock_urlopen, mock_request):
        # Arrange
        mock_urlopen.return_value.read.return_value = 'challenge\nabcde\nsuccess\nOK'
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.GetServerAuthResponse('http://a.com', 'md5password')

        # Assert
        self.assertEqual(result, {'auth_challenge': 'abcde', 'auth_response': common.MD5('abcde' + 'md5password')})
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    def test_MakeServerRequestWithAuthentication(self, mock_urlopen, mock_request):
        # Arrange
        mock_urlopen.return_value.read.side_effect = ['challenge\nabcde\nsuccess\nOK', 'result\nSomeValue\nsuccess\nOK']
        url = 'http://a.com'
        userAgent = 'Foo'
        connParams = {'server': url, 'user': 'i_robot', 'pwdhash': 'md5password'}
        mode = 'foo'
        modeParams = {'param1': '1'}
        expectedOutput = OrderedDict()
        expectedOutput['result'] = 'SomeValue'
        expectedParams = common.MergeDicts(common.MergeDicts({'mode': mode, 'auth_method': 'challenge', 'user': 'i_robot', 'ver': 1}, modeParams),
                                           {'auth_challenge': 'abcde', 'auth_response': common.MD5('abcde' + 'md5password')})
        cnn = connection.Connection(1, userAgent)

        # Act
        result = cnn.MakeServerRequestWithAuthentication(connParams, mode, modeParams)

        # Assert
        self.assertEqual(result, expectedOutput) 
        mock_request.assert_called_with(url + '/interface/flat', data = cnn.UrlEncode(expectedParams), headers = {'User-Agent': userAgent})	
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    def test_GetSessionToken(self, mock_urlopen, mock_request):
        # Arrange
        mock_urlopen.return_value.read.side_effect = ['challenge\nabcde\nsuccess\nOK', 'ljsession\nSessionToken\nsuccess\nOK']
        url = 'http://a.com'
        userAgent = 'Foo'
        connParams = {'server': url, 'user': 'i_robot', 'pwdhash': 'md5password'}
        mode = 'sessiongenerate'
        modeParams = {'expiration': 'short'}
        expectedParams = common.MergeDicts(common.MergeDicts({'mode': mode, 'auth_method': 'challenge', 'user': 'i_robot', 'ver': 1}, modeParams),
                                           {'auth_challenge': 'abcde', 'auth_response': common.MD5('abcde' + 'md5password')})
        cnn = connection.Connection(1, userAgent)

        # Act
        result = cnn.GetSessionToken(connParams)

        # Assert
        self.assertEqual(result, u'SessionToken') 
        mock_request.assert_called_with(url + '/interface/flat', data = cnn.UrlEncode(expectedParams), headers = {'User-Agent': userAgent})	
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    def test_ExpireSession(self, mock_urlopen, mock_request):
        # Arrange
        mock_urlopen.return_value.read.side_effect = ['challenge\nabcde\nsuccess\nOK', 'success\nOK']
        url = 'http://a.com'
        userAgent = 'Foo'
        connParams = {'server': url, 'user': 'i_robot', 'pwdhash': 'md5password'}
        mode = 'sessionexpire'
        modeParams = {'expire_id_123': 1}
        expectedParams = common.MergeDicts(common.MergeDicts({'mode': mode, 'auth_method': 'challenge', 'user': 'i_robot', 'ver': 1}, modeParams),
                                           {'auth_challenge': 'abcde', 'auth_response': common.MD5('abcde' + 'md5password')})
        cnn = connection.Connection(1, userAgent)

        # Act
        cnn.ExpireSession(connParams, 'v2:u12345:s123:abcdefg:abcdefghijklmnopqrstuvwxyz//1')

        # Assert
        mock_request.assert_called_with(url + '/interface/flat', data = cnn.UrlEncode(expectedParams), headers = {'User-Agent': userAgent})	
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    def test_ExpireSession_TokenIsNone(self, mock_request):
        # Arrange
        cnn = connection.Connection(1, 'Foo')

        # Act
        cnn.ExpireSession({}, None)

        # Assert
        self.assertFalse(mock_request.called)
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    def test_ExpireSession_TokenIsInvalid(self, mock_request):
        # Arrange
        cnn = connection.Connection(1, 'Foo')

        # Act
        cnn.ExpireSession({}, 'InvalidToken')

        # Assert
        self.assertFalse(mock_request.called)
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request):
        # Arrange
        url = 'http://a.com/img.png'
        mock_isfile.return_value = False
        responseHdrs = httplib.HTTPMessage(StringIO(""))
        responseHdrs["Content-Type"] = "image/png"
        mock_urlopen.return_value.read.side_effect = [b'0123456', b'']
        mock_urlopen.return_value.info.return_value = responseHdrs
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\')

        # Assert
        self.assertEqual(result, u'a:\\b\\img (a.com).png')
		
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage_FromLink(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request):
        # Arrange
        url = 'http://a.com/img.png'
        mock_isfile.return_value = False
        responseHdrs = httplib.HTTPMessage(StringIO(""))
        responseHdrs["Content-Type"] = "image/png"
        mock_urlopen.return_value.read.side_effect = [b'0123456', b'']
        mock_urlopen.return_value.info.return_value = responseHdrs
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\', True)

        # Assert
        self.assertEqual(result, u'a:\\b\\img (linked) (a.com).png')
		
    @mock.patch('connection.logging.getLogger', autospec=True)
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage_ContentTypeIsNotImage(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request, mock_logging):
        # Arrange
        url = 'http://a.com/img.png'
        mock_isfile.return_value = False
        responseHdrs = httplib.HTTPMessage(StringIO(""))
        responseHdrs["Content-Type"] = "application/pdf"
        mock_urlopen.return_value.read.side_effect = [b'0123456', b'']
        mock_urlopen.return_value.info.return_value = responseHdrs
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\')

        # Assert
        self.assertEqual(result, None)
        cnn.logger.debug.assert_called_once_with(u'Content-type header %s for url %s is not one of an image' % (responseHdrs["Content-Type"], url))
		
    @mock.patch('connection.logging.getLogger', autospec=True)
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage_NoContentTypeInHeaders(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request, mock_logging):
        # Arrange
        url = 'http://a.com/img.png'
        mock_isfile.return_value = False
        mock_urlopen.return_value.read.side_effect = [b'0123456', b'']
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\')

        # Assert
        self.assertEqual(result, None)
        cnn.logger.debug.assert_called_once_with(u'No content-type header for url %s' % url)
		
    @mock.patch('connection.logging', autospec=True)
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage_Error404OnDownload(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request, mock_logging):
        # Arrange
        url = 'http://a.com/img.png'
        mock_isfile.return_value = False
        mock_urlopen.side_effect = urllib2.HTTPError(url, 404, 'Not Found', None, None)
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\')

        # Assert
        self.assertEqual(result, None)
        cnn.logger.debug.assert_called_once_with(u'Error 404 on downloading from url %s, stopping download attempts' % url)
		
    @mock.patch('connection.logging', autospec=True)
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage_Error500OnDownload(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request, mock_logging):
        # Assert
        url = 'http://a.com/img.png'
        mock_isfile.return_value = False
        mock_urlopen.side_effect = urllib2.HTTPError(url, 500, 'Internal Server Error', None, None)
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\')

        # Assert
        self.assertEqual(result, None)
        cnn.logger.debug.assert_called_with(u'Exception on downloading attempt #3 from url %s' % url, exc_info = True)
        cnn.logger.warning.assert_called_once_with(u'Couldn\'t download image from url %s after 3 attempts' % url)
		
    @mock.patch('connection.logging', autospec=True)
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage_RandomErrorOnDownload(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request, mock_logging):
        # Arrange
        url = 'http://a.com/img.png'
        mock_isfile.return_value = False
        mock_urlopen.side_effect = RuntimeError('URGH!')
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\')

        # Assert
        self.assertEqual(result, None)
        cnn.logger.debug.assert_called_with(u'Exception on downloading attempt #3 from url %s' % url, exc_info = True)
        cnn.logger.warning.assert_called_once_with(u'Couldn\'t download image from url %s after 3 attempts' % url)
		
    @mock.patch('connection.logging', autospec=True)
    @mock.patch('connection.urllib2.Request', autospec=True)
    @mock.patch('connection.urllib2.urlopen', autospec=True)
    @mock.patch('connection.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.common.os.path.isfile', autospec=True)
    @mock.patch('connection.common.os.rename', autospec=True)
    @mock.patch('connection.open', create=True)
    def test_DownloadImage_ExtensionAndServerTypeMismatch(self, mock_open, mock_rename, mock_isfile, mock_common_create_path, mock_urlopen, mock_request, mock_logging):
        # Arrange
        url = 'http://a.com/img.jpg'
        mock_isfile.return_value = False
        responseHdrs = httplib.HTTPMessage(StringIO(""))
        responseHdrs["Content-Type"] = "image/png"
        mock_urlopen.return_value.read.side_effect = [b'0123456', b'']
        mock_urlopen.return_value.info.return_value = responseHdrs
        cnn = connection.Connection(1, 'Foo')

        # Act
        result = cnn.DownloadImage(url, 'a:\\b\\')

        # Assert
        self.assertEqual(result, u'a:\\b\\img (a.com).png')
		
	"""Technically speaking, we shouldn't be testing private methods of a class... but an extra unit test or two won't hurt"""
    def test___stripSensitiveInfoFromParams(self):
        # Arrange
        cnn = connection.Connection(1, 'Foo')

        # Act
        filteredParams = cnn._Connection__stripSensitiveInfoFromParams({'auth_challenge': 'foo', 'auth_response': 'bar', 'param1': 'baz'})

        # Assert
        self.assertEqual(filteredParams['auth_challenge'], cnn.secretWord)
        self.assertEqual(filteredParams['auth_response'], cnn.secretWord)
        self.assertEqual(filteredParams['param1'], 'baz')
		
    def test___stripSensitiveInfoFromHeaders(self):
        # Arrange
        cnn = connection.Connection(1, 'Foo')

        # Act
        filteredHeaders = cnn._Connection__stripSensitiveInfoFromHeaders({'X-Header': 'foo', 'Cookie': 'ljsession=abcde'})

        # Assert
        self.assertEqual(filteredHeaders['X-Header'], 'foo')
        self.assertEqual(filteredHeaders['Cookie'], 'ljsession=' + cnn.secretWord)

if __name__ == '__main__':
    unittest.main()