import os
import sys
from xml.etree.ElementTree import fromstring, Element
import re
import unittest
import mock

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
import common

class CommonTestCase(unittest.TestCase):
    
    def test_MergeDicts(self):
        # Act
        mergedDict = common.MergeDicts({'a': 1}, {'b': 2})

        # Assert
        self.assertEqual(mergedDict, {'a': 1, 'b': 2})
		
    def test_MD5(self):
       # Act
       result = common.MD5('SECRET')

       # Assert
       self.assertEqual(result, '44c7be48226ebad5dca8216674cad62b')

    def test_SplitCommaSeparatedString(self):
        # Act
        result = common.SplitCommaSeparatedString(' a   , b , c,d,e, f ')

        # Assert
        self.assertEqual(result, ['a', 'b', 'c', 'd', 'e', 'f'])
		
    def test_PrettyPrintXml_NoSpaces(self):
        # Arrange
        root = fromstring('<a><b>cd</b></a>')

        # Act
        result = common.PrettyPrintXml(root, None)

        # Assert
        self.assertEqual(result, u'<?xml version="1.0" ?>\n<a>\n  <b>cd</b>\n</a>\n')
		
    def test_PrettyPrintXml_WithSpaces(self):
        # Arrange
        root = fromstring(' <a>    <b>cd</b>\n</a>')

        # Act
        result = common.PrettyPrintXml(root, None)

        # Assert
        self.assertEqual(result, u'<?xml version="1.0" ?>\n<a>\n  <b>cd</b>\n</a>\n')
		
    def test_PrettyPrintXml_WithXSLT(self):
        # Arrange
        root = fromstring('<a><b>cd</b></a>')
        xsltFileName = u'xlst.xslt'

        # Act
        result = common.PrettyPrintXml(root, xsltFileName)

        # Assert
        self.assertEqual(result, u'<?xml version="1.0" ?>\n<?xml-stylesheet type="text/xsl" href="%s"?>\n<a>\n  <b>cd</b>\n</a>\n' % xsltFileName)
		
    def test_CreateAuthorUrl(self):
        # Act
        result = common.CreateAuthorUrl(u'http', u'livejournal.com', u'example_user')

        # Assert
        self.assertEqual(result, u'http://example-user.livejournal.com')

    def test_CreateAuthorExtUrl(self):
        # Act
        result = common.CreateAuthorExtUrl(u'http://www.livejournal.com', u'12345')

        # Assert
        self.assertEqual(result, u'http://www.livejournal.com/profile?userid=12345&t=I')
		
    def test_IsNullOrWhiteSpace_Null(self):
        self.assertTrue(common.IsNullOrWhiteSpace(None))

    def test_IsNullOrWhiteSpace_Space(self):
        self.assertTrue(common.IsNullOrWhiteSpace(' \n  '))

    def test_IsNullOrWhiteSpace_String(self):
        self.assertFalse(common.IsNullOrWhiteSpace('a'))
		
    def test_FindDictValueByKeyRegex_Value(self):
        # Act
        result = common.FindDictValueByKeyRegex({'a_1_foo': 1, 'b_2_bar': 2}, re.compile('^\w+_\d+_bar$', re.I))

        # Assert
        self.assertEqual(result, 2)

    def test_FindDictValueByKeyRegex_None(self):
        # Act
        result = common.FindDictValueByKeyRegex({'a_1_foo': 1, 'b_2_bar': 2}, re.compile('^\w+_\d+_baz$', re.I))

        # Assert
        self.assertEqual(result, None)
		
    @mock.patch('common.logging')
    @mock.patch('common.os.path')
    @mock.patch('common.os')
    def test_CreatePathIfNotExists_NotExists(self, mock_os, mock_path, mock_logging):
        # Arrange
        path = 'a:\\b\\c.txt'
        dir = os.path.dirname(path)
        mock_path.exists.return_value = False
        mock_path.dirname.return_value = dir

        # Act
        common.CreatePathIfNotExists(path)

        # Assert
        mock_os.makedirs.assert_called_with(dir)
        mock_logging.getLogger.assert_called_with('log')
		
    @mock.patch('common.logging')
    @mock.patch('common.os.path')
    @mock.patch('common.os')
    def test_CreatePathIfNotExists_Exists(self, mock_os, mock_path, mock_logging):
        # Arrange
        mock_path.exists.return_value = True

        # Act
        common.CreatePathIfNotExists('a:\\b\\c.txt')

        # Assert
        self.assertFalse(mock_os.makedirs.called)
		
    def test_ReadXmlNodeOrDefault_ParentIsNone(self):
        # Act
        result = common.ReadXmlNodeOrDefault(None, 'a', 'default')

        # Assert
        self.assertEqual(result, 'default')

    def test_ReadXmlNodeOrDefault_NoChild(self):
        # Arrange
        root = fromstring('<a><b>bbb</b></a>')

        # Act
        result = common.ReadXmlNodeOrDefault(root, 'c', 'default')

        # Assert
        self.assertEqual(result, 'default')

    def test_ReadXmlNodeOrDefault_ChildValueEmpty(self):
        # Arrange
        root = fromstring('<a><b></b></a>')

        # Act
        result = common.ReadXmlNodeOrDefault(root, 'b', 'default')

        # Assert
        self.assertEqual(result, 'default')

    def test_ReadXmlNodeOrDefault_ChildValueNotEmpty(self):
        # Arrange
        root = fromstring('<a><b>bbb</b></a>')

        # Act
        result = common.ReadXmlNodeOrDefault(root, 'b', 'default')

        # Assert
        self.assertEqual(result, 'bbb')
		
    @mock.patch('common.os.path')
    def test_ReadXmlFileOrDefault_NoFile(self, mock_path):
        # Arrange
        mock_path.exists.return_value = False
        defaultTag = 'foo'

        # Act
        result = common.ReadXmlFileOrDefault('a:\\b\\c.xml', defaultTag).tag

        # Assert
        self.assertEqual(result, defaultTag)
		
    @mock.patch('common.os.path')
    @mock.patch('common.open', create=True)
    def test_ReadXmlFileOrDefault_FileExistsWithInvalidData(self, mock_open, mock_path):
        # Arrange
        mock_path.exists.return_value = True
        mock_open.side_effect = [mock.mock_open(read_data='abc').return_value]
        defaultTag = 'foo'

        # Act
        result = common.ReadXmlFileOrDefault('a:\\b\\c.xml', defaultTag).tag

        # Assert
        self.assertEqual(result, defaultTag)
		
    @mock.patch('common.os.path')
    @mock.patch('common.open', create=True)
    def test_ReadXmlFileOrDefault_FileExistsWithValidData(self, mock_open, mock_path):
        # Arrange
        mock_path.exists.return_value = True
        mock_open.side_effect = [mock.mock_open(read_data='<a><b>bbb</b></a>').return_value]

        # Act
        result = common.ReadXmlFileOrDefault('a:\\b\\c.xml', 'foo').tag

        # Assert
        self.assertEqual(result, 'a')
		
    def test_GetUnicodeFileNameFromUrl(self):
        # Act
        result = common.GetUnicodeFileNameFromUrl('http://a.com/b/c/d.jpg', 'jpeg')

        # Assert
        self.assertEqual(result, 'd (a.com).jpg')
        
    def test_GetUnicodeFileNameFromUrl_Unquote(self):
        # Act
        result = common.GetUnicodeFileNameFromUrl('http://a.com/b/%E4%B8%80.GIF', 'gif')

        # Assert
        self.assertEqual(result, u'\u4e00 (a.com).GIF')
		
    def test_GetUnicodeFileNameFromUrl_NoFile(self):
        # Act
        result = common.GetUnicodeFileNameFromUrl('http://a.com/b/c', 'png')

        # Assert
        self.assertEqual(result, None)
		
    def test_GetUnicodeFileNameFromUrl_FileDoesNotMatchContentType(self):
        # Act
        result = common.GetUnicodeFileNameFromUrl('http://a.com/b/c.php?fileid=1', 'png')

        # Assert
        self.assertTrue(result, 'c (a.com).png')
		
    def test_GetUnicodeFileNameFromUrl_LinkedFile(self):
        # Act
        result = common.GetUnicodeFileNameFromUrl('http://a.com/b/c.php?fileid=1', 'png', 'linked')

        # assert
        self.assertTrue(result, 'c (linked) (a.com).png')
		
    @mock.patch('common.os.path.isfile', autospec=True)
    @mock.patch('common.os.rename', autospec=True)
    def test_RenameFile(self, mock_rename, mock_isfile):
        # Arrange
        mock_isfile.return_value = False
        oldFileName = 'a:\\b\\qwerty.tmp'
        newFileName = 'a:\\b\\test (a.com).jpg'

        # Act
        result = common.RenameFile(oldFileName, newFileName)

        # Assert
        self.assertEqual(result, newFileName)
        mock_rename.assert_called_with(oldFileName, newFileName)
		
    @mock.patch('common.os.path.isfile', autospec=True)
    @mock.patch('common.os.rename', autospec=True)
    @mock.patch('common.glob', autospec=True)
    def test_RenameFile_FileExists(self, mock_glob, mock_rename, mock_isfile):
        # Arrange
        mock_isfile.return_value = True
        mock_glob.glob.return_value = []
        oldFileName = 'a:\\b\\qwerty.tmp'
        newFileName = 'a:\\b\\test (a.com) (1).jpg'

        # Act
        result = common.RenameFile(oldFileName, 'a:\\b\\test (a.com).jpg')

        # Assert
        self.assertEqual(result, newFileName)
        mock_rename.assert_called_with(oldFileName, newFileName)
		
    @mock.patch('common.os.path.isfile', autospec=True)
    @mock.patch('common.os.rename', autospec=True)
    @mock.patch('common.glob', autospec=True)
    def test_RenameFile_MultipleFilesExist(self, mock_glob, mock_rename, mock_isfile):
        # Arrange
        mock_isfile.return_value = True
        mock_glob.glob.return_value = ['a:\\b\\test (a.com) (3).jpg', 'a:\\b\\test (a.com) (1).jpg', 'a:\\b\\test (a.com) (2).jpg']
        oldFileName = 'a:\\b\\qwerty.tmp'
        newFileName = 'a:\\b\\test (a.com) (4).jpg'

        # Act
        result = common.RenameFile(oldFileName, 'a:\\b\\test (a.com).jpg')

        # Assert
        self.assertEqual(result, newFileName)
        mock_rename.assert_called_with(oldFileName, newFileName)
		
    @mock.patch('common.os.path.isfile', autospec=True)
    @mock.patch('common.os.rename', autospec=True)
    @mock.patch('common.glob', autospec=True)
    def test_RenameFile_MultipleFilesExistWithoutEnumeration(self, mock_glob, mock_rename, mock_isfile):
        # Arrange
        mock_isfile.return_value = True
        mock_glob.glob.return_value = ['a:\\b\\test (a.com) (a).jpg', 'a:\\b\\test (a.com) (b).jpg', 'a:\\b\\test (a.com) (c).jpg']
        oldFileName = 'a:\\b\\qwerty.tmp'
        newFileName = 'a:\\b\\qwerty.jpg'

        # Act
        result = common.RenameFile(oldFileName, 'a:\\b\\test (a.com).jpg')

        # Assert
        self.assertEqual(result, newFileName)
        mock_rename.assert_called_with(oldFileName, newFileName)
		
    @mock.patch('common.logging', autospec=True)
    @mock.patch('common.os.path.isfile', autospec=True)
    @mock.patch('common.os.rename', autospec=True)
    def test_RenameFile_ThrowsExceptionOnFirstRename(self, mock_rename, mock_isfile, mock_logging):
        # Arrange
        mock_isfile.return_value = False
        mock_rename.side_effect = [OSError, mock.DEFAULT]

        # Act
        result = common.RenameFile('a:\\b\\qwerty.tmp', 'a:\\b\\test (a.com).jpg')

        # Assert
        self.assertEqual(result, 'a:\\b\\qwerty.jpg')
        mock_logging.getLogger.assert_called_with('log')
		
    @mock.patch('common.logging', autospec=True)
    @mock.patch('common.os.path.isfile', autospec=True)
    @mock.patch('common.os.rename', autospec=True)
    def test_RenameFile_ThrowsExceptionOnAllRenames(self, mock_rename, mock_isfile, mock_logging):
        # Arrange
        mock_isfile.return_value = False
        mock_rename.side_effect = [OSError, OSError]

        # Act
        result = common.RenameFile('a:\\b\\qwerty.tmp', 'a:\\b\\test (a.com).jpg')

        # Assert
        self.assertEqual(result, 'a:\\b\\qwerty.tmp')
        mock_logging.getLogger.assert_called_with('log')
		
    def test_CreateXmlElement(self):
        # Act
        result = common.CreateXmlElement('a', 'b')

        # Assert
        self.assertEqual(result.tag, 'a')
        self.assertEqual(result.text, 'b')

    def test_CreateXmlElement_UnicodeValue(self):
        # Act
        result = common.CreateXmlElement('a', u'\u4e00')

        # Assert
        self.assertEqual(result.tag, 'a')
        self.assertEqual(result.text, u'\u4e00')

    def test_CreateXmlElement_NonStringValue(self):
        result = common.CreateXmlElement('a', 1)
        self.assertEqual(result.tag, 'a')
        self.assertEqual(result.text, '1')

    def test_CreateXmlElement_NonStringValue(self):
        # Act
        result = common.CreateXmlElement('a', 1)

        # Assert
        self.assertEqual(result.tag, 'a')
        self.assertEqual(result.text, '1')

    def test_CreateXmlElement_XmlValue(self):
        # Act
        result = common.CreateXmlElement('a', fromstring('<root><b>c</b><b>d</b></root>'))

        # Assert
        self.assertEqual(result.tag, 'a')
        self.assertEqual(len(result.findall('b')), 2)

    def test_CreateXmlElement_ParentIsPresent(self):
        # Arrange
        root = fromstring('<root/>')

        # Act
        result = common.CreateXmlElement('a', 'b', root)

        # Assert
        self.assertTrue(root.find('a') is not None)
        self.assertEqual(root.find('a').text, 'b')

    def test_DotDict(self):
        # Act
        result = common.DotDict({'a': 1, 'b': 2})

        # Assert
        self.assertEqual(result.a, 1)
        self.assertEqual(result.b, 2)
		
if __name__ == '__main__':
    unittest.main()