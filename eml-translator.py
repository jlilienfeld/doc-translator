from pathlib import Path
from libretranslatepy import LibreTranslateAPI
import time
import argparse
import eml_parser
from bs4 import BeautifulSoup as bs
import base64
import docx


parser = argparse.ArgumentParser(
                    prog='eml-translator',
                    description='Translates EML files to english',
                    epilog='')
parser.add_argument('path')
parser.add_argument(
    '-l',
    '--language',
    help="2 letters language code.  Forces translation from this language to translate. (Defaults to auto detect)",
    required=False)
parser.add_argument(
'-s',
    '--server',
    help="https URL to the translation server",
    required=True
)
args = parser.parse_args()
print("Will translate all files in " + args.path)

source_language = "auto"
if args.language is not None:
    source_language = args.language.lower()


lt = LibreTranslateAPI(args.server)
supported_languages = lt.languages()


def save_file(file_path, data):
    translated_file = open(file_path, "wb")
    translated_file.write(data)
    translated_file.close()
    print(file_path + " has been saved.")


def retry(func, ex_type=Exception, limit=0, wait_ms=100, wait_increase_ratio=2, logger=None):
    """
    Retry a function invocation until no exception occurs
    :param func: function to invoke
    :param ex_type: retry only if exception is subclass of this type
    :param limit: maximum number of invocation attempts
    :param wait_ms: initial wait time after each attempt in milliseconds.
    :param wait_increase_ratio: increase wait period by multiplying this value after each attempt.
    :param logger: if not None, retry attempts will be logged to this logging.logger
    :return: result of first successful invocation
    :raises: last invocation exception if attempts exhausted or exception is not an instance of ex_type
    """
    attempt = 1
    while True:
        try:
            return func()
        except Exception as ex:
            if not isinstance(ex, ex_type):
                raise ex
            if 0 < limit <= attempt:
                if logger:
                    logger.warning("no more attempts")
                raise ex

            if logger:
                logger.error("failed execution attempt #%d", attempt, exc_info=ex)

            attempt += 1
            if logger:
                logger.info("waiting %d ms before attempt #%d", wait_ms, attempt)
            time.sleep(wait_ms / 1000)
            wait_ms *= wait_increase_ratio


def is_english_charpoint(string):
    for char in string:
        if not (0 < ord(char) <= 127):
            return False
    return True


def get_language_name(language_code):
    for language in supported_languages:
        if language['code'] == language_code:
            return language['name']
    return "Unknown - LibreTranslate returned no corresponding language for " + language_code


translation_marker = "\n[AUTO_TRANSLATED] FROM "
file_count = 0


def translate_docx(filename, partname, html_data):
    doc = docx.Document(filename)
    paragraph_num = len(doc.paragraphs)
    print("Translating " + str(paragraph_num) + ".docx paragraphs in email " + filename + " attachement: " + partname)
    paragraph_pos = 0
    for paragraph in doc.paragraphs:
        paragraph_pos += 1
        if translation_marker in paragraph.text:
            continue
        if len(paragraph.text) > 0:
            lang_code = lt.detect(q=paragraph.text)[0]['language']
            if lang_code == "en":
                continue
            translation = lt.translate(q=paragraph.text, source=lang_code, target="en")
            paragraph.text += translation_marker + get_language_name(lang_code) + ":\n" + translation + "\n\n"
    doc.save(pathStr + "-" + filename)



def translate_html(filename, partname, html_data):
    parsed_html = bs(html_data, "html.parser")
    for x in parsed_html.findAll(string=True):
        if x.string is not None:
            source_lang = "en"
            while True:
                try:
                    source_lang = lt.detect(q=x.string)[0]['language']
                    break
                except Exception as error:
                    continue

            if source_lang != "en":
                while True:
                    try:
                        result = lt.translate(q=x.string,
                                              source="auto", target="en")
                        original = x.string
                        translation = "<br />" + translation_marker + get_language_name(source_lang) + ": " + result
                        x.string.replace_with(original + " " + translation)
                        print(x.string)
                        break
                    except Exception as exception:
                        print("Skipped " + partname + " in " + filename + " because of ", type(exception))
                        continue
    return parsed_html.prettify(encoding='utf-8')


pathlist = Path(args.path).glob('**/*.eml')
for path in pathlist:
    file_count += 1
pathlist = Path(args.path).glob('**/*.eml')
print("Translating " + str(file_count) + " eml files")
current_count = 0
translation_needed = False
for path in pathlist:
    print(str(current_count) + " out of " + str(file_count) + " .eml files translated")
    current_count += 1
    pathStr = str(path)
    print("Processing " + pathStr)

    ep = eml_parser.EmlParser(include_attachment_data=True, include_raw_body=True)
    parsed_eml = ep.decode_email(path)

    if "body" in parsed_eml:
        body = parsed_eml["body"]
        index = 0
        for part in body:
            index += 1
            partName = "body-" + str(index) + ".html"
            if "content_type" in part:
                content_type = part["content_type"]
                if content_type == "text/html":
                    translation = translate_html(pathStr, partName, part["content"])
                    save_file(pathStr+"-"+partName, translation)
                else:
                    print("Not handling body with content-type: " + content_type)
                    save_file(pathStr+"-"+partName, part["content"])

    if "attachment" in parsed_eml:
        for attachment in parsed_eml["attachment"]:
            content_hdr = attachment["content_header"]
            content_type = content_hdr["content-type"][0]
            filename = attachment["filename"]
            if content_type == "text/html":
                translation = translate_html(pathStr, filename, attachment["raw"])
                save_file(pathStr + "-" + filename, translation)
            else:
                print("Not handling attachment " + filename + " with content-type: " + content_type)
                save_file(pathStr + "-" + filename, base64.b64decode(attachment["raw"]))

