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
Download a pocketmags magazines in PDF format from the HTML5 reader.

Usage:
    pocketmagstopdf.py (-h | --help)
    pocketmagstopdf.py [options] <pdf> <url>

Options:

    -h, --help                  Print brief usage summary.
    --dpi=DPI                   Set image resolution in dots per inch.
                                [default: 150]
    --quality=QUALITY           Set magazine download quality; Choose from extralow, low, mid or high.
                                [default: mid]

    <pdf>                       Save output to this file.
    <url>                       A URL to one image from the magazine.

Notes:

    PLEASE USE THIS SCRIPT RESPONSIBLY. THE MAGAZINE PUBLISHING INDUSTRY RELIES
    HEAVILY ON INCOME FROM SALES WITH VERY SLIM PROFIT MARGINS.

    URLs for pocketmag images can be found by using the HTML 5 reader and
    right-clicking on a page and selecting "inspect element". Look for URLs of
    the form:

        http://magazines.magazineclonercdn.com/<uuid1>/<uuid2>/high/<num>.jpg

    where <uuid{1,2}> are strings of letters and numbers with dashes separating
    them and <num> is some 4-digit number.

"""

import itertools
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

# But it seems unlikely that what # is expected to be the highest quality image is actually an old Atari bitmap with
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
    print('URL is: {}'.format(url))
    print('File is: {}'.format(pdf_fn))
    print('DPI is {}'.format(dpi))
    print('Quality is {}'.format(quality))

    m = URL_PATH_PATTERN.match(url.path)
    if not m:
        raise RuntimeError('URL path does not match expected pattern')
    prefix = m.group('prefix')

    q = QUALITY_PATTERN.match(quality)
    if not q:
        raise RuntimeError("--quality= argument does not match any of the expected values: extralow|low|mid|high")

    c = canvas.Canvas(pdf_fn)
    with saving(c):
        for page_num in itertools.count(0):
            page_url = list(url)
            file_extension = 'jpg'
            if quality == 'high':
                file_extension = 'bin'
            page_url[2] = '{}/{}/{:04d}.{}'.format(prefix, quality, page_num, file_extension)
            page_url = urlunparse(page_url)
            print('Downloading page {} from {}...'.format(page_num, page_url))

            try:
                with urlopen(page_url) as f:
                    # if: the extralow, low & mid quality "jpg" format URLs
                    if quality == 'extralow' or quality == 'low' or quality == 'mid':
                        im = Image.open(f)
                    # else: the high quality "bin" format URL
                    else:
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

            print('Image is {:.2f}in x {:.2f}in at {} DPI'.format(w, h, dpi))
            c.setPageSize((w*inch, h*inch))
            c.drawInlineImage(im, 0, 0, w*inch, h*inch)
            c.showPage()

if __name__ == '__main__':
    main()