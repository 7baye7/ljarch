import os
import sys
import unittest
import mock
import datetime
from collections import OrderedDict
from xml.etree.ElementTree import fromstring, Element, tostring

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
import postprocessor
import connection
import common

class PostProcessorTestCase(unittest.TestCase):
    def test_UnquotePlus(self):
        # Arrange
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        result = postPrc.UnquotePlus(u'%E6%AD%BB+%E5%88%91')
        
        # Assert
        self.assertEqual(result, u'\u6b7b \u5211')
		
    def test_TransformTaglist(self):
        # Arrange
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        result = postPrc.TransformTaglist(u'\u6b7b\u5211, \u91ce\u9f20')

        # Assert
        tags = result.findall('tag')
        self.assertEqual(len(tags), 2)
        self.assertEqual(tags[0].text, u'\u6b7b\u5211')
        self.assertEqual(tags[1].text, u'\u91ce\u9f20')
		
    def test_TransformTaglist_EmptyTagString(self):
        # Arrange
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        result = postPrc.TransformTaglist(None)

        # Assert
        self.assertEqual(len(result.findall('tag')), 0)
		
    def test_GetPublicPostId(self):
        # Arrange
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        result = postPrc.GetPublicPostId({'events_101_itemid': '1', 'events_101_anum': '2'})

        # Assert
        self.assertEqual(result, 258)
		
    def test_GetPublicPostId_NoItemid(self):
        # Arrange
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        with self.assertRaises(ValueError) as assertEx:
            postPrc.GetPublicPostId({'abc': '1', 'events_101_anum': '2'})

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Could not get itemid from post data')

    def test_GetPublicPostId_NoAnum(self):
        # Arrange
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        with self.assertRaises(ValueError) as assertEx:
            postPrc.GetPublicPostId({'events_101_itemid': '1', 'abc': '2'})

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Could not get anum from post data')
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.os.path.exists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_GetLastSyncDate(self, mock_open, mock_pathexists, mock_logging):
        # Arrange
        mock_pathexists.return_value = True
        lastSyncDate = '2015-01-27 23:50:59'
        mock_open.side_effect = [mock.mock_open(read_data=lastSyncDate).return_value]
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        result = postPrc.GetLastSyncDate()

        # Assert
        self.assertEqual(result, datetime.datetime.strptime(lastSyncDate, env['dateFormatString']))
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.os.path.exists', autospec=True)
    def test_GetLastSyncDate_NoFile(self, mock_pathexists, mock_logging):
        # Arrange
        mock_pathexists.return_value = False
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        result = postPrc.GetLastSyncDate()

        # Assert
        self.assertEqual(result, postPrc.minSyncDate)
        postPrc.logger.debug.assert_called_once_with(u'Didn\'t find file %s, returning default sync date' %
                                                     os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'], env['cachedDataFolder'], postPrc.lastSyncFileName))
													 
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_SaveLastSyncDate(self, mock_open, mock_common):
        # Arrange
        lastSyncDate = datetime.datetime(2015, 1, 27, 23, 50, 59)
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        postPrc.SaveLastSyncDate(lastSyncDate)

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(lastSyncDate.strftime(env['dateFormatString']))
		
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.os.path.exists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_CopyStylesheetToJournalFolder_StylesheetDoesNotExistInJournalFolder(self, mock_open, mock_pathexists, mock_common):
        # Arrange
        mock_pathexists.side_effect = [True, False]
        data = 'abc'
        fileToRead = mock.mock_open(read_data=data).return_value
        fileToWrite = mock.mock_open().return_value
        mock_open.side_effect = [fileToRead, fileToWrite]
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act 
        postPrc.CopyStylesheetToJournalFolder()

        # Assert
        file_handle = fileToWrite.__enter__.return_value
        file_handle.write.assert_called_with(data)
		
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.os.path.getmtime', autospec=True)
    @mock.patch('postprocessor.os.path.exists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_CopyStylesheetToJournalFolder_StylesheetExistsInJournalFolderButMainStylesheetWasModified(self, mock_open, mock_pathexists, mock_getmtime, mock_common):
        # Arrange
        mock_pathexists.side_effect = [True, True]
        mock_getmtime.side_effect = [2.3, 1.2]
        data = 'abc'
        fileToRead = mock.mock_open(read_data=data).return_value
        fileToWrite = mock.mock_open().return_value
        mock_open.side_effect = [fileToRead, fileToWrite]
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.CopyStylesheetToJournalFolder()

        # Assert
        file_handle = fileToWrite.__enter__.return_value
        file_handle.write.assert_called_with(data)
		
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.os.path.getmtime', autospec=True)
    @mock.patch('postprocessor.os.path.exists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_CopyStylesheetToJournalFolder_StylesheetExistsInJournalFolderAndMainStylesheetWasNotModified(self, mock_open, mock_pathexists, mock_getmtime, mock_common):
        # Arrange
        mock_pathexists.side_effect = [True, True]
        mock_getmtime.side_effect = [2.3, 2.5]
        data = 'abc'
        fileToRead = mock.mock_open(read_data=data).return_value
        fileToWrite = mock.mock_open().return_value
        mock_open.side_effect = [fileToRead, fileToWrite]
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.CopyStylesheetToJournalFolder()

        # Assert
        file_handle = fileToWrite.__enter__.return_value
        self.assertFalse(file_handle.write.called)
		
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.os.path.exists', autospec=True)
    def test_CopyStylesheetToJournalFolder_MainStylesheetDoesNotExist(self, mock_pathexists, mock_common):
        # Arrange
        mock_pathexists.side_effect = [False]
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with self.assertRaises(IOError) as assertEx:
            postPrc.CopyStylesheetToJournalFolder()

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'XSLT stylesheet is not found, expected path is %s'
                         % os.path.join(os.getcwdu(), env['xsltFile']))
		
    def test_FlatPostDataToXmlObject(self):
        # Arrange
        generator = 'Foo'
        postData = OrderedDict()
        postData[u'events_1_anum'] = u'1'
        postData[u'events_1_event'] = u'%E6%AD%BB+%E5%88%91'
        postData[u'events_1_eventtime'] = u'2015-01-28 03:12:00'
        postData[u'events_1_itemid'] = u'2'
        postData[u'events_1_subject'] = u'\u6b7b\u5211'
        postData[u'events_1_url'] = u'http://a.bcd/1234.html'
        postData[u'events_1_logtime'] = u'2015-01-28 03:12:00' # exclude
        postData[u'events_1_test_event_prop'] = u'abc' # exclude
        postData[u'prop_1_name'] = u'current_mood'
        postData[u'prop_1_value'] = u'URGH!'
        postData[u'prop_2_name'] = u'current_music'
        postData[u'prop_2_value'] = u'A - BCD.mp3'
        postData[u'prop_3_name'] = u'taglist'
        postData[u'prop_3_value'] = u'\u6b7b\u5211, \u6b7b\u5211'
        postData[u'prop_4_name'] = u'current_moodid' # exclude
        postData[u'prop_4_value'] = u'123'
        postData[u'prop_5_name'] = u'test_prop_prop' # exclude
        postData[u'prop_5_value'] = u'234'
        env = self.__getEnvironment(True, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        result = postPrc.FlatPostDataToXmlObject(postData)

        # Assert
        self.assertEqual(tostring(result), u'<post>' +
                '<generator>' + generator + '</generator>' +
                '<source>' + env['serverNetloc'] + '</source>' +
                '<source_schema>' + env['serverSchema'] + '</source_schema>' +
                '<source_shortname>' + env['sectionName'] + '</source_shortname>' +
                '<author>' + env['journal'] + '</author>' +
                '<author_url>http://B.a.bcd</author_url>' +
                '<anum>1</anum>' +
                '<event>' + self.__unicodeToHtml(u'\u6b7b \u5211') + '</event>' +
                '<eventtime>2015-01-28 03:12:00</eventtime>' +
                '<itemid>2</itemid>' +
                '<subject>' + self.__unicodeToHtml(u'\u6b7b\u5211') + '</subject>' +
                '<url>http://a.bcd/1234.html</url>' +
                '<current_mood>URGH!</current_mood>' +
                '<current_music>A - BCD.mp3</current_music>' +
                '<taglist>' +
                    '<tag>' + self.__unicodeToHtml(u'\u6b7b\u5211') + '</tag>' +
                    '<tag>' + self.__unicodeToHtml(u'\u6b7b\u5211') + '</tag>' +
                '</taglist>' +
            '</post>')
			
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_SavePostToFile_OldFileExistsAndThereAreCommentsInIt(self, mock_open, mock_createpath, mock_readxmlfileordefault):
        # Arrange
        oldPostComments = fromstring('<post><comments><comment>1</comment></comments></post>')
        mock_readxmlfileordefault.return_value = oldPostComments
        postData = OrderedDict()
        postData[u'events_1_anum'] = u'1'
        postData[u'prop_1_name'] = u'current_mood'
        postData[u'prop_1_value'] = u'URGH!'
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.SavePostToFile(postData, '1234.xml')

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        xmlToCheckAgainst = postPrc.FlatPostDataToXmlObject(postData)
        common.CreateXmlElement('comments', oldPostComments.find('comments'), xmlToCheckAgainst) # add comments to xml to check against
        file_handle.write.assert_called_with(common.PrettyPrintXml(xmlToCheckAgainst, None))
		
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_SavePostToFile_OldFileExistsButThereAreNoCommentsInIt(self, mock_open, mock_createpath, mock_readxmlfileordefault):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<post/>')
        postData = OrderedDict()
        postData[u'events_1_anum'] = u'1'
        postData[u'prop_1_name'] = u'current_mood'
        postData[u'prop_1_value'] = u'URGH!'
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.SavePostToFile(postData, '1234.xml')

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(common.PrettyPrintXml(postPrc.FlatPostDataToXmlObject(postData), None))
		
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_SavePostToFile_OldFileDoesNotExist(self, mock_open, mock_createpath, mock_readxmlfileordefault):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<FileDoesNotExist/>')
        postData = OrderedDict()
        postData[u'events_1_anum'] = u'1'
        postData[u'prop_1_name'] = u'current_mood'
        postData[u'prop_1_value'] = u'URGH!'
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.SavePostToFile(postData, '1234.xml')

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(common.PrettyPrintXml(postPrc.FlatPostDataToXmlObject(postData), None))
		
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_SavePostToFile_ApplyXSLT(self, mock_open, mock_createpath, mock_readxmlfileordefault):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<FileDoesNotExist/>')
        postData = OrderedDict()
        postData[u'events_1_anum'] = u'1'
        postData[u'prop_1_name'] = u'current_mood'
        postData[u'prop_1_value'] = u'URGH!'
        env = self.__getEnvironment(True, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        postPrc.SavePostToFile(postData, '1234.xml')

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(common.PrettyPrintXml(postPrc.FlatPostDataToXmlObject(postData), env['xsltFile']))
		
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_SavePostIdsMap(self, mock_open, mock_createpath, mock_readxmlfileordefault):
        # Arrange
        cachedXml = fromstring('<posts><post dbid="1" publicid="123"/></posts>')
        mock_readxmlfileordefault.return_value = cachedXml
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.SavePostIdsMap({2: 234})

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(cachedXml, 'utf-8').encode('utf-8'))
		
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    def test_SavePostIdsMap_NoCachedPosts(self, mock_open, mock_createpath, mock_readxmlfileordefault):
        # Arrange
        cachedXml = fromstring('<posts/>')
        mock_readxmlfileordefault.return_value = cachedXml
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.SavePostIdsMap({2: 234})

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(cachedXml, 'utf-8').encode('utf-8'))
		
    @mock.patch('postprocessor.open', create=True)
    def test_SavePostIdsMap_EmptyMap(self, mock_open):
        # Arrange
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.SavePostIdsMap({})

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        self.assertFalse(file_handle.write.called)
		

    @mock.patch('connection.Connection', autospec=True)
    def test_GetPost(self, mock_cnn):
        # Arrange
        postData = OrderedDict()
        postData[u'events_1_anum'] = u'1'
        postData[u'events_1_event'] = u'%E6%AD%BB+%E5%88%91'
        mock_cnn.return_value.MakeServerRequestWithAuthentication.return_value = postData
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(True, False))

        # Act
        result = postPrc.GetPost(1)

        # Assert
        self.assertEqual(result, postData)
		
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    @mock.patch('postprocessor.os.remove', create=True)
    def test_UpdateFilesMapping(self, mock_osremove, mock_open, mock_common, mock_logging):
        # Arrange
        itemCacheFilePath = 'a:\\b\\c\\d.xml'
        itemCacheXml = fromstring('<item><item dbid="1" publicid="123"/></item>')
        itemsToDelete = ['234.xml', '345.xml']
        pathToItems = 'a:\\b'
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.UpdateFilesMapping(itemCacheFilePath, itemCacheXml, itemsToDelete, pathToItems, 'item')

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(itemCacheXml))
        mock_osremove.assert_any_call(os.path.join(pathToItems, itemsToDelete[0]))
        mock_osremove.assert_any_call(os.path.join(pathToItems, itemsToDelete[1]))
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    @mock.patch('postprocessor.os.remove', create=True)
    def test_UpdateFilesMapping_ForceMapRewrite(self, mock_osremove, mock_open, mock_common, mock_logging):
        # Arrange
        itemCacheFilePath = 'a:\\b\\c\\d.xml'
        itemCacheXml = fromstring('<item><item dbid="1" publicid="123"/></item>')
        itemsToDelete = []
        pathToItems = 'a:\\b'
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.UpdateFilesMapping(itemCacheFilePath, itemCacheXml, itemsToDelete, pathToItems, 'item', True)

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(tostring(itemCacheXml))
        self.assertFalse(mock_osremove.called)
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.CreatePathIfNotExists', autospec=True)
    @mock.patch('postprocessor.open', create=True)
    @mock.patch('postprocessor.os.remove', create=True)
    def test_UpdateFilesMapping_ItemsToDeleteEmptyAndNotForceMapRewrite(self, mock_osremove, mock_open, mock_common, mock_logging):
        # Arrange
        itemCacheFilePath = 'a:\\b\\c\\d.xml'
        itemCacheXml = fromstring('<item><item dbid="1" publicid="123"/></item>')
        itemsToDelete = []
        pathToItems = 'a:\\b'
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        postPrc.UpdateFilesMapping(itemCacheFilePath, itemCacheXml, itemsToDelete, pathToItems, 'item')

        # Assert
        file_handle = mock_open.return_value.__enter__.return_value
        self.assertFalse(file_handle.write.called)
        self.assertFalse(mock_osremove.called)
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    def test_RemoveDeletedPosts_RemovePostButNotItsImages(self, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.side_effect = [fromstring('<posts><post dbid="1" publicid="12" /><post dbid="2" publicid="23" /><post dbid="3" publicid="34" /></posts>'),
                                                 fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/><post dbid="2"/></posts></image>' +
                                                                '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/></posts></image>' +
                                                            '</images>')]
        syncItemsToCheckForDeletion = [{'id': 1}, {'id': 3}] # post with id = 2 was deleted on server
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            postPrc.RemoveDeletedPosts(syncItemsToCheckForDeletion)

            # Assert
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            name, args, kwargs = wrappedMethod.mock_calls[0]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], env['cachedPostIdsFile']))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<posts><post dbid="1" publicid="12" /><post dbid="3" publicid="34" /></posts>')))
            self.assertEqual(args[2], ['23.xml'])
            self.assertEqual(args[3], journalPath)
            self.assertEqual(args[4], 'post')

            name, args, kwargs = wrappedMethod.mock_calls[1]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="1"/></posts></image>' +
                                                                        '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="1"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    def test_RemoveDeletedPosts_RemovePostWithImages(self, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.side_effect = [fromstring('<posts><post dbid="1" publicid="12" /><post dbid="2" publicid="23" /><post dbid="3" publicid="34" /></posts>'),
                                                 fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/><post dbid="2"/></posts></image>' +
                                                                '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/></posts></image>' +
                                                            '</images>')]
        syncItemsToCheckForDeletion = [{'id': 2}, {'id': 3}] # post with id = 1 was deleted on server
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            postPrc.RemoveDeletedPosts(syncItemsToCheckForDeletion)

            # Assert
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            name, args, kwargs = wrappedMethod.mock_calls[0]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], env['cachedPostIdsFile']))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<posts><post dbid="2" publicid="23" /><post dbid="3" publicid="34" /></posts>')))
            self.assertEqual(args[2], ['12.xml'])
            self.assertEqual(args[3], journalPath)
            self.assertEqual(args[4], 'post')

            name, args, kwargs = wrappedMethod.mock_calls[1]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="2"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], ['img2 (a.bcd).jpg'])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    def test_RemoveDeletedPosts_RemovePostWithoutImages(self, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.side_effect = [fromstring('<posts><post dbid="1" publicid="12" /><post dbid="2" publicid="23" /><post dbid="3" publicid="34" /></posts>'),
                                                 fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/><post dbid="2"/></posts></image>' +
                                                                '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/></posts></image>' +
                                                            '</images>')]
        syncItemsToCheckForDeletion = [{'id': 1}, {'id': 2}] # post with id = 3 was deleted on server
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            postPrc.RemoveDeletedPosts(syncItemsToCheckForDeletion)

            # Assert
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            name, args, kwargs = wrappedMethod.mock_calls[0]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], env['cachedPostIdsFile']))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<posts><post dbid="1" publicid="12" /><post dbid="2" publicid="23" /></posts>')))
            self.assertEqual(args[2], ['34.xml'])
            self.assertEqual(args[3], journalPath)
            self.assertEqual(args[4], 'post')

            name, args, kwargs = wrappedMethod.mock_calls[1]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="1"/><post dbid="2"/></posts></image>' +
                                                                        '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="1"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], False)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    def test_RemoveDeletedPosts_RemoveMoreThanOnePost(self, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.side_effect = [fromstring('<posts><post dbid="1" publicid="12" /><post dbid="2" publicid="23" /><post dbid="3" publicid="34" /></posts>'),
                                                 fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/><post dbid="2"/></posts></image>' +
                                                                '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/></posts></image>' +
                                                            '</images>')]
        syncItemsToCheckForDeletion = [{'id': 2}] # posts with id = 1 and 3 was deleted on server
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            postPrc.RemoveDeletedPosts(syncItemsToCheckForDeletion)

            # Assert
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            name, args, kwargs = wrappedMethod.mock_calls[0]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], env['cachedPostIdsFile']))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<posts><post dbid="2" publicid="23" /></posts>')))
            self.assertEqual(args[2], ['12.xml', '34.xml'])
            self.assertEqual(args[3], journalPath)
            self.assertEqual(args[4], 'post')

            name, args, kwargs = wrappedMethod.mock_calls[1]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="2"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], ['img2 (a.bcd).jpg'])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    def test_RemoveDeletedPosts_DontRemoveAnything(self, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.side_effect = [fromstring('<posts><post dbid="1" publicid="12" /><post dbid="2" publicid="23" /><post dbid="3" publicid="34" /></posts>'),
                                                 fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/><post dbid="2"/></posts></image>' +
                                                                '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/></posts></image>' +
                                                            '</images>')]
        syncItemsToCheckForDeletion = [{'id': 1}, {'id': 2}, {'id': 3}] # nothing was deleted
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            postPrc.RemoveDeletedPosts(syncItemsToCheckForDeletion)

            # Assert
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            name, args, kwargs = wrappedMethod.mock_calls[0]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], env['cachedPostIdsFile']))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<posts><post dbid="1" publicid="12" /><post dbid="2" publicid="23" /><post dbid="3" publicid="34" /></posts>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], journalPath)
            self.assertEqual(args[4], 'post')

            name, args, kwargs = wrappedMethod.mock_calls[1]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/><post dbid="2"/></posts></image>' +
                                                                '<image remote="http://a.bcd/img2.jpg" local="img2 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="1"/></posts></image>' +
                                                            '</images>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], False)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    def test_RemoveDeletedPosts_NoCachedData(self, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.side_effect = [fromstring('<NoCachedInfo/>'),
                                                 fromstring('<images/>')]
        syncItemsToCheckForDeletion = [{'id': 1}, {'id': 2}, {'id': 3}] # new data
        env = self.__getEnvironment(False, False)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            postPrc.RemoveDeletedPosts(syncItemsToCheckForDeletion)

            # Assert
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            name, args, kwargs = wrappedMethod.mock_calls[0]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], env['cachedPostIdsFile']))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<NoCachedInfo/>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], journalPath)
            self.assertEqual(args[4], 'post')

            name, args, kwargs = wrappedMethod.mock_calls[1]
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images/>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], False)
			
    @mock.patch('postprocessor.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_GetSyncItems(self, mock_cnn, mock_time):
        # Arrange
        syncItems1 = OrderedDict()
        syncItems1['sync_1_item'] = 'L-12'
        syncItems1['sync_1_time'] = '2015-01-30 23:45:12'
        syncItems1['sync_2_item'] = 'L-23'
        syncItems1['sync_2_time'] = '2015-01-30 23:43:12'
        syncItems1['sync_count'] = '2'
        syncItems1['sync_total'] = '3'
        syncItems2 = OrderedDict()
        syncItems2['sync_1_item'] = 'L-34'
        syncItems2['sync_1_time'] = '2015-01-30 23:44:12'
        syncItems2['sync_count'] = '1'
        syncItems2['sync_total'] = '1'
        mock_cnn.return_value.MakeServerRequestWithAuthentication.side_effect = [syncItems1, syncItems2]
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, False))

        # Act
        result = postPrc.GetSyncItems(datetime.datetime(2015, 1, 1, 0, 0, 0))

        # Assert
        self.assertEqual([elem['id'] for elem in result], [23, 34, 12])
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_DownloadedImage(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images/>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '<img src="http://a.bcd/img1.jpg" data-local-src="images/img1 (a.bcd).jpg">',
            'downloadedImageInfos': [{'remote': 'http://a.bcd/img1.jpg', 'local': 'img1 (a.bcd).jpg'}],
            'existingImageInfos': []
            }
        env = self.__getEnvironment(False, True)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            result = postPrc.ScrapeImages('<img src="http://a.bcd/img1.jpg">', postId = '123')

            # Assert
            name, args, kwargs = wrappedMethod.mock_calls[0]
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="123"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_NoPostId(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images/>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '<img src="http://a.bcd/img1.jpg" data-local-src="images/img1 (a.bcd).jpg">',
            'downloadedImageInfos': [{'remote': 'http://a.bcd/img1.jpg', 'local': 'img1 (a.bcd).jpg'}],
            'existingImageInfos': []
            }
        postPrc = postprocessor.PostProcessor('Foo', self.__getEnvironment(False, True))

        # Act
        with self.assertRaises(ValueError) as assertEx:
            result = postPrc.ScrapeImages('<img src="http://a.bcd/img1.jpg">')

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Parameter postId not present in arguments list')
		
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_ExistingImage(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="123"/></posts></image>' +
                                                            '</images>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '<img src="http://a.bcd/img1.jpg" data-local-src="images/img1 (a.bcd).jpg">',
            'downloadedImageInfos': [],
            'existingImageInfos': [{'remote': 'http://a.bcd/img1.jpg', 'local': 'img1 (a.bcd).jpg'}]
            }
        env = self.__getEnvironment(False, True)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            result = postPrc.ScrapeImages('<img src="http://a.bcd/img1.jpg">', postId = '124')

            # Assert
            name, args, kwargs = wrappedMethod.mock_calls[0]
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="123"/><post dbid="124"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_ExistingImage_LinkedImage(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="123"/></posts></image>' +
                                                            '</images>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '<a href="http://a.bcd/img1_big.jpg"><img src="http://a.bcd/img1.jpg" data-local-src="images/img1 (a.bcd).jpg"></a>',
            'downloadedImageInfos': [],
            'existingImageInfos': [{'remote': 'http://a.bcd/img1.jpg', 'local': 'img1 (a.bcd).jpg', 'linkedRemote': 'http://a.bcd/img1_big.jpg', 'linkedLocal': 'img1_big (linked) (a.bcd).jpg'}]
            }
        env = self.__getEnvironment(False, True)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            result = postPrc.ScrapeImages('<a href="http://a.bcd/img1_big.jpg"><img src="http://a.bcd/img1.jpg"></a>', postId = '124')

            # Assert
            name, args, kwargs = wrappedMethod.mock_calls[0]
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg" linkedRemote="http://a.bcd/img1_big.jpg" linkedLocal="img1_big (linked) (a.bcd).jpg">' +
                                                                            '<posts><post dbid="123"/><post dbid="124"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_DeletedImageSinglePost(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="123"/></posts></image>' +
                                                            '</images>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '',
            'downloadedImageInfos': [],
            'existingImageInfos': []
            }
        env = self.__getEnvironment(False, True)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            result = postPrc.ScrapeImages('<img src="http://a.bcd/img1.jpg">', postId = '123')

            # Assert
            name, args, kwargs = wrappedMethod.mock_calls[0]
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images/>')))
            self.assertEqual(args[2], ['img1 (a.bcd).jpg'])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_DeletedImageSinglePost_NormalImageAndLinkedImage(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg" linkedRemote="http://a.bcd/img1_big.jpg" linkedLocal="img1_big (linked) (a.bcd).jpg">' +
                                                                    '<posts><post dbid="123"/></posts></image>' +
                                                            '</images>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '',
            'downloadedImageInfos': [],
            'existingImageInfos': []
            }
        env = self.__getEnvironment(False, True)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            result = postPrc.ScrapeImages('', postId = '123')

            # Assert
            name, args, kwargs = wrappedMethod.mock_calls[0]
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images/>')))
            self.assertEqual(args[2], ['img1 (a.bcd).jpg', 'img1_big (linked) (a.bcd).jpg'])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)


    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_DeletedImageSinglePost_OnlyLinkedImage(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg" linkedRemote="http://a.bcd/img1_big.jpg" linkedLocal="img1_big (linked) (a.bcd).jpg">' +
                                                                    '<posts><post dbid="123"/></posts></image>' +
                                                            '</images>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '<img src="http://a.bcd/img1.jpg" data-local-src="images/img1 (a.bcd).jpg">',
            'downloadedImageInfos': [],
            'existingImageInfos': [{'remote': 'http://a.bcd/img1.jpg', 'local': 'img1 (a.bcd).jpg'}]
            }
        env = self.__getEnvironment(False, True)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            result = postPrc.ScrapeImages('', postId = '123')

            # Assert
            name, args, kwargs = wrappedMethod.mock_calls[0]
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="123"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], ['img1_big (linked) (a.bcd).jpg'])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)
			
    @mock.patch('postprocessor.logging.getLogger', autospec=True)
    @mock.patch('postprocessor.common.ReadXmlFileOrDefault', autospec=True)
    @mock.patch('postprocessor.ImageScraper.ScrapeImages') # can't use autospec=True on @classmethod because of a bug: http://bugs.python.org/issue23078
    def test_ScrapeImages_DeletedImageMultiplePosts(self, mock_imagescraper, mock_readxmlfileordefault, mock_logging):
        # Arrange
        mock_readxmlfileordefault.return_value = fromstring('<images>' +
                                                                '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                    '<posts><post dbid="123"/><post dbid="124"/></posts></image>' +
                                                            '</images>')
        mock_imagescraper.return_value = {
            'updatedMarkup': '',
            'downloadedImageInfos': [],
            'existingImageInfos': []
            }
        env = self.__getEnvironment(False, True)
        postPrc = postprocessor.PostProcessor('Foo', env)

        # Act
        with mock.patch.object(postPrc, 'UpdateFilesMapping') as wrappedMethod:
            result = postPrc.ScrapeImages('<img src="http://a.bcd/img1.jpg">', postId = '123')

            # Assert
            name, args, kwargs = wrappedMethod.mock_calls[0]
            journalPath = os.path.join(common.GetUpperLevelDir(), env['sectionName'], env['journal'])
            self.assertEqual(args[0], os.path.join(journalPath, env['cachedDataFolder'], postPrc.cachedImagePathsFileName))
            self.assertEqual(tostring(args[1]), tostring(fromstring('<images>' +
                                                                        '<image remote="http://a.bcd/img1.jpg" local="img1 (a.bcd).jpg">' +
                                                                            '<posts><post dbid="124"/></posts></image>' +
                                                                    '</images>')))
            self.assertEqual(args[2], [])
            self.assertEqual(args[3], os.path.join(journalPath, postPrc.imagesFolder))
            self.assertEqual(args[4], 'image')
            self.assertEqual(args[5], True)


		
    def __getEnvironment(self, applyXSLT, archiveImages):
         return {'cnn': connection.Connection(1, 'Foo'),
                    'passwordHash': 'abc',
                    'sectionName': 'A',
                    'journal': 'B',
                    'server': 'http://a.bcd',
                    'serverSchema': 'http',
                    'serverNetloc': 'a.bcd',
                    'applyXSLT': applyXSLT,
                    'archiveImages': archiveImages,
                    'exportCommentsPage': 'a.html',
                    'delay': 1,
                    'cachedDataFolder': 'cacheddatafolder',
                    'cachedPostIdsFile': 'cachedPostIdsFile.xml',
                    'xsltFile': 'xsltFile.xml',
                    'dateFormatString': '%Y-%m-%d %H:%M:%S',
                    'eventPropertiesToExclude': ['test_event_prop'],
                    'propPropertiesToExclude': ['test_prop_prop']
                }
				
    def __unicodeToHtml(self, s):
        return s.encode('ascii', 'xmlcharrefreplace')

if __name__ == '__main__':    
    unittest.main()