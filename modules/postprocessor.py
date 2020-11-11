import urllib
import logging
import re
import time
import os
import datetime
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring

import common
from imagescraper import ImageScraper

class PostProcessor:
    def __init__(self, generatorName, environment):
        self.generatorName = generatorName
        self.e = common.DotDict(environment)

        self.eventKeyRegex = re.compile('^events_\d+_(\w+)$', re.I) # matches something like events_1_(title)
        self.propKeyNameRegex = re.compile('^(prop_\d+_)name$', re.I) # matches something like (prop_1_)name
        self.propValueNamePattern = '%svalue'
        self.propertyHandlers = { 'event': [self.UnquotePlus, self.ScrapeImages], 'taglist': [self.TransformTaglist] }
        self.itemKeyRegex = re.compile('^sync_(\d+)_item$', re.I)
        self.postIdRegex = re.compile('^L-(\d+)$', re.I)
        self.lastSyncFileName = 'lastsync.dat'
        self.minSyncDate = datetime.datetime(1999, 3, 18, 0, 0, 0) # on this day LJ started working
        self.postItemIdRegex = re.compile('^events_\d+_itemid$', re.I)
        self.postAnumRegex = re.compile('^events_\d+_anum$', re.I)
        self.cachedImagePathsFileName = 'cachedimagepaths.xml'
        self.imagesFolder = 'images'

        # exclude properties like events_1_count from post export
        self.__defaultEventPropertiesToExclude = ['logtime', 'count']
        # exclude properties like prop_1_name\ncommentalter from post export
        self.__defaultPropPropertiesToExclude = ['useragent', 'commentalter', 'current_moodid', 'interface', 'give_features', 'langs', 'personifi_tags', 'revtime',
                                          'revnum', 'picture_mapid', 'import_source', 'opt_backdated', 'allowmask', 'opt_nocomments', 'opt_preformatted', 'hasscreened',
                                          'used_rte', 'personifi_lang', 'personifi_word_count', 'reading_time', 'spam_counter']

        # create image scraper settings. Ugly configuration, but it ensures we only take one pass through post HTML to download pics and change tags accordingly,
	# and also don't constantly open & close image mapping file
        self.imageScraperSettings = None if not self.e.archiveImages else {'cnn': self.e.cnn,
                                    'httpRequestDelaySeconds': self.e.delay,
                                    'sectionName': self.e.sectionName,
                                    'journal': self.e.journal,
                                    'cachedImagesXml': common.ReadXmlFileOrDefault(os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal,
                                                                                                self.e.cachedDataFolder, self.cachedImagePathsFileName), 'images'),
                                    'imagesFolder': self.imagesFolder
                                    }
        self.logger = logging.getLogger('log')
		
    def ProcessPosts(self):	
        #getting all available sync items because we'll use it to determine whether we need to delete local posts
        allSyncItems = self.GetSyncItems(self.minSyncDate)
        #getting last synchronization date 
        lastSyncDate = self.GetLastSyncDate()

        # getting sync items that are new or modified since last sync date
        syncItemsToUpdate = filter(lambda elem: elem['time'] > lastSyncDate, allSyncItems)
        lenSyncItems = len(syncItemsToUpdate)
        self.logger.info(u'%s: %s: got %d post info(s) to add or update' % (self.e.sectionName, self.e.journal, lenSyncItems))
		
        if self.e.applyXSLT: # copy stylesheet to journal folder
            self.CopyStylesheetToJournalFolder()
                    
        #retrieving posts
        postIdsMap = {} # saves database post ids and public post ids
        exception = None
        currentI = -1
        for i, postInfo in enumerate(syncItemsToUpdate):
            try:
                time.sleep(self.e.delay) # sleeping so that we're not making calls too often
                currentI = i
                self.logger.info(u'%s: %s: %d of %d: getting post with id = %d modified on %s' %
                            (self.e.sectionName, self.e.journal, i + 1, lenSyncItems, postInfo['id'], postInfo['time'].strftime(self.e.dateFormatString)))
                post = self.GetPost(postInfo['id'])
                publicPostId = self.GetPublicPostId(post)
                postFileName = u'%d.xml' % publicPostId
                self.SavePostToFile(post, postFileName)
                self.logger.info(u'%s: %s: post with id = %d saved as %s' % (self.e.sectionName, self.e.journal, postInfo['id'], postFileName))
                postIdsMap[postInfo['id']] = publicPostId
            except Exception as e:
                self.logger.debug(u'%s: %s: exception on retrieving or saving post with id = %d' % (self.e.sectionName, self.e.journal, syncItemsToUpdate[i]['id']), exc_info = True)
                exception = e
                break
        self.RemoveDeletedPosts(allSyncItems) # if any posts were deleted on server, let's delete them in our copy
        self.SavePostIdsMap(postIdsMap)

        if len(syncItemsToUpdate) > 0:
            if exception is None:
                # syncItems is sorted by time ASC, so we can just take the last element of the array as new sync date
                self.SaveLastSyncDate(syncItemsToUpdate[len(syncItemsToUpdate) - 1]['time'])
            else:
                # if there's a exception, take last processed post datetime as new sync date
                lastProcessedI = currentI - 1
                if lastProcessedI >= 0:
                    self.SaveLastSyncDate(syncItemsToUpdate[lastProcessedI]['time'])
                raise exception


    def GetSyncItems(self, startDate, result = None):
        """Gets post db ids and times they were created or last edited starting from startDate"""
        if result == None:
            result = []
        params = {'lastsync': startDate.strftime(self.e.dateFormatString)}
        self.logger.info(u'%s: %s: getting post info for syncronization starting from = %s...' % (self.e.sectionName, self.e.journal, params['lastsync']))

        #returns Array ( [sync_1_action] => create [sync_1_item] => L-1234 [sync_1_time] => 2016-12-06 03:25:00
        # [sync_2_action] => create [sync_2_item] => L-1235 [sync_2_time] => 2016-12-06 03:27:33 [sync_count] => 2 [sync_total] => 2 )
        connParams = {'server': self.e.server, 'user': self.e.journal, 'pwdhash': self.e.passwordHash }		
        syncItems = self.e.cnn.MakeServerRequestWithAuthentication(connParams, 'syncitems', params)

        timeKeyPattern = 'sync_%s_time'
        syncItemKeys = syncItems.keys()
        maxDateFound = startDate
            
        for key in syncItemKeys:
            numberMatches = self.itemKeyRegex.search(key)
            if numberMatches:
                timeKey = timeKeyPattern % (numberMatches.group(1))
                normalizedDateTimeString = re.sub('\.\d+$', '', syncItems[timeKey]) #chops off .00000 in dates like 2000-12-12 09:00:00.00000
                itemDateTime = datetime.datetime.strptime(normalizedDateTimeString, self.e.dateFormatString)

                postIdMatches = self.postIdRegex.search(syncItems[key])
                if postIdMatches:
                    result.append({'id': int(postIdMatches.group(1)), 'time': itemDateTime}) # postIdRegex.group(1) matches (\d+) in ^L-(\d+)$'

                if itemDateTime > maxDateFound:
                    maxDateFound = itemDateTime
        
        if int(syncItems['sync_count']) < int(syncItems['sync_total']):
            time.sleep(self.e.delay)
            self.GetSyncItems(maxDateFound, result)

        return sorted(result, key=lambda elem: elem['time']) # sort by time asc

    def GetPost(self, postId):
        """Loads individual post data by its db id"""
        params = {'selecttype': 'one', 'itemid': postId, 'lineendings': 'pc'}
        connParams = {'server': self.e.server, 'user': self.e.journal, 'pwdhash': self.e.passwordHash }
        postData = self.e.cnn.MakeServerRequestWithAuthentication(connParams, 'getevents', params)
        return postData

    def FlatPostDataToXmlObject(self, postData):
        xmlRoot = Element('post')

        # create mandatory default properties
        common.CreateXmlElement('generator', self.generatorName, xmlRoot)
        common.CreateXmlElement('source', self.e.serverNetloc, xmlRoot)
        common.CreateXmlElement('source_schema', self.e.serverSchema, xmlRoot)
        common.CreateXmlElement('source_shortname', self.e.sectionName, xmlRoot)
        common.CreateXmlElement('author', self.e.journal, xmlRoot)
        common.CreateXmlElement('author_url', common.CreateAuthorUrl(self.e.serverSchema, self.e.serverNetloc, self.e.journal), xmlRoot)
            
        postDataKeys = postData.keys()
        for key in postDataKeys:
            eventKeyNameMatches = self.eventKeyRegex.search(key)
            propKeyNameMatches = self.propKeyNameRegex.search(key)

            xmlSubElement = None
            xmlSubElementValue = None
            xmlSubElementName = None
            xmlPostDataKey = None
            
            if eventKeyNameMatches:
                eventKeyName = eventKeyNameMatches.group(1)
                if not (eventKeyName in self.e.eventPropertiesToExclude or eventKeyName in self.__defaultEventPropertiesToExclude):
                    xmlSubElementName = eventKeyName
                    xmlPostDataKey = key
            elif propKeyNameMatches:
                propKeyName = postData[key]
                if not (propKeyName in self.e.propPropertiesToExclude or propKeyName in self.__defaultPropPropertiesToExclude):
                    xmlSubElementName = propKeyName
                    xmlPostDataKey = self.propValueNamePattern % propKeyNameMatches.group(1) # produces something like prop_1_value

            if xmlSubElementName:
                xmlSubElementValue = postData[xmlPostDataKey]
                if xmlSubElementName in self.propertyHandlers:
                    for handler in self.propertyHandlers[xmlSubElementName]:
                        xmlSubElementValue = handler(xmlSubElementValue, postId = common.FindDictValueByKeyRegex(postData, self.postItemIdRegex))
                common.CreateXmlElement(xmlSubElementName, xmlSubElementValue, xmlRoot)           
        
        return xmlRoot


    def SavePostToFile(self, postData, fileName):
        try:
            postXml = self.FlatPostDataToXmlObject(postData)
            path = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal, fileName)
            # if file with this name already exists, pick up its comments first before rewriting it
            fileDoesNotExistTag = 'FileDoesNotExist'
            oldPostXml = common.ReadXmlFileOrDefault(path, fileDoesNotExistTag)
            if oldPostXml.tag != fileDoesNotExistTag:
                oldCommentsXml = oldPostXml.find('comments')
                if oldCommentsXml is not None:
                    common.CreateXmlElement('comments', oldCommentsXml, postXml)
            # convert post xml to string
            xsltFile = self.e.xsltFile if self.e.applyXSLT else None
            postXmlString = common.PrettyPrintXml(postXml, xsltFile)
            # write post xml string to file
            common.CreatePathIfNotExists(path)
            with open(path, "w") as postFile:
                postFile.write(postXmlString.encode('utf-8'))
        except:
            self.logger.debug('Post data: %s' % postData)
            for node in postXml:
                self.logger.debug('PostXml: tag: %s' % node.tag)
                self.logger.debug('PostXml: textType: %s' % type(node.text))
                self.logger.debug('PostXml: text: %s' % node.text)
            raise
                    
    def SavePostIdsMap(self, postIdsMap):
        if len(postIdsMap) > 0:
            path = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal, self.e.cachedDataFolder, self.e.cachedPostIdsFile)
            previouslyCachedIds = common.ReadXmlFileOrDefault(path, 'posts')
            
            for dbId in postIdsMap:
                if previouslyCachedIds.find('post[@dbid="%d"]' % dbId) is None: # didn't find anything cached with current dbId
                      newlyCachedId = SubElement(previouslyCachedIds, 'post')
                      newlyCachedId.attrib['dbid'] = str(dbId)
                      newlyCachedId.attrib['publicid'] = str(postIdsMap[dbId])

            common.CreatePathIfNotExists(path)
            with open(path, "w") as cachedIdsFile:
                cachedIdsFile.write(tostring(previouslyCachedIds, 'utf-8').encode('utf-8'))
				
    def RemoveDeletedPosts(self, syncItemsToCheckForDeletion):
        journalPath = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal)
        cachedPostIdsPath = os.path.join(journalPath, self.e.cachedDataFolder, self.e.cachedPostIdsFile)
        cachedImagePathsPath = os.path.join(journalPath, self.e.cachedDataFolder, self.cachedImagePathsFileName)
        noCachedInfoTag = 'NoCachedInfo'
        cachedPostIdsXml = common.ReadXmlFileOrDefault(cachedPostIdsPath, noCachedInfoTag)
        cachedImagePathsXml = common.ReadXmlFileOrDefault(cachedImagePathsPath, noCachedInfoTag)
        filesToDelete = []
        imagesToDelete = []
        forceImagesMapRewrite = False
        if len(syncItemsToCheckForDeletion) > 0 and cachedPostIdsXml.tag != noCachedInfoTag:
            existingPostIds = [syncItem['id'] for syncItem in syncItemsToCheckForDeletion]
            cachedPostIds = list(cachedPostIdsXml)
            filesToDelete = []
            for cachedPostInfo in cachedPostIds:
                if int(cachedPostInfo.attrib['dbid']) not in existingPostIds:
                    filesToDelete.append('%s.xml' % cachedPostInfo.attrib['publicid'])
                    cachedPostIdsXml.remove(cachedPostInfo)
                    if cachedImagePathsXml.tag != noCachedInfoTag:
                        imagesRelatedToPost = cachedImagePathsXml.findall('.//post[@dbid="%s"]../..' % cachedPostInfo.attrib['dbid']) # find parent of parent of 'post' with dbid
                        for imageInfo in imagesRelatedToPost:
                            if len(imageInfo.findall('posts/post')) == 1: # image is related only to this post, delete it
                                imagesToDelete.append(imageInfo.attrib['local'])
                                cachedImagePathsXml.remove(imageInfo)
                            else: # image is related to other posts, don't touch it but remove post reference from it
                                postNode = imageInfo.find('posts/post[@dbid="%s"]' % cachedPostInfo.attrib['dbid'])
                                imageInfo.find('posts').remove(postNode)
                            forceImagesMapRewrite = True
                            
        self.logger.info(u'%s: %s: found %d post file(s) to delete and %d image(s) related to these post(s)...' %
                         (self.e.sectionName, self.e.journal, len(filesToDelete), len(imagesToDelete)))
        self.UpdateFilesMapping(cachedPostIdsPath, cachedPostIdsXml, filesToDelete, journalPath, 'post')
        self.UpdateFilesMapping(cachedImagePathsPath, cachedImagePathsXml, imagesToDelete, os.path.join(journalPath, self.imagesFolder), 'image', forceImagesMapRewrite)
					
    def UpdateFilesMapping(self, itemCacheFilePath, itemCacheXml, itemsToDelete, pathToItems, itemName, forceMapRewrite = False):
        if len(itemsToDelete) > 0 or forceMapRewrite:
            common.CreatePathIfNotExists(itemCacheFilePath)
            with open(itemCacheFilePath, "w") as itemCacheFile:
                itemCacheFile.write(tostring(itemCacheXml, 'utf-8').encode('utf-8'))

            for itemToDelete in itemsToDelete:
                itemToDeletePath = os.path.join(pathToItems, itemToDelete)
                try:
                    os.remove(itemToDeletePath)
                except OSError:
                    self.logger.debug(u'%s: %s: couldn\'t delete %s file %s because it does not exist' % (self.e.sectionName, self.e.journal, itemName, itemToDeletePath))
                self.logger.info(u'%s: %s: deleted %s file %s' % (self.e.sectionName, self.e.journal, itemName, itemToDeletePath))

    def GetLastSyncDate(self):
        path = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal, self.e.cachedDataFolder, self.lastSyncFileName)
        if not os.path.exists(path):
            self.logger.debug(u'Didn\'t find file %s, returning default sync date' % path)
            return self.minSyncDate
        else:
            with open(path, "r") as lastSyncFile:
                lastSyncDateString = lastSyncFile.readline()
                return datetime.datetime.strptime(lastSyncDateString.strip(), self.e.dateFormatString)
                            
    def SaveLastSyncDate(self, date):
        path = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal, self.e.cachedDataFolder, self.lastSyncFileName)
        common.CreatePathIfNotExists(path)
        with open(path, "w") as lastSyncFile:
            lastSyncFile.write(date.strftime(self.e.dateFormatString))

    def CopyStylesheetToJournalFolder(self):
        copyToFolder = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal)
        copyFromPath = os.path.join(os.getcwdu(), self.e.xsltFile)
        copyToPath = os.path.join(copyToFolder, self.e.xsltFile)
        if not os.path.exists(copyFromPath):
            raise IOError(u'XSLT stylesheet is not found, expected path is %s' % copyFromPath)
        common.CreatePathIfNotExists(copyToPath)
        if not os.path.exists(copyToPath) or os.path.getmtime(copyFromPath) > os.path.getmtime(copyToPath):
            with open(copyFromPath, 'r') as sourceFile:
                sourceFileContent = sourceFile.read()
                with open(copyToPath, "w") as destFile:
                    destFile.write(sourceFileContent)

    def GetPublicPostId(self, postData):
        itemId = common.FindDictValueByKeyRegex(postData, self.postItemIdRegex)
        anum = common.FindDictValueByKeyRegex(postData, self.postAnumRegex)
        if itemId is None:
            raise ValueError(u'Could not get itemid from post data')
        if anum is None:
            raise ValueError(u'Could not get anum from post data')
        return int(itemId) * 256 + int(anum)
    
    def UnquotePlus(self, s, **kwargs):
        """Unquotes the quoted string"""
        return urllib.unquote_plus(s.encode('ascii')).decode('utf-8') # s is unicode, but unquote operates only on ascii, so we convert it to ascii, unquote and get it back to utf-8

    def ScrapeImages(self, markup, **kwargs):
        if self.imageScraperSettings is not None:
            result = ImageScraper.ScrapeImages(markup, self.imageScraperSettings)
            imagesToDelete = []
            
            if 'postId' not in kwargs:
                raise ValueError(u'Parameter postId not present in arguments list')
            postId = kwargs['postId']
            needCacheSaving = False
            if len(result['downloadedImageInfos']) > 0:
                for imageInfo in result['downloadedImageInfos']:
                    imgXml = SubElement(self.imageScraperSettings['cachedImagesXml'], 'image')
                    imgXml.attrib = {k: v for k, v in imageInfo.items() if k in ['local', 'remote', 'linkedLocal', 'linkedRemote']}
                    postsXml = SubElement(imgXml, 'posts')
                    postXml = SubElement(postsXml, 'post')
                    postXml.attrib['dbid'] = postId
                needCacheSaving = True
            if len(result['existingImageInfos']) > 0:
                for imageInfo in result['existingImageInfos']:
                    imgXml = self.imageScraperSettings['cachedImagesXml'].find('image[@remote="%s"]' % imageInfo['remote'])
                    if imgXml is None:
                        raise RuntimeError(u'Couldn\'t find any cached info about image %s when it should be present' % imageInfo['remote'])
                    if len(imgXml.attrib) != len(imageInfo):
                        # if linked image was deleted but original image stayed intact, delete linked image
                        if 'linkedLocal' in imgXml.attrib and 'linkedLocal' not in imageInfo:
                            imagesToDelete.append(imgXml.attrib['linkedLocal'])
                        imgXml.attrib = {k: v for k, v in imageInfo.items() if k in ['local', 'remote', 'linkedLocal', 'linkedRemote']}
                        needCacheSaving = True
                    postsXml = imgXml.find('posts')
                    if postsXml.find('post[@dbid="%s"]' % postId) is None:
                        postXml = SubElement(postsXml, 'post')
                        postXml.attrib['dbid'] = postId
                        needCacheSaving = True

            # if there was an image in the post and the post got edited so that the image was deleted - delete it
            cachedImagesRelatedToPost = self.imageScraperSettings['cachedImagesXml'].findall('.//post[@dbid="%s"]../..' % postId)
            realPostImageInfos = result['downloadedImageInfos'] + result['existingImageInfos']
            for cachedImageInfo in cachedImagesRelatedToPost:
                # cached image info not found in actual images belonging to post...
                if len(list(filter(lambda elem: elem['remote'] == cachedImageInfo.attrib['remote'], realPostImageInfos))) == 0:
                    if len(cachedImageInfo.findall('posts/post')) == 1: #  and related to only one post: delete it
                        imagesToDelete.extend([v for k, v in cachedImageInfo.attrib.items() if k in ['local', 'linkedLocal']])
                        self.imageScraperSettings['cachedImagesXml'].remove(cachedImageInfo)
                    else: # and related to other posts: remove reference to this post from it
                        postNode = cachedImageInfo.find('posts/post[@dbid="%s"]' % postId)
                        cachedImageInfo.find('posts').remove(postNode)
                    needCacheSaving = True
                    
            # let's save updated image mappings to file every time we have something new in them
            # it's slower, but this way there's less chance that script is interrupted somewhere up the line
            # and we end up with hundreds of unmapped images
            if needCacheSaving:
                cacheDir = common.GetUpperLevelDir()
                cachedImagePathsPath = os.path.join(cacheDir, self.e.sectionName, self.e.journal, self.e.cachedDataFolder, self.cachedImagePathsFileName)
                savedImagesFolderPath = os.path.join(cacheDir, self.e.sectionName, self.e.journal, self.imagesFolder)
                self.UpdateFilesMapping(cachedImagePathsPath, self.imageScraperSettings['cachedImagesXml'], imagesToDelete, savedImagesFolderPath, 'image', True)
                
            return result['updatedMarkup']
        return markup
		
    def TransformTaglist(self, taglist, **kwargs):
        """Transforms comma-separated string of tags "tag1, tag2, tag3" into xml Element object: <root><tag>tag1</tag><tag>tag2</tag><tag>tag3</tag></root>"""
        if common.IsNullOrWhiteSpace(taglist):
            return fromstring('<root/>')
        individualTags = common.SplitCommaSeparatedString(taglist)
        tagificator = lambda tag: u'<tag>' + tag + u'</tag>'
        s = u'<root>' + u''.join([tagificator(tag) for tag in individualTags]) + u'</root>'
        return fromstring(s.encode('utf-8'))