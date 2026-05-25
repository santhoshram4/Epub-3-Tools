import os
import glob
import datetime
import html
import re
import sys

# Checking for required libraries and guiding the user if missing
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("\n" + "!"*60)
    print(" [ERROR] 'beautifulsoup4' library is NOT installed in this system!")
    print(" Please run the following command in CMD to install it:")
    print(" >>> pip install beautifulsoup4 lxml")
    print("!"*60 + "\n")
    input("Press Enter to exit...")
    sys.exit(1)

class EpubAccessibilityReporter:
    def __init__(self, oebps_path):
        self.oebps_path = os.path.abspath(oebps_path)
        self.xhtml_dir = os.path.join(self.oebps_path, "xhtml")
        
        # 🌟 FIXED FOR EXE: Using os.getcwd() instead of __file__ to avoid Temp folder issue
        current_dir = os.getcwd()
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

                        if alt_val is None:
                            file_errors.append({"type": "Error", "line": line_no, "msg": "Missing 'alt' attribute."})
                        elif alt_val.strip() == "":
                            if role_val != "presentation":
                                file_errors.append({"type": "Warning", "line": line_no, "msg": "Empty alt found. Add role='presentation' for decorative images."})

                    # 2. Heading Check (ID & epub:type Validation)
                    headings = soup.find_all(['h1', 'h2', 'h3'])
                    for h in headings:
                        line_no = h.sourceline
                        if not h.get('id'):
                            file_errors.append({"type": "Error", "line": line_no, "msg": f"Heading <{h.name}> missing an 'id'."})
                        if not h.get('epub:type'):
                            file_errors.append({"type": "Error", "line": line_no, "msg": f"Heading <{h.name}> missing an 'epub:type' attribute."})

                    # 3. First Section under Body Check
                    body_tag = soup.find('body')
                    if body_tag:
                        first_section = body_tag.find('section')
                        if first_section:
                            line_no = first_section.sourceline
                            has_role = first_section.get('role')
                            has_epub_type = first_section.get('epub:type')
                            has_aria_label = first_section.get('aria-labelledby')
                            
                            missing_attrs = []
                            if not has_role: missing_attrs.append("'role'")
                            if not has_epub_type: missing_attrs.append("'epub:type'")
                            if not has_aria_label: missing_attrs.append("'aria-labelledby'")
                                
                            if missing_attrs:
                                attrs_str = ", ".join(missing_attrs)
                                file_errors.append({
                                    "type": "Error", 
                                    "line": line_no, 
                                    "msg": f"First <section> under body is missing required attributes: {attrs_str}."
                                })

                    # 4. Table Validation
                    tables = soup.find_all('table')
                    for table in tables:
                        line_no = table.sourceline
                        if not table.find('colgroup'):
                            file_errors.append({
                                "type": "Error",
                                "line": line_no,
                                "msg": "Table is missing a <colgroup> element."
                            })

                    # 5. Table Header<th> Validation
                    ths = soup.find_all('th')
                    for th in ths:
                        line_no = th.sourceline
                        if not th.get('scope'):
                            file_errors.append({"type": "Error", "line": line_no, "msg": "Table header <th> is missing a 'scope' attribute."})
                        if not th.find('p'):
                            file_errors.append({"type": "Error", "line": line_no, "msg": "Table header <th> must contain a <p> tag."})

                    # 6. Table Data<td> Validation
                    tds = soup.find_all('td')
                    for td in tds:
                        line_no = td.sourceline
                        if not td.find('p'):
                            file_errors.append({"type": "Error", "line": line_no, "msg": "Table cell <td> must contain a <p> tag."})

                    # 7. List Validation (<ul> and <ol>)
                    lists = soup.find_all(['ul', 'ol'])
                    for lisele in lists:
                        line_no = lisele.sourceline
                        if not lisele.get('role'):
                            file_errors.append({
                                "type": "Error",
                                "line": line_no,
                                "msg": f"List <{lisele.name}> is missing a 'role' attribute."
                            })

                    # 8. Figure Validation
                    figures = soup.find_all('figure')
                    for fig in figures:
                        line_no = fig.sourceline
                        first_child = fig.find(True) 
                        if not first_child or first_child.name != 'p':
                            file_errors.append({
                                "type": "Error",
                                "line": line_no,
                                "msg": "The <figure> tag must contain a <p> tag directly before the <img> tag."
                            })

            except Exception as e:
                file_errors.append({"type": "Error", "line": "N/A", "msg": f"File read error: {str(e)}"})

            if file_errors:
                file_errors.sort(key=lambda x: x['line'] if isinstance(x['line'], int) else 0)
            
            report_data.append({"filename": filename, "errors": file_errors})
        
        return report_data

    def generate_html_report(self):
        if not self.xhtml_files:
            print(f"\n[ERROR] XHTML files kidaikala in: {self.xhtml_dir}")
            input("Press Enter to exit...")
            return

        print(f"\n>>> Scanning XHTML files in {self.xhtml_dir}...")
        data = self.scan_for_errors()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>EPUB Accessibility Report</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 40px; background-color: #f4f7f6; }}
                .container {{ max-width: 1000px; margin: auto; }}
                h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
                .summary {{ text-align: center; margin-bottom: 30px; color: #7f8c8d; }}
                .file-card {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
                .filename {{ font-weight: bold; font-size: 1.2em; color: #2980b9; display: block; margin-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; vertical-align: middle; }}
                th {{ background-color: #f8f9fa; color: #333; }}
                .line-no {{ font-weight: bold; color: #555; width: 120px; }}
                .type-col {{ width: 120px; }}
                .error-type {{ font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; display: inline-block; text-align: center; width: 70px; }}
                .error {{ color: #c0392b; background: #f9ebea; }}
                .warning {{ color: #d35400; background: #fef5e7; }}
                .success-row {{ background-color: #e8f8f5; color: #117a65; font-weight: bold; font-size: 0.95em; padding: 15px; border-radius: 4px; border-left: 5px solid #1abc9c; margin-top: 10px; }}
                .msg {{ color: #34495e; line-height: 1.5; white-space: normal; word-break: normal; }}
                .msg b {{ color: #2c3e50; background-color: #eaecef; padding: 2px 4px; border-radius: 4px; font-family: Consolas, monospace; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Accessibility Audit Report</h1>
                <div class="summary">Generated: {now} | OEBPS: {self.oebps_path}</div>
        '''

        total_files_scanned = len(data)
        total_errors_count = 0
        issue_files_count = 0

        for item in data:
            html_content += f'''
            <div class="file-card">
                <span class="filename">📄 {item["filename"]}</span>'''
            
            if not item['errors']:
                html_content += f'''
                <div class="success-row">🎉 No issues found! Perfect file.</div>
                </div>'''
            else:
                issue_files_count += 1
                total_errors_count += len(item['errors'])
                html_content += f'''
                <table>
                    <tr><th style="width: 15%;">Line</th><th style="width: 15%;">Type</th><th style="width: 70%;">Issue Description</th></tr>'''
                for err in item['errors']:
                    type_class = err['type'].lower()
                    safe_msg = html.escape(err['msg'])
                    
                    bolded_msg = re.sub(r"((?:&#x27;|&#39;|').*?(?:&#x27;|&#39;|')|&lt;.*?&gt;|<.*?>)", lambda m: f"<b>{m.group(0)}</b>", safe_msg)
                    
                    html_content += f'''
                        <tr>
                            <td class="line-no">Line {err['line']}</td>
                            <td class="type-col"><span class="error-type {type_class}">{err['type']}</span></td>
                            <td class="msg">{bolded_msg}</td>
                        </tr>'''
                html_content += "</table></div>"

        html_content += "</div></body></html>"

        try:
            with open(self.report_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print("\n" + "="*50)
            print(" 🎉 PROCESS COMPLETED SUCCESSFULLY! 🎉")
            print("="*50)
            print(f" 📅 Timestamp       : {now}")
            print(f" 📁 Total Scanned    : {total_files_scanned} file(s)")
            print(f" 🗂️ Files with Issue : {issue_files_count} file(s)")
            print(f" ⚠️ Total Issues Found: {total_errors_count}")
            print(f" 📄 Report Saved At  : {self.report_file}")
            print("="*50)
            
            input("Press Enter to exit...")
            
        except Exception as e:
            print(f"\n[ERROR] Report write panna mudiyala: {e}")
            input("Press Enter to exit...")

if __name__ == "__main__":
    # 🌟 EXE friendly dynamic path detection
    # 'os.getcwd()' will always look at the current folder where the user double-clicks the EXE
    CURRENT_WORKING_DIR = os.getcwd()
    OEBPS_FOLDER = os.path.join(CURRENT_WORKING_DIR, "OEBPS")
    
    if os.path.exists(OEBPS_FOLDER):
        reporter = EpubAccessibilityReporter(OEBPS_FOLDER)
        reporter.generate_html_report()
    else:
        print(f"\n[ERROR] 'OEBPS' folder kidaikala!")
        print(f"Intha tool-ai entha folder-il vaithullirogal, adhae folder kulla 'OEBPS' irukka vendum.")
        print(f"Expected Path: {OEBPS_FOLDER}")
        print("="*50)
        input("Press Enter to exit...")