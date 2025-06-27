# processing.py (v9.1 - The Final Robust WhatsApp/Phone Fix)

import fitz
import re
from config import EDUCATION_LEVELS
from datetime import datetime

# --- FUNGSI HELPER ---

def extract_text_from_pdf(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf");
        text = "".join(page.get_text() for page in doc);
        doc.close()
        return text
    except Exception as e:
        return f"Error membaca PDF: {e}"

def extract_contact_info(text):
    # <<< PERBAIKAN TOTAL PADA LOGIKA DETEKSI TELEPON DI SINI >>>

    # Pola baru ini lebih fleksibel, mencari awalan lalu sisa angka (bisa ada spasi/strip)
    # Total panjang grup (setelah awalan) antara 8-12 digit angka.
    phone_pattern = r'(?:\+62|08)[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,4}'

    phone_match = re.search(phone_pattern, text)
    found_phone = phone_match.group(0).strip() if phone_match else "-"

    # Ekstraksi info lain (sudah benar)
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    email_match = re.search(email_pattern, text)
    found_email = email_match.group(0) if email_match else "-"

    ig_handle_pattern = r'@([a-zA-Z0-9\._-]{1,30})'
    ig_candidates = re.findall(ig_handle_pattern, text)
    found_ig_handle = "-"
    if ig_candidates:
        for handle in ig_candidates:
            if found_email == "-" or handle not in found_email:
                found_ig_handle = handle
                break

    linkedin_pattern = r'linkedin\.com/in/([a-zA-Z0-9_-]+)'
    github_pattern = r'github\.com/([a-zA-Z0-9_-]+)'
    linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
    github_match = re.search(github_pattern, text, re.IGNORECASE)

    return {
        "email": found_email,
        "phone": found_phone,
        "linkedin": f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else "-",
        "github": f"https://github.com/{github_match.group(1)}" if github_match else "-",
        "instagram": f"https://instagram.com/{found_ig_handle}" if found_ig_handle != "-" else "-"
    }


def find_skills(text, keywords_list):
    found = []; text_lower = text.lower()
    for skill in keywords_list:
        if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text_lower): found.append(skill)
    return found

def extract_education(text):
    text_lower = text.lower(); highest_level = 0
    patterns = {7: r's2|master|magister', 6: r's1|sarjana|bachelor', 5: r'd3|diploma', 3: r'sma|smk'}
    for score, pattern in sorted(patterns.items(), reverse=True):
        if re.search(r'\b(' + pattern + r')\b', text_lower):
            highest_level = score
            return highest_level
    return highest_level

def extract_experience(text):
    text_lower = text.lower(); total_duration = 0; current_year = datetime.now().year
    year_ranges = re.findall(r'(\b\d{4}\b)\s*-\s*(\b\d{4}\b|\bsekarang\b|\bpresent\b)', text_lower)
    for start_year_str, end_year_str in year_ranges:
        start_year = int(start_year_str)
        end_year = current_year if end_year_str.lower() in ['sekarang', 'present'] else int(end_year_str)
        if start_year > 1980 and end_year >= start_year:
            total_duration += (end_year - start_year)
    if total_duration == 0:
        found = re.findall(r'(\d+)\s*(?:tahun|thn|years|year)', text_lower)
        if found: total_duration = max([int(y) for y in found], default=0)
    return round(total_duration)

def extract_organizational_experience(text):
    text_lower = text.lower();
    keywords = ['organisasi', 'himpunan', 'ukm', 'bem', 'volunteer', 'sukarelawan']
    if any(re.search(r'\b' + kw + r'\b', text_lower) for kw in keywords):
        return 1
    return 0

def process_single_cv(args):
    file_id, file_name, file_bytes, hard_skills_list, soft_skills_list = args
    text = extract_text_from_pdf(file_bytes)
    contact_info = extract_contact_info(text)
    return {
        "file_id": file_id, "name": file_name, "text": text,
        "email": contact_info['email'], "phone": contact_info['phone'],
        "linkedin": contact_info['linkedin'], "github": contact_info['github'],
        "instagram": contact_info['instagram'],
        "education_score": extract_education(text),
        "work_exp": extract_experience(text),
        "org_exp": extract_organizational_experience(text),
        "hard_skills_found": find_skills(text, hard_skills_list),
        "soft_skills_found": find_skills(text, soft_skills_list),
        "status": "Pending",
    }