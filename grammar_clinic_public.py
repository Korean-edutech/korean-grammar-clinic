import streamlit as st
import google.generativeai as genai
import os
import glob
import json
import uuid
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(layout="wide", page_title="Korean Grammar Clinic")

api_key = os.environ.get("GEMINI_API_KEY")

# 💡 [관리자 비밀번호] 
ADMIN_PASSWORD = "admin"

# CSS 스타일 로드
try:
    with open("style.css", "r", encoding="utf-8") as css_file:
        custom_css = css_file.read()
    st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# 각 언어별 UI 사전
ui_texts = {
    "English": {
        "menu_clinic": "📚 Clinic", "menu_board": "💬 Community",
        "clinic": "Clinic", "select_room": "Select a grammar point:", "input_prompt": "Enter your question...", 
        "no_files": "No grammar files yet.", "error_key": "API key missing", "error_msg": "Error",
        "welcome": "Hello! Welcome to the **{room}**. What questions do you have today?", "loading": "Thinking...",
        "board_title": "Community Board", "board_prompt": "Share your questions or feedback!", "board_btn": "Post",
        "like": "👍 Like", "comment_prompt": "Write a comment...", "comment_btn": "Reply",
        "select_lang": "Select Language", "delete_btn": "🗑️ Delete"
    },
    "日本語": {
        "menu_clinic": "📚 クリニック", "menu_board": "💬 コミュニティ",
        "clinic": "クリニック", "select_room": "文法を選択:", "input_prompt": "質問を入力...", 
        "no_files": "ファイルがありません。", "error_key": "APIキーなし", "error_msg": "エラー",
        "welcome": "こんにちは！**{room}**へようこそ。どんな質問がありますか？", "loading": "考え中...",
        "board_title": "コミュニティ掲示板", "board_prompt": "質問や意見を共有しましょう！", "board_btn": "投稿",
        "like": "👍 いいね", "comment_prompt": "コメントを入力...", "comment_btn": "返信",
        "select_lang": "言語を選択してください", "delete_btn": "🗑️ 削除"
    },
    "한국어": {
        "menu_clinic": "📚 문법 클리닉", "menu_board": "💬 커뮤니티 게시판",
        "clinic": "클리닉", "select_room": "학습할 문법을 선택하세요:", "input_prompt": "질문을 입력하세요...", 
        "no_files": "등록된 문법이 없습니다.", "error_key": "API 키 오류", "error_msg": "에러 발생",
        "welcome": "안녕하세요! **{room}**에 오신 것을 환영합니다. 오늘 어떤 점이 궁금하신가요?", "loading": "작성 중...",
        "board_title": "커뮤니티 게시판", "board_prompt": "궁금한 점이나 의견을 남겨주세요!", "board_btn": "게시글 작성",
        "like": "👍 공감", "comment_prompt": "댓글을 남겨주세요...", "comment_btn": "댓글 달기",
        "select_lang": "언어를 선택하세요", "delete_btn": "🗑️ 삭제"
    },
    "中文": {
        "menu_clinic": "📚 语法诊所", "menu_board": "💬 社区",
        "clinic": "诊所", "select_room": "选择语法:", "input_prompt": "请输入问题...", 
        "no_files": "暂无文件。", "error_key": "无 API 密钥", "error_msg": "错误",
        "welcome": "你好！欢迎来到 **{room}**。有什么想问的吗？", "loading": "思考中...",
        "board_title": "社区论坛", "board_prompt": "分享您的问题或意见！", "board_btn": "发布",
        "like": "👍 赞", "comment_prompt": "写评论...", "comment_btn": "回复",
        "select_lang": "请选择语言", "delete_btn": "🗑️ 删除"
    },
    "Español": {
        "menu_clinic": "📚 Clínica", "menu_board": "💬 Comunidad",
        "clinic": "Clínica", "select_room": "Selecciona gramática:", "input_prompt": "Ingresa pregunta...", 
        "no_files": "Sin archivos.", "error_key": "Falta API", "error_msg": "Error",
        "welcome": "¡Hola! Bienvenido a la **{room}**. ¿Qué dudas tienes?", "loading": "Pensando...",
        "board_title": "Comunidad", "board_prompt": "¡Comparte preguntas o comentarios!", "board_btn": "Publicar",
        "like": "👍 Me gusta", "comment_prompt": "Escribe un comentario...", "comment_btn": "Responder",
        "select_lang": "Selecciona el idioma", "delete_btn": "🗑️ Eliminar"
    },
    "Tiếng Việt": {
        "menu_clinic": "📚 Phòng khám", "menu_board": "💬 Cộng đồng",
        "clinic": "Phòng khám", "select_room": "Chọn ngữ pháp:", "input_prompt": "Nhập câu hỏi...", 
        "no_files": "Chưa có tệp.", "error_key": "Thiếu API", "error_msg": "Lỗi",
        "welcome": "Xin chào! Chào mừng đến với **{room}**. Bạn có câu hỏi nào?", "loading": "Đang nghĩ...",
        "board_title": "Bảng cộng đồng", "board_prompt": "Chia sẻ câu hỏi hoặc ý kiến!", "board_btn": "Đăng",
        "like": "👍 Thích", "comment_prompt": "Viết bình luận...", "comment_btn": "Trả lời",
        "select_lang": "Chọn ngôn ngữ", "delete_btn": "🗑️ Xóa"
    }
}

# 언어 선택 창 문구 다국어화 상태 유지 로직
if "selected_lang" not in st.session_state:
    st.session_state.selected_lang = "한국어"

lang_list = list(ui_texts.keys())
default_idx = lang_list.index(st.session_state.selected_lang)

st.sidebar.title("🌐 Language")
current_lang_label = ui_texts[st.session_state.selected_lang]["select_lang"]

selected_lang = st.sidebar.selectbox(current_lang_label, lang_list, index=default_idx)

if selected_lang != st.session_state.selected_lang:
    st.session_state.selected_lang = selected_lang
    st.rerun()

t = ui_texts[st.session_state.selected_lang]

st.sidebar.divider()

# 사이드바 메뉴 네비게이션
page_mode = st.sidebar.radio("📌 Navigation", [t["menu_clinic"], t["menu_board"]])

st.sidebar.divider()

# 💡 [업데이트] 관리자 모드를 티 안 나게 구석으로 밀어내기 (공백 추가)
st.sidebar.markdown("<br>" * 8, unsafe_allow_html=True) 

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# 큰 버튼이나 텍스트 없이, 라벨을 숨긴 텍스트 입력창 하나만 배치
if not st.session_state.is_admin:
    admin_pwd = st.sidebar.text_input(
        "admin_hidden", 
        type="password", 
        placeholder="🔒", 
        label_visibility="collapsed", 
        key="admin_pwd_input"
    )
    # 버튼 없이 비밀번호를 치고 엔터를 누르면 즉시 관리자 모드 온!
    if admin_pwd == ADMIN_PASSWORD:
        st.session_state.is_admin = True
        st.rerun()
else:
    st.sidebar.caption("🔓 Admin Active")
    if st.sidebar.button("Logout"):
        st.session_state.is_admin = False
        st.rerun()

# ==========================================
# 1. 커뮤니티 게시판 페이지 로직
# ==========================================
if page_mode == t["menu_board"]:
    st.title(f"📢 {t['board_title']}")
    
    board_db = "community_board.json"
    
    if not os.path.exists(board_db):
        with open(board_db, "w", encoding="utf-8") as f:
            json.dump([], f)
            
    with open(board_db, "r", encoding="utf-8") as f:
        posts = json.load(f)

    # 새 글 작성 폼
    with st.form("new_post_form", clear_on_submit=True):
        new_content = st.text_area(t["board_prompt"], height=100)
        if st.form_submit_button(t["board_btn"]) and new_content.strip():
            new_post = {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%y/%m/%d %H:%M"),
                "lang": st.session_state.selected_lang,
                "content": new_content.strip(),
                "likes": 0,
                "comments": []
            }
            posts.insert(0, new_post)
            with open(board_db, "w", encoding="utf-8") as f:
                json.dump(posts, f, ensure_ascii=False, indent=4)
            st.rerun()
            
    st.divider()

    # 게시글 목록 출력
    for idx, post in enumerate(posts):
        with st.container():
            st.markdown(f"""
            <div style='background-color:#FFFFFF; padding:15px; border-radius:10px; border:1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <span style='font-size:0.8em; color:#64748B;'>✍️ {post['time']} ({post['lang']})</span><br>
                <div style='margin-top:10px; font-size:1.05em;'>{post['content'].replace('\n', '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 3])
            
            # 공감 버튼
            with col1:
                if st.button(f"{t['like']} ({post['likes']})", key=f"like_{post['id']}"):
                    posts[idx]["likes"] += 1
                    with open(board_db, "w", encoding="utf-8") as f:
                        json.dump(posts, f, ensure_ascii=False, indent=4)
                    st.rerun()
            
            # 관리자 전용 삭제 버튼
            with col2:
                if st.session_state.is_admin:
                    if st.button(t["delete_btn"], key=f"del_{post['id']}"):
                        posts.pop(idx)
                        with open(board_db, "w", encoding="utf-8") as f:
                            json.dump(posts, f, ensure_ascii=False, indent=4)
                        st.rerun()
            
            # 댓글 시스템
            with st.expander(f"💬 {t['comment_btn']} ({len(post['comments'])})"):
                for cmt in post['comments']:
                    st.markdown(f"<div style='background-color:#F8FAFC; padding:8px; border-radius:5px; margin-bottom:5px; font-size:0.9em;'>- {cmt}</div>", unsafe_allow_html=True)
                
                cmt_input = st.text_input(" ", placeholder=t["comment_prompt"], key=f"cmt_input_{post['id']}", label_visibility="collapsed")
                if st.button(t["comment_btn"], key=f"cmt_btn_{post['id']}"):
                    if cmt_input.strip():
                        posts[idx]["comments"].append(cmt_input.strip())
                        with open(board_db, "w", encoding="utf-8") as f:
                            json.dump(posts, f, ensure_ascii=False, indent=4)
                        st.rerun()
        st.write("---")

# ==========================================
# 2. 문법 클리닉(챗봇) 페이지 로직
# ==========================================
else:
    st.sidebar.title("📚 Grammar Topics")
    file_paths = glob.glob("grammar_data/*.txt")

    if not file_paths:
        st.sidebar.warning(t["no_files"])
    else:
        grammar_meta_words = [os.path.basename(path).replace(".txt", "") for path in file_paths]
        room_display_names = [f"{meta_word} {t['clinic']}" for meta_word in grammar_meta_words]
        
        selected_display_name = st.sidebar.radio(t["select_room"], room_display_names)
        
        if selected_display_name:
            st.title(f"🚪 {selected_display_name}")
            selected_meta_word = selected_display_name.replace(f" {t['clinic']}", "")
            
            with open(f"grammar_data/{selected_meta_word}.txt", "r", encoding="utf-8") as file:
                target_rules = file.read()

            if "current_room" not in st.session_state or st.session_state.current_room != selected_display_name:
                st.session_state.current_room = selected_display_name
                initial_greeting = t["welcome"].format(room=selected_display_name)
                st.session_state.messages = [{"role": "assistant", "content": initial_greeting}]

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): 
                    st.markdown(msg["content"])

            if prompt := st.chat_input(t["input_prompt"]):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): 
                    st.markdown(prompt)
                
                if not api_key:
                    with st.chat_message("assistant"):
                        st.error(t["error_key"])
                else:
                    genai.configure(api_key=api_key)
                    
                    system_instruction = f"""
                    당신은 외국인에게 한국어를 가르치는 친절하고 정밀한 전문 강사입니다. 
                    모든 답변은 반드시 {st.session_state.selected_lang}로 작성하세요. (한국어 문법 용어는 한글로 표기하고 {st.session_state.selected_lang} 번역 병기)
                    
                    [대화 행동 지침 - 최우선 준수 사항]
                    1. 질문자가 대화를 시작하기 전에 간단한 인사를 먼저 건네세요. (시스템 내부적으로 이미 선제 인사가 이루어졌음을 인지할 것)
                    2. 사용자가 "안녕", "Hello", "니하오" 등 가벼운 인사만 건네면, 문법 설명을 절대로 먼저 하지 말고 친절하게 해당 언어로 인사만 받아주세요.
                    3. 답변은 잡다한 설명 없이 간단하게 질문에 대한 핵심 내용만 명확히 하세요.
                    4. 모든 문법 답변엔 반드시 한국어 예문을 정확히 3개씩 덧붙이세요.
                    5. 예문을 만들 땐 문법적, 문맥적 오류나 비문이 없는지 출력 전에 스스로 한 번 더 철저하게 검토하세요.
                    6. 사용자가 본격적으로 문법에 대해 질문하거나 대화를 시도할 때만 아래 관리자가 등록한 교안/문법 규칙을 바탕으로 설명하세요.
                    
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
                    except Exception as e:
                        with st.chat_message("assistant"):
                            st.error(f"{t['error_msg']}: {e}")
