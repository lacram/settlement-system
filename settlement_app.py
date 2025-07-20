import streamlit as st
from datetime import datetime
import json
import sqlite3
import os
import uuid

# DB 초기화
def init_db():
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    
    # 거래 내역 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY, date TEXT, description TEXT, 
                  amount REAL, members TEXT, member_amounts TEXT, 
                  created_at TEXT, updated_at TEXT)''')
    
    # 정산 결과 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS settlements
                 (id INTEGER PRIMARY KEY, name TEXT, date TEXT, 
                  total_amount REAL, member_count INTEGER, 
                  settlement_data TEXT, created_at TEXT)''')
    
    # image_path 컬럼이 없으면 추가
    try:
        c.execute("ALTER TABLE settlements ADD COLUMN image_path TEXT")
    except sqlite3.OperationalError:
        pass  # 이미 컬럼이 있으면 무시
    
    conn.commit()
    conn.close()

# DB에서 거래 내역 로드
def load_transactions_from_db():
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    c.execute('SELECT * FROM transactions ORDER BY date DESC')
    rows = c.fetchall()
    conn.close()
    
    transactions = []
    for row in rows:
        transaction = {
            'id': row[0],
            'date': row[1],
            'description': row[2],
            'amount': row[3],
            'members': json.loads(row[4]),
            'member_amounts': json.loads(row[5]),
            'created_at': row[6],
            'updated_at': row[7] if row[7] else None
        }
        transactions.append(transaction)
    
    return transactions

# DB에 거래 저장
def save_transaction_to_db(transaction):
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO transactions 
                 (date, description, amount, members, member_amounts, created_at)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (transaction['date'], transaction['description'], transaction['amount'],
               json.dumps(transaction['members']), json.dumps(transaction['member_amounts']),
               transaction['created_at']))
    
    conn.commit()
    conn.close()

# DB에 거래 업데이트
def update_transaction_in_db(transaction):
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    
    c.execute('''UPDATE transactions 
                 SET date=?, description=?, amount=?, members=?, member_amounts=?, updated_at=?
                 WHERE id=?''',
              (transaction['date'], transaction['description'], transaction['amount'],
               json.dumps(transaction['members']), json.dumps(transaction['member_amounts']),
               transaction['updated_at'], transaction['id']))
    
    conn.commit()
    conn.close()

# DB에서 거래 삭제
def delete_transaction_from_db(transaction_id):
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    c.execute('DELETE FROM transactions WHERE id=?', (transaction_id,))
    conn.commit()
    conn.close()

# DB에 정산 결과 저장 (사진 경로 추가)
def save_settlement_to_db(name, date, total_amount, member_count, settlement_data, image_path=None):
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    c.execute('''INSERT INTO settlements 
                 (name, date, total_amount, member_count, settlement_data, created_at, image_path)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (name, date, total_amount, member_count, json.dumps(settlement_data), datetime.now().isoformat(), image_path))
    conn.commit()
    conn.close()

# DB에서 정산 결과 로드 (사진 경로 포함)
def load_settlements_from_db():
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    # image_path 컬럼 추가
    c.execute('SELECT id, name, date, total_amount, member_count, settlement_data, created_at, image_path FROM settlements ORDER BY date DESC')
    rows = c.fetchall()
    conn.close()
    settlements = []
    for row in rows:
        settlement = {
            'id': row[0],
            'name': row[1],
            'date': row[2],
            'total_amount': row[3],
            'member_count': row[4],
            'settlement_data': json.loads(row[5]),
            'created_at': row[6],
            'image_path': row[7]
        }
        settlements.append(settlement)
    return settlements

# DB에서 정산 결과 삭제
def delete_settlement_from_db(settlement_id):
    conn = sqlite3.connect('settlement.db')
    c = conn.cursor()
    c.execute('DELETE FROM settlements WHERE id=?', (settlement_id,))
    conn.commit()
    conn.close()

# 세션 상태 초기화
if 'transactions' not in st.session_state:
    st.session_state.transactions = []
if 'members' not in st.session_state:
    st.session_state.members = []
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now().strftime('%Y-%m-%d')
if 'editing_transaction' not in st.session_state:
    st.session_state.editing_transaction = None

# DB 초기화
init_db()

def calculate_settlement():
    """전체 정산 계산 - 저장된 거래 내역 기반"""
    if not st.session_state.transactions:
        return {}
    
    # 모든 거래에서 참여된 멤버들을 수집
    all_members = set()
    for transaction in st.session_state.transactions:
        all_members.update(transaction['members'])
    
    # 각 멤버별 정산 금액(=총 지출) 계산
    member_totals = {member: 0 for member in all_members}
    for transaction in st.session_state.transactions:
        for i, member in enumerate(transaction['members']):
            member_amount = transaction['member_amounts'][i]
            member_totals[member] += member_amount
    
    # 각 멤버별 정산 금액(=총 지출)으로 반환
    settlement_result = {}
    for member in all_members:
        settlement_result[member] = {
            'settlement_amount': member_totals[member],
            'transactions': []
        }
    
    # 각 거래별 상세 내역 추가
    for transaction in st.session_state.transactions:
        for i, member in enumerate(transaction['members']):
            if member in settlement_result:
                settlement_result[member]['transactions'].append({
                    'date': transaction['date'],
                    'description': transaction['description'],
                    'amount': transaction['member_amounts'][i],
                    'total_amount': transaction['amount']
                })
    
    return settlement_result

def load_transaction_for_edit(transaction):
    """거래를 수정 모드로 로드"""
    st.session_state.editing_transaction = transaction
    st.session_state.members = transaction['members'].copy()
    st.rerun()

def on_enter():
    if st.session_state.member_input:  # 입력값이 있을 때
        new_member = st.session_state.member_input.strip()
        if new_member and new_member not in st.session_state.members:
            st.session_state.members.append(new_member)
            # 참여자 추가 시 입력창 초기화
            st.session_state.member_input = ""

def clear_inputs():
    st.session_state.should_clear_inputs = True
    st.session_state.editing_transaction = None
    st.rerun()

def main():
    st.set_page_config(page_title="정산 시스템", layout="wide")
    
    # DB에서 거래 내역 로드
    if not st.session_state.transactions:
        st.session_state.transactions = load_transactions_from_db()
    
    # 입력 필드 초기화 플래그 확인
    if st.session_state.get('should_clear_inputs', False):
        st.session_state.should_clear_inputs = False
        st.rerun()
    
    # 정산 입력 필드 초기화 플래그 확인
    if st.session_state.get('should_clear_settlement_inputs', False):
        st.session_state.should_clear_settlement_inputs = False
        # 정산 입력 필드들을 초기화
        if 'settlement_name' in st.session_state:
            del st.session_state.settlement_name
        st.rerun()
    
    # 거래 내역 초기화 플래그 확인
    if st.session_state.get('should_clear_transactions', False):
        st.session_state.should_clear_transactions = False
        # 거래 내역 초기화
        st.session_state.transactions = []
        # DB에서 거래 내역 삭제
        conn = sqlite3.connect('settlement.db')
        c = conn.cursor()
        c.execute('DELETE FROM transactions')
        conn.commit()
        conn.close()
        st.rerun()
    
    # CSS 스타일 추가 - 모바일 호환성 개선
    st.markdown("""
    <style>
    /* 전체 레이아웃 */
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 1.5rem;
        font-size: 1.8rem;
        font-weight: bold;
    }
    
    /* 메트릭 카드 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        text-align: center;
    }
    .metric-card h4 {
        margin: 0 0 0.5rem 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .metric-card h2 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: bold;
    }
    
    /* 멤버 카드 */
    .member-card {
        background: white;
        padding: 0.8rem;
        border-radius: 8px;
        border: 1px solid #e1e5e9;
        margin: 0.3rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    .member-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    
    /* 정산 카드 */
    .settlement-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* 상태 텍스트 */
    .success-text {
        color: #28a745;
        font-weight: bold;
        padding: 0.5rem;
        background: rgba(40, 167, 69, 0.1);
        border-radius: 6px;
        border-left: 4px solid #28a745;
    }
    .error-text {
        color: #dc3545;
        font-weight: bold;
        padding: 0.5rem;
        background: rgba(220, 53, 69, 0.1);
        border-radius: 6px;
        border-left: 4px solid #dc3545;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        min-height: 44px;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* 입력 필드 스타일 */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e1e5e9;
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 숫자 입력 필드 */
    .stNumberInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e1e5e9;
        transition: all 0.2s ease;
    }
    .stNumberInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 탭 스타일 */
    .stTabs > div > div > div > div {
        border-radius: 8px 8px 0 0;
    }
    
    /* 확장 패널 스타일 */
    .streamlit-expanderHeader {
        border-radius: 8px;
        background: #f8f9fa;
        border: 1px solid #e1e5e9;
    }
    
    /* 모바일 최적화 */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }
        .metric-card {
            padding: 1rem;
            margin: 0.3rem 0;
        }
        .metric-card h2 {
            font-size: 1.3rem;
        }
        .member-card {
            padding: 0.6rem;
        }
        .stButton > button {
            min-height: 48px;
            font-size: 1rem;
        }
    }
    
    /* 다크 모드 지원 */
    @media (prefers-color-scheme: dark) {
        .member-card {
            background: #2d3748;
            border-color: #4a5568;
            color: white;
        }
        .streamlit-expanderHeader {
            background: #2d3748;
            border-color: #4a5568;
            color: white;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">💰 정산 시스템</h1>', unsafe_allow_html=True)
    
    # 탭 생성 (active_tab 세션 상태로 제어)
    tab_labels = ["📝 거래 입력", "🧮 정산 결과", "📚 정산 기록"]
    active_tab_idx = st.session_state.get('active_tab_idx', 0)
    tabs = st.tabs(tab_labels)

    # 탭 인덱스 매핑
    TAB_INPUT, TAB_RESULT, TAB_HISTORY = 0, 1, 2

    # 탭 전환 함수
    def switch_to_tab(tab_idx):
        st.session_state['active_tab_idx'] = tab_idx
        st.rerun()
    
    # 각 탭 내용은 tabs[0], tabs[1], tabs[2] with 블록으로 분기
    with tabs[TAB_INPUT]:
        st.header("거래 내역 입력")
        
        # 수정 모드 표시
        if st.session_state.editing_transaction:
            st.info(f"📝 수정 모드: {st.session_state.editing_transaction['description']}")
            if st.button("❌ 수정 취소"):
                clear_inputs()
                st.rerun()
        
        # 거래 정보 입력 - 모바일 친화적 레이아웃
        st.subheader("📝 거래 정보")
        
        # 수정 모드일 때 기존 값 로드
        default_description = st.session_state.editing_transaction['description'] if st.session_state.editing_transaction else ""
        default_amount = st.session_state.editing_transaction['amount'] if st.session_state.editing_transaction else 0
        default_date = datetime.strptime(st.session_state.editing_transaction['date'], '%Y-%m-%d') if st.session_state.editing_transaction else datetime.now()
        
        # 거래 날짜, 설명, 금액 순으로 세로 배치
        date = st.date_input("거래 날짜", value=default_date, key="date_input")
        st.session_state.current_date = date.strftime('%Y-%m-%d')
        description = st.text_input("거래 설명", value=default_description, placeholder="예: 점심 식사", key="description_input")
        amount = st.number_input("총 금액", value=float(default_amount), min_value=0.0, step=1.0, placeholder="금액을 입력하세요", key="amount_input")
        
        # 참여자 입력 - 모바일 친화적 UI
        st.subheader("👥 참여자 추가")
        
        # 모바일에서는 세로로 배치
        new_member = st.text_input("참여자 이름", placeholder="참여자 이름을 입력하고 엔터를 누르세요", key="member_input", on_change=on_enter)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("➕ 참여자 추가", type="primary", key="add_member_btn", use_container_width=True):
                if new_member.strip() and new_member.strip() not in st.session_state.members:
                    st.session_state.members.append(new_member.strip())
                    # 참여자 추가 시 입력창 초기화
                    st.session_state.member_input = ""
                    st.rerun()
        with col2:
            if st.button("🗑️ 전체 삭제", key="clear_members_btn", use_container_width=True):
                st.session_state.members = []
                st.rerun()
        
        # 현재 참여자 목록 표시 - 깔끔한 UI
        if st.session_state.members:
            st.subheader("📋 현재 참여자 목록")
            
            # 참여자별 금액 계산
            if amount > 0 and st.session_state.members:
                amount_per_person = amount / len(st.session_state.members)
                
                # 메트릭 카드
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f'<div class="metric-card"><h4>총 금액</h4><h2>{int(amount):,}원</h2></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-card"><h4>참여자 수</h4><h2>{len(st.session_state.members)}명</h2></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-card"><h4>1인당 금액</h4><h2>{int(amount_per_person):,}원</h2></div>', unsafe_allow_html=True)
                
                # 참여자별 금액 표시 및 수정 - 한 줄(row)에 이름, 금액 입력, 합계, 삭제 버튼이 모두 같은 높이로 정렬
                st.write("**참여자별 금액:**")
                total_modified = 0
                modified_amounts = []
                delete_index = None
                
                for i, member in enumerate(st.session_state.members):
                    cols = st.columns([3, 2, 2, 1])
                    with cols[0]:
                        st.markdown(f'<div style="display: flex; align-items: center; height: 44px;"><span style="font-size:1.1em;">👤 {member}</span></div>', unsafe_allow_html=True)
                    with cols[1]:
                        default_amount_per_person = st.session_state.editing_transaction['member_amounts'][i] if st.session_state.editing_transaction and i < len(st.session_state.editing_transaction['member_amounts']) else amount_per_person
                        modified_amount = st.number_input(
                            f"금액_{i}_{member}",
                            value=float(default_amount_per_person),
                            key=f"amount_{i}_{member}",
                            label_visibility="collapsed"
                        )
                        modified_amounts.append(modified_amount)
                    with cols[2]:
                        st.markdown(f'<div style="display: flex; align-items: center; height: 44px; font-weight: bold; text-align: right;">{int(modified_amount):,}원</div>', unsafe_allow_html=True)
                    with cols[3]:
                        if st.button("🗑️", key=f"delete_{i}_{member}", use_container_width=True):
                            delete_index = i
                # 루프가 끝난 뒤 실제 삭제 수행
                if delete_index is not None:
                    st.session_state.members = [m for j, m in enumerate(st.session_state.members) if j != delete_index]
                    st.rerun()
                total_modified = sum(modified_amounts)
                
                # 최종 금액 비교 - 개선된 표시
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**최종 입력 금액**: {int(total_modified):,}원")
                with col2:
                    st.write(f"**총 금액**: {int(amount):,}원")
                
                if abs(total_modified - amount) > 1:  # 1원 오차 허용
                    st.markdown(f'<p class="error-text">⚠️ 금액 불일치: {abs(total_modified - amount):,}원 차이</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<p class="success-text">✅ 금액 일치</p>', unsafe_allow_html=True)
                
                # 참여자 삭제 기능 - 모바일 친화적 UI
                # (참여자 관리 섹션 완전히 제거)
        
        # 거래 저장 - 모바일 친화적 버튼
        st.markdown("---")
        save_button_text = "💾 거래 수정" if st.session_state.editing_transaction else "💾 거래 저장"
        if st.button(save_button_text, type="primary", disabled=not (description and amount > 0 and st.session_state.members), use_container_width=True):
            if description and amount > 0 and st.session_state.members:
                # 수정된 금액들 수집
                modified_amounts = []
                for i in range(len(st.session_state.members)):
                    modified_amount = st.session_state.get(f"amount_{i}", amount / len(st.session_state.members))
                    modified_amounts.append(modified_amount)
                
                # 총 금액이 맞는지 확인
                total_modified = sum(modified_amounts)
                if abs(total_modified - amount) > 1:  # 1원 오차 허용
                    st.error(f"참여자별 금액의 합({int(total_modified):,}원)이 총 금액({int(amount):,}원)과 일치하지 않습니다!")
                else:
                    if st.session_state.editing_transaction:
                        # 수정 모드
                        transaction = st.session_state.editing_transaction
                        transaction.update({
                            'date': st.session_state.current_date,
                            'description': description,
                            'amount': amount,
                            'members': st.session_state.members.copy(),
                            'member_amounts': modified_amounts,
                            'updated_at': datetime.now().isoformat()
                        })
                        update_transaction_in_db(transaction)
                        st.success("거래가 수정되었습니다!")
                        clear_inputs()
                        st.rerun()
                    else:
                        # 새 거래 추가
                        transaction = {
                            'id': len(st.session_state.transactions) + 1,
                            'date': st.session_state.current_date,
                            'description': description,
                            'amount': amount,
                            'members': st.session_state.members.copy(),
                            'member_amounts': modified_amounts,
                            'created_at': datetime.now().isoformat()
                        }
                        save_transaction_to_db(transaction)
                        st.session_state.transactions.append(transaction)
                        st.success("거래가 저장되었습니다!")
                        # 입력 필드 초기화 플래그 설정
                        clear_inputs()
                        st.rerun()
            else:
                st.error("거래 설명, 금액, 참여자를 모두 입력해주세요!")
        
        # 저장된 거래 내역 표시 - 깔끔한 UI
        if st.session_state.transactions:
            st.subheader("📋 저장된 거래 내역")
            
            for transaction in st.session_state.transactions:
                with st.expander(f"{transaction['date']} - {transaction['description']} ({int(transaction['amount']):,}원)"):
                    st.write(f"**참여자**: {', '.join(transaction['members'])}")
                    st.write("**참여자별 금액:**")
                    for member, amount in zip(transaction['members'], transaction['member_amounts']):
                        st.write(f"- {member}: {int(amount):,}원")
                    
                    # 버튼들 - 모바일 친화적
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✏️ 수정", key=f"edit_transaction_{transaction['id']}", use_container_width=True):
                            load_transaction_for_edit(transaction)
                    with col2:
                        if st.button(f"🗑️ 삭제", key=f"delete_transaction_{transaction['id']}", use_container_width=True):
                            delete_transaction_from_db(transaction['id'])
                            st.session_state.transactions = [t for t in st.session_state.transactions if t['id'] != transaction['id']]
                            st.rerun()
    
    with tabs[TAB_RESULT]:
        st.header("정산 결과")
        
        if not st.session_state.transactions:
            st.info("📝 거래 내역을 먼저 입력해주세요!")
        else:
            settlement = calculate_settlement()
            
            if settlement:
                # 전체 요약 - 깔끔한 메트릭
                st.subheader("📊 전체 정산 요약")
                
                total_spent = sum(data['settlement_amount'] for data in settlement.values())
                
                # 정산 요약 카드 UI 개선
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'''<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem 1.5rem; border-radius: 18px; box-shadow: 0 6px 24px rgba(102,126,234,0.15); margin: 1rem 0; text-align: center;">
                        <h4 style="margin:0 0 0.7rem 0; font-size:1.1em; opacity:0.9;">총 거래 금액</h4>
                        <h2 style="margin:0; font-size:2.1em; font-weight:bold;">{int(total_spent):,}원</h2>
                    </div>''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''<div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 2rem 1.5rem; border-radius: 18px; box-shadow: 0 6px 24px rgba(240,147,251,0.12); margin: 1rem 0; text-align: center;">
                        <h4 style="margin:0 0 0.7rem 0; font-size:1.1em; opacity:0.9;">참여자 수</h4>
                        <h2 style="margin:0; font-size:2.1em; font-weight:bold;">{len(settlement)}명</h2>
                    </div>''', unsafe_allow_html=True)
                
                # 정산 결과 저장 UI (날짜, 이름, 사진 첨부 순)
                st.markdown("---")
                st.subheader("💾 정산 결과 저장")
                settlement_date = st.date_input("정산 날짜", value=datetime.now(), key="settlement_date")
                settlement_name = st.text_input("정산 이름", placeholder="예: 2024년 1월 정산", key="settlement_name")
                # 사진 첨부 (여러 장)
                settlement_images = st.file_uploader("정산 관련 사진 첨부 (여러 장 가능)", type=["png", "jpg", "jpeg"], key="settlement_image", accept_multiple_files=True)

                image_paths = []
                if settlement_images:
                    for img in settlement_images:
                        ext = os.path.splitext(img.name)[-1]
                        img_path = f"settlement_{settlement_name}_{settlement_date.strftime('%Y%m%d')}_{uuid.uuid4().hex}{ext}"
                        with open(img_path, "wb") as f:
                            f.write(img.read())
                        image_paths.append(img_path)
                image_paths_str = ",".join(image_paths) if image_paths else None

                # 정산 결과 저장 버튼 클릭 시 기록 탭으로 이동
                if st.button("💾 정산 결과 저장", type="primary", disabled=not settlement_name, use_container_width=True):
                    if settlement_name:
                        save_settlement_to_db(
                            settlement_name,
                            settlement_date.strftime('%Y-%m-%d'),
                            float(total_spent),
                            len(settlement),
                            settlement,
                            image_paths_str
                        )
                        st.success(f"정산 결과가 저장되었습니다: {settlement_name}")
                        st.session_state.should_clear_settlement_inputs = True
                        st.session_state.should_clear_transactions = True
                        st.session_state['active_tab_idx'] = TAB_HISTORY  # 기록 탭으로 이동
                        st.rerun()
                
                # 참여자별 상세 정산 - 모바일 친화적 카드
                st.subheader("👥 참여자별 정산 내역")
                
                for member, data in settlement.items():
                    # 정산 금액에 따른 색상 결정
                    sign = "+" if data['settlement_amount'] >= 0 else ""
                    color = "#28a745" if data['settlement_amount'] >= 0 else "#dc3545"
                    status_icon = "💰" if data['settlement_amount'] >= 0 else "💸"
                    status_text = "받을 금액" if data['settlement_amount'] >= 0 else "낼 금액"
                    
                    with st.expander(f"{status_icon} **{member}** - 총 지출: {int(data['settlement_amount']):,}원"):
                        # 모바일에서는 세로로 배치
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
                            <h4 style="margin: 0 0 0.5rem 0;">정산 요약</h4>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>총 지출:</span>
                                <span><strong>{int(data['settlement_amount']):,}원</strong></span>
                            </div>
                            <div style="display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 0.5rem;">
                                <span>정산 금액:</span>
                                <span style="color: {color}; font-weight: bold; font-size: 1.1em;">{sign}{int(data['settlement_amount']):,}원</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 상세 거래 내역
                        if data['transactions']:
                            st.write("**📋 상세 거래 내역:**")
                            for trans in data['transactions']:
                                st.markdown(f"""
                                <div style="background: white; padding: 0.8rem; border-radius: 8px; border-left: 4px solid #667eea; margin: 0.3rem 0;">
                                    <div style="font-weight: bold; color: #333;">{trans['description']}</div>
                                    <div style="color: #666; font-size: 0.9em;">{trans['date']}</div>
                                    <div style="color: #667eea; font-weight: bold; margin-top: 0.3rem;">{int(trans['amount']):,}원</div>
                                </div>
                                """, unsafe_allow_html=True)
                
                # 정산 요약 카드 UI (평균 금액 완전 제거, 카드 스타일 개선)
                st.subheader("📋 정산 요약")
                summary_data = []
                for member, data in settlement.items():
                    summary_data.append({
                        "참여자": member,
                        "총 지출": f"{int(data['settlement_amount']):,}원"
                    })
                if summary_data:
                    cols = st.columns(min(4, len(summary_data)))
                    for idx, row in enumerate(summary_data):
                        with cols[idx % len(cols)]:
                            st.markdown(f'''
                            <div style="background: linear-gradient(135deg, #f0f2f6 0%, #d9e7fa 100%); padding: 1.3rem 1.1rem; border-radius: 16px; box-shadow: 0 4px 16px rgba(102,126,234,0.10); margin: 0.8rem 0; text-align: center; transition: box-shadow 0.2s;">
                                <div style="font-size:1.15em; font-weight:600; color:#1f77b4; margin-bottom:0.6rem; letter-spacing:0.5px;">👤 {row['참여자']}</div>
                                <div style="font-size:1.7em; font-weight:bold; color:#222; letter-spacing:1px;">{row['총 지출']}</div>
                            </div>
                            ''', unsafe_allow_html=True)
    
    with tabs[TAB_HISTORY]:
        st.header("📚 정산 기록")
        
        settlements = load_settlements_from_db()
        
        if not settlements:
            st.info("📝 저장된 정산 기록이 없습니다.")
        else:
            st.subheader("📋 저장된 정산 목록")
            
            for settlement in settlements:
                with st.expander(f"📅 {settlement['date']} - {settlement['name']} ({int(settlement['total_amount']):,}원)"):
                    # 이미지가 있으면 표시
                    if settlement.get('image_path') and os.path.exists(settlement['image_path']):
                        st.image(settlement['image_path'], caption="첨부된 사진", use_container_width=True)
                    # 삭제 확인 버튼 추가
                    delete_key = f"delete_settlement_{settlement['id']}"
                    confirm_key = f"confirm_delete_settlement_{settlement['id']}"
                    
                    # 삭제 확인 상태 확인
                    if st.session_state.get(confirm_key, False):
                        st.warning(f"⚠️ 정말 '{settlement['name']}' 정산 기록을 삭제하시겠습니까?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ 확인", key=f"confirm_{settlement['id']}", use_container_width=True):
                                delete_settlement_from_db(settlement['id'])
                                st.success(f"정산 기록이 삭제되었습니다: {settlement['name']}")
                                # 확인 상태 초기화
                                st.session_state[confirm_key] = False
                                st.rerun()
                        with col2:
                            if st.button("❌ 취소", key=f"cancel_{settlement['id']}", use_container_width=True):
                                # 확인 상태 초기화
                                st.session_state[confirm_key] = False
                                st.rerun()
                    else:
                        if st.button(f"🗑️ 삭제", key=delete_key, use_container_width=True):
                            # 삭제 확인 상태 활성화
                            st.session_state[confirm_key] = True
                            st.rerun()
                    
                    # 정산 요약 정보
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f'<div class="metric-card"><h4>총 금액</h4><h2>{int(settlement["total_amount"]):,}원</h2></div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="metric-card"><h4>참여자 수</h4><h2>{settlement["member_count"]}명</h2></div>', unsafe_allow_html=True)
                    
                    # 참여자별 정산 내역
                    st.subheader("👥 참여자별 정산")
                    
                    for member, data in settlement['settlement_data'].items():
                        st.markdown(f"""
                        <div style="background: white; padding: 1rem; border-radius: 8px; border-left: 4px solid #e1e5e9; margin: 0.5rem 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h4 style="margin: 0;">{member}</h4>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 1.2em; font-weight: bold; color: #1f77b4;">
                                        정산 금액: {int(data['settlement_amount']):,}원
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        # 상세 거래 내역
                        if data['transactions']:
                            st.write("**📋 상세 거래 내역:**")
                            for trans in data['transactions']:
                                st.markdown(f"""
                                <div style="background: #f8f9fa; padding: 0.6rem; border-radius: 6px; margin: 0.2rem 0;">
                                    <div style="font-weight: bold; color: #333;">{trans['description']}</div>
                                    <div style="color: #666; font-size: 0.9em;">{trans['date']}</div>
                                    <div style="color: #667eea; font-weight: bold; margin-top: 0.2rem;">{int(trans['amount']):,}원</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                    # 정산 기록에서 expander를 펼쳤을 때만, 맨 하단에 첨부된 사진을 한 행에 3개씩 썸네일 그리드로 표시
                    image_paths = []
                    if settlement.get('image_path'):
                        # 여러 장 지원: 콤마로 구분된 경로 저장 시 분리
                        if ',' in str(settlement['image_path']):
                            image_paths = [p.strip() for p in settlement['image_path'].split(',') if p.strip()]
                        else:
                            image_paths = [settlement['image_path']]
                        # 실제 파일이 존재하는 것만 필터링
                        image_paths = [p for p in image_paths if os.path.exists(p)]
                    if image_paths:
                        st.markdown('---')
                        st.markdown('**첨부된 사진**')
                        for i in range(0, len(image_paths), 3):
                            cols = st.columns(3)
                            for j, img_path in enumerate(image_paths[i:i+3]):
                                with cols[j]:
                                    st.image(img_path, use_container_width=True)


if __name__ == "__main__":
    main() 