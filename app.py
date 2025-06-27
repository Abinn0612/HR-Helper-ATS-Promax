# app.py (v9.2 - The Final Stable Version)

import streamlit as st
import pandas as pd
import io
import re
from multiprocessing import Pool, cpu_count
from config import EDUCATION_KEYS, EDUCATION_LEVELS
from processing import process_single_cv

# --- FUNGSI HELPER ---
def calculate_final_score(candidate_data, config):
    min_edu_score = EDUCATION_LEVELS.get(config.get('min_education', 'S1'), 6)
    edu_score = 1.0 if candidate_data.get('education_score', 0) >= min_edu_score else candidate_data.get('education_score', 0) / 7.0
    work_exp = candidate_data.get('work_exp', 0); min_work_exp = config.get('min_work_exp', 1)
    exp_score = min(work_exp, min_work_exp) / min_work_exp if min_work_exp > 0 else 1.0
    org_exp = candidate_data.get('org_exp', 0); min_org_exp = config.get('min_org_exp', 1)
    org_score = min(org_exp, min_org_exp) / min_org_exp if min_org_exp > 0 else 1.0
    hard_skills_found = candidate_data.get('hard_skills_found', [])
    hard_skills_list = config.get('hard_skills_list', [])
    hard_skill_score = len(hard_skills_found) / len(hard_skills_list) if hard_skills_list else 0
    soft_skills_found = candidate_data.get('soft_skills_found', [])
    soft_skills_list = config.get('soft_skills_list', [])
    soft_skill_score = len(soft_skills_found) / len(soft_skills_list) if soft_skills_list else 0
    weights = config.get('weights', {});
    total_score = ((edu_score * weights.get('edu', 0.15)) + (exp_score * weights.get('work', 0.30)) + (org_score * weights.get('org', 0.05)) + (hard_skill_score * weights.get('hard', 0.40)) + (soft_skill_score * weights.get('soft', 0.10)))
    candidate_data['scores'] = {'Pendidikan': edu_score, 'Pengalaman Kerja': exp_score, 'Pengalaman Organisasi': org_score, 'Hard Skill': hard_skill_score, 'Soft Skill': soft_skill_score}
    candidate_data['final_score'] = total_score
    return candidate_data

def get_recommendation(score):
    if score >= 0.8: return "⭐⭐⭐ Sangat Direkomendasikan";
    if score >= 0.6: return "⭐⭐ Direkomendasikan";
    if score >= 0.4: return "⭐ Dipertimbangkan";
    return "❌ Kurang Sesuai"

def generate_excel_report(accepted_candidates, job_title):
    if not accepted_candidates: return None
    report_data = [{"Posisi":job_title, "Nama":d.get('name','-'), "Email":d.get('email','-'), "Telepon":d.get('phone','-'), "LinkedIn":d.get('linkedin','-'), "GitHub":d.get('github','-'), "Instagram":d.get('instagram','-'), "Skor":f"{d.get('final_score',0):.0%}", "Hard Skills":", ".join(d.get('hard_skills_found',[])), "Soft Skills":", ".join(d.get('soft_skills_found',[])), "Pendidikan":next((k for k,v in EDUCATION_LEVELS.items() if v==d.get('education_score')),"N/A"), "Pengalaman Kerja (Thn)":d.get('work_exp',0)} for d in accepted_candidates]
    df = pd.DataFrame(report_data); output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Kandidat Diterima')
    return output.getvalue()

def generate_action_link(contact_type, value):
    if not value or value == '-': return None
    if contact_type == 'email': return f"mailto:{value}";
    if contact_type == 'phone':
        cleaned = re.sub(r'[\s-]', '', value);
        if cleaned.startswith('0'): cleaned = '62'+cleaned[1:]
        elif cleaned.startswith('+'): cleaned = cleaned[1:]
        return f"https://wa.me/{cleaned}"
    return value if 'http' in value else f"https://{value}"

# --- STATE MANAGEMENT (SUDAH BENAR) ---
def select_candidate(cid): st.session_state.selected_candidate_id = cid
def delete_candidate(cid):
    if cid in st.session_state.candidates: st.session_state.candidates.pop(cid, None)
    if st.session_state.selected_candidate_id == cid: st.session_state.selected_candidate_id = None
    st.toast("Kandidat dihapus.", icon="🗑️")

def update_candidate_status(cid, status):
    if cid in st.session_state.candidates:
        st.session_state.candidates[cid]['status'] = status
        pending = [k for k, d in st.session_state.candidates.items() if d.get('status') == 'Pending']
        st.session_state.selected_candidate_id = pending[0] if pending else None
    
# --- INISIALISASI ---
def init_state():
    st.set_page_config(page_title="HR-Helper ATS Promax", page_icon="🚀", layout="wide")
    if 'app_ready' not in st.session_state:
        st.session_state.app_ready = True
        default_state = {'candidates': {}, 'selected_candidate_id': None, 'edit_mode': True, 'processed_file_ids': set()}
        for k, v in default_state.items():
            if k not in st.session_state: st.session_state[k] = v
        default_config = {"job_title":"Programmer", "min_education":"S1", "min_work_exp":1.0, "min_org_exp":0.0, "hard_skills_str":"Python,JavaScript,SQL,Git,API,HTML,CSS,React", "soft_skills_str":"Komunikasi,Kerja sama tim,Problem solving", "weight_edu":15, "weight_work":30, "weight_org":5, "weight_hard":40, "weight_soft":10}
        for k, v in default_config.items():
            if k not in st.session_state: st.session_state[k] = v

init_state()

# --- MAIN APP LAYOUT ---
st.title("🚀 HR-Helper: ATS Promax")

if __name__ == "__main__":
    c1, c2 = st.columns([1, 2])
    with c1:
        st.header("⚙ Panel Kontrol")
        with st.container(border=True): # Kriteria
            if st.session_state.edit_mode:
                with st.form("config_form"):
                    st.subheader("📝 Edit Kriteria")
                    st.text_input("Posisi", st.session_state.job_title, key="form_job_title")
                    st.selectbox("Pend. Min.", options=EDUCATION_KEYS, index=EDUCATION_KEYS.index(st.session_state.min_education), key="form_min_education")
                    st.number_input("Pengalaman Kerja Min.", min_value=0.0, step=0.5, value=st.session_state.min_work_exp, key="form_min_work_exp")
                    st.number_input("Pengalaman Organisasi Min.", min_value=0.0, step=0.5, value=st.session_state.min_org_exp, key="form_min_org_exp")
                    st.text_area("Hard Skills", value=st.session_state.hard_skills_str, key="form_hard_skills_str")
                    st.text_area("Soft Skills", value=st.session_state.soft_skills_str, key="form_soft_skills_str")
                    st.subheader("Bobot Skor")
                    b_cols = st.columns(2)
                    with b_cols[0]: st.number_input("Pend. (%)",0,100,st.session_state.weight_edu, key="form_weight_edu"); st.number_input("Kerja (%)",0,100,st.session_state.weight_work, key="form_weight_work"); st.number_input("Organisasi (%)",0,100,st.session_state.weight_org, key="form_weight_org")
                    with b_cols[1]: st.number_input("Hard (%)",0,100,st.session_state.weight_hard, key="form_weight_hard"); st.number_input("Soft (%)",0,100,st.session_state.weight_soft, key="form_weight_soft")
                    if st.form_submit_button("✔️ Selesai & Simpan", use_container_width=True, type="primary"):
                        total_w = sum([st.session_state[f"form_weight_{k}"] for k in ["edu","work","org","hard","soft"]])
                        if total_w != 100: st.error("Total bobot harus 100%!")
                        else:
                            form_keys = ["job_title", "min_education", "min_work_exp", "min_org_exp", "hard_skills_str", "soft_skills_str", "weight_edu", "weight_work", "weight_org", "weight_hard", "weight_soft"]
                            for key in form_keys: st.session_state[key] = st.session_state[f"form_{key}"]
                            st.session_state.edit_mode=False; st.rerun()
            else:
                st.subheader(f"Kriteria: {st.session_state.job_title}")
                if st.button("✏️ Edit", use_container_width=True): st.session_state.edit_mode=True; st.rerun()

        with st.container(border=True):
            st.subheader("📂 Unggah CV");
            uploaded_files = st.file_uploader("Upload",type="pdf",accept_multiple_files=True,disabled=st.session_state.edit_mode,label_visibility="collapsed")
        
        with st.container(border=True):
            st.subheader("👥 Kandidat"); query = st.text_input("Cari",label_visibility="collapsed", placeholder="Ketik nama...").lower()
            statuses, labels = ["Pending","Diterima","Ditolak"], [f"{s} ({len([c for c in st.session_state.candidates.values() if c.get('status')==s and query in c.get('name','').lower()])})" for s in ["Pending","Diterima","Ditolak"]]
            tabs = st.tabs(labels)
            for i, tab in enumerate(tabs):
                with tab:
                    filtered = {cid: d for cid, d in st.session_state.candidates.items() if d.get('status')==statuses[i] and query in d.get('name','').lower()}
                    if not filtered: st.caption("Tidak ada kandidat.")
                    else:
                        for cid, d in filtered.items():
                            r1,r2=st.columns([0.85,0.15]);r1.button(f"{d.get('name','N/A')} ({d.get('final_score',0):.0%})",key=f"sel_{cid}",on_click=select_candidate,args=(cid,),use_container_width=True);r2.button("🗑️",key=f"del_{cid}",on_click=delete_candidate,args=(cid,),use_container_width=True,help=f"Hapus {d.get('name','N/A')}")

        excel_data = generate_excel_report([d for d in st.session_state.candidates.values() if d['status'] == 'Diterima'], st.session_state.job_title)
        if excel_data: st.download_button("📄 Unduh Laporan", excel_data, "laporan_diterima.xlsx", use_container_width=True)

    with c2: # PANEL KANAN
        st.header(f"Seleksi {st.session_state.job_title}")
        if uploaded_files:
            h_s,s_s=[k.strip()for k in st.session_state.hard_skills_str.split(',')],[k.strip()for k in st.session_state.soft_skills_str.split(',')]
            tasks=[(f.file_id,f.name,f.getvalue(),h_s,s_s) for f in uploaded_files if f.file_id not in st.session_state.processed_file_ids]
            if tasks:
                with st.spinner(f"Memproses {len(tasks)} CV..."):
                    with Pool(processes=min(cpu_count(),len(tasks))) as p: results=p.map(process_single_cv,tasks)
                weights={'edu':st.session_state.weight_edu/100, 'work':st.session_state.weight_work/100, 'org':st.session_state.weight_org/100, 'hard':st.session_state.weight_hard/100, 'soft':st.session_state.weight_soft/100}
                cfg={'min_education':st.session_state.min_education, 'min_work_exp':st.session_state.min_work_exp, 'min_org_exp':st.session_state.min_org_exp, 'hard_skills_list':h_s, 'soft_skills_list':s_s, 'weights':weights}
                for res in results: st.session_state.processed_file_ids.add(res['file_id']);st.session_state.candidates[res['file_id']]=calculate_final_score(res,cfg)
                st.success("Selesai!");st.rerun()

        if not st.session_state.selected_candidate_id: st.info("Pilih kandidat dari panel kiri.")
        elif st.session_state.selected_candidate_id not in st.session_state.candidates: st.warning("Kandidat tidak tersedia.")
        else:
            cid,data=st.session_state.selected_candidate_id,st.session_state.candidates.get(st.session_state.selected_candidate_id)
            if data:
                with st.container(border=True):
                    st.subheader(f"📄 Detail: {data.get('name','N/A')}");st.markdown(f"**Status:** `{data.get('status','N/A')}`");st.markdown("---")
                    st.subheader("📝 Ringkasan"); d_c1,d_c2=st.columns(2); edu_lvl=next((k for k,v in EDUCATION_LEVELS.items() if v==data.get('education_score')),"N/A"); d_c1.metric("Pendidikan",edu_lvl); d_c2.metric("Pengalaman Kerja",f"{data.get('work_exp',0)} Thn");st.markdown("---")
                    st.subheader("📞 Kontak & Aksi");
                    for k,l in {'email':'💌 Email','phone':'💬 WhatsApp','linkedin':'🔗 LinkedIn','github':'💻 GitHub','instagram':'📸 Instagram'}.items():
                        val=data.get(k);
                        if val and val!='-':
                            link=generate_action_link(k,val);
                            if link: st.link_button(f"{l} {val.replace('https://','')}", link, use_container_width=True)
                    st.markdown("---");
                    st.subheader("📊 Skor"); s_c1,s_c2=st.columns(2)
                    with s_c1: st.write("**Skor Akhir:**");st.progress(data.get('final_score',0));st.markdown(f"## {data.get('final_score',0):.0%}");st.success(get_recommendation(data.get('final_score',0)))
                    with s_c2:
                        st.write("**Rincian:**"); scores=data.get('scores',{});
                        st.text(f"Pendidikan: {scores.get('Pendidikan',0):.0%}");st.text(f"Kerja: {scores.get('Pengalaman Kerja',0):.0%}");st.text(f"Organisasi: {scores.get('Pengalaman Organisasi',0):.0%}");st.text(f"Hard Skill: {scores.get('Hard Skill',0):.0%}");st.text(f"Soft Skill: {scores.get('Soft Skill',0):.0%}")
                    st.markdown("---"); st.subheader("Tindakan"); btn_cols=st.columns(2);
                    btn_cols[0].button("✅ Terima",key=f"acc_{cid}",on_click=update_candidate_status,args=(cid,"Diterima"),use_container_width=True,type="primary");
                    btn_cols[1].button("❌ Tolak",key=f"rej_{cid}",on_click=update_candidate_status,args=(cid,"Ditolak"),use_container_width=True)
                    with st.expander("Debug: Teks CV"): st.text_area("Teks",value=data.get('text',"N/A"),height=300,key=f"dbg_{cid}")