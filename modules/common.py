import re
from hashlib import md5
from xml.etree.ElementTree import tostring, fromstring, Element, SubElement, ParseError
from xml.dom.minidom import parseString
import os
import urllib
from urlparse import urlparse
import glob
import logging

def MergeDicts(a, b):
    """Merges two dictionaries and returns result"""
    c = a.copy()
    c.update(b)
    return c
	
def MD5(string):
    """Generates MD5 hash of a string. string.encode() enables generating MD5 of non-Latin strings"""
    hash = md5()
    hash.update(string.encode('utf-8'))
    return hash.hexdigest()
	
def SplitCommaSeparatedString(string):
    """Splits comma-separated string into array of results and trims them"""
    splittingPattern = re.compile('^\s+|\s*,\s*|\s+$')
    return [x for x in splittingPattern.split(string) if x]
	
def PrettyPrintXml(xmlElement, xsltFile):
    """Creates XML string with newlines and indents so it could be readable even in a simple text editor"""
    roughString = tostring(xmlElement, 'utf-8')
    # the following lines of code remove whitespace characters BETWEEN XML TAGS only. "<a>\n  <b>1\n  2</b>\n  </a>" produces "<a><b>1\n  2</b></a>".
    # This is to prevent whitespace duplication in toprettyxml() that comes further
    prettyPrintingPattern = re.compile('(?<=.\>)\s+(?=\<)', re.I | re.M)
    roughStringWithWhitespaceCharsBetweenTagsRemoved = ''.join([line for line in re.split(prettyPrintingPattern, roughString.decode('utf-8')) if line.strip()])
    reparsed = parseString(roughStringWithWhitespaceCharsBetweenTagsRemoved.encode('utf-8'))
    if xsltFile is not None:
        pi = reparsed.createProcessingInstruction('xml-stylesheet', 'type="text/xsl" href="%s"' % xsltFile)
        reparsed.insertBefore(pi, reparsed.firstChild)
    return reparsed.toprettyxml(indent='  ')
	
def CreateAuthorUrl(serverSchema, serverNetloc, author):
    """Creates url for normal user (belonging to service and identified by name)"""
    return u'%s://%s.%s' % (serverSchema, author.replace('_', '-'), serverNetloc)

def CreateAuthorExtUrl(server, authorId):
    """Creates url for OpenID user (not belonging to service and identified by id)"""
    return u'%s/profile?userid=%s&t=I' % (server, authorId)
		
def ReadXmlFileOrDefault(path, defaultTag):
    """Reads xml from file path and returns xml object. If path or file contents are invalid, returns xml element with default tag"""
    xmlObject = None
    if os.path.exists(path):
        with open(path, "r") as xmlFile:
            xmlContents = xmlFile.read()
        try:
            xmlObject = fromstring(xmlContents)
        except ParseError:
            pass 
    if xmlObject is None:
        xmlObject = Element(defaultTag)
    return xmlObject
	
def CreatePathIfNotExists(path):
    """Creates all nonexistent directories for path"""
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
        logger = logging.getLogger('log')
        logger.debug(u'Created missing directories for path %s' % path)
		
def IsNullOrWhiteSpace(string):
    """Checks if a string is None or whitespace"""
    return not string or string.isspace()
	
def FindDictValueByKeyRegex(d, regex):
    """Finds value in dictionary by key regex. Returns value or None if nothing is found"""
    result = [value for key, value in d.items() if regex.search(key)]
    if result:
        return result[0]
    else:
        return None
		
def ReadXmlNodeOrDefault(parentNode, nodeName, defaultValue):
    """Reads value of child XML node with nodeName from parentNode. If there is no child node with nodeName under parentNode, returns defaultValue"""
    if parentNode is None:
        return defaultValue
    childNode = parentNode.find(nodeName)
    if childNode is None or IsNullOrWhiteSpace(childNode.text):
        return defaultValue
    return childNode.text
	
def CreateXmlElement(name, value, parent = None):
	""" Creates a new xml element with tag name = name and text = value.
		If value is Element object, appends all of its child elements as children, any other type is assigned as text
		if parent not None, new element is created as a SubElement of parent, if parent is None, new element is independent
	"""
	if parent is not None:
		elem = SubElement(parent, name)
	else:
		elem = Element(name)

	if type(value) is Element:     # assign all child elements of this element to xmlElement
			elem[:] = list(value) # per documentation, value.getchildren() was deprecated and should be substituted by list(value)
	else:
		elem.text = value if isinstance(value, str) or isinstance(value, unicode) else str(value)
	return elem
	
def GetUnicodeFileNameFromUrl(url, contentType, appendToFileName = None):
    """Gets file name from url and assings content-type extension to it. If there's nothing that can be treated as file name in the url, returns None"""
    contentType = 'jpg' if contentType.lower() == 'jpeg' else contentType.lower()
    parseResult = urlparse(url)
    splitPath = parseResult.path.split('/')
    lastPathPart = splitPath[len(splitPath) - 1]
    if '.' in lastPathPart: # we have something that can be treated as extension
        unquotedLastPathPart = urllib.unquote(lastPathPart.encode('ascii')).decode('utf-8')
        filename, file_extension = os.path.splitext(unquotedLastPathPart)
        file_extension_nodot = file_extension.strip('.')
        file_extension_final = contentType if file_extension_nodot.lower() != contentType else file_extension_nodot
        appendToFileName = u' (%s)' % appendToFileName if appendToFileName is not None else ''
        return u'%s%s (%s).%s' % (filename, appendToFileName, parseResult.netloc, file_extension_final)
    else:
        return None
                    
def RenameFile(oldPath, newPath):
    """Renames file from old name (with full path) to new name (with full path). Can assign names like file (1).ext to files with duplicate names. Returns new file name with full path"""
    prospectiveNewPath = None
    oldFileNameWithNewExtension = None
    if not os.path.isfile(newPath):
        prospectiveNewPath = newPath
    else:
        filename, file_extension = os.path.splitext(newPath)
        pattern = u'%s (*)%s' % (filename, file_extension)
        fullFileNamesWithBrackets = glob.glob(pattern)
        if len(fullFileNamesWithBrackets) == 0:
            prospectiveNewPath = u'%s (1)%s' % (filename, file_extension)
        else:
            enumeratedRegex = re.compile('\((\d+)\)%s$' % file_extension)
            fileNumbers = []
            for fullFileName in fullFileNamesWithBrackets:
                matches = enumeratedRegex.search(fullFileName)
                if matches:
                    fileNumbers.append(int(matches.group(1)))
            if len(fileNumbers) > 0:
                prospectiveNewPath = u'%s (%d)%s' % (filename, max(fileNumbers) + 1, file_extension)

    # in case something goes awry on rename, let's create an extra option: temp name with new extension
    oldfilename, oldfile_extension = os.path.splitext(oldPath)
    newfilename, newfile_extension = os.path.splitext(newPath)
    oldFileNameWithNewExtension = oldfilename + newfile_extension 
    prospectiveNewPath = oldFileNameWithNewExtension if prospectiveNewPath is None else prospectiveNewPath
    try:
        os.rename(oldPath, prospectiveNewPath)
        return prospectiveNewPath
    except Exception as e:
        logger = logging.getLogger('log')
        logger.debug(u'Couldn\'t rename %s to %s' % (oldPath, prospectiveNewPath), exc_info = True)
        if prospectiveNewPath != oldFileNameWithNewExtension:
            try:
                os.rename(oldPath, oldFileNameWithNewExtension)
                return oldFileNameWithNewExtension
            except:
                logger.debug(u'Couldn\'t rename %s to %s' % (oldPath, oldFileNameWithNewExtension), exc_info = True)
        return oldPath
		
def GetUpperLevelDir():
    """Gets full path to a directory 1 level up from current execution path"""
    return os.path.abspath(os.path.join(os.getcwdu(), os.pardir))

class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__