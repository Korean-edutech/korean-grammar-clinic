import streamlit as st
import google.generativeai as genai
import os
import glob
import uuid
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# 페이지 기본 설정
st.set_page_config(layout="wide", page_title="Korean Grammar Clinic")

# 1. 🔑 제미나이 API 키 로드
api_key = os.environ.get("GEMINI_API_KEY")

# 2. 🔥 파이어베이스 초기화 (Secrets 금고 연동)
if not firebase_admin._apps:
    try:
        fb_credentials = dict(st.secrets["firebase"])
        if "private_key" in fb_credentials:
            fb_credentials["private_key"] = fb_credentials["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(fb_credentials)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"파이어베이스 연결 실패: {e}")

# Firestore 클라이언트 생성
db = firestore.client()

# 관리자 비밀번호
ADMIN_PASSWORD = "chamut"

# CSS 스타일 로드 (다크모드 완벽 대응)
try:
    with open("style.css", "r", encoding="utf-8") as css_file:
        custom_css = css_file.read()
    st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# 다국어 UI 사전 (6개국어 복구 및 로그인/비회원 관련 텍스트 추가)
ui_texts = {
    "English": {
        "nav_title": "📌 Menu", "menu_clinic": "📚 Clinic Home", "menu_board": "💬 Community Board",
        "clinic": "Clinic", "select_room": "Grammar Topics", "input_prompt": "Enter your question...", 
        "no_files": "No grammar files yet.", "error_key": "API key missing", "error_msg": "Error",
        "welcome": "Hello! Welcome to the **{room}**. What questions do you have today?", "loading": "Thinking...",
        "board_title": "Community Board", "board_prompt": "Share your questions or feedback!", "board_btn": "Post",
        "like": "👍 Like", "comment_prompt": "Write a comment...", "comment_btn": "Reply",
        "select_lang": "Select Language", "delete_btn": "🗑️ Delete",
        "login_title": "🔐 Sign In / Sign Up", "email": "Email", "pwd": "Password", "btn_login": "Sign In", "btn_signup": "Sign Up", "btn_guest": "👤 Continue as Guest"
    },
    "日本語": {
        "nav_title": "📌 メニュー", "menu_clinic": "📚 クリニックホーム", "menu_board": "💬 コミュニティ",
        "clinic": "クリニック", "select_room": "文法トピック", "input_prompt": "質問を入力...", 
        "no_files": "ファイルがありません。", "error_key": "APIキーなし", "error_msg": "エラー",
        "welcome": "こんにちは！**{room}**へようこそ。どんな質問がありますか？", "loading": "考え中...",
        "board_title": "コミュニティ掲示板", "board_prompt": "質問や意見を共有しましょう！", "board_btn": "投稿",
        "like": "👍 いいね", "comment_prompt": "コメントを入力...", "comment_btn": "返信",
        "select_lang": "言語を選択", "delete_btn": "🗑️ 削除",
        "login_title": "🔐 ログイン / 新規登録", "email": "メールアドレス", "pwd": "パスワード", "btn_login": "ログイン", "btn_signup": "新規登録", "btn_guest": "👤 ゲストとして続ける"
    },
    "한국어": {
        "nav_title": "📌 메뉴", "menu_clinic": "📚 문법 클리닉 홈", "menu_board": "💬 커뮤니티 게시판",
        "clinic": "클리닉", "select_room": "학습할 문법 목록", "input_prompt": "질문을 입력하세요...", 
        "no_files": "등록된 문법이 없습니다.", "error_key": "API 키 오류", "error_msg": "에러 발생",
        "welcome": "안녕하세요! **{room}**에 오신 것을 환영합니다. 오늘 어떤 점이 궁금하신가요?", "loading": "작성 중...",
        "board_title": "커뮤니티 게시판", "board_prompt": "궁금한 점이나 의견을 남겨주세요!", "board_btn": "게시글 작성",
        "like": "👍 공감", "comment_prompt": "댓글을 남겨주세요...", "comment_btn": "댓글 달기",
        "select_lang": "언어를 선택하세요", "delete_btn": "🗑️ 삭제",
        "login_title": "🔐 로그인 / 회원가입", "email": "이메일 주소", "pwd": "비밀번호", "btn_login": "로그인", "btn_signup": "회원가입", "btn_guest": "👤 비회원으로 시작하기"
    },
    "中文": {
        "nav_title": "📌 导航菜单", "menu_clinic": "📚 语法诊所主页", "menu_board": "💬 社区论坛",
        "clinic": "诊所", "select_room": "语法主题", "input_prompt": "请输入问题...", 
        "no_files": "暂无文件。", "error_key": "无 API 密钥", "error_msg": "错误",
        "welcome": "你好！欢迎来到 **{room}**。有什么想问的吗？", "loading": "思考中...",
        "board_title": "社区论坛", "board_prompt": "分享您的问题或意见！", "board_btn": "发布",
        "like": "👍 赞", "comment_prompt": "写评论...", "comment_btn": "回复",
        "select_lang": "选择语言", "delete_btn": "🗑️ 删除",
        "login_title": "🔐 登录 / 注册", "email": "邮箱", "pwd": "密码", "btn_login": "登录", "btn_signup": "注册", "btn_guest": "👤 以游客身份继续"
    },
    "Español": {
        "nav_title": "📌 Menú", "menu_clinic": "📚 Inicio de Clínica", "menu_board": "💬 Comunidad",
        "clinic": "Clínica", "select_room": "Temas de Gramática", "input_prompt": "Ingresa pregunta...", 
        "no_files": "Sin archivos.", "error_key": "Falta API", "error_msg": "Error",
        "welcome": "¡Hola! Bienvenido a la **{room}**. ¿Qué dudas tienes?", "loading": "Pensando...",
        "board_title": "Comunidad", "board_prompt": "¡Comparte preguntas o comentarios!", "board_btn": "Publicar",
        "like": "👍 Me gusta", "comment_prompt": "Escribe un comentario...", "comment_btn": "Responder",
        "select_lang": "Seleccionar idioma", "delete_btn": "🗑️ Eliminar",
        "login_title": "🔐 Iniciar sesión / Registrarse", "email": "Correo electrónico", "pwd": "Contraseña", "btn_login": "Iniciar sesión", "btn_signup": "Registrarse", "btn_guest": "👤 Continuar como invitado"
    },
    "Tiếng Việt": {
        "nav_title": "📌 Thực đơn", "menu_clinic": "📚 Trang chủ Phòng khám", "menu_board": "💬 Cộng đồng",
        "clinic": "Phòng khám", "select_room": "Chủ đề ngữ pháp", "input_prompt": "Nhập câu hỏi...", 
        "no_files": "Chưa có tệp.", "error_key": "Thiếu API", "error_msg": "Lỗi",
        "welcome": "Xin chào! Chào mừng đến với **{room}**. Bạn có câu hỏi nào?", "loading": "Đang nghĩ...",
        "board_title": "Bảng cộng đồng", "board_prompt": "Chia sẻ câu hỏi hoặc ý kiến!", "board_btn": "Đăng",
        "like": "👍 Thích", "comment_prompt": "Viết bình luận...", "comment_btn": "Trả lời",
        "select_lang": "Chọn ngôn ngữ", "delete_btn": "🗑️ Xóa",
        "login_title": "🔐 Đăng nhập / Đăng ký", "email": "Email", "pwd": "Mật khẩu", "btn_login": "Đăng nhập", "btn_signup": "Đăng ký", "btn_guest": "👤 Tiếp tục với tư cách khách"
    }
}

# 기본 세션 상태 정의
if "selected_lang" not in st.session_state:
    st.session_state.selected_lang = "한국어"
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# 현재 선택된 언어 사전 불러오기
t = ui_texts[st.session_state.selected_lang]
lang_list = list(ui_texts.keys())

# ==========================================
# 🔓 비로그인 상태: 로그인 / 회원가입 / 비회원 접속 화면
# ==========================================
if st.session_state.user_email is None:
    st.title("Welcome to Korean Grammar Clinic! 👋")
    
    # 언어 선택 드롭다운
    default_idx = lang_list.index(st.session_state.selected_lang)
    lang_choice = st.selectbox("🌐 Choose Your Language", lang_list, index=default_idx)
    if lang_choice != st.session_state.selected_lang:
        st.session_state.selected_lang = lang_choice
        st.rerun()
        
    st.write("---")
    
    # 로그인 화면 렌더링
    col1, col2, col3 = st.columns([1.5, 0.5, 2])
    with col1:
        st.subheader(t["login_title"])
        auth_email = st.text_input(t["email"], key="auth_email")
        auth_pwd = st.text_input(t["pwd"], type="password", key="auth_pwd")
        
        btn_action1, btn_action2 = st.columns(2)
        
        # 🔑 로그인
        with btn_action1:
            if st.button(t["btn_login"], use_container_width=True):
                if auth_email and auth_pwd:
                    user_ref = db.collection("users").document(auth_email).get()
                    if user_ref.exists and user_ref.to_dict().get("password") == auth_pwd:
                        st.session_state.user_email = auth_email
                        st.success("Success!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                else:
                    st.warning("Please fill in all fields.")
                    
        # 📝 회원가입
        with btn_action2:
            if st.button(t["btn_signup"], use_container_width=True):
                if auth_email and auth_pwd:
                    user_ref = db.collection("users").document(auth_email).get()
                    if user_ref.exists:
                        st.error("This email already exists.")
                    else:
                        db.collection("users").document(auth_email).set({
                            "email": auth_email,
                            "password": auth_pwd,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success("Account created successfully! Please click Login.")
                else:
                    st.warning("Please fill in all fields.")
        
        st.write("<br><br>", unsafe_allow_html=True)
        # 👤 비회원(Guest) 입장 버튼
        if st.button(t["btn_guest"], use_container_width=True, type="primary"):
            st.session_state.user_email = f"Guest_{str(uuid.uuid4())[:4]}"
            st.rerun()
            
    st.stop() # 접속 안 되었으면 아래 메인 화면 구동 중단

# ==========================================
# 🔐 로그인/비회원 접속 완료 상태: 메인 앱 화면 구동
# ==========================================

# 사이드바 상단 정보 및 로그아웃
st.sidebar.markdown(f"👤 **{st.session_state.user_email}**")
if st.sidebar.button("Logout", size="small"):
    st.session_state.user_email = None
    st.session_state.is_admin = False
    st.rerun()

st.sidebar.divider()

# 사이드바 언어 설정
default_idx = lang_list.index(st.session_state.selected_lang)
selected_lang = st.sidebar.selectbox("🌐 Language", lang_list, index=default_idx)
if selected_lang != st.session_state.selected_lang:
    st.session_state.selected_lang = selected_lang
    st.rerun()

st.sidebar.divider()

# 네비게이션 옵션 구성
nav_options = [t["menu_clinic"], t["menu_board"]]
if st.session_state.is_admin:
    nav_options.append("📊 관리자 대시보드")

selected_main_nav = st.sidebar.radio(t["nav_title"], nav_options)
selected_display_name = None

# 하위 문법 목록 스캔
if selected_main_nav == t["menu_clinic"]:
    file_paths = glob.glob("grammar_data/*.txt")
    if not file_paths:
        st.sidebar.warning(t["no_files"])
    else:
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        st.sidebar.caption(f"📂 {t['select_room']}") 
        
        grammar_meta_words = [os.path.basename(path).replace(".txt", "") for path in file_paths]
        room_display_names = [f"&nbsp;&nbsp;&nbsp;{meta_word} {t['clinic']}" for meta_word in grammar_meta_words]
        
        selected_display_name = st.sidebar.radio(
            "sub_menu_hidden_label", 
            room_display_names, 
            label_visibility="collapsed"
        )

st.sidebar.divider()

# 관리자 인증 히든 입력창
st.sidebar.markdown("<br>" * 4, unsafe_allow_html=True) 
if not st.session_state.is_admin:
    admin_pwd = st.sidebar.text_input("admin_hidden", type="password", placeholder="🔒", label_visibility="collapsed")
    if admin_pwd == ADMIN_PASSWORD:
        st.session_state.is_admin = True
        st.rerun()
else:
    st.sidebar.caption("🔓 Admin Active")

# --- 메인 기능 렌더링 ---

# 1. 📊 관리자 대시보드
if selected_main_nav == "📊 관리자 대시보드" and st.session_state.is_admin:
    st.title("📊 실시간 이용 통계 및 로그 (Firestore)")
    
    logs_ref = db.collection("logs").order_by("time", direction=firestore.Query.DESCENDING).stream()
    logs_list = [doc.to_dict() for doc in logs_ref]
    
    st.metric(label="총 누적 질문 수", value=f"{len(logs_list)} 회")
    st.divider()
    
    for log in logs_list:
        st.markdown(f"""
        <div style='background-color: var(--secondary-background-color); padding:10px; border-radius:5px; margin-bottom:10px;'>
            <span style='font-size:0.8em; color:gray;'>⏰ {log.get('time')} | 👤 {log.get('user')} | 🌐 {log.get('lang')} | 🚪 {log.get('room')}</span><br>
            <strong>Q:</strong> {log.get('prompt')}
        </div>
        """, unsafe_allow_html=True)

# 2. 📢 커뮤니티 게시판
elif selected_main_nav == t["menu_board"]:
    st.title(f"📢 {t['board_title']}")
    
    with st.form("new_post_form", clear_on_submit=True):
        new_content = st.text_area(t["board_prompt"], height=100)
        if st.form_submit_button(t["board_btn"]) and new_content.strip():
            post_id = str(uuid.uuid4())
            db.collection("posts").document(post_id).set({
                "id": post_id,
                "time": datetime.now().strftime("%y/%m/%d %H:%M"),
                "lang": st.session_state.selected_lang,
                "content": new_content.strip(),
                "likes": 0,
                "comments": [],
                "user": st.session_state.user_email
            })
            st.rerun()
            
    st.divider()

    posts_ref = db.collection("posts").order_by("time", direction=firestore.Query.DESCENDING).stream()
    for doc in posts_ref:
        post = doc.to_dict()
        with st.container():
            st.markdown(f"""
            <div style='background-color: var(--secondary-background-color); padding:15px; border-radius:10px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: var(--text-color);'>
                <span style='font-size:0.8em; opacity: 0.7;'>✍️ {post['time']} ({post['lang']}) - {post.get('user','Unknown')}</span><br>
                <div style='margin-top:10px; font-size:1.05em;'>{post['content'].replace('\n', '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button(f"{t['like']} ({post['likes']})", key=f"like_{post['id']}"):
                    db.collection("posts").document(post['id']).update({"likes": post['likes'] + 1})
                    st.rerun()
            with col2:
                if st.session_state.is_admin or post.get('user') == st.session_state.user_email:
                    if st.button(t["delete_btn"], key=f"del_{post['id']}"):
                        db.collection("posts").document(post['id']).delete()
                        st.rerun()
                        
            with st.expander(f"💬 {t['comment_btn']} ({len(post['comments'])})"):
                for cmt in post['comments']:
                    st.markdown(f"<div style='background-color:rgba(128,128,128,0.1); padding:8px; border-radius:5px; margin-bottom:5px; font-size:0.9em;'>- {cmt}</div>", unsafe_allow_html=True)
                
                cmt_input = st.text_input(" ", placeholder=t["comment_prompt"], key=f"cmt_input_{post['id']}", label_visibility="collapsed")
                if st.button(t["comment_btn"], key=f"cmt_btn_{post['id']}"):
                    if cmt_input.strip():
                        updated_comments = post['comments'] + [f"{st.session_state.user_email}: {cmt_input.strip()}"]
                        db.collection("posts").document(post['id']).update({"comments": updated_comments})
                        st.rerun()
        st.write("---")

# 3. 🚪 문법 클리닉 챗봇
elif selected_main_nav == t["menu_clinic"] and selected_display_name:
    actual_room_name = selected_display_name.replace("&nbsp;", "").strip()
    st.title(f"🚪 {actual_room_name}")
    
    selected_meta_word = actual_room_name.replace(f" {t['clinic']}", "")
    
    with open(f"grammar_data/{selected_meta_word}.txt", "r", encoding="utf-8") as file:
        target_rules = file.read()

    chat_doc_id = f"{st.session_state.user_email}_{selected_meta_word}"
    chat_ref = db.collection("chats").document(chat_doc_id).get()
    
    if chat_ref.exists:
        st.session_state.messages = chat_ref.to_dict().get("messages", [])
    else:
        initial_greeting = t["welcome"].format(room=actual_room_name)
        st.session_state.messages = [{"role": "assistant", "content": initial_greeting}]
        db.collection("chats").document(chat_doc_id).set({"messages": st.session_state.messages})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"])

    if prompt := st.chat_input(t["input_prompt"]):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
            
        db.collection("logs").add({
            "time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "user": st.session_state.user_email,
            "lang": st.session_state.selected_lang,
            "room": actual_room_name,
            "prompt": prompt
        })
        
        if not api_key:
            with st.chat_message("assistant"):
                st.error(t["error_key"])
        else:
            genai.configure(api_key=api_key)
            
            if st.session_state.selected_lang == "한국어":
                lang_rule = "모든 답변은 한자(漢字)나 영어를 절대 섞지 말고 오직 '자연스러운 한글(한국어)'로만 작성하세요. 문법 용어도 무조건 한글로만 적으세요."
            else:
                lang_rule = f"모든 답변은 반드시 {st.session_state.selected_lang}로 작성하세요. (한국어 문법 용어는 한글로 표기하고 {st.session_state.selected_lang} 번역 병기)"
            
            system_instruction = f"""
            당신은 외국인에게 한국어를 가르치는 친절하고 정밀한 전문 강사입니다. 
            
            [대화 행동 지침 - 최우선 준수 사항]
            0. {lang_rule}
            1. 답변은 잡다한 설명 없이 간단하게 질문에 대한 핵심 내용만 명확히 하세요.
            2. 모든 문법 답변엔 반드시 한국어 예문을 정확히 3개씩 덧붙이세요.
            3. 예문을 만들 땐 문법적, 문맥적 오류나 비문이 없는지 출력 전에 스스로 한 번 더 철저하게 검토하세요.
            4. 사용자가 본격적으로 문법에 대해 질문하거나 대화를 시도할 때만 아래 관리자가 등록한 교안/문법 규칙을 바탕으로 설명하세요.
            
            [관리자 등록 문법 규칙]
            {target_rules}
            """
            
            try:
                model = genai.GenerativeModel('models/gemini-2.5-flash', system_instruction=system_instruction)
                
                with st.chat_message("assistant"):
                    with st.spinner(t["loading"]):
                        response = model.generate_content(prompt)
                    st.markdown(response.text)
                    
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    db.collection("chats").document(chat_doc_id).set({"messages": st.session_state.messages})
            except Exception as e:
                with st.chat_message("assistant"):
                    st.error(f"{t['error_msg']}: {e}")
