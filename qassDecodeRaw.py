#import lpbfman.helpers.helpers as helpers
import os
import json
import sys
import datetime
import time
import pandas as pd
import numpy as np
import warnings
import pickle
import pathlib
from tqdm import tqdm

#import lpbfman.logger.logManager as logMan
import logging
#logger = logMan.logManager(__name__)

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

""" COMPLETE REWRITE??? """

# Load parameter list from json object
try:
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    qass_buffer_structure = os.path.join(__location__, 'qassBufferStructure.json')
    with open(qass_buffer_structure) as json_file:
        paramSet = json.load(json_file)
except FileNotFoundError as e:
    print("[-] ERROR: JSON buffer structure file not found: {}".format(e))
    print('[-] ERROR: Quitting...')
    sys.exit(0)


def getParamSize(paramLocation, paramName):
    """returns the size of paramter value (bit) or double for 'frqpband'

    Arguments:
        paramLocation {str} -- 'fileheader','datablock','subdata'
        paramName {str} -- ASCII tag as in QASS documentation

    Returns:
        [type] -- [description]
    """
    try:
        paramSize = paramSet[paramLocation][paramName]
        if paramSize == '32':
            return 4
        elif paramSize == '64':
            return 8
        elif paramSize == 'double':
            return 8

    except KeyError as e:
        paramSize = str(e) + ' not found in parameter list'
    return paramSize


def convertParamValue2(bytes):
    """converts a binary bitstream to integer value and returns it

    Arguments:
        bytes {byte} -- the data to convert

    Returns:
        int -- the bytes converted to an integer
    """
    # faster than convertParamValue
    return int.from_bytes(bytes, byteorder='little', signed=False)


def parseFileHeader(object_file):
    """parses the file header of a qass binary file

    Arguments:
        object_file {str} -- file path of the qass binary file

    Returns:
        dict -- fileheader map as a dictionary
    """

    result = {}
    with open(object_file, "rb") as binaryFile:
        binaryFile.seek(8)
        coupleBytes = binaryFile.read(4)
        bitString = ' '.join(map(lambda x: '{:08b}'.format(x), coupleBytes))
        bitArray = bitString.split()
        headerSize = int(bitArray[3] + bitArray[2] +
                         bitArray[1] + bitArray[0], 2)
        #logger.info('\n[+] Header size: ' + str(headerSize) + ' bytes')

        pos = 0
        while pos < headerSize:
            # read ASCII tags and get value size
            binaryFile.seek(pos)
            paramName = (binaryFile.read(8)).decode("utf-8")
            paramSize = getParamSize('fileheader', paramName)

            if paramSize == '0':
                #logger.info('[+] Reached end of header...\n\n')
                # result = [0, headerSize]
                return result
                # break

            # read value
            paramValueBytes = binaryFile.read(int(paramSize))
            paramValue = convertParamValue2(paramValueBytes)

            if paramName == 'sparemem':
                paramSize += int(paramValue)
            elif paramName == 'comments':
                paramSize += int(paramValue)
                paramValue = binaryFile.read(int(paramValue))
            elif paramName == 'frqpband':
                paramName = 'frqpband (double)'

            #logger.info('[+] ' + str(paramName) +
            #             "(" + str(paramSize) + " Byte) Value: " + str(paramValue))
            result[paramName] = paramValue

            pos += 8 + int(paramSize)


def parseBuffer(object_file):
    """parses qass binary file for data blocks

    Arguments:
        object_file {str} -- file path of qass binary

    Returns:
        list -- list of all data blocks with start and end of data block
    """
    # calculate file size of buffer
    statinfo = os.stat(object_file)
    fileSize = statinfo.st_size
    #logger.info('[+] File size: ' + str(fileSize) +
    #             ' bytes (' + str(hex(fileSize)) + ')')

    result = []
    with open(object_file, "rb") as binaryFile:
        binaryFile.seek(0)
        bitStream = binaryFile.read(fileSize)
        pos = 0

        # HEADER
        headerStartTag = str.encode('qassdata')
        headerStopTag = str.encode('headsend')
        headerStart = bitStream.find(headerStartTag)
        headerStop = bitStream.find(headerStopTag) + 8

        result.append([headerStart, headerStop])

        #logger.info('\n[+] Found headerblock at ' +
        #             str(hex(headerStart)) + ' to ' + str(hex(headerStop)))

        pos = headerStop
        # DATABLOCKS
        datablockNumber = 1
        datablockStartTag = str.encode('blochead')
        while pos < fileSize:
            datablockStart = bitStream.find(datablockStartTag, pos)
            datablockStop = bitStream.find(
                datablockStartTag, datablockStart + 1)
            if datablockStop == -1:
                datablockStop = fileSize
            datablockSize = datablockStop - datablockStart
            pos += datablockSize

            #logger.info('[+] Found datablock ' + str(datablockNumber) + ' at ' + str(hex(datablockStart)) +
            #             ' to ' + str(hex(datablockStop)) + ' (size: ' + str(datablockSize) + ' bytes)')

            result.append([datablockStart, datablockStop])
            datablockNumber += 1

    return result


def parseDataBlock(object_file, range, number):
    """parses a single data block in qass binary file

    Arguments:
        object_file {str} -- file path of the qass binary file
        range {list} -- list containing of datablock start and end
        number {int} -- the number of the datablock in file

    Returns:
        list -- list with start and end of data in datablock and header
    """
    #logger.info('\n[+] Parsing datablock ' + str(number))
    startPos = range[0]
    stopPos = range[1]
    result = []

    with open(object_file, "rb") as binaryFile:
        binaryFile.seek(startPos)
        bitStream = binaryFile.read(stopPos - startPos)

        headerStopTag = str.encode('blockend')
        headerStart = startPos
        headerStop = bitStream.find(headerStopTag) + startPos + 8
        result.append([headerStart, headerStop])
        #logger.info('[+] Found datablock header at ' +
        #             str(hex(startPos)) + ' to ' + str(hex(headerStop)))
        dataStart = headerStop
        dataStop = stopPos
        result.append([dataStart, dataStop])

        #logger.info('[+] Found datablock data at ' +
        #             str(hex(dataStart)) + ' to ' + str(hex(dataStop)))
        return result


def generateBufferMap(object_file):
    """generates buffermap from all datablocks

    Arguments:
        object_file {str} -- file path of the qass binary file

    Returns:
        list -- buffer structure of file
    """
    print("1/3 generate Buffer Map... ", end = ' ')
    #logger.info('[+] File: ' + object_file)
    bufferStructure = []

    datablocks = parseBuffer(object_file)
    
    for x in tqdm(range(1, len(datablocks))):
        bufferStructure.append(parseDataBlock(object_file, datablocks[x], x))

    #logger.info('[+] SUCESS: Buffer map generated\n')
    #logger.debug("[+] Buffer Map:\r\n")
    #logger.debug(bufferStructure)
    print("  done")
    return bufferStructure


def decodeDataBlock(start, stop, object_file, samples_per_frame, bytes_per_sample):
    """decodes a given datablock

    Arguments:
        start {int} -- start of datablock
        stop {int} -- end of datablock
        object_file {str} -- file path of the qass binary file
        samples_per_frame {int} -- samplerate??
        bytes_per_sample {int} -- number of bytes which are used per sample

    Returns:
        list -- decoded datablock
    """
    result = []
    row = []

    with open(object_file, "rb") as binaryFile:
        binaryFile.seek(start)
        index = 0
        pos = start
        while pos < stop:
            binaryFile.seek(pos)
            bitStream = binaryFile.read(bytes_per_sample)
            value = convertParamValue2(bitStream) - 32768 + 18
            row.append(value)
            pos += bytes_per_sample
            index += bytes_per_sample
            if len(row) % samples_per_frame == 0:
                buff = row[:]
                result.extend(buff)
                row.clear()
    return result

def decodeAllDataBlocks(bufferMap, object_file, samples_per_frame, bytes_per_sample):
    """wrapper to decode all datablocks

    Arguments:
        bufferMap {list} -- preprocessed buffermap
        object_file {str} -- file path of the qass binary file
        samples_per_frame {int} -- samplerate???
        bytes_per_sample {int} -- number of bytes which are used per sample

    Returns:
        list -- decoded file
    """
    print("3/3 decode all data blocks... ", end = ' ')
    filename = object_file.name
    object_number = (filename.split("_"))[2]
    # object_number = (object_number.split("."))[0]
    result = []
    counter = 1
    
    
    # iterate through all datablock in buffermap and decode them
    for datablock in tqdm(bufferMap):
        result.extend(
            decodeDataBlock(datablock[1][0], datablock[1][1], object_file, samples_per_frame, bytes_per_sample))
        counter += 1
        #print("{}/{}".format(counter , len(bufferMap)))
    print("  done")
    return result


'''
def decodeAllDataBlocks(bufferMap, object_file, samples_per_frame, bytes_per_sample):
    """wrapper to decode all datablocks

    Arguments:
        bufferMap {list} -- preprocessed buffermap
        object_file {str} -- file path of the qass binary file
        samples_per_frame {int} -- samplerate???
        bytes_per_sample {int} -- number of bytes which are used per sample

    Returns:
        list -- decoded file
    """
    object_file = pathlib.Path(object_file)
    object_file = object_file.as_posix()
    filename = object_file.split("/")[-1]
    filename = filename.replace("_00.000", ".p")

    # object_number = (filename.split("_"))[2]
    # object_number = (object_number.split("."))[0]
    result = []
    storeThis= []
    counter = 1

    if os.path.isfile(filename): # Python is struggling with already existing files after an error occurred
        os.remove(filename)

    # iterate through all datablock in buffermap and decode them
    for datablock in bufferMap:
        #Lukas:
        #result.extend(decodeDataBlock(datablock[1][0], datablock[1][1], object_file, samples_per_frame, bytes_per_sample))
        #Denis: The reason I used this is MemoryError prevention
        storeThis.extend(decodeDataBlock(datablock[1][0], datablock[1][1], object_file, samples_per_frame, bytes_per_sample))
        if counter % 20 == 0 or len(bufferMap)-counter <2:
            with open(filename, "ab") as fp:  # Pickling
                pickle.dump(storeThis, fp) # save
            storeThis.clear() # free up memory
        counter += 1
        print("{}/{}".format(counter, len(bufferMap)))
    # Denis: following 7 lines
    fp = open(filename, "rb")  # Unpickling
    result = pickle.load(fp)
    fp.close()
    if os.path.isfile(filename):
        os.remove(filename)
    else:  ## Show an error ##
        print("Error: %s file not found" % filename)
    return result
'''

def parseDataBlockHeader(start, stop, object_file):
    """parsed the header of a datablock

    Arguments:
        start {int} -- start of header data block
        stop {int} -- end of header data block
        object_file {str} -- file path of the qass binary file
    """
    with open(object_file, "rb") as binaryFile:
        binaryFile.seek(start)
        pos = start
        while pos < stop:
            paramName = (binaryFile.read(8)).decode("utf-8")
            paramSize = getParamSize('datablock', paramName)
            # read value
            paramValueBytes = binaryFile.read(int(paramSize))
            paramValue = convertParamValue2(paramValueBytes)
            #logger.debug('[+] ' + str(paramName) +
            #              "(" + str(paramSize) + " Byte) Value: " + str(paramValue))
            pos += 8 + int(paramSize)


def getFileHeaderValue(headerName, fileHeaderMap):
    """key->value in fileheadermap

    Arguments:
        headerName {str} -- name of parameter
        fileHeaderMap {list} -- preprocessed file header map

    Returns:
        [type] -- [description]
    """
    for i in fileHeaderMap:
        if i[0] == headerName:
            return i[1]
            # break


def countSamples(bufferMap, bytesPerSample):
    """gets number of samples in file

    Arguments:
        bufferMap {list} -- proprocessed bufferMap
        bytesPerSample {int} -- bytes per sample

    Returns:
        int -- total number of samples in file
    """
    samples = 0

    for i in bufferMap:
        start = i[1][0]
        stop = i[1][1]
        length = stop - start
        samples += length
    samples = int(samples / bytesPerSample)
    return samples


def generateBufferReport(fileHeaderMap, bufferMap):
    """crate human readable report of buffer file

    Arguments:
        fileHeaderMap {dict} -- preprocessed fileheaderMap
        bufferMap {list} -- preprocessed bufferMap

    Returns:
        dict -- fileheaderMap
    """
    print("1/3 generate Buffer Report... ", end = ' ')
    #logger.info('[+] Generating report for buffer file...\n')
    ts = datetime.datetime.fromtimestamp(
        int(fileHeaderMap['proctime'])).strftime('%Y-%m-%d_%H-%M-%S')
    #logger.info('[+] Measure date: ' + str(ts))
    #logger.info('[+] Data mode: ' + str(fileHeaderMap['datamode']))
    #logger.info('[+] Data type: ' + str(fileHeaderMap['datatype']))
    #logger.info('[+] Samples per Frame: ' + str(fileHeaderMap['s_p_fram']))
    #logger.info('[+] Bytes per Sample: ' + str(fileHeaderMap['b_p_samp']))
    #logger.info('[+] Sample rate: ' + str(fileHeaderMap['samplert']) + ' samples/second')
    #logger.info('[+] Compression ratio: ' + str(fileHeaderMap['comratio']))
    #logger.info('[+] Sample frequency: ' + str(fileHeaderMap['samplefr']) + ' Hz')

    nrSamples = countSamples(bufferMap, fileHeaderMap['b_p_samp'])
    nrFrames = nrSamples / fileHeaderMap['s_p_fram']
    tMeasure = nrSamples / fileHeaderMap['samplert']
    dt = tMeasure / nrFrames
    fileHeaderMap['dt'] = dt
    fileHeaderMap['tMeasure'] = tMeasure
    fileHeaderMap['nrFrames'] = nrFrames
    fileHeaderMap['nrSamples'] = nrSamples
    fileHeaderMap['timeString'] = ts
    #logger.info('[+] Time increment: ' + str(dt) + ' s')
    #logger.info('[+] Time time: ' + str(tMeasure) + ' s')
    #logger.info('[+] Total samples: ' + str(nrSamples))
    
    print("  done")
    
    return fileHeaderMap


def dataStore(data, file_header_map, output_file):
    """stores decoded binary file on disk

    Arguments:
        data {dataframe} -- the decoded data
        file_header_map {dict} -- preprocessed fileheadermap
        output_file {str} -- filename of output file

    Returns:
        str -- filename of output data
    """
    np_data = np.asarray(data)

    filename_data = output_file
    identifier_data = 'raw'
    df_data = pd.DataFrame(np_data)

    df_header = pd.DataFrame([{'fileHeaderMap': file_header_map}])
    identifier_header = 'file_header_map'
    filename_header = filename_data.replace('raw_layer', 'header_layer')

    df_data.to_hdf(filename_data, identifier_data, mode='w', complevel=1, complib='zlib') # complevel beeinflusst die zlib komprimierrung also einmal auf 9 stellen
    df_header.to_hdf(filename_header, identifier_header, mode='a', complevel=1, complib='zlib')
    return filename_data

def qassDecodeRaw(object_file, return_fileHeaderMap = True):
    buffer_map = generateBufferMap(object_file)
    file_header_map = generateBufferReport(parseFileHeader(object_file), buffer_map)
    data = decodeAllDataBlocks(buffer_map, object_file, file_header_map['s_p_fram'], file_header_map['b_p_samp'])
    
    if return_fileHeaderMap:
        return data, file_header_map
    else:
        return data
