import os
import sys
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_model_path
from core.settings import get_settings
from ui.api_client import HelmetApiClient, DEFAULT_API_URL

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
    "Результаты: обработанное видео, таблица нарушений и снимки."
)

def build_violation_pdf(
    events: list[dict],
    selected_indices: list[int],
    image_map: dict[int, bytes],
    protocol_meta: dict[str, str],
) -> bytes:
    def register_cyrillic_font() -> tuple[str, str]:
        candidates = [
            ROOT / "assets" / "fonts" / "DejaVuSans.ttf",
            ROOT / "assets" / "fonts" / "Arial.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/tahoma.ttf"),
        ]
        for path in candidates:
            if path.exists():
                pdfmetrics.registerFont(TTFont("ProtocolFont", str(path)))
                return "ProtocolFont", str(path)
        return "Helvetica", ""

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, page_height = A4
    base_font, font_path = register_cyrillic_font()

    def draw_kv_line(y: float, key: str, value: str) -> float:
        pdf.setFont(base_font, 10)
        pdf.drawString(40, y, f"{key}: {value or '-'}")
        return y - 14

    protocol_number = protocol_meta.get("protocol_number") or f"AUTO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pdf.setFont(base_font, 11)
    pdf.drawString(40, page_height - 40, protocol_meta.get("organization", "Орган, осуществляющий контроль ПДД"))
    pdf.setFont(base_font, 14)
    pdf.drawString(40, page_height - 62, "ПРОТОКОЛ ФИКСАЦИИ НАРУШЕНИЯ")
    pdf.setFont(base_font, 10)
    pdf.drawString(40, page_height - 78, "Факт управления ТС без защитного мотошлема")

    y = page_height - 106
    y = draw_kv_line(y, "Номер протокола", protocol_number)
    y = draw_kv_line(y, "Дата и время составления", generated_at)
    y = draw_kv_line(y, "Инспектор/оператор", protocol_meta.get("inspector", ""))
    y = draw_kv_line(y, "Место фиксации", protocol_meta.get("location", ""))
    y = draw_kv_line(y, "Источник данных", protocol_meta.get("source", "Видеоаналитика системы Helmet Violation Detection"))

    pdf.setFont(base_font, 10)
    y -= 8
    pdf.drawString(
        40,
        y,
        "Основание: автоматическая фиксация события отсутствия шлема на кадрах видеопотока.",
    )
    y -= 20

    if selected_indices:
        confidences = [
            float(events[i].get("confidence", 0.0))
            for i in selected_indices
            if events[i].get("confidence") is not None
        ]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    else:
        avg_conf = 0.0

    y = draw_kv_line(y, "Количество подтвержденных эпизодов", str(len(selected_indices)))
    y = draw_kv_line(y, "Средняя уверенность модели", f"{avg_conf:.3f}")
    y = draw_kv_line(y, "Комментарий", protocol_meta.get("comment", ""))

    y -= 10
    pdf.line(40, y, 555, y)
    y -= 20
    pdf.setFont(base_font, 10)
    pdf.drawString(40, y, "Подпись инспектора/оператора: ____________________")
    y -= 20
    pdf.drawString(40, y, "Подпись лица, ознакомленного с протоколом: ____________________")
    y -= 20
    pdf.drawString(40, y, "Дата ознакомления: ____________________")
    y -= 28

    if font_path:
        pdf.setFont(base_font, 8)
        pdf.drawString(40, y, f"Техническая информация: использован шрифт {Path(font_path).name}.")
    else:
        pdf.setFont(base_font, 8)
        pdf.drawString(40, y, "Техническая информация: системный шрифт без гарантии кириллицы.")

    pdf.showPage()
    y = page_height - 40
    pdf.setFont(base_font, 12)
    pdf.drawString(40, y, "Приложение А. Фотофиксация нарушения")
    y -= 20
    pdf.setFont(base_font, 9)
    pdf.drawString(40, y, f"Номер протокола: {protocol_number}")
    y -= 22

    for idx in selected_indices:
        event = events[idx]
        image_bytes = image_map.get(idx)
        if not image_bytes:
            continue

        if y < 240:
            pdf.showPage()
            y = page_height - 40
            pdf.setFont(base_font, 12)
            pdf.drawString(40, y, "Приложение А. Фотофиксация нарушения (продолжение)")
            y -= 26

        pdf.setFont(base_font, 11)
        pdf.drawString(40, y, f"Событие #{idx + 1}")
        y -= 16
        pdf.setFont(base_font, 10)
        pdf.drawString(40, y, f"track_id: {event.get('track_id', '-')}")
        y -= 14
        pdf.drawString(40, y, f"timestamp: {event.get('timestamp', '-')}")
        y -= 14
        pdf.drawString(40, y, f"confidence: {event.get('confidence', '-')}")
        y -= 12

        image = ImageReader(BytesIO(image_bytes))
        image_w, image_h = image.getSize()
        max_w, max_h = 260, 140
        scale = min(max_w / image_w, max_h / image_h)
        draw_w = image_w * scale
        draw_h = image_h * scale
        pdf.drawImage(
            image,
            40,
            y - draw_h,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        y -= draw_h + 24

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


api_url = os.getenv("HELMET_API_URL", DEFAULT_API_URL)
client = HelmetApiClient(api_url)

st.caption(f"Модель на сервере: `{model_path.name}`")
if is_trained:
    st.success("Обученная модель")
else:
    st.warning("Нужно обучение: `python training/train_yolo.py`")

try:
    health = client.health()
    if health.get("status") == "ok":
        st.success("API доступен")
    else:
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

        track_ids = sorted({event["track_id"] for event in events})
        violation_types = sorted({event["violation"] for event in events})

        selected_track = st.selectbox(
            "Фильтр по объекту (track_id)",
            ["Все"] + [str(track_id) for track_id in track_ids],
        )
        selected_violation = st.selectbox(
            "Фильтр по типу нарушения",
            ["Все"] + violation_types,
        )

        filtered_indices = [
            i
            for i, event in enumerate(events)
            if (selected_track == "Все" or str(event["track_id"]) == selected_track)
            and (selected_violation == "Все" or event["violation"] == selected_violation)
        ]
        filtered_events = [events[i] for i in filtered_indices]

        if filtered_events:
            grouped = defaultdict(list)
            for event in filtered_events:
                grouped[event["track_id"]].append(event)

            st.markdown("**Группы нарушений по одному объекту:**")
            for track_id, group in grouped.items():
                st.write(f"track_id {track_id}: {len(group)} снимков")

            st.dataframe(
                pd.DataFrame(filtered_events)[display_cols],
                use_container_width=True,
            )
            st.metric("Всего нарушений", len(filtered_events))
        else:
            st.warning("Нет событий для выбранного фильтра")
    else:
        st.info("Нарушений не обнаружено")

    st.subheader("Выберите релевантные снимки для PDF-протокола")
    if events:
        st.markdown("### Реквизиты протокола")
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            protocol_number = st.text_input("Номер протокола", value=f"AUTO-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
            organization = st.text_input("Организация/подразделение", value="Отдел мониторинга нарушений ПДД")
            inspector = st.text_input("Инспектор/оператор", value="")
        with meta_col2:
            location = st.text_input("Место фиксации", value="")
            source = st.text_input("Источник данных", value="Видеоаналитика Helmet Violation Detection")
            comment = st.text_area("Комментарий", value="", height=80)

        selected_indices = []
        cols = st.columns(3)
        for index, event in zip(filtered_indices, filtered_events):
            col = cols[index % 3]
            image_bytes = image_map.get(index)
            if image_bytes:
                col.image(
                    image_bytes,
                    caption=f"Событие {index + 1} | track {event.get('track_id', '-')}",
                    use_container_width=True,
                )
            else:
                col.warning("Снимок недоступен")
            if col.checkbox(
                f"Включить в протокол #{index + 1}",
                key=f"report_event_{index}",
                value=(len(selected_indices) == 0),
            ):
                selected_indices.append(index)

        if selected_indices:
            protocol_meta = {
                "protocol_number": protocol_number.strip(),
                "organization": organization.strip(),
                "inspector": inspector.strip(),
                "location": location.strip(),
                "source": source.strip(),
                "comment": comment.strip(),
            }
            pdf_bytes = build_violation_pdf(events, selected_indices, image_map, protocol_meta)
            st.download_button(
                "Скачать PDF-протокол",
                data=pdf_bytes,
                file_name="helmet_violation_report.pdf",
                mime="application/pdf",
                type="primary",
            )
        else:
            st.info("Отметьте хотя бы один снимок для формирования PDF")
    else:
        st.info("Нет снимков для выбора")
