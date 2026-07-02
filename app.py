from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

import pandas as pd
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

MODULES = {"food": "الغذاء", "medicine": "الأدوية", "lifestyle": "لايف ستايل وتكات ذكية", "learning": "التعلم"}
FOOD_SLIDES = {
    "why": "ليه ده وحش",
    "stop": "حاجات لازم تبطلها حالًا",
    "alts": "بدائل لذيذة",
    "scan": "امسح QR أو باركود",
    "ai": "اسأل الذكاء",
}
LEARNING_SLIDES = {
    "intro": "Introduction to Marketing For Project Manager",
    "lectures": "Lectures in Marketing For Project Manager",
    "ai": "AI Explanation",
    "courses": "Free Courses",
}
MEDICINE_SLIDES = {
    "summary": "الملخص التنفيذي",
    "method": "المنهجية",
    "evidence": "مصفوفة الأدلة",
    "quality": "جودة الدليل",
    "prophetic": "الطب النبوي",
    "interactions": "التداخلات",
    "conclusion": "الخلاصة",
}
LIFESTYLE_SLIDES = {
    "overview": "الخريطة الذكية",
    "library": "ملفات الأوتوفاجي والصيام",
    "plans": "خطط 100 يوم",
    "checks": "جداول وفحوصات الأمان",
    "diagrams": "Diagrams & Visuals",
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
    st.session_state.setdefault("medicine_slide", "summary")
    st.session_state.setdefault("lifestyle_slide", "overview")
    st.session_state.setdefault("learning_slide", "intro")
    if st.session_state.learning_slide not in LEARNING_SLIDES:
        st.session_state.learning_slide = "intro"
    if st.session_state.lifestyle_slide not in LIFESTYLE_SLIDES:
        st.session_state.lifestyle_slide = "overview"


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
[data-testid="stHorizontalBlock"] { direction: rtl; align-items: stretch; }
[data-testid="column"] { direction: rtl; }
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

div[role="radiogroup"][aria-label="SELECT PROGRAM"],
div[role="radiogroup"][aria-label="FOOD SLIDE NAV"],
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"],
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"],
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] {
  width: 100% !important;
}

div[data-testid="stRadio"]:has(div[role="radiogroup"][aria-label="SELECT PROGRAM"]) {
  min-height: calc(100vh - 96px);
  border-radius: 34px;
  padding: 30px 16px;
  background: rgba(6, 9, 22, 0.92);
  border: 1px solid var(--border);
  box-shadow: 0 12px 30px rgba(46, 107, 255, 0.1);
}

div[data-testid="stRadio"]:has(div[role="radiogroup"][aria-label="SELECT PROGRAM"]) label[data-testid="stWidgetLabel"] {
  position: relative;
  display: grid !important;
  grid-template-columns: 1fr 44px;
  gap: 12px;
  align-items: center;
  margin: 0 10px 52px !important;
  direction: rtl;
  color: var(--text) !important;
}

div[data-testid="stRadio"]:has(div[role="radiogroup"][aria-label="SELECT PROGRAM"]) label[data-testid="stWidgetLabel"]::before {
  content: "";
  grid-column: 2;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--cyan), var(--purple));
  box-shadow: 0 0 28px rgba(0, 224, 255, 0.45);
}

div[data-testid="stRadio"]:has(div[role="radiogroup"][aria-label="SELECT PROGRAM"]) label[data-testid="stWidgetLabel"] p {
  grid-column: 1;
  color: var(--text) !important;
  font-size: 17px !important;
  line-height: 1.05 !important;
  font-weight: 900 !important;
  letter-spacing: 0 !important;
  white-space: nowrap !important;
  text-align: right !important;
}

div[role="radiogroup"][aria-label="SELECT PROGRAM"] {
  display: grid !important;
  gap: 12px !important;
  margin: 0 16px 16px;
}

div[role="radiogroup"][aria-label="SELECT PROGRAM"] label[data-baseweb="radio"] {
  min-height: 46px;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 16px !important;
  border-radius: 999px !important;
  border: 1px solid transparent !important;
  background: transparent !important;
  color: rgba(240, 247, 255, 0.68) !important;
  transition: background 180ms ease, color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

div[role="radiogroup"][aria-label="SELECT PROGRAM"] label[data-baseweb="radio"]:hover {
  background: rgba(255, 255, 255, 0.05) !important;
  color: rgba(240, 247, 255, 0.92) !important;
}

div[role="radiogroup"][aria-label="SELECT PROGRAM"] label[data-baseweb="radio"]:has(input:checked) {
  color: var(--text) !important;
  border-color: rgba(0, 224, 255, 0.78) !important;
  background: linear-gradient(115deg, rgba(0, 224, 255, 0.96), rgba(46, 107, 255, 0.9) 54%, rgba(173, 64, 255, 0.86)) !important;
  box-shadow: 0 14px 28px rgba(0, 224, 255, 0.22), 0 10px 26px rgba(173, 64, 255, 0.26);
}

div[role="radiogroup"][aria-label="SELECT PROGRAM"] label[data-baseweb="radio"] > div:first-child,
div[role="radiogroup"][aria-label="SELECT PROGRAM"] label[data-baseweb="radio"] > input,
div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] label[data-baseweb="radio"] > div:first-child,
div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] label[data-baseweb="radio"] > input,
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] label[data-baseweb="radio"] > div:first-child,
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] label[data-baseweb="radio"] > input,
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] label[data-baseweb="radio"] > div:first-child,
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] label[data-baseweb="radio"] > input,
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] label[data-baseweb="radio"] > div:first-child,
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] label[data-baseweb="radio"] > input {
  display: none !important;
}

div[role="radiogroup"][aria-label="SELECT PROGRAM"] p {
  color: inherit !important;
  font-weight: 900 !important;
  text-align: center !important;
}

div[role="radiogroup"][aria-label="FOOD SLIDE NAV"],
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"],
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"],
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] {
  display: flex !important;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-start;
  direction: rtl;
  gap: 30px !important;
  min-height: 42px;
  margin: 0 0 24px;
  padding: 0 2px 7px;
  border: 0 !important;
  background: transparent !important;
}

div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] label[data-baseweb="radio"],
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] label[data-baseweb="radio"],
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] label[data-baseweb="radio"],
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] label[data-baseweb="radio"] {
  position: relative;
  min-height: 38px;
  padding: 0 14px !important;
  border: 1px solid rgba(0, 224, 255, 0.16) !important;
  border-radius: 999px !important;
  background: rgba(19, 27, 52, 0.34) !important;
  color: rgba(190, 216, 238, 0.82) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  transition: background 180ms ease, border-color 180ms ease, color 180ms ease, opacity 180ms ease, transform 220ms ease;
}

div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] label[data-baseweb="radio"]::after,
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] label[data-baseweb="radio"]::after,
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] label[data-baseweb="radio"]::after,
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] label[data-baseweb="radio"]::after {
  content: "";
  position: absolute;
  right: 0;
  left: 0;
  bottom: -5px;
  height: 2px;
  transform: scaleX(0);
  transform-origin: center;
  background: linear-gradient(90deg, var(--purple), var(--pink));
  box-shadow: 0 0 12px rgba(173, 64, 255, 0.7);
  transition: transform 240ms ease;
}

div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] label[data-baseweb="radio"]:hover,
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] label[data-baseweb="radio"]:hover,
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] label[data-baseweb="radio"]:hover,
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] label[data-baseweb="radio"]:hover {
  color: rgba(235, 248, 255, 0.96) !important;
  background: rgba(255, 255, 255, 0.055) !important;
  border-color: rgba(0, 224, 255, 0.28) !important;
}

div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked),
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked),
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked),
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked) {
  color: var(--text) !important;
  background: rgba(46, 107, 255, 0.16) !important;
  border-color: rgba(173, 64, 255, 0.38) !important;
}

div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked)::after,
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked)::after,
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked)::after,
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] label[data-baseweb="radio"]:has(input:checked)::after {
  transform: scaleX(1);
}

div[role="radiogroup"][aria-label="FOOD SLIDE NAV"] p,
div[role="radiogroup"][aria-label="MEDICINE SLIDE NAV"] p,
div[role="radiogroup"][aria-label="LIFESTYLE SLIDE NAV"] p,
div[role="radiogroup"][aria-label="LEARNING SLIDE NAV"] p {
  color: inherit !important;
  font-size: 14px !important;
  font-weight: 900 !important;
  text-align: right !important;
}

.stats-enter {
  animation: statsEnter 360ms ease both;
}

@keyframes statsEnter {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
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

.visual-main { max-width: 1147px; padding-top: 8px; direction: rtl; }
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
.learning-table { width: 100%; border-collapse: separate; border-spacing: 0 10px; direction: ltr; }
.learning-table th { color: var(--cyan); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; text-align: left; padding: 0 14px 4px; }
.learning-table td { color: rgba(222, 235, 249, 0.9); font-size: 14px; line-height: 1.55; padding: 16px 14px; background: rgba(19, 27, 52, 0.56); border-top: 1px solid rgba(51, 82, 133, 0.42); border-bottom: 1px solid rgba(51, 82, 133, 0.42); vertical-align: top; }
.learning-table td:first-child { border-left: 1px solid rgba(51, 82, 133, 0.42); border-radius: 18px 0 0 18px; color: var(--cyan); font-weight: 900; white-space: nowrap; }
.learning-table td:last-child { border-right: 1px solid rgba(51, 82, 133, 0.42); border-radius: 0 18px 18px 0; }
.lecture-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.lecture-chip { display: inline-flex; align-items: center; min-height: 28px; padding: 0 10px; border-radius: 999px; color: var(--cyan); background: rgba(0, 224, 255, 0.08); border: 1px solid rgba(0, 224, 255, 0.22); font-size: 12px; font-weight: 900; }
.lecture-detail { margin-top: 18px; border-radius: 26px; border: 1px solid rgba(51, 82, 133, 0.42); background: rgba(14, 19, 38, 0.62); overflow: hidden; box-shadow: 0 12px 24px rgba(0, 224, 255, 0.08); direction: ltr; }
.lecture-detail summary { cursor: pointer; list-style: none; padding: 22px 26px; color: var(--text); font-size: 20px; font-weight: 900; background: linear-gradient(90deg, rgba(0, 224, 255, 0.12), rgba(173, 64, 255, 0.1)); }
.lecture-detail summary::-webkit-details-marker { display: none; }
.lecture-detail summary span { display: block; margin-top: 7px; color: var(--muted); font-size: 13px; font-weight: 700; line-height: 1.55; }
.lecture-body { padding: 22px 26px 26px; }
.lecture-section { margin-top: 16px; padding: 18px 20px; border-radius: 20px; border: 1px solid rgba(51, 82, 133, 0.34); background: rgba(19, 27, 52, 0.46); }
.lecture-section h3 { margin: 0 0 10px; color: var(--cyan); font-size: 16px; font-weight: 900; }
.lecture-section p { color: rgba(222, 235, 249, 0.9); font-size: 14px; line-height: 1.72; margin: 8px 0 0; }
.lecture-section ul { margin: 10px 0 0; padding-left: 20px; color: rgba(222, 235, 249, 0.9); }
.lecture-section li { margin: 6px 0; font-size: 14px; line-height: 1.65; }
.lecture-point { margin: 9px 0; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; align-items: start; }
.lecture-en { color: rgba(222, 235, 249, 0.92); font-size: 14px; line-height: 1.68; direction: ltr; text-align: left; }
.lecture-ar { direction: rtl; text-align: right; color: rgba(124, 232, 255, 0.94); font-size: 13px; line-height: 1.75; border-right: 2px solid rgba(0, 224, 255, 0.45); padding: 4px 10px 4px 0; }
.lecture-ar b { color: var(--cyan); font-weight: 900; }
.lifestyle-table { width: 100%; border-collapse: separate; border-spacing: 0 10px; direction: rtl; }
.lifestyle-table th { color: var(--cyan); font-size: 12px; text-align: right; padding: 0 14px 4px; }
.lifestyle-table td { color: rgba(222, 235, 249, 0.92); font-size: 14px; line-height: 1.65; padding: 15px 14px; background: rgba(19, 27, 52, 0.56); border-top: 1px solid rgba(51, 82, 133, 0.42); border-bottom: 1px solid rgba(51, 82, 133, 0.42); vertical-align: top; }
.lifestyle-table td:first-child { border-right: 1px solid rgba(51, 82, 133, 0.42); border-radius: 0 18px 18px 0; color: var(--cyan); font-weight: 900; }
.lifestyle-table td:last-child { border-left: 1px solid rgba(51, 82, 133, 0.42); border-radius: 18px 0 0 18px; }
.smart-checks { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 12px; }
.smart-check { min-height: 72px; padding: 16px 18px; border-radius: 20px; color: rgba(222, 235, 249, 0.92); background: rgba(19, 27, 52, 0.52); border: 1px solid rgba(51, 82, 133, 0.38); line-height: 1.6; }
.smart-check b { display: block; color: var(--cyan); margin-bottom: 4px; }
.life-flow { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 16px; direction: rtl; }
.life-node { position: relative; min-height: 126px; padding: 18px; border-radius: 24px; background: linear-gradient(135deg, rgba(0, 224, 255, 0.13), rgba(173, 64, 255, 0.09)); border: 1px solid rgba(0, 224, 255, 0.26); box-shadow: 0 12px 24px rgba(0, 224, 255, 0.08); }
.life-node strong { display: block; color: var(--text); font-size: 17px; margin-bottom: 8px; }
.life-node span { color: var(--muted); font-size: 13px; line-height: 1.65; }
.life-timeline { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin-top: 14px; direction: rtl; }
.life-step { padding: 15px; border-radius: 18px; background: rgba(14, 19, 38, 0.7); border: 1px solid rgba(51, 82, 133, 0.42); }
.life-step b { color: var(--yellow); display: block; margin-bottom: 6px; }
.life-step span { color: var(--muted); font-size: 13px; line-height: 1.55; }
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
  .lecture-point { grid-template-columns: 1fr; gap: 6px; }
  .smart-checks, .life-flow, .life-timeline { grid-template-columns: 1fr; }
  .bars { gap: 12px; overflow-x: auto; }
}
</style>
"""
    )


def topbar(module: str) -> str:
    return f"""
<header class="visual-topbar">
  <div>
    <h1>{FULL_TITLE}</h1>
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
            ("عناصر مُقيّمة", "20+", "غذاء ومكملات وتركيبات", "var(--cyan)"),
            ("وصفات نبوية", "13", "مقارنة بالدليل الحديث", "var(--green)"),
            ("تداخلات", "10", "تحذيرات عملية", "var(--pink)"),
            ("قاعدة الأمان", "طبيب", "لا تغيير علاج ذاتيًا", "var(--yellow)"),
        ]
    elif module == "lifestyle":
        data = [
            ("ملفات", "7", "أوتوفاجي وصيام بالعربي", "var(--cyan)"),
            ("خطط", "3", "100 يوم حسب الحالة", "var(--green)"),
            ("أمان", "STOP", "معايير إيقاف واضحة", "var(--pink)"),
            ("قرار", "طبيب", "خصوصًا مع تاريخ سرطان", "var(--yellow)"),
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


def food_slide_nav(slide: str) -> str:
    return st.radio(
        "FOOD SLIDE NAV",
        list(FOOD_SLIDES.keys()),
        index=list(FOOD_SLIDES.keys()).index(slide),
        format_func=lambda key: FOOD_SLIDES[key],
        key="food_slide",
        horizontal=True,
        label_visibility="collapsed",
    )


def food_module(slide: str) -> None:
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


def rich_text(text: str) -> str:
    value = escape(text.strip())
    value = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", value)
    return value.replace("\n", "<br>")


@st.cache_data(show_spinner=False)
def load_medicine_report() -> dict:
    path = Path(__file__).parent / "medicine" / "medicine_app.py"
    if not path.exists():
        return {"sections": {}, "tables": []}
    source = path.read_text(encoding="utf-8")
    match = re.search(r"DATA\s*=\s*json\.loads\(r'''(.*?)'''\)", source, flags=re.S)
    if not match:
        return {"sections": {}, "tables": []}
    return json.loads(match.group(1))


def medicine_slide_nav(active: str) -> str:
    return st.radio(
        "MEDICINE SLIDE NAV",
        list(MEDICINE_SLIDES.keys()),
        index=list(MEDICINE_SLIDES.keys()).index(active),
        format_func=lambda key: MEDICINE_SLIDES[key],
        key="medicine_slide",
        horizontal=True,
        label_visibility="collapsed",
    )


def medicine_text_section(title: str, text: str, kind: str = "") -> None:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        html(panel(title, "لا توجد بيانات كافية في ملف الأدوية.", kind=kind or "warning-panel"))
        return
    cards = "".join(
        panel(title if idx == 0 else f"{title} · {idx + 1}", rich_text(part), kind=kind if idx == 0 else "compact")
        for idx, part in enumerate(paragraphs)
    )
    html(f'<section class="visual-grid two">{cards}</section>')


def medicine_table_cards(title: str, table: dict, key_prefix: str) -> None:
    header = table.get("header", [])
    rows = table.get("rows", [])
    query = st.text_input(
        f"بحث داخل {title}",
        key=f"{key_prefix}_search",
        placeholder="اكتب اسم مادة، تداخل، أو كلمة من الجدول...",
        label_visibility="collapsed",
    ).strip().lower()
    if query:
        rows = [row for row in rows if query in " ".join(str(cell).lower() for cell in row)]

    html(panel(title, f"عدد النتائج المعروضة: {len(rows)}", kind="mission"))
    if not rows:
        html(panel("لا توجد نتائج", "جرّب كلمة أبسط أو امسح البحث.", kind="warning-panel"))
        return

    cards = []
    for row in rows:
        padded = list(row) + [""] * max(0, len(header) - len(row))
        row_title = rich_text(str(padded[0])) if padded else "عنصر"
        details = []
        for label, cell in zip(header[1:], padded[1:]):
            if str(cell).strip():
                details.append(f"<li><b>{escape(str(label))}:</b> {rich_text(str(cell))}</li>")
        cards.append(
            f'<article class="visual-panel compact"><h2>{row_title}</h2>'
            f'<ul>{"".join(details)}</ul></article>'
        )
    html(f'<section class="visual-grid two">{"".join(cards)}</section>')


def medicine_module(active: str) -> None:
    report = load_medicine_report()
    sections = report.get("sections", {})
    tables = report.get("tables", [])

    html(panel(
        "قاعدة أمان للأدوية والمكملات",
        "هذا القسم للتوعية بالتداخلات وجودة الدليل فقط. لا توقف أو تغير أي دواء أو جرعة، ولا تبدأ مكملات مركزة بدون طبيب الأورام.",
        kind="danger-panel",
    ))

    if not sections:
        html(panel("ملف الأدوية غير جاهز", "لم أتمكن من قراءة بيانات medicine_app.py داخل مجلد medicine.", kind="warning-panel"))
        return

    if active == "summary":
        medicine_text_section("الملخص التنفيذي", sections["الملخص التنفيذي"]["text"], "mission")
    elif active == "method":
        medicine_text_section("منهجية البحث وحدود الاستدلال", sections["منهجية البحث وحدود الاستدلال"]["text"])
        cards = [
            panel("الأعلى أولوية", "المراجعات المنهجية والتحليلات التلوية، ثم التجارب العشوائية المحكمة.", kind="compact"),
            panel("لا نساوي المختبر بالإنسان", "قتل خلايا في طبق المختبر لا يعني علاج ورم عند الإنسان.", kind="compact"),
            panel("الغذاء غير المكمل", "الغذاء الكامل أقل خطورة عادة من المستخلصات والكبسولات عالية الجرعة.", kind="compact"),
        ]
        html(f'<section class="visual-grid three">{"".join(cards)}</section>')
    elif active == "evidence":
        section = sections["الأغذية والبهارات والمشروبات والتركيبات الطبيعية"]
        medicine_text_section("الأغذية والتركيبات الطبيعية", section["text"], "mission")
        if len(tables) > 0:
            medicine_table_cards("العناصر ذات الدليل البشري الأكثر فائدة", tables[0], "medicine_best")
        if len(tables) > 1:
            medicine_table_cards("عناصر واعدة لكن الدليل الأورامي غير حاسم", tables[1], "medicine_promising")
    elif active == "quality":
        medicine_text_section("مستويات الدليل السريري وتقييم الجودة", sections["مستويات الدليل السريري وتقييم الجودة"]["text"])
        if len(tables) > 2:
            medicine_table_cards("جدول تقدير الجودة العملية للأدلة", tables[2], "medicine_quality")
    elif active == "prophetic":
        medicine_text_section("الطب النبوي في الميزان العلمي", sections["الطب النبوي في الميزان العلمي"]["text"])
        if len(tables) > 3:
            medicine_table_cards("المقارنة بين العلاجات النبوية وأدلتها الحديثة", tables[3], "medicine_prophetic")
    elif active == "interactions":
        medicine_text_section("التداخلات الدوائية وموانع الاستعمال العملية", sections["التداخلات الدوائية وموانع الاستعمال العملية"]["text"], "danger-panel")
        if len(tables) > 4:
            medicine_table_cards("جدول التداخلات الأهم عمليًا", tables[4], "medicine_interactions")
    else:
        medicine_text_section("فجوات المعرفة والخلاصة النهائية", sections["فجوات المعرفة والتوصيات البحثية"]["text"], "warning-panel")


def lifestyle_slide_nav(active: str) -> str:
    if active not in LIFESTYLE_SLIDES:
        active = "overview"
    return st.radio(
        "LIFESTYLE SLIDE NAV",
        list(LIFESTYLE_SLIDES.keys()),
        index=list(LIFESTYLE_SLIDES.keys()).index(active),
        format_func=lambda key: LIFESTYLE_SLIDES[key],
        key="lifestyle_slide",
        horizontal=True,
        label_visibility="collapsed",
    )


def lifestyle_source_folder() -> Path:
    root = Path(__file__).parent
    preferred = root / "Autophagy_Fasting_7_Separate_Arabic_Files"
    if preferred.exists():
        return preferred
    arabic = root / "ملفات_الأوتوفاجي_والصيام_7_ملفات_منفصلة" / "ملفات_الأوتوفاجي_والصيام_بالعربي"
    return arabic


def is_lifestyle_heading(text: str) -> bool:
    clean = text.strip()
    if not clean or clean.startswith("•") or len(clean) > 80:
        return False
    if clean in {"الخطوة", "المرحلة", "ماذا يحدث؟", "الأيام", "الهدف الأساسي", "التركيب اليومي", "قاعدة القرار", "النمط", "مثال النافذة", "التكرار", "التركيز", "المؤشر", "الاتجاه المقبول", "عتبة التدخل"}:
        return False
    return bool(re.search(r"(الخلاصة|تنبيه|كيف|آلية|هرم|جدول|خطة|شروط|مبادئ|متى|قائمة|بوابة|العلاقة|التفرقة|معايير|المتابعة|الادعاءات|التدريجية|المرحلية|الإيقاف)", clean))


@st.cache_data(show_spinner=False)
def load_lifestyle_docs() -> list[dict[str, object]]:
    folder = lifestyle_source_folder()
    docs: list[dict[str, object]] = []
    if not folder.exists():
        return docs
    for path in sorted(folder.glob("*.docx")):
        paragraphs = read_docx_paragraphs(path)
        if not paragraphs:
            continue
        sections: list[dict[str, object]] = []
        current: dict[str, object] | None = None
        for paragraph in paragraphs[3:]:
            if is_lifestyle_heading(paragraph):
                if current:
                    sections.append(current)
                current = {"title": paragraph, "blocks": []}
            elif current:
                current["blocks"].append(paragraph)
        if current:
            sections.append(current)
        docs.append(
            {
                "number": re.match(r"(\d+)", path.name).group(1) if re.match(r"(\d+)", path.name) else str(len(docs) + 1),
                "title": paragraphs[0],
                "subtitle": paragraphs[1] if len(paragraphs) > 1 else "",
                "meta": paragraphs[2] if len(paragraphs) > 2 else "",
                "sections": sections,
                "file": path.name,
                "all_text": " ".join(paragraphs),
            }
        )
    return docs


def lifestyle_table(title: str, headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{rich_text(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<article class='visual-panel'><h2>{escape(title)}</h2><table class='lifestyle-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></article>"


def lifestyle_flow() -> str:
    nodes = [
        ("حالة الشخص", "مريض أثناء العلاج؟ متعافٍ مستقر؟ بالغ سليم؟ القرار يبدأ من الحالة وليس من ترند الصيام."),
        ("بوابة الأمان", "وزن، شهية، سوائل، أدوية، سكر، ضغط، أعراض، وموافقة الطبيب عند وجود سرطان."),
        ("الخطة المناسبة", "حماية تغذية أثناء العلاج، تدرج محدود بعد التعافي، أو صيام محافظ للبالغ السليم."),
        ("المتابعة والإيقاف", "أي فقد وزن، دوخة، جفاف، هبوط سكر، أو ضعف تناول يعني نوقف ونراجع الفريق."),
    ]
    return "<div class='life-flow'>" + "".join(f"<div class='life-node'><strong>{title}</strong><span>{body}</span></div>" for title, body in nodes) + "</div>"


def lifestyle_timeline() -> str:
    steps = [
        ("1-10", "تقييم وتهيئة بدون قفز"),
        ("11-30", "تثبيت المدخول والنوم والسوائل"),
        ("31-60", "تدرج بسيط إذا المؤشرات مستقرة"),
        ("61-90", "تحسين الجودة لا التشدد"),
        ("91-100", "مراجعة واستدامة أو إيقاف"),
    ]
    return "<div class='life-timeline'>" + "".join(f"<div class='life-step'><b>{d}</b><span>{t}</span></div>" for d, t in steps) + "</div>"


def lifestyle_overview(docs: list[dict[str, object]]) -> None:
    html(panel("لايف ستايل وتكات ذكية", "مساحة عملية تجمع ملفات الأوتوفاجي والصيام في شكل قرارات آمنة: ماذا ينفع؟ ماذا لا ينفع؟ متى نوقف؟ ومتى لازم الطبيب يكون في الصورة؟", kind="mission"))
    html(lifestyle_flow())
    rows = [
        ["أثناء علاج السرطان", "لا صيام علاجي", "الأولوية: تغذية، سوائل، بروتين، تحمل العلاج، وموافقة فريق الأورام."],
        ["متعافٍ مستقر بعد العلاج", "توقيت وجبات تدريجي فقط", "يبدأ بعد الاستقرار الطبي وغياب فقد الوزن وسوء التغذية."],
        ["بالغ سليم", "صيام محدد بالوقت بحذر", "تدرج محافظ، جودة أكل، نوم، سوائل، ولا صيام طويل."],
        ["أي أعراض إنذار", "إيقاف ومراجعة", "دوخة، جفاف، هبوط سكر، قيء/إسهال، فقد وزن، ضعف تناول، أو تدهور وظيفة."],
    ]
    html(lifestyle_table("مصفوفة القرار السريع", ["الحالة", "القرار", "التفسير العملي"], rows))
    html(panel("تنبيه أمان", DISCLAIMER, kind="danger-panel"))


def lifestyle_library(docs: list[dict[str, object]]) -> None:
    query = st.text_input("بحث في ملفات اللايف ستايل", key="lifestyle_search", placeholder="ابحث: أوسومي، 100 يوم، معايير الإيقاف، علاج السرطان...", label_visibility="collapsed").strip().lower()
    filtered = [doc for doc in docs if not query or query in str(doc["all_text"]).lower() or query in str(doc["title"]).lower()]
    rows = [[doc["number"], doc["title"], doc["subtitle"], doc["file"]] for doc in filtered]
    html(lifestyle_table("فهرس ملفات الأوتوفاجي والصيام", ["#", "الملف", "المحتوى", "Source"], rows or [["-", "لا توجد نتائج", "جرّب كلمة بحث أبسط", "-"]]))
    if not filtered:
        return
    options = {f"{doc['number']} · {doc['title']}": doc for doc in filtered}
    selected = st.selectbox("اختر ملفًا لعرضه", list(options.keys()), key="selected_lifestyle_doc")
    doc = options[selected]
    cards = [panel(str(doc["title"]), f"{doc['subtitle']}<br>{doc['meta']}", kind="mission")]
    for section in doc["sections"][:10]:
        bullets = [str(block).replace("•", "").strip() for block in section["blocks"] if str(block).strip().startswith("•")][:8]
        paragraphs = [str(block) for block in section["blocks"] if not str(block).strip().startswith("•")]
        body = rich_text(" ".join(paragraphs[:5])) if paragraphs else "نقاط عملية من الملف."
        cards.append(panel(str(section["title"]), body, bullets, "compact"))
    html(f'<section class="visual-grid two">{"".join(cards)}</section>')


def lifestyle_plans() -> None:
    html(panel("خطط 100 يوم حسب الحالة", "هذه ليست وصفة علاجية. هي تنظيم آمن للقرار: المريض أثناء العلاج له أولوية مختلفة عن المتعافي المستقر وعن البالغ السليم.", kind="mission"))
    html(lifestyle_timeline())
    rows = [
        ["مريض أثناء العلاج", "وجبات منتظمة بلا صيام متعمد", "بروتين، سوائل، سعرات كافية، متابعة أعراض", "أي فقد وزن أو ضعف تناول أو جفاف"],
        ["متعافٍ مستقر", "12:12 ثم تدرج محدود إذا مستقر", "ثبات وزن وطاقة ومدخول كافٍ", "تعب، فقد وزن، اضطراب أدوية، هبوط سكر"],
        ["بالغ سليم", "12:12 ثم 13:11 ثم 14:10 حسب التحمل", "جودة غذاء، نوم، ترطيب، لا أكل ليلي", "دوخة، نهم، اضطراب نوم، أداء ضعيف"],
    ]
    html(lifestyle_table("جدول المقارنة بين الخطط", ["الفئة", "النمط", "الأولوية", "متى نوقف؟"], rows))


def lifestyle_checks() -> None:
    checks = [
        ("قبل البداية", "وزن ثابت، شهية مقبولة، سوائل كافية، لا قيء/إسهال مستمر، ومراجعة الأدوية."),
        ("أثناء العلاج", "لا تغيير توقيت أكل أو صيام بدون موافقة صريحة من طبيب الأورام وأخصائي التغذية."),
        ("أدوية حساسة", "سكري، ضغط، مضادات تجلط، كورتيزون، أو أدوية لازم مع الطعام = مراجعة طبية قبل أي نافذة صيام."),
        ("معايير إيقاف فورية", "دوخة شديدة، إغماء، قلة بول، هبوط سكر، قيء/إسهال، قرح فم تمنع الأكل، أو فقد وزن مستمر."),
        ("متابعة أسبوعية", "وزن، طاقة، شهية، نوم، حركة، سوائل، أعراض هضمية، ونسبة الالتزام بالخطة."),
        ("سؤال الطبيب", "هل توقيت الوجبات مناسب للعلاج؟ هل أدويتي تتأثر؟ ما الحد الأدنى للبروتين والسوائل؟"),
    ]
    html("<article class='visual-panel'><h2>Checklist الأمان الذكي</h2><div class='smart-checks'>" + "".join(f"<div class='smart-check'><b>{title}</b>{body}</div>" for title, body in checks) + "</div></article>")
    rows = [
        ["الوزن", "مرة أسبوعيًا", "ثبات أو حسب خطة الطبيب", "فقد غير مقصود مستمر"],
        ["كمية الطعام", "يوميًا أثناء العلاج", "تحقيق هدف الفريق", "أقل من 50% لأكثر من أسبوع"],
        ["السوائل والبول", "يوميًا", "بول منتظم ولا عطش شديد", "قلة بول، دوخة، جفاف"],
        ["القوة والوظيفة", "أسبوعيًا", "نشاط ثابت", "ضعف واضح أو سقوط أو تعب غير معتاد"],
    ]
    html(lifestyle_table("جدول متابعة مختصر", ["المؤشر", "التكرار", "المقبول", "عتبة التدخل"], rows))


def lifestyle_diagrams() -> None:
    html(panel("Diagrams & Visual Illustrations", "رسومات قرار مبسطة تربط الأوتوفاجي والصيام بالأمان العملي، بدون ادعاء علاج السرطان.", kind="mission"))
    html(lifestyle_flow())
    html(lifestyle_timeline())
    rows = [
        ["نقص مغذيات", "إشارات خلوية تتغير", "قد يزيد نشاط إعادة التدوير داخل الخلية", "لا يساوي علاج سرطان"],
        ["صيام طويل", "ضغط أعلى على الجسم", "قد يرفع مخاطر الجفاف/الهبوط/نقص التغذية", "غير مناسب أثناء العلاج بدون طبيب"],
        ["توقيت وجبات محافظ", "نوم وأكل أكثر انتظامًا", "قد يساعد الصحة العامة عند المناسبين", "يتوقف عند أعراض إنذار"],
    ]
    html(lifestyle_table("خريطة مبسطة: من السلوك إلى القرار", ["السلوك", "الأثر المحتمل", "المعنى", "حد الأمان"], rows))


def lifestyle_module(active: str) -> None:
    docs = load_lifestyle_docs()
    if not docs:
        html(panel("ملفات اللايف ستايل غير موجودة", "لم أجد ملفات الأوتوفاجي والصيام داخل مجلد المشروع.", kind="warning-panel"))
        return
    if active == "overview":
        lifestyle_overview(docs)
    elif active == "library":
        lifestyle_library(docs)
    elif active == "plans":
        lifestyle_plans()
    elif active == "checks":
        lifestyle_checks()
    else:
        lifestyle_diagrams()


def load_courses() -> list[dict[str, str]]:
    path = Path(__file__).with_name("courses.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def learning_slide_nav(active: str) -> str:
    if active not in LEARNING_SLIDES:
        active = "intro"
    return st.radio(
        "LEARNING SLIDE NAV",
        list(LEARNING_SLIDES.keys()),
        index=list(LEARNING_SLIDES.keys()).index(active),
        format_func=lambda key: LEARNING_SLIDES[key],
        key="learning_slide",
        horizontal=True,
        label_visibility="collapsed",
    )


def split_numbered_items(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?=\d+\.\s*)", compact)
    return [re.sub(r"^\d+\.\s*", "", part).strip() for part in parts if part.strip()]


EGYPTIAN_EXACT_TRANSLATIONS = {
    "Learning Outcomes": "هتطلع من الجزء ده فاهم إيه وتعرف تعمل إيه عمليًا.",
    "Session Flow": "تقسيمة وقت المحاضرة خطوة بخطوة.",
    "Applied Output": "المخرج العملي اللي المفروض تسلمه أو تطبقه في الآخر.",
    "Source component": "جزء المصدر أو نوع المعلومة اللي بنراجعها.",
    "What it contributes": "إيه القيمة أو الإضافة اللي الجزء ده بيقدمها.",
    "Critical assessment": "تقييم نقدي: هل الكلام قوي، ناقص، ولا فيه تحيز؟",
    "Definition and examples": "تعريف وأمثلة تساعدنا نفهم الموضوع عمليًا.",
    "Benefits": "الفوائد المتوقعة، بس لازم نربطها بدليل وقياس مش كلام عام.",
    "Challenges": "التحديات اللي ممكن تعطل التنفيذ أو تقلل النتيجة.",
    "Lifecycle phases": "مراحل دورة حياة المشروع من التخطيط للتنفيذ والقياس والإغلاق.",
    "Tool taxonomy": "تصنيف الأدوات: كل أداة بتخدم إيه ومين يستخدمها.",
    "Productive promotion": "هنا فيه ترويج لأداة معينة، فلازم نقيمها بحياد.",
    "Best practices": "أفضل ممارسات نقدر نحولها لقواعد تشغيل واضحة.",
    "DECISION RULE": "قاعدة قرار: لا تعتمد على رقم أو ادعاء قبل ما تعرف مصدره وسياقه.",
    "APPLIED WORKSHOP": "تطبيق عملي: هنحول الكلام لتمرين أو مخرج واضح.",
    "KNOWLEDGE CHECK": "مراجعة فهم: أسئلة تتأكد إن الفكرة وصلت واتطبقت.",
    "Applied learning and assessment": "تعلم تطبيقي وتقييم: المطلوب هنا إنك تطبق مش تحفظ.",
}


EGYPTIAN_TERM_TRANSLATIONS = {
    "marketing project management": "إدارة مشروعات التسويق",
    "marketing objective": "هدف تسويقي",
    "approved scope of work": "scope شغل معتمد",
    "scope of work": "نطاق الشغل",
    "time-phased delivery plan": "خطة تسليم متقسمة على الوقت",
    "accountable cross-functional team": "فريق من كذا تخصص وكل واحد مسؤول",
    "controlled budget": "ميزانية متراقبة",
    "measurement architecture": "نظام قياس واضح",
    "documented decision process": "طريقة قرار متوثقة",
    "stakeholder": "صاحب مصلحة",
    "stakeholders": "أصحاب المصلحة",
    "governance": "حوكمة",
    "strategic alignment": "توافق مع الاستراتيجية",
    "delivery": "التسليم",
    "measurement": "القياس",
    "applied learning": "تعلم تطبيقي",
    "evidence": "دليل",
    "evidence-backed claims": "ادعاءات مدعومة بدليل",
    "vendor-led promotion": "ترويج جاي من البائع",
    "source quality": "جودة المصدر",
    "decision useability": "قابلية استخدامه في القرار",
    "executive papers": "مذكرات تنفيذية",
    "business cases": "دراسات جدوى / business case",
    "procurement decisions": "قرارات الشراء",
    "session flow": "تقسيمة المحاضرة",
    "applied output": "المخرج العملي",
    "learning outcomes": "نواتج التعلم",
    "product launch": "إطلاق منتج",
    "integrated campaign": "حملة متكاملة",
    "content / seo program": "برنامج محتوى وSEO",
    "lifecycle / email": "رحلة عميل وإيميل",
    "brand refresh": "تحديث البراند",
    "event / experience": "فعالية أو تجربة",
    "primary objective": "الهدف الأساسي",
    "typical complexity drivers": "أسباب التعقيد المعتادة",
    "core deliverables": "المخرجات الأساسية",
    "dashboard": "داشبورد",
    "risk": "مخاطر",
    "risks": "مخاطر",
    "budget": "ميزانية",
    "schedule": "جدول زمني",
    "capacity": "قدرة الفريق",
    "resource": "مورد",
    "resources": "موارد",
    "change control": "ضبط التغييرات",
    "communication": "تواصل",
    "collaboration": "تعاون",
    "analytics": "تحليلات",
    "compliance": "التزام",
    "ai governance": "حوكمة الذكاء الاصطناعي",
    "vendor evaluation": "تقييم الموردين",
    "operating model": "نموذج تشغيل",
    "roadmap": "خارطة طريق",
    "maturity model": "نموذج نضج",
}


def replace_terms_for_egyptian(text: str) -> str:
    translated = text
    for source, target in sorted(EGYPTIAN_TERM_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(re.escape(source), target, translated, flags=re.I)
    translated = re.sub(r"\bmin\b", "دقيقة", translated, flags=re.I)
    translated = re.sub(r"\band\b", "و", translated, flags=re.I)
    translated = re.sub(r"\bor\b", "أو", translated, flags=re.I)
    translated = re.sub(r"\bwith\b", "مع", translated, flags=re.I)
    translated = re.sub(r"\binto\b", "إلى", translated, flags=re.I)
    translated = re.sub(r"\bfor\b", "لـ", translated, flags=re.I)
    return translated


def egyptian_translation(text: str) -> str:
    clean = re.sub(r"\s+", " ", str(text).strip())
    if not clean:
        return ""
    if clean in EGYPTIAN_EXACT_TRANSLATIONS:
        return EGYPTIAN_EXACT_TRANSLATIONS[clean]
    lowered = clean.lower()
    if lowered.startswith("marketing project management is"):
        return "إدارة مشروعات التسويق يعني إنك تحول هدف تسويقي واضح لخطة شغل متقسمة، بميزانية، فريق مسؤول، ومؤشرات قياس واضحة."
    if " | " in clean and "min" in lowered:
        return "تقسيمة الوقت: " + replace_terms_for_egyptian(clean)
    if "?" in clean:
        return "السؤال: " + replace_terms_for_egyptian(clean)
    replaced = replace_terms_for_egyptian(clean)
    if replaced != clean:
        return "المقصود: " + replaced
    if any(word in lowered for word in ["define", "classify", "connect", "distinguish", "audit", "establish"]):
        return "المطلوب هنا إنك تفهم النقطة وتحوّلها لطريقة شغل عملية، مش تحفظها كنص."
    if any(word in lowered for word in ["plan", "control", "measure", "review", "evaluate"]):
        return "الفكرة هنا إنك تدير الموضوع بخطة، متابعة، وقياس واضح عشان القرار يبقى مضبوط."
    return "شرح مبسط: النقطة دي بتوضح فكرة عملية لازم مدير المشروع يفهمها ويطبقها في الشغل اليومي."


def bilingual_point(text: str) -> str:
    return (
        "<div class='lecture-point'>"
        f"<div class='lecture-en'>{escape(str(text))}</div>"
        f"<div class='lecture-ar'>{escape(egyptian_translation(str(text)))}</div>"
        "</div>"
    )


def lecture_heading(title: str) -> str:
    return (
        f"<h3>{escape(str(title))}</h3>"
        f"<div class='lecture-ar'>{escape(egyptian_translation(str(title)))}</div>"
    )


def lecture_search_text(lecture: dict[str, object]) -> str:
    raw_items = [
        str(lecture["number"]),
        str(lecture["title"]),
        str(lecture["subtitle"]),
        str(lecture["session_flow"]),
        str(lecture["applied_output"]),
        *lecture["outcomes"],
        *lecture["sections"],
    ]
    raw_items.extend(
        str(block)
        for section in lecture["full_sections"]
        for block in [section["title"], *section["blocks"]]
    )
    translated_items = [egyptian_translation(item) for item in raw_items]
    return " ".join(raw_items + translated_items).lower()


def read_docx_paragraphs(path: Path) -> list[str]:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def build_lecture_sections(paragraphs: list[str], start_index: int) -> list[dict[str, object]]:
    skip_labels = {
        "LEARNING OUTCOMES",
        "SESSION FLOW",
        "APPLIED OUTPUT",
        "LECTURE APPLICATION",
    }
    sections: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for paragraph in paragraphs[start_index:]:
        if paragraph in skip_labels or paragraph.startswith("LECTURE ") and "BRIEF" in paragraph:
            continue
        is_heading = (
            bool(re.match(r"^\d+\.\d+\s+", paragraph))
            or paragraph in {"DECISION RULE", "APPLIED WORKSHOP", "KNOWLEDGE CHECK", "Applied learning and assessment"}
        )
        if is_heading:
            if current:
                sections.append(current)
            current = {"title": paragraph, "blocks": []}
            continue
        if current is None:
            continue
        current["blocks"].append(paragraph)
    if current:
        sections.append(current)
    return sections


@st.cache_data(show_spinner=False)
def load_marketing_lectures() -> list[dict[str, object]]:
    folder = Path(__file__).parent / "Marketing_Project_Management_13_Lectures"
    lectures: list[dict[str, object]] = []
    if not folder.exists():
        return lectures
    for path in sorted(folder.glob("Lecture_*.docx")):
        paragraphs = read_docx_paragraphs(path)
        title_index = next((idx for idx, item in enumerate(paragraphs) if item.startswith("LECTURE ") and "|" in item), -1)
        title_line = paragraphs[title_index] if title_index >= 0 else path.stem.replace("_", " ")
        subtitle = paragraphs[title_index + 1] if title_index >= 0 and title_index + 1 < len(paragraphs) else ""
        lecture_match = re.search(r"LECTURE\s+(\d+)\s*\|\s*(.+)", title_line)
        number = lecture_match.group(1) if lecture_match else re.search(r"Lecture_(\d+)", path.name).group(1)
        title = lecture_match.group(2).strip().title() if lecture_match else path.stem.replace("_", " ").title()

        outcomes: list[str] = []
        session_flow = ""
        applied_output = ""
        section_titles: list[str] = []
        full_sections: list[dict[str, object]] = []
        for idx, paragraph in enumerate(paragraphs):
            if paragraph == "LEARNING OUTCOMES" and idx + 1 < len(paragraphs):
                outcomes = split_numbered_items(paragraphs[idx + 1])
            elif paragraph == "SESSION FLOW" and idx + 1 < len(paragraphs):
                session_flow = paragraphs[idx + 1]
            elif paragraph == "APPLIED OUTPUT" and idx + 1 < len(paragraphs):
                applied_output = paragraphs[idx + 1]
            elif re.match(r"^\d+\.\d+\s+", paragraph):
                section_titles.append(paragraph)
        content_start = next((idx for idx, item in enumerate(paragraphs) if re.match(r"^\d+\.\d+\s+", item)), title_index + 1)
        full_sections = build_lecture_sections(paragraphs, content_start)

        lectures.append(
            {
                "number": number,
                "title": title,
                "subtitle": subtitle,
                "outcomes": outcomes[:4],
                "session_flow": session_flow,
                "applied_output": applied_output,
                "sections": section_titles[:6],
                "full_sections": full_sections,
                "file": path.name,
            }
        )
    return lectures


def learning_intro() -> None:
    cards = [
        panel(
            "Marketing for Project Managers",
            "يعني إنك تعرف توصل قيمة المشروع للعميل، الإدارة، الفريق، والاستيكهولدرز بطريقة واضحة ومقنعة. هو مش إعلانات فقط؛ هو value communication وstakeholder alignment وtrust-building.",
            kind="mission",
        ),
        panel(
            "Stakeholder Value Proposition",
            "ابدأ من صاحب المصلحة: مين هو؟ يهتم بإيه؟ المشروع هيسلم له قيمة إيه؟ يخاف من أي خطر؟ وما الرسالة التي يحتاج أن يسمعها؟",
            ["Who is the stakeholder?", "What value matters?", "What risk blocks trust?", "What message should land?"],
            "compact",
        ),
        panel(
            "Project Positioning",
            "ضع المشروع في مكان واضح: لماذا يهم، ما المشكلة التي يحلها، ما المختلف فيه، ما القيمة التجارية، وما شكل النجاح القابل للقياس.",
            kind="compact",
        ),
        panel(
            "Communication Plan as Marketing",
            "التقارير الأسبوعية، الداشبورد، executive summaries، claims/EOT narratives، presentations، وrisk communication كلها أصول تسويق للثقة لو اتعملت باحتراف.",
            kind="compact",
        ),
        panel(
            "Personal Branding",
            "مدير المشروع القوي واضح، موثوق، مرتب، يستخدم البيانات، يتكلم بلغة النتائج، يبني الثقة، ويسلّم باستمرار.",
            kind="compact",
        ),
        panel(
            "Client Pitch",
            "صيغة 30 ثانية: Problem -> Impact -> Solution -> Evidence -> Next action. لا تبدأ بالتفاصيل؛ ابدأ بالقرار والقيمة.",
            kind="compact",
        ),
        panel(
            "Case Study",
            "بدل: المشروع اتأخر وهنحاول نعوض. قل: التأخير الحالي أثره 12 يومًا على المسار الحرج. خطة التعافي تضيف وردية ثانية على نشاطين حرجين وتعيد 8 أيام خلال 3 أسابيع. نحتاج موافقة العميل اليوم.",
            kind="warning-panel",
        ),
    ]
    html(f'<section class="visual-grid two">{"".join(cards)}</section>')


def learning_lectures() -> None:
    lectures = load_marketing_lectures()
    if not lectures:
        html(panel("Lectures in Marketing For Project Manager", "لم أجد ملفات المحاضرات داخل مجلد Marketing_Project_Management_13_Lectures.", kind="warning-panel"))
        return

    query = st.text_input(
        "بحث داخل المحاضرات",
        key="lecture_search",
        placeholder="Search lecture title, outcome, session flow...",
        label_visibility="collapsed",
    ).strip().lower()
    filtered = []
    for lecture in lectures:
        haystack = lecture_search_text(lecture)
        if not query or query in haystack:
            filtered.append(lecture)

    html(
        panel(
            "Lectures in Marketing For Project Manager",
            f"برنامج احترافي من 13 محاضرة مبني كمسار تدريبي متدرج: Strategy, Governance, Delivery, Measurement, Applied Learning. المعروض الآن: {len(filtered)} / {len(lectures)}.",
            kind="mission",
        )
    )

    rows = []
    for lecture in filtered:
        outcomes = "<br>".join(f"- {escape(item)}" for item in lecture["outcomes"]) or "Professional lecture outcomes"
        sections = "<br>".join(escape(item) for item in lecture["sections"][:4]) or escape(str(lecture["session_flow"]))
        rows.append(
            "<tr>"
            f"<td>Lecture {escape(str(lecture['number']))}</td>"
            f"<td><b>{escape(str(lecture['title']))}</b><br><span>{escape(str(lecture['subtitle']))}</span></td>"
            f"<td>{outcomes}</td>"
            f"<td>{escape(str(lecture['applied_output']))}<div class='lecture-meta'><span class='lecture-chip'>90 min</span><span class='lecture-chip'>{escape(str(lecture['file']))}</span></div></td>"
            f"<td>{sections}</td>"
            "</tr>"
        )
    table = (
        "<article class='visual-panel'><h2>Lecture Index</h2>"
        "<table class='learning-table'><thead><tr>"
        "<th>No.</th><th>Lecture</th><th>Learning Outcomes</th><th>Applied Output</th><th>Core Sections</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></article>"
    )
    html(table)

    lecture_options = {
        f"Lecture {lecture['number']} · {lecture['title']}": lecture
        for lecture in filtered
    }
    if not lecture_options:
        html(panel("لا توجد محاضرات", "غيّر كلمة البحث لعرض المحاضرات.", kind="warning-panel"))
        return

    dropdown_options = ["Lecture Index"] + list(lecture_options.keys())
    selected_label = st.selectbox(
        "اختر محاضرة لعرض الشرح الكامل",
        dropdown_options,
        key="selected_learning_lecture",
    )
    if selected_label == "Lecture Index":
        html(panel("Lecture Index", "اختر محاضرة من القائمة لعرض الشرح الكامل. الفهرس بالأعلى يعرض كل المحاضرات المتاحة بعد البحث.", kind="compact"))
        return
    selected_lecture = lecture_options[selected_label]

    details = ["<article class='visual-panel'><h2>Complete Lecture Explanation</h2><p>اختر محاضرة من القائمة لعرض الشرح الكامل المستخرج من ملف Word بنفس ترتيب المادة الأصلية.</p></article>"]
    for lecture in [selected_lecture]:
        sections_html = []
        header_bits = []
        if lecture["outcomes"]:
            header_bits.append(
                f"<div class='lecture-section'>{lecture_heading('Learning Outcomes')}<ul>"
                + "".join(f"<li>{bilingual_point(item)}</li>" for item in lecture["outcomes"])
                + "</ul></div>"
            )
        if lecture["session_flow"]:
            header_bits.append(f"<div class='lecture-section'>{lecture_heading('Session Flow')}{bilingual_point(str(lecture['session_flow']))}</div>")
        if lecture["applied_output"]:
            header_bits.append(f"<div class='lecture-section'>{lecture_heading('Applied Output')}{bilingual_point(str(lecture['applied_output']))}</div>")
        for section in lecture["full_sections"]:
            blocks = section["blocks"]
            if not blocks:
                continue
            list_items = []
            paragraph_items = []
            for block in blocks:
                if len(str(block)) < 120 and not str(block).endswith("."):
                    list_items.append(f"<li>{bilingual_point(str(block))}</li>")
                else:
                    paragraph_items.append(bilingual_point(str(block)))
            content = ("<ul>" + "".join(list_items) + "</ul>" if list_items else "") + "".join(paragraph_items)
            sections_html.append(
                f"<div class='lecture-section'>{lecture_heading(str(section['title']))}{content}</div>"
            )
        details.append(
            "<details class='lecture-detail'>"
            f"<summary>Lecture {escape(str(lecture['number']))} · {escape(str(lecture['title']))}"
            f"<span>{escape(str(lecture['subtitle']))}</span></summary>"
            "<div class='lecture-body'>"
            + "".join(header_bits)
            + "".join(sections_html)
            + "</div></details>"
        )
    html("".join(details))


def learning_module(active: str) -> None:
    if active == "intro":
        learning_intro()
    elif active == "lectures":
        learning_lectures()
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
    side_col, main_col = st.columns([248, 1147], gap="large")
    with side_col:
        module = st.radio(
            "SELECT PROGRAM",
            list(MODULES.keys()),
            index=list(MODULES.keys()).index(module),
            format_func=lambda key: MODULES[key],
            key="module",
            label_visibility="visible",
        )
    with main_col:
        html(f'<section class="visual-main">{topbar(module)}')
        if module == "food":
            food_slide = food_slide_nav(st.session_state.food_slide)
            html(f'<div class="stats-enter">{kpis(module)}</div>')
            food_module(food_slide)
        elif module == "medicine":
            medicine_slide = medicine_slide_nav(st.session_state.medicine_slide)
            html(f'<div class="stats-enter">{kpis(module)}</div>')
            medicine_module(medicine_slide)
        elif module == "lifestyle":
            lifestyle_slide = lifestyle_slide_nav(st.session_state.lifestyle_slide)
            html(f'<div class="stats-enter">{kpis(module)}</div>')
            lifestyle_module(lifestyle_slide)
        else:
            learning_slide = learning_slide_nav(st.session_state.learning_slide)
            html(f'<div class="stats-enter">{kpis(module)}</div>')
            learning_module(learning_slide)
        html("</section>")
    footer()


if __name__ == "__main__":
    main()
