#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
import ConfigParser
import xml.dom.minidom
import shutil
import sys
    
def getNumberFromString(valueStr):
    digit = None
    # 尝试分别用int或者float来解析valueStr
    try:
        digit = int(valueStr)
    except ValueError:
        try:
            digit = float(valueStr)
        except ValueError:
            digit = None
    return digit

def getRatioNumber(number, ratio):
    # 将ratio乘以number得到新的number值
    newNumber = ratio * number
    # 去掉多余的.0
    if newNumber == int(newNumber):
        newNumber = int(newNumber)
    return newNumber
    
# 获取配置文件解释器
def getConfigParser() :
    configFile = os.path.join(os.path.dirname(__file__), 'config.ini')
    if os.path.exists(configFile):
        parser = ConfigParser.ConfigParser()
        parser.read(configFile)
        return parser

# 判断是否是Eclipse的工程
def isEclipseProject(projectDir):
    manifestFile = os.path.join(projectDir, 'AndroidManifest.xml')
    return os.path.exists(manifestFile)

# 判断是否是AndroidStudio的工程
def isAndroidStudioProject(projectDir):
    manifestFile = os.path.join(projectDir, 'AndroidManifest.xml')
    gradleFile = os.path.join(projectDir, 'build.gradle')
    if os.path.exists(manifestFile):
        return False
    else:
        return os.path.exists(gradleFile)
    
def getResPath(isEclipse, projectDir):
    if isEclipse:
        path = os.path.join(projectDir, 'res')
        print 'The project res path is ' + path
        return path
    else:
        path = os.path.join(projectDir, r'src\main\res')
        print 'The project res path is ' + path
        return path
    
# 从某个配置节点获取对应的dict
def convertConfigToDict(config, section) :
    if config.has_section(section):
        # 获取section节点下所有的items
        configItems = config.items(section)
        destDict = {}
        # 遍历所有items，将items解析为key和value
        # key为目标dimens后缀，value为倍率
        for key, value in configItems:
            value.strip()
            splitValue = value.split(' ')
            dpValue = splitValue[0]
            spValue = ''
            for splitItem in splitValue[1:]:
                if splitItem != '':
                    spValue = splitItem
                    break
            dpRatio = getNumberFromString(dpValue)
            # sp数值未配置，则表示sp数值和dp数值相等
            if spValue == '':
                spRatio = dpRatio
            else:
                spRatio = getNumberFromString(spValue)
            
            # ratio解析失败，则此条配置无效，继续下一条
            if dpRatio == None or spRatio == None:
                continue
            # 缩放比例必须大于0
            if dpRatio <= 0 or spRatio <= 0:
                continue
            ratioKey = (dpRatio, spRatio)
            # 如果dict中已经包含此条倍率，则将当期key直接添加到该倍率下
            if destDict.has_key(ratioKey):
                destDict[ratioKey].append(key)
            # 如果dict中没有包含此条倍率，则直接为此倍率设置一个新的list值
            else:
                destDict[ratioKey] = [key]
        return destDict
    
# 获取dimensDirctory目录中包含dimen配置的所有文件
def getFilesWithDimenConfig(dimensDirctory):
    fileList = []
    # 遍历dimensDirctory目录下所有的文件
    (parent, _, fileNames) = os.walk(dimensDirctory).next()
    for fileName in fileNames:
        # 不是xml文件，不做处理
        if not fileName.endswith('.xml'):
            continue
        try:
            # 解析xml文件
            fileFullPath = os.path.join(parent, fileName)
            dom = xml.dom.minidom.parse(fileFullPath)
            root = dom.documentElement
            # 找出所有的dimen节点
            dimenItems = root.getElementsByTagName('dimen')
            # dimen节点个数不是0，表示此文件存在dimen配置，继续下一个文件
            if len(dimenItems) != 0:
                fileList.append(fileFullPath)
                continue
            # dimen节点个数是0，找出所有的item节点
            itemItems = root.getElementsByTagName('item')
            # 遍历所有item节点
            for item in itemItems:
                # 如果item节点的type是dimen，表示此文件存在dimen配置，继续下一个文件
                if item.getAttribute('type') == u'dimen':
                    fileList.append(fileFullPath)
                    break
        except:
            continue
    return fileList

def getDestFile(srcFileName, destFolder):
    fileBaseName = os.path.basename(srcFileName)
    fileDirName = os.path.dirname(srcFileName)
    fileDirBaseName = os.path.basename(fileDirName)
    splitDirBaseName = fileDirBaseName.split('-')
    basePart = splitDirBaseName[0]
    orientationPart = None
    if len(splitDirBaseName) != 1:
        orientationPart = splitDirBaseName[1]
    fileParent = os.path.dirname(fileDirName)
    splitDest = destFolder.split('-')
    dpiPart = None
    swPart = None
    versionPart = None
    sizePart = None
    for splitItem in splitDest:
        if splitItem in ('ldpi', 'mdpi', 'hdpi','xhdpi', 'xxhdpi', 'xxxhdpi'):
            dpiPart = splitItem
        elif splitItem in ('small', 'normal', 'large','xlarge'):
            sizePart = splitItem
        elif splitItem.startswith('sw') and splitItem.endswith('dp'):
            swPart = splitItem
        elif splitItem.startswith('v') and splitItem[1:].isdigit():
            versionPart = splitItem
    
    newName = basePart
    if dpiPart != None:
        newName = newName + '-' + dpiPart
    if swPart != None:
        newName = newName + '-' + swPart
    if sizePart != None:
        newName = newName + '-' + sizePart
    if orientationPart != None:
        newName = newName + '-' + orientationPart
    if versionPart != None:
        newName = newName + '-' + versionPart
    
    destFileDirName = os.path.join(fileParent, newName)
    if not os.path.exists(destFileDirName):
        os.mkdir(destFileDirName)
    destFileName = os.path.join(destFileDirName, fileBaseName)
    return destFileName

# dimensDirctory是包含dimens配置的源目录，
# 读取dimensDirctory目录中所有的dimens节点内容，
# 然后保存到destinations指定的文件夹中
def processDir(dimensDirctory, destinationDict):
    # dimensDirctory目录不存在，直接返回
    if not os.path.exists(dimensDirctory):
        return
    
    print 'process directory ' + os.path.basename(dimensDirctory)
    # 获取dimensDirctory目录中包含dimen配置的所有文件
    fileList = getFilesWithDimenConfig(dimensDirctory)
    print 'dimension files in the directory:',
    for temp in fileList:
        print os.path.basename(temp),
    print
    # 遍历所有的目标配置
    for (ratio, destFolders) in destinationDict.items():
        # 遍历dimensDirctory目录下所有包含dimen配置的文件
        for fileName in fileList:
            # 如果比例为1，不需要解析xml和计算，直接复制文件即可
            if ratio[0] == 1 and ratio[1] == 1:
                for dest in destFolders:
                    destFileName = getDestFile(fileName, dest)
                    shutil.copyfile(fileName, destFileName)
            # 如果比例不为1，需要解析xml，并计算得到每个dp和sp的新的值，然后用新的值替换掉以前的值，最后保存到新的文件中
            else:
                try:
                    # 解析xml文件
                    dom = xml.dom.minidom.parse(fileName)
                    root = dom.documentElement
                    # 找出所有的dimen节点
                    dimenItems = root.getElementsByTagName('dimen')
                    # 遍历所有dimen节点
                    for item in dimenItems:
                        itemValue = item.firstChild.data
                        # 如果节点数值单位不是dp也不是sp，继续下一个item
                        if not itemValue.endswith(u'dp') and not itemValue.endswith(u'sp'):
                            continue
                        # 得到value对应的数值，可能是int，也可能是float
                        itemValueByNumber = getNumberFromString(itemValue[0:-2])
                        # value不是数值，继续下一个item
                        if itemValueByNumber == None:
                            continue
                        # 将ratio乘以itemValueByNumber得到新的value值
                        if itemValue.endswith(u'dp'):
                            newItemValue = getRatioNumber(itemValueByNumber, ratio[0])
                        else:
                            newItemValue = getRatioNumber(itemValueByNumber, ratio[1])
                        item.firstChild.data = str(newItemValue) + itemValue[-2:]
                        
                    # 找出所有的item节点
                    itemItems = root.getElementsByTagName('item')
                    # 遍历所有item节点
                    for item in itemItems:
                        # 如果item节点的type不是dimen，继续下一条
                        if item.getAttribute('type') != u'dimen':
                            continue
                        itemValue = item.firstChild.data
                        # 如果节点数值单位不是dp也不是sp，继续下一个item
                        if not itemValue.endswith(u'dp') and not itemValue.endswith(u'sp'):
                            continue
                        # 得到value对应的数值，可能是int，也可能是float
                        itemValueByNumber = getNumberFromString(itemValue[0:-2])
                        # value不是数值，继续下一个item
                        if itemValueByNumber == None:
                            continue
                        # 将ratio乘以itemValueByNumber得到新的value值
                        # 将ratio乘以itemValueByNumber得到新的value值
                        if itemValue.endswith(u'dp'):
                            newItemValue = getRatioNumber(itemValueByNumber, ratio[0])
                        else:
                            newItemValue = getRatioNumber(itemValueByNumber, ratio[1])
                        item.firstChild.data = str(newItemValue) + itemValue[-3:-1]
                        
                    for dest in destFolders:
                        destFileName = getDestFile(fileName, dest)
                        destFile = codecs.open(destFileName, 'w', 'utf-8')
                        dom.writexml(destFile, encoding='utf-8')
                        destFile.close()
                        replaceNewline(fileName, destFileName)
                        
                except Exception,e:
                    print e
                    continue

def replaceNewline(srcFile, destFile):
    if os.path.exists(srcFile) and os.path.exists(destFile):
        srcfp = open(srcFile, 'rU')
        srcfp.read()
        srcNewl = srcfp.newlines
        srcfp.close()
        
        destfp = open(destFile, 'rU')
        lines = destfp.readlines()
        destNewl = destfp.newlines
        destfp.close()
        
        if len(lines) != 0:
            line0 = lines[0]
            index = line0.find('?>')
            if index != -1 and index != len(line0) - 2:
                lines[0] = line0[:index+2] + destNewl
                lines.insert(1, line0[index+2:])
        if srcNewl != None and destNewl != None and srcNewl != destNewl:
            for lineStr in lines:
                lineStr = lineStr.rstrip(destNewl) + srcNewl
                
        destfp = open(destFile, 'w')
        destfp.writelines(lines)
        destfp.close()
        
def process():
    # 判断工程是Eclipse还是Android Studio
    isEclipse = isEclipseProject(projectDir)
    isAndroidStudio = isAndroidStudioProject(projectDir)
    # 既不是Eclipse，也不是Android Studio
    if not isEclipse and not isAndroidStudio:
         raise RuntimeError('Unknown project type')
    
    resDirectory = getResPath(isEclipse, projectDir)

    # 对全部配置，需要转换普通版，横版和竖版
    if AllConfig != None and len(AllConfig) != 0:
        dimensDirctory = os.path.join(resDirectory, 'values')
        processDir(dimensDirctory, AllConfig)
        dimensDirctory = os.path.join(resDirectory, 'values-port')
        processDir(dimensDirctory, AllConfig)
        dimensDirctory = os.path.join(resDirectory, 'values-land')
        processDir(dimensDirctory, AllConfig)
        
    # 如果有普通配置，且配置项目个数不为0，则开始处理普通配置项
    if GeneralConfig != None and len(GeneralConfig) != 0:
        dimensDirctory = os.path.join(resDirectory, 'values')
        processDir(dimensDirctory, GeneralConfig)
    # 如果有竖版配置，且配置项目个数不为0，则开始处理竖版配置项
    if PortConfig != None and len(PortConfig) != 0:
        dimensDirctory = os.path.join(resDirectory, 'values-port')
        processDir(dimensDirctory, PortConfig)
    # 如果有横版配置，且配置项目个数不为0，则开始处理横版配置项
    if LandConfig != None and len(LandConfig) != 0:
        dimensDirctory = os.path.join(resDirectory, 'values-land')
        processDir(dimensDirctory, LandConfig)

if  __name__ == '__main__':
    configParser = getConfigParser()
    if configParser == None:
        raise RuntimeError('Get parser failed')
    # 获取配置文件中配置的项目目录
    if len(sys.argv) > 1:
        projectDir = sys.argv[1]
    else:
        projectDir = configParser.get("Dir", "ProjectDir")
    # 没有相应配置，返回
    if projectDir is None:
         raise RuntimeError('Unknown parameters')
    if not os.path.exists(projectDir):
         raise RuntimeError('Invalid parameters')
    # 分别将配置文件中配置的全部配置，通用配置，竖版配置和横版配置转换到dict中
    AllConfig = convertConfigToDict(configParser, 'Dimens-All')
    GeneralConfig = convertConfigToDict(configParser, 'Dimens-General')
    PortConfig = convertConfigToDict(configParser, 'Dimens-Port')
    LandConfig = convertConfigToDict(configParser, 'Dimens-Land')
    # 生成dimens
    process()