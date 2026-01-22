import os
import io
import json
import zipfile
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import quote

import httpx
import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Экспертиза локальных актов РГГУ")

# Vercel использует /tmp для временных файлов
UPLOADS_DIR = Path("/tmp/uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

results_store: dict = {}

# ==================== НОРМАТИВНЫЕ АКТЫ ====================

UKAZ_809_TEXT = """
УКАЗ ПРЕЗИДЕНТА РОССИЙСКОЙ ФЕДЕРАЦИИ ОТ 09.11.2022 № 809
"Об утверждении Основ государственной политики по сохранению и укреплению
традиционных российских духовно-нравственных ценностей"

КЛЮЧЕВЫЕ ПОЛОЖЕНИЯ:

1. Традиционные ценности - это нравственные ориентиры, формирующие мировоззрение
граждан России, передаваемые от поколения к поколению, лежащие в основе
общероссийской гражданской идентичности и единого культурного пространства страны.

2. К традиционным ценностям относятся:
   - жизнь, достоинство, права и свободы человека
   - патриотизм, гражданственность, служение Отечеству
   - высокие нравственные идеалы
   - крепкая семья, созидательный труд
   - приоритет духовного над материальным
   - гуманизм, милосердие, справедливость
   - коллективизм, взаимопомощь и взаимоуважение
   - историческая память и преемственность поколений
   - единство народов России

3. Угрозы традиционным ценностям:
   - деятельность экстремистских и террористических организаций
   - действия США и других недружественных государств
   - деструктивная идеология
   - деятельность транснациональных корпораций и иностранных НКО

4. Цели государственной политики:
   - сохранение и укрепление традиционных ценностей
   - передача их от поколения к поколению
   - противодействие распространению деструктивной идеологии
   - формирование на международной арене образа России как хранителя ценностей

5. Задачи в сфере образования и воспитания:
   - воспитание в духе уважения к традиционным ценностям
   - поддержка общественных проектов в сфере патриотического воспитания
   - сохранение исторической памяти, противодействие фальсификации истории
   - поддержка религиозных организаций традиционных конфессий
   - защита института семьи, материнства, отцовства и детства
"""

RASPORYAZHENIE_1734_TEXT = """
РАСПОРЯЖЕНИЕ ПРАВИТЕЛЬСТВА РОССИЙСКОЙ ФЕДЕРАЦИИ ОТ 01.07.2024 № 1734-р
"О Плане мероприятий по реализации в 2024-2026 г.г. Основ государственной политики
по сохранению и укреплению традиционных российских духовно-нравственных ценностей"

КЛЮЧЕВЫЕ МЕРОПРИЯТИЯ ПЛАНА:

1. Нормативно-правовое обеспечение:
   - Подготовка предложений по совершенствованию законодательства
   - Мониторинг реализации государственной политики в сфере ценностей

2. Образование и воспитание:
   - Разработка методических рекомендаций для образовательных организаций
   - Включение вопросов традиционных ценностей в образовательные программы
   - Проведение всероссийских мероприятий патриотической направленности
   - Поддержка добровольческих движений

3. Культура и искусство:
   - Поддержка проектов, направленных на сохранение традиционных ценностей
   - Создание контента, продвигающего традиционные ценности
   - Противодействие деструктивному контенту

4. Информационная политика:
   - Формирование позитивного информационного пространства
   - Защита детей от деструктивной информации
   - Развитие медиаграмотности

5. Работа с молодёжью:
   - Поддержка молодёжных организаций патриотической направленности
   - Развитие наставничества
   - Вовлечение молодёжи в общественно полезную деятельность

6. Международное сотрудничество:
   - Продвижение традиционных ценностей на международных площадках
   - Поддержка соотечественников за рубежом

7. Научное обеспечение:
   - Проведение исследований в сфере традиционных ценностей
   - Мониторинг угроз традиционным ценностям
"""

ANALYSIS_PROMPT = """Ты — эксперт по правовому анализу локальных нормативных актов образовательных организаций.

Твоя задача: проанализировать предоставленный документ (локальный нормативный акт РГГУ) на предмет соответствия двум федеральным документам:

1. Указ Президента РФ от 09.11.2022 № 809 "Об утверждении Основ государственной политики по сохранению и укреплению традиционных российских духовно-нравственных ценностей"

2. Распоряжение Правительства РФ от 01.07.2024 № 1734-р "О Плане мероприятий по реализации в 2024-2026 г.г. Основ государственной политики по сохранению и укреплению традиционных российских духовно-нравственных ценностей"

=== СОДЕРЖАНИЕ УКАЗА № 809 ===
{ukaz_text}

=== СОДЕРЖАНИЕ РАСПОРЯЖЕНИЯ № 1734-р ===
{rasporyazhenie_text}

=== АНАЛИЗИРУЕМЫЙ ДОКУМЕНТ ===
Название: {doc_name}

Текст документа:
{doc_text}

=== ИНСТРУКЦИИ ===

Проведи детальный анализ и верни результат СТРОГО в следующем JSON формате:

{{
    "document_name": "название анализируемого документа",
    "summary": "краткое описание содержания документа (2-3 предложения)",

    "ukaz_809": {{
        "matches": [
            {{
                "doc_reference": "ссылка на пункт/раздел анализируемого документа",
                "ukaz_reference": "ссылка на положение Указа № 809",
                "description": "описание соответствия"
            }}
        ],
        "contradictions": [
            {{
                "doc_reference": "ссылка на пункт/раздел документа или 'отсутствует'",
                "ukaz_reference": "ссылка на положение Указа № 809",
                "description": "описание расхождения или отсутствующего элемента",
                "recommendation": "рекомендация по устранению"
            }}
        ]
    }},

    "rasporyazhenie_1734": {{
        "matches": [
            {{
                "doc_reference": "ссылка на пункт/раздел анализируемого документа",
                "rasp_reference": "ссылка на пункт Плана мероприятий",
                "description": "описание соответствия"
            }}
        ],
        "contradictions": [
            {{
                "doc_reference": "ссылка на пункт/раздел документа или 'отсутствует'",
                "rasp_reference": "ссылка на пункт Плана мероприятий",
                "description": "описание расхождения или отсутствующего элемента",
                "recommendation": "рекомендация по устранению"
            }}
        ]
    }},

    "conclusion": {{
        "status": "соответствует" | "частично соответствует" | "требует доработки",
        "summary": "итоговое заключение (2-3 предложения)",
        "priority_recommendations": ["список приоритетных рекомендаций по доработке"]
    }}
}}

ВАЖНО:
- Если соответствий или противоречий нет, оставь пустой массив []
- Будь конкретен в ссылках на пункты документов
- Учитывай специфику образовательной организации
- Отвечай ТОЛЬКО валидным JSON без дополнительного текста
"""

# ==================== ФУНКЦИИ ПАРСИНГА ====================

def extract_text_from_pdf(file_path: Path) -> str:
    try:
        doc = fitz.open(str(file_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения PDF: {str(e)}")


def extract_text_from_docx(file_path: Path) -> str:
    try:
        doc = Document(str(file_path))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения DOCX: {str(e)}")


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix == ".docx":
        return extract_text_from_docx(file_path)
    elif suffix == ".txt":
        return file_path.read_text(encoding="utf-8")
    else:
        raise HTTPException(status_code=400, detail=f"Неподдерживаемый формат: {suffix}. Используйте PDF, DOCX или TXT")


# ==================== LLM ИНТЕГРАЦИЯ ====================

async def analyze_document(doc_name: str, doc_text: str) -> dict:
    prompt = ANALYSIS_PROMPT.format(
        ukaz_text=UKAZ_809_TEXT,
        rasporyazhenie_text=RASPORYAZHENIE_1734_TEXT,
        doc_name=doc_name,
        doc_text=doc_text[:50000]
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://krechet.space",
        "X-Title": "RGGU Expertise Service"
    }

    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.1
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Ошибка API: {response.status_code}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            return {"document_name": doc_name, "raw_response": content, "parse_error": str(e)}


# ==================== ГЕНЕРАЦИЯ DOCX ====================

def create_expertise_docx(analysis: dict) -> io.BytesIO:
    doc = Document()
    title = doc.add_heading("ЭКСПЕРТНОЕ ЗАКЛЮЧЕНИЕ", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()
    doc.add_paragraph(f"Наименование документа: {analysis.get('document_name', 'Не указано')}")
    doc.add_paragraph(f"Дата экспертизы: {datetime.now().strftime('%d.%m.%Y')}")

    if analysis.get('summary'):
        doc.add_paragraph()
        doc.add_paragraph(f"Краткое содержание: {analysis['summary']}")

    doc.add_heading("АНАЛИЗ НА СООТВЕТСТВИЕ УКАЗУ ПРЕЗИДЕНТА РФ ОТ 09.11.2022 № 809", level=1)
    ukaz = analysis.get('ukaz_809', {})

    doc.add_heading("Соответствует:", level=2)
    for m in ukaz.get('matches', []):
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f"{m.get('doc_reference', '')}: ").bold = True
        p.add_run(f"{m.get('description', '')} ")
        p.add_run(f"(соотв. {m.get('ukaz_reference', '')})").italic = True
    if not ukaz.get('matches'):
        doc.add_paragraph("Явных соответствий не выявлено.", style='List Bullet')

    doc.add_heading("Расходится:", level=2)
    for c in ukaz.get('contradictions', []):
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f"{c.get('doc_reference', '')}: ").bold = True
        p.add_run(f"{c.get('description', '')} ")
        p.add_run(f"(см. {c.get('ukaz_reference', '')})").italic = True
    if not ukaz.get('contradictions'):
        doc.add_paragraph("Расхождений не выявлено.", style='List Bullet')

    doc.add_heading("АНАЛИЗ НА СООТВЕТСТВИЕ РАСПОРЯЖЕНИЮ ПРАВИТЕЛЬСТВА РФ ОТ 01.07.2024 № 1734-р", level=1)
    rasp = analysis.get('rasporyazhenie_1734', {})

    doc.add_heading("Соответствует:", level=2)
    for m in rasp.get('matches', []):
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f"{m.get('doc_reference', '')}: ").bold = True
        p.add_run(f"{m.get('description', '')} ")
        p.add_run(f"(соотв. {m.get('rasp_reference', '')})").italic = True
    if not rasp.get('matches'):
        doc.add_paragraph("Явных соответствий не выявлено.", style='List Bullet')

    doc.add_heading("Расходится:", level=2)
    for c in rasp.get('contradictions', []):
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f"{c.get('doc_reference', '')}: ").bold = True
        p.add_run(f"{c.get('description', '')} ")
        p.add_run(f"(см. {c.get('rasp_reference', '')})").italic = True
    if not rasp.get('contradictions'):
        doc.add_paragraph("Расхождений не выявлено.", style='List Bullet')

    doc.add_heading("ИТОГОВОЕ ЗАКЛЮЧЕНИЕ", level=1)
    conclusion = analysis.get('conclusion', {})
    p = doc.add_paragraph()
    p.add_run("Статус: ").bold = True
    p.add_run(conclusion.get('status', 'не определён').upper())
    if conclusion.get('summary'):
        doc.add_paragraph(conclusion['summary'])

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ==================== HTML СТРАНИЦА ====================

HTML_PAGE = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Экспертиза НПА РГГУ</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .drag-over { border-color: #3b82f6 !important; background-color: #eff6ff !important; }
        .fade-in { animation: fadeIn 0.3s ease-in; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #3b82f6; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; display: inline-block; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">Экспертиза локальных актов РГГУ</h1>
            <p class="text-gray-600">Анализ на соответствие Указу № 809 и Распоряжению № 1734-р</p>
        </div>

        <div class="bg-white rounded-xl shadow-lg p-6 mb-8">
            <div id="dropZone" class="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center cursor-pointer transition-all hover:border-blue-400 hover:bg-blue-50">
                <div class="text-6xl mb-4">📁</div>
                <p class="text-lg text-gray-700 mb-2">Перетащите файлы сюда</p>
                <p class="text-gray-500 mb-4">или нажмите для выбора</p>
                <p class="text-sm text-gray-400">PDF, DOCX, TXT (до 20 файлов)</p>
                <input type="file" id="fileInput" multiple accept=".pdf,.docx,.txt" class="hidden">
            </div>
            <div id="fileList" class="mt-4 hidden">
                <h3 class="font-semibold text-gray-700 mb-2">Выбранные файлы:</h3>
                <ul id="fileListItems" class="space-y-2"></ul>
            </div>
            <button id="analyzeBtn" class="w-full mt-6 bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-400 hidden">▶ Провести экспертизу</button>
        </div>

        <div id="progressSection" class="bg-white rounded-xl shadow-lg p-6 mb-8 hidden">
            <div class="flex items-center gap-3">
                <div class="spinner"></div>
                <span id="progressText" class="text-gray-700">Анализ документов...</span>
            </div>
        </div>

        <div id="resultsSection" class="hidden">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold text-gray-800">Результаты экспертизы</h2>
                <button id="exportAllBtn" class="bg-green-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-green-700">📥 Скачать все (ZIP)</button>
            </div>
            <div id="resultsList" class="space-y-4"></div>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const fileListItems = document.getElementById('fileListItems');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const progressSection = document.getElementById('progressSection');
        const resultsSection = document.getElementById('resultsSection');
        const resultsList = document.getElementById('resultsList');
        const exportAllBtn = document.getElementById('exportAllBtn');
        let selectedFiles = [];
        let currentSessionId = null;

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('drag-over'); handleFiles(e.dataTransfer.files); });
        fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

        function handleFiles(files) {
            selectedFiles = Array.from(files).slice(0, 20);
            if (selectedFiles.length === 0) { fileList.classList.add('hidden'); analyzeBtn.classList.add('hidden'); return; }
            fileList.classList.remove('hidden');
            analyzeBtn.classList.remove('hidden');
            fileListItems.innerHTML = selectedFiles.map((file, i) => `<li class="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2"><span>📄 ${file.name}</span><button onclick="removeFile(${i})" class="text-red-500">✕</button></li>`).join('');
        }

        function removeFile(index) { selectedFiles.splice(index, 1); handleFiles(selectedFiles); }

        analyzeBtn.addEventListener('click', async () => {
            if (selectedFiles.length === 0) return;
            analyzeBtn.disabled = true;
            progressSection.classList.remove('hidden');
            resultsSection.classList.add('hidden');

            const formData = new FormData();
            selectedFiles.forEach(file => formData.append('files', file));

            try {
                const response = await fetch('/nparggu/api/analyze', { method: 'POST', body: formData });
                if (!response.ok) throw new Error('Ошибка сервера');
                const data = await response.json();
                currentSessionId = data.session_id;
                progressSection.classList.add('hidden');
                displayResults(data.results);
            } catch (error) {
                alert('Ошибка: ' + error.message);
                progressSection.classList.add('hidden');
            } finally {
                analyzeBtn.disabled = false;
            }
        });

        function displayResults(results) {
            resultsSection.classList.remove('hidden');
            resultsList.innerHTML = results.map((result, index) => {
                if (result.error) return `<div class="bg-white rounded-xl shadow-lg p-6 border-l-4 border-red-500"><span>❌</span> <b>${result.filename}</b>: ${result.error}</div>`;
                const ukaz = result.ukaz_809 || {};
                const rasp = result.rasporyazhenie_1734 || {};
                const conclusion = result.conclusion || {};
                return `<div class="bg-white rounded-xl shadow-lg p-6 fade-in">
                    <div class="flex justify-between items-start mb-4">
                        <div><h3 class="font-semibold">📄 ${result.filename || result.document_name}</h3><p class="text-sm text-gray-500">${result.summary || ''}</p></div>
                    </div>
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="bg-gray-50 rounded-lg p-3"><p class="text-sm font-medium">Указ № 809</p><p class="text-sm">✅ ${(ukaz.matches||[]).length} | ❌ ${(ukaz.contradictions||[]).length}</p></div>
                        <div class="bg-gray-50 rounded-lg p-3"><p class="text-sm font-medium">Распоряжение № 1734-р</p><p class="text-sm">✅ ${(rasp.matches||[]).length} | ❌ ${(rasp.contradictions||[]).length}</p></div>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm font-medium">${conclusion.status || ''}</span>
                        <button onclick="downloadSingle(${index})" class="bg-blue-600 text-white px-3 py-1 rounded text-sm">📥 DOCX</button>
                    </div>
                </div>`;
            }).join('');
        }

        function downloadSingle(index) { if (currentSessionId) window.location.href = `/nparggu/api/export/${currentSessionId}/${index}`; }
        exportAllBtn.addEventListener('click', () => { if (currentSessionId) window.location.href = `/nparggu/api/export-all/${currentSessionId}`; });
    </script>
</body>
</html>'''


# ==================== API ЭНДПОИНТЫ ====================

@app.get("/", response_class=HTMLResponse)
@app.get("/nparggu", response_class=HTMLResponse)
@app.get("/nparggu/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/nparggu/api/analyze")
async def analyze_files(files: List[UploadFile] = File(...)):
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Максимум 20 файлов")

    session_id = str(uuid.uuid4())
    results = []

    for file in files:
        safe_filename = re.sub(r'[^\w\.\-]', '_', file.filename)
        file_path = UPLOADS_DIR / f"{session_id}_{safe_filename}"
        content = await file.read()
        file_path.write_bytes(content)

        try:
            text = extract_text(file_path)
            if not text.strip():
                results.append({"filename": file.filename, "error": "Не удалось извлечь текст"})
                continue
            analysis = await analyze_document(file.filename, text)
            analysis["filename"] = file.filename
            results.append(analysis)
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})
        finally:
            if file_path.exists():
                file_path.unlink()

    results_store[session_id] = results
    return {"session_id": session_id, "results": results}


@app.get("/nparggu/api/export/{session_id}/{index}")
async def export_single(session_id: str, index: int):
    if session_id not in results_store:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    results = results_store[session_id]
    if index < 0 or index >= len(results):
        raise HTTPException(status_code=404, detail="Документ не найден")
    analysis = results[index]
    if "error" in analysis:
        raise HTTPException(status_code=400, detail="Нет экспертизы")

    docx_buffer = create_expertise_docx(analysis)
    filename_ascii = f"Expertiza_{index}.docx"
    filename_utf8 = quote(f"Экспертиза_{index}.docx")

    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename_ascii}"; filename*=UTF-8\'\'{filename_utf8}'}
    )


@app.get("/nparggu/api/export-all/{session_id}")
async def export_all(session_id: str):
    if session_id not in results_store:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    results = results_store[session_id]

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i, analysis in enumerate(results):
            if "error" not in analysis:
                docx_buffer = create_expertise_docx(analysis)
                zf.writestr(f"Expertiza_{i}.docx", docx_buffer.getvalue())
    zip_buffer.seek(0)

    filename = f"Expertiza_RGGU_{session_id[:8]}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
