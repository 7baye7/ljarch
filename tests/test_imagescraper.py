#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import mock
from xml.etree.ElementTree import fromstring
import re

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
import imagescraper
import connection

class ImageScraperTestCase(unittest.TestCase):

    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName = 'i (a.bcd).jpg'
        storedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedImageName)
        markup = 'Some markup. <IMG SRC="http://a.bcd/i.jpg" WIDTH="800px" />. Some more markup.'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)
        mock_cnn.return_value.DownloadImage.return_value = storedImagePath

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertTrue(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName) in result['updatedMarkup'])
        self.assertEqual(len([elem for elem in result['downloadedImageInfos'] if elem['local'] == storedImageName and elem['remote'] == 'http://a.bcd/i.jpg']), 1)

    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_LinkedImage(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName = 'i (a.bcd).jpg'
        storedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedImageName)
        storedLinkedImageName = 'l-i (linked) (a.bcd).jpg'
        storedLinkedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName)
        markup = 'Some markup. <A HREF="http://a.bcd/l-i.jpg"><IMG SRC="http://a.bcd/i.jpg" WIDTH="800px" /></A>. Some more markup.'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = [storedImagePath, storedLinkedImagePath]

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertTrue(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName) in result['updatedMarkup'])
        self.assertEqual(len([elem for elem in result['downloadedImageInfos']
                              if elem['local'] == storedImageName and
                              elem['remote'] == 'http://a.bcd/i.jpg' and
                              elem['linkedRemote'] == 'http://a.bcd/l-i.jpg' and
                              elem['linkedLocal'] == storedLinkedImagePath]), 1)
							  
    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_LinkedImage_MultipleImagesUnderOneLink(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName1 = 'i1 (a.bcd).jpg'
        storedImageName2 = 'i2 (a.bcd).jpg'
        storedImagePath1 = 'a:\\%s\\%s' % (imagesFolder, storedImageName1)
        storedImagePath2 = 'a:\\%s\\%s' % (imagesFolder, storedImageName2)
        storedLinkedImageName1 = 'l-i (linked) (a.bcd).jpg'
        storedLinkedImagePath1 = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName1)
        storedLinkedImageName2 = 'l-i (linked) (a.bcd) (1).jpg'
        storedLinkedImagePath2 = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName2)
        markup = 'Некий текст. <A HREF="http://a.bcd/l-i.jpg"><IMG SRC="http://a.bcd/i1.jpg" WIDTH="800px" /><IMG SRC="http://a.bcd/i2.jpg" WIDTH="800px" /></A>. Ещё текст.'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = [storedImagePath1, storedLinkedImagePath1, storedImagePath2, storedLinkedImagePath2]

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertTrue(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName1) in result['updatedMarkup'])
        self.assertTrue(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName2) in result['updatedMarkup'])
        self.assertEqual(len([elem for elem in result['downloadedImageInfos']
                              if elem['local'] == storedImageName1 and
                              elem['remote'] == 'http://a.bcd/i1.jpg' and
                              elem['linkedRemote'] == 'http://a.bcd/l-i.jpg' and
                              elem['linkedLocal'] == storedLinkedImagePath1]), 1)
        self.assertEqual(len([elem for elem in result['downloadedImageInfos']
                              if elem['local'] == storedImageName2 and
                              elem['remote'] == 'http://a.bcd/i2.jpg' and
                              elem['linkedRemote'] == 'http://a.bcd/l-i.jpg' and
                              elem['linkedLocal'] == storedLinkedImagePath2]), 1)
		
    def test_ScrapeImages_NoImageTags(self):
        # Arrange
        imagesFolder = 'images'
        markup = 'Some markup. <a href="http://a.bcd/l-i.jpg">There are no image tags here</a>. Some more markup.'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertEqual(result['updatedMarkup'], markup)
		
    def test_ScrapeImages_ImageTagWithoutSrc(self):
        # Arrange
        imagesFolder = 'images'
        markup = 'Some markup. <a href="http://a.bcd/l-i.jpg"><img width="800px"/></a>. Some more markup.'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertEqual(result['updatedMarkup'], markup)
		
    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_ExceptionOnParse(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        markup = 'Some markup. <a href="http://a.bcd/l-i.jpg"><img src="http://a.bcd/i.jpg" width="800px"/></a>. Some more markup.'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = RuntimeError

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertEqual(result['updatedMarkup'], markup)
		
    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_DuplicateImageTags_TagWithLinkedImageComesFirst(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName = 'i (a.bcd).jpg'
        storedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedImageName)
        storedLinkedImageName = 'l-i (linked) (a.bcd).jpg'
        storedLinkedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName)
        markup = 'Some markup. <A HREF="http://a.bcd/l-i.jpg"><IMG SRC="http://a.bcd/i.jpg" WIDTH="200px" /></A>. Some more markup. <IMG SRC="http://a.bcd/i.jpg" WIDTH="800px" />'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = [storedImagePath, storedLinkedImagePath]

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertEqual(result['updatedMarkup'].count(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName)), 2)
        downloadedImageInfosLength = len([elem for elem in result['downloadedImageInfos']
                                          if elem['local'] == storedImageName and
                                          elem['remote'] == 'http://a.bcd/i.jpg' and
                                          elem['linkedRemote'] == 'http://a.bcd/l-i.jpg' and
                                          elem['linkedLocal'] == storedLinkedImagePath])
        self.assertEqual(downloadedImageInfosLength, 1)



    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_DuplicateImageTags_TagWithLinkedImageComesLast(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName = 'i (a.bcd).jpg'
        storedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedImageName)
        storedLinkedImageName = 'l-i (linked) (a.bcd).jpg'
        storedLinkedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName)
        markup = 'Some markup. <IMG SRC="http://a.bcd/i.jpg" WIDTH="800px" />. Some more markup. <A HREF="http://a.bcd/l-i.jpg"><IMG SRC="http://a.bcd/i.jpg" WIDTH="200px" /></A>'
        settings = self.__getScraperSettings(fromstring('<images/>'), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = [storedImagePath, storedLinkedImagePath]

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertEqual(result['updatedMarkup'].count(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName)), 2)
        downloadedImageInfosLength = len([elem for elem in result['downloadedImageInfos']
                                          if elem['local'] == storedImageName and
                                          elem['remote'] == 'http://a.bcd/i.jpg' and
                                          elem['linkedRemote'] == 'http://a.bcd/l-i.jpg' and
                                          elem['linkedLocal'] == storedLinkedImagePath])
        self.assertEqual(downloadedImageInfosLength, 1)
		
    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_ImageExistsInCache(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName = 'i (a.bcd).jpg'
        storedCachedImageName = 'i_cached (a.bcd).jpg'
        storedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedImageName)
        storedLinkedImageName = 'l-i (linked) (a.bcd).jpg'
        storedLinkedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName)
        markup = 'Some markup. <A HREF="http://a.bcd/l-i.jpg"><IMG SRC="http://a.bcd/i.jpg" WIDTH="200px" /></A>. Some more markup. <IMG SRC="http://a.bcd/i_cached.jpg" WIDTH="800px" />'
        settings = self.__getScraperSettings(fromstring('<images><image local="%s" remote="http://a.bcd/i_cached.jpg"><posts><post dbid="1" /></posts></image></images>' % storedCachedImageName), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = [storedImagePath, storedLinkedImagePath]

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        downloadedImageInfosLength = len([elem for elem in result['downloadedImageInfos']
                                          if elem['local'] == storedImageName and
                                          elem['remote'] == 'http://a.bcd/i.jpg' and
                                          elem['linkedRemote'] == 'http://a.bcd/l-i.jpg' and
                                          elem['linkedLocal'] == storedLinkedImagePath])
        self.assertEqual(result['updatedMarkup'].count(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName)), 1)
        self.assertEqual(result['updatedMarkup'].count(u'data-local-src="%s/%s"' % (imagesFolder, storedCachedImageName)), 1)
        self.assertEqual(downloadedImageInfosLength, 1)
        self.assertEqual(len([elem for elem in result['existingImageInfos'] if elem['local'] == storedCachedImageName and elem['remote'] == 'http://a.bcd/i_cached.jpg']), 1)
		
    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_ImageExistsInCache_WithoutLinkedImage(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName = 'i (a.bcd).jpg'
        storedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedImageName)
        storedLinkedImageName = 'l-i (linked) (a.bcd).jpg'
        storedLinkedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName)
        markup = 'Some markup. <A HREF="http://a.bcd/l-i.jpg"><IMG SRC="http://a.bcd/i.jpg" WIDTH="200px" /></A>. Some more markup.'
        settings = self.__getScraperSettings(fromstring('<images><image local="%s" remote="http://a.bcd/i.jpg"><posts><post dbid="1" /></posts></image></images>' % storedImageName), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = [storedLinkedImagePath]

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        existingImageInfosLength = len([elem for elem in result['existingImageInfos']
                                          if elem['local'] == storedImageName and
                                          elem['remote'] == 'http://a.bcd/i.jpg' and
                                          elem['linkedRemote'] == 'http://a.bcd/l-i.jpg' and
                                          elem['linkedLocal'] == storedLinkedImagePath])
        self.assertEqual(result['updatedMarkup'].count(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName)), 1)
        self.assertEqual(existingImageInfosLength, 1)
		
    @mock.patch('imagescraper.logging', autospec=True)
    @mock.patch('imagescraper.time', autospec=True)
    @mock.patch('connection.Connection', autospec=True)
    def test_ScrapeImages_ImageExistsInCache_LinkedImageGotDeleted(self, mock_cnn, mock_time, mock_logging):
        # Arrange
        imagesFolder = 'images'
        storedImageName = 'i (a.bcd).jpg'
        storedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedImageName)
        storedLinkedImageName = 'l-i (linked) (a.bcd).jpg'
        storedLinkedImagePath = 'a:\\%s\\%s' % (imagesFolder, storedLinkedImageName)
        markup = 'Some markup. <IMG SRC="http://a.bcd/i.jpg" WIDTH="200px" />. Some more markup.'
        settings = self.__getScraperSettings(
            fromstring('<images><image local="%s" remote="http://a.bcd/i.jpg" linkedRemote="http://a.bcd/l-i.jpg" linkedLocal="%s"><posts><post dbid="1" /></posts></image></images>' %
                       (storedImageName, storedLinkedImagePath)), imagesFolder)
        mock_cnn.return_value.DownloadImage.side_effect = [storedLinkedImagePath]

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        existingImageInfos = [elem for elem in result['existingImageInfos'] if elem['local'] == storedImageName and elem['remote'] == 'http://a.bcd/i.jpg']
        self.assertEqual(result['updatedMarkup'].count(u'data-local-src="%s/%s"' % (imagesFolder, storedImageName)), 1)
        self.assertEqual(len(existingImageInfos), 1)
        self.assertFalse('linkedRemote' in existingImageInfos[0])
        self.assertFalse('linkedLocal' in existingImageInfos[0])
		
    def test_NoImagesButKnownIssueWithSelfClosingTags(self):
        # Arrange
        markup = 'Some markup. <user name="some user">. Some more markup.'
        settings = self.__getScraperSettings(fromstring('<images/>'), '')

        # Act
        result = imagescraper.ImageScraper.ScrapeImages(markup, settings)

        # Assert
        self.assertEqual(markup, result['updatedMarkup'])
		
    def __getScraperSettings(self, cachedImagesXml, imagesFolder):
        return {'cnn': connection.Connection(1, 'Foo'),
                    'httpRequestDelaySeconds': 1,
                    'sectionName': 'A',
                    'journal': 'B',
                    'cachedImagesXml': cachedImagesXml,
                    'imagesFolder': imagesFolder}

if __name__ == '__main__':
    unittest.main()