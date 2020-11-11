import sys, os
from os import system
from os.path import abspath

encoding = sys.getfilesystemencoding()
if getattr(sys, 'frozen', False): # running compiled script
    workingScriptDirPath = os.path.dirname(unicode(sys.executable, encoding))
else: # running normal .py file
    workingScriptDirPath = os.path.dirname(os.path.abspath(unicode(__file__, encoding)))

sys.path.append(workingScriptDirPath)

from modules.logger import SetupLogger
from modules.configreader import GetConfig
from modules.passwordreader import ReadPasswordHash
from modules.connection import Connection
from modules.common import MergeDicts, GetUpperLevelDir
from modules.postprocessor import PostProcessor
from modules.commentprocessor import CommentProcessor

def main():
    # Some constants
    scriptName = 'Archiver'
    httpRequestTimeoutSeconds = 30
    httpRequestDelaySeconds = 3 # so that we're not banned for accessing the site too often
    configFileName = 'archiver.config'
    xsltFileName = 'stylesheet.xsl'
    logFolderName = 'logs'
    logFileName = 'archiver.log'
    dateFormatString = '%Y-%m-%d %H:%M:%S' # dates should be in yyyy-mm-dd hh:mm:ss
    cachedDataFolderName = 'cached data'
    cachedPostIdsFileName = 'cachedpostids.xml'
    
    #switching working directory to the directory where the script is located
    if os.getcwdu() != workingScriptDirPath:
        os.chdir(workingScriptDirPath)
    logger = SetupLogger(os.path.join(GetUpperLevelDir(), logFolderName, logFileName), dateFormatString)
    try:
        cnn = Connection(httpRequestTimeoutSeconds, scriptName)
        
        configSections = GetConfig(os.path.join(GetUpperLevelDir(), configFileName))
        for setting in configSections:
            setting['passwordHash'] = ReadPasswordHash(setting['journal'], setting['sectionName'])

        globalSettings = {'cnn': cnn,
                       'delay': httpRequestDelaySeconds,
                       'cachedDataFolder': cachedDataFolderName,
                       'cachedPostIdsFile':cachedPostIdsFileName,
                       'xsltFile': xsltFileName,
                       'dateFormatString': dateFormatString}
        for configSection in configSections:
            try:
                environment = MergeDicts(configSection, globalSettings)
                #retrieving posts
                postPrc = PostProcessor(scriptName, environment)
                postPrc.ProcessPosts()

                #retrieving comments
                if environment['archiveComments']:
                    commPrc = CommentProcessor(environment)
                    commPrc.ProcessComments()
            except Exception as ex:
                logger.debug(u'Critical error in processing journal %s on server %s' % (environment['journal'], environment['sectionName']), exc_info = True)
                logger.error(u'Application has encountered an error while processing journal %s on server %s: %s. Check %s\%s\%s for full exception traceback and other details.' %
                             (environment['journal'], environment['sectionName'], ex, workingScriptDirPath, logFolderName, logFileName))
    except Exception as e:
        logger.debug(u'Critical application error', exc_info = True)
        logger.critical(u'Application has encountered a critical error and was stopped: %s. Check %s\%s\%s for full exception traceback and other details.' %
                        (e, workingScriptDirPath, logFolderName, logFileName))


if __name__ == '__main__':	
    main()