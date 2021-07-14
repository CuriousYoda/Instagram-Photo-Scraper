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


def requestUrl(url, retries=1, user_agent=""):
    runType = getRunType()
    if runType == RUN_TYPES.WITHOUT_LOGIN:
        return requestUrlWithoutLogin(url, retries, user_agent)
    else:
        return requestUrlNormal(url, retries, user_agent)


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
def requestUrlWithoutLogin(url, retries=1, user_agent=""):
    try:
        if not user_agent:
            user_agent = readProperty("USER_AGENT")
        response = requests.get(url, stream=True, headers={
                                'User-Agent': user_agent})

        if len(response.history) > 1:
            if response.history[0].status_code == 302:
                print("IP is restricted. Try again after few hours.")
                sys.exit()

        return response
    except Exception as e:
        logging.info("\nERROR retrieving content")
        logging.debug("\nERROR retrieving content" + url)
        logging.debug('Error on line {}'.format(sys.exc_info()
                                                [-1].tb_lineno), type(e).__name__, e, "\n")
        retrySameUrl(url, retries)


# This is the common method for sending a Url request
def requestUrlNormal(url, retries=1, user_agent=""):
    try:
        if not user_agent:
            user_agent = readProperty("USER_AGENT")
        cookies = getCookies()
        response = requests.get(url, stream=True, cookies=cookies, headers={
                                'User-Agent': user_agent})

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
    success = True
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
        if os.path.isfile(fileName):
            print("Skipped. File exists.")
            success = False
            continue
        requestAndSaveUrlInChunk(img_url, fileName)
        counter = counter + 1
    return success


def getTargetDownloadCount(totalPostCount):
    targetPostCount = int(input(
        'Number of posts to download: '))
    if totalPostCount < targetPostCount:
        targetPostCount = totalPostCount
    return targetPostCount


def getStartingPointForUserpostDownload():
    targetPostCount = input(
        'Start from (keep empty to start from the beginning): ')
    print("")
    if targetPostCount:
        return int(targetPostCount)
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


def hasMorePostsToDownload(posts):
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


def getPostListForHashTagSections(sections):
    posts = []
    for section in sections:
        for post in getHashTagPostElements(section):
            posts.append(post)

    return posts


def getCountForDownloadCategory(category, posts):
    totalpostCount = getTotalPostCount(posts)
    targetCount = 0
    if category == "top":
        print("Downloading the top " + str(len(posts)))
        targetCount = len(posts)
    else:
        if targetCount == 0:
            print("Total of " + str(totalpostCount) + " recent posts")
            targetCount = getTargetDownloadCount(totalpostCount)
    return targetCount


def getUserNameFromUserId(userId):
    user_agent = readProperty("USER_AGENT1")
    url = "https://i.instagram.com/api/v1/users/" + userId + "/info/"
    response = requestUrl(url, 1, user_agent)
    json_object = json.loads(response.text)
    return json_object['user']['username']


def getFileName(post):
    isVideo = isItAVideo(post)

    if isVideo:
        filetype = ".mp4"
    else:
        filetype = ".jpeg"

    userId = getPostOwnerId(post)
    userName = getUserNameFromUserId(userId)
    shortPostCode = getPostShortCode(post)

    fileName = userName + "@" + shortPostCode + filetype
    return fileName


def savePost(post, postFileName):
    isVideo = isItAVideo(post)
    shortPostCode = getPostShortCode(post)

    if isVideo:
        mediaLink = getVideoLink(post)
    else:
        mediaLink = getImageLink(post)

    if isVideo:
        postUrl = getInstaBasePostUrl() + shortPostCode
        downloadVideoFromInstapost(postUrl, postFileName)
    else:
        requestAndSaveUrlInChunk(mediaLink, postFileName)


def processOneBatch(hashTagPosts, folderName, counter, totalTarget):
    sections = getSections(hashTagPosts)
    posts = getPostListForHashTagSections(sections)
    for post in posts:
        postFileName = folderName + "/" + getFileName(post)
        if os.path.isfile(postFileName):
            print("Skipped. File exists")
            continue
        savePost(post, postFileName)

        counter = counter + 1
        print("Saved post number: " + str(counter))

        if (counter >= totalTarget):
            print("\nCompleted.")
            print("Downloaded " + str(counter) + " posts.")
            sys.exit()
    return counter


def getHashTagData(hashTag, urlApennder=""):
    hashTagDataUrl = getBaseUrlForHashTags(hashTag) + urlApennder
    response = requestUrl(hashTagDataUrl)
    hashTagData = json.loads(response.text)
    return hashTagData


def getUserMedia(instaDataUrl):
    userData = json.loads(requestUrl(instaDataUrl).text)
    userMedia = userData['data']['user']['edge_owner_to_timeline_media']
    return userMedia


def hasMoreUserPosts(userMedia):
    hasNextPage = userMedia['page_info']['has_next_page']
    if str(hasNextPage).lower() == "false":
        return False
    else:
        return True


def getEndCursorForUserPosts(userMedia):
    return userMedia['page_info']['end_cursor']


def getUserPosts(userMedia):
    return userMedia['edges']


def downloadHashTagPosts(instaLoggedIn=False):
    # We start with user name. If user keeps it empty, we crawl for posts
    # from Instagram official account
    hashTag = input('\nHashTag: #') or "instagram"

    # There are two categroy of posts for a hashtag. Top or Most recent
    print('\nCategory')
    print('\t1:Top Posts or\n\t2:Recent Posts')
    categoryInput = input("Input: ")
    category = getCategory(categoryInput)

    # We have not started downloading yet, so these values are set to 0
    counter = 0
    print("\nDownloading " + category + " Instagram Posts for #" + hashTag)

    hashTagData = getHashTagData(hashTag)
    if not hashTagData:
        print("No posts for the hashtag #" + hashTag)
        sys.exit()

    folderName = createFolder("#" + hashTag)
    targetCount = getCountForDownloadCategory(category, hashTagData)
    hashTagPosts = getHashTagPosts(hashTagData, category)
    hasMorePosts = hasMorePostsToDownload(hashTagPosts)
    counter = processOneBatch(hashTagPosts, folderName, counter, targetCount)

    while hasMorePosts:
        endCursor = getEndCursor(hashTagPosts)
        maxIdAppender = "&max_id=" + endCursor
        hashTagData = getHashTagData(hashTag, maxIdAppender)
        hashTagPosts = getHashTagPosts(hashTagData, category)
        hasMorePosts = hasMorePostsToDownload(hashTagPosts)
        counter = processOneBatch(
            hashTagPosts, folderName, counter, targetCount)

    print("No more posts for the hashtag #" + hashTag)


def procesUserPost(post, folderName):
    shortPostCode = post['node']['shortcode']
    display_url = post['node']['display_url']
    isItAVideo = isUserPostAVideo(post['node'])
    isItMultipleMedia = isUserPostHasMultiple(post['node'])

    if isItAVideo:
        postFileName = folderName + "/" + shortPostCode + ".mp4"
    else:
        postFileName = folderName + "/" + shortPostCode + ".jpeg"

    if os.path.isfile(postFileName):
        print("Skipped. File exists.")
        return False

    postUrl = getInstaBasePostUrl() + shortPostCode

    if isItAVideo:
        downloadVideoFromInstapost(postUrl, postFileName)
    elif isItMultipleMedia:
        fileName = folderName + "/" + shortPostCode
        return downloadMultipleMediaFromInstapost(postUrl, fileName)
    else:
        requestAndSaveUrlInChunk(display_url, postFileName)

    return True


def downloadUserposts(instaLoggedIn=False):
    # We start with user name. If user keeps it empty,
    # we crawl for posts from Instagram official account
    userName = input('\nInstagram username:   ')

    # This is used to check whether we have more posts
    # left to download from the account. By default, we set it to True
    hasMorePosts = True

    # Using the username, we crawl for other user information
    userInfo = getUserinfo(userName)
    userId = userInfo['pk']
    userFullName = userInfo['full_name']
    if not userFullName:
        userFullName = userName

    # This is the generic url to retrieve the first batch of post information
    # It also has an end_cursor,
    # which we can use to query for the next pictures
    instaDataUrl = getBaseUrlForUserposts(userId)
    print(instaDataUrl)
    # we haven't started downloading yet. So these values are set to 0
    downloadCount = 0
    targetPostCount = 0

    print("\nDownloading posts for " + userFullName)

    userMedia = getUserMedia(instaDataUrl)
    userPosts = getUserPosts(userMedia)
    hasMorePosts = hasMoreUserPosts(userMedia)
    numberOfPosts = len(userPosts)
    urlAppender = ""
    totalPostCount = userMedia['count']

    if totalPostCount == 0:
        print("No posts for this account")
        sys.exit()

    print("This account has " + str(totalPostCount) + " posts\n")
    targetPostCount = getTargetDownloadCount(totalPostCount)
    startingPoint = getStartingPointForUserpostDownload()
    folderName = createFolder(userFullName)

    while hasMorePosts:

        if startingPoint > numberOfPosts:
            instaDataUrl = getBaseUrlForUserposts(userId) + urlAppender
            startingPoint = startingPoint - numberOfPosts
            continue

        for post in userPosts:
            if startingPoint > 1:
                startingPoint = startingPoint - 1
                continue

            state = procesUserPost(post, folderName)
            if state:
                downloadCount = downloadCount + 1
                print("Saved post number: " + str(downloadCount))

            if (downloadCount >= targetPostCount):
                print("\nCompleted.")
                print("Downloaded " + str(downloadCount) + " posts.\n")
                sys.exit()

        endCursor = getEndCursorForUserPosts(userMedia)
        urlAppender = "&after=" + endCursor
        instaDataUrl = getBaseUrlForUserposts(userId) + urlAppender
        userMedia = getUserMedia(instaDataUrl)
        userPosts = getUserPosts(userMedia)
        hasMorePosts = hasMoreUserPosts(userMedia)
        totalPostCount = userMedia['count']
        numberOfPosts = len(userPosts)


def main():
    # With RunType 1, we make authenticated calls. So as the first step, we login
    # to the instagram and save our client cookies to be used in future calls
    instaLoggedIn = False
    if getRunType() == RUN_TYPES.NORMAL:
        instaLoggedIn = InstaLogin(
            getInstaUserName(),
            getInstaPassword()).login

    # We provide options
    while True:
        print("\nDownload posts from a")
        print("\t1. Instagram Account or")
        print("\t2. Hashtag")
        print("\t3. Exit\n")
        userChoice = input('Input: ') or "1"

        if userChoice == "1":
            downloadUserposts(instaLoggedIn)
        elif userChoice == "2":
            downloadHashTagPosts(instaLoggedIn)
        else:
            logging.info("Instagram Scraper terminated.")
            sys.exit()


main()
