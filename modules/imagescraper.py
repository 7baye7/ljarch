from bs4 import BeautifulSoup
import os
import time
import logging
import re

import common

class ImageScraper():
    def __init__(self, environment):
        self.cnn = environment['cnn']
        self.httpRequestDelaySeconds = environment['httpRequestDelaySeconds']
        self.sectionName = environment['sectionName']
        self.journal = environment['journal']
        self.cachedImagesXml = environment['cachedImagesXml']
        self.imagesFolder = environment['imagesFolder']
        self.logger = logging.getLogger('log')
        self.selfClosingTagRegex = re.compile('<\/(lj|user)>', re.I)

    def loadLinkedImage(self, soup, imgTag, keyDict, pathToSaveFile, addSleepTime = False):
        if 'linkedRemote' not in keyDict and imgTag.parent.name == u'a':
            # there's a link surrounding an image that potentially links to the larger version of the image. Let's download it
            a = imgTag.parent
            parentLinkHref = a.get('href')
            if parentLinkHref and not parentLinkHref.isspace():
                if addSleepTime:
                    time.sleep(self.httpRequestDelaySeconds)
                downloadedLinkedImagePath = self.cnn.DownloadImage(parentLinkHref, pathToSaveFile, True)
                if downloadedLinkedImagePath is not None:
                    keyDict['linkedRemote'] = parentLinkHref
                    keyDict['linkedLocal'] = downloadedLinkedImagePath
                    path, filename = os.path.split(downloadedLinkedImagePath)
                    a['data-local-src'] = u'%s/%s' % (self.imagesFolder, filename)
                    self.logger.info(u'Downloaded linked image from %s' % parentLinkHref)
        elif 'linkedRemote' in keyDict and imgTag.parent.name != u'a':
            # there's information about a larger version of the image in the link, but no actual link. Let's remove the information
            imagesWithSameLinkedRemoteCount = len(filter(lambda img:
                                             img.parent.name == u'a' and
                                             img.parent.get('href') == keyDict['linkedRemote'],
                                             soup.find_all('img', attrs={'src': keyDict['remote']})))
            if imagesWithSameLinkedRemoteCount == 0:
                keyDict.pop('linkedRemote', None)
                keyDict.pop('linkedLocal', None)

    def scrape(self, markup):
        """The main magic is done here. HTML tags are checked for being img and having scr. If there's info about this src in either image cache that comes
            in XML form or in the array of already downloaded images that didn't make it to cache yet (these are the ones that were downloaded while parsing the same
            piece of HTML, say, we have 2 links to the same image in one post), then the image is downloaded, and its remote and local links are put into 
            downloadedImageInfos. If the image is in cache, cached info is used, and its remote and local links are put into existingImageInfos."""
        soup = BeautifulSoup(markup, 'html.parser')
        downloadedImageInfos = []
        existingImageInfos = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and not src.isspace():
                try:
                    cachedImageInfo = self.cachedImagesXml.find('image[@remote="%s"]' % src)
                    freshlyDownloadedImageInfo = list(filter(lambda elem: elem['remote'] == src, downloadedImageInfos))
                    pathToSaveFile = os.path.join(common.GetUpperLevelDir(), self.sectionName, self.journal, self.imagesFolder)
                    if cachedImageInfo is not None:
                        img['data-local-src'] = u'%s/%s' % (self.imagesFolder, cachedImageInfo.attrib['local'])
                        existingImgInfo = {k: v for k, v in cachedImageInfo.attrib.items() if k in ['local', 'remote', 'linkedLocal', 'linkedRemote']}
                        self.loadLinkedImage(soup, img, existingImgInfo, pathToSaveFile)
                        existingImageInfos.append(existingImgInfo)
                    elif len(freshlyDownloadedImageInfo) > 0:
                        freshImgInfo = freshlyDownloadedImageInfo[0]
                        img['data-local-src'] = u'%s/%s' % (self.imagesFolder, freshImgInfo['local'])
                        self.loadLinkedImage(soup, img, freshImgInfo, pathToSaveFile)
                    else:
                        downloadedImagePath = self.cnn.DownloadImage(src, pathToSaveFile)
                        if downloadedImagePath is not None:
                            path, filename = os.path.split(downloadedImagePath)
                            img['data-local-src'] = u'%s/%s' % (self.imagesFolder, filename)
                            self.logger.info(u'Downloaded image from %s' % src)
                            imgInfo = {'remote': src, 'local': filename}
                            self.loadLinkedImage(soup, img, imgInfo, pathToSaveFile, True)
                            downloadedImageInfos.append(imgInfo)
                            time.sleep(self.httpRequestDelaySeconds)
                except:
                    self.logger.debug(u'%s: %s: Exception on trying to process image path %s in markup "%s"' % (self.sectionName, self.journal, src, markup), exc_info = True)

        updatedMarkup = self.fixSelfClosingTags(unicode(soup))
        return {'updatedMarkup': updatedMarkup, 'downloadedImageInfos': downloadedImageInfos, 'existingImageInfos': existingImageInfos }

    def fixSelfClosingTags(self, stringifiedSoup):
        """ An unfortunate known issue of html.parser in BeautifulSoup is that it adds unnecessary closing tags for custom tags
        that do not need it, like "this is <user name="foo"> user Foo" turns into "this is <user name="foo"> user Foo</user>"
        This method aims to take care of this discrepancy."""
        return self.selfClosingTagRegex.sub('', stringifiedSoup)

    @classmethod
    def ScrapeImages(cls, markup, environment):
        _p = cls(environment)
        return _p.scrape(markup)