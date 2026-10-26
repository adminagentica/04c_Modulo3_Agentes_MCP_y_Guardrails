"""Extract paragraphs from approved source DOCX files using only the standard library."""
import json
import sys
import zipfile
import xml.etree.ElementTree as ET

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(sys.argv[1]) as source:
    if source.getinfo('word/document.xml').file_size > 8_000_000:
        raise ValueError('Documento demasiado grande para esta demo local.')
    document = ET.fromstring(source.read('word/document.xml'))
paragraphs = [''.join(p.itertext()).strip() for p in document.findall('.//w:body/w:p', ns)]
print(json.dumps([p for p in paragraphs if p], ensure_ascii=False))
