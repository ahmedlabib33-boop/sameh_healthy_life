from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests
import streamlit as st


RiskLevel = Literal["HIGH", "MEDIUM", "LOW"]

APP_NAME = "Mohamed Sameh Guard"
FULL_TITLE = "Eng. Mohamed Sameh | Life Guard | Learning Tool"
ARABIC_NAME = "حارس محمد سامح"
MEDICINE_ANSWER = "قسم الأدوية لسه تحت التجهيز. لا توقف أو تغير أي دواء أو جرعة بدون طبيب الأورام."
DISCLAIMER = (
    "هذا التطبيق للتوعية وتقليل المخاطر الغذائية فقط. لا يشخص السرطان، لا يعالج السرطان، لا يوقف دواء، "
    "لا يغير جرعة، ولا يستبدل طبيب الأورام أو أخصائي تغذية أورام. مع تاريخ سرطان أو رجوع أعراض، "
    "أي قرار علاج أو صيام أو مكملات أو نظام قاسٍ لازم يتم مع الفريق الطبي."
)
FINAL_MESSAGE = (
    "أي منتج يجمع: زيت نباتي مكرر + سكر أو دقيق أبيض + إضافات + صلاحية طويلة = غير مناسب لمحمد سامح. "
    "ومع تاريخ السرطان، الأفضل نغلق هذا الباب بالكامل: لا مقليات مطاعم، لا زيت متكرر، لا سمن نباتي، "
    "لا نوتيلا، لا شيبسي، لا مايونيز، لا بسكويت وويفر وكيك جاهز."
)

MODULES = {"food": "الغذاء", "medicine": "الأدوية", "learning": "التعلم"}
FOOD_SLIDES = {
    "why": "ليه ده وحش",
    "stop": "حاجات لازم تبطلها حالًا",
    "alts": "بدائل لذيذة",
    "scan": "امسح QR أو باركود",
    "ai": "اسأل الذكاء",
}
LEARNING_SLIDES = {
    "intro": "يعني إيه Marketing for Project Managers؟",
    "value": "Stakeholder Value Proposition",
    "position": "Positioning للمشروع",
    "comm": "Communication Plan as Marketing",
    "brand": "Personal Branding",
    "pitch": "Client Pitch",
    "case": "Case Study",
    "ai": "AI Explanation",
    "courses": "Free Courses",
}


@dataclass
class RiskAnalysis:
    level: RiskLevel
    score: int
    flags: list[str]
    explanation: list[str]
    recommendation: str
    alternatives: list[str]


HIGH_RISK_KEYWORDS = [
    "partially hydrogenated oil",
    "hydrogenated vegetable oil",
    "hydrogenated oil",
    "vegetable shortening",
    "shortening",
    "margarine",
    "vanaspati ghee",
    "زيت مهدرج",
    "مهدرج جزئيًا",
    "مهدرج جزئيا",
    "سمن نباتي",
    "دهن نباتي مهدرج",
    "مارجرين",
    "شورتنينج",
]
OIL_KEYWORDS = [
    "vegetable oil",
    "vegetable fat",
    "palm oil",
    "palm kernel oil",
    "sunflower oil",
    "soybean oil",
    "corn oil",
    "canola oil",
    "rapeseed oil",
    "cottonseed oil",
    "refined oils",
    "زيت نباتي",
    "دهن نباتي",
    "زيت نخيل",
    "زيت نواة النخيل",
    "زيت عباد الشمس",
    "زيت دوار الشمس",
    "زيت صويا",
    "زيت ذرة",
    "زيت كانولا",
    "زيت بذرة القطن",
    "زيوت مكررة",
]
SUGAR_KEYWORDS = ["glucose syrup", "high fructose corn syrup", "maltodextrin", "sugar", "sweeteners", "شراب جلوكوز", "شراب الذرة عالي الفركتوز", "مالتوديكسترين", "سكر", "محليات"]
REFINED_CARB_KEYWORDS = ["refined wheat flour", "modified starch", "fried", "pre-fried", "instant", "دقيق أبيض", "نشا معدل", "مقلي", "نصف مقلي", "سريع التحضير"]
ADDITIVE_KEYWORDS = ["mono and diglycerides", "emulsifier", "artificial flavor", "preservatives", "flavor enhancers", "colors", "مونو وداي جلسريد", "مستحلبات", "نكهات صناعية", "مواد حافظة", "محسنات طعم", "ألوان صناعية"]

PRODUCT_CATEGORIES = [
    ("شيبسي وسناكس ومقرمشات", "HIGH", "Chipsy، Forno، Doritos، Cheetos، Tiger snacks، Bake Rolz، Kettle chips، Nachos، Tortilla chips، Corn puffs، Popcorn microwave", "غالبًا تحتوي زيوت نباتية مكررة، ملح عالي، نكهات صناعية، وأحيانًا تكون مقلية أو مخبوزة بزيوت معالجة."),
    ("بسكويت وويفر وكيك جاهز", "HIGH", "BiscoMisr products، Tiger biscuits، Wafers، Cookies، Cream-filled biscuits، Tea biscuits، Cake bars، Cupcakes، Swiss rolls، Donuts، Packaged croissants", "الخطر من اجتماع السكر + الدقيق الأبيض + الدهون النباتية أو زيت النخيل + إضافات ومثبتات."),
    ("مخبوزات ومعجنات تجارية", "HIGH", "Molto، Croissant، Pate، Danish pastry، Puff pastry، Ready pies، Frozen pizza dough", "المخبوزات التجارية غالبًا تعتمد على دهن نباتي أو مارجرين أو زيت نخيل للقوام والهشاشة وطول الصلاحية."),
    ("سبريد وحلويات كريمية", "HIGH", "Nutella، Chocolate hazelnut spread، Cocoa spread، Peanut butter with added vegetable oil، Cream fillings", "النوتيلا والسبريد غالبًا تحتوي سكر عالي وزيت نخيل أو دهون نباتية، وليست مناسبة لشخص يحاول تقليل الالتهاب والأكسدة."),
    ("مايونيز وصوصات جاهزة", "HIGH", "Mayonnaise، Ranch، Thousand Island، Garlic sauce، Burger sauce، Shawerma sauce، Cheese sauce، BBQ sauce high sugar، Ketchup high sugar", "المايونيز غالبًا أساسه زيت نباتي بنسبة كبيرة. الصوصات الجاهزة تجمع زيوت، سكر أو ملح، مثبتات، ونكهات."),
    ("أكل سريع ومقليات مطاعم", "HIGH", "French fries، Fried chicken، Broasted chicken، Crispy chicken، Fried fish، Fried shrimp، Fried falafel، Fried eggplant، Nuggets، Spring rolls", "أخطر فئة لأنها غالبًا تستخدم زيت عميق يتسخن لساعات ويتعرض للهواء وبقايا الطعام ويتعاد استخدامه."),
    ("أكل مجمد ونصف مقلي", "MEDIUM", "Frozen fries، Frozen nuggets، Frozen chicken strips، Frozen burger patties، Frozen spring rolls، Frozen pizza، Frozen ready meals", "منتجات كثيرة تكون نصف مقلية أو تحتوي زيوت نباتية ومواد حافظة ومثبتات. افحص المكونات."),
    ("نودلز وشوربة بودر", "HIGH", "Instant noodles، Soup powder، Instant pasta meals، Mac and cheese instant، Snack meals، Seasoning sachets", "غالبًا تحتوي دهون نباتية أو زيت نخيل، نشا معدل، ملح عالي، ومحسنات طعم."),
    ("بدائل ألبان ومشروبات نباتية", "MEDIUM", "Almond milk with sunflower oil، Oat milk with canola/sunflower oil، Coffee creamer، Non-dairy creamer، Plant-based cheese", "لبن اللوز أو الشوفان ليس ممنوعًا تلقائيًا. المرفوض هو النوع الذي يحتوي زيت مضاف، سكر عالي، مثبتات كثيرة، أو قائمة طويلة."),
    ("معلبات بالزيت", "MEDIUM", "Tuna in sunflower oil، Sardines in vegetable oil، Beans with vegetable oil، Ready meals preserved in oil", "اختار بالماء أو زيت زيتون واضح، أو صفي الزيت جيدًا لو لا يوجد بديل."),
]

ALTERNATIVES = [
    ("شيبسي", "فشار بيت بدون زيت أو بزيت زيتون قليل + بابريكا"),
    ("نوتيلا", "طحينة 100% + كاكاو خام + نقطة عسل بسيطة"),
    ("مايونيز", "زبادي يوناني + ليمون + ثوم + رشة ملح"),
    ("بطاطس مقلية", "بطاطس فرن بزيت زيتون قليل"),
    ("بروستد", "فراخ مشوية بتتبيلة زبادي وليمون"),
    ("بسكويت محشي", "فاكهة + مكسرات طبيعية"),
    ("لبن لوز تجاري طويل المكونات", "لبن أو زبادي طبيعي أو لبن لوز مكوناته قليلة بدون زيت وسكر"),
    ("كوفي كريمر", "لبن طبيعي أو قرفة"),
    ("سمن نباتي", "زيت زيتون بكر بكمية قليلة أو دهون طبيعية محدودة حسب الطبيب"),
    ("صوص جاهز", "حمص أو طحينة أو زبادي بالثوم"),
    ("نودلز", "شوربة بيت بخضار وبروتين"),
    ("مشروب غازي", "مياه + ليمون + نعناع"),
    ("حلوى صناعية", "فاكهة مع قرفة أو زبادي"),
    ("كيك جاهز", "شوفان بالموز أو زبادي وفاكهة"),
]
SHOPPING_LIST = ["زيت زيتون بكر ممتاز", "طحينة 100% سمسم", "مكسرات طبيعية بدون زيت", "زبادي طبيعي", "بيض", "سمك", "فراخ", "عدس وفول وحمص", "شوفان", "خضار وفاكهة", "بطاطس للفرن", "حبوب كاملة", "ليمون وثوم وتوابل"]


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def init_state() -> None:
    st.session_state.setdefault("module", "food")
    st.session_state.setdefault("food_slide", "why")
    st.session_state.setdefault("learning_slide", "intro")


def inject_css() -> None:
    html(
        """
<style>
:root {
  --bg-1: #04050e;
  --bg-2: #060e1f;
  --panel: rgba(14, 19, 38, 0.72);
  --panel-soft: rgba(19, 27, 52, 0.55);
  --border: rgba(51, 82, 133, 0.42);
  --cyan: #00e0ff;
  --blue: #2e6bff;
  --purple: #ad40ff;
  --green: #30ff9e;
  --pink: #ff2ead;
  --yellow: #ffc940;
  --text: #f0f7ff;
  --muted: rgba(156, 173, 199, 0.95);
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  direction: rtl;
  color: var(--text);
  overflow-x: hidden;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
  background:
    radial-gradient(circle at 88% 9%, rgba(173, 64, 255, 0.5), transparent 18rem),
    radial-gradient(circle at 38% 92%, rgba(0, 224, 255, 0.24), transparent 18rem),
    repeating-linear-gradient(90deg, transparent 0 79px, rgba(51, 82, 133, 0.14) 80px 81px),
    repeating-linear-gradient(0deg, transparent 0 79px, rgba(51, 82, 133, 0.12) 80px 81px),
    linear-gradient(90deg, var(--bg-1), var(--bg-2)) !important;
}

[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"], #MainMenu, footer { display: none !important; }
.block-container { max-width: none !important; padding: 32px 42px 58px 23px !important; }
[data-testid="stVerticalBlock"] { gap: 0.95rem !important; }
.element-container { margin: 0 !important; }
p { margin: 0; }
a { color: inherit; text-decoration: none; }

.visual-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  gap: 30px;
  padding: 32px 19px 58px 19px;
}

.visual-sidebar {
  min-height: calc(100vh - 64px);
  border-radius: 34px;
  padding: 24px 16px;
  background: rgba(6, 9, 22, 0.92);
  border: 1px solid var(--border);
  box-shadow: 0 12px 30px rgba(46, 107, 255, 0.1);
}

.visual-brand {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 12px;
  align-items: center;
  margin: 10px 20px 58px;
  direction: ltr;
}

.brand-orb {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--cyan), var(--purple));
  box-shadow: 0 0 28px rgba(0, 224, 255, 0.45);
}

.visual-brand strong { display: block; font-size: 22px; line-height: 1; font-weight: 900; }
.visual-brand span { display: block; margin-top: 4px; color: var(--muted); font-size: 12px; }

.visual-nav {
  display: grid;
  gap: 12px;
  margin: 0 16px;
}

.visual-nav a,
.visual-nav div {
  min-height: 44px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  color: rgba(156, 173, 199, 0.88);
  border-radius: 16px;
  border: 1px solid rgba(51, 82, 133, 0.3);
  background: rgba(19, 27, 52, 0.55);
  font-size: 14px;
  font-weight: 750;
}

.visual-nav .active {
  color: var(--text);
  font-weight: 900;
  border-color: rgba(0, 224, 255, 0.82);
  background: linear-gradient(90deg, var(--blue), var(--purple));
  box-shadow: 0 12px 20px rgba(173, 64, 255, 0.28);
}

.visual-health {
  margin: 218px 16px 0;
  padding: 24px 18px;
  min-height: 198px;
  border-radius: 26px;
  background: rgba(19, 27, 52, 0.56);
  border: 1px solid rgba(0, 224, 255, 0.22);
}
.visual-health small { color: var(--cyan); font-size: 12px; font-weight: 900; letter-spacing: 0.04em; }
.visual-health b { display: block; margin: 20px 0 14px; color: var(--text); font-size: 40px; line-height: 1; font-weight: 900; }
.visual-health p { margin: 0; color: var(--muted); font-size: 14px; line-height: 1.45; }

.visual-main { max-width: 1147px; padding-top: 8px; }
.visual-topbar { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; margin-bottom: 28px; }
.visual-topbar h1 { margin: 0 0 6px; color: var(--text); font-size: 34px; line-height: 1.1; font-weight: 900; direction: ltr; text-align: right; }
.visual-subtitle { margin: 0; color: var(--muted); font-size: 15px; }
.visual-actions { display: flex; gap: 14px; align-items: center; }
.visual-search { width: 254px; height: 50px; display: flex; align-items: center; padding: 0 24px; border-radius: 18px; background: rgba(14, 19, 38, 0.62); border: 1px solid rgba(51, 82, 133, 0.45); color: rgba(156, 173, 199, 0.85); font-size: 14px; }
.visual-deploy { width: 120px; height: 50px; display: flex; align-items: center; justify-content: center; border-radius: 18px; color: var(--text); font-size: 15px; font-weight: 900; border: 1px solid rgba(0, 224, 255, 0.65); background: linear-gradient(90deg, var(--cyan), var(--blue)); box-shadow: 0 12px 18px rgba(0, 224, 255, 0.25); }

.visual-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 22px; margin-bottom: 26px; }
.visual-kpi { min-height: 132px; padding: 22px; border-radius: 28px; border: 1px solid rgba(51, 82, 133, 0.38); background: var(--panel); box-shadow: 0 12px 18px rgba(0, 224, 255, 0.08); }
.visual-kpi .label { display: flex; align-items: center; gap: 12px; color: var(--muted); font-size: 13px; }
.dot { width: 12px; height: 12px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 16px var(--accent); flex: 0 0 auto; }
.visual-kpi strong { display: block; margin-top: 18px; font-size: 34px; line-height: 1; font-weight: 900; }
.visual-kpi small { display: block; margin-top: 8px; color: var(--accent); font-size: 13px; font-weight: 900; }

.visual-grid { display: grid; grid-template-columns: 1.55fr 0.72fr; gap: 24px; }
.visual-grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.visual-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.visual-panel { position: relative; overflow: hidden; border-radius: 30px; border: 1px solid rgba(51, 82, 133, 0.36); background: rgba(14, 19, 38, 0.62); box-shadow: 0 12px 24px rgba(0, 224, 255, 0.08); padding: 26px 30px; min-height: 100%; }
.visual-panel h2, .visual-panel h3 { margin: 0 0 14px; color: var(--text); font-size: 22px; font-weight: 900; }
.visual-panel p, .visual-panel li { margin: 0; color: var(--muted); font-size: 15px; line-height: 1.75; }
.visual-panel ul { margin: 12px 0 0; padding-right: 18px; }
.visual-panel.compact { padding: 20px; border-radius: 24px; }
.mission { min-height: 242px; border-color: rgba(0, 224, 255, 0.35); box-shadow: 0 12px 24px rgba(0, 224, 255, 0.12); }
.streams { min-height: 242px; }
.stream-row { min-height: 50px; display: grid; grid-template-columns: 1fr 56px 92px; gap: 10px; align-items: center; border-top: 1px solid rgba(51, 82, 133, 0.34); font-size: 14px; }
.stream-row b { color: rgba(240, 247, 255, 0.95); }
.stream-row em { color: var(--cyan); font-style: normal; font-weight: 900; }
.ok { color: var(--green); } .warn { color: var(--yellow); } .bad { color: var(--pink); }
.brief { min-height: 248px; }
.bars { min-height: 248px; display: flex; align-items: flex-end; gap: 24px; padding: 30px 34px; border-radius: 24px; }
.bars span { width: 18px; height: var(--h); border-radius: 8px; background: linear-gradient(180deg, var(--purple), var(--blue)); box-shadow: 0 12px 10px rgba(46, 107, 255, 0.18), 0 0 18px rgba(0, 224, 255, 0.35); }

.warning-panel { border-color: rgba(255, 201, 64, 0.58); background: linear-gradient(135deg, rgba(255, 201, 64, 0.12), rgba(14, 19, 38, 0.62)); }
.danger-panel { border-color: rgba(255, 46, 173, 0.65); background: linear-gradient(135deg, rgba(255, 46, 173, 0.16), rgba(14, 19, 38, 0.62)); box-shadow: 0 0 32px rgba(255, 46, 173, 0.16); }
.risk-badge { display: inline-flex; align-items: center; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 900; border: 1px solid currentColor; margin-bottom: 12px; }
.high { color: var(--pink); } .medium { color: var(--yellow); } .low { color: var(--green); }

div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
  direction: rtl !important;
  text-align: right !important;
  color: var(--text) !important;
  background: rgba(14, 19, 38, 0.62) !important;
  border: 1px solid rgba(51, 82, 133, 0.45) !important;
  border-radius: 18px !important;
}

div[data-testid="stSelectbox"] label {
  color: var(--cyan) !important;
  font-size: 12px !important;
  font-weight: 900 !important;
  letter-spacing: 0.04em;
}

div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  min-height: 48px;
  border-radius: 16px !important;
  color: var(--text) !important;
  border: 1px solid rgba(0, 224, 255, 0.55) !important;
  background: linear-gradient(90deg, rgba(46, 107, 255, 0.72), rgba(173, 64, 255, 0.54)) !important;
  box-shadow: 0 12px 20px rgba(173, 64, 255, 0.18);
}

div[data-testid="stSelectbox"] [data-baseweb="select"] span {
  color: var(--text) !important;
  font-weight: 900 !important;
}

div[data-testid="stButton"] button {
  width: 100%;
  min-height: 50px;
  border-radius: 18px;
  color: var(--text);
  font-weight: 900;
  border: 1px solid rgba(0, 224, 255, 0.65);
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  box-shadow: 0 12px 18px rgba(0, 224, 255, 0.25);
}

.visual-footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  min-height: 34px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 3px;
  padding: 7px 12px;
  color: #b8cbd2;
  font-size: 0.84rem;
  border-top: 1px solid rgba(0, 224, 255, 0.24);
  background: rgba(4, 5, 14, 0.92);
  backdrop-filter: blur(12px);
  box-shadow: 0 -10px 28px rgba(0, 0, 0, 0.28);
  direction: ltr;
}
.visual-footer .author { color: var(--cyan); font-weight: 900; }
.visual-footer .mark { color: var(--text); font-weight: 900; margin-left: 2px; }

@media (max-width: 980px) {
  .block-container { padding: 0 12px 58px !important; }
  .visual-shell { grid-template-columns: 1fr; padding: 12px 0 58px; }
  .visual-sidebar { min-height: auto; }
  .visual-health { margin-top: 28px; }
  .visual-topbar, .visual-actions { flex-direction: column; align-items: stretch; }
  .visual-search, .visual-deploy { width: auto; }
  .visual-kpis, .visual-grid, .visual-grid.two, .visual-grid.three { grid-template-columns: 1fr; }
  .bars { gap: 12px; overflow-x: auto; }
}
</style>
"""
    )


def sidebar(module: str) -> str:
    return f"""
<aside class="visual-sidebar">
  <div class="visual-brand">
    <div class="brand-orb"></div>
    <div>
      <strong>GUARD</strong>
      <span>Control OS 2200</span>
    </div>
  </div>
  <div class="visual-nav">
    <div class="active">{MODULES[module]}</div>
  </div>
  <section class="visual-health">
    <small>HEALTH GUARD</small>
    <b>87%</b>
    <p>نظام حماية غذائية وتعليم عملي لمهندس محمد سامح. AI fallback نشط عند غياب Ollama.</p>
  </section>
</aside>
"""


def topbar(module: str) -> str:
    return f"""
<header class="visual-topbar">
  <div>
    <h1>{FULL_TITLE}</h1>
    <p class="visual-subtitle">{ARABIC_NAME} · {MODULES[module]} · واجهة حماية غذائية وتعليم عملي</p>
  </div>
  <div class="visual-actions">
    <div class="visual-search">Search intelligence...</div>
    <div class="visual-deploy">Ollama</div>
  </div>
</header>
"""


def kpis(module: str) -> str:
    if module == "food":
        data = [
            ("مستوى الخطر", "HIGH", "زيت + سكر + دقيق + إضافات", "var(--pink)"),
            ("شرائح الغذاء", "5", "تحليل وبدائل وسكانر وAI", "var(--cyan)"),
            ("قاعدة الحظر", "10", "فئات منتجات عالية الخطورة", "var(--yellow)"),
            ("البدائل", "14", "اختيارات لذيذة واقعية", "var(--green)"),
        ]
    elif module == "medicine":
        data = [
            ("الحالة", "LOCKED", "قريبًا", "var(--yellow)"),
            ("الأمان", "100%", "لا تغيير دواء بدون طبيب", "var(--green)"),
            ("الوحدات", "6", "مخططة للنسخة القادمة", "var(--cyan)"),
            ("AI Guard", "ON", "إجابة أدوية آمنة", "var(--pink)"),
        ]
    else:
        data = [
            ("المسار", "9", "شرائح تعليمية", "var(--cyan)"),
            ("Pitch", "30s", "صيغة عملية للعميل", "var(--green)"),
            ("Courses", "6", "موارد تم التحقق منها", "var(--purple)"),
            ("AI Coach", "ON", "شرح وتسويق مشاريع", "var(--pink)"),
        ]
    cards = ""
    for label, value, note, accent in data:
        cards += f"""
<div class="visual-kpi" style="--accent: {accent}">
  <div class="label"><span class="dot"></span>{label}</div>
  <strong>{value}</strong>
  <small>{note}</small>
</div>
"""
    return f'<section class="visual-kpis">{cards}</section>'


def find_flags(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [word for word in keywords if word.lower() in lower]


def analyze_ingredients(text: str, product_name: str = "") -> RiskAnalysis:
    combined = f"{product_name} {text}".strip()
    high = find_flags(combined, HIGH_RISK_KEYWORDS)
    oils = find_flags(combined, OIL_KEYWORDS)
    sugars = find_flags(combined, SUGAR_KEYWORDS)
    carbs = find_flags(combined, REFINED_CARB_KEYWORDS)
    additives = find_flags(combined, ADDITIVE_KEYWORDS)
    score = len(high) * 45 + len(oils) * 17 + len(sugars) * 14 + len(carbs) * 12 + len(additives) * 8
    if high:
        score = max(score, 92)
    if oils and (sugars or carbs) and additives:
        score = max(score, 88)
    if oils and ("مايونيز" in combined or "mayonnaise" in combined.lower()):
        score = max(score, 86)
    score = min(score, 100)
    flags = list(dict.fromkeys(high + oils + sugars + carbs + additives))
    explanation: list[str] = []
    if high:
        explanation.append("وجود زيوت مهدرجة أو مهدرجة جزئيًا يرفع المنتج إلى HIGH RISK وممنوع قدر الإمكان.")
    if oils:
        explanation.append("الزيوت الصناعية، خصوصًا مع التسخين أو القلي أو التخزين السيئ، قد تساهم في أكسدة الدهون وبيئة التهابية غير مناسبة.")
    if sugars:
        explanation.append("السكر العالي والمتكرر قد يرفع الإنسولين ومقاومة الإنسولين ويدعم نمطًا غذائيًا التهابيًا.")
    if carbs:
        explanation.append("الكربوهيدرات المكررة تتحول سريعًا إلى جلوكوز وترفع سكر الدم والإنسولين بسرعة.")
    if additives:
        explanation.append("الإضافات مع الزيت والسكر أو الدقيق الأبيض تجعل المنتج أقرب لفائق التصنيع.")
    if score >= 75:
        return RiskAnalysis("HIGH", score, flags, explanation, "ممنوع", ["فشار بيت", "زبادي بالثوم والليمون", "بطاطس فرن", "طحينة 100%"])
    if score >= 35:
        return RiskAnalysis("MEDIUM", score, flags, explanation or ["يحتاج قراءة دقيقة للمكونات والكمية."], "قلل جدًا", ["منتج بمكونات قصيرة وواضحة", "تحضير منزلي"])
    return RiskAnalysis("LOW", score, flags, ["لا تظهر مؤشرات خطورة واضحة من القواعد الحالية."], "مناسب نسبيًا", ["استمر في مكونات قصيرة وواضحة"])


def lookup_product_by_barcode(barcode: str) -> dict[str, str] | None:
    try:
        response = requests.get(
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields=product_name,ingredients_text,nutriments",
            timeout=6,
        )
        if response.status_code != 200:
            return None
        product = response.json().get("product")
        if not product:
            return None
        return {
            "name": product.get("product_name") or "منتج بدون اسم",
            "ingredients": product.get("ingredients_text") or "",
            "nutrition": json.dumps(product.get("nutriments") or {}, ensure_ascii=False)[:900],
        }
    except requests.RequestException:
        return None


def fallback_answer(question: str, mode: str = "food") -> str:
    q = question.lower()
    prefix = f"{DISCLAIMER}\n\n"
    if any(word in q for word in ["دواء", "جرعة", "مكمل", "medicine", "علاج"]):
        return prefix + MEDICINE_ANSWER
    if mode == "learning":
        if "pitch" in q or "بيع" in q:
            return "صيغة pitch قوية: المشكلة -> الأثر -> الحل -> الدليل -> القرار المطلوب. خلي الكلام قصير ومربوط بنتيجة business واضحة."
        if "dashboard" in q or "داشبورد" in q:
            return "اشرح الداشبورد من القرار المطلوب، مش من الرسومات: أين نقف؟ ما الخطر؟ ما القرار؟ وما الإجراء القادم؟"
        return "Marketing for Project Managers يعني توصيل قيمة المشروع بوضوح للعميل والإدارة والفريق، وبناء ثقة من خلال بيانات، ترتيب، ونتائج قابلة للقرار."
    if "مايونيز" in q:
        return prefix + "المايونيز الجاهز غالبًا زيت نباتي مكرر مع إضافات. الأفضل زبادي يوناني + ليمون + ثوم + رشة ملح."
    if "نوتيلا" in q:
        return prefix + "النوتيلا غالبًا سكر عالي + دهن نباتي. بديل ألطف: طحينة 100% + كاكاو خام + نقطة عسل بسيطة."
    if "شيبسي" in q:
        return prefix + "الشيبسي يجمع زيت نباتي مكرر + كربوهيدرات مكررة + ملح وإضافات. بديله فشار بيت بدون زيت أو بزيت زيتون قليل."
    if "سكر" in q:
        return prefix + "الجلوكوز وقود لكل خلايا الجسم، مش للخلايا السرطانية فقط. لكن السكر العالي والمتكرر قد يرفع الإنسولين والالتهاب والوزن."
    if "كربوهيدرات" in q or "دقيق" in q:
        return prefix + "الكربوهيدرات المكررة مثل الدقيق الأبيض والبسكويت والنودلز تتحول سريعًا إلى جلوكوز وترفع سكر الدم والإنسولين."
    return prefix + "لو المنتج فيه زيت نباتي مكرر + سكر أو دقيق أبيض + إضافات + صلاحية طويلة، يبقى غير مناسب لمحمد سامح. ابعتلي المكونات وأنا أحللها لك."


def ask_ollama(question: str, mode: str = "food") -> str:
    try:
        response = requests.post(
            f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/generate",
            json={
                "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                "prompt": f"{DISCLAIMER}\n\nأجب بالعربية المصرية بشكل مباشر وآمن. السؤال: {question}",
                "stream": False,
            },
            timeout=4,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip() or fallback_answer(question, mode)
    except requests.RequestException:
        return fallback_answer(question, mode)


def panel(title: str, body: str, bullets: list[str] | None = None, kind: str = "") -> str:
    items = "".join(f"<li>{item}</li>" for item in (bullets or []))
    return f'<article class="visual-panel {kind}"><h2>{title}</h2><p>{body}</p>{"<ul>" + items + "</ul>" if items else ""}</article>'


def food_why() -> None:
    cards = [
        panel("الزيوت النباتية الصناعية", "زيوت مثل عباد الشمس، الصويا، الذرة، الكانولا، بذرة القطن، والزيوت المختلطة تدخل بكثرة في الأكل المصنع والمقليات. الخطر الأكبر يظهر مع الحرارة العالية، القلي العميق، التخزين السيئ، وإعادة استخدام الزيت.", ["Aldehydes / ألدهيدات", "Free radicals / جذور حرة", "Lipid peroxides / بيروكسيدات الدهون", "Polar compounds / مركبات قطبية", "Polymerized fats / دهون متبلمرة", "Acrolein / أكرولين"]),
        panel("HNE", "4-HNE أو 4-Hydroxynonenal من نواتج أكسدة الدهون الغنية بأوميغا-6، خصوصًا linoleic acid الموجود في زيوت عباد الشمس والصويا والذرة. يزيد مع التسخين العالي، القلي العميق، إعادة استخدام الزيت، أو التخزين السيئ.", ["قد يتفاعل مع البروتينات وأغشية الخلايا والحمض النووي", "يرتبط بحثيًا بمسارات الإجهاد التأكسدي والالتهاب"]),
        panel("الالتهاب المزمن", "الالتهاب المزمن والضغط التأكسدي ليسوا تفاصيل بسيطة. لا نقول إن الزيت وحده يسبب السرطان مباشرة، لكن الزيوت المتدهورة حراريًا والمقليات والأكل المصنع قد تساهم في بيئة التهابية وأكسدية غير مرغوبة.", []),
        panel("الدهون المهدرجة", "الدهون المتحولة الناتجة عن الزيوت المهدرجة أو المهدرجة جزئيًا تعتبر من أسوأ الدهون الصناعية، وترتبط بمخاطر القلب والأوعية.", ["partially hydrogenated oil", "hydrogenated vegetable oil", "vegetable shortening", "margarine", "vanaspati ghee", "سمن نباتي"], "danger-panel"),
        panel("السكر", "الجلوكوز وقود تستخدمه خلايا الجسم كلها، وكثير من الخلايا السرطانية تستهلك الجلوكوز بكثافة. مش معنى كده إن معلقة سكر وحدها تعمل سرطان، لكن نمط غذائي عالي السكر وغير منضبط يخلق بيئة غير مناسبة.", ["مشروبات غازية", "نوتيلا", "بسكويت", "كيك", "شراب جلوكوز"]),
        panel("الكربوهيدرات المكررة", "الدقيق الأبيض، البسكويت، الكيك، الكرواسون، النودلز، الشيبسي، البطاطس المقلية، والمخبوزات التجارية تتحول سريعًا إلى جلوكوز. التركيبة الأخطر هي: زيت مصنع + سكر أو دقيق أبيض + إضافات + صلاحية طويلة.", []),
        panel("الإضافات والمنتجات فائقة التصنيع", "ليست كل إضافة وحدها معناها سم، لكن اجتماع الإضافات مع زيوت مصنعة وسكر ودقيق أبيض يجعل المنتج ultra-processed وغير مناسب لشخص يحاول تقليل الالتهاب والأكسدة.", ["artificial flavors", "emulsifiers", "glucose syrup", "high fructose corn syrup", "maltodextrin", "modified starch"]),
        panel("قاعدة محمد سامح", FINAL_MESSAGE, [], "danger-panel"),
    ]
    html(f'<section class="visual-grid two">{"".join(cards)}</section>')


def food_stop() -> None:
    query = st.text_input("ابحث في المنتجات أو الفئات", placeholder="مثال: مايونيز، نوتيلا، نودلز، زيت نخيل")
    risk_filter = st.selectbox("فلتر الخطورة", ["الكل", "HIGH", "MEDIUM"], label_visibility="collapsed")
    cards = ""
    for name, risk, examples, message in PRODUCT_CATEGORIES:
        hay = f"{name} {examples} {message}".lower()
        if query and query.lower() not in hay:
            continue
        if risk_filter != "الكل" and risk != risk_filter:
            continue
        cls = "high" if risk == "HIGH" else "medium"
        cards += f'<article class="visual-panel compact"><span class="risk-badge {cls}">{risk} RISK</span><h2>{name}</h2><p>{message}</p><p><b>أمثلة:</b> {examples}</p></article>'
    html(f'<section class="visual-grid two">{cards or panel("لا توجد نتائج", "جرّب كلمة أبسط أو اكتب المكونات في صفحة التحليل.")}</section>')
    html(panel("تحذير تغيير المكونات", "المنتجات تتغير ومكوناتها تختلف من حجم لطعم ومن بلد تصنيع لآخر. القرار النهائي من قراءة المكونات على العبوة.", kind="warning-panel"))


def food_alts() -> None:
    cards = "".join(f'<article class="visual-panel compact"><h2>{bad}</h2><p>{good}</p></article>' for bad, good in ALTERNATIVES)
    html(f'<section class="visual-grid three">{cards}</section>')
    html(panel("قائمة شراء آمنة نسبيًا", " · ".join(SHOPPING_LIST), kind="mission"))


def result_panel(result: RiskAnalysis) -> str:
    cls = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}[result.level]
    flags = ", ".join(result.flags) if result.flags else "لا توجد مؤشرات واضحة"
    explanation = "".join(f"<li>{line}</li>" for line in result.explanation)
    alternatives = "".join(f"<li>{item}</li>" for item in result.alternatives)
    alarm = "تحذير شديد: المنتج يحتوي مكونات غير مناسبة لمحمد سامح. الأفضل تجنبه." if result.level == "HIGH" else ""
    return f"""
<article class="visual-panel {'danger-panel' if result.level == 'HIGH' else ''}">
  <span class="risk-badge {cls}">{result.level} RISK · {result.recommendation} · {result.score}/100</span>
  <h2>نتيجة التحليل</h2>
  <p><b>Red flags:</b> {flags}</p>
  <ul>{explanation}</ul>
  <p><b>بدائل:</b></p><ul>{alternatives}</ul>
  <p class="{cls}">{alarm}</p>
</article>
"""


def food_scan() -> None:
    html(panel("امسح QR أو باركود", "اسمح باستخدام الكاميرا للفحص. في Streamlit يتم استخدام camera input مع fallback يدوي للباركود أو المكونات. يعمل على localhost وHTTPS عند سماح المتصفح.", kind="mission"))
    camera = st.camera_input("افتح الكاميرا داخل البرنامج")
    if camera:
        html(panel("تم التقاط صورة", "لو لم يتم قراءة الباركود تلقائيًا، اكتب الرقم أو المكونات يدويًا.", kind="warning-panel"))
    barcode = st.text_input("اكتب رقم الباركود", placeholder="مثال: 5449000000996")
    if st.button("ابحث في OpenFoodFacts"):
        product = lookup_product_by_barcode(barcode.strip())
        if product and product.get("ingredients"):
            html(panel(product["name"], product["ingredients"], kind="streams"))
            html(result_panel(analyze_ingredients(product["ingredients"], product["name"])))
        else:
            html(panel("لم نجد المنتج", "لم نجد المنتج في قاعدة البيانات. اكتب المكونات من العبوة.", kind="warning-panel"))
    manual = st.text_area("اكتب اسم المنتج أو المكونات يدويًا", placeholder="مثال: زيت نباتي، دقيق أبيض، سكر، مستحلبات...")
    if st.button("حلل المكونات"):
        html(result_panel(analyze_ingredients(manual)) if manual.strip() else panel("بيانات ناقصة", "اكتب المكونات أولًا حتى نقدر نحلل المنتج.", kind="warning-panel"))


def ai_box(mode: str) -> None:
    prompt = st.text_input("اسأل الذكاء", placeholder="مثال: هو المايونيز ينفع؟ أو اعملي pitch")
    if st.button("اسأل الآن"):
        html(panel("إجابة الذكاء", ask_ollama(prompt, mode) if prompt.strip() else "اكتب السؤال بحرية بالعربي أو المصري.", kind="mission"))


def food_module(slide: str) -> None:
    slide = st.selectbox(
        "اختر شريحة الغذاء",
        list(FOOD_SLIDES.keys()),
        index=list(FOOD_SLIDES.keys()).index(slide),
        format_func=lambda key: FOOD_SLIDES[key],
        key="food_slide",
    )
    html(panel("⚠ تنبيه طبي", DISCLAIMER, kind="warning-panel"))
    if slide == "why":
        food_why()
    elif slide == "stop":
        food_stop()
    elif slide == "alts":
        food_alts()
    elif slide == "scan":
        food_scan()
    else:
        ai_box("food")


def medicine_module() -> None:
    planned = ["أدوية يجب سؤال الطبيب عنها", "مكملات ممنوع تبدأها وحدك", "تداخلات غذاء ودواء", "أسئلة لطبيب الأورام", "سجل الأعراض", "تذكير الجرعات"]
    cards = panel("الأدوية — قريبًا", "هذا القسم سيتم تجهيزه لاحقًا لمراجعة الأدوية والمكملات والأسئلة المهمة لطبيب الأورام. حاليًا لا تغير أي دواء أو جرعة بدون الطبيب.", kind="mission")
    cards += panel("قاعدة أمان", MEDICINE_ANSWER, kind="danger-panel")
    cards += "".join(panel(item, "وحدة مخططة للنسخة القادمة.", kind="compact") for item in planned)
    html(f'<section class="visual-grid two">{cards}</section>')


def load_courses() -> list[dict[str, str]]:
    path = Path(__file__).with_name("courses.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def learning_module(active: str) -> None:
    active = st.selectbox(
        "اختر شريحة التعلم",
        list(LEARNING_SLIDES.keys()),
        index=list(LEARNING_SLIDES.keys()).index(active),
        format_func=lambda key: LEARNING_SLIDES[key],
        key="learning_slide",
    )
    content = {
        "intro": ("Marketing for Project Managers", "يعني إنك تعرف توصل قيمة المشروع للعميل، الإدارة، الفريق، والاستيكهولدرز بطريقة واضحة ومقنعة. مش إعلان فقط؛ هو value communication وtrust building."),
        "value": ("Stakeholder Value Proposition", "مين صاحب المصلحة؟ يهتم بإيه؟ المشروع هيسلم قيمة إيه؟ يخاف من أي خطر؟ والرسالة التي يجب أن يسمعها؟"),
        "position": ("Positioning للمشروع", "وضح لماذا المشروع مهم، ما المشكلة التي يحلها، ما المختلف فيه، ما القيمة التجارية، وما شكل النجاح."),
        "comm": ("Communication Plan as Marketing", "التقارير الأسبوعية، الداشبورد، executive summaries، claims/EOT narratives، presentations، وrisk communication كلها أصول تسويق للثقة لو اتعملت باحتراف."),
        "brand": ("Personal Branding", "كن واضحًا، موثوقًا، مرتبًا، استخدم البيانات، تكلم بلغة النتائج، ابنِ الثقة، وسلّم باستمرار."),
        "pitch": ("Client Pitch", "صيغة 30 ثانية: Problem → Impact → Solution → Evidence → Next action."),
    }
    if active in content:
        title, body = content[active]
        html(panel(title, body, kind="mission"))
    elif active == "case":
        html('<section class="visual-grid two">' + panel("تواصل ضعيف", "المشروع اتأخر بسبب ظروف خارجة عن إرادتنا، وهنحاول نعوض في الفترة القادمة.") + panel("تواصل قوي بأسلوب تسويقي", "التأخير الحالي أثره 12 يومًا على المسار الحرج. خطة التعافي تضيف وردية ثانية على نشاطين حرجين وتعيد 8 أيام خلال 3 أسابيع. نحتاج موافقة العميل اليوم لتقليل أثر نهاية المشروع.", kind="mission") + "</section>")
    elif active == "ai":
        ai_box("learning")
    else:
        cards = ""
        for course in load_courses():
            cards += panel(course["provider"], f'<b>{course["title"]}</b><br>{course["status"]}<br><a href="{course["link"]}">افتح المورد</a><br>آخر تحقق: {course["last_verified"]}<br>{course["notes"]}', kind="compact")
        html(f'<section class="visual-grid two">{cards}</section>')


def footer() -> None:
    html(
        """
<footer class="visual-footer">
  <span>Design and creation | </span>
  <span class="author">Ahmed Labib</span>
  <span> | </span><span class="mark">©️</span>
</footer>
"""
    )


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="A", layout="wide", initial_sidebar_state="collapsed")
    init_state()
    inject_css()
    module = st.session_state.module
    main_col, side_col = st.columns([1147, 248], gap="large")
    with side_col:
        module = st.selectbox(
            "SELECT PROGRAM",
            list(MODULES.keys()),
            index=list(MODULES.keys()).index(module),
            format_func=lambda key: MODULES[key],
            key="module",
        )
        html(sidebar(module))
    with main_col:
        html(f'<section class="visual-main">{topbar(module)}{kpis(module)}')
        if module == "food":
            food_module(st.session_state.food_slide)
        elif module == "medicine":
            medicine_module()
        else:
            learning_module(st.session_state.learning_slide)
        html("</section>")
    footer()


if __name__ == "__main__":
    main()
