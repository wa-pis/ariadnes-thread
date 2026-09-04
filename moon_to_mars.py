#!/usr/bin/env python3
"""Учебная 2D-модель перелёта из окрестности Луны к Марсу.

Запуск:
    python3 moon_to_mars.py

Модель строит идеализированное окно запуска, размещая Марс в точке встречи,
интегрирует движение аппарата и сохраняет moon_to_mars.csv и
moon_to_mars.svg рядом со скриптом. Реальная дата запуска не подбирается.
"""

from __future__ import annotations

import csv
import sys
from math import acos, atan2, cos, degrees, pi, sin, sqrt
from pathlib import Path

import numpy as np


DAY = 86_400.0
AU = 149_597_870.7  # км

# Гравитационные параметры mu = G*M, км^3/с^2.
MU_SUN = 1.32712440018e11
MU_EARTH = 398_600.435507
MU_MOON = 4_902.800066
MU_MARS = 42_828.375214

EARTH_ORBIT = AU
MARS_ORBIT = 227_939_200.0
MOON_ORBIT = 384_400.0
MARS_RADIUS = 3_389.5

N_EARTH = sqrt(MU_SUN / EARTH_ORBIT**3)
N_MARS = sqrt(MU_SUN / MARS_ORBIT**3)
N_MOON = 2 * pi / (27.321661 * DAY)

# Начинаем на 70 000 км дальше Луны: примерно за границей её сферы влияния,
# уже после условного мгновенного разгона с лунной орбиты.
MOON_ESCAPE_OFFSET = 70_000.0
EARTH_START_RADIUS = MOON_ORBIT + MOON_ESCAPE_OFFSET
ARRIVAL_RADIUS = MARS_RADIUS + 300.0  # входящая траектория на высоте 300 км
MAX_FLIGHT_TIME = 300 * DAY

# Оценка скорости через переход Хомана и земную гиперболу ухода.
TRANSFER_AXIS = (EARTH_ORBIT + MARS_ORBIT) / 2
TRANSFER_SPEED = sqrt(MU_SUN * (2 / EARTH_ORBIT - 1 / TRANSFER_AXIS))
EARTH_SPEED = sqrt(MU_SUN / EARTH_ORBIT)
EARTH_ESCAPE_V_INFINITY = TRANSFER_SPEED - EARTH_SPEED
HYPERBOLA_ECCENTRICITY = (
    1 + EARTH_START_RADIUS * EARTH_ESCAPE_V_INFINITY**2 / MU_EARTH
)
MOON_PHASE = pi / 2 - acos(-1 / HYPERBOLA_ECCENTRICITY)
EARTH_RELATIVE_START_SPEED = sqrt(
    EARTH_ESCAPE_V_INFINITY**2 + 2 * MU_EARTH / EARTH_START_RADIUS
)


def circular_position(radius: float, angular_speed: float, phase: float, t: float) -> np.ndarray:
    angle = phase + angular_speed * t
    return radius * np.array([cos(angle), sin(angle)])


def circular_velocity(radius: float, angular_speed: float, phase: float, t: float) -> np.ndarray:
    angle = phase + angular_speed * t
    return radius * angular_speed * np.array([-sin(angle), cos(angle)])


def earth_position(t: float) -> np.ndarray:
    return circular_position(EARTH_ORBIT, N_EARTH, 0.0, t)


def earth_velocity(t: float) -> np.ndarray:
    return circular_velocity(EARTH_ORBIT, N_EARTH, 0.0, t)


def moon_position(t: float) -> np.ndarray:
    return earth_position(t) + circular_position(MOON_ORBIT, N_MOON, MOON_PHASE, t)


def moon_velocity(t: float) -> np.ndarray:
    return earth_velocity(t) + circular_velocity(MOON_ORBIT, N_MOON, MOON_PHASE, t)


def mars_position(t: float, phase: float) -> np.ndarray:
    return circular_position(MARS_ORBIT, N_MARS, phase, t)


def mars_velocity(t: float, phase: float) -> np.ndarray:
    return circular_velocity(MARS_ORBIT, N_MARS, phase, t)


def initial_state() -> np.ndarray:
    radial = np.array([cos(MOON_PHASE), sin(MOON_PHASE)])
    tangent = np.array([-sin(MOON_PHASE), cos(MOON_PHASE)])
    position = earth_position(0.0) + EARTH_START_RADIUS * radial
    velocity = earth_velocity(0.0) + EARTH_RELATIVE_START_SPEED * tangent
    return np.concatenate((position, velocity))


def pull(position: np.ndarray, source: np.ndarray, mu: float) -> np.ndarray:
    delta = source - position
    distance = np.linalg.norm(delta)
    return mu * delta / distance**3


def heliocentric_pull(
    position: np.ndarray, source: np.ndarray, mu: float
) -> np.ndarray:
    """Прямое притяжение минус ускорение Солнца в гелиоцентрической системе."""
    return pull(position, source, mu) - mu * source / np.linalg.norm(source) ** 3


def derivative(
    t: float, state: np.ndarray, mars_phase: float | None = None
) -> np.ndarray:
    position = state[:2]
    acceleration = pull(position, np.zeros(2), MU_SUN)
    acceleration += heliocentric_pull(position, earth_position(t), MU_EARTH)
    acceleration += heliocentric_pull(position, moon_position(t), MU_MOON)
    if mars_phase is not None:
        acceleration += heliocentric_pull(
            position, mars_position(t, mars_phase), MU_MARS
        )

    # Масса аппарата здесь не нужна: она сокращается в F=ma.
    return np.concatenate((state[2:], acceleration))


def rk4_step(
    t: float, state: np.ndarray, step: float, mars_phase: float | None = None
) -> np.ndarray:
    k1 = derivative(t, state, mars_phase)
    k2 = derivative(t + step / 2, state + step * k1 / 2, mars_phase)
    k3 = derivative(t + step / 2, state + step * k2 / 2, mars_phase)
    k4 = derivative(t + step, state + step * k3, mars_phase)
    return state + step * (k1 + 2 * k2 + 2 * k3 + k4) / 6


def find_mars_orbit_crossing(step: float = 600.0) -> tuple[float, np.ndarray]:
    """Пристрелочный прогон без Марса: где аппарат пересечёт его орбиту."""
    t = 0.0
    state = initial_state()
    radius = np.linalg.norm(state[:2])

    while t < MAX_FLIGHT_TIME:
        next_state = rk4_step(t, state, step)
        next_radius = np.linalg.norm(next_state[:2])
        if radius < MARS_ORBIT <= next_radius:
            fraction = (MARS_ORBIT - radius) / (next_radius - radius)
            return t + fraction * step, state + fraction * (next_state - state)
        t += step
        state, radius = next_state, next_radius

    raise RuntimeError("Аппарат не пересёк орбиту Марса за 300 суток")


def local_step(base_step: float, distance_to_mars: float) -> float:
    """Уменьшаем шаг только рядом с Марсом, где ускорение быстро меняется."""
    if distance_to_mars < 20_000:
        return min(base_step, 10.0)
    if distance_to_mars < 200_000:
        return min(base_step, 60.0)
    if distance_to_mars < 1_000_000:
        return min(base_step, 300.0)
    return base_step


def record(t: float, state: np.ndarray, mars_phase: float) -> list[float]:
    earth = earth_position(t)
    moon = moon_position(t)
    mars = mars_position(t, mars_phase)
    return [
        t / DAY,
        *state[:2],
        *state[2:],
        *earth,
        *moon,
        *mars,
        np.linalg.norm(state[:2] - mars),
    ]


def simulate(base_step: float = 900.0) -> tuple[float, float, np.ndarray, list[list[float]]]:
    crossing_t, crossing_state = find_mars_orbit_crossing()
    crossing_angle = atan2(crossing_state[1], crossing_state[0])
    mars_phase = (crossing_angle - N_MARS * crossing_t) % (2 * pi)

    t = 0.0
    state = initial_state()
    rows = [record(t, state, mars_phase)]
    next_sample = 0.5 * DAY

    while t < MAX_FLIGHT_TIME:
        distance = np.linalg.norm(state[:2] - mars_position(t, mars_phase))
        step = min(local_step(base_step, distance), MAX_FLIGHT_TIME - t)
        next_state = rk4_step(t, state, step, mars_phase)
        next_t = t + step
        next_distance = np.linalg.norm(
            next_state[:2] - mars_position(next_t, mars_phase)
        )

        if distance > ARRIVAL_RADIUS >= next_distance:
            fraction = (distance - ARRIVAL_RADIUS) / (distance - next_distance)
            arrival_t = t + fraction * step
            arrival_state = state + fraction * (next_state - state)
            rows.append(record(arrival_t, arrival_state, mars_phase))
            return mars_phase, arrival_t, arrival_state, rows

        t, state = next_t, next_state
        if t >= next_sample:
            rows.append(record(t, state, mars_phase))
            next_sample += 0.5 * DAY

    raise RuntimeError("Аппарат не пересёк высоту 300 км над Марсом")


def write_csv(rows: list[list[float]], path: Path) -> None:
    header = [
        "day",
        "spacecraft_x_km",
        "spacecraft_y_km",
        "spacecraft_vx_km_s",
        "spacecraft_vy_km_s",
        "earth_x_km",
        "earth_y_km",
        "moon_x_km",
        "moon_y_km",
        "mars_x_km",
        "mars_y_km",
        "distance_to_mars_km",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def write_svg(rows: list[list[float]], path: Path) -> None:
    size, margin = 900, 60
    scale = (size - 2 * margin) / (3.3 * AU)

    def point(x: float, y: float) -> tuple[float, float]:
        return size / 2 + x * scale, size / 2 - y * scale

    trajectory = " ".join(
        f"{point(row[1], row[2])[0]:.2f},{point(row[1], row[2])[1]:.2f}"
        for row in rows
    )
    start = point(rows[0][1], rows[0][2])
    arrival = point(rows[-1][1], rows[-1][2])
    mars_at_arrival = point(rows[-1][9], rows[-1][10])
    orbit_earth = EARTH_ORBIT * scale
    orbit_mars = MARS_ORBIT * scale

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
<rect width="100%" height="100%" fill="#07111f"/>
<text x="30" y="38" fill="#e8eef7" font-family="system-ui" font-size="22">Окрестность Луны → Марс (учебная 2D-модель)</text>
<circle cx="{size/2}" cy="{size/2}" r="{orbit_earth:.2f}" fill="none" stroke="#365574" stroke-width="1"/>
<circle cx="{size/2}" cy="{size/2}" r="{orbit_mars:.2f}" fill="none" stroke="#683f3b" stroke-width="1"/>
<circle cx="{size/2}" cy="{size/2}" r="8" fill="#ffd166"/>
<polyline points="{trajectory}" fill="none" stroke="#55d6be" stroke-width="3"/>
<circle cx="{start[0]:.2f}" cy="{start[1]:.2f}" r="6" fill="#66aaff"/>
<circle cx="{arrival[0]:.2f}" cy="{arrival[1]:.2f}" r="6" fill="#ffffff"/>
<circle cx="{mars_at_arrival[0]:.2f}" cy="{mars_at_arrival[1]:.2f}" r="7" fill="#ef6f55"/>
<text x="{start[0]+10:.2f}" y="{start[1]-10:.2f}" fill="#9fc9ff" font-family="system-ui" font-size="15">старт у Луны</text>
<text x="{arrival[0]+10:.2f}" y="{arrival[1]-10:.2f}" fill="#ffad99" font-family="system-ui" font-size="15">высота 300 км</text>
<text x="30" y="875" fill="#8da2b8" font-family="system-ui" font-size="14">Расстояния показаны в масштабе; размеры тел увеличены.</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def self_check() -> None:
    coarse_t, _ = find_mars_orbit_crossing(1_200.0)
    fine_t, _ = find_mars_orbit_crossing(600.0)
    _, coarse_arrival_t, _, _ = simulate(1_800.0)
    phase, arrival_t, arrival_state, _ = simulate(900.0)
    assert abs(coarse_t - fine_t) < 60.0
    assert abs(coarse_arrival_t - arrival_t) < 60.0
    assert 40 < degrees(phase) < 50
    assert arrival_t < MAX_FLIGHT_TIME
    assert np.isfinite(arrival_state).all()
    print(
        "OK: сходимость по времени пересечения",
        f"{abs(coarse_t - fine_t):.1f} с; высота 300 км через {arrival_t / DAY:.2f} суток",
    )


def main() -> None:
    if "--self-check" in sys.argv:
        self_check()
        return

    mars_phase, arrival_t, arrival_state, rows = simulate()
    output_dir = Path(__file__).resolve().parent
    csv_path = output_dir / "moon_to_mars.csv"
    svg_path = output_dir / "moon_to_mars.svg"
    write_csv(rows, csv_path)
    write_svg(rows, svg_path)

    start = initial_state()
    relative_to_moon = np.linalg.norm(start[2:] - moon_velocity(0.0))
    relative_to_mars = np.linalg.norm(
        arrival_state[2:] - mars_velocity(arrival_t, mars_phase)
    )
    print(f"Начальная фаза Марса:        {degrees(mars_phase):8.3f}°")
    print(f"Скорость относительно Земли: {EARTH_RELATIVE_START_SPEED:8.3f} км/с")
    print(f"Скорость относительно Луны:  {relative_to_moon:8.3f} км/с")
    escape_speed = sqrt(2 * MU_MARS / ARRIVAL_RADIUS)
    print(f"Время до высоты 300 км:      {arrival_t / DAY:8.2f} суток")
    print(f"Скорость сближения:          {relative_to_mars:8.3f} км/с")
    print(f"Скорость убегания там:       {escape_speed:8.3f} км/с")
    print("Захват на орбиту не смоделирован: без торможения аппарат столкнётся с Марсом.")
    print(f"Результаты: {csv_path.name}, {svg_path.name}")


if __name__ == "__main__":
    main()
