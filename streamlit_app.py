import streamlit as st
import json
import random
import html

st.set_page_config(page_title="Ochrona sygnalistów - Quiz", page_icon="🎓", layout="wide")

# --- CSS i stylizacja ---
# Wstrzyknięcie własnego CSS, aby nadać aplikacji nowoczesny, "SaaS-owy" wygląd.
# Używamy zmiennych CSS dla łatwiejszej zmiany kolorów.
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --primary-color: #2563EB; /* Niebieski 'korpo' */
        --secondary-color: #1E293B; /* Ciemny szary/granat */
        --accent-color: #10B981; /* Zielony akcent */
        --text-color: #334155;
        --bg-color: #F8FAFC;
        --card-bg: #FFFFFF;
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Tło aplikacji */
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
    }

    /* Nagłówek i Sidebar */
    [data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #E2E8F0;
    }
    
    h1, h2, h3 {
        color: var(--secondary-color);
        font-weight: 700;
    }

    /* Karty (Cards) */
    .stCard {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 24px;
        box-shadow: var(--shadow-md);
        margin-bottom: 24px;
        border: 1px solid #E2E8F0;
    }

    /* Przyciski */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Usuwamy domyślne menu Streamlit dla czystszego wyglądu (opcjonalne) */
    /* #MainMenu {visibility: hidden;} */
    /* footer {visibility: hidden;} */
</style>
""", unsafe_allow_html=True)

# --- Stała z nazwą pliku ---
LOCAL_QUESTIONS_FILE = "baza_pytan.json"

# --- Funkcje (wczytywanie, logika) ---
@st.cache_data
def load_questions_from_local_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, None
    except FileNotFoundError:
        return None, f"Błąd: Nie znaleziono pliku '{filepath}'."
    except json.JSONDecodeError:
        return None, f"Błąd: Nie można przetworzyć pliku JSON ('{filepath}')."

def initialize_session_state():
    if 'screen' not in st.session_state:
        st.session_state.screen = 'menu'
    if 'incorrect_ids' not in st.session_state:
        st.session_state.incorrect_ids = set()
    if 'last_session_mistakes' not in st.session_state:
        st.session_state.last_session_mistakes = []
    if 'question_results' not in st.session_state:
        st.session_state.question_results = []
    if 'quiz_scope_name' not in st.session_state:
        st.session_state.quiz_scope_name = "Pełny quiz"
    # Inicjalizacja domyślnych wartości jeśli nie istnieją
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'newly_incorrect_count' not in st.session_state:
        st.session_state.newly_incorrect_count = 0 
    if 'questions_to_ask' not in st.session_state:
        st.session_state.questions_to_ask = []

class QuizLogic:
    def __init__(self, questions_list):
        self.questions = questions_list


def is_multi_answer(question):
    return len(question.get("correct_answers", [])) > 1


def format_answer_letters(answers):
    return ", ".join(answer.upper() for answer in sorted(answers))


def get_question_stats(questions):
    total = len(questions)
    multi = sum(1 for question in questions if is_multi_answer(question))
    single = total - multi
    return total, single, multi


def filter_questions(questions, query="", answer_filter="Wszystkie", review_ids=None):
    review_ids = review_ids or set()
    normalized_query = query.strip().lower()
    filtered = []

    for question in questions:
        searchable = " ".join(
            [question["text"], *question.get("options", {}).values()]
        ).lower()
        if normalized_query and normalized_query not in searchable:
            continue
        if answer_filter == "Jedna poprawna" and is_multi_answer(question):
            continue
        if answer_filter == "Wiele poprawnych" and not is_multi_answer(question):
            continue
        if answer_filter == "Do powtórki" and question["id"] not in review_ids:
            continue
        filtered.append(question)

    return filtered


def start_quiz(quiz_logic, review_only=False, num_questions=None, question_pool=None, scope_name=None):
    st.session_state.score = 0
    st.session_state.current_question_index = 0
    st.session_state.newly_incorrect_count = 0
    st.session_state.last_session_mistakes = []
    st.session_state.question_results = []
    st.session_state.answer_submitted = False
    st.session_state.score_calculated = False
    st.session_state.user_selection = []
    
    if question_pool is not None:
        questions_pool = question_pool[:]
        st.session_state.quiz_scope_name = scope_name or "Quiz celowany"
    elif review_only:
        incorrect_ids_in_session = st.session_state.get('incorrect_ids', set())
        if not incorrect_ids_in_session:
            st.toast("Brak pytań do powtórki.", icon="🎉")
            return
        questions_pool = [q for q in quiz_logic.questions if q["id"] in incorrect_ids_in_session]
        st.session_state.quiz_scope_name = "Powtórka błędów"
    elif num_questions:
        questions_pool = random.sample(quiz_logic.questions, min(num_questions, len(quiz_logic.questions)))
        st.session_state.quiz_scope_name = f"Losowy quiz ({len(questions_pool)} pytań)"
    else:
        questions_pool = quiz_logic.questions[:]
        st.session_state.quiz_scope_name = "Pełny quiz"

    if not questions_pool:
        st.error("Wystąpił błąd przy tworzeniu puli pytań.")
        return

    random.shuffle(questions_pool)
    st.session_state.questions_to_ask = questions_pool
    st.session_state.screen = 'quiz'

# --- Ekrany ---

def sidebar_status():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2641/2641457.png", width=64) # Generyczna ikona dokumentu/prawa
        st.title("Panel Kontrolny")
        
        if st.session_state.screen == 'quiz':
            total = len(st.session_state.questions_to_ask)
            current = st.session_state.current_question_index + 1
            progress = st.session_state.current_question_index / total if total > 0 else 0
            
            st.caption(st.session_state.get("quiz_scope_name", "Quiz"))
            st.markdown(f"**Postęp:** {current}/{total}")
            st.progress(progress)
            
            st.markdown(f"**Wynik:** {st.session_state.score}")
            st.markdown("---")
            if st.button("Przerwij Quiz", use_container_width=True, type="secondary"):
                st.session_state.screen = 'menu'
                st.rerun()
        else:
            st.markdown("Witaj w systemie testowym Ochrona sygnalistów.")
            st.markdown("Wybierz tryb quizu z menu głównego.")

            incorrect_cnt = len(st.session_state.get('incorrect_ids', set()))
            quiz_logic = st.session_state.get("quiz_logic_ref")
            if quiz_logic:
                total, single, multi = get_question_stats(quiz_logic.questions)
                st.markdown("---")
                st.metric("Pytania w bazie", total)
                st.caption(f"{single} jednokrotnego wyboru · {multi} wielokrotnego wyboru")
            if incorrect_cnt > 0:
                st.warning(f"Masz {incorrect_cnt} pytań do powtórki.")

def show_main_menu(quiz_logic):
    st.title("📚 Ochrona sygnalistów - Quiz Wiedzy")
    st.markdown("Wybierz tryb nauki albo szybko przejrzyj bazę pytań.")

    total, single, multi = get_question_stats(quiz_logic.questions)
    review_count = len(st.session_state.get('incorrect_ids', set()))
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    stat_col1.metric("Pytania", total)
    stat_col2.metric("Jedna odpowiedź", single)
    stat_col3.metric("Wiele odpowiedzi", multi)
    stat_col4.metric("Do powtórki", review_count)

    quiz_tab, browser_tab = st.tabs(["Quiz", "Przegląd bazy"])

    with quiz_tab:
        # Kontener główny - Karta
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
    
        col1, col2 = st.columns(2)
    
        with col1:
            st.info("💡 **Pełny Test**\n\nPrzejdź przez wszystkie dostępne pytania w bazie.")
            if st.button("Rozpocznij Pełny Quiz", use_container_width=True, type="primary"):
                start_quiz(quiz_logic)
                st.rerun()

        with col2:
            st.success("🎲 **Szybki Losowy**\n\nWylosuj określoną liczbę pytań na rozgrzewkę.")
            with st.form("random_quiz_form", border=False):
                num = st.number_input("Liczba pytań", min_value=1, max_value=len(quiz_logic.questions), value=10, step=1, label_visibility="collapsed")
                if st.form_submit_button("Start Losowy", use_container_width=True):
                    start_quiz(quiz_logic, num_questions=num)
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("🎯 Quiz celowany")
        with st.form("targeted_quiz_form", border=False):
            target_filter = st.selectbox(
                "Zakres",
                ["Wiele poprawnych", "Jedna poprawna", "Do powtórki"],
                help="Wybierz typ pytań, które chcesz ćwiczyć.",
            )
            target_pool = filter_questions(
                quiz_logic.questions,
                answer_filter=target_filter,
                review_ids=st.session_state.get("incorrect_ids", set()),
            )
            target_count = st.number_input(
                "Liczba pytań",
                min_value=1,
                max_value=max(1, len(target_pool)),
                value=min(10, max(1, len(target_pool))),
                step=1,
                disabled=not target_pool,
            )
            submitted = st.form_submit_button("Start Celowany", use_container_width=True)
            if submitted:
                if not target_pool:
                    st.warning("Brak pytań dla wybranego zakresu.")
                else:
                    selected_pool = random.sample(target_pool, min(target_count, len(target_pool)))
                    start_quiz(
                        quiz_logic,
                        question_pool=selected_pool,
                        scope_name=f"Quiz celowany: {target_filter}",
                    )
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
        # Karta powtórek (tylko jeśli są błędy)
        if review_count > 0:
            st.markdown('<div class="stCard" style="border-left: 5px solid #F59E0B;">', unsafe_allow_html=True)
            st.subheader("🔁 Powtórki")
            st.write(f"Zgromadziłeś **{review_count}** pytań, na które udzielono błędnej odpowiedzi.")
            if st.button("Rozpocznij Sesję Powtórkową", use_container_width=True, type="secondary"):
                 start_quiz(quiz_logic, review_only=True)
                 st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with browser_tab:
        show_question_browser(quiz_logic)


def show_question_browser(quiz_logic):
    review_ids = st.session_state.get("incorrect_ids", set())
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("Szukaj", placeholder="np. RPO, zgłoszenie zewnętrzne, działania odwetowe")
    with col2:
        answer_filter = st.selectbox(
            "Filtr",
            ["Wszystkie", "Jedna poprawna", "Wiele poprawnych", "Do powtórki"],
        )

    filtered = filter_questions(
        quiz_logic.questions,
        query=query,
        answer_filter=answer_filter,
        review_ids=review_ids,
    )

    result_col1, result_col2, result_col3 = st.columns(3)
    result_col1.metric("Wyniki", len(filtered))
    result_col2.metric("Wielokrotne", sum(1 for question in filtered if is_multi_answer(question)))
    result_col3.metric("W powtórkach", sum(1 for question in filtered if question["id"] in review_ids))

    if filtered:
        quiz_size = st.slider(
            "Liczba pytań do quizu z wyników",
            min_value=1,
            max_value=len(filtered),
            value=min(10, len(filtered)),
        )
        if st.button("Start Quizu z Wyników", use_container_width=True, type="primary"):
            selected_pool = random.sample(filtered, quiz_size)
            start_quiz(
                quiz_logic,
                question_pool=selected_pool,
                scope_name="Quiz z przeglądu bazy",
            )
            st.rerun()
    else:
        st.info("Brak pytań pasujących do filtrów.")
        return

    st.divider()
    for question in filtered[:20]:
        preview = question["text"][:90] + ("..." if len(question["text"]) > 90 else "")
        label = f"#{question['id']} · {preview}"
        with st.expander(label):
            st.write(question["text"])
            for key, value in sorted(question["options"].items()):
                marker = "✅" if key in question["correct_answers"] else "•"
                st.markdown(f"{marker} **{key.upper()}**. {value}")
            st.caption(f"Poprawne odpowiedzi: {format_answer_letters(question['correct_answers'])}")

    if len(filtered) > 20:
        st.caption(f"Pokazano pierwsze 20 z {len(filtered)} wyników.")


def show_question_screen():
    q_list = st.session_state.questions_to_ask
    index = st.session_state.current_question_index
    q = q_list[index]
    correct_count = len(q["correct_answers"])
    escaped_question = html.escape(q["text"])
    
    # Custom Question Card
    st.markdown(f"""
    <div class="stCard">
        <h3 style="margin-top: 0;">Pytanie {index + 1} z {len(q_list)}</h3>
        <p style="color: #64748B; margin-bottom: 12px;">ID #{q['id']} · zaznacz {correct_count} {"odpowiedź" if correct_count == 1 else "odpowiedzi"}</p>
        <p style="font-size: 1.2rem; font-weight: 500; color: #1E293B;">{escaped_question}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Options
    options = {f"{key}) {value}": key for key, value in sorted(q["options"].items())}
    
    st.markdown("##### Wybierz odpowiedź:")
    user_selection_keys = []
    
    # Używamy kontenera, aby opcje były ładnie zgrupowane
    with st.container():
        for label, key in options.items():
            # Checkbox jest trudny do ostylowania w CSS Streamlit, ale standardowy wygląda OK z customowym fontem
            if st.checkbox(label, key=f"cb_{key}_{q['id']}", disabled=st.session_state.answer_submitted):
                user_selection_keys.append(key)
    
    st.session_state.user_selection = user_selection_keys
    
    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        if not st.session_state.answer_submitted:
            if st.button("Sprawdź odpowiedź", use_container_width=True, type="primary"):
                st.session_state.answer_submitted = True
                st.rerun()
        else:
            if st.button("Następne pytanie ➡️", use_container_width=True, type="primary"):
                if index + 1 < len(q_list):
                    st.session_state.current_question_index += 1
                    st.session_state.answer_submitted = False
                    st.session_state.score_calculated = False
                    st.rerun()
                else:
                    st.session_state.screen = 'summary'
                    st.rerun()

    # Logika sprawdzania (naliczanie punktów)
    if st.session_state.answer_submitted and not st.session_state.score_calculated:
        user_answers = set(st.session_state.user_selection)
        correct_answers = set(q["correct_answers"])
        is_correct = user_answers == correct_answers
        
        st.session_state.question_results.append({
            "question": q,
            "user_answers": sorted(user_answers),
            "correct_answers": sorted(correct_answers),
            "is_correct": is_correct,
        })
        
        if is_correct:
            st.session_state.score += 1
            st.session_state.incorrect_ids.discard(q["id"])
        else:
            st.session_state.newly_incorrect_count += 1
            st.session_state.last_session_mistakes.append({
                "question": q,
                "user_answers": sorted(user_answers),
                "correct_answers": sorted(correct_answers),
            })
            st.session_state.incorrect_ids.add(q["id"])
        
        st.session_state.score_calculated = True

    # Wyświetlanie feedbacku
    if st.session_state.answer_submitted:
        user_answers = set(st.session_state.user_selection)
        correct_answers = set(q["correct_answers"])
        
        # Mapa liter na pełne treści
        correct_option_texts = [f"{k}) {q['options'][k]}" for k in sorted(correct_answers)]
        
        st.markdown("<br>", unsafe_allow_html=True) # Spacer
        
        if user_answers == correct_answers:
            st.success("✅ **Świetnie!** To jest poprawna odpowiedź.")
        else:
            st.error(f"❌ **Błąd.** Prawidłowa odpowiedź to:")
            for txt in correct_option_texts:
                st.markdown(f"- {txt}")


def show_summary_screen():
    st.balloons()
    
    st.markdown('<div class="stCard" style="text-align: center;">', unsafe_allow_html=True)
    st.title("🎉 Koniec Quizu")
    
    total = len(st.session_state.questions_to_ask)
    score = st.session_state.score
    percentage = (score / total) * 100 if total > 0 else 0
    
    mistakes = st.session_state.get("last_session_mistakes", [])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Wynik", f"{score}/{total}")
    col2.metric("Skuteczność", f"{percentage:.1f}%")
    col3.metric("Błędy w sesji", len(mistakes))
    
    st.markdown('</div>', unsafe_allow_html=True)

    if mistakes:
        st.subheader("Pytania do poprawki")
        for item in mistakes:
            question = item["question"]
            with st.expander(f"#{question['id']} · {question['text'][:90]}"):
                st.write(question["text"])
                user_answers = format_answer_letters(item["user_answers"]) or "brak"
                correct_answers = format_answer_letters(item["correct_answers"])
                st.warning(f"Twoja odpowiedź: {user_answers}")
                st.success(f"Poprawna odpowiedź: {correct_answers}")
                for key, value in sorted(question["options"].items()):
                    marker = "✅" if key in item["correct_answers"] else "•"
                    st.markdown(f"{marker} **{key.upper()}**. {value}")
    else:
        st.success("Bez błędów w tej sesji.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Wróć do menu", use_container_width=True):
            st.session_state.screen = 'menu'
            st.rerun()
    with col2:
        if mistakes:
            if st.button("🔄 Powtórz błędne z tej sesji", use_container_width=True, type="primary"):
                 mistake_questions = [item["question"] for item in mistakes]
                 start_quiz(
                     quiz_logic=st.session_state.get('quiz_logic_ref'),
                     question_pool=mistake_questions,
                     scope_name="Powtórka błędów z sesji",
                 )
                 st.rerun()


questions_data, error_message = load_questions_from_local_file(LOCAL_QUESTIONS_FILE)

if error_message:
    st.error(error_message)
    st.stop()

initialize_session_state()
quiz_logic = QuizLogic(questions_list=questions_data)
# Hack, żeby mieć dostęp do quiz_logic w przyciskach wewnątrz funkcji
st.session_state.quiz_logic_ref = quiz_logic 

sidebar_status()

if st.session_state.screen == 'menu':
    show_main_menu(quiz_logic)
elif st.session_state.screen == 'quiz':
    show_question_screen()
elif st.session_state.screen == 'summary':
    show_summary_screen()
