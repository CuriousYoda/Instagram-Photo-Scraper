__author__ = "@CuriousYoda"
__copyright__ = "Copyright (C) 2021 @CuriousYoda"
__license__ = "MIT"
__version__ = "1.0"

import json
from bs4 import BeautifulSoup
import os
import requests
from enum import Enum
import sys
import configparser
from instalog import InstaLogin
import time
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    '--debug',
    action='store_true',
    help='print debug messages')
args = parser.parse_args()
if args.debug:
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
else:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)


class RUN_TYPES(str, Enum):
    NORMAL = "1"
    PROXY = "2"
    WITHOUT_LOGIN = "3"


def getRunType():
    return readProperty("RUN_TYPE")


def readProperty(propertyValue):
    config = configparser.RawConfigParser()
    config_file = open('insta-scraper.properties', encoding="utf-8")
    config.read_file(config_file)
    value = config.get("UserInput", propertyValue)
    if not value:
        logging.info("Missing property value: " + propertyValue)
        sys.exit()
    return value


def getCookies():
    cookies = json.load(open("cookies.txt"))
    return cookies


def requestUrl(url, retries=1):
    runType = getRunType()
    if runType == RUN_TYPES.WITHOUT_LOGIN:
        return requestUrlWithoutLogin(url, retries)
    else:
        return requestUrlNormal(url, retries)


def isAJsonResponse(responseType):
    if 'application/json' in responseType:
        return True
    else:
        return False


def getBaseUrlForHashTags(hashTag):
    return "https://www.instagram.com/explore/tags/" + hashTag + "/?__a=1"


def getBaseUrlForUserPhotos(userId):
    photosToFetchInOneCall = readProperty("PHOTOS_TO_FETCH_IN_ONE_CALL")
    return "https://www.instagram.com/graphql/query/?query_id=" \
        "17888483320059182&id=" + userId + "&first=" + photosToFetchInOneCall


def getUserInfoRequestUrl(userName):
    return "https://www.instagram.com/web/search/topsearch/?context=" \
        "blended&query=" \
        + userName + "&rank_token=0.3953592318270893&count=1"


# First call to get the basic user information such as the userId
def getUserinfo(userName):
    try:
        userInfo = {}
        userInfoRequestUrl = getUserInfoRequestUrl(userName)
        response = requestUrl(userInfoRequestUrl)
        responseType = response.headers.get('content-type')
        if isAJsonResponse(responseType):
            userInfoRequestData = json.loads(response.text)
            userInfo = userInfoRequestData['users'][0]['user']
        else:
            logging.info("\nError: Try again after a while")
            logging.debug(userInfoRequestUrl + " resulted a response type: "
                          + responseType)
            sys.exit()
        return userInfo
    except Exception as e:
        logging.info("\nERROR in retriving basic user details")
        logging.debug('Error on line {}'.format(sys.exc_info()
                                                [-1].tb_lineno), type(e).__name__, e, "\n")
        sys.exit()


# Create the folder for saving the photos
def createFolder(userName):
    instaFolder = readProperty("BASE_FOLDER")
    if not os.path.isdir(instaFolder):
        os.makedirs(instaFolder)

    photoFolder = instaFolder + "/" + userName
    if not os.path.isdir(photoFolder):
        os.makedirs(photoFolder)

    return photoFolder


def getInstaUserName():
    return readProperty("INSTA_USER_NAME")


def getInstaPassword():
    return readProperty("INSTA_PASSWORD")


def retrySameUrl(url, retries):
    if (retries <= 3):
        logging.info("Retry attempt: " + str(retries) +
                     " for the same url in 5 seconds")
        retries = retries + 1
        time.sleep(5)
        requestUrl(url, retries)
    else:
        logging.info("Retried for three times unsuccessfully")
        sys.exit()


# This is the common method for sending a Url request
def requestUrlWithoutLogin(url, retries=1):
    try:
        response = requests.get(url, headers={
                                'User-Agent': 'Mozilla/5.0 (Macintosh;'
                                'Intel Mac OS X 10_9_3) AppleWebKit/537.36'
                                '(KHTML, like Gecko) Chrome/35.0.1916.47'
                                'Safari/537.36'})
        responseCode = response.status_code

        if responseCode != 200:
            logging.info("\nError:"+str(responseCode))
            logging.debug("Request returned a " + str(responseCode) + "\n")
            retrySameUrl(url, retries)
        else:
            return response
    except Exception as e:
        logging.info("\nERROR retrieving content")
        logging.debug("\nERROR retrieving content" + url)
        logging.debug('Error on line {}'.format(sys.exc_info()
                                                [-1].tb_lineno), type(e).__name__, e, "\n")
        retrySameUrl(url, retries)


# This is the common method for sending a Url request
def requestUrlNormal(url, retries=1):
    try:
        cookies = getCookies()
        response = requests.get(url, cookies=cookies, headers={
                                'User-Agent': 'Mozilla/5.0 (Macintosh;'
                                'Intel Mac OS X 10_9_3) AppleWebKit/537.36'
                                '(KHTML, like Gecko) Chrome/35.0.1916.47'
                                'Safari/537.36'})
        responseCode = response.status_code
        if responseCode != 200:
            logging.info("\nERROR retrieving content")
            logging.debug("\nERROR retrieving content" + url)
            logging.debug("Request returned a " + str(responseCode) + "\n")
            retrySameUrl(url, retries)
        else:
            return response
    except Exception as e:
        logging.info("\nERROR retrieving content")
        logging.debug("\nERROR: " + url)
        logging.debug('Error on line {}'.format(sys.exc_info()
                                                [-1].tb_lineno), type(e).__name__, e, "\n")
        retrySameUrl(url, retries)


# Once we have the link to insta image,
# we extract the direct image link and download the photo
def downloadInstaPhoto(url):
    embedInstaPageResponse = requestUrl(url)
    soup = BeautifulSoup(embedInstaPageResponse.text, 'html.parser')
    img_url = soup.find_all('img')[1]['src']
    if img_url:
        imageResponse = requestUrl(img_url)
        return imageResponse
    else:
        return embedInstaPageResponse


def getPhotoCountToDownload(totalNumberOfPhotos):
    photoCountToDownload = int(input(
        'How many photos should we download? '))
    if totalNumberOfPhotos < photoCountToDownload:
        photoCountToDownload = totalNumberOfPhotos
    return photoCountToDownload


def getStartingPointForUserPhotoDownload():
    photoCountToDownload = input(
        'From which photo should we start the download ')
    if photoCountToDownload:
        return int(photoCountToDownload)
    else:
        return 1


def downloadUserPhotos(instaLoggedIn=False):
    # We start with user name. If user keeps it empty,
    # we crawl for images from Instagram official account
    userName = input(
        '\nEnter instagram username you want to explore:   ') or "instagram"

    # This is used to check whether we have more photos
    # left to download from the account.
    hasMorePhotos = True

    # Using the username, we crawl for other user information
    userInfo = getUserinfo(userName)
    userId = userInfo['pk']
    userFullName = userInfo['full_name']
    if not userFullName:
        userFullName = userName

    # We create a folder to save images
    folderName = createFolder(userFullName)

    # This is the generic url to retrieve the first batch of photo information
    # It also has an end_cursor,
    # which we can use to query for the next pictures
    instaDataUrl = getBaseUrlForUserPhotos(userId)

    # we haven't started downloading yet. So these values are set to 0
    downloadCount = 0
    photoCountToDownload = 0

    print("\nDownloading Instagram Photos for "
          + userFullName)
    # Loop to go through call by call to fetch next 12 photos of the user.
    # Each call will reveal whether more photos are left to retrive
    while hasMorePhotos:
        userData = json.loads(requestUrl(instaDataUrl).text)

        userMedia = userData['data']['user']['edge_owner_to_timeline_media']
        userPosts = userMedia['edges']
        endCursor = userMedia['page_info']['end_cursor']
        hasNextPage = userMedia['page_info']['has_next_page']
        totalNumberOfPhotos = userMedia['count']

        if photoCountToDownload == 0:
            print("This account has a total of " +
                  str(totalNumberOfPhotos) + " photos")
            photoCountToDownload = getPhotoCountToDownload(totalNumberOfPhotos)
            startingPoint = getStartingPointForUserPhotoDownload()

        if str(hasNextPage).lower() == "false":
            hasMorePhotos = False

        if startingPoint > len(userPosts):
            instaDataUrl = getBaseUrlForUserPhotos(userId) + "&after=" + endCursor
            startingPoint = startingPoint - len(userPosts)
            continue

        print("\nWe have currently downloaded " + str(downloadCount) +
              " photos and plan to download " + str(photoCountToDownload))
        print("We have " + str(photoCountToDownload - downloadCount) +
              " more photos to download\n")

        for post in userPosts:
            shortImageName = post['node']['shortcode']
            display_url = post['node']['display_url']
            response = requestUrl(display_url)
            imageFileName = folderName + "/" + shortImageName + ".jpeg"

            if startingPoint > 1:
                startingPoint = startingPoint - 1
                continue

            if os.path.isfile(imageFileName):
                print("Skipped. Already downloaded photo")
                continue

            with open(imageFileName, 'wb') as f:
                downloadCount = downloadCount + 1
                f.write(response.content)
                f.close()
                print("Download and saved photo number: " + str(downloadCount))

            if (downloadCount >= photoCountToDownload):
                print("\nCompleted. Downloaded " +
                      str(downloadCount) + " photos of " + userFullName + "\n")
                sys.exit()

        instaDataUrl = getBaseUrlForUserPhotos(userId) + "&after=" + endCursor


def getTotalPhotoCount(hashTagData):
    if getRunType() == RUN_TYPES.NORMAL:
        return hashTagData['data']['media_count']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return hashTagData['graphql']['hashtag']['edge_hashtag_to_media']['count']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getHashTagPosts(hashTagData, category):
    if getRunType() == RUN_TYPES.NORMAL:
        return hashTagData['data'][category]
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return hashTagData['graphql']['hashtag']['edge_hashtag_to_media']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def hasMorePhotosToDownload(posts):
    if getRunType() == RUN_TYPES.NORMAL:
        return posts['more_available']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return posts['page_info']['has_next_page']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getEndCursor(posts):
    if getRunType() == RUN_TYPES.NORMAL:
        return posts['next_max_id']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return posts['page_info']['end_cursor']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getSections(posts):
    if getRunType() == RUN_TYPES.NORMAL:
        return posts['sections']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return posts['edges']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getHashTagImageElements(section):
    if getRunType() == RUN_TYPES.NORMAL:
        return section['layout_content']['medias']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return [section]
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getImageLink(image):
    if getRunType() == RUN_TYPES.NORMAL:
        media = image['media']
        if media.get('image_versions2'):
            return media['image_versions2']['candidates'][0]['url']
        else:
            return media['carousel_media'][0]['image_versions2']['candidates'][0]['url']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return image['node']['display_url']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getImageCode(image):
    if getRunType() == RUN_TYPES.NORMAL:
        return image['media']['code']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return image['node']['shortcode']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getCategory(categoryInput):
    if categoryInput and categoryInput == "2":
        return "recent"
    else:
        return "top"


def downloadHashTagPhotos(instaLoggedIn=False):
    # We start with user name. If user keeps it empty, we crawl for images
    # from Instagram official account
    hashTag = input(
        '\nEnter HashTag you want to explore.": #') or "instagram"

    # There are two categroy of photos for a hashtag. Top or Most recent
    categoryInput = input(
        '\nDo you wish to download'
        '\n   1: Top Posts or\n   2: Recent Posts\n') or "1"
    category = getCategory(categoryInput)

    # This is used to check whether we have more photos
    # left to download from the hashtag.
    hasMorePhotos = True

    # We have not started downloading yet, so these values are set to 0
    downloadCount = 0
    photoCountToDownload = 0

    # We create folder to save images
    folderName = createFolder("#" + hashTag)

    print("\nDownloading " + category +
          " Instagram Photos for #" + hashTag)

    hashTagDataUrl = getBaseUrlForHashTags(hashTag)

    while hasMorePhotos:
        response = requestUrl(hashTagDataUrl)
        hashTagData = json.loads(response.text)

        totalPhotoCount = getTotalPhotoCount(hashTagData)
        posts = getHashTagPosts(hashTagData, category)
        hasMorePhotos = hasMorePhotosToDownload(posts)
        if not hasMorePhotos:
            logging.info("No images found for the #" + hashTag)
            break
        endCursor = getEndCursor(posts)
        sections = getSections(posts)

        images = []
        for section in sections:
            for image in getHashTagImageElements(section):
                images.append(image)

        if category == "top":
            print("Downloading the top " + str(len(images))
                  + " photos for #" + hashTag)
            photoCountToDownload = len(images)
        else:
            if photoCountToDownload == 0:
                print("This hashtag has a total of " +
                      str(totalPhotoCount) + " photos")
                photoCountToDownload = getPhotoCountToDownload(totalPhotoCount)

            print("\nWe have currently downloaded " + str(downloadCount) +
                  " photos and plan to download " + str(photoCountToDownload))
            print("We have " + str(photoCountToDownload - downloadCount) +
                  " more photos to download\n")

        for image in images:
            mediaLink = getImageLink(image)
            response = requestUrl(mediaLink)
            shortImageName = getImageCode(image)
            imageFileName = folderName + "/" + shortImageName + ".jpeg"

            if os.path.isfile(imageFileName):
                print("Skipped. Already downloaded photo")
                continue

            with open(imageFileName, 'wb') as f:
                downloadCount = downloadCount + 1
                f.write(response.content)
                f.close()
                print("Download and saved photo number: " +
                      str(downloadCount))

            if (downloadCount >= photoCountToDownload):
                print("\nCompleted. Downloaded " +
                      str(downloadCount) + " of #" + hashTag + "\n")
                sys.exit()

        hashTagDataUrl = getBaseUrlForHashTags(
            hashTag) + "&max_id=" + endCursor


# With RunType 1, we make authenticated calls. So as the first step, we login
# to the instagram and save our client cookies to be used in future calls
instaLoggedIn = False
if getRunType() == RUN_TYPES.NORMAL:
    instaLoggedIn = InstaLogin(getInstaUserName(), getInstaPassword()).login

# We provide options
print("\nWhat should we download today?\n")
print("     1. Photos from an Instagram Account")
print("     2. Photos from an Instagram Hashtag\n")
userChoice = input('Enter your choice: ') or "1"

if userChoice == "1":
    downloadUserPhotos(instaLoggedIn)
elif userChoice == "2":
    downloadHashTagPhotos(instaLoggedIn)
else:
    logging.info("Invalid Option. App terminated")
    sys.exit()
