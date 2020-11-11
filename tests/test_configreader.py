import os
import sys
import unittest
import mock
from xml.etree.ElementTree import fromstring, Element, tostring

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
from configreader import GetConfig


class ConfigReaderTestCase(unittest.TestCase):

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig_NoConfigFile(self, mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<NoConfigFile/>')

        # Act
        with self.assertRaises(IOError) as assertEx:
            GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'No config file at a:\\b\\c.config')

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig_IgnoreSection(self, mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<configSections><configSection name="A" ignore="1"/></configSections>')

        # Act
        result = GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(len(result), 0)

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig_NoSectionName(self, mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<configSections><configSection ignore="0"/></configSections>')

        # Act
        with self.assertRaises(ValueError) as assertEx:
            GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'Encountered config section without name attribute')

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig_NoServer(self, mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<configSections><configSection name="A" ignore="0"/></configSections>')

        # Act
        with self.assertRaises(ValueError) as assertEx:
            GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'No server specified for config section with name A')

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig_NoExportCommentsPage(self, mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<configSections><configSection name="A"><server>abc</server></configSection></configSections>')

        # Act
        with self.assertRaises(ValueError) as assertEx:
            GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'No export comments page specified for config section with name A')

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig(self, mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<configSections>' +
                                                            '<configSection name="A">' +
                                                                '<server>abc</server>' +
                                                                '<exportCommentsPage>abc</exportCommentsPage>' +
                                                                '<eventPropertiesToExclude>' +
                                                                    '<eventPropertyToExclude>abc</eventPropertyToExclude>' +
                                                                    '<eventPropertyToExclude>bcd</eventPropertyToExclude>' +
                                                                '</eventPropertiesToExclude>' +
                                                                '<propPropertiesToExclude>' +
                                                                    '<propPropertyToExclude>abc</propPropertyToExclude>' +
                                                                '</propPropertiesToExclude>' +
                                                                '<users>' +
                                                                    '<user>' +
                                                                        '<name>abc</name>' +
                                                                        '<applyXSLT>1</applyXSLT>' +
                                                                        '<archiveComments>0</archiveComments>' +
                                                                        '<archiveImages>1</archiveImages>' +
                                                                    '</user>' +
                                                                    '<user ignore="1">' +
                                                                        '<name>abc</name>' +
                                                                        '<applyXSLT>1</applyXSLT>' +
                                                                        '<archiveComments>0</archiveComments>' +
                                                                        '<archiveImages>1</archiveImages>' +
                                                                    '</user>' +
                                                                '</users>' +
                                                            '</configSection>' +
                                                        '</configSections>')

        # Act
        result = GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['eventPropertiesToExclude']), 2)
        self.assertEqual(len(result[0]['propPropertiesToExclude']), 1)
        self.assertTrue(result[0]['applyXSLT'])
        self.assertFalse(result[0]['archiveComments'])
        self.assertTrue(result[0]['archiveImages'])

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig_NoUserName(self, mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<configSections>' +
                                                            '<configSection name="A">' +
                                                                '<server>abc</server>' +
                                                                '<exportCommentsPage>abc</exportCommentsPage>' +
                                                                '<eventPropertiesToExclude></eventPropertiesToExclude>' +
                                                                '<propPropertiesToExclude></propPropertiesToExclude>' +
                                                                '<users>' +
                                                                    '<user/>'
                                                                '</users>' +
                                                            '</configSection>' +
                                                        '</configSections>')

        # Act
        with self.assertRaises(ValueError) as assertEx:
            GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(u'%s' % str(assertEx.exception), u'No user name specified for one of the users in config section with name A')

    @mock.patch('configreader.ReadXmlFileOrDefault', autospec=True)
    def test_GetConfig_NoUsers(self,mock_readxmlordefault):
        # Arrange
        mock_readxmlordefault.return_value = fromstring('<configSections>' +
                                                            '<configSection name="A">' +
                                                                '<server>abc</server>' +
                                                                '<exportCommentsPage>abc</exportCommentsPage>' +
                                                                '<eventPropertiesToExclude></eventPropertiesToExclude>' +
                                                                '<propPropertiesToExclude></propPropertiesToExclude>' +
                                                            '</configSection>' +
                                                        '</configSections>')

        # Act
        result = GetConfig('a:\\b\\c.config')

        # Assert
        self.assertEqual(len(result), 0)

if __name__ == '__main__':    
    unittest.main()