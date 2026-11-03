# -*- coding: utf-8 -*-
"""
Сборка статического сайта по ЕГЭ по информатике:
главная, страницы 27 заданий и реестр официальных документов.
Запуск:  python build_site.py
"""
from __future__ import annotations

import hashlib
import html
import json
from datetime import date
from pathlib import Path
from urllib.parse import quote

from content_tasks import TASKS, TASK_SECTIONS, TASK_BY_NUM

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "Исходники"
UPDATED = "03.11.2026"
UPDATED_LONG = "3 ноября 2026"

# Порядок хостингов видеоразборов: VK, Rutube, YouTube.
VIDEO_HOST_ORDER = {"VK": 0, "Rutube": 1, "YouTube": 2}
VIDEO_HOST_LABELS = {"VK": "VK Видео", "Rutube": "RuTube", "YouTube": "YouTube"}

VIDEO_HOST_ICONS = {
    "VK": (
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<path fill="#0077FF" d="m9.489.004.729-.003h3.564l.73.003.914.01.433.007.418.011.403.014.388.016.374.021.36.025.345.03.333.033c1.74.196 2.933.616 3.833 1.516.9.9 1.32 2.092 1.516 3.833l.034.333.029.346.025.36.02.373.025.588.012.41.013.644.009.915.004.98-.001 3.313-.003.73-.01.914-.007.433-.011.418-.014.403-.016.388-.021.374-.025.36-.03.345-.033.333c-.196 1.74-.616 2.933-1.516 3.833-.9.9-2.092 1.32-3.833 1.516l-.333.034-.346.029-.36.025-.373.02-.588.025-.41.012-.644.013-.915.009-.98.004-3.313-.001-.73-.003-.914-.01-.433-.007-.418-.011-.403-.014-.388-.016-.374-.021-.36-.025-.345-.03-.333-.033c-1.74-.196-2.933-.616-3.833-1.516-.9-.9-1.32-2.092-1.516-3.833l-.034-.333-.029-.346-.025-.36-.02-.373-.025-.588-.012-.41-.013-.644-.009-.915-.004-.98.001-3.313.003-.73.01-.914.007-.433.011-.418.014-.403.016-.388.021-.374.025-.36.03-.345.033-.333c.196-1.74.616-2.933 1.516-3.833.9-.9 2.092-1.32 3.833-1.516l.333-.034.346-.029.36-.025.373-.02.588-.025.41-.012.644-.013.915-.009ZM6.79 7.3H4.05c.13 6.24 3.25 9.99 8.72 9.99h.31v-3.57c2.01.2 3.53 1.67 4.14 3.57h2.84c-.78-2.84-2.83-4.41-4.11-5.01 1.28-.74 3.08-2.54 3.51-4.98h-2.58c-.56 1.98-2.22 3.78-3.8 3.95V7.3H10.5v6.92c-1.6-.4-3.62-2.34-3.71-6.92Z"/>'
        "</svg>"
    ),
    "Rutube": (
        '<svg viewBox="0 0 132 132" aria-hidden="true" focusable="false">'
        '<rect width="132" height="132" fill="#100943"/>'
        '<circle cx="132" cy="66" r="66" fill="#ED143B"/>'
        '<path fill="#fff" d="M81.5361 62.9865H42.5386V47.5547H81.5361C83.814 47.5547 85.3979 47.9518 86.1928 48.6451C86.9877 49.3385 87.4801 50.6245 87.4801 52.5031V58.0441C87.4801 60.0234 86.9877 61.3094 86.1928 62.0028C85.3979 62.6961 83.814 62.9925 81.5361 62.9925V62.9865ZM84.2115 33.0059H26V99H42.5386V77.5294H73.0176L87.4801 99H106L90.0546 77.4287C95.9333 76.5575 98.573 74.756 100.75 71.7869C102.927 68.8179 104.019 64.071 104.019 57.7359V52.7876C104.019 49.0303 103.621 46.0613 102.927 43.7857C102.233 41.51 101.047 39.5307 99.362 37.7528C97.5824 36.0698 95.6011 34.8845 93.2223 34.0904C90.8435 33.3971 87.8716 33 84.2115 33V33.0059Z"/>'
        "</svg>"
    ),
    "YouTube": (
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<path fill="#FF0000" d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>'
        "</svg>"
    ),
}


def video_host(url: str) -> str:
    """Хостинг видео по ссылке."""
    lowered = url.lower()
    if "vk.com/" in lowered or "vk.ru/" in lowered or "vkvideo" in lowered:
        return "VK"
    if "rutube" in lowered:
        return "Rutube"
    if "youtube" in lowered or "youtu.be" in lowered:
        return "YouTube"
    return ""


def video_sort_key(video) -> int:
    """Сортировка видеоразборов по хостингу, внутри — исходный порядок."""
    return VIDEO_HOST_ORDER.get(video_host(video[3]), len(VIDEO_HOST_ORDER))


def fmt_size(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n / 1024:.0f}\u00a0КБ"
    return f"{n / 1024 / 1024:.1f}\u00a0МБ".replace(".", ",")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def d(**kw):
    """Документ реестра."""
    kw.setdefault("year", "2027")
    kw.setdefault("kind", "pdf")
    kw.setdefault("filter_kind", "kim")
    kw.setdefault("status", "project")
    kw.setdefault("status_label", "проект")
    kw.setdefault("pages", None)
    kw.setdefault("alt_path", None)
    kw.setdefault("alt_label", None)
    kw.setdefault("note", None)
    return kw


FIPI_2027_ZIP = "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2027/inf_11_2027.zip"
FIPI_2026_ZIP = "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2026/inf_11_2026.zip"
FIPI_NORM = "https://fipi.ru/ege/normativno-pravovye-dokumenty"
FIPI_METHOD = "https://fipi.ru/ege/analiticheskie-i-metodicheskie-materialy"
FIPI_NAV = "https://fipi.ru/navigator-podgotovki/navigator-ege"
FIPI_OPEN = "https://fipi.ru/ege/otkrytyy-bank-zadaniy-ege/otkrytyye-varianty-kim-ege"

DOCS = [
    # ------------------------------------------------------------------ 2027
    d(
        section="kim2027",
        code="27·ДЕМО",
        title="Демонстрационный вариант",
        desc="КИМ ЕГЭ 2027 по информатике: 27 заданий, ответы, критерии оценивания и файлы для компьютерной части.",
        path="Исходники/inf_11_2027/ИНФ-11 ЕГЭ 2027 ДЕМО.pdf",
        source=FIPI_2027_ZIP,
        source_label="ФИПИ · inf_11_2027.zip",
        pages=14,
    ),
    d(
        section="kim2027",
        code="27·СПЕЦ",
        title="Спецификация",
        desc="Структура и содержание работы: 27 заданий, 29 первичных баллов, 235 минут, 11 заданий со специализированным ПО.",
        path="Исходники/inf_11_2027/ИНФ-11 ЕГЭ 2027 СПЕЦ.pdf",
        source=FIPI_2027_ZIP,
        source_label="ФИПИ · inf_11_2027.zip",
        pages=8,
    ),
    d(
        section="kim2027",
        code="27·КОДИФ",
        title="Кодификатор",
        desc="Проверяемые элементы содержания и требования к результатам. Четыре содержательных раздела курса информатики.",
        path="Исходники/inf_11_2027/ИНФ-11 ЕГЭ 2027 КОДИФ.pdf",
        source=FIPI_2027_ZIP,
        source_label="ФИПИ · inf_11_2027.zip",
        pages=8,
    ),
    d(
        section="kim2027",
        code="27·ИЗМ",
        title="Планируемые изменения",
        desc="Сводный документ ФИПИ по всем предметам. Раздел «Информатика»: структура без изменений, новые темы заданий 10, 13, 23 и формат ответа 27.",
        path="Исходники/inf_11_2027/Планируемые изменения в КИМ ЕГЭ 2027.pdf",
        source="https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2027/Plan_izmeneniya_KIM_EGE_2027.pdf",
        source_label="ФИПИ · планируемые изменения",
        pages=2,
    ),
    d(
        section="kim2027",
        code="27·ZIP",
        title="Полный архив ФИПИ",
        desc="Оригинальная выгрузка: демоверсия, спецификация, кодификатор и папка «Файлы» с материалами к заданиям.",
        path="Исходники/inf_11_2027/inf_11_2027.zip",
        source="https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2027/inf_11_2027.zip",
        source_label="ФИПИ · inf_11_2027.zip",
        kind="zip",
        status_label="архив",
    ),
    d(
        section="kim2027",
        code="27·ФАЙЛЫ",
        title="Файлы к заданиям",
        desc="Девять файлов .ods и .txt для заданий 3, 9, 17, 18, 22, 23, 24, 26 и 27.",
        path="Исходники/inf_11_2027/Файлы к демоверсии 2027.zip",
        source=FIPI_2027_ZIP,
        source_label="ФИПИ · inf_11_2027.zip",
        kind="zip",
        status_label="архив",
    ),
    # ------------------------------------------------------- 2027 сроки/баллы
    d(
        section="dates2027",
        code="27·РАСП",
        title="Проект расписания ЕГЭ 2027",
        desc="Информатика: 6 апреля (досрочный период), 18–19 июня (основной). Резервные дни — 19 апреля, 21, 23, 25 и 26 июня.",
        path="Исходники/Нормативные документы/Проект приказа. Расписание ЕГЭ 2027 (PDF).pdf",
        source="https://regulation.gov.ru/projects/172223/",
        source_label="regulation.gov.ru · проект № 172223",
        pages=6,
        status="project",
        status_label="проект",
        filter_kind="norm",
        alt_path="Исходники/Нормативные документы/Проект приказа. Расписание ЕГЭ 2027 (DOCX).docx",
        alt_label="DOCX",
        note="PDF — копия официального DOCX с портала. Общественное обсуждение — до 10.11.2026.",
    ),
    d(
        section="dates2027",
        code="27·БАЛЛ",
        title="Проект минимальных баллов на 2027/28",
        desc="Минимум для приёма в вузы, подведомственные Минобрнауки: информатика — 46 баллов. Это не минимальный балл для аттестата.",
        path="Исходники/Нормативные документы/Проект приказа. Минимальные баллы ЕГЭ 2027-28 (PDF).pdf",
        source="https://regulation.gov.ru/projects/172213/",
        source_label="regulation.gov.ru · проект № 172213",
        pages=3,
        status="project",
        status_label="проект",
        filter_kind="norm",
        alt_path="Исходники/Нормативные документы/Проект приказа. Минимальные баллы ЕГЭ 2027-28 (DOCX).docx",
        alt_label="DOCX",
        note="PDF — копия официального DOCX с портала. Проект приказа Минобрнауки России от 23.10.2026.",
    ),
    # ------------------------------------------------------------------ 2026
    d(
        section="kim2026",
        code="26·ДЕМО",
        title="Демонстрационный вариант",
        desc="Утверждённый КИМ ЕГЭ 2026: 27 заданий, ответы, критерии оценивания и файлы для компьютерной части.",
        path="Исходники/inf_11_2026/ИНФ-11 ЕГЭ 2026 ДЕМО.pdf",
        source=FIPI_2026_ZIP,
        source_label="ФИПИ · inf_11_2026.zip",
        year="2026",
        status="approved",
        status_label="утверждён",
        pages=14,
    ),
    d(
        section="kim2026",
        code="26·СПЕЦ",
        title="Спецификация",
        desc="Структура работы 2026 года: 27 заданий, 29 первичных баллов, 235 минут.",
        path="Исходники/inf_11_2026/ИНФ-11 ЕГЭ 2026 СПЕЦ.pdf",
        source=FIPI_2026_ZIP,
        source_label="ФИПИ · inf_11_2026.zip",
        year="2026",
        status="approved",
        status_label="утверждён",
        pages=9,
    ),
    d(
        section="kim2026",
        code="26·КОДИФ",
        title="Кодификатор",
        desc="Элементы содержания и требования к результатам для КИМ 2026 года.",
        path="Исходники/inf_11_2026/ИНФ-11 ЕГЭ 2026 КОДИФ.pdf",
        source=FIPI_2026_ZIP,
        source_label="ФИПИ · inf_11_2026.zip",
        year="2026",
        status="approved",
        status_label="утверждён",
        pages=13,
    ),
    d(
        section="kim2026",
        code="26·ZIP",
        title="Полный архив ФИПИ",
        desc="Оригинальный ZIP: демоверсия, спецификация, кодификатор и папка «Файлы».",
        path="Исходники/inf_11_2026/inf_11_2026.zip",
        source="https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2026/inf_11_2026.zip",
        source_label="ФИПИ · inf_11_2026.zip",
        year="2026",
        kind="zip",
        status="approved",
        status_label="архив",
    ),
    d(
        section="kim2026",
        code="26·ВАРИАНТ",
        title="Открытый вариант КИМ 2026",
        desc="Вариант, опубликованный ФИПИ 28.04.2026: 28 страниц с заданиями, ответами и критериями.",
        path="Исходники/inf_11_2026/Открытый вариант 2026/Открытый вариант КИМ ЕГЭ 2026 (Информатика).pdf",
        source="https://doc.fipi.ru/ege/otkrytyy-bank-zadaniy-ege/otkrytyye-varianty-kim-ege/2026/Inf_1_ege2026.zip",
        source_label="ФИПИ · открытые варианты 2026",
        year="2026",
        status="approved",
        status_label="утверждён",
        pages=28,
    ),
    d(
        section="kim2026",
        code="26·ВАР-ZIP",
        title="Открытый вариант: оригинальный ZIP",
        desc="ZIP ФИПИ с PDF варианта и файлами к заданиям.",
        path="Исходники/inf_11_2026/Открытый вариант КИМ ЕГЭ 2026 (Информатика).zip",
        source="https://doc.fipi.ru/ege/otkrytyy-bank-zadaniy-ege/otkrytyye-varianty-kim-ege/2026/Inf_1_ege2026.zip",
        source_label="ФИПИ · открытые варианты 2026",
        year="2026",
        kind="zip",
        status="approved",
        status_label="архив",
    ),
    d(
        section="kim2026",
        code="26·ФАЙЛЫ",
        title="Файлы к демоверсии 2026",
        desc="Десять файлов .odt, .ods и .txt для заданий демонстрационного варианта.",
        path="Исходники/inf_11_2026/Файлы к демоверсии 2026.zip",
        source=FIPI_2026_ZIP,
        source_label="ФИПИ · inf_11_2026.zip",
        year="2026",
        kind="zip",
        status="approved",
        status_label="архив",
    ),
    # ------------------------------------------------------------ методические
    d(
        section="method",
        code="МЕТ·2026",
        title="Методические рекомендации для учителей",
        desc="Анализ типичных ошибок участников ЕГЭ 2026 года и рекомендации по подготовке. Опубликовано 15.09.2026.",
        path="Исходники/Методические материалы/Методические рекомендации для учителей. Информатика. 2026.pdf",
        source="https://doc.fipi.ru/ege/analiticheskie-i-metodicheskie-materialy/2026/inf_mr_2026.pdf",
        source_label="ФИПИ · аналитические материалы",
        year="2026",
        status="current",
        status_label="2026",
        filter_kind="method",
        pages=31,
    ),
    d(
        section="method",
        code="НАВ·2026",
        title="Навигатор самостоятельной подготовки",
        desc="Методические рекомендации по самостоятельной подготовке к ЕГЭ по информатике в 2026 году.",
        path="Исходники/Методические материалы/Навигатор самостоятельной подготовки. Информатика. 2026.pdf",
        source=FIPI_NAV,
        source_label="ФИПИ · навигатор подготовки",
        year="2026",
        status="current",
        status_label="2026",
        filter_kind="method",
        pages=20,
    ),
    d(
        section="method",
        code="НАВ·01",
        title="Навигатор: цифровая грамотность",
        desc="Тематический раздел навигатора: устройство компьютера, сети, программное обеспечение.",
        path="Исходники/Методические материалы/Навигатор. Цифровая грамотность.pdf",
        source="https://doc.fipi.ru/navigator-podgotovki/navigator-ege/2026/Inf_1_gramotnost.pdf",
        source_label="ФИПИ · навигатор, раздел 1",
        year="2026",
        status="current",
        status_label="2026",
        filter_kind="method",
        pages=2,
    ),
    d(
        section="method",
        code="НАВ·02",
        title="Навигатор: теоретические основы",
        desc="Тематический раздел: кодирование, измерение информации, логика, моделирование.",
        path="Исходники/Методические материалы/Навигатор. Теоретические основы информатики.pdf",
        source="https://doc.fipi.ru/navigator-podgotovki/navigator-ege/2026/Inf_2_teoriya.pdf",
        source_label="ФИПИ · навигатор, раздел 2",
        year="2026",
        status="current",
        status_label="2026",
        filter_kind="method",
        pages=6,
    ),
    d(
        section="method",
        code="НАВ·03",
        title="Навигатор: алгоритмы и программирование",
        desc="Тематический раздел: алгоритмы, анализ программ, программирование на языках высокого уровня.",
        path="Исходники/Методические материалы/Навигатор. Алгоритмы и программирование.pdf",
        source="https://doc.fipi.ru/navigator-podgotovki/navigator-ege/2026/Inf_3_algoritm.pdf",
        source_label="ФИПИ · навигатор, раздел 3",
        year="2026",
        status="current",
        status_label="2026",
        filter_kind="method",
        pages=4,
    ),
    d(
        section="method",
        code="НАВ·04",
        title="Навигатор: информационные технологии",
        desc="Тематический раздел: электронные таблицы, базы данных, текстовые документы, поиск.",
        path="Исходники/Методические материалы/Навигатор. Информационные технологии.pdf",
        source="https://doc.fipi.ru/navigator-podgotovki/navigator-ege/2026/Inf_4_tehnologii.pdf",
        source_label="ФИПИ · навигатор, раздел 4",
        year="2026",
        status="current",
        status_label="2026",
        filter_kind="method",
        pages=3,
    ),
    # --------------------------------------------------------------- нормативные
    d(
        section="norm",
        code="НОРМ·01",
        title="Порядок проведения ГИА-11",
        desc="Приказ Минпросвещения России и Рособрнадзора № 233/552 от 04.04.2023. Права участников, сроки, апелляции.",
        path="Исходники/Нормативные документы/Порядок проведения ГИА-11 (приказ 233-552 от 04.04.2023).pdf",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/Poriadok-provedeniia-GIA-11.pdf",
        source_label="ФИПИ · нормативные документы",
        year="2026",
        status="current",
        status_label="действует",
        filter_kind="norm",
        pages=62,
    ),
    d(
        section="norm",
        code="НОРМ·02",
        title="Изменения в Порядок ГИА-11",
        desc="Приказ № 243/802 от 12.04.2024: изменения в порядок проведения ГИА-11.",
        path="Исходники/Нормативные документы/Изменения в Порядок ГИА-11 (приказ 243-802 от 12.04.2024).pdf",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/Prikaz_243_802_12.04.24.pdf",
        source_label="ФИПИ · нормативные документы",
        year="2026",
        status="current",
        status_label="действует",
        filter_kind="norm",
        pages=3,
    ),
    d(
        section="norm",
        code="НОРМ·03",
        title="Порядок разработки и хранения КИМ",
        desc="Приказ Рособрнадзора № 871 от 11.08.2022: разработка, использование и хранение КИМ.",
        path="Исходники/Нормативные документы/Порядок разработки и хранения КИМ (приказ 871 от 11.08.2022).pdf",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/poryadok-razrabotki-kim.pdf",
        source_label="ФИПИ · нормативные документы",
        year="2026",
        status="current",
        status_label="действует",
        filter_kind="norm",
        pages=12,
    ),
    d(
        section="norm",
        code="НОРМ·04",
        title="Изменения в Порядок разработки КИМ",
        desc="Приказ Рособрнадзора № 73 от 19.01.2024.",
        path="Исходники/Нормативные документы/Изменения в Порядок разработки КИМ (приказ 73 от 19.01.2024).pdf",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/poryadok-razrabotki-kim_izm_2024.pdf",
        source_label="ФИПИ · нормативные документы",
        year="2026",
        status="current",
        status_label="действует",
        filter_kind="norm",
        pages=5,
    ),
    d(
        section="norm",
        code="НОРМ·05",
        title="Изменения в Порядок разработки КИМ",
        desc="Приказ Рособрнадзора № 1555 от 27.08.2025.",
        path="Исходники/Нормативные документы/Изменения в Порядок разработки КИМ (приказ 1555 от 27.08.2025).pdf",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/Prikaz_1555_2025.pdf",
        source_label="ФИПИ · нормативные документы",
        year="2026",
        status="current",
        status_label="действует",
        filter_kind="norm",
        pages=8,
    ),
    d(
        section="norm",
        code="НОРМ·06",
        title="Единое расписание ЕГЭ 2026",
        desc="Приказ № 798/1094 от 07.11.2025: досрочный, основной и дополнительный периоды ЕГЭ 2026 года.",
        path="Исходники/Нормативные документы/Единое расписание ЕГЭ 2026 (приказ 798-1094 от 07.11.2025).pdf",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/ege2026.pdf",
        source_label="ФИПИ · нормативные документы",
        year="2026",
        status="current",
        status_label="действует",
        filter_kind="norm",
        pages=6,
    ),
    d(
        section="norm",
        code="НОРМ·07",
        title="Правила заполнения бланков",
        desc="Правила заполнения бланков ЕГЭ и ГВЭ-11 в 2026 году. 45 страниц с образцами.",
        path="Исходники/Нормативные документы/Правила заполнения бланков ЕГЭ и ГВЭ-11 в 2026 году.pdf",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/Pravila_zapolneniya_blankov_2026.pdf",
        source_label="ФИПИ · нормативные документы",
        year="2026",
        status="current",
        status_label="действует",
        filter_kind="norm",
        pages=45,
    ),
    d(
        section="norm",
        code="НОРМ·08",
        title="Методические документы ГИА 2026",
        desc="Архив Рособрнадзора: методические документы для организации и проведения ГИА-11 в 2026 году.",
        path="Исходники/Нормативные документы/Методические документы ГИА 2026 (Рособрнадзор).zip",
        source="https://doc.fipi.ru/ege/normativno-pravovye-dokumenty/MR_RON_GIA_2026.zip",
        source_label="ФИПИ · письмо № 04-20 от 02.02.2026",
        year="2026",
        status="current",
        status_label="архив",
        filter_kind="norm",
        kind="zip",
    ),
]

ARCHIVE = [
    (2025, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2025/inf_11_2025.zip", "ДЕМО · КОДИФ · СПЕЦ + файлы"),
    (2024, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2024/inf_11_2024.zip", "ДЕМО · КОДИФ · СПЕЦ + файлы"),
    (2023, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2023/inf_11_2023.zip", "ДЕМО · КОДИФ · СПЕЦ + файлы"),
    (2022, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2022/inf_11_2022.zip", "ДЕМО · КОДИФ · СПЕЦ + файлы"),
    (2021, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2021/inf-ege-2021.zip", "ДЕМО · КОДИФ · СПЕЦ + файлы"),
    (2020, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2020/inf_ege_2020.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2019, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2019/inf_ege_2019.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2018, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2018/ing_ege_2018.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2017, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2017/inf_ege_2017.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2016, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2016/inf_11_2016.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2015, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2015/inf_11_2015.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2014, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2014/Inf_ege14.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2013, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2013/inf11.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2012, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2012/infEGE2012.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2011, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2011/inf_10_11_10.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2010, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2010/inf.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2009, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2009/inf.zip", "ДЕМО · КОДИФ · СПЕЦ"),
    (2007, "https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/2007/inf.zip", "ДЕМО · КОДИФ · СПЕЦ (DOC)"),
]

SECTIONS = [
    dict(
        id="kim2027",
        num="01",
        nav="2027 · КИМ",
        eyebrow="2027 · проекты ФИПИ",
        title="КИМ и материалы",
        lead="Демоверсия, спецификация, кодификатор и сводка изменений. Опубликованы 28.08.2026 как проекты; общественное обсуждение завершилось 30.09.2026.",
        filter_kind="kim",
        year="2027",
    ),
    dict(
        id="dates2027",
        num="02",
        nav="2027 · сроки и баллы",
        eyebrow="2027 · проекты приказов",
        title="Сроки и минимальные баллы",
        lead="Проект расписания и проект минимальных баллов для приёма в вузы. Оба документа пока не утверждены — даты и баллы могут измениться.",
        filter_kind="norm",
        year="2027",
    ),
    dict(
        id="kim2026",
        num="03",
        nav="2026 · действующая база",
        eyebrow="2026 · утверждено",
        title="Действующие КИМ и открытый вариант",
        lead="Полный комплект утверждённых документов 2026 года и открытый вариант, опубликованный ФИПИ 28.04.2026. Полезен для практики и сравнения с проектом 2027 года.",
        filter_kind="kim",
        year="2026",
    ),
    dict(
        id="method",
        num="04",
        nav="Методические материалы",
        eyebrow="Методика · 2026",
        title="Материалы для подготовки",
        lead="Разбор типичных ошибок, рекомендации для учителей и навигатор самостоятельной подготовки по четырём содержательным разделам.",
        filter_kind="method",
        year="2026",
    ),
    dict(
        id="norm",
        num="05",
        nav="Нормативная база",
        eyebrow="Правила · процедура",
        title="Нормативные документы",
        lead="Порядок проведения ГИА-11, правила разработки КИМ, расписание 2026 года и правила заполнения бланков.",
        filter_kind="norm",
        year="2026",
    ),
    dict(
        id="archive",
        num="06",
        nav="Архив демоверсий",
        eyebrow="2007–2025 · ФИПИ",
        title="Архив демоверсий",
        lead="Оригинальные ZIP-архивы ФИПИ по годам: демонстрационный вариант, спецификация, кодификатор и файлы к заданиям. Форматы прошлых лет могут отличаться от действующей модели.",
        filter_kind="archive",
        year="archive",
    ),
]

SOURCES = [
    ("ФИПИ", "Демоверсии, спецификации, кодификаторы", "https://fipi.ru/ege/demoversii-specifikacii-kodifikatory"),
    ("ФИПИ", "Нормативно-правовые документы", "https://fipi.ru/ege/normativno-pravovye-dokumenty"),
    ("ФИПИ", "Аналитические и методические материалы", "https://fipi.ru/ege/analiticheskie-i-metodicheskie-materialy"),
    ("ФИПИ", "Навигатор самостоятельной подготовки", "https://fipi.ru/navigator-podgotovki/navigator-ege"),
    ("ФИПИ", "Открытые варианты КИМ", "https://fipi.ru/ege/otkrytyy-bank-zadaniy-ege/otkrytyye-varianty-kim-ege"),
    ("ФИПИ", "Открытый банк заданий ЕГЭ", "https://ege.fipi.ru/bank/"),
    ("Рособрнадзор", "ГИА-11: документы и материалы", "https://obrnadzor.gov.ru/gia/gia-11/"),
    ("regulation.gov.ru", "Проект расписания ЕГЭ 2027", "https://regulation.gov.ru/projects/172223/"),
]


def doc_size(doc: dict) -> int:
    return (ROOT / doc["path"]).stat().st_size


def doc_meta(doc: dict) -> str:
    parts = []
    if doc["kind"] == "pdf":
        parts.append("PDF")
        if doc["pages"]:
            parts.append(f"{doc['pages']}\u00a0стр.")
    elif doc["kind"] == "zip":
        parts.append("ZIP")
    elif doc["kind"] == "docx":
        parts.append("DOCX")
    parts.append(fmt_size(doc_size(doc)))
    return " · ".join(parts)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def url(path: str) -> str:
    return quote(path.replace("\\", "/"), safe="/")


def render_doc(doc: dict) -> str:
    path = url(doc["path"])
    basename = Path(doc["path"]).name
    search = " ".join(
        str(x)
        for x in [
            doc["code"],
            doc["title"],
            doc["desc"],
            doc["year"],
            doc["source_label"],
            "проект" if doc["status"] == "project" else "",
            "архив" if doc["kind"] == "zip" else "",
        ]
    ).lower()
    badge = f'<span class="badge badge-{esc(doc["status"])}">{esc(doc["status_label"])}</span>'
    alt = ""
    if doc.get("alt_path"):
        alt = (
            f'<span class="alt">оригинал: '
            f'<a href="{url(doc["alt_path"])}" download>{esc(doc["alt_label"])}</a></span>'
        )
    note = ""
    if doc.get("note"):
        note = f'<p class="doc-note">{esc(doc["note"])}</p>'
    actions = (
        f'<a class="btn btn-open" href="{path}" target="_blank" rel="noopener" '
        f'data-view="{esc(doc["kind"])}" data-path="{path}" data-title="{esc(doc["title"])}" '
        f'data-code="{esc(doc["code"])}" data-status="{esc(doc["status_label"])}" '
        f'data-source="{esc(doc["source"])}" data-filename="{esc(basename)}">Открыть</a>'
        f'<a class="btn btn-dl" href="{path}" download="{esc(basename)}">Скачать</a>'
    )
    return f'''
<article class="doc" data-doc data-year="{esc(doc["year"])}" data-kind="{esc(doc["filter_kind"])}"
         data-status="{esc(doc["status"])}" data-search="{esc(search)}">
  <div class="doc-code">
    <span class="code">{esc(doc["code"])}</span>
    {badge}
  </div>
  <div class="doc-body">
    <h3>{esc(doc["title"])}</h3>
    <p>{esc(doc["desc"])}</p>
    <div class="doc-meta">
      <span>{doc_meta(doc)}</span>
      {alt}
      <a class="source" href="{esc(doc["source"])}" target="_blank" rel="noopener noreferrer">Источник: {esc(doc["source_label"])} <span aria-hidden="true">↗</span></a>
    </div>
    {note}
  </div>
  <div class="doc-actions">{actions}</div>
</article>'''


def render_section(section: dict) -> str:
    docs = [x for x in DOCS if x["section"] == section["id"]]
    if section["id"] == "archive":
        body = render_archive()
    else:
        body = '<div class="doc-list">' + "".join(render_doc(x) for x in docs) + "</div>"

    extra = ""
    if section["id"] == "kim2027":
        extra = '''
<div class="changes">
  <div class="changes-copy">
    <p class="eyebrow">Что меняется в 2027</p>
    <h3>Структура прежняя, акценты другие</h3>
    <p>Количество заданий и максимальный первичный балл не изменились. ФИПИ перераспределил темы нескольких заданий и изменил форму записи ответа в задании 27.</p>
  </div>
  <dl class="change-list">
    <div><dt><a href="tasks/10.html">Задание 10</a></dt><dd>маска подсети вместо поиска в текстовом процессоре</dd></div>
    <div><dt><a href="tasks/13.html">Задание 13</a></dt><dd>анализ хода исполнения алгоритма</dd></div>
    <div><dt><a href="tasks/23.html">Задание 23</a></dt><dd>алгоритмические задачи на графы</dd></div>
    <div><dt><a href="tasks/27.html">Задание 27</a></dt><dd>один ответ из двух чисел вместо двух строк</dd></div>
  </dl>
</div>'''
    elif section["id"] == "dates2027":
        extra = '''
<div class="dates" aria-label="Ключевые даты проекта расписания ЕГЭ 2027">
  <div><span class="date">06.04</span><span class="date-label">досрочный период · информатика</span></div>
  <div><span class="date">18–19.06</span><span class="date-label">основной период · информатика</span></div>
  <div><span class="date">21 · 23 · 25 · 26.06</span><span class="date-label">резервные дни</span></div>
  <div><span class="date">46</span><span class="date-label">минимальный балл для вузов · проект</span></div>
</div>
<p class="dates-note">Проект расписания опубликован 26.10.2026. Даты могут измениться после утверждения приказа. Минимальный балл для получения аттестата на 2027 год на 03.11.2026 не опубликован.</p>'''
    elif section["id"] == "archive":
        extra = '''
<div class="archive-note">
  <p><strong>2008 год:</strong> на странице ФИПИ архив за этот год не опубликован. Для 2018 года ФИПИ выложил архив под именем <code>ing_ege_2018.zip</code> — внутри документы по информатике.</p>
</div>'''

    return f'''
<section class="registry-section" id="{section["id"]}" data-section-kind="{section["filter_kind"]}" data-section-year="{section["year"]}">
  <header class="section-head">
    <div class="section-num">{section["num"]}</div>
    <div class="section-copy">
      <p class="eyebrow">{esc(section["eyebrow"])}</p>
      <h2>{esc(section["title"])}</h2>
      <p class="section-lead">{esc(section["lead"])}</p>
    </div>
  </header>
  {extra}
  {body}
</section>'''


def render_archive() -> str:
    rows = []
    for year, source, composition in ARCHIVE:
        path = f"Исходники/Архив демоверсий/inf_11_{year}.zip"
        size = fmt_size((ROOT / path).stat().st_size)
        rows.append(f'''
<tr data-doc data-year="archive" data-kind="archive" data-search="{year} архив демоверсия">
  <td class="archive-year">{year}</td>
  <td class="archive-composition">{esc(composition)}</td>
  <td class="archive-size">{size}</td>
  <td class="archive-actions">
    <a class="text-link" href="{url(path)}" download>Скачать ZIP</a>
    <a class="source" href="{esc(source)}" target="_blank" rel="noopener noreferrer">Источник <span aria-hidden="true">↗</span></a>
  </td>
</tr>''')
    return f'''
<div class="archive-wrap">
  <table class="archive-table">
    <thead>
      <tr><th scope="col">Год</th><th scope="col">Состав архива</th><th scope="col">Размер</th><th scope="col">Действия</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>'''


def render_sources() -> str:
    cards = []
    for name, title, link in SOURCES:
        cards.append(f'''
<a class="source-card" href="{esc(link)}" target="_blank" rel="noopener noreferrer">
  <span class="source-name">{esc(name)}</span>
  <span class="source-title">{esc(title)}</span>
  <span class="source-url">{esc(link)}</span>
</a>''')
    return f'''
<section class="registry-section sources-section" id="sources">
  <header class="section-head">
    <div class="section-num">07</div>
    <div class="section-copy">
      <p class="eyebrow">Первоисточники</p>
      <h2>Официальные сайты</h2>
      <p class="section-lead">Ссылки на разделы, откуда скачаны документы. Если файл обновился, приоритет всегда у первоисточника.</p>
    </div>
  </header>
  <div class="sources-grid">{''.join(cards)}</div>
</section>'''


# ---------------------------------------------------------------------------
# Общие элементы сайта
# ---------------------------------------------------------------------------

def point_word(n: int) -> str:
    return f"{n} балл" if n == 1 else f"{n} балла"


def tasks_word(n: int) -> str:
    n10 = n % 10
    n100 = n % 100
    if n10 == 1 and n100 != 11:
        return f"{n} задание"
    if 2 <= n10 <= 4 and not 12 <= n100 <= 14:
        return f"{n} задания"
    return f"{n} заданий"


def task_points(num: int) -> int:
    return 2 if num in (26, 27) else 1


# Задания 19–21 объединены в одну страницу: 19 — основная, 20 и 21 — якоря на ней.
MERGED_PAGES = {
    20: (19, "subtask-20"),
    21: (19, "subtask-21"),
}
MERGED_NUMS = {19} | set(MERGED_PAGES)


def task_href(num: int, prefix: str = "tasks/") -> str:
    if num in MERGED_PAGES:
        target, anchor = MERGED_PAGES[num]
        return f"{prefix}{target:02d}.html#{anchor}"
    return f"{prefix}{num:02d}.html"


def task_label(num: int) -> str:
    task = TASK_BY_NUM[num]
    if task.get("subtasks"):
        return f"19–21 · {task['title']}"
    return f"{num:02d} · {task['title']}"


def topbar(prefix: str, active: str, meta: str | None = None) -> str:
    def nav_item(key: str, href: str, label: str) -> str:
        cls = ' class="is-active"' if active == key else ""
        aria = ' aria-current="page"' if active == key else ""
        return f'<a href="{href}"{cls}{aria}>{label}</a>'

    meta_html = meta or f'<span>2027 · 27 заданий</span><span>обновлено {UPDATED}</span>'
    return f'''
<header class="topbar">
  <a class="brand" href="{prefix}index.html" aria-label="На главную">
    <span class="brand-mark" aria-hidden="true">И</span>
    <span class="brand-text">ЕГЭ · Информатика<small>подготовка по заданиям</small></span>
  </a>
  <nav class="site-nav" aria-label="Основная навигация">
    {nav_item("home", f"{prefix}index.html", "Главная")}
    {nav_item("tasks", f"{prefix}tasks/index.html", "Задания")}
    {nav_item("documents", f"{prefix}documents.html", "Документы")}
  </nav>
  <div class="topbar-meta">{meta_html}</div>
</header>'''


def page_shell(title: str, description: str, prefix: str, active: str, content: str, meta: str | None = None) -> str:
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#F0F1EB">
<link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{prefix}assets/site.css">
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
{topbar(prefix, active, meta)}
<main id="main">
{content}
</main>
{footer(prefix)}
<script src="{prefix}assets/site.js" defer></script>
</body>
</html>'''


def footer(prefix: str) -> str:
    return f'''
<footer>
  <div class="footer-inner">
    <div>
      <p class="footer-mark">ЕГЭ · Информатика · 2027</p>
      <p class="footer-note">Разбор заданий, ключевые темы и официальные документы. Составлено {UPDATED_LONG}. Не является официальным ресурсом ФИПИ или Рособрнадзора.</p>
    </div>
    <div>
      <p class="footer-title">Разделы</p>
      <p class="footer-note"><a href="{prefix}index.html">Главная</a> · <a href="{prefix}tasks/index.html">Все задания</a> · <a href="{prefix}documents.html">Документы</a></p>
      <p class="footer-note">27 заданий · 29 первичных баллов · 235 минут</p>
    </div>
    <div>
      <p class="footer-title">Первоисточники</p>
      <p class="footer-note"><a href="https://fipi.ru/ege/demoversii-specifikacii-kodifikatory" target="_blank" rel="noopener noreferrer">ФИПИ</a> · <a href="https://obrnadzor.gov.ru/gia/gia-11/" target="_blank" rel="noopener noreferrer">Рособрнадзор</a> · <a href="https://regulation.gov.ru/projects/172223/" target="_blank" rel="noopener noreferrer">проект расписания</a></p>
      <p class="footer-note">Права на документы принадлежат их правообладателям. Копии сохранены для ознакомления и подготовки.</p>
    </div>
  </div>
</footer>'''


def breadcrumbs(prefix: str, items: list[tuple[str | None, str]]) -> str:
    parts = []
    for href, label in items:
        if href:
            parts.append(f'<a href="{href}">{esc(label)}</a>')
        else:
            parts.append(f'<span aria-current="page">{esc(label)}</span>')
    return '<nav class="breadcrumb" aria-label="Хлебные крошки">' + '<span class="crumb-sep">/</span>'.join(parts) + "</nav>"


# ---------------------------------------------------------------------------
# Карта заданий и карточки
# ---------------------------------------------------------------------------

def render_task_map_cell(
    task: dict,
    prefix: str,
    current_set: set[int],
    compact: bool = False,
    merge_merged: bool = True,
) -> str:
    num = task["num"]
    is_range = bool(task.get("subtasks")) and merge_merged
    classes = ["task-cell", f"task-cell--{task['section']}"]

    if is_range:
        classes.append("task-cell--range")
        if current_set & MERGED_NUMS:
            classes.append("is-current")
    elif num in current_set:
        classes.append("is-current")

    if num in MERGED_NUMS:
        classes.append("task-cell--merged")
    if compact:
        classes.append("task-cell--compact")

    section = TASK_SECTIONS[task["section"]]
    if is_range:
        caption = (
            f'<strong>Задания 19–21</strong> · {esc(task["title"])} · '
            f'одна общая страница'
        )
        data_task = ",".join(str(n) for n in sorted(MERGED_NUMS))
        label = "19–21"
        aria_label = f'Задания 19–21: {esc(task["title"])}'
    else:
        if num in MERGED_PAGES:
            caption = (
                f'<strong>Задание {num}</strong> · в теме 19–21 · '
                f'{esc(section["short"])} · {point_word(task_points(num))}'
            )
        else:
            caption = (
                f'<strong>Задание {num}</strong> · {esc(task["title"])} · '
                f'{esc(section["short"])} · {point_word(task_points(num))}'
            )
        data_task = str(num)
        label = str(num)
        aria_label = f'Задание {num}: {esc(task["title"])}'

    return (
        f'<a class="{" ".join(classes)}" href="{task_href(num, prefix)}" data-task="{data_task}" '
        f'data-section="{task["section"]}" data-title="{esc(task["title"])}" '
        f'data-caption="{esc(caption)}" aria-label="{aria_label}">'
        f'<span>{label}</span></a>'
    )


def task_map(
    prefix: str = "tasks/",
    current: int | list[int] | tuple[int, ...] | None = None,
    compact: bool = False,
    extra_class: str = "",
) -> str:
    if current is None:
        current_set: set[int] = set()
    elif isinstance(current, (list, tuple, set)):
        current_set = set(current)
    else:
        current_set = {current}

    cells = []
    for task in TASKS:
        if not compact and task["num"] in MERGED_PAGES:
            continue
        cells.append(
            render_task_map_cell(
                task,
                prefix,
                current_set,
                compact=compact,
                merge_merged=not compact,
            )
        )
    extra = " task-map--compact" if compact else ""
    if extra_class:
        extra += f" {extra_class}"
    return f'<div class="task-map{extra}" data-task-map>{"".join(cells)}</div>'


def render_map_panel(prefix: str = "tasks/") -> str:
    legend = "".join(
        f'<span class="legend-item"><span class="legend-dot legend-dot--{key}"></span>{esc(sec["short"])}</span>'
        for key, sec in TASK_SECTIONS.items()
    )
    return f'''
<aside class="map-panel reveal" aria-label="Карта заданий">
  <div class="map-head">
    <span>Карта заданий</span>
    <span class="map-progress" data-progress-count>0 / 27</span>
  </div>
  {task_map(prefix)}
  <p class="map-caption" id="map-caption">Наведите на номер, чтобы увидеть тему задания.</p>
  <p class="map-merge-note"><span>19–21</span> — одна общая страница: теория и способы решения</p>
  <div class="map-legend">{legend}</div>
  <a class="map-link" href="{prefix}index.html">Все задания <span aria-hidden="true">→</span></a>
</aside>'''


def render_task_card(task: dict, prefix: str = "tasks/") -> str:
    num = task["num"]
    section = TASK_SECTIONS[task["section"]]
    pts = task_points(num)
    classes = ["task-card", f"task-card--{task['section']}"]
    flag = ""
    if task.get("subtasks"):
        classes.append("task-card--merged")
        flag = '<span class="task-card-flag">19–21 · одна страница</span>'
    elif task.get("merged_into"):
        classes.append("task-card--merged-part")
        flag = f'<span class="task-card-flag">часть темы {task["merged_into"]}–21</span>'
    search = f'{num} {task["title"]} {task["subtitle"]} {task["summary"]} {section["label"]}'.lower()
    return f'''
<a class="{" ".join(classes)}" href="{task_href(num, prefix)}"
   data-task-card data-task="{num}" data-section="{task["section"]}" data-search="{esc(search)}">
  <span class="task-card-top">
    <span class="task-card-num">{num:02d}</span>
    <span class="task-card-points">{point_word(pts)}</span>
  </span>
  <span class="task-card-title">{esc(task["title"])}</span>
  {flag}
  <span class="task-card-summary">{esc(task["summary"])}</span>
  <span class="task-card-foot">{esc(section["short"])} · {esc(task["answer"])}</span>
</a>'''


def render_task_groups(prefix: str = "tasks/") -> str:
    groups = []
    for key, section in TASK_SECTIONS.items():
        cards = "".join(render_task_card(TASK_BY_NUM[num], prefix) for num in section["tasks"])
        merged_note = ""
        if any(num in MERGED_NUMS for num in section["tasks"]):
            merged_note = (
                f'<p class="task-group-note">'
                f'<a href="{task_href(19, prefix)}">Задания 19–21</a> объединены в одну тему: '
                f'общая теория и способы решения.</p>'
            )
        groups.append(f'''
<section class="task-group" id="section-{key}" data-task-group="{key}">
  <header class="task-group-head">
    <div class="task-group-marker task-group-marker--{key}" aria-hidden="true">{len(section["tasks"]):02d}</div>
    <div class="task-group-copy">
      <p class="eyebrow">{esc(section["label"])}</p>
      <h2>{esc(section["label"])}</h2>
      <p>{esc(section["description"])} {tasks_word(len(section["tasks"]))} · {point_word(section["points"])}.</p>
      {merged_note}
    </div>
  </header>
  <div class="task-cards task-cards--{key}">{cards}</div>
</section>''')
    return "".join(groups)


def render_changes(prefix: str = "tasks/") -> str:
    return f'''
<div class="changes changes--home">
  <div class="changes-copy">
    <p class="eyebrow">Что меняется в 2027</p>
    <h3>Структура прежняя, акценты другие</h3>
    <p>Количество заданий и максимальный первичный балл не изменились. ФИПИ перераспределил темы нескольких заданий и изменил форму записи ответа в задании 27.</p>
  </div>
  <dl class="change-list">
    <div><dt><a href="{task_href(10, prefix)}">Задание 10</a></dt><dd>маска подсети вместо поиска в текстовом процессоре</dd></div>
    <div><dt><a href="{task_href(13, prefix)}">Задание 13</a></dt><dd>анализ хода исполнения алгоритма вместо маски подсети</dd></div>
    <div><dt><a href="{task_href(23, prefix)}">Задание 23</a></dt><dd>алгоритмические задачи на графы</dd></div>
    <div><dt><a href="{task_href(27, prefix)}">Задание 27</a></dt><dd>один ответ из двух чисел вместо двух строк</dd></div>
  </dl>
</div>'''


def render_facts() -> str:
    return '''
<div class="facts" aria-label="Параметры экзамена">
  <div><strong>27</strong><span>заданий</span></div>
  <div><strong>29</strong><span>первичных баллов</span></div>
  <div><strong>235</strong><span>минут</span></div>
  <div><strong>4</strong><span>содержательных раздела</span></div>
</div>
<p class="facts-note">По проекту спецификации 2027 года: 11 заданий базового уровня, 11 повышенного и 5 высокого. Задания 1–25 — по 1 баллу, 26 и 27 — по 2 балла.</p>'''


def render_steps() -> str:
    return f'''
<section class="home-section" id="how">
  <header class="section-head section-head--home">
    <div class="section-num">02</div>
    <div class="section-copy">
      <p class="eyebrow">План · без лишнего</p>
      <h2>С чего начать</h2>
      <p class="section-lead">Три шага, которые связывают официальные материалы с разбором конкретных заданий.</p>
    </div>
  </header>
  <div class="steps-grid">
    <article class="step-card">
      <span class="step-num">01</span>
      <h3>Проверьте базу</h3>
      <p>Откройте демоверсию 2027 и решите 5–7 заданий подряд. Отметьте, что даётся легко, а где приходится угадывать.</p>
      <a class="text-link" href="documents.html#kim2027">Демоверсия 2027 <span aria-hidden="true">→</span></a>
    </article>
    <article class="step-card">
      <span class="step-num">02</span>
      <h3>Разберите слабые темы</h3>
      <p>Перейдите к карте заданий. На странице каждого задания — что проверяется, что повторить, как решать и типичные ошибки.</p>
      <a class="text-link" href="#task-map">Карта заданий <span aria-hidden="true">→</span></a>
    </article>
    <article class="step-card">
      <span class="step-num">03</span>
      <h3>Закрепите на вариантах</h3>
      <p>После теории решайте открытый вариант 2026 и задания из открытого банка ФИПИ. Возвращайтесь к слабым номерам.</p>
      <a class="text-link" href="documents.html#kim2026">Открытый вариант 2026 <span aria-hidden="true">→</span></a>
    </article>
  </div>
</section>'''


def render_materials() -> str:
    cards = [
        ("ФИПИ · 2027", "Демоверсия 2027", "27 заданий, ответы, критерии и файлы для компьютерной части.", "documents.html#kim2027"),
        ("ФИПИ · 2027", "Спецификация и кодификатор", "Структура работы, баллы, время и проверяемые элементы содержания.", "documents.html#kim2027"),
        ("ФИПИ · 2026", "Навигатор подготовки", "Рекомендации по самостоятельной подготовке и четыре тематических раздела.", "documents.html#method"),
        ("ФИПИ · 2026", "Методические рекомендации", "Разбор типичных ошибок участников ЕГЭ 2026 года.", "documents.html#method"),
        ("ФИПИ · 2026", "Открытый вариант 2026", "Реальный вариант с ответами и критериями — для тренировки.", "documents.html#kim2026"),
        ("Реестр", "Все официальные документы", "47 позиций: КИМ, нормативная база, методические материалы и архив.", "documents.html"),
    ]
    html_cards = "".join(
        f'''
<a class="material-card{' material-card--accent' if i == 5 else ''}" href="{href}">
  <span class="material-label">{esc(label)}</span>
  <span class="material-title">{esc(title)}</span>
  <span class="material-desc">{esc(desc)}</span>
  <span class="material-arrow" aria-hidden="true">↗</span>
</a>'''
        for i, (label, title, desc, href) in enumerate(cards)
    )
    return f'''
<section class="home-section" id="materials">
  <header class="section-head section-head--home">
    <div class="section-num">03</div>
    <div class="section-copy">
      <p class="eyebrow">Официальные материалы</p>
      <h2>Что открыть рядом с заданиями</h2>
      <p class="section-lead">Документы ФИПИ и Рособрнадзора, по которым составлялись страницы заданий. Все файлы лежат локально в папке «Исходники».</p>
    </div>
  </header>
  <div class="materials-grid">{html_cards}</div>
  <div class="documents-cta">
    <div>
      <p class="eyebrow">Отдельный раздел</p>
      <h3>Реестр официальных документов</h3>
      <p>Демоверсии, спецификации, кодификаторы, приказы, расписание, бланки и архив 2007–2025 — с поиском и ссылками на первоисточники.</p>
    </div>
    <a class="btn btn-primary" href="documents.html">Перейти в документы</a>
  </div>
</section>'''


def render_practice(task: dict, prefix: str = "tasks/") -> str:
    section = task["section"]
    nav_section = task.get("navigator", section)
    navigator = {
        "digital": "Навигатор. Цифровая грамотность.pdf",
        "theory": "Навигатор. Теоретические основы информатики.pdf",
        "algo": "Навигатор. Алгоритмы и программирование.pdf",
        "it": "Навигатор. Информационные технологии.pdf",
    }[nav_section]
    nav_path = url(f"Исходники/Методические материалы/{navigator}")
    demo_path = url("Исходники/inf_11_2027/ИНФ-11 ЕГЭ 2027 ДЕМО.pdf")
    method_path = url("Исходники/Методические материалы/Методические рекомендации для учителей. Информатика. 2026.pdf")
    return f'''
<div class="practice-grid">
  <a class="practice-link" href="https://ege.fipi.ru/bank/" target="_blank" rel="noopener noreferrer">
    <span class="practice-label">ФИПИ</span><span class="practice-title">Открытый банк заданий</span><span class="practice-arrow" aria-hidden="true">↗</span>
  </a>
  <a class="practice-link" href="{prefix}{nav_path}" target="_blank" rel="noopener">
    <span class="practice-label">Навигатор · 2026</span><span class="practice-title">{esc(TASK_SECTIONS[nav_section]["short"])}</span><span class="practice-arrow" aria-hidden="true">↗</span>
  </a>
  <a class="practice-link" href="{prefix}{demo_path}" target="_blank" rel="noopener">
    <span class="practice-label">Демоверсия</span><span class="practice-title">КИМ 2027</span><span class="practice-arrow" aria-hidden="true">↗</span>
  </a>
  <a class="practice-link" href="{prefix}{method_path}" target="_blank" rel="noopener">
    <span class="practice-label">Методика</span><span class="practice-title">Разбор ошибок 2026</span><span class="practice-arrow" aria-hidden="true">↗</span>
  </a>
</div>
<p class="practice-note">{esc(task.get("practice_note", "Навигатор и методические рекомендации опубликованы в 2026 году: номера заданий в них могут отличаться от нумерации 2027 года. Ориентируйтесь на тему."))}</p>'''


def render_related(task: dict, prefix: str = "tasks/") -> str:
    links = []
    for num in task.get("related", []):
        other = TASK_BY_NUM[num]
        links.append(f'<a class="related-link" href="{task_href(num, prefix)}">{num:02d} · {esc(other["title"])}</a>')
    if not links:
        return ""
    return f'''
<div class="related-links">
  <span class="related-label">Смотрите также</span>
  {''.join(links)}
</div>'''


def render_task_subtasks(task: dict) -> str:
    subtasks = task.get("subtasks")
    if not subtasks:
        return ""

    cards = []
    for spec in subtasks:
        cards.append(f'''
<article class="theory-card" id="subtask-{spec["num"]}">
  <p class="mini-label">Задание {spec["num"]}</p>
  <h3>{esc(spec["title"])}</h3>
  <p>{esc(spec["text"])}</p>
  <p class="method-answer"><span>Ответ</span>{esc(spec["answer"])}</p>
</article>''')

    return f'''
<section class="task-block" id="subtasks">
  <div class="block-head block-head--small">
    <p class="eyebrow">Одна игра — три задания</p>
    <h2>Что спрашивают в 19, 20 и 21</h2>
    <p class="block-lead">{esc(task.get("subtasks_lead", ""))}</p>
  </div>
  <div class="subtask-grid">{"".join(cards)}</div>
</section>'''


def render_task_theory(task: dict) -> str:
    theory = task.get("theory")
    if not theory:
        return ""

    checklist = "".join(f"<li>{esc(x)}</li>" for x in theory.get("checklist", []))
    blocks = []
    for block in theory.get("blocks", []):
        items = ""
        if block.get("items"):
            items = '<ul class="theory-list">' + "".join(
                f"<li>{esc(x)}</li>" for x in block["items"]
            ) + "</ul>"
        formulas = ""
        if block.get("formulas"):
            formulas = '<div class="formula-inline">' + "".join(
                f"<code>{esc(x)}</code>" for x in block["formulas"]
            ) + "</div>"
        blocks.append(f'''
<article class="theory-card">
  <h3>{esc(block["title"])}</h3>
  <p>{esc(block.get("text", ""))}</p>
  {items}
  {formulas}
</article>''')

    example = theory.get("example")
    example_html = ""
    if example:
        steps = "".join(f"<li>{esc(x)}</li>" for x in example.get("steps", []))
        parts = []
        if example.get("svg"):
            parts.append(f'<div class="graph-wrap">{example["svg"]}</div>')
        if example.get("table"):
            parts.append(f'<div class="table-wrap">{example["table"]}</div>')
        grid = ""
        if parts:
            grid_class = "theory-example-grid" if len(parts) > 1 else "theory-example-grid theory-example-grid--single"
            grid = f'<div class="{grid_class}">{"".join(parts)}</div>'
        example_html = f'''
<div class="theory-example">
  <div class="block-head block-head--small">
    <p class="eyebrow">Разбор примера</p>
    <h3>{esc(example["title"])}</h3>
    <p>{esc(example.get("text", ""))}</p>
  </div>
  {grid}
  <ol class="task-steps">{steps}</ol>
  <p class="example-answer"><span>Ответ</span>{esc(example.get("answer", ""))}</p>
</div>'''

    checklist_label = "Минимум для заданий 19–21" if task.get("subtasks") else f"Минимум для задания {task['num']}"
    return f'''
<section class="task-block task-block--theory" id="theory">
  <div class="block-head">
    <p class="eyebrow">Теория</p>
    <h2>Что нужно знать</h2>
    <p class="block-lead">{esc(theory.get("lead", ""))}</p>
  </div>
  <div class="theory-checklist">
    <p class="mini-label">{checklist_label}</p>
    <ul class="check-list">{checklist}</ul>
  </div>
  <div class="theory-grid">{"".join(blocks)}</div>
  {example_html}
</section>'''


def render_task_methods(task: dict) -> str:
    methods = task.get("methods")
    if not methods:
        return ""

    cards = []
    for method in methods:
        steps = ""
        if method.get("steps"):
            steps = '<ol class="task-steps">' + "".join(
                f"<li>{esc(x)}</li>" for x in method["steps"]
            ) + "</ol>"
        items = ""
        if method.get("items"):
            items = '<ul class="task-list">' + "".join(
                f"<li>{esc(x)}</li>" for x in method["items"]
            ) + "</ul>"

        example_html = ""
        example = method.get("example")
        if example:
            code = ""
            if example.get("code"):
                code = f'<pre class="code-block"><code>{esc(example["code"])}</code></pre>'
            example_html = f'''
<div class="method-example">
  <p class="mini-label">Пример</p>
  <p>{esc(example.get("text", ""))}</p>
  {code}
  <p class="method-answer"><span>Ответ</span>{esc(example.get("answer", ""))}</p>
</div>'''

        source = ""
        if method.get("source"):
            source = f'<p class="method-source">{esc(method["source"])}</p>'

        cards.append(f'''
<article class="method-card">
  <header class="method-head">
    <span class="method-num">{esc(method.get("num", ""))}</span>
    <div>
      <p class="eyebrow">{esc(method.get("tag", ""))}</p>
      <h3>{esc(method["title"])}</h3>
    </div>
  </header>
  <p class="method-when"><strong>Когда использовать:</strong> {esc(method.get("when", ""))}</p>
  {steps}
  {items}
  {example_html}
  {source}
</article>''')

    cheatsheet = ""
    rows = task.get("cheatsheet") or []
    if rows:
        body = "".join(
            f"<tr><td>{esc(condition)}</td><td>{esc(method)}</td></tr>"
            for condition, method in rows
        )
        cheatsheet = f'''
<div class="cheatsheet">
  <p class="mini-label">Шпаргалка: формулировка → метод</p>
  <div class="cheatsheet-wrap">
    <table class="cheatsheet-table">
      <thead><tr><th>В условии</th><th>Что делать</th></tr></thead>
      <tbody>{body}</tbody>
    </table>
  </div>
</div>'''

    videos = task.get("videos") or []
    video_html = ""
    if videos:
        links = ""
        for label, task_id, time, url in sorted(videos, key=video_sort_key):
            host = video_host(url)
            meta = " · ".join(esc(part) for part in (task_id, time) if part)
            host_icon = ""
            if host:
                name = VIDEO_HOST_LABELS[host]
                host_icon = (
                    f'<span class="video-host" title="{esc(name)}">'
                    f'<span class="video-host-icon">{VIDEO_HOST_ICONS[host]}</span>'
                    f'<span class="video-host-name">{esc(name)}</span></span>'
                )
            links += (
                f'<a class="video-link" href="{esc(url)}" target="_blank" rel="noopener noreferrer">'
                f'<span class="video-label">{esc(label)}</span>'
                f'<span class="video-meta">{meta}</span>'
                f'{host_icon}</a>'
            )
        video_html = f'''
<div class="video-block">
  <p class="mini-label">Видеоразборы по теме</p>
  <div class="video-list">{links}</div>
  <p class="video-note">Ссылки и таймкоды взяты из базы Kompege.</p>
</div>'''

    source_note = ""
    if task.get("source_note"):
        source_note = f'<p class="method-source-note">{esc(task["source_note"])}</p>'

    methods_label = "заданий 19–21" if task.get("subtasks") else f"задания {task['num']}"
    return f'''
<section class="task-block task-block--methods" id="methods">
  <div class="block-head">
    <p class="eyebrow">Способы решения</p>
    <h2>Выберите метод под формулировку</h2>
    <p class="block-lead">Методы собраны по решениям {methods_label} из базы Kompege. Начните с того, что именно нужно найти в условии.</p>
  </div>
  <div class="methods-list">{"".join(cards)}</div>
  {cheatsheet}
  {video_html}
  {source_note}
</section>'''


def render_task_toc(task: dict) -> str:
    if not task.get("theory") and not task.get("methods"):
        return ""
    subtasks_link = '<a href="#subtasks">19–21</a>' if task.get("subtasks") else ""
    return f'''
<nav class="task-toc" aria-label="На странице задания">
  <span class="task-toc-label">На странице</span>
  {subtasks_link}
  <a href="#theory">Теория</a>
  <a href="#methods">Способы решения</a>
  <a href="#mistakes">Ошибки</a>
  <a href="#practice">Практика</a>
</nav>'''


def render_task_page(num: int) -> str:
    task = TASK_BY_NUM[num]
    section = TASK_SECTIONS[task["section"]]
    subtask_specs = task.get("subtasks")
    is_merged = bool(subtask_specs)
    subtask_nums = [spec["num"] for spec in subtask_specs] if is_merged else []
    pts = sum(task_points(n) for n in subtask_nums) if is_merged else task_points(num)

    prev_num = next((n for n in range(num - 1, 0, -1) if n not in MERGED_PAGES), None)
    next_num = next((n for n in range(num + 1, 28) if n not in MERGED_PAGES), None)
    prev_task = TASK_BY_NUM[prev_num] if prev_num else None
    next_task = TASK_BY_NUM[next_num] if next_num else None

    page_label = "Задания 19–21" if is_merged else f"Задание {num}"
    page_number = "19–21" if is_merged else f"{num:02d}"
    current_cells = subtask_nums if is_merged else num
    progress_toggle = ",".join(str(n) for n in subtask_nums) if is_merged else str(num)

    changed = ""
    if task.get("changed"):
        changed = f'''
<div class="callout callout--change">
  <span class="callout-label">2027</span>
  <p>{esc(task["changed"])}</p>
</div>'''
    merged_note = ""
    if is_merged:
        merged_note = '''
<div class="callout">
  <span class="callout-label">19–21</span>
  <p>Страницы 19, 20 и 21 объединены: это одна игра с тремя вопросами. Ниже — теория, способы решения и форматы ответа для всех трёх номеров.</p>
</div>'''
    note = ""
    if task.get("note"):
        note = f'<p class="task-note">{esc(task["note"])}</p>'

    formulas = ""
    if task.get("formulas"):
        items = "".join(f"<li><code>{esc(x)}</code></li>" for x in task["formulas"])
        formulas = f'''
<section class="task-block">
  <h2>Ключевые формулы</h2>
  <ul class="formula-list">{items}</ul>
</section>'''

    what = "".join(f"<li>{esc(x)}</li>" for x in task["what"])
    repeat = "".join(f"<li>{esc(x)}</li>" for x in task["repeat"])
    steps = "".join(f"<li>{esc(x)}</li>" for x in task["steps"])
    mistakes = "".join(f"<li>{esc(x)}</li>" for x in task["mistakes"])

    theory_html = render_task_theory(task)
    methods_html = render_task_methods(task)
    subtasks_html = render_task_subtasks(task)
    toc_html = render_task_toc(task)

    knowledge_html = theory_html or f'''
    <section class="task-block">
      <h2>Что нужно уметь</h2>
      <ul class="task-list">{what}</ul>
    </section>
    <section class="task-block">
      <h2>Что повторить</h2>
      <ul class="task-list task-list--columns">{repeat}</ul>
    </section>'''

    solution_html = methods_html or f'''
    <section class="task-block">
      <h2>Как решать</h2>
      <ol class="task-steps">{steps}</ol>
    </section>'''

    prev_html = ""
    if prev_task:
        prev_html = f'<a class="prev-next-link" href="{task_href(prev_task["num"], "")}"><span>← Предыдущее</span><strong>{esc(task_label(prev_task["num"]))}</strong></a>'
    next_html = ""
    if next_task:
        next_html = f'<a class="prev-next-link prev-next-link--next" href="{task_href(next_task["num"], "")}"><span>Следующее →</span><strong>{esc(task_label(next_task["num"]))}</strong></a>'

    extra_badge = ""
    if is_merged:
        extra_badge = '<span class="badge badge-project">19 · 20 · 21</span>'
    elif task.get("changed"):
        extra_badge = '<span class="badge badge-project">новая тема 2027</span>'
    number_class = "task-number task-number--range" if is_merged else "task-number"

    content = f'''
{breadcrumbs("../", [("../index.html", "Главная"), ("index.html", "Задания"), (None, page_label)])}

<section class="task-hero">
  <div class="{number_class}" aria-hidden="true">{page_number}</div>
  <div class="task-hero-copy">
    <p class="eyebrow">{esc(section["label"])} · {("3 задания · " if is_merged else "")}{point_word(pts)}</p>
    <h1>{esc(task["title"])}</h1>
    <p class="task-subtitle">{esc(task["subtitle"])}</p>
    <p class="lead">{esc(task["summary"])}</p>
    <div class="task-badges">
      <span class="badge badge-section badge-section--{task["section"]}">{esc(section["short"])}</span>
      <span class="badge badge-answer">{esc(task["answer"])}</span>
      {extra_badge}
    </div>
  </div>
</section>

{toc_html}

<div class="task-layout">
  <div class="task-main">
    {changed}
    {merged_note}
    <section class="task-block">
      <h2>Что проверяет</h2>
      <p class="task-checked">{esc(task["checked"])}</p>
      <p class="task-source">Основание: проект спецификации и кодификатора КИМ 2027. <a href="../documents.html#kim2027">Открыть документы <span aria-hidden="true">↗</span></a></p>
    </section>
    {subtasks_html}
    {knowledge_html}
    {solution_html}
    <section class="task-block" id="mistakes">
      <h2>Типичные ошибки</h2>
      <ul class="task-list task-list--mistakes">{mistakes}</ul>
    </section>
    {formulas}
    {note}
    <section class="task-block" id="practice">
      <h2>Практика</h2>
      {render_practice(task, "../")}
    </section>
    {render_related(task, "")}
    <nav class="prev-next" aria-label="Соседние задания">
      {prev_html}
      {next_html}
    </nav>
  </div>

  <aside class="task-aside">
    <div class="aside-card">
      <div class="aside-head">
        <span>Карта заданий</span>
        <span class="map-progress" data-progress-count>0 / 27</span>
      </div>
      {task_map("", current=current_cells, compact=True)}
      <a class="aside-link" href="index.html">Все задания <span aria-hidden="true">→</span></a>
    </div>
    <div class="aside-card aside-card--progress">
      <p class="aside-label">Прогресс</p>
      <button class="btn btn-primary progress-toggle" type="button" data-progress-toggle="{progress_toggle}" aria-pressed="false">Отметить как изученное</button>
      <p class="progress-note" data-progress-text>0 из 27 изучено</p>
      <div class="progress-line" aria-hidden="true"><span data-progress-bar></span></div>
    </div>
    <div class="aside-card">
      <p class="aside-label">Быстрые ссылки</p>
      <a class="aside-link" href="../documents.html#kim2027">Демоверсия 2027 <span aria-hidden="true">↗</span></a>
      <a class="aside-link" href="../documents.html#method">Навигатор и методика <span aria-hidden="true">↗</span></a>
      <a class="aside-link" href="../documents.html">Все документы <span aria-hidden="true">↗</span></a>
    </div>
  </aside>
</div>'''

    title = f'{page_label} ЕГЭ по информатике — {task["title"]}'
    description = f'{task["summary"]} Теория, способы решения и типичные ошибки. ЕГЭ-2027, информатика.'
    return page_shell(title, description, "../", "tasks", content, meta=f'<span>{page_label} из 27</span><span>{esc(section["short"])}</span>')


def render_credit_banner() -> str:
    return '''
<section class="credit-banner" id="sources" aria-labelledby="credit-title">
  <div class="credit-banner-copy">
    <p class="eyebrow">Источники материалов</p>
    <h2 id="credit-title">Сайт создан<br>на материалах<br><em>КомпЕГЭ</em></h2>
    <p class="credit-lead">База заданий, решения, видеоразборы и методические подходы взяты с сайта <a href="https://kompege.ru/" target="_blank" rel="noopener noreferrer">КомпЕГЭ</a> и переработаны в учебные разборы. Ссылки на первоисточники сохранены на страницах заданий.</p>
    <p class="credit-fine">Проект не является официальным ресурсом ФИПИ, Рособрнадзора или КомпЕГЭ. Права на исходные материалы принадлежат их авторам.</p>
  </div>
  <nav class="credit-links" aria-label="Ссылки на первоисточники">
    <a class="credit-link" href="https://kompege.ru/" target="_blank" rel="noopener noreferrer">
      <span class="credit-link-index" aria-hidden="true">01</span>
      <span class="credit-link-body">
        <span class="credit-link-label">Сайт</span>
        <strong>КомпЕГЭ</strong>
        <span class="credit-link-desc">База заданий, решений и видеоразборов</span>
      </span>
      <span class="credit-link-arrow" aria-hidden="true">↗</span>
    </a>
    <a class="credit-link" href="https://vk.ru/ege_info_open" target="_blank" rel="noopener noreferrer">
      <span class="credit-link-index" aria-hidden="true">02</span>
      <span class="credit-link-body">
        <span class="credit-link-label">ВКонтакте</span>
        <strong>Открытый курс</strong>
        <span class="credit-link-desc">Группа открытого курса КомпЕГЭ в ВК<br>ЕГЭ Информатика 2027 | Открытый курс</span>
      </span>
      <span class="credit-link-arrow" aria-hidden="true">↗</span>
    </a>
    <a class="credit-link" href="https://kompege.ru/course" target="_blank" rel="noopener noreferrer">
      <span class="credit-link-index" aria-hidden="true">03</span>
      <span class="credit-link-body">
        <span class="credit-link-label">Сайт</span>
        <strong>Открытый курс</strong>
        <span class="credit-link-desc">Бесплатные материалы открытого курса КомпЕГЭ</span>
      </span>
      <span class="credit-link-arrow" aria-hidden="true">↗</span>
    </a>
    <a class="credit-link" href="https://promo.kompege.ru/" target="_blank" rel="noopener noreferrer">
      <span class="credit-link-index" aria-hidden="true">04</span>
      <span class="credit-link-body">
        <span class="credit-link-label">Годовой курс</span>
        <strong>Записаться на годовой курс</strong>
        <span class="credit-link-desc">Страница курса и запись на 2026/27</span>
      </span>
      <span class="credit-link-arrow" aria-hidden="true">↗</span>
    </a>
  </nav>
</section>
'''


def build_home() -> None:
    task_groups = render_task_groups("tasks/")
    content = f'''
{render_credit_banner()}
<section class="home-hero">
  <div class="home-hero-copy reveal">
    <p class="eyebrow">ЕГЭ · Информатика · 2027</p>
    <h1>27 заданий.<br>Понятный порядок<br>подготовки.</h1>
    <p class="lead">Разбор каждого задания, ключевые темы, типичные ошибки и официальные документы. Начните с карты экзамена или сразу с нужного номера.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="#task-map">Карта заданий</a>
      <a class="btn btn-ghost" href="tasks/index.html">Все задания</a>
      <a class="btn btn-ghost" href="documents.html">Документы</a>
    </div>
    <div class="status-note">
      <span class="status-dot" aria-hidden="true"></span>
      <p><strong>Статус на {UPDATED}.</strong> Документы КИМ-2027 — проекты ФИПИ от 28.08.2026. Расписание 2027 — проект от 26.10.2026. Минимальные баллы 2027/28 — проект от 23.10.2026.</p>
    </div>
  </div>
  {render_map_panel("tasks/")}
</section>

<div class="facts-wrap">
  {render_facts()}
</div>

<section class="home-section" id="task-map">
  <header class="section-head section-head--home">
    <div class="section-num">01</div>
    <div class="section-copy">
      <p class="eyebrow">Карта экзамена</p>
      <h2>Все задания по разделам</h2>
      <p class="section-lead">27 заданий сгруппированы по четырём содержательным разделам спецификации. У каждого — разбор с теорией, порядком решения и ошибками.</p>
    </div>
  </header>
  {task_groups}
</section>

{render_changes("tasks/")}

{render_steps()}

{render_materials()}

<section class="closing-band">
  <div>
    <p class="eyebrow">Начать можно с любого номера</p>
    <h2>Не нужно проходить всё подряд</h2>
    <p>Откройте карту заданий, выберите тему, которая западает, и разберите её. Прогресс сохраняется в браузере — изученные задания отмечаются на карте.</p>
  </div>
  <a class="btn btn-primary" href="tasks/index.html">Открыть все задания</a>
</section>'''
    page = page_shell(
        "ЕГЭ по информатике 2027 — подготовка по заданиям",
        "Разбор всех 27 заданий ЕГЭ по информатике 2027: что проверяет каждое задание, что повторить, как решать, типичные ошибки и официальные документы ФИПИ.",
        "",
        "home",
        content,
    )
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    print(f"index.html: {len(page):,} bytes")


def build_tasks_index() -> None:
    task_groups = render_task_groups("")
    filters = "".join(
        f'<button class="chip" data-task-filter="{key}" aria-pressed="false">{esc(sec["label"])} · {len(sec["tasks"])}</button>'
        for key, sec in TASK_SECTIONS.items()
    )
    map_side = "".join(
        f'<li><span class="legend-dot legend-dot--{key}"></span>'
        f'<span class="map-side-label">{esc(sec["short"])}</span>'
        f'<em>{tasks_word(len(sec["tasks"]))} · {point_word(sec["points"])}</em></li>'
        for key, sec in TASK_SECTIONS.items()
    )
    content = f'''
{breadcrumbs("", [("../index.html", "Главная"), (None, "Задания")])}

<section class="page-hero">
  <p class="eyebrow">27 заданий · 29 первичных баллов · 235 минут</p>
  <h1>Все задания ЕГЭ по информатике</h1>
  <p class="lead">Полный список заданий 2027 года с краткими темами. Открывайте нужный номер, чтобы увидеть, что проверяется, что повторить и как решать.</p>
  <div class="progress-panel">
    <div class="progress-panel-head">
      <span class="progress-label">Ваш прогресс</span>
      <span class="map-progress" data-progress-count>0 / 27</span>
    </div>
    <div class="progress-line" aria-hidden="true"><span data-progress-bar></span></div>
    <div class="progress-panel-foot">
      <p class="progress-note" data-progress-text>0 из 27 изучено</p>
      <button class="text-link" type="button" data-progress-reset>Сбросить прогресс</button>
    </div>
  </div>
</section>

<section class="task-index-section">
  <div class="task-index-head">
    <div>
      <p class="eyebrow">Фильтр по разделу</p>
      <h2>Выберите блок</h2>
    </div>
    <p class="task-index-count" data-task-count>27 заданий</p>
  </div>
  <div class="chips chips--tasks" role="group" aria-label="Фильтр заданий по разделу">
    <button class="chip is-active" data-task-filter="all" aria-pressed="true">Все · 27</button>
    {filters}
  </div>
  <div class="task-map-row">
    {task_map("", extra_class="task-map--index")}
    <aside class="task-map-side" aria-label="Разделы карты">
      <p class="eyebrow">Цвета на карте</p>
      <ul>{map_side}</ul>
      <p class="map-side-note">Зелёная точка появляется после того, как вы отметите задание изученным. Прогресс сохраняется в браузере.</p>
    </aside>
  </div>
  {task_groups}
</section>

<section class="closing-band closing-band--light">
  <div>
    <p class="eyebrow">Официальные документы</p>
    <h2>Демоверсия, спецификация и кодификатор</h2>
    <p>Все документы ФИПИ, по которым составлены эти страницы, — в отдельном разделе с поиском и первоисточниками.</p>
  </div>
  <a class="btn btn-ghost" href="../documents.html">Перейти в документы</a>
</section>'''
    page = page_shell(
        "Все задания ЕГЭ по информатике 2027 — список и темы",
        "Все 27 заданий ЕГЭ по информатике 2027: темы, разделы, баллы и ссылки на разбор каждого задания.",
        "../",
        "tasks",
        content,
    )
    (ROOT / "tasks").mkdir(exist_ok=True)
    (ROOT / "tasks" / "index.html").write_text(page, encoding="utf-8")
    print(f"tasks/index.html: {len(page):,} bytes")


def render_redirect_page(num: int) -> str:
    target, anchor = MERGED_PAGES[num]
    url = f"{target:02d}.html#{anchor}"
    task = TASK_BY_NUM[num]
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Задание {num} — в составе заданий 19–21</title>
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={url}">
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/site.css">
</head>
<body>
<main id="main" style="padding:40px 24px">
  <p class="eyebrow">Страница объединена</p>
  <h1 style="font-family:var(--serif);font-size:32px;margin:8px 0 12px">Задание {num} входит в тему 19–21</h1>
  <p>Теория и способы решения для заданий 19, 20 и 21 собраны на одной странице.</p>
  <p><a href="{url}">Перейти к заданиям 19–21 · {esc(task["title"])}</a></p>
</main>
</body>
</html>'''


def build_task_pages() -> None:
    (ROOT / "tasks").mkdir(exist_ok=True)
    for task in TASKS:
        num = task["num"]
        page = render_redirect_page(num) if num in MERGED_PAGES else render_task_page(num)
        path = ROOT / "tasks" / f"{num:02d}.html"
        path.write_text(page, encoding="utf-8")
    print(f"tasks/01.html … tasks/27.html (19–21 объединены)")


def build_manifest() -> int:
    for section in SECTIONS:
        for doc in [x for x in DOCS if x["section"] == section["id"]]:
            if not (ROOT / doc["path"]).exists():
                raise FileNotFoundError(doc["path"])

    total_files = len(DOCS) + len(ARCHIVE)
    manifest = {
        "generated": date.today().isoformat(),
        "subject": "Информатика",
        "exam": "ЕГЭ",
        "note": "Проекты КИМ 2027 и проекты приказов на 2027 год; утверждённые версии на 03.11.2026 не опубликованы.",
        "documents": [
            {
                "code": x["code"],
                "title": x["title"],
                "path": x["path"],
                "source": x["source"],
                "pages": x["pages"],
                "size": doc_size(x),
                "sha256": sha256(ROOT / x["path"]),
            }
            for x in DOCS
        ]
        + [
            {
                "code": f"АРХИВ·{year}",
                "title": f"Архив демоверсий {year}",
                "path": f"Исходники/Архив демоверсий/inf_11_{year}.zip",
                "source": source,
                "pages": None,
                "size": (ROOT / f"Исходники/Архив демоверсий/inf_11_{year}.zip").stat().st_size,
                "sha256": sha256(ROOT / f"Исходники/Архив демоверсий/inf_11_{year}.zip"),
            }
            for year, source, _ in ARCHIVE
        ],
    }
    (SRC / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return total_files


def build_documents() -> None:
    total_files = build_manifest()

    sections_html = "".join(render_section(s) for s in SECTIONS)
    nav_html = "".join(
        f'<a href="#{s["id"]}"><span class="nav-num">{s["num"]}</span>{esc(s["nav"])}</a>'
        for s in SECTIONS
    )

    content = f'''
<section class="hero hero--documents" aria-labelledby="hero-title">
  <div class="hero-copy reveal">
    {breadcrumbs("", [("index.html", "Главная"), (None, "Документы")])}
    <p class="eyebrow">Раздел сайта · официальные документы</p>
    <h1 id="hero-title">Документы<br>для ЕГЭ по<br>информатике</h1>
    <p class="hero-year"><strong>2027</strong> проекты КИМ <span>·</span> <strong>2026</strong> действующая база</p>
    <p class="lead">Демоверсии, спецификации, кодификаторы, методические рекомендации и нормативные акты. Всё скачано с официальных сайтов, лежит в папке «Исходники» и открывается с этой страницы.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="#kim2027">Смотреть 2027</a>
      <a class="btn btn-ghost" href="#archive">Архив демоверсий</a>
      <a class="btn btn-ghost" href="index.html">← К заданиям</a>
    </div>
    <div class="status-note">
      <span class="status-dot" aria-hidden="true"></span>
      <p><strong>Статус на {UPDATED}.</strong> КИМ 2027 — проекты ФИПИ от 28.08.2026. Расписание 2027 — проект от 26.10.2026. Минимальные баллы 2027/28 — проект от 23.10.2026.</p>
    </div>
  </div>

  <aside class="cover reveal" aria-label="Параметры КИМ ЕГЭ 2027">
    <div class="cover-top">
      <span>КИМ ЕГЭ · Информатика</span>
      <span>11 класс</span>
    </div>
    <div class="cover-number">27<span>заданий в варианте</span></div>
    <dl class="cover-stats">
      <div><dt>Первичных баллов</dt><dd>29</dd></div>
      <div><dt>Время экзамена</dt><dd>235 <small>мин</small></dd></div>
      <div><dt>Заданий с ПО</dt><dd>11</dd></div>
      <div><dt>Минимум для вузов*</dt><dd>46</dd></div>
    </dl>
    <div class="cover-foot">
      <div class="barcode" aria-hidden="true"></div>
      <span class="cover-caption">ПРОЕКТ · 28.08.2026</span>
    </div>
    <div class="stamp" aria-hidden="true"><span>ПРОЕКТ</span>2027</div>
    <p class="cover-footnote">* проект приказа Минобрнауки на 2027/28; не минимальный балл для аттестата.</p>
  </aside>
</section>

<div class="index-strip" aria-label="Состав реестра">
  <div><strong>{total_files}</strong><span>позиций в реестре</span></div>
  <div><strong>{len(ARCHIVE)}</strong><span>архивных лет ФИПИ</span></div>
  <div><strong>2</strong><span>проекта приказов 2027</span></div>
  <div><strong>100%</strong><span>локальные копии</span></div>
</div>

<div class="workspace" id="registry">
  <aside class="rail">
    <p class="rail-title">Реестр</p>
    <nav class="rail-nav" aria-label="Разделы реестра">{nav_html}<a href="#sources"><span class="nav-num">07</span>Источники</a></nav>
    <div class="rail-note">
      <p>Все файлы — в папке <code>Исходники</code>. У каждой позиции указан первоисточник.</p>
      <a href="{url("Исходники/manifest.json")}">Манифест файлов <span aria-hidden="true">↗</span></a>
    </div>
  </aside>

  <div class="registry-body">
    <div class="toolbar" role="search">
      <label class="search-label" for="search">Поиск по документам</label>
      <div class="search-row">
        <input id="search" type="search" placeholder="Кодификатор, расписание, 46" autocomplete="off">
        <button class="search-clear" id="search-clear" type="button" aria-label="Очистить поиск" hidden>×</button>
        <span class="search-hint" aria-hidden="true">/</span>
      </div>
      <div class="chips" role="group" aria-label="Фильтр документов">
        <button class="chip is-active" data-filter="all" aria-pressed="true">Все</button>
        <button class="chip" data-filter="2027" aria-pressed="false">2027</button>
        <button class="chip" data-filter="2026" aria-pressed="false">2026</button>
        <button class="chip" data-filter="kim" aria-pressed="false">КИМ</button>
        <button class="chip" data-filter="method" aria-pressed="false">Методика</button>
        <button class="chip" data-filter="norm" aria-pressed="false">Нормативные</button>
        <button class="chip" data-filter="archive" aria-pressed="false">Архив</button>
      </div>
      <p class="result-count" id="result-count" aria-live="polite"></p>
    </div>

    {sections_html}

    <div class="empty-state" id="empty-state" hidden>
      <p class="eyebrow">Ничего не найдено</p>
      <h2>Попробуйте другой запрос</h2>
      <p>Поиск идёт по названию, описанию, году и коду документа. Например: «демо», «2027», «бланки».</p>
      <button class="btn btn-ghost" id="reset-search" type="button">Сбросить фильтры</button>
    </div>

    {render_sources()}
  </div>
</div>

<dialog class="viewer" id="viewer" aria-labelledby="viewer-title">
  <div class="viewer-head">
    <div>
      <p class="eyebrow" id="viewer-code">Документ</p>
      <h2 id="viewer-title">Просмотр</h2>
    </div>
    <button class="viewer-close" id="viewer-close" type="button" aria-label="Закрыть просмотр">×</button>
  </div>
  <div class="viewer-body">
    <iframe id="viewer-frame" title="Просмотр документа" loading="lazy"></iframe>
    <div class="viewer-note" id="viewer-note" hidden></div>
  </div>
  <div class="viewer-foot">
    <a id="viewer-source" href="#" target="_blank" rel="noopener noreferrer">Первоисточник <span aria-hidden="true">↗</span></a>
    <a id="viewer-newtab" href="#" target="_blank" rel="noopener">Открыть PDF в новой вкладке</a>
    <a id="viewer-download" class="btn btn-primary" href="#" download>Скачать</a>
  </div>
</dialog>'''

    page = page_shell(
        "Документы ЕГЭ по информатике 2027 — ФИПИ, Рособрнадзор",
        "Реестр официальных документов ЕГЭ по информатике: демоверсия, спецификация, кодификатор, методические и нормативные материалы 2027 и 2026 годов.",
        "",
        "documents",
        content,
    )
    (ROOT / "documents.html").write_text(page, encoding="utf-8")
    print(f"documents.html: {len(page):,} bytes; documents: {total_files}")


def build() -> None:
    build_documents()
    build_home()
    build_tasks_index()
    build_task_pages()
    print("site built")


if __name__ == "__main__":
    build()
