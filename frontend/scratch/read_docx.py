import zipfile
import xml.etree.ElementTree as ET
import sys

def extract_text_from_docx(docx_path, out_path):
    try:
        with zipfile.ZipFile(docx_path, 'r') as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            paragraphs = tree.findall('.//w:p', ns)
            text = []
            for p in paragraphs:
                texts = p.findall('.//w:t', ns)
                p_text = ''.join([t.text for t in texts if t.text])
                if p_text:
                    text.append(p_text)
            
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text))
    except Exception as e:
        print(f"Error reading {docx_path}: {e}")

if __name__ == '__main__':
    extract_text_from_docx(sys.argv[1], sys.argv[2])
