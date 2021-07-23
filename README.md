# Instagram-Posts-Scraper

Downloads most recent posts (both photos and videos) for a username or hashtag. Be polite with # number of downloads, don't to overuse so that Instagram removes/changes their open APIs (again) or restrict your IP. 

## Features
- Takes a Instagram user name and downloads X posts starting from most recent ones
  - You can define how many posts to be downloaded
- Takes a Instagram Hash Tag and downloads the top posts or X posts posted recently
- Works with few different run types
  - Run_TYPE 1 - Works with authenticated calls. You need a instagram user name and password for this. Be polite, otherwise Instagram will restrict your account. 
  - RUN_TYPE 2 - Through Proxy (temporarily not supported)
  - RUN_TYPE 3 - Without login, and through regular internet connection. We recommend this one. However, be polite with your downloads, otherwise your IP might be blocked by Instagram.

## Git Installtion
```
# clone the repo
$ git clone https://github.com/CuriousYoda/Instagram-Posts-Scraper.git

# change the working directory to Facebook-Video-Downloader
$ cd Instagram-Posts-Scraper

# install the requirements
$ pip3 install -r requirements.txt
```

## Required Properties
- Set up the RUN TYPE in the properties file. Default is RUN TYPE 3, which requires no user name or password for Instagram. However, this run type might have limitations on number of posts which can be downloader.
- If you use RUN TYPE 1
  - Set up your instagram user name and password in the properties file. Be polite with downloads. Otherwise, Instagram will restrict your account. 
- Set up the folder path to download images in the properties file
- User posts will be saved to a folder name with User Full Name and Hashtag posts to a folder named with that hashtag

## Usage
```
# With exe (Only for Windows systems)
$ Double click on exe or Open a CMD prompt and run "insta-scraper.exe"

# Through script
$ python insta-scraper.py

```

## Known Issues


## Next Steps
- Fix known issues
- Support for proxy solution

## Screenshots
Downloading recent posts for a hashtag

![image](https://user-images.githubusercontent.com/86459866/124739618-a9ce5880-df37-11eb-96ce-8fb8c9420067.png)




Copyright (c) [2021] [[@CuriousYoda](https://twitter.com/CuriousYoda)]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
