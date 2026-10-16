import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import os

DATA_FILE = "payroll_data.json"

st.set_page_config(page_title="초당예반 근태 관리", page_icon="🌱", layout="centered")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()
st.title("🌱 초당예반 근태 기록 시스템")

mode = st.sidebar.radio("접속 모드", ["직원 근태 입력", "사장님 관리자 모드 (정산)"])
emp_list = list(data.keys())

if not emp_list and mode != "사장님 관리자 모드 (정산)":
    st.warning("등록된 직원이 없습니다. '사장님 관리자 모드'에서 먼저 직원을 등록해 주세요.")
    st.stop()

# 현재 날짜 기준 기본 정산월 자동 계산 (매월 4일 기준)
now = datetime.now()
if now.day >= 4:
    init_month = now.month + 1
    init_year = now.year
    if init_month > 12:
        init_month = 1
        init_year += 1
else:
    init_month = now.month
    init_year = now.year

years_list = [2026, 2027, 2028]
default_year_idx = years_list.index(init_year) if init_year in years_list else 0
default_month_idx = init_month - 1

# 기록이 없을 때 소정근로일이면 1일 근로시간, 아니면 0.0을 반환하는 헬퍼 함수
def get_hours(recs, ds, c_date, emp_info):
    val = recs.get(ds, "")
    if val != "" and val is not None:
        try:
            return float(val)
        except:
            pass
    work_days = emp_info.get("work_days", [])
    daily_hrs = float(emp_info.get("daily_hours", 5.0))
    if c_date.weekday() in work_days:
        return daily_hrs
    return 0.0

if mode == "직원 근태 입력":
    st.subheader("📝 본인 근무시간 입력")
    if not emp_list:
        st.stop()
    
    if "selected_emp" not in st.session_state or st.session_state["selected_emp"] not in emp_list:
        st.session_state["selected_emp"] = emp_list[0]

    st.write("👉 **본인의 이름을 터치해 주세요:**")
    selected_emp = st.pills(
        "직원 선택",
        options=emp_list,
        default=st.session_state["selected_emp"],
        selection_mode="single",
        label_visibility="collapsed"
    )
    st.session_state["selected_emp"] = selected_emp
    emp_info = data[selected_emp]
    
    st.markdown(f"### ✨ **[{selected_emp}]** 님 환영합니다!")

    col_y, col_m = st.columns(2)
    with col_y:
        target_year = st.selectbox("정산 연도", years_list, index=default_year_idx, key="emp_y")
    with col_m:
        target_month = st.selectbox("정산 월", list(range(1, 13)), index=default_month_idx, key="emp_m")

    start_date = date(target_year - 1, 12, 4) if target_month == 1 else date(target_year, target_month - 1, 4)
    end_date = date(target_year, target_month, 3)
    st.write(f"**기록 기간:** {start_date.strftime('%Y.%m.%d')} - {end_date.strftime('%Y.%m.%d')}")

    if "records" not in emp_info:
        emp_info["records"] = {}

    all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    
    weeks = []
    current_week = []
    for d in all_dates:
        current_week.append(d)
        if d.weekday() == 6 or d == end_date:
            weeks.append(current_week)
            current_week = []

    daily_inputs = {}
    with st.form(f"employee_record_form_{selected_emp}"):
        st.markdown("---")
        st.write("소정근로일이 아닌 날은 기본적으로 빈칸으로 표시되며, 필요시 숫자를 입력할 수 있습니다.")
        
        for w_idx, week in enumerate(weeks):
            w_start_str = week[0].strftime("%m/%d")
            w_end_str = week[-1].strftime("%m/%d")
            st.markdown(f"**📌 {w_idx + 1}주차 ({w_start_str} ~ {w_end_str})**")
            
            for d in week:
                date_str = d.strftime("%Y-%m-%d")
                wd = d.weekday()
                
                if wd == 5:
                    day_color = "#3b82f6"
                    day_name = "토"
                elif wd == 6:
                    day_color = "#ef4444"
                    day_name = "일"
                else:
                    day_color = "inherit"
                    day_name = ["월","화","수","목","금"][wd]
                
                stored_val = emp_info["records"].get(date_str, "")
                is_work_day = wd in emp_info["work_days"]

                if stored_val != "" and stored_val is not None:
                    def_val = float(stored_val)
                elif is_work_day:
                    def_val = float(emp_info["daily_hours"])
                else:
                    def_val = None

                c1, c2 = st.columns([1, 1.8])
                with c1:
                    st.markdown(f"<div style='padding-top: 12px; font-weight: bold; color: {day_color};'>{d.month}/{d.day} ({day_name})</div>", unsafe_allow_html=True)
                with c2:
                    daily_inputs[date_str] = st.number_input(
                        f"시간_{date_str}", 
                        value=def_val, 
                        step=0.5, 
                        format="%.1f", 
                        label_visibility="collapsed", 
                        key=f"mob_d_{selected_emp}_{date_str}"
                    )
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
            
        if st.form_submit_button("💾 내 근무 기록 저장하기", use_container_width=True):
            cleaned_inputs = {}
            work_days_set = set(emp_info.get("work_days", []))
            for k, v in daily_inputs.items():
                d_obj = datetime.strptime(k, "%Y-%m-%d").date()
                is_wd = d_obj.weekday() in work_days_set
                if v is None or (v == 0.0 and not is_wd):
                    cleaned_inputs[k] = ""
                else:
                    cleaned_inputs[k] = float(v)
            
            emp_info["records"].update(cleaned_inputs)
            save_data(data)
            st.success(f"[{selected_emp}] 님의 근무 기록이 안전하게 저장되었습니다!")
            st.rerun()

    tmp_recs = emp_info.get("records", {}).copy()
    for k, v in daily_inputs.items():
        if v is not None:
            tmp_recs[k] = float(v)
    
    t_hrs = 0
    curr = start_date
    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        t_hrs += get_hours(tmp_recs, d_str, curr, emp_info)
        curr += timedelta(days=1)

    st.markdown("---")
    st.markdown("### ⏱️ 이번 달 나의 누적 근무시간")
    st.metric(label="총 근무시간", value=f"{t_hrs:.1f} 시간")

else:
    st.subheader("🔐 사장님 관리자 모드")
    if st.text_input("관리자 비밀번호를 입력하세요", type="password", key="admin_pw") != "1234":
        st.info("관리자 비밀번호를 입력하세요. (기본: 1234)")
        st.stop()
    st.success("관리자 권한 확인됨")

    col_y, col_m = st.columns(2)
    target_year = col_y.selectbox("정산 연도", years_list, index=default_year_idx, key="adm_y")
    target_month = col_m.selectbox("정산 월", list(range(1, 13)), index=default_month_idx, key="adm_m")

    start_date = date(target_year - 1, 12, 4) if target_month == 1 else date(target_year, target_month - 1, 4)
    end_date = date(target_year, target_month, 3)

    st.markdown("---")
    s_str = start_date.strftime("%m/%d")
    e_str = end_date.strftime("%m/%d")
    st.markdown(f"### 💸 전체 직원 급여 지출 예상 ({s_str} - {e_str})")
    
    tot_pay, summary = 0, []
    for e_name, e_dat in data.items():
        recs = e_dat.get("records", {})
        hw = float(e_dat.get('hourly_wage', 10834))
        aj = e_dat.get('apply_juhyu', True)
        dh = float(e_dat.get('daily_hours', 5.0))
        wd = e_dat.get('work_days', [])
        hol = e_dat.get('holiday', 0)
        tax_type = e_dat.get('tax_type', '적용 안 함')
        
        s_hrs, s_j_hrs, wc = 0.0, 0.0, len(wd)
        jpw = (dh * wc / 40) * 8 if (aj and wc > 0) else 0.0

        c_date = start_date
        while c_date <= end_date:
            ds = c_date.strftime("%Y-%m-%d")
            s_hrs += get_hours(recs, ds, c_date, e_dat)
            if aj and c_date.weekday() == hol:
                ws = c_date - timedelta(days=6)
                perf = all(get_hours(recs, (ws + timedelta(days=i)).strftime("%Y-%m-%d"), ws + timedelta(days=i), e_dat) != 0 for i in range(7) if start_date <= ws + timedelta(days=i) <= end_date and (ws + timedelta(days=i)).weekday() in wd)
                if perf and wc > 0:
                    s_j_hrs += jpw
            c_date += timedelta(days=1)

        epay = (s_hrs + s_j_hrs) * hw
        tot_pay += epay
        summary.append({"직원명": e_name, "총근무시간": f"{s_hrs:.1f} 시간", "주휴시간": f"{s_j_hrs:.1f} 시간", "예상급여(세전)": f"{epay:,.0f} 원"})

    st.metric(label="🚨 이번 달 총 예상 인건비 지출 합계 (세전)", value=f"{tot_pay:,.0f} 원")
    if summary:
        st.table(pd.DataFrame(summary))

    st.markdown("---")
    st.subheader("🔍 직원별 상세 정산 및 급여명세서")
    selected_emp = st.selectbox("상세 조회할 직원 선택", emp_list, key="admin_emp_target")
    emp_info = data[selected_emp]
    hw = float(emp_info.get('hourly_wage', 10834))
    aj = emp_info.get('apply_juhyu', True)
    tax_type = emp_info.get('tax_type', '적용 안 함')

    recs = emp_info.get("records", {})
    tot_h, tot_jh = 0.0, 0.0
    dh = float(emp_info.get('daily_hours', 5.0))
    wd_cnt = len(emp_info.get('work_days', []))
    jpw_emp = (dh * wd_cnt / 40) * 8 if (aj and wd_cnt > 0) else 0.0

    curr = start_date
    while curr <= end_date:
        ds = curr.strftime("%Y-%m-%d")
        tot_h += get_hours(recs, ds, curr, emp_info)
        if aj and curr.weekday() == emp_info["holiday"]:
            ws = curr - timedelta(days=6)
            perf = all(get_hours(recs, (ws + timedelta(days=i)).strftime("%Y-%m-%d"), ws + timedelta(days=i), emp_info) != 0 for i in range(7) if start_date <= ws + timedelta(days=i) <= end_date and (ws + timedelta(days=i)).weekday() in emp_info["work_days"])
            if perf and wd_cnt > 0:
                tot_jh += jpw_emp
        curr += timedelta(days=1)

    tot_base_pay = tot_h * hw
    tot_juhyu_pay = tot_jh * hw
    gross_pay = tot_base_pay + tot_juhyu_pay

    # 공제 내역 계산 (10원 단위 절사)
    deduct_tot, d_inc, d_loc, d_pen, d_hlth, d_care, d_emp = 0, 0, 0, 0, 0, 0, 0
    if tax_type == "3.3% (사업소득)":
        d_inc = int(gross_pay * 0.03) // 10 * 10
        d_loc = int(gross_pay * 0.003) // 10 * 10
        deduct_tot = d_inc + d_loc
    elif tax_type == "4대보험 (근로소득)":
        d_pen = int(gross_pay * 0.045) // 10 * 10
        d_hlth = int(gross_pay * 0.03545) // 10 * 10
        d_care = int(d_hlth * 0.1295) // 10 * 10
        d_emp = int(gross_pay * 0.009) // 10 * 10
        deduct_tot = d_pen + d_hlth + d_care + d_emp

    net_pay = gross_pay - deduct_tot

    # 주차별 일급 및 주휴수당 발생 여부 계산
    all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    weeks = []
    current_week = []
    for d in all_dates:
        current_week.append(d)
        if d.weekday() == 6 or d == end_date:
            weeks.append(current_week)
            current_week = []

    weekly_data = []
    for w_idx, week in enumerate(weeks):
        w_hrs = 0.0
        for d in week:
            ds = d.strftime("%Y-%m-%d")
            w_hrs += get_hours(recs, ds, d, emp_info)
        
        w_pay = w_hrs * hw
        
        # 주휴수당 발생 여부 체크
        w_juhyu_issued = False
        if aj and wd_cnt > 0:
            for d in week:
                if d.weekday() == emp_info["holiday"]:
                    ws = d - timedelta(days=6)
                    perf = all(get_hours(recs, (ws + timedelta(days=i)).strftime("%Y-%m-%d"), ws + timedelta(days=i), emp_info) != 0 for i in range(7) if start_date <= ws + timedelta(days=i) <= end_date and (ws + timedelta(days=i)).weekday() in emp_info["work_days"])
                    if perf:
                        w_juhyu_issued = True
                    break
        
        w_start_str = week[0].strftime("%m/%d")
        w_end_str = week[-1].strftime("%m/%d")
        weekly_data.append({
            "주차": f"{w_idx + 1}주차 ({w_start_str}~{w_end_str})",
            "주간 일급": f"{w_pay:,.0f}원",
            "주휴수당": "발생" if w_juhyu_issued else "미발생"
        })

    st.markdown("### 📊 주차별 급여 현황")
    st.table(pd.DataFrame(weekly_data))

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🧾 급여명세서 (캡처용)")
    with st.container(border=True):
        st.markdown(f"<h3 style='text-align: center; margin-bottom: 0px;'>{target_year}년 {target_month}월 급여명세서</h3>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; color: gray; margin-bottom: 20px;'>지급대상기간: {start_date.strftime('%Y.%m.%d')} ~ {end_date.strftime('%Y.%m.%d')}</div>", unsafe_allow_html=True)
        st.markdown(f"**성명:** {selected_emp} &nbsp;&nbsp;|&nbsp;&nbsp; **시급:** {hw:,.0f}원")
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔵 지급 내역")
            st.write(f"- 기본급: {tot_base_pay:,.0f} 원")
            st.write(f"- 주휴수당: {tot_juhyu_pay:,.0f} 원")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"**지급 총액: {gross_pay:,.0f} 원**")
        
        with c2:
            st.markdown("#### 🔴 공제 내역")
            if tax_type == "3.3% (사업소득)":
                st.write(f"- 소득세 (3%): {d_inc:,.0f} 원")
                st.write(f"- 지방소득세 (0.3%): {d_loc:,.0f} 원")
            elif tax_type == "4대보험 (근로소득)":
                st.write(f"- 국민연금: {d_pen:,.0f} 원")
                st.write(f"- 건강보험: {d_hlth:,.0f} 원")
                st.write(f"- 장기요양보험: {d_care:,.0f} 원")
                st.write(f"- 고용보험: {d_emp:,.0f} 원")
            else:
                st.write("- 공제 항목 없음")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"**공제 총액: {deduct_tot:,.0f} 원**")

        st.divider()
        st.markdown(f"<h3 style='text-align: right; color: #3b82f6;'>💰 차인지급액 (실지급액): {net_pay:,.0f} 원</h3>", unsafe_allow_html=True)

    # 사장님 사이드바: 직원 관리 및 수정
    st.sidebar.header("👥 직원 관리 및 수정")
    act_type = st.sidebar.selectbox("작업 선택", ["기존 직원 정보 수정", "신규 직원 등록"], key="admin_action")
    
    tax_options = ["적용 안 함", "3.3% (사업소득)", "4대보험 (근로소득)"]

    if act_type == "기존 직원 정보 수정":
        if emp_list:
            edit_target_emp = st.sidebar.selectbox("수정할 직원 선택", emp_list, key="sidebar_edit_emp")
            
            if st.session_state.get("last_selected_emp") != edit_target_emp:
                st.session_state["last_selected_emp"] = edit_target_emp
                curr_data = data[edit_target_emp]
                st.session_state["edit_w_input"] = int(curr_data.get("hourly_wage", 10834))
                st.session_state["edit_h_input"] = float(curr_data.get("daily_hours", 5.0))
                st.session_state["edit_hol_input"] = int(curr_data.get("holiday", 0))
                st.session_state["edit_aj_input"] = bool(curr_data.get("apply_juhyu", True))
                st.session_state["edit_tax_input"] = curr_data.get("tax_type", "적용 안 함")
                saved_wd = curr_data.get("work_days", [])
                for i in range(7):
                    st.session_state[f"wd_chk_{i}"] = i in saved_wd
                st.rerun()
            else:
                curr_data = data[edit_target_emp]
        else:
            st.sidebar.warning("등록된 직원이 없습니다.")
            edit_target_emp = None
            curr_data = {}
    else:
        edit_target_emp = None
        if st.session_state.get("last_act_type") != act_type:
            st.session_state["last_act_type"] = act_type
            st.session_state["last_selected_emp"] = None
            st.session_state["edit_w_input"] = 10834
            st.session_state["edit_h_input"] = 5.0
            st.session_state["edit_hol_input"] = 0
            st.session_state["edit_aj_input"] = True
            st.session_state["edit_tax_input"] = "적용 안 함"
            for i in range(7):
                st.session_state[f"wd_chk_{i}"] = i in [1, 2, 3, 4]
            st.rerun()
        curr_data = {}

    if act_type == "신규 직원 등록":
        st.sidebar.write("### ➕ 신규 직원 등록")
        e_name_input = st.sidebar.text_input("이름", key="new_name_input")
    else:
        st.sidebar.write(f"### ✏️ [{edit_target_emp}] 정보 수정")
        e_name_input = edit_target_emp

    hw_in = st.sidebar.number_input("기본 시급 (원)", step=10, key="edit_w_input")
    dh_in = st.sidebar.number_input("1일 소정근로시간", step=0.5, key="edit_h_input")
    
    st.sidebar.write("소정근로일 선택")
    wd_in = []
    wd_cols = st.sidebar.columns(7)
    days_lbl = ["월","화","수","목","금","토","일"]
    for i, d in enumerate(days_lbl):
        with wd_cols[i]:
            if st.sidebar.checkbox(d, key=f"wd_chk_{i}"):
                wd_in.append(i)
                
    hol_in = st.sidebar.selectbox("주휴일 선택", options=range(7), format_func=lambda x: days_lbl[x], key="edit_hol_input")
    aj_in = st.sidebar.checkbox("주휴수당 지급 대상 (주 15시간 이상)", key="edit_aj_input")
    
    st.sidebar.markdown("---")
    tax_in = st.sidebar.selectbox("세금 및 보험 공제 설정", tax_options, key="edit_tax_input")
    
    if st.sidebar.button("💾 저장 및 반영하기", use_container_width=True):
        t_name = e_name_input.strip()
        if not t_name:
            st.sidebar.error("이름을 입력해주세요.")
        else:
            existing_recs = data.get(t_name, {}).get("records", {})
            data[t_name] = {
                "hourly_wage": hw_in, 
                "daily_hours": dh_in, 
                "work_days": wd_in, 
                "holiday": hol_in, 
                "apply_juhyu": aj_in,
                "tax_type": tax_in,
                "records": existing_recs
            }
            save_data(data)
            st.sidebar.success(f"[{t_name}] 정보가 저장되었습니다!")
            st.rerun()