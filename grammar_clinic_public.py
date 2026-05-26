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

# CSS 스타일 로드
try:
    with open("style.css", "r", encoding="utf-8") as css_file:
        custom_css = css_file.read()
    st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass
    
# 🌐 다국어 UI 사전 (에러 메시지 다국어 완벽 추가!)
ui_texts = {
    "한국어": {
        "main_title": "한국어 문법 클리닉에 오신 것을 환영합니다! 👋", "choose_lang": "🌐 언어를 선택하세요",
        "nav_title": "📌 메뉴", "menu_clinic": "📚 문법 클리닉 홈", "menu_board": "💬 커뮤니티 게시판", "menu_history": "🏆 내 학습 기록",
        "clinic": "클리닉", "select_room": "학습할 문법 목록", "input_prompt": "질문을 입력하세요...", 
        "no_files": "등록된 문법이 없습니다.", "error_key": "API 키 오류", "error_msg": "에러 발생",
        "welcome": "안녕하세요! **{room}**에 오신 것을 환영합니다. 오늘 어떤 점이 궁금하신가요?", "loading": "작성 중...",
        "board_title": "커뮤니티 게시판", "board_prompt": "궁금한 점이나 의견을 남겨주세요!", "board_btn": "게시글 작성",
        "like": "👍 공감", "comment_prompt": "댓글을 남겨주세요...", "comment_btn": "댓글 달기",
        "select_lang": "언어를 선택하세요", "delete_btn": "🗑️ 삭제",
        "login_title": "🔐 로그인 / 회원가입", "email": "이메일 주소", "pwd": "비밀번호", "btn_login": "로그인", "btn_signup": "회원가입", "btn_guest": "👤 비회원으로 시작하기",
        "signup_agree": "개인정보 수집 및 이용 동의 (필수)",
        "guest_agree": "서비스 품질 향상을 위한 대화 기록 무기명 수집에 동의합니다. (필수)",
        "agree_warn_signup": "회원가입을 위해 개인정보 수집 및 이용에 동의해 주세요.",
        "agree_warn_guest": "비회원 이용을 위해 데이터 수집에 동의해 주세요.",
        "chat_warn": "⚠️ 대화 내용은 서비스 품질 향상을 위해 익명으로 수집될 수 있습니다. 개인정보(이름, 연락처 등)를 절대 입력하지 마세요.",
        "history_desc": "지금까지 여러 문법 방에서 나눈 대화들을 한눈에 모아볼 수 있습니다.",
        "history_search": "🔍 검색어 입력 (문법 방 이름이나 질문 내용을 검색해 보세요)",
        "history_no_record": "아직 대화 기록이 없습니다. 문법 클리닉에서 첫 질문을 남겨보세요!",
        "history_no_result": "'{query}'에 대한 검색 결과가 없습니다.",
        "history_view": "🚪 '{room}' 클리닉 기록 보기", "history_me": "👤 나", "history_teacher": "🤖 선생님",
        "guide_title": "📖 '{room}' 학습 가이드 및 추천 질문",
        "guide_desc": "이 방에서는 **{room}** 문법에 대해 집중적으로 묻고 답할 수 있습니다. 어떻게 시작할지 모르겠다면 아래 버튼을 클릭해 보세요!",
        "btn_q1": "🎯 기본 의미와 규칙", "btn_q2": "📝 예문 3개 만들기", "btn_q3": "🤔 비슷한 문법 비교",
        "prompt_q1": "'{room}' 문법의 기본적인 의미와 사용 규칙을 초보자도 이해하기 쉽게 설명해 줘.",
        "prompt_q2": "'{room}' 문법을 활용한 자연스러운 한국어 예문 3개를 만들어 줘.",
        "prompt_q3": "'{room}' 문법과 가장 헷갈리기 쉬운 문법을 딱 1개만 골라서 차이점을 짧게 설명하고, 다시 '{room}' 문법의 핵심 특징으로 마무리해 줘.",
        "error_quota": "⏳ 앗, 선생님이 잠시 생각할 시간이 필요해요! 약 20초 뒤에 다시 질문해 주세요."
    },
    "English": {
        "main_title": "Welcome to Korean Grammar Clinic! 👋", "choose_lang": "🌐 Choose Your Language",
        "nav_title": "📌 Menu", "menu_clinic": "📚 Clinic Home", "menu_board": "💬 Community Board", "menu_history": "🏆 My History",
        "clinic": "Clinic", "select_room": "Grammar Topics", "input_prompt": "Enter your question...", 
        "no_files": "No grammar files yet.", "error_key": "API key missing", "error_msg": "Error",
        "welcome": "Hello! Welcome to the **{room}**. What questions do you have today?", "loading": "Thinking...",
        "board_title": "Community Board", "board_prompt": "Share your questions or feedback!", "board_btn": "Post",
        "like": "👍 Like", "comment_prompt": "Write a comment...", "comment_btn": "Reply",
        "select_lang": "Select Language", "delete_btn": "🗑️ Delete",
        "login_title": "🔐 Sign In / Sign Up", "email": "Email", "pwd": "Password", "btn_login": "Sign In", "btn_signup": "Sign Up", "btn_guest": "👤 Continue as Guest",
        "signup_agree": "I agree to the collection and use of personal information (Required)",
        "guest_agree": "I agree to the anonymous collection of chat logs for service improvement (Required)",
        "agree_warn_signup": "Please agree to the privacy policy to sign up.",
        "agree_warn_guest": "Please agree to the data collection to continue as guest.",
        "chat_warn": "⚠️ Chat logs may be collected anonymously to improve service quality. Do NOT enter personal information (name, contact info, etc.).",
        "history_desc": "You can view all your conversations from various grammar rooms at a glance.",
        "history_search": "🔍 Search (Enter a grammar topic or keyword)",
        "history_no_record": "No chat history found. Leave your first question in the Grammar Clinic!",
        "history_no_result": "No search results found for '{query}'.",
        "history_view": "🚪 View '{room}' Clinic Records", "history_me": "👤 Me", "history_teacher": "🤖 Teacher",
        "guide_title": "📖 '{room}' Study Guide & Suggested Questions",
        "guide_desc": "In this room, you can ask and answer questions focusing on the **{room}** grammar. If you don't know how to start, click the buttons below!",
        "btn_q1": "🎯 Basic Meaning & Rules", "btn_q2": "📝 Create 3 Examples", "btn_q3": "🤔 Compare Similar Grammar",
        "prompt_q1": "Please explain the basic meaning and usage rules of the '{room}' grammar in an easy way for beginners to understand.",
        "prompt_q2": "Please create 3 natural Korean example sentences using the '{room}' grammar.",
        "prompt_q3": "Please pick exactly 1 grammar point that is easily confused with the '{room}' grammar, briefly explain the difference, and finish by summarizing the core features of the '{room}' grammar.",
        "error_quota": "⏳ The teacher needs a moment to think! Please try asking again in about 20 seconds."
    },
    "日本語": {
        "main_title": "韓国語文法クリニックへようこそ！ 👋", "choose_lang": "🌐 言語を選択してください",
        "nav_title": "📌 メニュー", "menu_clinic": "📚 クリニックホーム", "menu_board": "💬 コミュニティ", "menu_history": "🏆 学習履歴",
        "clinic": "クリニック", "select_room": "文法トピック", "input_prompt": "質問を入力...", 
        "no_files": "ファイルがありません。", "error_key": "APIキーなし", "error_msg": "エラー",
        "welcome": "こんにちは！**{room}**へようこそ。どんな質問がありますか？", "loading": "考え中...",
        "board_title": "コミュニティ掲示板", "board_prompt": "質問や意見を共有しましょう！", "board_btn": "投稿",
        "like": "👍 いいね", "comment_prompt": "コメントを入力...", "comment_btn": "返信",
        "select_lang": "言語を選択", "delete_btn": "🗑️ 削除",
        "login_title": "🔐 ログイン / 新規登録", "email": "メールアドレス", "pwd": "パスワード", "btn_login": "ログイン", "btn_signup": "新規登録", "btn_guest": "👤 ゲストとして続ける",
        "signup_agree": "個人情報の収集および利用に同意します（必須）",
        "guest_agree": "サービス向上のための対話記録の無名収集に同意します（必須）",
        "agree_warn_signup": "会員登録には個人情報収集への同意が必要です。",
        "agree_warn_guest": "ゲスト利用にはデータ収集への同意が必要です。",
        "chat_warn": "⚠️ 対話内容はサービス向上のため無名で収集される場合があります。個人情報（氏名、連絡先など）は絶対に入力しないでください。",
        "history_desc": "これまで様々な文法ルームで交わした会話をひと目で確認できます。",
        "history_search": "🔍 検索 (文法トピックやキーワードを入力してください)",
        "history_no_record": "まだ会話履歴がありません。文法クリニックで最初の質問を残してみましょう！",
        "history_no_result": "'{query}' に関する検索結果がありません。",
        "history_view": "🚪 '{room}' クリニック履歴を見る", "history_me": "👤 私", "history_teacher": "🤖 先生",
        "guide_title": "📖 '{room}' 学習ガイドとおすすめの質問",
        "guide_desc": "この部屋では、**{room}** の文法に集中して質疑応答ができます。始め方がわからない場合は、下のボタンをクリックしてみてください！",
        "btn_q1": "🎯 基本的な意味と規則", "btn_q2": "📝 例文を3つ作成", "btn_q3": "🤔 似ている文法と比較",
        "prompt_q1": "初心者にもわかりやすいように、'{room}' 文法の基本的な意味と使用規則を説明してください。",
        "prompt_q2": "'{room}' 文法を活用した自然な韓国語の例文を3つ作成してください。",
        "prompt_q3": "'{room}' 文法と最も混同しやすい文法を1つだけ選び、違いを短く説明した後、再び '{room}' 文法の核心的な特徴で締めくくってください。",
        "error_quota": "⏳ 先生が少し考える時間が必要です！約20秒後にもう一度質問してください。"
    },
    "中文": {
        "main_title": "欢迎来到韩国语语法诊所！ 👋", "choose_lang": "🌐 请选择您的语言",
        "nav_title": "📌 导航菜单", "menu_clinic": "📚 语法诊所主页", "menu_board": "💬 社区论坛", "menu_history": "🏆 我的学习记录",
        "clinic": "诊所", "select_room": "语法主题", "input_prompt": "请输入问题...", 
        "no_files": "暂无文件。", "error_key": "无 API 密钥", "error_msg": "错误",
        "welcome": "你好！欢迎来到 **{room}**。有什么想问的吗？", "loading": "思考中...",
        "board_title": "社区论坛", "board_prompt": "分享您的问题或意见！", "board_btn": "发布",
        "like": "👍 赞", "comment_prompt": "写评论...", "comment_btn": "回复",
        "select_lang": "选择语言", "delete_btn": "🗑️ 删除",
        "login_title": "🔐 登录 / 注册", "email": "邮箱", "pwd": "密码", "btn_login": "登录", "btn_signup": "注册", "btn_guest": "👤 以游客身份继续",
        "signup_agree": "我同意收集和使用个人信息（必填）",
        "guest_agree": "我同意匿名收集聊天记录以用于改进服务（必填）",
        "agree_warn_signup": "请同意隐私政策以进行注册。",
        "agree_warn_guest": "请同意数据收集以游客身份继续。",
        "chat_warn": "⚠️ 聊天记录可能会被匿名收集以用于改进服务质量。请勿输入个人信息（姓名、联系方式等）。",
        "history_desc": "您可以一目了然地查看在各个语法聊天室中的所有对话。",
        "history_search": "🔍 输入关键字 (搜索语法聊天室名称或对话内容)",
        "history_no_record": "暂无对话记录。请在语法诊所留下您的第一个问题！",
        "history_no_result": "没有找到关于 '{query}' 的搜索结果。",
        "history_view": "🚪 查看 '{room}' 诊所记录", "history_me": "👤 我", "history_teacher": "🤖 老师",
        "guide_title": "📖 '{room}' 学习指南与推荐问题",
        "guide_desc": "在这个房间里，您可以集中提问和回答关于 **{room}** 语法的问题。如果您不知道如何开始，请点击下面的按钮！",
        "btn_q1": "🎯 基本含义与规则", "btn_q2": "📝 创建3个例句", "btn_q3": "🤔 比较相似语法",
        "prompt_q1": "请用初学者易于理解的方式解释 '{room}' 语法的基本含义和使用规则。",
        "prompt_q2": "请使用 '{room}' 语法创建3个自然的韩语例句。",
        "prompt_q3": "请挑出1个最容易与 '{room}' 语法混淆的语法，简要说明差异，然后再次以 '{room}' 语法的核心特征作为总结。",
        "error_quota": "⏳ 老师需要一点时间思考！请在大约20秒后再试一次。"
    },
    "Español": {
        "main_title": "¡Bienvenido a la Clínica de Gramática Coreana! 👋", "choose_lang": "🌐 Elige tu idioma",
        "nav_title": "📌 Menú", "menu_clinic": "📚 Inicio de Clínica", "menu_board": "💬 Comunidad", "menu_history": "🏆 Mi Historial",
        "clinic": "Clínica", "select_room": "Temas de Gramática", "input_prompt": "Ingresa pregunta...", 
        "no_files": "Sin archivos.", "error_key": "Falta API", "error_msg": "Error",
        "welcome": "¡Hola! Bienvenido a la **{room}**. ¿Qué dudas tienes?", "loading": "Pensando...",
        "board_title": "Comunidad", "board_prompt": "¡Comparte preguntas o comentarios!", "board_btn": "Publicar",
        "like": "👍 Me gusta", "comment_prompt": "Escribe un comentario...", "comment_btn": "Responder",
        "select_lang": "Seleccionar idioma", "delete_btn": "🗑️ Eliminar",
        "login_title": "🔐 Iniciar sesión / Registrarse", "email": "Correo electrónico", "pwd": "Contraseña", "btn_login": "Iniciar sesión", "btn_signup": "Registrarse", "btn_guest": "👤 Continuar como invitado",
        "signup_agree": "Acepto la recopilación y el uso de información personal (Obligatorio)",
        "guest_agree": "Acepto la recopilación anónima de registros de chat para mejorar el servicio (Obligatorio)",
        "agree_warn_signup": "Por favor, acepte la política de privacidad para registrarse.",
        "agree_warn_guest": "Por favor, acepte la recopilación de datos para continuar como invitado.",
        "chat_warn": "⚠️ Los registros de chat pueden recopilarse de forma anónima para mejorar la calidad del servicio. NO introduzca información personal (nombre, contacto, etc.).",
        "history_desc": "Puedes ver todas tus conversaciones de varias salas de gramática de un vistazo.",
        "history_search": "🔍 Buscar (Busque salas de gramática o contenido)",
        "history_no_record": "No hay historial de chat. ¡Deja tu primera pregunta!",
        "history_no_result": "No se encontraron resultados para '{query}'.",
        "history_view": "🚪 Ver registros de '{room}'", "history_me": "👤 Yo", "history_teacher": "🤖 Profesor",
        "guide_title": "📖 Guía de Estudio y Preguntas para '{room}'",
        "guide_desc": "En esta sala, puedes hacer y responder preguntas enfocadas en **{room}**. Si no sabes cómo empezar, ¡haz clic abajo!",
        "btn_q1": "🎯 Significado y Reglas", "btn_q2": "📝 Crear 3 Ejemplos", "btn_q3": "🤔 Comparar Gramática",
        "prompt_q1": "Explica el significado básico y las reglas de uso de '{room}' de manera fácil.",
        "prompt_q2": "Crea 3 oraciones de ejemplo naturales usando '{room}'.",
        "prompt_q3": "Elige 1 gramática que se confunda con '{room}', explica la diferencia y resume '{room}'.",
        "error_quota": "⏳ ¡El profesor necesita un momento para pensar! Vuelve a preguntar en unos 20 segundos."
    },
    "Tiếng Việt": {
        "main_title": "Chào mừng đến với Phòng khám Ngữ pháp Tiếng Hàn! 👋", "choose_lang": "🌐 Chọn ngôn ngữ của bạn",
        "nav_title": "📌 Thực đơn", "menu_clinic": "📚 Trang chủ Phòng khám", "menu_board": "💬 Cộng đồng", "menu_history": "🏆 Lịch sử học tập",
        "clinic": "Phòng khám", "select_room": "Chủ đề ngữ pháp", "input_prompt": "Nhập câu hỏi...", 
        "no_files": "Chưa có tệp.", "error_key": "Thiếu API", "error_msg": "Lỗi",
        "welcome": "Xin chào! Chào mừng đến với **{room}**. Bạn có câu hỏi nào?", "loading": "Đang nghĩ...",
        "board_title": "Bảng cộng đồng", "board_prompt": "Chia sẻ câu hỏi hoặc ý kiến!", "board_btn": "Đăng",
        "like": "👍 Thích", "comment_prompt": "Viết bình luận...", "comment_btn": "Trả lời",
        "select_lang": "Chọn ngôn ngữ", "delete_btn": "🗑️ Xóa",
        "login_title": "🔐 Đăng nhập / Đăng ký", "email": "Email", "pwd": "Mật khẩu", "btn_login": "Đăng nhập", "btn_signup": "Đăng ký", "btn_guest": "👤 Tiếp tục với tư cách khách",
        "signup_agree": "Tôi đồng ý thu thập và sử dụng thông tin cá nhân (Bắt buộc)",
        "guest_agree": "Tôi đồng ý thu thập ẩn danh lịch sử trò chuyện để cải thiện dịch vụ (Bắt buộc)",
        "agree_warn_signup": "Vui lòng đồng ý với chính sách bảo mật để đăng ký.",
        "agree_warn_guest": "Vui lòng đồng ý thu thập dữ liệu để tiếp tục với tư cách khách.",
        "chat_warn": "⚠️ Lịch sử trò chuyện có thể được thu thập ẩn danh để cải thiện chất lượng dịch vụ. TUYỆT ĐỐI KHÔNG nhập thông tin cá nhân (tên, số điện thoại, v.v.).",
        "history_desc": "Bạn có thể xem thoáng qua tất cả các cuộc trò chuyện từ các phòng ngữ pháp khác nhau.",
        "history_search": "🔍 Nhập từ khóa tìm kiếm (Tìm kiếm tên phòng hoặc nội dung)",
        "history_no_record": "Chưa có lịch sử trò chuyện. Hãy để lại câu hỏi đầu tiên của bạn!",
        "history_no_result": "Không tìm thấy kết quả tìm kiếm cho '{query}'.",
        "history_view": "🚪 Xem hồ sơ phòng khám '{room}'", "history_me": "👤 Tôi", "history_teacher": "🤖 Giáo viên",
        "guide_title": "📖 Hướng dẫn học & Câu hỏi gợi ý '{room}'",
        "guide_desc": "Trong phòng này, bạn có thể hỏi đáp tập trung vào ngữ pháp **{room}**. Nếu bạn không biết bắt đầu từ đâu, hãy nhấp vào các nút bên dưới!",
        "btn_q1": "🎯 Ý nghĩa & Quy tắc", "btn_q2": "📝 Tạo 3 ví dụ", "btn_q3": "🤔 So sánh ngữ pháp",
        "prompt_q1": "Hãy giải thích ý nghĩa cơ bản và quy tắc sử dụng của ngữ pháp '{room}' một cách dễ hiểu.",
        "prompt_q2": "Hãy tạo 3 câu ví dụ tiếng Hàn tự nhiên sử dụng ngữ pháp '{room}'.",
        "prompt_q3": "Hãy chọn đúng 1 ngữ pháp dễ nhầm lẫn nhất với '{room}', giải thích ngắn gọn sự khác biệt và tóm tắt lại '{room}'.",
        "error_quota": "⏳ Giáo viên cần một chút thời gian để suy nghĩ! Vui lòng hỏi lại sau khoảng 20 giây."
    },
    "Français": {
        "main_title": "Bienvenue à la Clinique de Grammaire Coréenne ! 👋", "choose_lang": "🌐 Choisissez votre langue",
        "nav_title": "📌 Menu", "menu_clinic": "📚 Accueil Clinique", "menu_board": "💬 Forum Communautaire", "menu_history": "🏆 Mon Historique",
        "clinic": "Clinique", "select_room": "Sujets de Grammaire", "input_prompt": "Entrez votre question...", 
        "no_files": "Aucun fichier de grammaire.", "error_key": "Clé API manquante", "error_msg": "Erreur",
        "welcome": "Bonjour ! Bienvenue dans la **{room}**. Quelles questions avez-vous aujourd'hui ?", "loading": "Réflexion...",
        "board_title": "Forum Communautaire", "board_prompt": "Partagez vos questions ou commentaires !", "board_btn": "Publier",
        "like": "👍 J'aime", "comment_prompt": "Écrire un commentaire...", "comment_btn": "Répondre",
        "select_lang": "Choisir la langue", "delete_btn": "🗑️ Supprimer",
        "login_title": "🔐 Connexion / Inscription", "email": "E-mail", "pwd": "Mot de passe", "btn_login": "Se connecter", "btn_signup": "S'inscrire", "btn_guest": "👤 Continuer en tant qu'invité",
        "signup_agree": "J'accepte la collecte et l'utilisation d'informations personnelles (Requis)",
        "guest_agree": "J'accepte la collecte anonyme des journaux de discussion pour l'amélioration du service (Requis)",
        "agree_warn_signup": "Veuillez accepter la politique de confidentialité pour vous inscrire.",
        "agree_warn_guest": "Veuillez accepter la collecte de données pour continuer en tant qu'invité.",
        "chat_warn": "⚠️ Les journaux de discussion peuvent être collectés anonymement pour améliorer le service. N'entrez PAS d'informations personnelles.",
        "history_desc": "Vous pouvez voir en un coup d'œil toutes vos conversations dans les différentes salles de grammaire.",
        "history_search": "🔍 Rechercher (Entrez un thème ou un mot-clé)",
        "history_no_record": "Aucun historique de chat. Laissez votre première question !",
        "history_no_result": "Aucun résultat trouvé pour '{query}'.",
        "history_view": "🚪 Voir les dossiers '{room}'", "history_me": "👤 Moi", "history_teacher": "🤖 Professeur",
        "guide_title": "📖 Guide d'étude et questions pour '{room}'",
        "guide_desc": "Dans ce salon, posez des questions sur **{room}**. Cliquez sur les boutons ci-dessous !",
        "btn_q1": "🎯 Sens et règles", "btn_q2": "📝 Créer 3 exemples", "btn_q3": "🤔 Comparer grammaire",
        "prompt_q1": "Expliquez le sens de base et les règles de '{room}' facilement.",
        "prompt_q2": "Créez 3 phrases d'exemple naturelles utilisant '{room}'.",
        "prompt_q3": "Choisissez 1 grammaire confondue avec '{room}', expliquez la différence et résumez '{room}'.",
        "error_quota": "⏳ Le professeur a besoin d'un moment pour réfléchir ! Veuillez réessayer dans environ 20 secondes."
    },
    "हिन्दी": {
        "main_title": "कोरियाई व्याकरण क्लिनिक में आपका स्वागत है! 👋", "choose_lang": "🌐 अपनी भाषा चुनें",
        "nav_title": "📌 मेनू", "menu_clinic": "📚 क्लिनिक होम", "menu_board": "💬 कमाईनिटी बोर्ड", "menu_history": "🏆 मेरा इतिहास",
        "clinic": "क्लिनिक", "select_room": "व्याकरण विषय", "input_prompt": "अपना प्रश्न दर्ज करें...", 
        "no_files": "अभी तक कोई फ़ाइल नहीं।", "error_key": "एपीआई कुंजी", "error_msg": "त्रुटि",
        "welcome": "नमस्ते! **{room}** में आपका स्वागत है। आज आपके क्या प्रश्न हैं?", "loading": "सोच रहा हूँ...",
        "board_title": "सामुदायिक बोर्ड", "board_prompt": "अपने प्रश्न या प्रतिक्रिया साझा करें!", "board_btn": "पोस्ट करें",
        "like": "👍 लाइक", "comment_prompt": "एक टिप्पणी लिखें...", "comment_btn": "उत्तर दें",
        "select_lang": "भाषा चुनें", "delete_btn": "🗑️ हटाएं",
        "login_title": "🔐 साइन इन / साइन अप", "email": "ईमेल", "pwd": "पासवर्ड", "btn_login": "साइन इन", "btn_signup": "साइन अप", "btn_guest": "👤 अतिथि के रूप में जारी रखें",
        "signup_agree": "सहमत हूँ (आवश्यक)",
        "guest_agree": "सहमत हूँ (आवश्यक)",
        "agree_warn_signup": "कृपया गोपनीयता नीति से सहमत हों।",
        "agree_warn_guest": "कृपया डेटा संग्रह से सहमत हों।",
        "chat_warn": "⚠️ व्यक्तिगत जानकारी दर्ज न करें।",
        "history_desc": "आप अपनी सभी बातचीत देख सकते हैं।",
        "history_search": "🔍 खोजें",
        "history_no_record": "कोई चैट इतिहास नहीं मिला।",
        "history_no_result": "'{query}' के लिए कोई खोज परिणाम नहीं मिले।",
        "history_view": "🚪 '{room}' रिकॉर्ड देखें", "history_me": "👤 मैं", "history_teacher": "🤖 शिक्षक",
        "guide_title": "📖 '{room}' अध्ययन मार्गदर्शिका",
        "guide_desc": "**{room}** व्याकरण पर ध्यान केंद्रित करें। नीचे दिए गए बटन पर क्लिक करें!",
        "btn_q1": "🎯 मूल अर्थ", "btn_q2": "📝 3 उदाहरण", "btn_q3": "🤔 तुलना करें",
        "prompt_q1": "आसान तरीके से '{room}' के मूल अर्थ की व्याख्या करें।",
        "prompt_q2": "'{room}' का उपयोग करके 3 उदाहरण बनाएं।",
        "prompt_q3": "'{room}' के साथ भ्रमित व्याकरण की तुलना करें।",
        "error_quota": "⏳ शिक्षक को सोचने के लिए थोड़ा समय चाहिए! कृपया लगभग 20 सेकंड के बाद फिर से पूछें।"
    },
    "Italiano": {
        "main_title": "Benvenuti alla Clinica di Grammatica Coreana! 👋", "choose_lang": "🌐 Scegli la tua lingua",
        "nav_title": "📌 Menu", "menu_clinic": "📚 Home Clinica", "menu_board": "💬 Bacheca Comunità", "menu_history": "🏆 La mia Cronologia",
        "clinic": "Clinica", "select_room": "Argomenti di Grammatica", "input_prompt": "Inserisci la tua domanda...", 
        "no_files": "Nessun file di grammatica.", "error_key": "Chiave API mancante", "error_msg": "Errore",
        "welcome": "Ciao! Benvenuto nella **{room}**. Che domande hai oggi?", "loading": "Pensando...",
        "board_title": "Bacheca Comunità", "board_prompt": "Condividi le tue domande o feedback!", "board_btn": "Pubblica",
        "like": "👍 Mi piace", "comment_prompt": "Scrivi un commento...", "comment_btn": "Rispondi",
        "select_lang": "Seleziona lingua", "delete_btn": "🗑️ Elimina",
        "login_title": "🔐 Accedi / Registrati", "email": "Email", "pwd": "Password", "btn_login": "Accedi", "btn_signup": "Registrati", "btn_guest": "👤 Continua come ospite",
        "signup_agree": "Accetto la raccolta e l'uso delle informazioni personali (Obbligatorio)",
        "guest_agree": "Accetto la raccolta anonima dei registri di chat (Obbligatorio)",
        "agree_warn_signup": "Si prega di accettare l'informativa sulla privacy.",
        "agree_warn_guest": "Si prega di accettare la raccolta dei dati.",
        "chat_warn": "⚠️ NON inserire informazioni personali (nome, contatti, ecc.).",
        "history_desc": "Puoi vedere tutte le tue conversazioni a colpo d'occhio.",
        "history_search": "🔍 Cerca (Inserisci un argomento o una parola chiave)",
        "history_no_record": "Nessuna cronologia chat trovata. Lascia la tua prima domanda!",
        "history_no_result": "Nessun risultato di ricerca trovato per '{query}'.",
        "history_view": "🚪 Visualizza i record '{room}'", "history_me": "👤 Io", "history_teacher": "🤖 Insegnante",
        "guide_title": "📖 Guida e domande per '{room}'",
        "guide_desc": "Fai domande su **{room}**. Clicca sui pulsanti qui sotto!",
        "btn_q1": "🎯 Significato e regole", "btn_q2": "📝 Crea 3 esempi", "btn_q3": "🤔 Confronta grammatica",
        "prompt_q1": "Spiega il significato e le regole di '{room}' in modo facile.",
        "prompt_q2": "Crea 3 frasi di esempio usando '{room}'.",
        "prompt_q3": "Scegli 1 grammatica che si confonde con '{room}' e spiega la differenza.",
        "error_quota": "⏳ L'insegnante ha bisogno di un momento per pensare! Riprova tra circa 20 secondi."
    }
}

# 기본 세션 상태 정의
if "selected_lang" not in st.session_state:
    st.session_state.selected_lang = "한국어"
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# 현재 선택된 언어 사전 매핑
t = ui_texts[st.session_state.selected_lang]
lang_list = list(ui_texts.keys())

# ==========================================
# 🔓 비로그인 상태: 로그인 / 회원가입 / 비회원 접속 화면
# ==========================================
if st.session_state.user_email is None:
    st.title(t["main_title"]) 
    
    # 첫 화면 언어 선택 드롭다운 
    default_idx = lang_list.index(st.session_state.selected_lang)
    lang_choice = st.selectbox(t["choose_lang"], lang_list, index=default_idx)
    if lang_choice != st.session_state.selected_lang:
        st.session_state.selected_lang = lang_choice
        st.rerun()
        
    st.write("---")
    
    col1, col2, col3 = st.columns([1.6, 0.4, 2])
    with col1:
        st.subheader(t["login_title"])
        auth_email = st.text_input(t["email"], key="auth_email")
        auth_pwd = st.text_input(t["pwd"], type="password", key="auth_pwd")
        
        # 📝 회원가입용 필수 약관 체크박스
        signup_agree = st.checkbox(t["signup_agree"], key="signup_agree_key")
        
        btn_action1, btn_action2 = st.columns(2)
        
        # 🔑 로그인 인증 기능
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
                    
        # 📝 회원가입 데이터 수집 기능 (체크박스 검증)
        with btn_action2:
            if st.button(t["btn_signup"], use_container_width=True):
                if not signup_agree:
                    st.warning(t["agree_warn_signup"])
                elif auth_email and auth_pwd:
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
        
        st.write("<br><br><br>", unsafe_allow_html=True)
        st.write("---")
        
        # 👤 비회원 무기명 로그 수집 필수 약관 체크박스
        guest_agree = st.checkbox(t["guest_agree"], key="guest_agree_key")
        
        # 👤 비회원(Guest) 입장 처리 버튼
        if st.button(t["btn_guest"], use_container_width=True, type="primary"):
            if not guest_agree:
                st.warning(t["agree_warn_guest"])
            else:
                st.session_state.user_email = f"Guest_{str(uuid.uuid4())[:4]}"
                st.rerun()
            
    st.stop() 

# ==========================================
# 🔐 인증 완료 상태: 메인 대시보드 및 서비스 구동
# ==========================================

# 사이드바 프로필 및 로그아웃 처리
st.sidebar.markdown(f"👤 **{st.session_state.user_email}**")
if st.sidebar.button("Logout"):
    st.session_state.user_email = None
    st.session_state.is_admin = False
    st.rerun()

st.sidebar.divider()

# 사이드바 내부 언어 변경 연동
default_idx = lang_list.index(st.session_state.selected_lang)
selected_lang = st.sidebar.selectbox(t["choose_lang"], lang_list, index=default_idx)
if selected_lang != st.session_state.selected_lang:
    st.session_state.selected_lang = selected_lang
    st.rerun()

st.sidebar.divider()

# 메인 메뉴 탭 구성
nav_options = [t["menu_clinic"], t["menu_board"], t["menu_history"]] # 💡 다국어 변수로 교체 완료!
if st.session_state.is_admin:
    nav_options.append("📊 관리자 대시보드")

selected_main_nav = st.sidebar.radio(t["nav_title"], nav_options)
selected_display_name = None

# 로컬 교안 데이터 자동 연동 스캔
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

# 은밀한 관리자 활성화 인증 창
st.sidebar.markdown("<br>" * 4, unsafe_allow_html=True) 
if not st.session_state.is_admin:
    admin_pwd = st.sidebar.text_input("admin_hidden", type="password", placeholder="🔒", label_visibility="collapsed")
    if admin_pwd == ADMIN_PASSWORD:
        st.session_state.is_admin = True
        st.rerun()
else:
    st.sidebar.caption("🔓 Admin Active")

# --- 각 메뉴별 메인 비즈니스 로직 렌더링 ---

# 0. 🏆 내 학습 기록 (마이페이지) 로직
if selected_main_nav == t["menu_history"]: 
    st.title(t["menu_history"])
    st.write(t["history_desc"])
    
    # 🔍 검색창 추가 (다국어화 완료)
    search_query = st.text_input(t["history_search"], "")
    
    # Firestore에서 내 대화 기록 싹 다 가져오기
    chats_ref = db.collection("chats").stream()
    my_chats = []
    
    for doc in chats_ref:
        if doc.id.startswith(f"{st.session_state.user_email}_"):
            room_name = doc.id.replace(f"{st.session_state.user_email}_", "")
            my_chats.append({"room": room_name, "messages": doc.to_dict().get("messages", [])})
            
    if not my_chats:
        st.info(t["history_no_record"])
    else:
        filtered_chats = []
        for chat in my_chats:
            if not search_query:
                filtered_chats.append(chat)
            else:
                is_match = search_query.lower() in chat['room'].lower()
                if not is_match:
                    for msg in chat['messages']:
                        if search_query.lower() in msg['content'].lower():
                            is_match = True
                            break
                if is_match:
                    filtered_chats.append(chat)
        
        if not filtered_chats:
            st.warning(t["history_no_result"].format(query=search_query))
        else:
            import re
            for chat in filtered_chats:
                with st.expander(t["history_view"].format(room=chat['room']), expanded=True if search_query else False):
                    for msg in chat['messages']:
                        display_content = msg['content']
                        
                        if search_query:
                            escaped_search = re.escape(search_query)
                            display_content = re.sub(
                                f"({escaped_search})", 
                                r"<mark style='background-color: #FFEB3B; color: black; font-weight: bold; padding: 1px 3px; border-radius: 3px;'>\1</mark>", 
                                display_content, 
                                flags=re.IGNORECASE
                            )
                        
                        if msg["role"] == "user":
                            st.markdown(f"**{t['history_me']}:** {display_content}", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**{t['history_teacher']}:** {display_content}", unsafe_allow_html=True)
                            st.divider()
        
        # 필터링된 결과 화면에 뿌려주기
        if not filtered_chats:
            st.warning(f"'{search_query}'에 대한 검색 결과가 없습니다.")
        else:
            import re  # 💡 단어 치환 및 강조를 위한 파이썬 정규표현식 모듈 임포트
            
            for chat in filtered_chats:
                with st.expander(f"🚪 '{chat['room']}' 클리닉 기록 보기", expanded=True if search_query else False):
                    for msg in chat['messages']:
                        display_content = msg['content']
                        
                        # 💡 검색어가 입력되어 있다면, 본문 안에서 해당 단어를 찾아 형광펜(<mark>) 처리!
                        if search_query:
                            escaped_search = re.escape(search_query) # 특수문자 예외 처리
                            # 원본 글자 케이스(대소문자 등)를 유지하면서 노란색 마킹 스타일 적용
                            display_content = re.sub(
                                f"({escaped_search})", 
                                r"<mark style='background-color: #FFEB3B; color: black; font-weight: bold; padding: 1px 3px; border-radius: 3px;'>\1</mark>", 
                                display_content, 
                                flags=re.IGNORECASE
                            )
                        
                        # HTML 마킹 태그를 인식할 수 있도록 unsafe_allow_html=True 옵션 추가
                        if msg["role"] == "user":
                            st.markdown(f"**👤 나:** {display_content}", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**🤖 선생님:** {display_content}", unsafe_allow_html=True)
                            st.divider()
                            
# 1. 📊 관리자 대시보드 로직 (표 형태로 UI 업그레이드!)
if selected_main_nav == "📊 관리자 대시보드" and st.session_state.is_admin:
    st.title("📊 실시간 이용 통계 및 로그 (Firestore)")
    
    logs_ref = db.collection("logs").order_by("time", direction=firestore.Query.DESCENDING).stream()
    logs_list = [doc.to_dict() for doc in logs_ref]
    
    st.metric(label="총 누적 질문 수", value=f"{len(logs_list)} 회")
    st.divider()
    
    st.subheader("📝 상세 질문 로그 데이터")
    
    if logs_list:
        # 데이터프레임(표) 형태로 깔끔하게 렌더링
        st.dataframe(
            logs_list,
            column_config={
                "time": st.column_config.TextColumn("⏰ 질문 시간", width="medium"),
                "user": st.column_config.TextColumn("👤 사용자(이메일/게스트)", width="medium"),
                "lang": st.column_config.TextColumn("🌐 언어", width="small"),
                "room": st.column_config.TextColumn("🚪 문법 주제", width="small"),
                "prompt": st.column_config.TextColumn("💬 질문 내용", width="large")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("아직 수집된 질문 데이터가 없습니다.")

# 2. 📢 실시간 커뮤니티 게시판 로직
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

# 3. 🚪 문법 클리닉 챗봇 엔진 로직 (개인정보 수집 동의 고지 완료 및 기록 암묵적 무한 영구 저장)
elif selected_main_nav == t["menu_clinic"] and selected_display_name:
    actual_room_name = selected_display_name.replace("&nbsp;", "").strip()
    st.title(f"🚪 {actual_room_name}")
    
    selected_meta_word = actual_room_name.replace(f" {t['clinic']}", "")
    
    with open(f"grammar_data/{selected_meta_word}.txt", "r", encoding="utf-8") as file:
        target_rules = file.read()

   # ==========================================
    # 💡 [1단계 적용] 방 사용 가이드 및 예상 질문 칩 (다국어 완벽 적용)
    # ==========================================
    with st.expander(t["guide_title"].format(room=selected_meta_word), expanded=True):
        st.markdown(t["guide_desc"].format(room=selected_meta_word))
        
        col1, col2, col3 = st.columns(3)
        suggested_q = None
        
        if col1.button(t["btn_q1"], use_container_width=True):
            suggested_q = t["prompt_q1"].format(room=selected_meta_word)
        if col2.button(t["btn_q2"], use_container_width=True):
            suggested_q = t["prompt_q2"].format(room=selected_meta_word)
        if col3.button(t["btn_q3"], use_container_width=True):
            suggested_q = t["prompt_q3"].format(room=selected_meta_word)
    # ==========================================
    # ==========================================

    # 각 개인 유저 이메일/게스트 ID 기반의 Firestore 개인 대화 백업 세션 로드
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

    # 💡 개인정보 입력 절대 금지 안내 자막 실시간 다국어 출력 
    st.caption(t["chat_warn"])
    
    # 💡 추천 질문 버튼을 눌렀거나(suggested_q), 직접 텍스트를 입력했을 때(user_input) 둘 다 정상 작동하도록 설계
    user_input = st.chat_input(t["input_prompt"])
    prompt = suggested_q or user_input
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
            
        # 📊 중앙 대시보드 집계용 글로벌 로그 기록 누적 (Firestore)
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
            5. 💡 답변의 맨 마지막에는 반드시 '**💡 더 알아보면 좋은 개념**'이라는 소제목을 달고, 현재 설명한 내용과 연관된 심화 문법이나 비교해서 알아두면 좋은 다른 문법 1~2가지를 짧게 추천하여 추가 학습을 유도하세요.
            
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
                    # 실시간 대화 상태 변경 후 Firestore 원격 백업 갱신
                    db.collection("chats").document(chat_doc_id).set({"messages": st.session_state.messages})
                    
            except Exception as e:
                # 💡 [버그 픽스] 에러 발생 시 방금 들어간 질문을 타임머신처럼 취소(삭제)해서 버튼 먹통 방지!
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                    st.session_state.messages.pop() 
                    db.collection("chats").document(chat_doc_id).set({"messages": st.session_state.messages}) 

                error_msg = str(e)
                with st.chat_message("assistant"):
                    if "429" in error_msg or "quota" in error_msg.lower():
                        # 💡 길고 지저분했던 if문 다 지우고, 다국어 사전에 만들어둔 키값으로 한 방에 연동!
                        st.warning(t["error_quota"]) 
                    else:
                        st.error(f"{t['error_msg']}: {error_msg}")
