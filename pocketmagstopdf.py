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
    pmdown.py (-h | --help)
    pmdown.py [options] <pdf> <url>

Options:

    -h, --help                  Print brief usage summary.
    --dpi=DPI                   Set image resolution in dots per inch.
                                [default: 150]

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

import docopt
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# The pattern of the URL path for a magazine
# Original Gist pattern
# URL_PATH_PATTERN = re.compile(r'(?P<prefix>^[a-f0-9\-/]*/high/)[0-9]{4}.jpg')
# One of my updated patterns
URL_PATH_PATTERN = re.compile(r'(?P<prefix>/mcmags/[a-f0-9\-]*/[a-f0-9\-]*/extralow/)[0-9]{4}.jpg')
# One of my updated patterns
URL_PATH_PATTERN = re.compile(r'(?P<prefix>^/mcmags/[a-f0-9\-/]*/mid/)[0-9]{4}.jpg')
# Example URL: https://mcdatastore.blob.core.windows.net/mcmags/f3786b15-4b19-456e-9b58-2af137a35bcd/9e3ee986-08f3-4679-bf58-ebe1151852e3/low/0025.jpg

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
    print('URL is: {}'.format(url))
    print('File is: {}'.format(pdf_fn))
    print('DPI is {}'.format(dpi))

    m = URL_PATH_PATTERN.match(url.path)
    if not m:
        raise RuntimeError('URL path does not match expected pattern')
    prefix = m.group('prefix')

    c = canvas.Canvas(pdf_fn)
    with saving(c):
        for page_num in itertools.count(0):
            page_url = list(url)
            page_url[2] = '{}{:04d}.jpg'.format(prefix, page_num)
            page_url = urlunparse(page_url)
            print('Downloading page {} from {}...'.format(page_num, page_url))

            try:
                with urlopen(page_url) as f:
                    im = Image.open(f)
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