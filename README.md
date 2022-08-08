# Download pocketmags magazines in PDF format from the HTML5 reader.

## Acknowledgements:
This is a modified version of the GitHub Gist called [pmdown.py](https://gist.github.com/rjw57/b9fbbd173d22aca42a80) written by the GitHub user [rjw57](https://github.com/rjw57). I would have contributed my changes to the original but alas it is only a Gist, not a GitHub Repository.

I have modified the original Python code in order to:
- Enable downloading of magazines in the elusive "high" quality format (only when `--quality=high` is used, otherwise the default is "mid").
- Add a title to the generated PDF's metadata as the default of "untitled.pdf" was annoying me.

**NB:** I have only been able to test this on the small number of magazines I have purchased on [pocketmags.com](https://pocketmags.com)

With thanks to:
- [rjw57](https://github.com/rjw57) for the original [pmdown.py](https://gist.github.com/rjw57/b9fbbd173d22aca42a80) Python script
- [bani6809](https://github.com/bani6809) for revealing in the [comments](https://gist.github.com/rjw57/b9fbbd173d22aca42a80?permalink_comment_id=3779130#gistcomment-3779130) that the "high" quality image urls end in `bin` not `jpg`.

## Usage:

    `pocketmagstopdf.py (-h | --help)`

    `pocketmagstopdf.py [options] <pdf> <url>`

## Options:

```
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

```

## Notes:

**PLEASE USE THIS SCRIPT RESPONSIBLY. THE MAGAZINE PUBLISHING INDUSTRY RELIES
HEAVILY ON INCOME FROM SALES WITH VERY SLIM PROFIT MARGINS.**

URLs for pocketmags images can be found by using the HTML 5 reader and
right-clicking on a page and selecting "inspect element". Look for URLs of
the form:

`https://mcdatastore.blob.core.windows.net/mcmags/<uuid1>/<uuid2>/extralow/<num>.jpg`

where `<uuid{1,2}>` are strings of letters and numbers with dashes separating
them and `<num>` is some 4-digit number.