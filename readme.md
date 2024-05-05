# Overview

First time:
```
git clone https://github.com/jlilienfeld/doc-translator
cd doc-translator
python3 -m venv .
source bin/activate
pip install -r requirements.txt
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