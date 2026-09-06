"""Presentation boundary for the local research explorer."""

from __future__ import annotations

import math
from pathlib import Path
import tomllib
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from . import ephemeris
from .errors import EphemerisError, ScenarioValidationError, TransferSearchError
from .explorer import SCIENCE_LOCK, sample_transfer
from .models import ImpulsiveTransferCandidate
from .scenario import scenario_from_mapping
from .transfer import IGNORED_SCENARIO_FIELDS, search_impulsive_transfers


ROOT = Path(__file__).resolve().parents[2]
LABELS = {
    "departure_start_utc": "Начало окна старта (UTC, …Z)",
    "departure_end_utc": "Конец окна старта (UTC, …Z)",
    "time_of_flight_min_days": "Минимальный перелёт, суток",
    "time_of_flight_max_days": "Максимальный перелёт, суток",
    "initial_mass_kg": "Начальная масса, кг",
    "dry_mass_kg": "Сухая масса, кг",
    "isp_s": "Удельный импульс, с",
    "max_thrust_n": "Тяга, Н (M2 не учитывает)",
    "srp_area_m2": "Площадь, м² (M2 не учитывает)",
    "reflectivity_coefficient": "Коэффициент отражения (M2 не учитывает)",
    "maneuver_magnitude_sigma_fraction": "Ошибка импульса, доля (M2 не учитывает)",
    "maneuver_pointing_sigma_deg": "Ошибка направления, ° (M2 не учитывает)",
    "central_body": "Центральное тело",
    "altitude_km": "Высота орбиты, км",
    "eccentricity": "Эксцентриситет",
    "inclination_deg": "Наклонение, ° (M2 не учитывает)",
    "raan_deg": "Долгота восходящего узла, ° (M2 не учитывает)",
    "argument_of_periapsis_deg": "Аргумент перицентра, ° (M2 не учитывает)",
    "true_anomaly_deg": "Истинная аномалия, ° (M2 не учитывает)",
    "periapsis_altitude_km": "Высота перицентра, км",
    "apoapsis_altitude_km": "Высота апоцентра, км",
    "stations": "Наземные станции",
    "cadence_hours": "Интервал измерений, ч",
    "range_sigma_m": "Ошибка дальности, м",
    "range_rate_sigma_m_s": "Ошибка скорости, м/с",
    "angular_sigma_arcsec": "Угловая ошибка, угл. с",
    "min_elevation_deg": "Минимальный угол места, °",
    "runtime_seconds": "Лимит расчёта, с",
    "random_seed": "Seed (M2 не учитывает)",
    "max_candidates": "Максимум вариантов",
}


def _invalidate() -> None:
    for name in ("result", "sampled", "sampled_id"):
        st.session_state.pop(name, None)


def _load_example() -> None:
    _invalidate()
    for key in list(st.session_state):
        if key.startswith("field:"):
            del st.session_state[key]
    st.session_state["inputs"] = tomllib.loads(
        (ROOT / "examples/reference_mission.toml").read_text(encoding="utf-8")
    )


def _input_fields(raw: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    titles = {"search": "Даты перелёта", "spacecraft": "Аппарат",
              "departure_orbit": "Орбита Луны", "target_orbit": "Орбита Марса",
              "tracking": "Измерения (не используются)", "limits": "Лимиты поиска"}
    for section in ("search", "spacecraft", "departure_orbit", "target_orbit", "tracking", "limits"):
        values[section] = {}
        with st.expander(titles[section], expanded=section in ("search", "spacecraft")):
            for name, value in raw[section].items():
                key = f"field:{section}.{name}"
                label = LABELS.get(name, name)
                if isinstance(value, (int, float)):
                    edited = st.number_input(
                        label, value=value, key=key, on_change=_invalidate,
                        format="%d" if isinstance(value, int) else "%.6g",
                    )
                else:
                    text = ", ".join(value) if isinstance(value, list) else value
                    edited = st.text_input(label, value=text, key=key, on_change=_invalidate)
                    if isinstance(value, list):
                        edited = [part.strip() for part in edited.split(",")]
                values[section][name] = edited
    return values


def _render_trajectory(candidate: ImpulsiveTransferCandidate) -> None:
    if st.session_state.get("sampled_id") != candidate.candidate_id:
        st.session_state.pop("sampled", None)
        with SCIENCE_LOCK:
            states = sample_transfer(candidate)
            context = {
                body: tuple(ephemeris._query_body_state_tdb(body, s.epoch_tdb_s) for s in states)
                for body in ("Sun", "Earth", "Mars")
            }
        st.session_state["sampled"] = (states, context)
        st.session_state["sampled_id"] = candidate.candidate_id
    states, context = st.session_state["sampled"]
    index = st.slider("Момент перелёта", 0, len(states) - 1, 0)
    scale = 1e9  # m -> million km, display boundary only.
    figure = go.Figure()
    for name, track, color in (
        ("Аппарат", states, "#36d6bc"),
        ("Земля", context["Earth"], "#568bff"),
        ("Марс", context["Mars"], "#ff9266"),
    ):
        x = [(s.position_m[0] - sun.position_m[0]) / scale for s, sun in zip(track, context["Sun"])]
        y = [(s.position_m[1] - sun.position_m[1]) / scale for s, sun in zip(track, context["Sun"])]
        figure.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name, line={"color": color}))
        figure.add_trace(go.Scatter(x=[x[index]], y=[y[index]], mode="markers", showlegend=False,
                                   marker={"color": color, "size": 12}))
        if name == "Аппарат":
            figure.add_trace(go.Scatter(x=[x[0], x[-1]], y=[y[0], y[-1]], mode="markers+text",
                                       text=["Старт: Луна", "Прибытие: Марс"], showlegend=False))
    figure.add_trace(go.Scatter(x=[0], y=[0], mode="markers", name="Солнце",
                               marker={"color": "#ffd36d", "size": 17}))
    figure.update_layout(height=540, xaxis_title="X, млн км", yaxis_title="Y, млн км",
                         yaxis={"scaleanchor": "x", "scaleratio": 1}, margin={"l": 10, "r": 10, "t": 20, "b": 10})
    st.plotly_chart(figure, use_container_width=True)
    current = states[index]
    speed = math.dist(current.velocity_m_s, context["Sun"][index].velocity_m_s)
    st.caption("Проекция XY осей J2000 относительно Солнца; это не плоскость эклиптики. Размеры тел условные.")
    st.write(f"UTC: {current.epoch_utc} · Скорость относительно Солнца: {speed / 1000:.3f} км/с")
    with st.expander("Точное состояние — SI / SSB / J2000"):
        st.json({"epoch_tdb_s": current.epoch_tdb_s, "time_scale": "TDB seconds since J2000",
                 "origin": current.origin, "orientation": current.orientation,
                 "position_m": current.position_m, "velocity_m_s": current.velocity_m_s})


def main() -> None:
    st.set_page_config(page_title="Ариадна · Луна → Марс", page_icon="🛰️", layout="wide")
    st.title("Ариадна · Луна → Марс")
    st.caption("Исследуйте перелёт: параметры → варианты → траектория")
    st.warning("Исследовательская модель M2: движение вокруг Солнца и идеальные импульсы. "
               "Не моделирует реальные включения двигателя, выход с орбиты Луны или захват Марсом. Не план полёта.")
    st.button("Загрузить пример", on_click=_load_example)
    if "inputs" not in st.session_state:
        st.info("Загрузите пример явно: даты и параметры аппарата не выбираются за вас.")
        return
    left, right = st.columns([1, 2.3])
    with left:
        calculate = st.button("Рассчитать перелёт", type="primary")
        inputs = _input_fields(st.session_state["inputs"])
        if calculate:
            _invalidate()
            try:
                scenario = scenario_from_mapping(inputs)
                with st.spinner("Ищем варианты перелёта…"), SCIENCE_LOCK:
                    result = search_impulsive_transfers(scenario)
                st.session_state["result"] = result
            except (ScenarioValidationError, TransferSearchError, EphemerisError) as exc:
                st.error(str(exc))
    with right:
        if "sampling_error" in st.session_state:
            st.error(st.session_state.pop("sampling_error"))
        result = st.session_state.get("result")
        if result is None:
            st.info("Задайте параметры и нажмите «Рассчитать перелёт».")
            return
        candidates = {c.candidate_id: c for c in result.pareto_front}
        chosen = st.selectbox("Вариант перелёта", list(candidates))
        candidate = candidates[chosen]
        a, b, c = st.columns(3)
        a.metric("Перелёт, суток", f"{candidate.flight_time_s / 86400:.1f}")
        b.metric("Идеальное Δv, км/с", f"{candidate.total_delta_v_m_s / 1000:.3f}")
        c.metric("Топливо, кг", f"{candidate.propellant_mass_kg:.1f}")
        if not candidate.mass_feasible:
            st.error("Недостаточно топлива по идеальной оценке M2: конечная масса ниже сухой.")
        else:
            st.info("Идеальный бюджет топлива проходит; физическая выполнимость не доказана.")
        st.write(f"Старт: {candidate.departure_epoch_utc} · Прибытие: {candidate.arrival_epoch_utc}")
        st.caption(f"Оценены {result.evaluated_candidates} вариантов; показан фронт время/топливо.")
        try:
            _render_trajectory(candidate)
        except (TransferSearchError, EphemerisError) as exc:
            _invalidate()
            st.session_state["sampling_error"] = str(exc)
            st.rerun()
        with st.expander("Что не учитывает эта модель"):
            st.write("Импульсы оцениваются только в начале и конце перелёта. Продолжительность включений не вычисляется.")
            st.write(list(IGNORED_SCENARIO_FIELDS))
