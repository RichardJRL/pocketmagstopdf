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
    --dpi=DPI                   Set image resolution in dots per inch.
                                [default: 150]
    --quality=QUALITY           Set magazine download quality; Choose from extralow, low, mid or high.
                                [default: mid]
    --title=TITLE               Set magazine title in the PDF metadata
                                default value is the filename with;
                                    - underscores replaced with spaces
                                    - the file extension removed
    --range-from=PAGE-FROM      Define a portion of the magazine to download, starting from this page number. (Optional)
                                Downloads from the beginning of the magazine if absent.
                                [default: 1]
    --range-to=PAGE-TO          Define a portion of the magazine to download, ending on this page number. (Optional)
                                Downloads to the end of the magazine if absent.
                                [default: 999]
    <pdf>                       Save output to this file.
    <url>                       A URL to one image from the magazine.

Notes:

    PLEASE USE THIS SCRIPT RESPONSIBLY. THE MAGAZINE PUBLISHING INDUSTRY RELIES
    HEAVILY ON INCOME FROM SALES WITH VERY SLIM PROFIT MARGINS.

    URLs for pocketmags images can be found by using the HTML 5 reader and
    right-clicking on a page and selecting "inspect element". Look for URLs of
    the form:

        https://mcdatastore.blob.core.windows.net/mcmags/<uuid1>/<uuid2>/extralow/<num>.jpg

    where <uuid{1,2}> are strings of letters and numbers with dashes separating
    them and <num> is some 4-digit number.

"""

import itertools
import os.path
import re
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

import binascii
import docopt
import PIL
from io import BytesIO
from PIL import Image
from PIL import UnidentifiedImageError
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


# The pattern of the URL path for a magazine
URL_PATH_PATTERN = re.compile(r'(?P<prefix>^/mcmags/[a-f0-9\-]*/[a-f0-9\-]*)/(?P<imagequality>(extralow|low|mid|high)/)[0-9]{4}.(bin|jpg)')

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
QUALITY_PATTERN = re.compile("(extralow|low|mid|high)")

# Notes on the "high" image size with the "bin" file extension.
# Running the Linux "file" command gives the output:
# Atari DEGAS Elite bitmap 320 x 200 x 16, color palette ffe0 0010 4a46 4946 0001 ...

# But it seems unlikely that what is expected to be the highest quality image is actually an old Atari bitmap with
# 320 x 200 resolution! Using a hex editor (Okteta) to examine the bin file immediately revealed the string "JFIF"
# near the beginning of the file. This is one of the things expected in the header of a "jpg" file but the first two
# bytes of the file were 0x0000 when for a "jpg" they should be 0xFFD8. The rest of the beginning of the file also
# looked like what would be expected in a "jpg" header section. Editing the first two bytes of the "bin" file to
# 0xFFD8 resulted in it opening in the Gwenview image viewer and showed it to have a resolution of 1447 x 2048.

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

    m = URL_PATH_PATTERN.match(url.path)
    if not m:
        raise RuntimeError('URL path does not match expected pattern')
    prefix = m.group('prefix')

    q = QUALITY_PATTERN.match(quality)
    if not q:
        raise RuntimeError("--quality= argument does not match any of the expected values: extralow|low|mid|high")

    # NB: docopts gives the variable 'title' the string value of "None" not the type "None" when it is absent as a CLA
    # Hence 'if title == "None"' rather than 'if title is None'
    if title == "None":
        (title, extension) = os.path.splitext(os.path.basename(pdf_fn))
        title = title.replace('_', ' ')

    # Check range_from and range_to are both >0, exit if not
    if range_from < 1 or range_to < 1:
        raise RuntimeError("Error setting the page range to download, the optional arguments --range-from and --range-to, if specified, must be integer values greater than 1")

    # Check range_from < range_to
    if range_from > range_to:
        raise RuntimeError("Error setting the page range to download. --range-from must be less than --range-to")

    # Assemble range text
    end_text = " to page " + str(range_to)
    if range_to == 999:
        end_text = " to the end of the magazine"
    range_text = 'Range of pages to download is page ' + str(range_from) + end_text

    print('URL is {}'.format(url.geturl()))
    print('File is {}'.format(pdf_fn))
    print('DPI is {}'.format(dpi))
    print('Quality is {}'.format(quality))
    print(range_text)

    c = canvas.Canvas(pdf_fn)
    c.setTitle(title)
    with saving(c):

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
                    else:
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

            print('Image is {} x {} pixels and {:.2f}in x {:.2f}in at {} DPI'.format(im.width, im.height, w, h, dpi))
            c.setPageSize((w * inch, h * inch))
            c.drawInlineImage(im, 0, 0, w*inch, h*inch)
            c.showPage()

if __name__ == '__main__':
    main()