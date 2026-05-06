import os
import re
import glob
from bs4 import BeautifulSoup

class EpubAutomationTool:
    def __init__(self, oebps_path, isbn, title):
        self.path = os.path.abspath(oebps_path)
        self.xhtml_dir = os.path.join(self.path, "xhtml")
        self.isbn = isbn
        self.title = title
        
        if os.path.exists(self.xhtml_dir):
            self.xhtml_files = sorted([os.path.basename(f) for f in glob.glob(os.path.join(self.xhtml_dir, "*.xhtml"))])
        else:
            self.xhtml_files = []
            
        self.nav_data = [] # For navMap/TOC
        self.page_list = [] # For pageList/page-map
        self.play_order = 1

    def clean_text(self, text):
        return " ".join(text.split())

    def scan_contents(self):
        print(f"Scanning {len(self.xhtml_files)} files...")
        for filename in self.xhtml_files:
            filepath = os.path.join(self.xhtml_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'xml')
                
                # 1. Scanning for Headings (Modules/Sessions)
                headings = soup.find_all(['h1', 'h2'], id=True)
                for h in headings:
                    self.nav_data.append({
                        "id": h['id'],
                        "label": self.clean_text(h.get_text()),
                        "src": f"xhtml/{filename}#{h['id']}",
                        "order": str(self.play_order)
                    })
                    self.play_order += 1

                # 2. Scanning for Page Numbers
                pages = soup.find_all(id=re.compile(r'^page_'))
                for p in pages:
                    p_val = p['id'].replace('page_', '')
                    self.page_list.append({
                        "id": f"p{self.play_order}",
                        "value": p_val,
                        "label": p_val,
                        "src": f"xhtml/{filename}#{p['id']}",
                        "order": str(self.play_order)
                    })
                    self.play_order += 1

    def generate_ncx(self):
        print("Generating toc.ncx...")
        nav_points = ""
        for item in self.nav_data:
            nav_points += f'''    <navPoint id="{item['id']}" playOrder="{item['order']}">
      <navLabel><text>{item['label']}</text></navLabel>
      <content src="{item['src']}"/>
    </navPoint>\n'''

        page_targets = ""
        for p in self.page_list:
            page_targets += f'''    <pageTarget id="{p['id']}" type="normal" playOrder="{p['order']}" value="{p['value']}">
      <navLabel><text>{p['label']}</text></navLabel>
      <content src="{p['src']}"/>
    </pageTarget>\n'''

        ncx_template = f'''<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en">
  <head>
    <meta name="dtb:uid" content="urn:isbn:{self.isbn}"/>
    <meta name="dtb:depth" content="2"/>
    <meta name="dtb:totalPageCount" content="{len(self.page_list)}"/>
    <meta name="dtb:maxPageNumber" content="{len(self.page_list)}"/>
  </head>
  <docTitle><text>{self.title}</text></docTitle>
  <navMap>
{nav_points}  </navMap>
  <pageList>
{page_targets}  </pageList>
</ncx>'''
        with open(os.path.join(self.path, "toc.ncx"), "w", encoding="utf-8") as f:
            f.write(ncx_template)

    def generate_nav(self):
        print("Generating nav.xhtml...")
        list_items = "".join([f'<li><a href="{i["src"]}">{i["label"]}</a></li>\n' for i in self.nav_data])
        page_items = "".join([f'<li><a href="{p["src"]}">{p["label"]}</a></li>\n' for p in self.page_list])

        nav_template = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
{list_items}    </ol>
  </nav>
  <nav epub:type="page-list" id="page-list" hidden="hidden">
    <ol>
{page_items}    </ol>
  </nav>
</body>
</html>'''
        with open(os.path.join(self.path, "nav.xhtml"), "w", encoding="utf-8") as f:
            f.write(nav_template)

    def generate_opf(self):
        print("Generating content.opf...")
        manifest = []
        spine = []
        
        manifest.append('    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
        manifest.append('    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
        
        img_path = os.path.join(self.path, "images")
        if os.path.exists(img_path):
            for f in os.listdir(img_path):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                    ext = f.split('.')[-1].lower()
                    m_type = "image/png" if ext == "png" else "image/jpeg"
                    if ext == "svg": m_type = "image/svg+xml"
                    manifest.append(f'    <item id="img_{f.replace(".","_")}" href="images/{f}" media-type="{m_type}"/>')

        css_path = os.path.join(self.path, "styles")
        if os.path.exists(css_path):
            for f in os.listdir(css_path):
                if f.endswith(".css"):
                    manifest.append(f'    <item id="css_{f.replace(".","_")}" href="styles/{f}" media-type="text/css"/>')

        for f in self.xhtml_files:
            item_id = f.replace(".xhtml", "").replace("-", "_")
            manifest.append(f'    <item id="{item_id}" href="xhtml/{f}" media-type="application/xhtml+xml"/>')
            spine.append(f'    <itemref idref="{item_id}"/>')

        opf_template = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="pub-id" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:isbn:{self.isbn}</dc:identifier>
    <dc:title>{self.title}</dc:title>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">2024-05-05T12:00:00Z</meta>
  </metadata>
  <manifest>
{"\n".join(manifest)}
  </manifest>
  <spine toc="ncx">
{"\n".join(spine)}
  </spine>
  <guide>
    <reference type="toc" title="Table of Contents" href="nav.xhtml"/>
    <reference type="text" title="Beginning" href="xhtml/{self.xhtml_files[0] if self.xhtml_files else ''}"/>
  </guide>
</package>'''
        
        with open(os.path.join(self.path, "content.opf"), "w", encoding="utf-8") as f:
            f.write(opf_template)
        print("Success: OPF (with Guide tag), NCX, and NAV generated!")

# --- Execution ---
if __name__ == "__main__":
    OEBPS_PATH = r"C:\tools-test\OEBPS" 
    tool = EpubAutomationTool(OEBPS_PATH, "9781663050632", "Magnetic Literacy")
    if os.path.exists(OEBPS_PATH):
        tool.scan_contents()
        tool.generate_ncx()
        tool.generate_nav()
        tool.generate_opf()