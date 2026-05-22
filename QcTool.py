import os
import glob
import datetime
from bs4 import BeautifulSoup

class EpubAccessibilityReporter:
    def __init__(self, oebps_path):
        self.oebps_path = os.path.abspath(oebps_path)
        self.xhtml_dir = os.path.join(self.oebps_path, "xhtml")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.report_file = os.path.join(current_dir, "Accessibility_Report.html")
        
        if os.path.exists(self.xhtml_dir):
            self.xhtml_files = sorted(glob.glob(os.path.join(self.xhtml_dir, "*.xhtml")))
        else:
            self.xhtml_files = []

    def scan_for_errors(self):
        report_data = []
        for filepath in self.xhtml_files:
            filename = os.path.basename(filepath)
            file_errors = []
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'html.parser')

                    # 1. Image Check with role="presentation" logic
                    imgs = soup.find_all('img')
                    for img in imgs:
                        line_no = img.sourceline
                        alt_val = img.get('alt')
                        role_val = img.get('role')

                        # Condition 1: Alt attribute-ae illai (Strict Error)
                        if alt_val is None:
                            file_errors.append({"type": "Error", "line": line_no, "msg": "Missing 'alt' attribute."})
                        
                        # Condition 2: Alt empty-ah irukku, aana role="presentation" illai (Warning)
                        elif alt_val.strip() == "":
                            if role_val != "presentation":
                                file_errors.append({"type": "Warning", "line": line_no, "msg": "Empty alt found. Add role='presentation' for decorative images."})
                            # else: Inga alt="" matrum role="presentation" irukku, so ignore pannidum.

                    # 2. Heading ID Check
                    headings = soup.find_all(['h1', 'h2', 'h3'])
                    for h in headings:
                        line_no = h.sourceline
                        if not h.get('id'):
                            file_errors.append({"type": "Error", "line": line_no, "msg": f"Heading <{h.name}> missing an 'id'."})

                    # 3. First Section under Body Check (New Update)
                    body_tag = soup.find('body')
                    if body_tag:
                        # body-ku kela irukura muthal section tag-ah matum edukiroam
                        first_section = body_tag.find('section')
                        if first_section:
                            line_no = first_section.sourceline
                            
                            # Attributes validation
                            has_role = first_section.get('role')
                            has_epub_type = first_section.get('epub:type')
                            has_aria_label = first_section.get('aria-labelledby')
                            
                            missing_attrs = []
                            if not has_role:
                                missing_attrs.append("'role'")
                            if not has_epub_type:
                                missing_attrs.append("'epub:type'")
                            if not has_aria_label:
                                missing_attrs.append("'aria-labelledby'")
                                
                            if missing_attrs:
                                attrs_str = ", ".join(missing_attrs)
                                file_errors.append({
                                    "type": "Error", 
                                    "line": line_no, 
                                    "msg": f"First <section> under body is missing required attributes: {attrs_str}."
                                })

                # (Additional checks for lang attribute etc can stay here)

            except Exception as e:
                file_errors.append({"type": "Error", "line": "N/A", "msg": f"File read error: {str(e)}"})

            if file_errors:
                file_errors.sort(key=lambda x: x['line'] if isinstance(x['line'], int) else 0)
                report_data.append({"filename": filename, "errors": file_errors})
        
        return report_data

    def generate_html_report(self):
        if not self.xhtml_files:
            print(f"!!! Error: XHTML files kidaikala in {self.xhtml_dir}")
            return

        data = self.scan_for_errors()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>EPUB Accessibility Report</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 40px; background-color: #f4f7f6; }}
                .container {{ max-width: 1000px; margin: auto; }}
                h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
                .summary {{ text-align: center; margin-bottom: 30px; color: #7f8c8d; }}
                .file-card {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
                .filename {{ font-weight: bold; font-size: 1.2em; color: #2980b9; display: block; margin-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
                th {{ background-color: #f8f9fa; color: #333; }}
                .line-no {{ font-weight: bold; color: #555; width: 80px; }}
                .error-type {{ font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; }}
                .error {{ color: #c0392b; background: #f9ebea; }}
                .warning {{ color: #d35400; background: #fef5e7; }}
                .msg {{ color: #34495e; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Accessibility Audit Report</h1>
                <div class="summary">Generated: {now} | OEBPS: {self.oebps_path}</div>
        '''

        for item in data:
            html_content += f'''
            <div class="file-card">
                <span class="filename">📄 {item["filename"]}</span>
                <table>
                    <tr><th>Line</th><th>Type</th><th>Issue Description</th></tr>'''
            for err in item['errors']:
                type_class = err['type'].lower()
                html_content += f'''
                    <tr>
                        <td class="line-no">Line {err['line']}</td>
                        <td><span class="error-type {type_class}">{err['type']}</span></td>
                        <td class="msg">{err['msg']}</td>
                    </tr>'''
            html_content += "</table></div>"

        html_content += "</div></body></html>"

        try:
            with open(self.report_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"SUCCESS! Report created at: {self.report_file}")
        except Exception as e:
            print(f"!!! Error: {e}")

if __name__ == "__main__":
    OEBPS_FOLDER = r"C:\QC tool test\OEBPS"
    if os.path.exists(OEBPS_FOLDER):
        reporter = EpubAccessibilityReporter(OEBPS_FOLDER)
        reporter.generate_html_report()
    else:
        print("Path not found!")