# Overview

First time:
```
git clone https://github.com/jlilienfeld/doc-translator
cd doc-translator
python3 -m venv .
source bin/activate
pip install -r requirements.txt
sudo apt-get install libmagic1
```

When using a new shell:
```
<Get into the repository director>
source bin/activate
```

Translator's usage:
```
python3 eml-translator.py
> usage: eml-translator [-h] [-l LANGUAGE] path
> eml-translator: error: the following arguments are required: path
```

Example:
```
python3 eml-translator.py /docs-folder
```


```
Processing /VGTRK/tmakarenkova@vgtrk.ru.pst/tmakarenkova@vgtrk.ru/Отправленные/190.eml
/VGTRK/tmakarenkova@vgtrk.ru.pst/tmakarenkova@vgtrk.ru/Отправленные/190.eml-rtf-body.rtf has been saved.
/VGTRK/tmakarenkova@vgtrk.ru.pst/tmakarenkova@vgtrk.ru/Отправленные/190.eml-DSC01010.JPG has been saved.
11421 out of 1031643 .eml files iterated
Processing /VGTRK/tmakarenkova@vgtrk.ru.pst/tmakarenkova@vgtrk.ru/Отправленные/141.eml
Traceback (most recent call last):
  File "/root/workspace/doc-translator/eml-translator.py", line 275, in <module>
    process_email_part(content_type, pathStr, partName, part["content"])
  File "/root/workspace/doc-translator/eml-translator.py", line 241, in process_email_part
    save_file(pathStr + "-" + partName, data)
  File "/root/workspace/doc-translator/eml-translator.py", line 97, in save_file
    translated_file.write(data)
TypeError: a bytes-like object is required, not 'str'
```
