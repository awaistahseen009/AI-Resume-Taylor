import os
import tempfile
import subprocess
from typing import Optional

# Optional dependency: xhtml2pdf (pure pip install)
try:
    from xhtml2pdf import pisa
except Exception:  # pragma: no cover
    pisa = None

# Optional dependency: plasTeX for LaTeX -> HTML preview
try:
    from plasTeX import TeX as _PlasTeXTeX
    from plasTeX.Renderers import HTML5 as _PlasTeXHTML5
except Exception:  # pragma: no cover
    _PlasTeXTeX = None
    _PlasTeXHTML5 = None

class PDFGenerator:
    """Service for generating PDF files from LaTeX source"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.latex_compiler = self._find_latex_compiler()
        self.last_method: Optional[str] = None  # 'latex' or 'html_fallback'
    
    def _find_latex_compiler(self) -> Optional[str]:
        """Find available LaTeX compiler (prefer XeLaTeX/LuaLaTeX for font support)"""
        compilers = ['xelatex', 'lualatex', 'pdflatex']
        for compiler in compilers:
            try:
                result = subprocess.run([compiler, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return compiler
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return None
    
    def generate_pdf(self, latex_source: str, output_name: str = None) -> str:
        """Generate PDF from LaTeX source"""
        if not output_name:
            output_name = f"resume_{os.getpid()}"
        
        # Try LaTeX compilation first
        if self.latex_compiler:
            try:
                pdf = self._compile_latex_to_pdf(latex_source, output_name)
                self.last_method = 'latex'
                return pdf
            except Exception as e:
                print(f"LaTeX compilation failed: {e}")
        
        # Fallback to HTML/CSS conversion
        pdf = self._generate_pdf_from_html(latex_source, output_name)
        self.last_method = 'html_fallback'
        return pdf

    def generate_html(self, latex_source: str) -> str:
        """Generate HTML preview from LaTeX source.
        Tries plasTeX if available; falls back to simple converter otherwise.
        """
        # Try plasTeX first
        if _PlasTeXTeX and _PlasTeXHTML5:
            try:
                tex = _PlasTeXTeX()
                tex.input(latex_source)
                doc = tex.parse()
                renderer = _PlasTeXHTML5.Renderer() if hasattr(_PlasTeXHTML5, 'Renderer') else _PlasTeXHTML5()
                result = renderer.render(doc)

                # plasTeX may return dict of files -> content
                if isinstance(result, dict):
                    # Prefer index.html or first .html
                    for key in ['index.html', 'index.htm']:
                        if key in result:
                            return result[key]
                    for k, v in result.items():
                        if isinstance(k, str) and k.lower().endswith(('.html', '.htm')):
                            return v
                    # Fallback: join all string contents
                    joined = ''.join(str(v) for v in result.values())
                    if joined:
                        return joined
                elif isinstance(result, str):
                    return result
            except Exception:
                # Ignore and fall back
                pass

        # Fallback simple converter
        return self._latex_to_html(latex_source)
    
    def _compile_latex_to_pdf(self, latex_source: str, output_name: str) -> str:
        """Compile LaTeX to PDF using pdflatex"""
        # Create temporary files
        tex_file = os.path.join(self.temp_dir, f"{output_name}.tex")
        pdf_file = os.path.join(self.temp_dir, f"{output_name}.pdf")
        
        # Write LaTeX source to file
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_source)
        
        # Compile LaTeX
        try:
            # Run pdflatex twice for proper cross-references
            for _ in range(2):
                result = subprocess.run([
                    self.latex_compiler,
                    '-interaction=nonstopmode',
                    '-halt-on-error',
                    '-output-directory', self.temp_dir,
                    tex_file
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    raise Exception(f"LaTeX compilation error (using {self.latex_compiler}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            
            if not os.path.exists(pdf_file):
                raise Exception("PDF file was not generated")
            
            return pdf_file
            
        except subprocess.TimeoutExpired:
            raise Exception("LaTeX compilation timed out")
        except Exception as e:
            # Clean up temporary files
            for ext in ['.tex', '.aux', '.log', '.out']:
                temp_file = os.path.join(self.temp_dir, f"{output_name}{ext}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            raise e
    
    def _generate_pdf_from_html(self, latex_source: str, output_name: str) -> str:
        """Fallback: Convert LaTeX-like content to HTML then PDF using xhtml2pdf"""
        # Convert LaTeX to HTML-like format
        html_content = self._latex_to_html(latex_source)

        if pisa is None:
            raise Exception(
                "xhtml2pdf is not installed. Install with 'pip install xhtml2pdf' to enable PDF generation without wkhtmltopdf."
            )

        pdf_file = os.path.join(self.temp_dir, f"{output_name}.pdf")
        # Write intermediate HTML for debugging/inspection
        try:
            html_debug_path = os.path.join(self.temp_dir, f"{output_name}.html")
            with open(html_debug_path, 'w', encoding='utf-8') as hf:
                hf.write(html_content)
        except Exception:
            pass
        try:
            with open(pdf_file, 'wb') as out_f:
                result = pisa.CreatePDF(src=html_content, dest=out_f, encoding='utf-8')
            if result.err:
                raise Exception("xhtml2pdf failed to generate PDF")
            if not os.path.exists(pdf_file):
                raise Exception("PDF file was not generated")
            return pdf_file
        except Exception as e:
            raise Exception(f"PDF generation failed: {str(e)}")
    
    def _latex_to_html(self, latex_source: str) -> str:
        """Convert basic LaTeX to HTML for PDF generation.
        If no LaTeX document markers are present, treat entire input as body text."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { 
                    font-family: 'Times New Roman', serif; 
                    font-size: 11pt; 
                    line-height: 1.4; 
                    margin: 0; 
                    padding: 20px;
                }
                .header { 
                    text-align: center; 
                    margin-bottom: 20px; 
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }
                .name { 
                    font-size: 18pt; 
                    font-weight: bold; 
                    margin-bottom: 5px; 
                }
                .contact { 
                    font-size: 10pt; 
                    color: #666; 
                }
                .section { 
                    margin: 15px 0; 
                }
                .section-title { 
                    font-size: 12pt; 
                    font-weight: bold; 
                    text-transform: uppercase; 
                    border-bottom: 1px solid #333; 
                    margin-bottom: 8px; 
                    padding-bottom: 2px;
                }
                .item { 
                    margin: 8px 0; 
                }
                .item-title { 
                    font-weight: bold; 
                    margin-bottom: 3px; 
                }
                .item-details { 
                    margin-left: 15px; 
                }
                ul { 
                    margin: 5px 0; 
                    padding-left: 20px; 
                }
                li { 
                    margin: 2px 0; 
                }
            </style>
        </head>
        <body>
        """
        
        # Parse LaTeX content and convert to HTML
        lines = latex_source.split('\n')
        # If no explicit document markers, render entire content
        has_explicit_doc = ('\\begin{document}' in latex_source) or ('\\end{document}' in latex_source)
        in_document = not has_explicit_doc  # start in document if no explicit markers
        current_section = None
        any_content = False
        
        for line in lines:
            line = line.strip()
            
            if '\\begin{document}' in line:
                in_document = True
                continue
            elif '\\end{document}' in line:
                break
            elif not in_document:
                continue
            
            # Parse LaTeX commands
            if '\\name{' in line:
                name = self._extract_latex_content(line, '\\name{')
                html += f'<div class="header"><div class="name">{name}</div>'
                any_content = True
            elif '\\phone' in line or '\\email' in line or '\\social' in line:
                contact = self._extract_latex_content(line, '{')
                html += f'<div class="contact">{contact}</div>'
            elif '\\makecvtitle' in line:
                html += '</div>'  # Close header
            elif '\\section{' in line:
                if current_section:
                    html += '</div>'  # Close previous section
                section_title = self._extract_latex_content(line, '\\section{')
                html += f'<div class="section"><div class="section-title">{section_title}</div>'
                current_section = section_title
                any_content = True
            elif '\\cventry{' in line:
                # Extract entry content (simplified)
                content = line.replace('\\cventry{', '').replace('}', '')
                html += f'<div class="item"><div class="item-title">{content}</div></div>'
                any_content = True
            elif '\\item ' in line:
                item_content = line.replace('\\item ', '')
                html += f'<li>{item_content}</li>'
                any_content = True
            elif line and not line.startswith('\\'):
                html += f'<p>{line}</p>'
                any_content = True
        
        if current_section:
            html += '</div>'  # Close last section
        
        # Fallback: if nothing was parsed/added, render entire input as paragraphs
        if not any_content:
            body = '\n'.join(l for l in lines if l.strip())
            # Simple paragraphization
            paras = ''.join(f'<p>{line.strip()}</p>' for line in body.split('\n'))
            html += paras

        html += '</body></html>'
        return html
    
    def _extract_latex_content(self, line: str, command: str) -> str:
        """Extract content from LaTeX command"""
        start = line.find(command)
        if start == -1:
            return ""
        
        start += len(command)
        brace_count = 0
        content = ""
        
        for char in line[start:]:
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    break
                brace_count -= 1
            else:
                content += char
        
        return content.strip()
    
    def cleanup_temp_files(self, file_path: str):
        """Clean up temporary files"""
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass  # Ignore cleanup errors
