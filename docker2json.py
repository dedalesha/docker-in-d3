#!/usr/bin/python
import json
import subprocess
import re

imagesRegex = re.compile('(.+?)\\s+(.+?)\\s+(.+?)\\s')
containersRegex = re.compile('(.+?)\\s+(.+?)\\s')

def readCommandOutput(cmdArray, skipHeader=False, removeLastEmptyLine=True):
	cmdProcess = subprocess.Popen(cmdArray, stdout=subprocess.PIPE)
	(cmdOut, cmdErr) = cmdProcess.communicate()
	cmdLines = cmdOut.split('\n')
	if skipHeader:
		del cmdLines[0]
	if removeLastEmptyLine:
		if not cmdLines[len(cmdLines)-1]:
			del cmdLines[len(cmdLines)-1]
	return cmdLines

def parseImages():
	images = []
	imageLines = readCommandOutput(["/usr/bin/docker", "images"], skipHeader = True)
	for line in imageLines:
		match = imagesRegex.match(line)
		if match:
			images.append(
				{
					'imageName' : match.group(1),
					'id' : match.group(3),
					'group' : 1 if match.group(1) == '<none>' else 2
				}
			)

	return images

def listContainers():
	return readCommandOutput(["/usr/bin/docker", "ps", "-a", "-q"])

def inspectContainers():
	inspectCommand = ["/usr/bin/docker", "inspect"] + listContainers()
	cmdProcess = subprocess.Popen(inspectCommand, stdout=subprocess.PIPE)
	(cmdOut, cmdErr) = cmdProcess.communicate()
	containers = json.loads(cmdOut)
	return containers

containers = inspectContainers()


knownHistory = set([])
imageDependencies = {}

def parseImageDependencies(imageId):
	if not imageId in knownHistory:
		historyLines = readCommandOutput(["/usr/bin/docker", "history", "-q", imageId])
		dependent = ''
		for line in historyLines:
			if dependent:
				imageDependencies[dependent] = line
				dependent = ''
			if not line in knownHistory:
				knownHistory.add(line)
				dependent = line

def dumpJson():
	return


images = parseImages()
for image in images:
	parseImageDependencies(image['id'])

def findNonFilteredDependency(imageId, imagesById, dependencies):
	if imageId in dependencies:
		dependency = dependencies[imageId]
		if dependency in imagesById:
			return dependency
		else:
			return findNonFilteredDependency(dependency, imagesById, dependencies)
	else:
		return '<terminal>'

def indexImages(images):
	imagesById = {}	
	for image in images:
		imagesById[image['id']] = image
	return imagesById


imagesById = indexImages(images)

def reduceDependencies(imagesById, dependencies):

	for dependency in dependencies:
		dependencies[dependency] = findNonFilteredDependency(dependency, imagesById, dependencies)

	return

def dependenciesAsIndexes(imagesById, dependencies):
	result = []
	for dependency in dependencies:
		if (dependency in imagesById) and not (dependencies[dependency] == '<terminal>'):
			result.append({'source':imagesById.keys().index(dependency), 'target':imagesById.keys().index(dependencies[dependency])})
	return result

reduceDependencies(imagesById, imageDependencies)

orderedImages = []
for imageId in imagesById:
	orderedImages.append(imagesById[imageId])

def containersAsNodes(containers):
	containerNodes = []
	for container in containers:
		containerNodes.append({
				'imageName':container['Name'],
				'id':container['Id'],
				'group':3
			})
	return containerNodes

def containerDependencies(containers, orderedImages):
	result = []
	i = 0;
	for container in containers:
		source = len(orderedImages) + i
		target = 0

		j = 0;
		for image in orderedImages:
			if container['Image'].startswith(image['id']):
				target = j
				break
			j = j + 1

		result.append({'source':source, 'target':target})
		i = i + 1
	return result

with open('graph.json', 'w') as fp:
    json.dump(
    	{
			'nodes': orderedImages + containersAsNodes(containers),
			'links': dependenciesAsIndexes(imagesById, imageDependencies) + containerDependencies(containers, orderedImages)
		}, fp)
