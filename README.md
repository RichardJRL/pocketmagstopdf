# Download pocketmags magazines in PDF format from the HTML5 reader.

### PLEASE USE THIS SCRIPT RESPONSIBLY. THE MAGAZINE PUBLISHING INDUSTRY RELIES HEAVILY ON INCOME FROM SALES WITH VERY SLIM PROFIT MARGINS.

## Acknowledgements:
This is a modified version of the GitHub Gist called [pmdown.py](https://gist.github.com/rjw57/b9fbbd173d22aca42a80) written by the GitHub user [rjw57](https://github.com/rjw57). I would have contributed my changes to the original but alas it is only a Gist, not a GitHub Repository.

With thanks to:
- [rjw57](https://github.com/rjw57) for the original [pmdown.py](https://gist.github.com/rjw57/b9fbbd173d22aca42a80) Python script.
- [bani6809](https://github.com/bani6809) for revealing in the [comments](https://gist.github.com/rjw57/b9fbbd173d22aca42a80?permalink_comment_id=3779130#gistcomment-3779130) that the "high" and "extrahigh" quality image urls end in `bin` not `jpg`.
- [shirblc](https://github.com/shirblc) for replacing my collection of Python `print` statements with proper Python logging.

**NB:** I have only been able to test this on the small number of magazines I have purchased on [pocketmags.com](https://pocketmags.com)

## Feature Additions:
### 14/07/2022
- Add the option to enable downloading of magazines in the elusive "high" quality format (only when `--quality=high` is used, otherwise the default is "mid").
- Added the option to insert a custom title into the generated PDF's metadata to replace the default of "untitled.pdf".
### 13/08/2022
- Add the option to specify a range of pages to download, rather than the whole magazine.
- Add the option to save images to a separate directory in addition to generating the PDF.
- And the option to set a delay between downloading pages in case of any server-imposed rate-limiting.
### 30/09/2022
- Add the option to enable downloading of magazines in the Holy-Grail "original" format (only when `--quality=original` is used, otherwise the default is "mid").
- Add options to alter the verbiage level of the program's output:
  - `--quiet` suppresses all output except warnings and errors.
  - No option given will present a normal level of informational output.
  - `--debug` prints comprehensive PDF-related information. 
- Add the option to hide the User UUID watermark that is inserted on each page of the PDF when `--quality=original` is used.
### 09/12/2022
- Add proper Python Logger support (implemented by [shirblc](https://github.com/shirblc))
### 19/03/2023
- Add the option to enable downloading of magazines in the newly-discovered "extrahigh" quality format (only when `--quality=extrahigh` is used, otherwise the default is "mid").

## Usage:

```
pocketmagstopdf.py (-h | --help)
pocketmagstopdf.py [options] <pdf> <url>
```

## Options:

```
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

--save-images               Save the downloaded JPEG images of the magazine pages to a subdirectory with the same
                            name as the magazine in addition to generating the PDF of the magazine.
                            Not used with '--quality=original'.
                            [default: False]

--image-subdir-prefix=PFX   If --save-images=yes then prefix name of the subdirectory the images are saved to with
                            this string. Blank by default. (Optional)
                            Not used with '--quality=original'.
                            [default: ]

--image-subdir-suffix=SFX   If --save-images=yes then suffix name of the subdirectory the images are saved to with
                            this string. Blank by default. (Optional)
                            Not used with '--quality=original'.
                            [default: ]

--uuid=UUID                 Specifies the User UUID to use to download the PDF when '--quality=original' is used
                            and --uuid-randomise is not used.
                            Read the 'Notes' section below for details of how to find it. (Optional/Required)
                            Only used with '--quality=original'.
                            [default: None]

--uuid-randomise            Uses a random UUID to download the PDF when '--quality=original' is specified. (Optional)
                            [default: False]

--uuid-hide                 Hides the User UUID watermark on each page of the PDF by making it transparent.
                            This option is overridden by '--uuid-destroy'.
                            Only used with '--quality=original' as watermark not present on lower quality downloads.
                            [default: False]

--uuid-destroy              Completely wipes the User UUID watermark from each page of the PDF. (Experimental)
                            This option overrides by '--uuid-hide'.
                            Only used with '--quality=original' as watermark not present on lower quality downloads.
                            [default: False]

--timestamp-change          Alters the timestamp within the downloaded PDF.
                            Only used with '--quality=original'.
                            [default: False]

--quiet                     Suppress printing of all output except warning and error messages.
                            [default: False]

--debug                     Print extra output to aid debugging of the program.
                            Setting both '--quiet' and '--debug' is contradictory
                            If this happens, a warning is issued and the debug setting overrides the quiet setting.
                            [default: False]

<pdf>                       Save output to this file. (Required)
<url>                       A URL to one image from the magazine. (Required)
```

## Examples:
```
pocketmagstopdf.py --quality=high --delay=2 --title="My Magazine, Issue 73, October 2022" my_magazine.pdf https://mcdatastore.blob.core.windows.net/mcmags/<STORAGE_BUCKET_UUID>/<ISSUE_UUID>/extralow/0000.jpg

pocketmagstopdf.py --quality=original --delay=0.5 --uuid-hide --uuid=<USER_UUID> my_magazine.pdf https://mcdatastore.blob.core.windows.net/mcmags/<STORAGE_BUCKET_UUID>/<ISSUE_UUID>/extralow/0000.jpg
```

## Notes:

**PLEASE USE THIS SCRIPT RESPONSIBLY. THE MAGAZINE PUBLISHING INDUSTRY RELIES
HEAVILY ON INCOME FROM SALES WITH VERY SLIM PROFIT MARGINS.**

URLs for pocketmags images and User UUIDs can be found by using the HTML 5 reader and right-clicking on a page and selecting "inspect element". Look for URLs of the form:

`https://mcdatastore.blob.core.windows.net/mcmags/<uuid1>/<uuid2>/extralow/<num>.jpg`

where `<uuid{1,2}>` are strings of letters and numbers with dashes separating them and <num> is some 4-digit number.

The User UUID required for downloading the magazine when '--quality=original' can be found by searching the HTML for the text "userGuid:" and copying the hexadecimal value that follows it without the surrounding single quote characters.