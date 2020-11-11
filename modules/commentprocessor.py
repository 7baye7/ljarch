import logging
import time
import os
import re
import datetime
from xml.etree.ElementTree import SubElement, tostring, fromstring
from itertools import takewhile

import common

class CommentProcessor:
    def __init__(self, environment):
        self.e = common.DotDict(environment)
        self.cachedUserIdsFileName = 'cacheduserids.xml'
        self.extUserRealNameRegex = re.compile('<title>([^<]+)</title>', re.I | re.M)
        self.maxCommentBodiesOnPage = 1000
        self.commentDateFormatString = '%Y-%m-%dT%H:%M:%SZ' # comment dates are returned as yyyy-mm-ddThh:mm:ssZ
        self.cachedEnrichedCommentsMetadataFileName = 'cachedcommentsmetadata_%d.xml'
        self.logger = logging.getLogger('log')
        
    def ProcessComments(self):
        sessionToken = None
        connParams = {'server': self.e.server, 'user': self.e.journal, 'pwdhash': self.e.passwordHash }
        try:
            self.logger.info(u'%s: %s: getting session token for comments...' % (self.e.sectionName, self.e.journal))
            sessionToken = self.e.cnn.GetSessionToken(connParams)
            
            self.logger.info(u'%s: %s: getting comments metadata...' % (self.e.sectionName, self.e.journal))
            metadata = self.GetCommentsInfo(sessionToken, 'META', 0)
            maxIdNode = metadata.find('maxid')
            maxId = 0 if maxIdNode is None else int(maxIdNode.text)
            if maxId > 0:
                # merge current user metadata with cached user metadata
                currentUsermaps = metadata.find('usermaps')
                mergedUsermaps = self.MergeUserIdsMapXmlWithCache(metadata.find('usermaps'))
                metadata.remove(currentUsermaps)
                metadata.append(mergedUsermaps)

                #get min comment id (useful if comment enumeration does not start with 1)
                minIdKey = lambda cmt: int(cmt.attrib['id'])
                minIdElement = min(metadata.findall('comments/comment'), key = minIdKey)
                startId = int(minIdElement.attrib['id'])

                self.logger.info(u'%s: %s: found %d comments, enumeration starts with %d and ends with %d' %
                            (self.e.sectionName, self.e.journal, len(metadata.findall('comments/comment')), startId, maxId))
                
                #remove comments metadata (it's utterly useless, no need to waste memory on it)
                metadata.remove(metadata.find('comments'))

                while startId < maxId:
                    time.sleep(self.e.delay) # sleeping so that we're not making calls too often
                    maxCommentIdOnPage = self.ProcessCommentsPage(sessionToken, startId, metadata)
                    startId = maxCommentIdOnPage + 1
            else:
                self.logger.info(u'%s: %s: journal has no comments' % (self.e.sectionName, self.e.journal))
        finally:
            self.logger.info(u'%s: %s: expiring created session token...' % (self.e.sectionName, self.e.journal))
            self.e.cnn.ExpireSession(connParams, sessionToken)
            self.logger.info(u'%s: %s: session token expired successfully' % (self.e.sectionName, self.e.journal))
			
    def GetCommentsInfo(self, sessionToken, infoType, startId):
        """Gets comment metadata or bodies in xml format"""
        getInfoType = None
        if infoType == 'META':
            getInfoType = 'comment_meta'
        elif infoType == 'BODY':
            getInfoType = 'comment_body'
        else:
            raise ValueError(u'Invalid infoType %s, expected either META or BODY' % infoType)
        exportCommentsPage = '%s/%s' % (self.e.server, self.e.exportCommentsPage)
        params = {'get': getInfoType, 'startid': startId }
        headers = {'Cookie': 'ljsession=%s' % sessionToken }  
        xmlResult = self.e.cnn.MakeRequest(exportCommentsPage, params, headers, 'GET')
        return fromstring(xmlResult.encode('utf-8'))


    def MergeUserIdsMapXmlWithCache(self, userIdsMapXml):
        path = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal, self.e.cachedDataFolder, self.cachedUserIdsFileName)
        previouslyCachedIdsXml = common.ReadXmlFileOrDefault(path, 'usermaps')
        needCacheSaving = False

        if len(previouslyCachedIdsXml) > 0: # we have some cached ids, let's check if we need to delete any users
            previouslyCachedIds = list(previouslyCachedIdsXml)
            for previouslyCachedId in previouslyCachedIds:
                if userIdsMapXml.find('usermap[@id="%s"]' % previouslyCachedId.attrib['id']) is None: # didn't find anything like cached id in fresh user metadata
                    previouslyCachedIdsXml.remove(previouslyCachedId)
                    needCacheSaving = True
        
        if len(userIdsMapXml) > 0: # usermap has children
            usermaps = list(userIdsMapXml) # get children
            for usermap in usermaps:
                if previouslyCachedIdsXml.find('usermap[@id="%s"]' % usermap.attrib['id']) is None: # didn't find anything cached with current id
                    if usermap.attrib['user'].startswith('ext_'): # go and find real user name
                        try:
                            time.sleep(self.e.delay)
                            profilePage = self.e.cnn.MakeRequest('%s/profile' % self.e.server, {'userid': usermap.attrib['id'], 't': 'I'}, type = 'GET')
                            pageTitleMatches = self.extUserRealNameRegex.search(profilePage)
                            if pageTitleMatches:
                                title = pageTitleMatches.group(1)
                                # finding last '-' in string, taking everything before it and trimming the result
                                # if there's no '-', taking the whole string
                                endPos = title.rfind('-')
                                if endPos == -1:
                                    endPos = len(title)
                                usermap.attrib['real_name'] = title[0:endPos].strip()
                            else:
                                self.logger.warning(u'Got profile page of OpenID user %s but couldn\'t find its title to extract user\'s "real" name from it' % usermap.attrib['user'])
                        except Exception as e:
                            # if getting "real" name of ext_12345 user fails, log it but don't stop
                            self.logger.warning(u'Couldn\'t get profile page of OpenID user %s' % usermap.attrib['user'], exc_info = True)
                        
                    previouslyCachedIdsXml.append(usermap)
                    needCacheSaving = True
                    
        if needCacheSaving:     
            common.CreatePathIfNotExists(path)
            with open(path, "w") as cachedIdsFile:
                cachedIdsFile.write(tostring(previouslyCachedIdsXml, 'utf-8').encode('utf-8'))
        return previouslyCachedIdsXml

    def ProcessCommentsPage(self, sessionToken, startId, commentsMetadata):
        self.logger.info(u'%s: %s: getting comment bodies starting with comment id = %d' % (self.e.sectionName, self.e.journal, startId))
        bodies = self.GetCommentsInfo(sessionToken, 'BODY', startId)
        combinationResult = self.CombineCommentBodiesWithMetadata(bodies, commentsMetadata)
        exportPageNumber = int(startId / self.maxCommentBodiesOnPage)
            
        newOrUpdatedComments = self.GetNewOrUpdatedComments(exportPageNumber, combinationResult['enrichedComments'])
        commentsByPostId = {}
        for comment in newOrUpdatedComments:
            postId = comment.attrib['jitemid']
            if postId not in commentsByPostId:
                commentsByPostId[postId] = []
            commentsByPostId[postId].append(comment)
        self.logger.info(u'%s: %s: found %d new or updated comments for %d posts on page #%d' %
                    (self.e.sectionName, self.e.journal, len(newOrUpdatedComments), len(commentsByPostId), exportPageNumber))

        if len(commentsByPostId) > 0:
            cwd = common.GetUpperLevelDir()
            cachedPostIdsPath = os.path.join(cwd, self.e.sectionName, self.e.journal, self.e.cachedDataFolder, self.e.cachedPostIdsFile)
            cachedPostIds = common.ReadXmlFileOrDefault(cachedPostIdsPath, 'posts')
            if len(list(cachedPostIds)) > 0: # we have any cached post ids
                for postId in commentsByPostId:
                    cachedPostIdItem = cachedPostIds.find('post[@dbid="%s"]' % postId)
                    if cachedPostIdItem is not None:
                        postFilePath = os.path.join(cwd, self.e.sectionName, self.e.journal, '%s.xml' % cachedPostIdItem.attrib['publicid'])
                        doNotProcessTag = 'DoNotProcess' # if we end up having a document with this tag, it means we didn't open the actual file and have nowhere to write comments. Don't raise error because it's comments, but don't process further
                        postXml = common.ReadXmlFileOrDefault(postFilePath, doNotProcessTag)
                        if postXml.tag != doNotProcessTag:
                            self.AddUpdateCommentsInPostXml(postXml, commentsByPostId[postId])
                            with open(postFilePath, "w") as postFile:
                                xsltFile = self.e.xsltFile if self.e.applyXSLT else None
                                postXmlString = common.PrettyPrintXml(postXml, xsltFile)
                                postFile.write(postXmlString.encode('utf-8'))
                        else:
                            self.logger.debug(u'%s: %s: couldn\'t find file %s.xml required by comment chain attached to post dbId = %s' %
                                      (self.e.sectionName, self.e.journal, cachedPostIdItem.attrib['publicid'], postId))
        return combinationResult['maxCommentId']
    

    def CombineCommentBodiesWithMetadata(self, bodies, metadata):
        metadataCommentsNode = metadata.find('comments')
        
        #get user mappings
        metadataUsermapsNode = metadata.find('usermaps')

        #while we're cycling through the list of comments, let's find max comment id for further processing
        maxCommentId = 0

        #merge comment states and user mappings with comment bodies
        commentBodies = bodies.findall('comments/comment')
        enrichedComments = []
        for commentBody in commentBodies:
            if commentBody.attrib['jitemid'] != '0': # export mechanism sometimes fails to properly attach comments to posts, we won't process anything that has post id equal to 0
                # match poster id with poster name
                userNode = metadataUsermapsNode.find('usermap[@id="%s"]' % commentBody.attrib['posterid'])
                commentBody.attrib['poster_name'] = userNode.attrib['real_name'] if 'real_name' in userNode.attrib else userNode.attrib['user']
                if userNode.attrib['user'].startswith('ext_'):
                    commentBody.attrib['poster_url'] = common.CreateAuthorExtUrl(self.e.server, userNode.attrib['id'])
                else:
                    commentBody.attrib['poster_url'] = common.CreateAuthorUrl(self.e.serverSchema, self.e.serverNetloc, userNode.attrib['user'])

                # while we're at it, let's convert weird parameter data format to our standard one
                dateNode = commentBody.find('date')
                if dateNode is not None:
                    dateObject = datetime.datetime.strptime(dateNode.text, self.commentDateFormatString)
                    dateNode.text = dateObject.strftime(self.e.dateFormatString)
                enrichedComments.append(commentBody)

            commentId = int(commentBody.attrib['id'])
            maxCommentId = commentId if commentId > maxCommentId else maxCommentId
        return {'maxCommentId': maxCommentId, 'enrichedComments': enrichedComments}


    def GetNewOrUpdatedComments(self, pageNumber, commentBodies):
        newOrUpdatedComments = []
        if len(commentBodies) > 0:
            path = os.path.join(common.GetUpperLevelDir(), self.e.sectionName, self.e.journal, self.e.cachedDataFolder, self.cachedEnrichedCommentsMetadataFileName % pageNumber)
            enrichedCommentsMetadataXml = common.ReadXmlFileOrDefault(path, 'comments')

            # first check if we have any metadata to remove on the current page
            existingCommentIds = [elem.attrib['id'] for elem in commentBodies]
            removedCommentMetadataCount = self.RemoveDeletedCommentsMetadata(enrichedCommentsMetadataXml, existingCommentIds)
            self.logger.info(u'%s: %s: found %d comment metadata piece(s) to remove on page #%d' % (self.e.sectionName, self.e.journal, removedCommentMetadataCount, pageNumber))
            
            for commentBody in commentBodies:
                commentId = commentBody.attrib['id']
                commentState = commentBody.attrib['state'] if 'state' in commentBody.attrib else 'A' # it's python's ternary operator. If comment has state, so be it, else assign 'A'(ctive)
                commentDate = common.ReadXmlNodeOrDefault(commentBody, 'date', None)
                commentSubjectAndText = '%s%s' % (common.ReadXmlNodeOrDefault(commentBody, 'subject', ''), common.ReadXmlNodeOrDefault(commentBody, 'body', ''))
                subjectBodyHash = common.MD5(commentSubjectAndText) if commentSubjectAndText != '' else ''
                    
                commentFromMetadata = enrichedCommentsMetadataXml.find('comment[@id="%s"]' % commentId)
                if commentFromMetadata is None: # didn't find anything cached with current comment id
                    commentBody.attrib['processingstate'] = 'new'
                    newOrUpdatedComments.append(commentBody) # add comment to new comments list
                    newCommentMetadata = SubElement(enrichedCommentsMetadataXml, 'comment') # create new comment metadata entry
                    newCommentMetadata.attrib['id'] = commentId
                    newCommentMetadata.attrib['state'] = commentState
                    self.WriteNodeAttribIfNotDefault(newCommentMetadata, 'date', commentDate, None)
                    self.WriteNodeAttribIfNotDefault(newCommentMetadata, 'subjectbodyhash', subjectBodyHash, '')
                else:
                    commentFromMetadataState = commentFromMetadata.attrib['state'] if 'state' in commentFromMetadata.attrib else 'A'
                    commentFromMetadataDate = commentFromMetadata.attrib['date'] if 'date' in commentFromMetadata.attrib else None
                    commentFromMetadataSubjectBodyHash = commentFromMetadata.attrib['subjectbodyhash'] if 'subjectbodyhash' in commentFromMetadata.attrib else ''
                    if commentFromMetadataDate != commentDate or commentFromMetadataState != commentState or commentFromMetadataSubjectBodyHash != subjectBodyHash: # date or state or body or subject changed
                        commentBody.attrib['processingstate'] = 'updated'
                        newOrUpdatedComments.append(commentBody) # add comment to updated comments list
                        commentFromMetadata.attrib['state'] = commentState
                        self.WriteNodeAttribIfNotDefault(commentFromMetadata, 'date', commentDate, None)
                        self.WriteNodeAttribIfNotDefault(commentFromMetadata, 'subjectbodyhash', subjectBodyHash, '')
                                            
            # write updated data back to file            
            common.CreatePathIfNotExists(path)
            with open(path, "w") as cachedEnrichedCommentsMetadataFile:
                cachedEnrichedCommentsMetadataFile.write(tostring(enrichedCommentsMetadataXml, 'utf-8').encode('utf-8'))
        # return new and updated comments
        return newOrUpdatedComments
		
    def RemoveDeletedCommentsMetadata(self, cachedCommentsMetadataXml, existingCommentIds):
        removedCommentMetadataCount = 0
        if len(cachedCommentsMetadataXml) > 0: # we have some cached comments metadata, let's see if we need to delete anything
            enrichedCommentsMetadata = list(cachedCommentsMetadataXml)
            for cachedCM in enrichedCommentsMetadata:
                if cachedCM.attrib['id'] not in existingCommentIds:
                    cachedCommentsMetadataXml.remove(cachedCM)
                    removedCommentMetadataCount += 1
        return removedCommentMetadataCount


    def AddUpdateCommentsInPostXml(self, postXml, newOrUpdatedComments):
        commentsNode = postXml.find('comments')
        if commentsNode is None:
            commentsNode = SubElement(postXml, 'comments')
        parent_map = {c: p for p in commentsNode.getiterator() for c in p} # searches for parent nodes
            
        for comment in newOrUpdatedComments:
            if comment.attrib['processingstate'] == 'new':
                if 'parentid' not in comment.attrib: # top-level comment
                    indexToInsertAt = self.GetCommentIndexToInsertAt(comment, list(commentsNode))
                    commentsNode.insert(indexToInsertAt, comment)
                else:
                    # recursively search comments
                    parentComment = commentsNode.find('.//comment[@id="%s"]' % comment.attrib['parentid'])
                    if parentComment is None:
                        raise RuntimeError(u'Found no parent comment for comment with id = %s and parentid = %s in post with url = %s' % (comment.attrib['id'], comment.attrib['parentid'], postXml.find('url').text))
                    childCommentsNode = parentComment.find('comments')
                    if childCommentsNode is None:
                        childCommentsNode = SubElement(parentComment, 'comments')
                    indexToInsertAt = self.GetCommentIndexToInsertAt(comment, childCommentsNode.findall('comment'))
                    childCommentsNode.insert(indexToInsertAt, comment)
            else: # processingstate == 'updated'
                existingComment = commentsNode.find('.//comment[@id="%s"]' % comment.attrib['id'])
                if existingComment is None:
                    raise RuntimeError(u'Found no comment with id = %s to update in post with url = %s' % (comment.attrib['id'], postXml.find('url').text))
                # we will never have a situation where a comment having child comments is updated (it's prohibited in LJ), 
                #so we won't care about keeping child comments of the edited comment
                existingCommentIndex = list(parent_map[existingComment]).index(existingComment)
                existingCommentParent = parent_map[existingComment]
                existingCommentParent.insert(existingCommentIndex, comment)
                existingCommentParent.remove(existingComment)
                            
            comment.attrib.pop('processingstate', None) #deleting the temporary processing key

    def GetCommentIndexToInsertAt(self, comment, sameLevelComments):
        """Gets index at which to insert new comment under its parent node. The order is determined by comment id: the greater the id, the newer the comment ->
		old comments go to the top, new comments go to the bottom"""
        commentId = int(comment.attrib['id'])
        idLessThanCommentId = lambda cmt: int(cmt.attrib['id']) < commentId
        #takewhile takes elements until the first False in lambda, so if there were 3 comments with ids 1, 2, 4, and we have one that has id = 3, len(list(takewhile))) will return 2 as index to insert comment with id = 3
        return len(list(takewhile(idLessThanCommentId, sameLevelComments)))
		
    def WriteNodeAttribIfNotDefault(self, node, attribName, attribValue, attribValueDefault):
        """Write attribute with given name to given node if provided attribute value is not default, else remove the attribute"""
        if attribValue != attribValueDefault:
            node.attrib[attribName] = attribValue
        else:
            node.attrib.pop(attribName, None)