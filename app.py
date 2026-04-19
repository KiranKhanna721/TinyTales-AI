import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import base64
import time
import re
import json
#

# ── Retry helper ──────────────────────────────────────────────────────────────
def retry_with_backoff(fn, max_retries=8, base_delay=20):
    """Call fn(); on 429 wait and retry with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                m = re.search(r"retryDelay.*?(\d+)s", msg)
                wait = int(m.group(1)) + 5 if m else base_delay * (2 ** attempt)
                wait = min(wait, 120)
                st.toast(f"⏳ Rate limited — retrying in {wait}s (attempt {attempt+1}/{max_retries})", icon="⏳")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Still rate-limited after {max_retries} retries. Try a fresh API key or enable billing at aistudio.google.com.")

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StoryCanvas",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:ital,wght@0,400;0,500;1,400&display=swap');

/* Root theme */
:root {
    --cream: #fdf6ec;
    --parchment: #f5e6c8;
    --ink: #2c1810;
    --rust: #c0612b;
    --gold: #d4a017;
    --sage: #6b7c5c;
    --shadow: rgba(44,24,16,0.15);
}

/* Global */
html, body, [class*="css"] {
    font-family: 'Lora', Georgia, serif;
    background-color: var(--cream);
    color: var(--ink);
}

/* Hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1100px; margin: 0 auto; }

/* ── Hero header ── */
.hero {
    text-align: center;
    padding: 3.5rem 1rem 2rem;
    position: relative;
}
.hero-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 4.2rem;
    font-weight: 700;
    color: var(--ink);
    letter-spacing: -1px;
    line-height: 1.1;
    margin: 0;
}
.hero-title span { color: var(--rust); font-style: italic; }
.hero-subtitle {
    font-family: 'Lora', serif;
    font-size: 1.1rem;
    color: var(--sage);
    margin-top: 0.75rem;
    font-style: italic;
    letter-spacing: 0.3px;
}
.hero-divider {
    width: 80px;
    height: 3px;
    background: linear-gradient(90deg, var(--rust), var(--gold));
    margin: 1.5rem auto 0;
    border-radius: 2px;
}

/* ── Prompt form ── */
.prompt-card {
    background: white;
    border: 1.5px solid var(--parchment);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    box-shadow: 0 4px 24px var(--shadow);
    margin: 2rem 0;
}
.prompt-label {
    font-family: 'Playfair Display', serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--ink);
    margin-bottom: 0.5rem;
}

/* Streamlit input overrides */
.stTextArea textarea {
    font-family: 'Lora', serif !important;
    font-size: 1rem !important;
    border: 1.5px solid var(--parchment) !important;
    border-radius: 10px !important;
    background: var(--cream) !important;
    color: var(--ink) !important;
    padding: 1rem !important;
    resize: none;
}
.stTextArea textarea:focus {
    border-color: var(--rust) !important;
    box-shadow: 0 0 0 3px rgba(192,97,43,0.12) !important;
}

/* Select box */
.stSelectbox > div > div {
    font-family: 'Lora', serif !important;
    border-color: var(--parchment) !important;
    background: var(--cream) !important;
}

/* Generate button */
.stButton > button {
    font-family: 'Playfair Display', serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, var(--rust), #a0451e) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.75rem 2.5rem !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 4px 14px rgba(192,97,43,0.35) !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(192,97,43,0.45) !important;
}

/* ── Book pages ── */
.book-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: var(--ink);
    text-align: center;
    margin: 2.5rem 0 0.5rem;
    font-style: italic;
}
.book-subtitle {
    text-align: center;
    color: var(--sage);
    font-size: 0.9rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 2.5rem;
}

.page-spread {
    display: flex;
    gap: 2rem;
    align-items: stretch;
    background: white;
    border-radius: 18px;
    border: 1.5px solid var(--parchment);
    box-shadow: 0 6px 32px var(--shadow);
    overflow: hidden;
    margin-bottom: 2.5rem;
    min-height: 340px;
}
.page-spread.reversed { flex-direction: row-reverse; }

.page-image {
    flex: 0 0 45%;
    position: relative;
    overflow: hidden;
}
.page-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

.page-text-side {
    flex: 1;
    padding: 2.5rem 2rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
}
.page-number {
    font-family: 'Playfair Display', serif;
    font-size: 0.75rem;
    color: var(--gold);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.page-text {
    font-family: 'Lora', serif;
    font-size: 1.08rem;
    line-height: 1.9;
    color: var(--ink);
}
.page-text::first-letter {
    font-family: 'Playfair Display', serif;
    font-size: 3.2rem;
    font-weight: 700;
    color: var(--rust);
    float: left;
    line-height: 0.75;
    margin: 0.1em 0.1em 0 0;
}
.page-corner {
    position: absolute;
    bottom: 1rem;
    right: 1.5rem;
    font-size: 1.4rem;
    opacity: 0.18;
}

/* ── Progress ── */
.progress-label {
    font-family: 'Lora', serif;
    font-size: 0.95rem;
    color: var(--sage);
    font-style: italic;
    text-align: center;
    margin-top: 0.4rem;
}

/* ── Tips sidebar ── */
.tip-box {
    background: var(--parchment);
    border-left: 4px solid var(--gold);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-top: 1.5rem;
    font-size: 0.88rem;
    color: var(--ink);
    line-height: 1.6;
}
.tip-box strong {
    font-family: 'Playfair Display', serif;
    color: var(--rust);
    display: block;
    margin-bottom: 0.3rem;
}

/* ── End ornament ── */
.end-ornament {
    text-align: center;
    font-size: 1.6rem;
    margin: 1.5rem 0 3rem;
    opacity: 0.4;
    letter-spacing: 8px;
}

/* ── Error box ── */
.stAlert { border-radius: 10px !important; font-family: 'Lora', serif !important; }

/* ── Field labels ── */
.field-label {
    font-family: 'Lora', serif;
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--ink);
    margin: 0.9rem 0 0.2rem;
}
.required { color: var(--rust); font-size: 0.75rem; }
.optional { color: var(--sage); font-size: 0.72rem; font-style: italic; }

/* ── Full story text block ── */
.story-full {
    background: white;
    border: 1.5px solid var(--parchment);
    border-radius: 16px;
    padding: 2.5rem 3rem;
    box-shadow: 0 4px 24px var(--shadow);
    margin: 2rem 0;
}
.story-page-text {
    margin-bottom: 1.8rem;
    padding-bottom: 1.8rem;
    border-bottom: 1px dashed var(--parchment);
}
.story-page-text:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}
.story-page-label {
    font-family: 'Playfair Display', serif;
    font-size: 0.7rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--gold);
    display: block;
    margin-bottom: 0.5rem;
}
.story-body {
    font-family: 'Lora', serif;
    font-size: 1.08rem;
    line-height: 1.9;
    color: var(--ink);
    margin: 0;
}
.story-body::first-letter {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 700;
    color: var(--rust);
    float: left;
    line-height: 0.75;
    margin: 0.1em 0.1em 0 0;
}

/* ── Section divider ── */
.section-divider {
    text-align: center;
    font-family: 'Playfair Display', serif;
    font-size: 1rem;
    color: var(--sage);
    letter-spacing: 4px;
    margin: 2.5rem 0 2rem;
    text-transform: uppercase;
}

/* ── Illustration section ── */
.illus-label {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--rust);
    margin-bottom: 0.75rem;
    letter-spacing: 0.5px;
}
.illus-caption {
    font-family: 'Lora', serif;
    font-size: 1rem;
    line-height: 1.8;
    color: var(--ink);
    background: white;
    border-left: 3px solid var(--gold);
    padding: 1rem 1.5rem;
    border-radius: 0 8px 8px 0;
    margin-top: 1rem;
    font-style: italic;
}
.illus-placeholder {
    background: var(--parchment);
    border-radius: 12px;
    padding: 3rem;
    text-align: center;
    font-family: 'Lora', serif;
    color: var(--sage);
    font-size: 1rem;
}
.illus-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--parchment), transparent);
    margin: 2.5rem 0;
}
</style>
""", unsafe_allow_html=True)


# ── Helper: configure Gemini ──────────────────────────────────────────────────
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


# ── Helper: generate story pages ─────────────────────────────────────────────
def generate_story_pages(client: genai.Client, prompt: str, num_pages: int, age_group: str,
                          characters: str = "", genre: str = "", tone: str = "",
                          setting: str = "", extra: str = "") -> list[dict]:
    """Call Gemini to produce page text + an image prompt for each page."""
    age_instructions = {
        "Toddler (2–4)": "very simple words, short sentences, repetition, lots of action sounds",
        "Early reader (5–7)": "simple but vivid language, short paragraphs, relatable emotions",
        "Middle grade (8–11)": "richer vocabulary, deeper emotions, a clear story arc",
    }
    style = age_instructions.get(age_group, "simple but vivid language")

    # Build optional context block
    context_parts = []
    if characters.strip():
        context_parts.append(f"CHARACTERS: {characters.strip()}")
    if genre.strip() and genre != "— None —":
        context_parts.append(f"GENRE: {genre}")
    if tone.strip() and tone != "— None —":
        context_parts.append(f"TONE: {tone}")
    if setting.strip():
        context_parts.append(f"SETTING: {setting.strip()}")
    if extra.strip():
        context_parts.append(f"EXTRA REQUIREMENTS: {extra.strip()}")
    context_block = "\n".join(context_parts)

    system = (
        "You are a children's book author. Write a " + str(num_pages) + "-page illustrated story.\n"
        "Style guide: " + style + ".\n"
        + context_block + "\n"
        "Return ONLY a JSON array with " + str(num_pages) + " objects, each having:\n"
        '  \"page\": page number (int)\n'
        '  \"text\": 8-10 rich descriptive sentences of story text per page. Write the full passage, do not cut short.\n'
        '  \"image_prompt\": a detailed watercolour illustration prompt including: '
        "(1) hero/main character with clear physical description matching character details provided, "
        "(2) the challenge or action on this page, "
        "(3) the setting/environment in vivid detail. Warm palette, no text, no letters in image.\n"
        "No markdown, no extra keys. Pure JSON array only. Every page text field must be complete."
    )

    def _call():
        return client.models.generate_content(
            model="gemini-3-flash-preview",
            contents="Story idea: " + prompt + "\n\nGenerate the " + str(num_pages) + "-page children's book now.",
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.9,
                max_output_tokens=16384,
            ),
        )

    resp = retry_with_backoff(_call)
    raw = resp.text.strip()

    # Strip markdown fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw).strip()

    # Try to parse; if truncated attempt recovery by appending closing brackets
    pages = None
    for suffix in ["", "}]", "}]}]", "]"]:
        try:
            pages = json.loads(raw + suffix)
            if suffix:
                st.toast("Story JSON was truncated - recovered partial content.", icon="warning")
            break
        except json.JSONDecodeError:
            continue

    if pages is None:
        st.error("Could not parse story JSON. Raw response: " + raw[:500])
        st.stop()

    # Ensure every page has image_prompt; fallback to text if missing
    import html as html_lib
    for page in pages:
        if not page.get("image_prompt"):
            page["image_prompt"] = "Children's book illustration: " + page.get("text", "")[:200]
        if "text" in page:
            page["text"] = html_lib.escape(page["text"])

    return pages


# ── Helper: generate illustration ────────────────────────────────────────────
def generate_illustration(client: genai.Client, image_prompt: str) -> Image.Image | None:
    """Call Nano Banana Pro (gemini-3-pro-image-preview) - direct call, no wrapper."""
    prompt_text = "Children's book illustration, watercolour style, warm soft colours, no text, no letters: " + image_prompt
    st.write("🖌️ Sending prompt to Nano Banana Pro...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt_text],
    )

    for part in response.parts:
        if part.inline_data is not None:
            return part.as_image()

    # Nothing came back - show what the model returned for debugging
    texts = [p.text for p in response.parts if p.text]
    st.error("No image in response. Model said: " + str(texts[:2]))
    return None


# ── Helper: image → base64 for HTML ──────────────────────────────────────────
def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── Helper: placeholder SVG ──────────────────────────────────────────────────
PLACEHOLDER_SVG = """<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'>
  <rect width='400' height='300' fill='#f5e6c8'/>
  <text x='50%' y='48%' font-family='Georgia' font-size='18' fill='#c0612b' text-anchor='middle' dy='.3em'>🎨 Illustration</text>
  <text x='50%' y='60%' font-family='Georgia' font-size='13' fill='#6b7c5c' text-anchor='middle'>could not be generated</text>
</svg>"""


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

# ── Hero ──
st.markdown("""
<div class="hero">
  <h1 class="hero-title">Story<span>Canvas</span></h1>
  <p class="hero-subtitle">Turn your imagination into a fully illustrated children's book — in seconds.</p>
  <div class="hero-divider"></div>
</div>
""", unsafe_allow_html=True)

# ── Layout: form col + tips col ──
col_form, col_tips = st.columns([2, 1], gap="large")

with col_form:
    st.markdown('<div class="prompt-card">', unsafe_allow_html=True)
    st.markdown('<p class="prompt-label">🖋️ Build Your Story</p>', unsafe_allow_html=True)

    api_key = st.text_input(
        "Google AI API Key",
        type="password",
        placeholder="AIza...",
        help="Get your free key at aistudio.google.com",
    )

    st.markdown('<p class="field-label">📖 Story Idea <span class="required">*</span></p>', unsafe_allow_html=True)
    story_prompt = st.text_area(
        "story_idea",
        placeholder="e.g. A tiny mouse searches for his grandmother's lost silver button deep inside a magical forest…",
        height=90,
        label_visibility="collapsed",
    )

    st.markdown('<p class="field-label">🧑‍🤝‍🧑 Characters & Descriptions <span class="optional">(optional)</span></p>', unsafe_allow_html=True)
    characters = st.text_area(
        "characters",
        placeholder="e.g. Pip — a small brown mouse with big round ears and a red scarf. Grandma — a wise old mouse with silver fur and round spectacles.",
        height=90,
        label_visibility="collapsed",
    )

    col_g, col_t = st.columns(2)
    with col_g:
        st.markdown('<p class="field-label">🎭 Genre <span class="optional">(optional)</span></p>', unsafe_allow_html=True)
        genre = st.selectbox(
            "genre",
            ["— None —", "Adventure", "Fantasy", "Mystery", "Fairy Tale", "Friendship", "Comedy", "Educational", "Nature & Animals", "Sci-Fi"],
            label_visibility="collapsed",
        )
    with col_t:
        st.markdown('<p class="field-label">🎨 Tone <span class="optional">(optional)</span></p>', unsafe_allow_html=True)
        tone = st.selectbox(
            "tone",
            ["— None —", "Whimsical & Playful", "Warm & Cozy", "Exciting & Adventurous", "Funny & Silly", "Calm & Dreamy", "Brave & Inspiring"],
            label_visibility="collapsed",
        )

    col_s, col_e = st.columns(2)
    with col_s:
        st.markdown('<p class="field-label">🌍 Setting <span class="optional">(optional)</span></p>', unsafe_allow_html=True)
        setting = st.text_input(
            "setting",
            placeholder="e.g. An enchanted autumn forest",
            label_visibility="collapsed",
        )
    with col_e:
        st.markdown('<p class="field-label">✨ Extra Details <span class="optional">(optional)</span></p>', unsafe_allow_html=True)
        extra = st.text_input(
            "extra",
            placeholder="e.g. Must have a happy ending, include a rainbow",
            label_visibility="collapsed",
        )

    col_a, col_b = st.columns(2)
    with col_a:
        age_group = st.selectbox(
            "Age group",
            ["Toddler (2–4)", "Early reader (5–7)", "Middle grade (8–11)"],
            index=1,
        )
    with col_b:
        num_pages = st.selectbox("Number of pages", [1,2,3, 4, 5, 6, 7, 8], index=4)

    generate_btn = st.button("✨ Generate My Storybook", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_tips:
    st.markdown("""
    <div class="tip-box">
        <strong>✏️ Story Idea tips</strong>
        Describe the core journey or problem.<br><br>
        <em>"A mouse searches for his grandmother's lost button in a magical forest."</em>
    </div>
    <div class="tip-box" style="margin-top:1rem;">
        <strong>🧑‍🤝‍🧑 Character tips</strong>
        Name + appearance + personality works best.<br><br>
        <em>"Pip — small brown mouse, red scarf, curious. Grandma — silver fur, round glasses, wise."</em>
    </div>
    <div class="tip-box" style="margin-top:1rem;">
        <strong>🎨 Powered by</strong>
        <b>Nano Banana</b> for illustrations<br>
        <b>Gemini 3 Flash</b> for storytelling
    </div>
    <div class="tip-box" style="margin-top:1rem;">
        <strong>🔑 Get your API Key</strong>
        Visit <a href="https://aistudio.google.com" target="_blank">aistudio.google.com</a> — free to start!
    </div>
    """, unsafe_allow_html=True)


# ── Generation flow ──────────────────────────────────────────────────────────
if generate_btn:
    if not api_key:
        st.error("Please enter your Google AI API key above.")
        st.stop()
    if not story_prompt.strip():
        st.error("Please describe your story idea!")
        st.stop()

    client = get_client(api_key)

    # ── Step 1: Write story & show it immediately ────────────────────────────
    with st.spinner("📝 Writing your story…"):
        try:
            pages = generate_story_pages(
                client, story_prompt, num_pages, age_group,
                characters=characters, genre=genre, tone=tone,
                setting=setting, extra=extra,
            )
        except Exception as e:
            st.error(f"Story generation failed: {e}")
            st.stop()

    words = story_prompt.strip().split()
    short_title = " ".join(words[:6]).title()
    if len(words) > 6:
        short_title += "…"

    st.markdown(f'<h2 class="book-title">"{short_title}"</h2>', unsafe_allow_html=True)
    st.markdown(f'<p class="book-subtitle">✦ {age_group} · {len(pages)} pages ✦</p>', unsafe_allow_html=True)

    # Print full story text immediately
    st.markdown('<div class="story-full">', unsafe_allow_html=True)
    for i, page in enumerate(pages):
        st.markdown(f"""
        <div class="story-page-text">
            <span class="story-page-label">Page {i + 1}</span>
            <p class="story-body">{page.get("text", "")}</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Step 2: Generate & show each illustration as it completes ────────────
    st.markdown('<div class="section-divider">✦ &nbsp; Illustrations &nbsp; ✦</div>', unsafe_allow_html=True)

    decorations = ["🌟", "🌿", "🦋", "🌊", "🍄", "🌙", "🐉", "🌈"]
    progress_bar = st.progress(0, text="🎨 Painting illustrations…")

    for i, page in enumerate(pages):
        deco = decorations[i % len(decorations)]
        text = page.get("text", "")

        progress_bar.progress(i / len(pages), text=f"🎨 Painting page {i+1} of {len(pages)}…")

        st.markdown(f'<div class="illus-label">{deco} Page {i + 1}</div>', unsafe_allow_html=True)

        # Wait between calls to stay under rate limit (except first page)
        if i > 0:
            time.sleep(10)

        # Generate image
        img = None
        with st.spinner(f"Painting page {i+1} of {len(pages)}..."):
            try:
                img = generate_illustration(client, page["image_prompt"])
            except Exception as e:
                st.error(f"Page {i+1} failed: {e}")

        # Render result
        if img:
            st.image(img, use_container_width=True)
        else:
            st.markdown(
                '<div class="illus-placeholder">🎨 Illustration could not be generated for this page</div>',
                unsafe_allow_html=True
            )

        st.markdown(f'<p class="illus-caption">{text}</p>', unsafe_allow_html=True)
        st.markdown('<div class="illus-divider"></div>', unsafe_allow_html=True)

    progress_bar.progress(1.0, text="✅ All illustrations complete!")
    time.sleep(0.8)
    progress_bar.empty()

    st.markdown('<div class="end-ornament">✦ · ✦ · ✦</div>', unsafe_allow_html=True)
    st.success(f"✅ Your {len(pages)}-page storybook is complete!")
