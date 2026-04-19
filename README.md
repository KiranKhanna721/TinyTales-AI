# 📖 StoryCanvas — AI Illustrated Childrens Book Generator

Generate fully illustrated children's books from a single sentence using
**Gemini 2.0 Flash** (story writing) and **Imagen 3 / Nano Banana** (illustrations).

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get your API key
Visit https://aistudio.google.com → Get API key (free tier works)

### 3. Run the app
```bash
streamlit run app.py
```

### 4. Open in browser
Streamlit will open automatically at http://localhost:8501

---

## 🏗️ How it works

1. You type a story idea + choose age group + number of pages
2. **Gemini 2.0 Flash** writes the story and generates a detailed image prompt per page
3. **Imagen 3 (Nano Banana)** paints a watercolour illustration for each page
4. The app renders a beautiful book-spread layout — alternating image left/right

---

## ☁️ Deploy to Streamlit Cloud (free)

1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Connect your repo → select `app.py`
4. Deploy — share the link with judges!

---

## 📁 File structure
```
storycanvas/
├── app.py            # Full Streamlit application
├── requirements.txt  # Dependencies
└── README.md         # This file
```

---

## 💡 Demo prompts to wow the judges

- *"A tiny robot who gets lost in a jungle and befriends a parrot"*
- *"A little cloud who can't rain and wants to help a thirsty flower"*
- *"A brave girl who discovers a secret library hidden inside a whale"*
