import re
from urlparse import urlparse
from modules.common import IsNullOrWhiteSpace, ReadXmlFileOrDefault, ReadXmlNodeOrDefault

def GetConfig(configFilePath):
    noConfigFile = 'NoConfigFile'
    configFileXml = ReadXmlFileOrDefault(configFilePath, noConfigFile)
    if configFileXml.tag == noConfigFile:
        raise IOError(u'No config file at %s' % configFilePath)
    
    configSettings = []
    configSections = configFileXml.findall('configSection')
    for configSection in configSections:
        if 'ignore' in configSection.attrib and configSection.attrib['ignore'] == '1':
            continue
        if 'name' not in configSection.attrib or IsNullOrWhiteSpace(configSection.attrib['name']):
            raise ValueError(u'Encountered config section without name attribute')
        server = ReadXmlNodeOrDefault(configSection, 'server', None)
        if server is None:
            raise ValueError(u'No server specified for config section with name %s' % configSection.attrib['name'])
        exportCommentsPage = ReadXmlNodeOrDefault(configSection, 'exportCommentsPage', None)
        if exportCommentsPage is None:
            raise ValueError(u'No export comments page specified for config section with name %s' % configSection.attrib['name'])
        eventPropertiesToExclude = [elem.text for elem in configSection.findall('eventPropertiesToExclude/eventPropertyToExclude')]
        propPropertiesToExclude = [elem.text for elem in configSection.findall('propPropertiesToExclude/propPropertyToExclude')]
        
        users = configSection.findall('users/user')
        for user in users:
            if 'ignore' in user.attrib and user.attrib['ignore'] == '1':
                continue
            sectionProperties = {}
            sectionProperties['sectionName'] = configSection.attrib['name']
            sectionProperties['server'] = server
            urlParseResult = urlparse(server)
            sectionProperties['serverSchema'] = urlParseResult.scheme
            sectionProperties['serverNetloc'] = re.sub('^www\.', '', urlParseResult.netloc, flags = re.I)
            sectionProperties['exportCommentsPage'] = exportCommentsPage
            sectionProperties['eventPropertiesToExclude'] = eventPropertiesToExclude
            sectionProperties['propPropertiesToExclude'] = propPropertiesToExclude
            
            journal = ReadXmlNodeOrDefault(user, 'name', None)
            if journal is None:
                raise ValueError(u'No user name specified for one of the users in config section with name %s' % configSection.attrib['name'])
            sectionProperties['journal'] = journal
                
            userExportProps = ['applyXSLT', 'archiveComments', 'archiveImages']
            for prop in userExportProps:
                value = ReadXmlNodeOrDefault(user, prop, None)
                sectionProperties[prop] = True if value == '1' else False
            configSettings.append(sectionProperties)
    return configSettings
