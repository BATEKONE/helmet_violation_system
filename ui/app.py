import os
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_model_path
from core.settings import get_settings
from ui.api_client import DEFAULT_API_URL, HelmetApiClient

st.set_page_config(
    page_title="Helmet Violation Detection",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

settings = get_settings()
model_path = get_model_path()
is_trained = "helmet_detector" in str(model_path)

st.title("🏍️ Система детекции нарушений — отсутствие шлема")
st.markdown(
    "Загрузите видео — анализ выполняется на сервере через API. "
    "Результаты: обработанное видео, таблица нарушений и снимки. "
    "На финальном шаге можно выбрать релевантные кадры и скачать PDF-отчет."
)

def build_violation_pdf(events: list[dict], selected_indices: list[int], image_map: dict[int, bytes]) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, page_height - 50, "Отчет о нарушении (отсутствие шлема)")
    c.setFont("Helvetica", 10)
    c.drawString(40, page_height - 68, f"Сформирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(40, page_height - 84, f"Количество выбранных кадров: {len(selected_indices)}")

    y = page_height - 110
    for idx in selected_indices:
        event = events[idx]
        image_bytes = image_map.get(idx)
        if not image_bytes:
            continue

        if y < 230:
            c.showPage()
            y = page_height - 50

        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"Событие #{idx + 1}")
        y -= 16
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"track_id: {event.get('track_id', '-')}")
        y -= 14
        c.drawString(40, y, f"timestamp: {event.get('timestamp', '-')}")
        y -= 14
        c.drawString(40, y, f"confidence: {event.get('confidence', '-')}")
        y -= 12

        image = ImageReader(BytesIO(image_bytes))
        img_w, img_h = image.getSize()
        max_w, max_h = 240, 140
        ratio = min(max_w / img_w, max_h / img_h)
        draw_w = img_w * ratio
        draw_h = img_h * ratio
        c.drawImage(image, 40, y - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
        y -= draw_h + 24

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


api_url = os.getenv("HELMET_API_URL", DEFAULT_API_URL)
client = HelmetApiClient(api_url)

st.caption(f"Модель на сервере: `{model_path.name}`")
if is_trained:
    st.success("Обученная модель подключена")
else:
    st.warning("Нужно обучение: `python training/train_yolo.py`")

try:
    health = client.health()
    if health.get("status") != "ok":
        st.warning(f"API: {health.get('status')} (БД: {health.get('database')}, Redis: {health.get('redis')})")
except Exception as exc:
    st.error(f"API недоступен: {exc}")
    st.info("Запустите API: `python scripts/run_api.py` и worker: `python workers/run_worker.py`")

if "job_data" not in st.session_state:
    st.session_state.job_data = None

uploaded = st.file_uploader(
    "Загрузить видео",
    type=["mp4", "avi", "mov", "mkv"],
)

if uploaded:
    temp_input = settings.data_dir / "temp_upload.mp4"
    temp_input.parent.mkdir(parents=True, exist_ok=True)

    with open(temp_input, "wb") as f:
        f.write(uploaded.getbuffer())

    if st.button("Запустить анализ", type="primary"):
        progress = st.progress(0.0)
        status = st.empty()

        try:
            with st.spinner("Отправка видео на сервер..."):
                created = client.create_job(temp_input, uploaded.name)
                job_id = created["id"]

            def on_progress(value, job_status):
                progress.progress(min(value, 1.0))
                status.text(f"Статус: {job_status} — {value * 100:.0f}%")

            with st.spinner("Ожидание результата анализа..."):
                job = client.wait_for_job(job_id, progress_callback=on_progress)

            progress.progress(1.0)
            status.empty()

            if job["status"] == "failed":
                st.error(job.get("error_message") or "Ошибка обработки")
            else:
                events = client.list_events(job_id)
                video_bytes = b""
                try:
                    video_bytes = client.download_video(job_id)
                except Exception:
                    video_bytes = b""

                image_map: dict[int, bytes] = {}
                for i, event in enumerate(events):
                    image_url = event.get("image_url")
                    if not image_url:
                        continue
                    try:
                        image_map[i] = client.download_image(image_url)
                    except Exception:
                        continue

                st.session_state.job_data = {
                    "job_id": job_id,
                    "events": events,
                    "video_bytes": video_bytes,
                    "image_map": image_map,
                }
                st.success("Анализ завершён")

        except Exception as exc:
            st.error(f"Ошибка: {exc}")
else:
    st.info("Выберите видеофайл для начала анализа")

if st.session_state.job_data:
    events = st.session_state.job_data["events"]
    video_bytes = st.session_state.job_data["video_bytes"]
    image_map = st.session_state.job_data["image_map"]

    st.subheader("Обработанное видео")
    if video_bytes:
        st.video(video_bytes, format="video/mp4")
        st.download_button(
            "Скачать обработанное видео",
            video_bytes,
            file_name="helmet_analysis.mp4",
            mime="video/mp4",
        )
    else:
        st.warning("Видео недоступно")

    st.subheader("Зарегистрированные нарушения")
    if events:
        df = pd.DataFrame(events)
        display_cols = [
            c for c in ("track_id", "violation", "timestamp", "confidence", "bbox")
            if c in df.columns
        ]
        st.dataframe(df[display_cols], use_container_width=True)
        st.metric("Всего нарушений", len(events))
    else:
        st.info("Нарушений не обнаружено")

    st.subheader("Выбор релевантных снимков для отчета")
    if events:
        selected_indices = []
        cols = st.columns(3)
        for i, event in enumerate(events):
            col = cols[i % 3]
            image_bytes = image_map.get(i)
            if image_bytes:
                col.image(
                    image_bytes,
                    caption=f"Событие {i + 1} | track {event.get('track_id', '-')}",
                    use_container_width=True,
                )
            else:
                col.warning("Снимок недоступен")
            if col.checkbox(
                f"Включить в отчет #{i + 1}",
                key=f"report_event_{i}",
                value=(i == 0),
            ):
                selected_indices.append(i)

        if selected_indices:
            pdf_bytes = build_violation_pdf(events, selected_indices, image_map)
            st.download_button(
                "Скачать PDF-отчет по выбранным кадрам",
                data=pdf_bytes,
                file_name="helmet_violation_report.pdf",
                mime="application/pdf",
                type="primary",
            )
        else:
            st.info("Выберите хотя бы один снимок для формирования PDF")
    else:
        st.info("Нет снимков для выбора")
