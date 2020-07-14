import urllib


def get_code_from_jurisdiction_url(url):
    pieces = urllib.parse.urlsplit(url).path.strip("/").split("/")
    try:
        code = pieces[1]
    except IndexError:
        code = ""
    return code
