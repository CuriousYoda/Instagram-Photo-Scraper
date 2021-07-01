# Instagram-Photo-Scraper

Downloads most recent images for a username or hashtag. Be polite with # number of downloads, don't to overuse so that Instagram removes their open APIs (again) or restrict your IP. 

## Features
- Takes a Instagram user name and downloads X photos starting from most recent ones
  - You can define how many photos to be downloaded
- Takes a Instagram Hash Tag and downloads the top photos or X photos posted recently
- Works with few different run types
  - Run_TYPE 1 - Works with authenticated calls. You need a instagram user name and password for this
  - RUN_TYPE 2 - Through Proxy (currently not supported)
  - RUN_TYPE 3 - Without login, and through regular internet connection. We recommend this one. However, your IP might be blocked by instagram if you download heavily. So be polite

## How to use
- Set up the RUN TYPE in the properties file.
- If you use RUN TYPE 1
  - Set up your instagram user name and password in the properties file.
- Set up the folder path to download images in the properties file
- Run the insta-scraper.exe either by double clicking or by opening CMD prompt and typing "insta-scraper.exe"
- Photos will be downloaded to the folder you specified. User photos will be saved to a folder name with User Full Name and Hashtag photos to a folder named with that hashtag

## Development & Packaging
- TBA ( Code is not open as of now)

## Next Steps
- Start downloading photos for users from a given starting point (not from the beginning)
- Support for proxy solution

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
