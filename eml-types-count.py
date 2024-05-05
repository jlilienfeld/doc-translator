from pathlib import Path
import argparse
import eml_parser

parser = argparse.ArgumentParser(
                    prog='eml-types-count',
                    description='Iterates a repository of eml files and returns all content-types found within',
                    epilog='')
parser.add_argument('path')
args = parser.parse_args()
print("Collection content types for all files in " + args.path)

translation_marker = "\n[AUTO_TRANSLATED] FROM "
file_count = 0

pathlist = Path(args.path).glob('**/*.eml')
for path in pathlist:
    file_count += 1
pathlist = Path(args.path).glob('**/*.eml')
print("Translating " + str(file_count) + " eml files")
current_count = 0
translation_needed = False
contentTypes = {}
failed_eml = []
for path in pathlist:
    print(str(current_count) + " out of " + str(file_count) + " .eml files translated")
    current_count += 1
    pathStr = str(path)
    print("Processing " + pathStr)

    ep = eml_parser.EmlParser()
    parsed_eml = None
    try:
        parsed_eml = ep.decode_email(path)
    except Exception as e:
        print("Failed to parse eml: " + pathStr)
        failed_eml.append(pathStr)
        continue

    if "body" in parsed_eml:
        body = parsed_eml["body"]
        for part in body:
            if "content_type" in part:
                content_type = part["content_type"]
                if content_type not in contentTypes:
                    contentTypes[content_type] = 1
                else:
                    contentTypes[content_type] += 1

    if "attachment" in parsed_eml:
        for attachment in parsed_eml["attachment"]:
            content_hdr = attachment["content_header"]
            content_type = content_hdr["content-type"][0]
            if content_type not in contentTypes:
                contentTypes[content_type] = 1
            else:
                contentTypes[content_type] += 1


file1 = open("results.txt", "w")

for content_type in contentTypes.keys():
    print(content_type + ": " + str(contentTypes[content_type]))
    file1.write(content_type + ": " + str(contentTypes[content_type]))

for eml in failed_eml:
    print("Failed: " + eml)
    file1.write("Failed: " + eml)

file1.close()
