import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

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
)

settings = get_settings()
model_path = get_model_path()
is_trained = "helmet_detector" in str(model_path)

st.title("🏍️ Система детекции нарушений — отсутствие шлема")
st.markdown(
    "Загрузите видео — анализ выполняется на сервере через API. "
    "Результаты: обработанное видео, таблица нарушений и снимки."
)

with st.sidebar:
    st.header("Подключение")
    api_url = st.text_input("URL API", value=os.getenv("HELMET_API_URL", DEFAULT_API_URL))
    client = HelmetApiClient(api_url)

    try:
        health = client.health()
        if health.get("status") == "ok":
            st.success("API доступен")
        else:
            st.warning(f"API: {health.get('status')} (БД: {health.get('database')}, Redis: {health.get('redis')})")
    except Exception as exc:
        st.error(f"API недоступен: {exc}")
        st.info("Запустите API: `python scripts/run_api.py` и worker: `python workers/run_worker.py`")

    st.divider()
    st.header("Модель (на сервере)")
    st.write(f"**Путь:** `{model_path.name}`")
    if is_trained:
        st.success("Обученная модель")
    else:
        st.warning("Нужно обучение: `python training/train_yolo.py`")

uploaded = st.file_uploader(

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
                    "job_id": job_id,
                    "events": events,
                st.subheader("Обработанное видео")
                try:
                    video_bytes = client.download_video(job_id)
                    if video_bytes:
                        st.video(video_bytes, format="video/mp4")
                        st.download_button(
                            "Скачать обработанное видео",
                            video_bytes,
                            file_name="helmet_analysis.mp4",
                            mime="video/mp4",
                        )
                except Exception as exc:
                    st.warning(f"Видео недоступно: {exc}")
            file_name="helmet_analysis.mp4",
                st.subheader("Зарегистрированные нарушения")
                events = client.list_events(job_id)

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
                st.subheader("Снимки нарушений")
                if events:
                    cols = st.columns(3)
                    for i, event in enumerate(events):
                        try:
                            img_bytes = client.download_image(event["image_url"])
                            cols[i % 3].image(
                                img_bytes,
                                caption=f"track {event['track_id']}",
                                use_container_width=True,
                            )
                        except Exception:
                            cols[i % 3].warning("Снимок недоступен")
                else:
                    st.info("Снимки отсутствуют")
                f"Включить в отчет #{i + 1}",
        except Exception as exc:
            st.error(f"Ошибка: {exc}")
else:
    st.info("Выберите видеофайл для начала анализа")
            )
        else:
            st.info("Выберите хотя бы один снимок для формирования PDF")
    else:
        st.info("Нет снимков для выбора")
