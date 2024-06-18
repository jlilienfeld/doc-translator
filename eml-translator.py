from pathlib import Path
from libretranslatepy import LibreTranslateAPI
import time
import argparse
import eml_parser
from bs4 import BeautifulSoup as bs, Stylesheet, Comment
import base64
import docx
from PyPDF2 import PdfReader
import io
import os
import magic

from openai import OpenAI

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
parser.add_argument(
    '-a',
    '--openaiurl',
    help="Optional.  Experimental.  When specified, this tool will mark spam emails as spam.",
    required=False
)
parser.add_argument(
    '-r',
    '--replicas',
    help="Optional.  Number of replicas of this script will run for translation.",
    required=False,
    default=1
)
parser.add_argument(
    '-i',
    '--index',
    help="Optional.  Replica index to run.  Zero based.",
    required=False,
    default=0
)
args = parser.parse_args()
print("Will translate all files in " + args.path)

source_language = "auto"
if args.language is not None:
    source_language = args.language.lower()
target_language = "en"

lt = LibreTranslateAPI(args.server)
supported_languages = lt.languages()

ai_client = None
if args.openaiurl is not None:
    ai_client = OpenAI(base_url=args.openaiurl, api_key="lm-studio")


def numeric_hash(input):
    acc_val = 0
    for character in input:
        for byte in character.encode("utf-8"):
            acc_val += byte * 97
    return acc_val % int(args.replicas)


def replica_is_owner(input):
    hash = numeric_hash(input)
    return hash == int(args.index)


def ai_email_summarize(text):
    if ai_client is None:
        return
    completion = ai_client.chat.completions.create(
        model="QuantFactory/Meta-Llama-3-8B-Instruct-GGUF",
        messages=[
            {"role": "system", "content": "You will summarize everything I say under 256 characters."},
            {"role": "user", "content": text}
        ],
        temperature=0.7,
    )

    print(completion.choices[0].message.content)


def save_file(file_path, data):
    translated_file = open(file_path, "wb")
    if isinstance(data, str):
        translated_file.write(data.encode("utf-8"))
    else:
        translated_file.write(data)
    translated_file.close()
    print(file_path + " has been saved.")


def detect_lang(text):
    if (len(text)==0):
        return "en"
    while True:
        try:
            return lt.detect(q=text)[0]['language']
        except Exception:
            time.sleep(1)
            continue


def translate_text(text):
    if (len(text)==0):
        return text
    while True:
        try:
            return lt.translate(q=text,
                                source=source_language, target=target_language)
        except Exception:
            time.sleep(1)
            continue


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
    doc = docx.Document(io.BytesIO(html_data))
    paragraph_num = len(doc.paragraphs)
    print("Translating " + str(paragraph_num) + ".docx paragraphs in email " + filename + " attachment: " + partname)
    paragraph_pos = 0
    for paragraph in doc.paragraphs:
        paragraph_pos += 1
        if translation_marker in paragraph.text:
            continue
        if len(paragraph.text) > 0:
            lang_code = detect_lang(paragraph.text)
            if lang_code == "en":
                continue
            translation = translate_text(paragraph.text)
            paragraph.text += translation_marker + get_language_name(lang_code) + ":\n" + translation + "\n\n"
    if doc.inline_shapes.part is not None:
        for key in doc.inline_shapes.part.related_parts:
            related_part = doc.inline_shapes.part.related_parts[key]
            if isinstance(related_part, docx.ImagePart):
                save_file(pathStr + "-" + partname + "-" + related_part.partname.replace("/", "_"), related_part.blob)

    doc.save(pathStr + "-" + partname)


def translate_pdf(filename, partname, pdf_data):
    reader = PdfReader(io.BytesIO(pdf_data))
    print("Translating " + str(len(reader.pages)) + " paragraphs in email " + filename + " attachment: " + partname)
    output_text = ""
    for page in reader.pages:
        text = page.extract_text()
        lang_code = detect_lang(text)
        if lang_code == "en":
            output_text += text
            continue
        output_text += translate_text(text)
    return output_text


def translate_html(pathStr, partName, html_data):
    print("Translating HTML from email " + pathStr + " attachment: " + partName)
    parsed_html = bs(html_data, "html.parser")
    extracted_text = ""
    for x in parsed_html.findAll(string=True):
        if x.string is not None and not isinstance(x.string, Comment) and not isinstance(x.string, Stylesheet):
            source_lang = detect_lang(x.string)

            if source_lang != "en":
                while True:
                    try:
                        result = translate_text(x.string)
                        original = x.string
                        translation = " --- " + translation_marker + get_language_name(source_lang) + ": " + result
                        x.string.replace_with(original + " " + translation)
                        extracted_text += result
                        break
                    except Exception as exception:
                        print("Skipped " + partName + " in " + pathStr + " because of ", type(exception))
                        break
            else:
                extracted_text += x.string
    return parsed_html.prettify(encoding='utf-8')


def translate_plain_text(pathStr, partName, data):
    print("Translating plaintext from email " + pathStr + " attachment: " + partName)
    lines = iter(data.splitlines())
    translated = ""
    for line in lines:
        source_lang = detect_lang(line)
        translated += line
        if source_lang != "en":
            translated += "Translation from " + source_lang + ":\n"
            translated += translate_text(line)
    return translated


def process_email_part(contentType, pathStr, partName, data):
    if len(partName) > 200:
        toRemove = len(partName) - 200
        partName = partName[:128] + partName[128+toRemove:]

    if isinstance(data, bytes):
        if contentType == "text/plain":
            contentType = "unknown"
        contentType = magic.from_buffer(data, mime=True)

    match contentType:
        case "text/html":
            translation = translate_html(pathStr, partName, data)
            save_file(pathStr + "-" + partName, translation)

        case "text/plain":
            if isinstance(data, bytes):
                save_file(pathStr + "-" + partName, data)
            else :
                translation = translate_plain_text(pathStr, partName, data)
                save_file(pathStr + "-" + partName, translation.encode("utf-8"))

        case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            translate_docx(pathStr, partName, data)

        case "application/pdf":
            translation = translate_pdf(pathStr, partName, data)
            save_file(pathStr + "-" + partName, data)
            save_file(pathStr + "-" + partName + "-translated-content.txt", translation.encode("utf-8"))

        case _:
            save_file(pathStr + "-" + partName, data)


pathlist = Path(args.path).glob('**/*.eml')
for path in pathlist:
    file_count += 1
pathlist = Path(args.path).glob('**/*.eml')
print("Translating " + str(file_count) + " eml files")
current_count = 0
translation_needed = False
for path in pathlist:
    print(str(current_count) + " out of " + str(file_count) + " .eml files iterated")
    current_count += 1
    pathStr = str(path)

    if not replica_is_owner(pathStr):
        continue

    if os.path.isfile(pathStr+"-body-1.html"):
        print("Skipping " + pathStr+": Already translated.")
        continue
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
                process_email_part(content_type, pathStr, partName, part["content"])

    if "attachment" in parsed_eml:
        for attachment in parsed_eml["attachment"]:
            content_hdr = attachment["content_header"]
            content_type = content_hdr["content-type"][0]
            filename = attachment["filename"]
            process_email_part(content_type, pathStr, filename, base64.b64decode(attachment["raw"]))
