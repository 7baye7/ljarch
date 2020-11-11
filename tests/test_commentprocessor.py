#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
from xml.etree.ElementTree import fromstring, Element, tostring
import unittest
import mock
import datetime

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
import commentprocessor
import connection
import common

class CommentProcessorTestCase(unittest.TestCase):
    def test_GetCommentIndexToInsertAt_ReturnIndexZeroIfNoCommentsYet(self):
        # Arrange
        comment = fromstring('<comment id="1"/>')
        sameLevelComments = []
        settings = self.__getEnvironment(False)
        commPrc = commentprocessor.CommentProcessor(settings)

        # Act
        result = commPrc.GetCommentIndexToInsertAt(comment, sameLevelComments)

        # Assert
        self.assertEqual(result, 0)
		
    def test_GetCommentIndexToInsertAt_ReturnIndexBetweenOtherComments(self):
        # Arrange
        comment = fromstring('<comment id="3" />')
        sameLevelComments = [ fromstring('<comment id="1"/>'),
                              fromstring('<comment id="2"/>'),
                              fromstring('<comment id="18"/>')]
        settings = self.__getEnvironment(False)
        commPrc = commentprocessor.CommentProcessor(settings)

        # Act
        result = commPrc.GetCommentIndexToInsertAt(comment, sameLevelComments)

        # Assert
        self.assertEqual(result, 2) # xml enumeration starts with 0
		
    def test_GetCommentIndexToInsertAt_ReturnIndexAfterAllComments(self):
        # Arrange
        comment = fromstring('<comment id="18" />')
        sameLevelComments = [ fromstring('<comment id="1"/>'),
                              fromstring('<comment id="2"/>'),
                              fromstring('<comment id="4"/>')]
        settings = self.__getEnvironment(False)
        commPrc = commentprocessor.CommentProcessor(settings)

        # Act
        result = commPrc.GetCommentIndexToInsertAt(comment, sameLevelComments)

        # Assert
        self.assertEqual(result, 3) # xml enumeration starts with 0
		
    def test_GetCommentsInfo_InvalidInfoType(self):
        # Arrange
        settings = self.__getEnvironment(False)
        commPrc = commentprocessor.CommentProcessor(settings)

        # Act
        with self.assertRaises(ValueError) as assertEx:
            commPrc.GetCommentsInfo('abc', 'InvalidInfoType', 123)

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Invalid infoType InvalidInfoType, expected either META or BODY')
		
    @mock.patch('connection.Connection', autospec=True)
    def test_GetCommentsInfo_Info(self, mock_cnn):
        # Arrange
        settings = self.__getEnvironment(False)
        sessionToken = 'abc'
        startId = 123
        returnValue = u'<livejournal><maxid>1</maxid><comments><comment id="1" posterid="1"/></comments><usermaps><usermap id="1" user="abc"/></usermaps></livejournal>'
        mock_cnn.return_value.MakeRequest.return_value = returnValue
        commPrc = commentprocessor.CommentProcessor(settings)

        # Act
        result = commPrc.GetCommentsInfo(sessionToken, 'META', startId)

        # Assert
        self.assertEqual(tostring(result), tostring(fromstring(returnValue)))
        commPrc.e.cnn.MakeRequest.assert_called_with('%s/%s' % (settings['server'], settings['exportCommentsPage']),
                                            {'get': 'comment_meta', 'startid': startId },
                                            {'Cookie': 'ljsession=%s' % sessionToken },
                                            'GET')
											
    @mock.patch('connection.Connection', autospec=True)
    def test_GetCommentsInfo_Body(self, mock_cnn):
        # Arrange
        settings = self.__getEnvironment(False)
        sessionToken = 'abc'
        startId = 123
        returnValue = u'<livejournal><comments><comment id="1" jitemid="1" posterid="1"><body>Text.</body><date>2015-01-24T17:51:54Z</date></comment></comments></livejournal>'
        mock_cnn.return_value.MakeRequest.return_value = returnValue
        commPrc = commentprocessor.CommentProcessor(settings)

        # Act
        result = commPrc.GetCommentsInfo(sessionToken, 'BODY', startId)

        # Assert
        self.assertEqual(tostring(result), tostring(fromstring(returnValue)))
        commPrc.e.cnn.MakeRequest.assert_called_with('%s/%s' % (settings['server'], settings['exportCommentsPage']),
                                            {'get': 'comment_body', 'startid': startId },
                                            {'Cookie': 'ljsession=%s' % sessionToken },
                                            'GET')
											
    def test_AddUpdateCommentsInPostXml_AddNewCommentToPostWithoutComments(self):
        # Arrange
        postXml = fromstring('<post><itemid>1</itemid></post>')
        newOrUpdatedComments = [fromstring('<comment id="1" jitemid="1" processingstate="new"/>')]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        commPrc.AddUpdateCommentsInPostXml(postXml, newOrUpdatedComments)

        # Assert
        self.assertTrue(postXml.find('comments/comment[@id="1"]') is not None)
        self.assertTrue(postXml.find('comments/comment[@id="1"][@processingstate]') is None)
		
    def test_AddUpdateCommentsInPostXml_AddNewCommentOnParentLevelToPostWithComments(self):
        # Arrange
        postXml = self.__getPostXml()
        newOrUpdatedComments = [fromstring('<comment id="3" jitemid="1" processingstate="new"/>')]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        commPrc.AddUpdateCommentsInPostXml(postXml, newOrUpdatedComments)

        # Assert
        self.assertTrue(postXml.find('comments/comment[@id="3"]') is not None)
        self.assertTrue(postXml.find('comments/comment[@id="3"][@processingstate]') is None)
        self.assertEqual(list(postXml.find('comments')).index(newOrUpdatedComments[0]), 1)
		
    """Technically this case should not even happen because comments seem to be sorted by id and an older id always comes first and goes into post first"""
    def test_AddUpdateCommentsInPostXml_AddNewCommentOnParentLevelToPostWithCommentsEarlierThanOtherComments(self):
        # Arrange
        postXml = self.__getPostXml()
        newOrUpdatedComments = [fromstring('<comment id="0" jitemid="1" processingstate="new"/>')]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        commPrc.AddUpdateCommentsInPostXml(postXml, newOrUpdatedComments)

        # Assert
        self.assertTrue(postXml.find('comments/comment[@id="0"]') is not None)
        self.assertTrue(postXml.find('comments/comment[@id="0"][@processingstate]') is None)
        self.assertEqual(list(postXml.find('comments')).index(newOrUpdatedComments[0]), 0)
		
    def test_AddUpdateCommentsInPostXml_AddNewCommentOnChildLevel(self):
        # Arrange
        postXml = self.__getPostXml()
        newOrUpdatedComments = [fromstring('<comment id="3" jitemid="1" parentid="2" processingstate="new"/>')]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        commPrc.AddUpdateCommentsInPostXml(postXml, newOrUpdatedComments)

        # Assert
        self.assertTrue(postXml.find('comments/comment/comments/comment/comments/comment[@id="3"]') is not None)
        self.assertTrue(postXml.find('comments/comment/comments/comment/comments/comment[@id="3"][@processingstate]') is None)
		
    def test_AddUpdateCommentsInPostXml_UpdateComment(self):
        # Arrange
        postXml = self.__getPostXml()
        newOrUpdatedComments = [fromstring('<comment id="2" jitemid="1" parentid="1" processingstate="updated"><body>Comment 2 updated</body></comment>')]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        commPrc.AddUpdateCommentsInPostXml(postXml, newOrUpdatedComments)

        # Assert
        self.assertEqual(postXml.find('comments/comment/comments/comment[@id="2"]/body').text, 'Comment 2 updated')
        self.assertTrue(postXml.find('comments/comment/comments/comment[@id="2"][@processingstate]') is None)
		
    def test_AddUpdateCommentsInPostXml_NoCommentToUpdate(self):
        # Arrange
        postXml = self.__getPostXml()
        commentId = '100'
        newOrUpdatedComments = [fromstring('<comment id="%s" jitemid="1" parentid="1" processingstate="updated"></comment>' % commentId)]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        with self.assertRaises(RuntimeError) as assertEx:
            commPrc.AddUpdateCommentsInPostXml(postXml, newOrUpdatedComments)

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Found no comment with id = %s to update in post with url = %s' % (commentId, postXml.find('url').text))
		
    def test_RemoveDeletedCommentsMetadata(self):
        # Arrange
        cachedCommentsMetadataXml = fromstring('<comments><comment id="1" /><comment id="2" /></comments>')
        existingCommentIds = ['2']
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.RemoveDeletedCommentsMetadata(cachedCommentsMetadataXml, existingCommentIds)

        # Assert
        self.assertEqual(result, 1)
        self.assertTrue(cachedCommentsMetadataXml.find('comment[@id="1"]') is None)
        self.assertTrue(cachedCommentsMetadataXml.find('comment[@id="2"]') is not None)
		
    def test_RemoveDeletedCommentsMetadata_AllIdsPresent(self):
        # Arrange
        cachedCommentsMetadataXml = fromstring('<comments><comment id="1" /><comment id="2" /></comments>')
        existingCommentIds = ['2', '1']
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.RemoveDeletedCommentsMetadata(cachedCommentsMetadataXml, existingCommentIds)

        # Assert
        self.assertEqual(result, 0)
        self.assertTrue(cachedCommentsMetadataXml.find('comment[@id="1"]') is not None)
        self.assertTrue(cachedCommentsMetadataXml.find('comment[@id="2"]') is not None)
		
    def test_RemoveDeletedCommentsMetadata_NoCachedMetadata(self):
        # Arrange
        cachedCommentsMetadataXml = fromstring('<comments/>')
        existingCommentIds = ['2']
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.RemoveDeletedCommentsMetadata(cachedCommentsMetadataXml, existingCommentIds)

        # Assert
        self.assertEqual(result, 0)
		
    def test_CombineCommentBodiesWithMetadata(self):
        # Arrange
        env = self.__getEnvironment(False)
        commPrc = commentprocessor.CommentProcessor(env)

        # Act
        result = commPrc.CombineCommentBodiesWithMetadata(self.__getBodies(), self.__getMetadata())

        # Assert
        self.assertEqual(result['maxCommentId'], 3)
        self.assertEqual(len(result['enrichedComments']), 2)
        self.assertEqual(len([enrichedComment for enrichedComment in result['enrichedComments'] if 'poster_name' in enrichedComment.attrib]), 2)
        self.assertEqual(len([enrichedComment for enrichedComment in result['enrichedComments'] if 'poster_url' in enrichedComment.attrib]), 2)
        self.assertEqual(len([datetime.datetime.strptime(enrichedComment.find('date').text, env['dateFormatString']) for enrichedComment in result['enrichedComments']]), 2)
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_GetNewOrUpdatedComments_NewNoState(self, mock_open, mock_createpath, mock_readxmlordefault, mock_logging):
        # Arrange
        commentText = 'Text.'
        commentTextHash = common.MD5(commentText)
        mock_readxmlordefault.return_value = fromstring('<comments/>')
        commentBodies = [fromstring('<comment id="12" jitemid="23" posterid="34" parentid="45"><body>%s</body><date>2015-01-09 23:51:22</date></comment>' % commentText)]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.GetNewOrUpdatedComments(0, commentBodies)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].attrib['processingstate'], 'new')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(fromstring('<comments><comment subjectbodyhash="%s" id="12" state="A" date="2015-01-09 23:51:22"/></comments>' % commentTextHash)))
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_GetNewOrUpdatedComments_BodyUpdated(self, mock_open, mock_createpath, mock_readxmlordefault, mock_logging):
        # Arrange
        initialCommentBodyHash = common.MD5('AAA')
        updatedCommentBody = 'AAB'
        updatedCommentBodyHash = common.MD5(updatedCommentBody)
        mock_readxmlordefault.return_value = fromstring('<comments><comment id="12" state="A" date="2015-01-09 23:51:22" subjectbodyhash="%s"/></comments>' % initialCommentBodyHash)
        commentBodies = [fromstring('<comment id="12" jitemid="23" posterid="34" parentid="45"><body>%s</body><date>2015-01-09 23:51:22</date></comment>' % updatedCommentBody)]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.GetNewOrUpdatedComments(0, commentBodies)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].attrib['processingstate'], 'updated')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(fromstring('<comments><comment id="12" state="A" date="2015-01-09 23:51:22" subjectbodyhash="%s"/></comments>' % updatedCommentBodyHash)))
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_GetNewOrUpdatedComments_SubjectUpdated(self, mock_open, mock_createpath, mock_readxmlordefault, mock_logging):
        # Arrange
        body = u'ЖЗЙ'
        initialCommentSubjectBodyHash = common.MD5(u'АБВ%s' % body)
        updatedCommentSubject = u'ЭЮЯ'
        updatedCommentSubjectBodyHash = common.MD5(u'%s%s' % (updatedCommentSubject, body))
        mock_readxmlordefault.return_value = fromstring(u'<comments><comment id="12" state="A" date="2015-01-09 23:51:22" subjectbodyhash="%s"/></comments>' % initialCommentSubjectBodyHash)
        commentBodiesString = u'<comment id="12" jitemid="23" posterid="34" parentid="45"><subject>%s</subject><body>%s</body><date>2015-01-09 23:51:22</date></comment>' % (updatedCommentSubject, body)
        commentBodies = [fromstring(commentBodiesString.encode('utf-8'))]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.GetNewOrUpdatedComments(0, commentBodies)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].attrib[u'processingstate'], u'updated')
        file_handle = mock_open.return_value.__enter__.return_value
        expectedCommentBodiesString = u'<comments><comment id="12" state="A" date="2015-01-09 23:51:22" subjectbodyhash="%s"/></comments>' % updatedCommentSubjectBodyHash
        file_handle.write.assert_called_with(tostring(fromstring(expectedCommentBodiesString.encode('utf-8'))))
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_GetNewOrUpdatedComments_NewHasState(self, mock_open, mock_createpath, mock_readxmlordefault, mock_logging):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<comments/>')
        commentBodies = [fromstring('<comment id="12" jitemid="23" posterid="34" parentid="45" state="D"></comment>')]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.GetNewOrUpdatedComments(0, commentBodies)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].attrib['processingstate'], 'new')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(fromstring('<comments><comment id="12" state="D"/></comments>')))
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_GetNewOrUpdatedComments_DateUpdated(self, mock_open, mock_createpath, mock_readxmlordefault, mock_logging):
        # Arrange
        commentText = 'Text.'
        commentTextHash = common.MD5(commentText)
        mock_readxmlordefault.return_value = fromstring('<comments><comment id="12" state="A" date="2015-01-09 23:51:22"/></comments>')
        commentBodies = [fromstring('<comment id="12" jitemid="23" posterid="34" parentid="45"><body>%s</body><date>2015-02-09 23:51:22</date></comment>' % commentText)]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.GetNewOrUpdatedComments(0, commentBodies)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].attrib['processingstate'], 'updated')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(fromstring('<comments><comment subjectbodyhash="%s" id="12" state="A" date="2015-02-09 23:51:22"/></comments>' % commentTextHash)))
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_GetNewOrUpdatedComments_Deleted(self, mock_open, mock_createpath, mock_readxmlordefault, mock_logging):
        # Arrange
        commentText1 = 'Text.'
        commentTextHash1 = common.MD5(commentText1)
        commentTextHash2 = common.MD5('Text2.')
        mock_readxmlordefault.return_value = fromstring('<comments><comment id="12" state="A" date="2015-01-09 23:51:22" subjectbodyhash="%s"/><comment id="23" state="A" date="2015-02-09 23:51:22" subjectbodyhash="%s"/></comments>' % (commentTextHash1, commentTextHash2))
        commentBodies = [fromstring('<comment id="12" jitemid="23" posterid="34" parentid="45"><body>%s</body><date>2015-01-09 23:51:22</date></comment>' % commentText1)]
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.GetNewOrUpdatedComments(0, commentBodies)

        # Assert
        self.assertEqual(len(result), 0)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(fromstring('<comments><comment id="12" state="A" date="2015-01-09 23:51:22" subjectbodyhash="%s"/></comments>' % commentTextHash1)))
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    @mock.patch('commentprocessor.time', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_MergeUserIdsMapXmlWithCache_NormalUser(self, mock_open, mock_time, mock_cnn, mock_createpath, mock_readxml, mock_logging):
        # Arrange
        mock_readxml.return_value = fromstring('<usermaps/>')
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.MergeUserIdsMapXmlWithCache(fromstring('<usermaps><usermap user="abc" id="12"/></usermaps>'))

        # Assert
        expectedResult = tostring(fromstring('<usermaps><usermap user="abc" id="12"/></usermaps>'))
        self.assertEqual(tostring(result), expectedResult)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(expectedResult)

    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    @mock.patch('commentprocessor.time', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_MergeUserIdsMapXmlWithCache_ExtUser(self, mock_open, mock_time, mock_cnn, mock_createpath, mock_readxml, mock_logging):
        # Arrange
        mock_readxml.return_value = fromstring('<usermaps/>')
        mock_cnn.return_value.MakeRequest.return_value = u'<html><head><title>realname - Profile</title></head><body>Text</body></html>'
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.MergeUserIdsMapXmlWithCache(fromstring('<usermaps><usermap user="ext_12345" id="23"/></usermaps>'))

        # Assert
        expectedResult = tostring(fromstring('<usermaps><usermap user="ext_12345" id="23" real_name="realname"/></usermaps>'))
        self.assertEqual(tostring(result), expectedResult)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(expectedResult)
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    @mock.patch('commentprocessor.time', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_MergeUserIdsMapXmlWithCache_ExtUserRaisesException(self, mock_open, mock_time, mock_cnn, mock_createpath, mock_readxml, mock_logging):
        # Arrange
        mock_readxml.return_value = fromstring('<usermaps/>')
        mock_cnn.return_value.MakeRequest.side_effect = RuntimeError(u'URGH!')
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.MergeUserIdsMapXmlWithCache(fromstring('<usermaps><usermap user="ext_12345" id="23"/></usermaps>'))

        # Assert
        expectedResult = tostring(fromstring('<usermaps><usermap user="ext_12345" id="23"/></usermaps>'))
        self.assertEqual(tostring(result), expectedResult)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(expectedResult)
        commPrc.logger.warning.assert_called_with(u'Couldn\'t get profile page of OpenID user ext_12345', exc_info = True)
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    @mock.patch('commentprocessor.time', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_MergeUserIdsMapXmlWithCache_ExtUserInvalidUserPageTitle(self, mock_open, mock_time, mock_cnn, mock_createpath, mock_readxml, mock_logging):
        # Arrange
        mock_readxml.return_value = fromstring('<usermaps/>')
        mock_cnn.return_value.MakeRequest.return_value = u'<html><head><notitle/></head><body>Text</body></html>'
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.MergeUserIdsMapXmlWithCache(fromstring('<usermaps><usermap user="ext_12345" id="23"/></usermaps>'))

        # Assert
        expectedResult = tostring(fromstring('<usermaps><usermap user="ext_12345" id="23"/></usermaps>'))
        self.assertEqual(tostring(result), expectedResult)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(expectedResult)
        commPrc.logger.warning.assert_called_with(u'Got profile page of OpenID user ext_12345 but couldn\'t find its title to extract user\'s "real" name from it')
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    @mock.patch('commentprocessor.time', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_MergeUserIdsMapXmlWithCache_ExtUserTitleWithoutDash(self, mock_open, mock_time, mock_cnn, mock_createpath, mock_readxml, mock_logging):
        # Arrange
        mock_readxml.return_value = fromstring('<usermaps/>')
        mock_cnn.return_value.MakeRequest.return_value = u'<html><head><title>realname</title></head><body>Text</body></html>'
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.MergeUserIdsMapXmlWithCache(fromstring('<usermaps><usermap user="ext_12345" id="23"/></usermaps>'))

        # Assert
        expectedResult = tostring(fromstring('<usermaps><usermap user="ext_12345" id="23" real_name="realname"/></usermaps>'))
        self.assertEqual(tostring(result), expectedResult)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(expectedResult)
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    @mock.patch('commentprocessor.time', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_MergeUserIdsMapXmlWithCache_DeletedUser(self, mock_open, mock_time, mock_cnn, mock_createpath, mock_readxml, mock_logging):
        # Arrange
        mock_readxml.return_value = fromstring('<usermaps><usermap user="abc" id="12"/><usermap user="ext_12345" id="23" real_name="realname"/></usermaps>')
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))

        # Act
        result = commPrc.MergeUserIdsMapXmlWithCache(fromstring('<usermaps><usermap user="ext_12345" id="23"/></usermaps>'))

        # Assert
        expectedResult = tostring(fromstring('<usermaps><usermap user="ext_12345" id="23" real_name="realname"/></usermaps>'))
        self.assertEqual(tostring(result), expectedResult)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(expectedResult)
		
    @mock.patch('commentprocessor.logging.getLogger', autospec=True)
    @mock.patch('commentprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('commentprocessor.open', create=True)
    def test_ProcessCommentsPage(self, mock_open, mock_readxmlordefault, mock_logging):
        # Arrange
        commPrc = commentprocessor.CommentProcessor(self.__getEnvironment(False))
        with mock.patch.object(commPrc, 'GetCommentsInfo') as mock_getcommentsinfo:
            with mock.patch.object(commPrc, 'CombineCommentBodiesWithMetadata') as mock_combinecomments:
                with mock.patch.object(commPrc, 'GetNewOrUpdatedComments') as mock_getneworupdated:
                    mock_getneworupdated.return_value = [fromstring('<comment id="12" jitemid="23" posterid="34" processingstate="updated"><body>Text.</body><date>2015-01-09 23:51:22</date></comment>'),
                                                         fromstring('<comment id="13" jitemid="23" posterid="34" parentid="12" processingstate="new"><body>Text 2.</body><date>2015-01-09 23:51:22</date></comment>')]

                    mock_readxmlordefault.side_effect = [fromstring('<posts><post dbid="23" publicid="123"/><post dbid="24" publicid="124"/></posts>'),
                                     fromstring('<post><url>http://a.bcd/123.html</url><comments><comment id="12" jitemid="23" posterid="34"><body>Text.</body><date>2011-01-09 23:51:22</date></comment></comments></post>')]

                    # Act
                    commPrc.ProcessCommentsPage('abc', 0, fromstring('<metadata/>'))

                    # Assert
                    expectedResult = common.PrettyPrintXml(fromstring('<post>' +
                                                         '<url>http://a.bcd/123.html</url>' +
                                                         '<comments>' +
                                                             '<comment id="12" jitemid="23" posterid="34">' +
                                                                 '<body>Text.</body>' +
                                                                 '<date>2015-01-09 23:51:22</date>' +
                                                                 '<comments>' +
                                                                     '<comment id="13" jitemid="23" posterid="34" parentid="12">' +
                                                                         '<body>Text 2.</body>' +
                                                                         '<date>2015-01-09 23:51:22</date>' +
                                                                     '</comment>' +
                                                                 '</comments>' +
                                                             '</comment>' +
                                                         '</comments>' +
                                                     '</post>'), None)
                    file_handle = mock_open.return_value.__enter__.return_value
                    file_handle.write.assert_called_with(expectedResult)


    def __getEnvironment(self, applyXSLT):
         return {'cnn': connection.Connection(1, 'Foo'),
                    'passwordHash': 'abc',
                    'sectionName': 'A',
                    'journal': 'B',
                    'server': 'http://a.bcd',
                    'serverSchema': 'http',
                    'serverNetloc': 'a.bcd',
                    'applyXSLT': applyXSLT,
                    'exportCommentsPage': 'a.html',
                    'delay': 1,
                    'cachedDataFolder': 'cacheddatafolder',
                    'cachedPostIdsFile': 'cachedPostIdsFile.xml',
                    'xsltFile': 'xsltFile.xml',
                    'dateFormatString': '%Y-%m-%d %H:%M:%S'                    
                }
				
    def __getPostXml(self):
        return fromstring('<post>' +
                                 '<itemid>1</itemid>' +
                                 '<url>http://a.bcd/1234.html</url>' +
                                 '<comments>' +
                                     '<comment id="1" jitemid="1">' +
                                         '<body>Comment 1</body>' +
                                         '<comments>' +
                                             '<comment id="2" jitemid="1" parentid="1">' +
                                                 '<body>Comment 2</body>' +
                                             '</comment>' +
                                         '</comments>'
                                     '</comment>' +
                                 '</comments>' +
                             '</post>')
							 
    def __getMetadata(self):
        return fromstring('<livejournal>' +
                              '<maxid>3</maxid>' +
                              '<comments>' +
                                  '<comment id="1" posterid="2"/>' +
                                  '<comment id="2" posterid="1"/>' +
                                  '<comment id="3" posterid="2" state="D"/>' +
                                  '<comment id="4" posterid="1"/>' +
                                '</comments>' +
                              '<usermaps>' +
                                  '<usermap id="1" user="abc"/>' +
                                  '<usermap id="2" user="ext_123" real_name="xyz"/>' +
                              '</usermaps>' +
                          '</livejournal>')
						  
    def __getBodies(self):
        return fromstring('<livejournal>' +
                              '<comments>' +
                                  '<comment id="1" jitemid="0" posterid="2" parentid="2">' +
                                      '<body>Text</body>' +
                                      '<date>2015-01-24T17:51:54Z</date>' +
                                  '</comment>' +
                                  '<comment id="2" jitemid="1" posterid="1">' +
                                      '<body>Text 1</body>' +
                                      '<date>2015-01-24T17:51:54Z</date>' +
                                  '</comment>' +
                                  '<comment id="3" jitemid="1" posterid="2" parentid="2">' +
                                      '<body>Text 2</body>' +
                                      '<date>2015-01-24T17:51:54Z</date>' +
                                  '</comment>' +
                                '</comments>' +
                            '</livejournal>')

if __name__ == '__main__':
    unittest.main()