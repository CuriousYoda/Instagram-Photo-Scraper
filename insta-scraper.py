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
from clint.textui import progress
import re

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


def getBaseUrlForUserposts(userId):
    postsToFetchInOneCall = readProperty("POSTS_TO_FETCH_IN_ONE_CALL")
    return "https://www.instagram.com/graphql/query/?query_id=" \
        "17888483320059182&id=" + userId + "&first=" + postsToFetchInOneCall


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


def isUserPostAVideo(post):
    return post['is_video']


# Create the folder for saving the posts
def createFolder(userName):
    instaFolder = readProperty("BASE_FOLDER")
    if not os.path.isdir(instaFolder):
        os.makedirs(instaFolder)

    postFolder = instaFolder + "/" + userName
    if not os.path.isdir(postFolder):
        os.makedirs(postFolder)

    return postFolder


def getInstaBasePostUrl():
    return "https://www.instagram.com/p/"


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
        response = requests.get(url, stream=True, headers={
                                'User-Agent': 'Mozilla/5.0 (Macintosh;'
                                'Intel Mac OS X 10_9_3) AppleWebKit/537.36'
                                '(KHTML, like Gecko) Chrome/35.0.1916.47'
                                'Safari/537.36'})
        responseCode = response.status_code

        if responseCode != 200:
            logging.info("\nError:" + str(responseCode))
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
        response = requests.get(url, stream=True, cookies=cookies, headers={
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


def isUserPostHasMultiple(post):
    if post['__typename'] == "GraphSidecar":
        return True
    else:
        return False


# Downloading the user videos is not straight forward.
# We need to extract it from the post
def downloadVideoFromInstapost(url, postFileName):
    response = requestUrl(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', text=re.compile('window\\._sharedData'))
    shared_data = script_tag.string.partition('=')[-1].strip(' ;')
    json_object = json.loads(shared_data)
    page = json_object['entry_data']['PostPage'][0]
    post_url = page['graphql']['shortcode_media']['video_url']
    if post_url:
        requestAndSaveUrlInChunk(post_url, postFileName)


# Downloading a post with multiple medias is not straight forward.
# We need to extract it from the post
def downloadMultipleMediaFromInstapost(url, postFileName):
    embedInstaPageResponse = requestUrl(url)
    soup = BeautifulSoup(embedInstaPageResponse.text, 'html.parser')
    script_tag = soup.find('script', text=re.compile('window\\._sharedData'))
    shared_data = script_tag.string.partition('=')[-1].strip(' ;')
    json_object = json.loads(shared_data)
    page = json_object['entry_data']['PostPage'][0]
    sideCars = page['graphql']['shortcode_media']['edge_sidecar_to_children']
    links = sideCars['edges']
    counter = 0
    for link in links:
        img_url = link['node']['display_url']
        fileName = postFileName + str(counter) + ".jpeg"
        requestAndSaveUrlInChunk(img_url, fileName)
        counter = counter + 1


def getPostCountToDownload(totalNumberOfposts):
    postCountToDownload = int(input(
        'How many posts should we download? '))
    if totalNumberOfposts < postCountToDownload:
        postCountToDownload = totalNumberOfposts
    return postCountToDownload


def getStartingPointForUserpostDownload():
    postCountToDownload = input(
        'From which post should we start the download ')
    if postCountToDownload:
        return int(postCountToDownload)
    else:
        return 1


def requestAndSaveUrlInChunk(url, postFileName):
    response = requestUrl(url)
    with open(postFileName, 'wb') as f:
        total_length = int(response.headers.get('content-length'))
        for chunk in progress.bar(response.iter_content(
                chunk_size=1024), expected_size=(total_length / 1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()


def downloadUserposts(instaLoggedIn=False):
    # We start with user name. If user keeps it empty,
    # we crawl for posts from Instagram official account
    userName = input(
        '\nEnter instagram username you want to explore:   ') or "instagram"

    # This is used to check whether we have more posts
    # left to download from the account.
    hasMorePosts = True

    # Using the username, we crawl for other user information
    userInfo = getUserinfo(userName)
    userId = userInfo['pk']
    userFullName = userInfo['full_name']
    if not userFullName:
        userFullName = userName

    # We create a folder to save posts
    folderName = createFolder(userFullName)

    # This is the generic url to retrieve the first batch of post information
    # It also has an end_cursor,
    # which we can use to query for the next pictures
    instaDataUrl = getBaseUrlForUserposts(userId)

    # we haven't started downloading yet. So these values are set to 0
    downloadCount = 0
    postCountToDownload = 0

    print("\nDownloading Instagram posts for "
          + userFullName)
    # Loop to go through call by call to fetch next 12 posts of the user.
    # Each call will reveal whether more posts are left to retrive
    while hasMorePosts:
        userData = json.loads(requestUrl(instaDataUrl).text)

        userMedia = userData['data']['user']['edge_owner_to_timeline_media']
        userPosts = userMedia['edges']
        endCursor = userMedia['page_info']['end_cursor']
        hasNextPage = userMedia['page_info']['has_next_page']
        totalNumberOfposts = userMedia['count']

        if postCountToDownload == 0:
            print("This account has a total of " +
                  str(totalNumberOfposts) + " posts")
            postCountToDownload = getPostCountToDownload(totalNumberOfposts)
            startingPoint = getStartingPointForUserpostDownload()

        if str(hasNextPage).lower() == "false":
            hasMorePosts = False

        if startingPoint > len(userPosts):
            instaDataUrl = getBaseUrlForUserposts(
                userId) + "&after=" + endCursor
            startingPoint = startingPoint - len(userPosts)
            continue

        print("\nWe have currently downloaded " + str(downloadCount) +
              " posts and plan to download " + str(postCountToDownload))
        print("We have " + str(postCountToDownload - downloadCount) +
              " more posts to download\n")

        for post in userPosts:
            shortPostCode = post['node']['shortcode']
            display_url = post['node']['display_url']
            isItAVideo = isUserPostAVideo(post['node'])
            isItMultipleMedia = isUserPostHasMultiple(post['node'])

            if isItAVideo:
                postFileName = folderName + "/" + shortPostCode + ".mp4"
            else:
                postFileName = folderName + "/" + shortPostCode + ".jpeg"

            if startingPoint > 1:
                startingPoint = startingPoint - 1
                continue

            if os.path.isfile(postFileName):
                print("Skipped. Already downloaded post")
                continue

            downloadCount = downloadCount + 1
            postUrl = getInstaBasePostUrl() + shortPostCode

            if isItAVideo:
                downloadVideoFromInstapost(postUrl, postFileName)
            elif isItMultipleMedia:
                fileName = folderName + "/" + shortPostCode
                downloadMultipleMediaFromInstapost(postUrl, fileName)
            else:
                requestAndSaveUrlInChunk(display_url, postFileName)

            print("Downloaded and saved post number: " + str(downloadCount))

            if (downloadCount >= postCountToDownload):
                print("\nCompleted. Downloaded " +
                      str(downloadCount) + " posts of " + userFullName + "\n")
                sys.exit()

        instaDataUrl = getBaseUrlForUserposts(userId) + "&after=" + endCursor


def getTotalPostCount(hashTagData):
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


def postCountToDownloadToDownload(posts):
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


def getHashTagPostElements(section):
    if getRunType() == RUN_TYPES.NORMAL:
        return section['layout_content']['medias']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return [section]
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def isItAVideo(post):
    if getRunType() == RUN_TYPES.NORMAL:
        if str(post['media']['media_type']) == "2":
            return True
        else:
            return False
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        if post['node']['__typename'] == "GraphVideo":
            return True
        else:
            return False
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getVideoLink(post):
    if getRunType() == RUN_TYPES.NORMAL:
        media = post['media']
        if media.get('video_versions'):
            return media['video_versions'][0]['url']
        else:
            return media['carousel_media'][0]['video_versions'][0]['url']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return post['node']['display_url']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getImageLink(post):
    if getRunType() == RUN_TYPES.NORMAL:
        media = post['media']
        if media.get('image_versions2'):
            return media['image_versions2']['candidates'][0]['url']
        else:
            return media['carousel_media'][0]['image_versions2']['candidates'][0]['url']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return post['node']['display_url']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getPostShortCode(post):
    if getRunType() == RUN_TYPES.NORMAL:
        return post['media']['code']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return post['node']['shortcode']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def getCategory(categoryInput):
    if categoryInput and categoryInput == "2":
        return "recent"
    else:
        return "top"


def getPostOwnerId(post):
    if getRunType() == RUN_TYPES.NORMAL:
        return post['media']['user']['username']
    elif getRunType() == RUN_TYPES.WITHOUT_LOGIN:
        return post['node']['owner']['id']
    else:
        logging.info("Not Supported this Run Type")
        sys.exit()


def downloadHashTagPosts(instaLoggedIn=False):
    # We start with user name. If user keeps it empty, we crawl for posts
    # from Instagram official account
    hashTag = input(
        '\nEnter HashTag you want to explore.": #') or "instagram"

    # There are two categroy of posts for a hashtag. Top or Most recent
    categoryInput = input(
        '\nDo you wish to download'
        '\n   1: Top Posts or\n   2: Recent Posts\n') or "1"
    category = getCategory(categoryInput)

    # This is used to check whether we have more posts
    # left to download from the hashtag.
    hasMorePosts = True

    # We have not started downloading yet, so these values are set to 0
    downloadCount = 0
    postCountToDownload = 0

    # We create folder to save posts
    folderName = createFolder("#" + hashTag)

    print("\nDownloading " + category +
          " Instagram Posts for #" + hashTag)

    hashTagDataUrl = getBaseUrlForHashTags(hashTag)

    while hasMorePosts:
        response = requestUrl(hashTagDataUrl)
        hashTagData = json.loads(response.text)

        totalpostCount = getTotalPostCount(hashTagData)
        posts = getHashTagPosts(hashTagData, category)
        hasMorePosts = postCountToDownloadToDownload(posts)
        if not hasMorePosts:
            logging.info("No posts found for the #" + hashTag)
            break
        endCursor = getEndCursor(posts)
        sections = getSections(posts)

        posts = []
        for section in sections:
            for post in getHashTagPostElements(section):
                posts.append(post)

        if category == "top":
            print("Downloading the top " + str(len(posts))
                  + " posts for #" + hashTag)
            postCountToDownload = len(posts)
        else:
            if postCountToDownload == 0:
                print("This hashtag has a total of " +
                      str(totalpostCount) + " posts")
                postCountToDownload = getPostCountToDownload(totalpostCount)

            print("\nWe have currently downloaded " + str(downloadCount) +
                  " posts and plan to download " + str(postCountToDownload))
            print("We have " + str(postCountToDownload - downloadCount) +
                  " more posts to download\n")

        for post in posts:
            isVideo = isItAVideo(post)

            if isVideo:
                mediaLink = getVideoLink(post)
                filetype = ".mp4"
            else:
                mediaLink = getImageLink(post)
                filetype = ".jpeg"

            userName = getPostOwnerId(post)
            shortPostCode = getPostShortCode(post)
            postFileName = folderName + "/" + shortPostCode + "@" + userName + filetype

            requestAndSaveUrlInChunk(mediaLink, postFileName) 

            downloadCount = downloadCount + 1
            print("Download and saved post number: " + str(downloadCount))

            if (downloadCount >= postCountToDownload):
                print("\nCompleted. Downloaded " +
                      str(downloadCount) + " posts of #" + hashTag + "\n")
                sys.exit()

        maxIdAppender = "&max_id=" + endCursor
        hashTagDataUrl = getBaseUrlForHashTags(hashTag) + maxIdAppender


# With RunType 1, we make authenticated calls. So as the first step, we login
# to the instagram and save our client cookies to be used in future calls
instaLoggedIn = False
if getRunType() == RUN_TYPES.NORMAL:
    instaLoggedIn = InstaLogin(getInstaUserName(), getInstaPassword()).login

# We provide options
print("\nWhat should we download today?\n")
print("     1. Posts from an Instagram Account")
print("     2. Posts from an Instagram Hashtag\n")
userChoice = input('Enter your choice: ') or "1"

if userChoice == "1":
    downloadUserposts(instaLoggedIn)
elif userChoice == "2":
    downloadHashTagPosts(instaLoggedIn)
else:
    logging.info("Invalid Option. App terminated")
    sys.exit()
