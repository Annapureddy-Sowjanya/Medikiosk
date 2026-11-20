from pathlib import Path
from pypdf import PdfReader
def extract_text(path:Path):
 suffix=path.suffix.lower()
 if suffix=='.pdf':
  try:
   text='\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages).strip()
   if text:return text[:100000], 'extracted'
   try:
    from pdf2image import convert_from_path
    import pytesseract
    pages=convert_from_path(str(path),first_page=1,last_page=8); text='\n'.join(pytesseract.image_to_string(p) for p in pages).strip()
    return (text[:100000],'ocr') if text else ('No text detected. Check scan quality.','empty')
   except Exception:return ('This PDF appears scanned. Install Poppler and pdf2image for scanned-PDF OCR.','needs_ocr_setup')
  except Exception:return ('Could not read this PDF. Check that it is valid.','error')
 try:
  import pytesseract
  from PIL import Image
  text=pytesseract.image_to_string(Image.open(path).convert('RGB')).strip()
  return (text[:100000],'ocr') if text else ('No text detected. Check image quality.','empty')
 except Exception as exc:return (f'OCR could not run ({type(exc).__name__}). Install Tesseract OCR and check PATH.','needs_ocr_setup')
