# Eng. Mohamed Sameh | Life Guard | Learning Tool

Python Streamlit version of the premium Arabic RTL medical-tech dashboard.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Ollama

Default:

```bash
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=llama3.2:3b
ollama pull llama3.2:3b
ollama serve
```

The app safely falls back to built-in Arabic answers if Ollama is unavailable.

## Scanner

Streamlit opens the camera inside the app through `st.camera_input`. For barcode lookup, enter the barcode number manually and press OpenFoodFacts lookup, or type ingredients directly.

Camera access works on localhost and HTTPS. The browser must be allowed to use the camera.

## Update data

Risk rules, dangerous product categories, alternatives, and AI fallback answers are inside `app.py` for easy Streamlit deployment.

Course links are stored in `courses.json` with provider, title, status, link, last verified date, and notes. Verify course availability before production release because free/audit/trial terms can change by provider, region, and account.

## Validation

```bash
python -m compileall -q .
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8507 --server.headless true
```

Then open:

```text
http://127.0.0.1:8507
```

## Streamlit Cloud deployment

Do not hardcode `server.port` or `server.address` in `.streamlit/config.toml` for Streamlit Cloud. The platform expects its own port, commonly `8501`, and a fixed local port like `8507` will fail health checks.

## Medical disclaimer

هذا التطبيق للتوعية وتقليل المخاطر الغذائية فقط. لا يشخص السرطان، لا يعالج السرطان، لا يوقف دواء، لا يغير جرعة، ولا يستبدل طبيب الأورام أو أخصائي تغذية أورام. مع تاريخ سرطان أو رجوع أعراض، أي قرار علاج أو صيام أو مكملات أو نظام قاسٍ لازم يتم مع الفريق الطبي.

## Footer

`Design and creation | Ahmed Labib | ©️`

Ahmed Labib is highlighted in cyan/blue.
