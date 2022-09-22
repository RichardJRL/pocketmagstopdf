#!/usr/bin/env python3
#
# THIS SCRIPT REQUIRES PYTHON 3
#
# Install requirements via:
#   pip3 install docopt pillow reportlab
#
# Dedicated to the public domain where possible.
# See: https://creativecommons.org/publicdomain/zero/1.0/
"""
Download pocketmags magazines in PDF format from the HTML5 reader.

Usage:
    pocketmagstopdf.py (-h | --help)
    pocketmagstopdf.py [options] <pdf> <url>

Options:

    -h, --help                  Print brief usage summary.

    --quality=QUALITY           Set magazine download quality.
                                Choose from extralow, low, mid, high or original. (Optional)
                                [default: mid]

    --dpi=DPI                   Set image resolution in dots per inch. (Optional)
                                Not used with '--quality=original'.
                                [default: 150]

    --title=TITLE               Set magazine title in the PDF metadata. (Optional)
                                Not used with '--quality=original'.
                                default value is the filename with;
                                    - underscores replaced with spaces
                                    - the file extension removed

    --range-from=PAGE-FROM      Define a portion of the magazine to download, starting from this page number. (Optional)
                                Downloads from the beginning of the magazine - page 1 - if absent.
                                [default: 1]

    --range-to=PAGE-TO          Define a portion of the magazine to download, ending on this page number. (Optional)
                                Downloads to the end of the magazine if absent.
                                [default: 999]

    --delay=DELAY               Set the time in seconds to wait between downloading each page of the magazine. (Optional)
                                There is no delay if absent. The value of the delay may be integer or decimal.
                                Used both whenenever probing for the last valid page number of the magazine and
                                between downloading each individual page for all quality settings except 'original'.
                                [default: 0]

    --save-images=SAVE-IMAGES   Save the downloaded JPEG images of the magazine pages to a subdirectory with the same
                                name as the magazine in addition to generating the PDF of the magazine.
                                Not used with '--quality=original'.
                                Choose from yes or no.
                                [default: no]

    --image-subdir-prefix=PFX   If --save-images=yes then prefix name of the subdirectory the images are saved to with
                                this string. Blank by default. (Optional)
                                Not used with '--quality=original'.
                                [default: ]

    --image-subdir-suffix=SFX   If --save-images=yes then suffix name of the subdirectory the images are saved to with
                                this string. Blank by default. (Optional)
                                Not used with '--quality=original'.
                                [default: ]

    --uuid=UUID                 User UUID required if '--quality=original' is specified and --uuid-randomise is not used.
                                Read the 'Notes' section below for details of how to find it. (Optional/Required)
                                [default: None]

    --uuid-randomise            Uses a random UUID to download the PDF when '--quality=original' is specified. (Optional)
                                [default: False]

    <pdf>                       Save output to this file. (Required)
    <url>                       A URL to one image from the magazine. (Required)

Notes:

    PLEASE USE THIS SCRIPT RESPONSIBLY. THE MAGAZINE PUBLISHING INDUSTRY RELIES
    HEAVILY ON INCOME FROM SALES WITH VERY SLIM PROFIT MARGINS.

    URLs for pocketmags images and User UUIDs can be found by using the HTML 5 reader and
    right-clicking on a page and selecting "inspect element". Look for URLs of the form:

        https://mcdatastore.blob.core.windows.net/mcmags/<uuid1>/<uuid2>/extralow/<num>.jpg

    where <uuid{1,2}> are strings of letters and numbers with dashes separating them
    and <num> is some 4-digit number.

    The User UUID required for downloading the magazine when '--quality=original' can be
    found by searching the HTML for the text "userGuid:" and copying the hexadecimal
    value that follows it without the surrounding single quote characters.

"""

import os.path
import re
import uuid
from contextlib import contextmanager
from time import sleep
from urllib.error import HTTPError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

import binascii
import docopt
import PIL
from io import BytesIO

import requests as requests
from PIL import Image
from PIL import UnidentifiedImageError
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# The pattern of the URL path for a magazine
URL_PATH_PATTERN = re.compile(
    r'(?P<prefix>^/mcmags/(?P<bucket_uuid>[a-f0-9\-]+)/(?P<magazine_uuid>[a-f0-9\-]+))/(?P<imagequality>(extralow|low|mid|high))/[0-9]{4}.(bin|jpg)')

# Example URLs sampled 8 July 2022, deliberately using an advert from a magazine:
# https://mcdatastore.blob.core.windows.net/mcmags/f3786b15-4b19-456e-9b58-2af137a35bcd/ba9c5bcb-cf96-4215-a2f5-841ddb4a119c/extralow/0046.jpg
# https://mcdatastore.blob.core.windows.net/mcmags/f3786b15-4b19-456e-9b58-2af137a35bcd/ba9c5bcb-cf96-4215-a2f5-841ddb4a119c/low/0046.jpg
# https://mcdatastore.blob.core.windows.net/mcmags/f3786b15-4b19-456e-9b58-2af137a35bcd/ba9c5bcb-cf96-4215-a2f5-841ddb4a119c/mid/0046.jpg
# https://mcdatastore.blob.core.windows.net/mcmags/f3786b15-4b19-456e-9b58-2af137a35bcd/ba9c5bcb-cf96-4215-a2f5-841ddb4a119c/high/0046.bin

# Image Sizes (based upon the above URLs)
# extralow: 340  x 480
# low:      362  x 512
# mid:      905  x 1280
# high:     1447 x 2048
QUALITY_PATTERN = re.compile("(extralow|low|mid|high|original)")

# Notes on the "high" image size with the "bin" file extension.
# Running the Linux "file" command gives the output:
# Atari DEGAS Elite bitmap 320 x 200 x 16, color palette ffe0 0010 4a46 4946 0001 ...

# But it seems unlikely that what is expected to be the highest quality image is actually an old Atari bitmap with
# 320 x 200 resolution! Using a hex editor (Okteta) to examine the bin file immediately revealed the string "JFIF"
# near the beginning of the file. This is one of the things expected in the header of a "jpg" file but the first two
# bytes of the file were 0x0000 when for a "jpg" they should be 0xFFD8. The rest of the beginning of the file also
# looked like what would be expected in a "jpg" header section. Editing the first two bytes of the "bin" file to
# 0xFFD8 resulted in it opening in the Gwenview image viewer and showed it to have a resolution of 1447 x 2048.

# The pattern for a standard UUID, used to identify storage blobs, magazines and users
UUID_PATTERN = re.compile("^[a-z0-9]{8}-([a-z0-9]{4}-){3}[a-z0-9]{12}$")

@contextmanager
def saving(thing):
    """Context manager which ensures save() is called on thing."""
    try:
        yield thing
    finally:
        thing.save()


def main():
    opts = docopt.docopt(__doc__)
    pdf_fn, url = (opts[k] for k in ('<pdf>', '<url>'))
    url = urlparse(url)
    dpi = float(opts['--dpi'])
    quality = str(opts['--quality'])
    title = str(opts['--title'])
    range_from = int(opts['--range-from'])
    range_to = int(opts['--range-to'])
    delay = float(opts['--delay'])
    save_images = str(opts['--save-images'])
    image_subdir_prefix = str(opts['--image-subdir-prefix'])
    image_subdir_suffix = str(opts['--image-subdir-suffix'])
    user_uuid = str(opts['--uuid'])
    user_uuid_randomise = bool(opts['--uuid-randomise'])

    m = URL_PATH_PATTERN.match(url.path)
    if not m:
        raise RuntimeError('URL path does not match expected pattern')
    prefix = m.group('prefix')

    q = QUALITY_PATTERN.match(quality)
    if not q:
        raise RuntimeError(
            "--quality= argument does not match any of the expected values: extralow|low|mid|high|original")

    bu = UUID_PATTERN.match(m.group('bucket_uuid'))
    if not bu:
        raise RuntimeError('URL supplied does not contain a valid storage bucket UUID')
    bucket_uuid = bu.string

    mu = UUID_PATTERN.match(m.group('magazine_uuid'))
    if not mu:
        raise RuntimeError('URL supplied does not contain a valid magazine UUID')
    magazine_uuid = mu.string

    # NB: docopts gives the variable 'title' the string value of "None" not the type "None" when it is absent as a CLA
    # Hence 'if title == "None"' rather than 'if title is None'
    if title == "None":
        (title, extension) = os.path.splitext(os.path.basename(pdf_fn))
        title = title.replace('_', ' ')

    # Check range_from and range_to are both >0, exit if not
    if range_from < 1 or range_to < 1:
        raise RuntimeError(
            "Error setting the page range to download, the optional arguments --range-from= and --range-to=, if specified, must have integer values greater than 1")

    # Check range_from < range_to
    if range_from > range_to:
        raise RuntimeError("Error setting the page range to download. the value of--range-from= must be less than the value of --range-to=")

    # Assemble range text
    end_text = " to page " + str(range_to)
    if range_to == 999:
        end_text = " to the end of the magazine"
    range_text = 'Range of pages to download is page ' + str(range_from) + end_text
    # TODO: Move last-page-finding code to before the range of pages to download is printed, so the inaccurate default of 999 is never shown

    # Check delay value
    if delay < 0:
        raise RuntimeError(
            "Error setting the delay between page downloads. The value of --delay= must be not be less than zero.")

    # Check save_images value
    save_images = save_images.lower()
    if save_images != 'yes' and save_images != 'no':
        raise RuntimeError(
            "Error setting the behaviour of saving images. The value of --save-images= must be either yes or no.")

    # Warn that save_images is not compatible with 'original' quality
    if save_images == 'yes' and quality == 'original':
        raise RuntimeError("Error: cannot save images when quality is set to 'original'.")

    # Check that a UUID option is provided with '--quality=original'
    if quality == 'original':
        if user_uuid == 'None' and user_uuid_randomise is False:
            print('Error: if \'--quality=original\' is used, EITHER --uuid=UUID OR --uuid-randomise MUST be present.')
            exit(1)
        if user_uuid != 'None':
            if not UUID_PATTERN.match(user_uuid):
                raise RuntimeError('User UUID supplied with \'--uuid=\' is not a valid UUID')
        if user_uuid_randomise == True:
            user_uuid = uuid.uuid4()

    print('URL is {}'.format(url.geturl()))
    print('File is {}'.format(pdf_fn))
    print('Storage bucket UUID is {}'.format(bucket_uuid))
    print('Magazine UUID is {}'.format(magazine_uuid))
    print('DPI is {}'.format(dpi))
    print('Quality is {}'.format(quality))
    print(range_text)
    print('Delay between downloading each page is {} seconds'.format(delay))
    print('Saving images is {}'.format(save_images))
    print('User UUID is {}'.format(user_uuid))
    print('Randomise User UUID is {}'.format(str(user_uuid_randomise).lower()))

    if quality != 'original':
        c = canvas.Canvas(pdf_fn)
        c.setTitle(title)
        with saving(c):

            # create directory to hold magazine images, if required
            if save_images == 'yes':
                (pdf_parent_dir_name, pdf_filename) = os.path.split(os.path.abspath(pdf_fn))
                (image_subdir_name, extension) = os.path.splitext(pdf_filename)
                image_subdir_name = image_subdir_prefix + image_subdir_name + image_subdir_suffix
                image_subdir_path = os.path.join(pdf_parent_dir_name, image_subdir_name)
                os.makedirs(image_subdir_path)

            for page_num in range(range_from - 1, range_to):
                page_url = list(url)
                file_extension = 'jpg'
                if quality == 'high':
                    file_extension = 'bin'
                page_url[2] = '{}/{}/{:04d}.{}'.format(prefix, quality, page_num, file_extension)
                page_url = urlunparse(page_url)

                try:
                    with urlopen(page_url) as f:
                        print('Downloading page {} from {}...'.format(page_num + 1, page_url))
                        # if: the extralow, low & mid quality "jpg" format URLs
                        if quality == 'extralow' or quality == 'low' or quality == 'mid':
                            im = Image.open(f)
                        # else: the high quality "bin" format URL
                        elif quality == 'high':
                            # Rewrite the beginning of the file in include the proper JPEG file type code.
                            jpg_header = binascii.unhexlify('FFD8')
                            filedata = f.read()[2:]
                            imgdata = BytesIO(jpg_header + filedata)
                            try:
                                im = Image.open(imgdata)
                            except PIL.UnidentifiedImageError as uie:
                                print("Page", page_num, "is not a valid image file. Unable to continue; exiting...")
                                break

                except HTTPError as e:
                    if e.code == 404:
                        print('No image found => stopping')
                        break
                    raise e

                w, h = tuple(dim / dpi for dim in im.size)

                print(
                    'Image is {} x {} pixels and {:.2f}in x {:.2f}in at {} DPI'.format(im.width, im.height, w, h, dpi))
                c.setPageSize((w * inch, h * inch))
                c.drawInlineImage(im, 0, 0, w * inch, h * inch)
                c.showPage()
                if save_images == 'yes':
                    # Save in "human-ranged" format - starting the page count from 1, not 0.
                    image_name = '{:04d}.jpg'.format(page_num + 1)
                    image_path = os.path.join(image_subdir_path, image_name)
                    im.save(image_path)
                sleep(delay)

    # else quality = 'original'
    else:
        print("Downloading magazine as the original PDF")
        user_uuid = uuid.uuid4()
        post_request_url = 'http://readerv2.pocketmags.com/PrintPage'
        post_request_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "readerv2.pocketmags.com",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
            "Origin": "https://pocketmags.com",
            "Referer": "https://pocketmags.com"
        }
        post_request_data = {
            "id": magazine_uuid,
            "user": user_uuid,
        }

        # Check the range_to value exists as a magazine page (as the default is 999)
        # by checking the extralow JPG for the page exists. Need HTTP response 200, not 404.
        # Jumps between pages in 20,10,5,2,1 page intervals to avoid having to check everysingle page.
        # The page jump size halves and the process works backwards after a page is not found.
        file_extension = 'jpg'
        page_num = range_from - 1
        page_jump = 20
        last_good_page = -1
        last_bad_page = None
        bad_page_count = 0
        bad_page_limit = page_jump
        jpeg_quality = 'extralow'
        while True:
            sleep(delay)
            jpeg_url = list(url)
            jpeg_url[2] = '{}/{}/{:04d}.{}'.format(prefix, jpeg_quality, page_num, file_extension)
            jpeg_url = urlunparse(jpeg_url)
            jpeg_exists_response = requests.get(url=jpeg_url)
            if jpeg_exists_response.status_code == 200:
                last_good_page = page_num
                if last_good_page + 1 == last_bad_page:
                    print("Page {} is the last good page".format(last_good_page))
                    range_to = last_good_page + 1
                    break
                page_num += page_jump
            elif jpeg_exists_response.status_code == 404:
                last_bad_page = page_num
                bad_page_count += 1
                page_jump = page_jump // 2
                if page_jump < 1:
                    page_jump = 1
                page_num -= page_jump
                if page_num < 0:
                    page_num = 0
                if bad_page_count == bad_page_limit:
                    raise RuntimeError("Error: Cannot find any valid page numbers, exiting...")
            else:
                raise RuntimeError(
                    "Unexpected HTTP error code encountered while probing for the last page in the magazine: HTTP error {}".format(
                        jpeg_exists_response.status_code))
            print("HTTP response code {} for URL {}".format(jpeg_exists_response.status_code, jpeg_url))
            print("Last good page number: {}, last bad page number: {}".format(last_good_page, last_bad_page))
            print("Page jump value is {}".format(page_jump))
            print("Next page to be queried is {}".format(page_num))

        # Add the required number of pages to the post_request_data
        index_number = 0
        for page_num in range(range_from - 1, range_to):
            post_request_data["pages[{}]".format(index_number)] = page_num
            index_number += 1
        print(post_request_data)

        pdf_response = requests.post(url=post_request_url, data=post_request_data, headers=post_request_headers)
        if pdf_response.status_code == 200:
            print('Success: Downloaded magazine')
        else:
            print('Error: Unable to download magazine: HTTP error code {}'.format(pdf_response.status_code))
            exit(1)

        pdf_download = pdf_response.content

        # Save the original un-edited PDF download
        with open(pdf_fn, 'bw') as pdf_original:
            pdf_original.write(pdf_download)
            print('Saved PDF download to {}'.format(pdf_fn))

if __name__ == '__main__':
    main()
