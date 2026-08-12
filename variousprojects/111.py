"""
Telecom Raw Log Processor - Complete Production Pipeline v2.0
=============================================================
Полный ETL-пайплайн обработки сырых логов базовых станций и ядра сети.

Возможности:
  - Парсинг RAN (базовые станции) и Core (S1-MME) логов
  - Обезличивание IMSI (HMAC-SHA256, усечение до 64 бит)
  - Расчет расстояний: TA→км, TA→метры, горизонтальное расстояние
  - Геопривязка: проекция позиции абонента по азимуту + TA + высоте
  - Построение треков движения (сессии)
  - Анализ причин обрывов (5 сценариев)
  - Экспорт: GeoJSON (QGIS), CSV, Parquet, ClickHouse, HTML-карта

Запуск демо:
    python telecom_pipeline.py

Требования: Python 3.9+
Установка:  pip install numpy pandas pyarrow clickhouse-driver folium
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import sqlite3
import sys
import uuid
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import (Any, Dict, Generator, Iterable, List,
                    Optional, Set, Tuple, Union)

warnings.filterwarnings('ignore')

# ============================================================================
# Dependency checks
# ============================================================================
_DEPS: Dict[str, bool] = {}

try:
    import numpy as np
    _DEPS['numpy'] = True
except ImportError:
    _DEPS['numpy'] = False

try:
    import pandas as pd
    _DEPS['pandas'] = True
except ImportError:
    _DEPS['pandas'] = False

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    _DEPS['pyarrow'] = True
except ImportError:
    _DEPS['pyarrow'] = False

try:
    from clickhouse_driver import Client as CHClient
    _DEPS['clickhouse'] = True
except ImportError:
    _DEPS['clickhouse'] = False

try:
    import geopandas as gpd
    _DEPS['geopandas'] = True
except ImportError:
    _DEPS['geopandas'] = False

try:
    from shapely.geometry import Point, LineString
    _DEPS['shapely'] = True
except ImportError:
    _DEPS['shapely'] = False

try:
    import folium
    from folium.plugins import HeatMap
    _DEPS['folium'] = True
except ImportError:
    _DEPS['folium'] = False


# ============================================================================
# Constants
# ============================================================================
METERS_PER_TA = 78.12          # метров на 1 шаг TA (3GPP TS 36.211)
KM_PER_TA = METERS_PER_TA / 1000.0
EARTH_RADIUS_M = 6_371_000.0

# Пороги RSRP
RSRP_EXCELLENT = -80
RSRP_GOOD = -95
RSRP_MID = -105
RSRP_EDGE = -115
RSRP_CRITICAL = -124

# Пороги расстояний (км)
DIST_VERY_CLOSE = 0.2
DIST_CLOSE = 1.0
DIST_MEDIUM = 5.0
DIST_FAR = 10.0
DIST_VERY_FAR = 30.0


# ============================================================================
# Enums
# ============================================================================
class SignalQuality(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    MID_CELL = "MID_CELL"
    CELL_EDGE = "CELL_EDGE"
    CRITICAL = "CRITICAL"
    BELOW_SENS = "BELOW_SENS"


class DropCause(str, Enum):
    COVERAGE_HOLE = "COVERAGE_HOLE"
    HO_FAILURE = "HO_FAILURE"
    SUDDEN_UE_LOSS = "SUDDEN_UE_LOSS"
    ISOLATED_CELL_EDGE = "ISOLATED_CELL_EDGE"
    CORE_FAILURE = "CORE_FAILURE"
    NORMAL_END = "NORMAL_END"
    UNKNOWN = "UNKNOWN"


class MovementTrend(str, Enum):
    APPROACHING = "APPROACHING"
    RECEDING = "RECEDING"
    STATIONARY = "STATIONARY"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# Utility Functions
# ============================================================================
def ta_to_km(ta: int) -> float:
    """TA → километры."""
    return round(ta * KM_PER_TA, 3)


def ta_to_m(ta: int) -> float:
    """TA → метры."""
    return round(ta * METERS_PER_TA, 1)


def classify_distance_km(dist_km: float) -> str:
    if dist_km <= DIST_VERY_CLOSE:
        return "very_close"
    elif dist_km <= DIST_CLOSE:
        return "close"
    elif dist_km <= DIST_MEDIUM:
        return "medium"
    elif dist_km <= DIST_FAR:
        return "far"
    elif dist_km <= DIST_VERY_FAR:
        return "very_far"
    return "edge"


def classify_rsrp(rsrp: float) -> SignalQuality:
    if rsrp > RSRP_EXCELLENT:
        return SignalQuality.EXCELLENT
    if rsrp > RSRP_GOOD:
        return SignalQuality.GOOD
    if rsrp > RSRP_MID:
        return SignalQuality.MID_CELL
    if rsrp > RSRP_EDGE:
        return SignalQuality.CELL_EDGE
    if rsrp > RSRP_CRITICAL:
        return SignalQuality.CRITICAL
    return SignalQuality.BELOW_SENS


def ground_distance_km(ta: int, height_m: float) -> float:
    """Горизонтальное расстояние с учетом высоты антенны."""
    slant = ta_to_m(ta)
    if slant <= height_m:
        return round(slant * 0.6 / 1000.0, 3)
    ground = math.sqrt(slant ** 2 - height_m ** 2)
    return round(ground / 1000.0, 3)


def haversine_distance(lat1: float, lon1: float,
                       lat2: float, lon2: float) -> float:
    """Расстояние между точками в метрах."""
    rlat1, rlon1 = math.radians(lat1), math.radians(lon1)
    rlat2, rlon2 = math.radians(lat2), math.radians(lon2)
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def project_point(lat: float, lon: float, distance_m: float,
                  azimuth_deg: float, tilt_deg: float = 0.0) -> Tuple[float, float]:
    """Проекция точки на расстояние по азимуту."""
    if distance_m <= 0:
        return lat, lon
    horizontal = distance_m * math.cos(math.radians(tilt_deg))
    if horizontal <= 0:
        return lat, lon
    rlat = math.radians(lat)
    rlon = math.radians(lon)
    raz = math.radians(azimuth_deg)
    ad = horizontal / EARTH_RADIUS_M
    new_lat = math.asin(
        math.sin(rlat) * math.cos(ad) +
        math.cos(rlat) * math.sin(ad) * math.cos(raz)
    )
    new_lon = rlon + math.atan2(
        math.sin(raz) * math.sin(ad) * math.cos(rlat),
        math.cos(ad) - math.sin(rlat) * math.sin(new_lat)
    )
    return math.degrees(new_lat), math.degrees(new_lon)


def estimate_ue_position(ta: int, site_lat: float, site_lon: float,
                         azimuth: float, tilt: float, height_m: float) -> Tuple[float, float]:
    """Оценка позиции абонента."""
    slant = ta_to_m(ta)
    if slant <= height_m:
        horizontal = slant * 0.6
    else:
        horizontal = math.sqrt(slant ** 2 - height_m ** 2)
    return project_point(site_lat, site_lon, horizontal, azimuth, tilt)


def detect_movement_trend(ta_list: List[int]) -> MovementTrend:
    """Тренд движения по TA."""
    if len(ta_list) < 2:
        return MovementTrend.UNKNOWN
    recent = ta_list[-3:] if len(ta_list) >= 3 else ta_list
    if len(recent) < 2:
        return MovementTrend.UNKNOWN
    first, last = recent[0], recent[-1]
    if last > first + 1:
        return MovementTrend.RECEDING
    elif last < first - 1:
        return MovementTrend.APPROACHING
    elif all(abs(recent[i] - recent[i-1]) <= 1 for i in range(1, len(recent))):
        return MovementTrend.STATIONARY
    return MovementTrend.UNKNOWN


# ============================================================================
# Data Models
# ============================================================================
@dataclass
class NeighborCell:
    pci: int
    cell_id: Optional[str] = None
    rsrp: float = -140.0
    rsrq: Optional[float] = None
    delta_rsrp: float = 0.0
    trigger: str = "A3"
    ttt_ms: int = 0
    forbidden: bool = False

    def __post_init__(self):
        if not 0 <= self.pci <= 1007:
            raise ValueError(f"PCI {self.pci} out of range")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pci': self.pci, 'cell_id': self.cell_id,
            'rsrp': self.rsrp, 'rsrq': self.rsrq,
            'delta_rsrp': self.delta_rsrp, 'trigger': self.trigger,
            'ttt_ms': self.ttt_ms, 'forbidden': self.forbidden,
        }


@dataclass
class NetworkEvent:
    subscriber_hash: str
    cell_id: str
    timestamp: datetime
    ta: int
    rsrp: float
    neighbor_list: List[NeighborCell] = field(default_factory=list)
    event_type: str = "MEASUREMENT_REPORT"
    source: str = "RAN"
    # Расчетные
    distance_km: float = 0.0
    distance_m: float = 0.0
    distance_category: str = ""
    signal_quality: str = ""
    ue_lat: Optional[float] = None
    ue_lon: Optional[float] = None
    site_lat: Optional[float] = None
    site_lon: Optional[float] = None
    is_edge: bool = False
    anomaly: str = ""

    def __post_init__(self):
        if not 0 <= self.ta <= 3846:
            raise ValueError(f"TA {self.ta} out of range")
        if self.distance_km == 0.0:
            self.distance_km = ta_to_km(self.ta)
        if self.distance_m == 0.0:
            self.distance_m = ta_to_m(self.ta)
        if not self.distance_category:
            self.distance_category = classify_distance_km(self.distance_km)
        if not self.signal_quality:
            self.signal_quality = classify_rsrp(self.rsrp).value

    def to_dict(self) -> Dict[str, Any]:
        return {
            'subscriber_hash': self.subscriber_hash,
            'cell_id': self.cell_id,
            'timestamp': self.timestamp.isoformat(),
            'ta': self.ta,
            'rsrp': self.rsrp,
            'distance_km': self.distance_km,
            'distance_m': self.distance_m,
            'distance_category': self.distance_category,
            'signal_quality': self.signal_quality,
            'ue_lat': self.ue_lat,
            'ue_lon': self.ue_lon,
            'site_lat': self.site_lat,
            'site_lon': self.site_lon,
            'is_edge': self.is_edge,
            'event_type': self.event_type,
            'neighbor_count': len(self.neighbor_list),
            'anomaly': self.anomaly,
        }


@dataclass
class SubscriberSession:
    subscriber_hash: str
    events: List[NetworkEvent] = field(default_factory=list)

    @property
    def start_time(self) -> Optional[datetime]:
        return self.events[0].timestamp if self.events else None

    @property
    def end_time(self) -> Optional[datetime]:
        return self.events[-1].timestamp if self.events else None

    @property
    def start_cell(self) -> Optional[str]:
        return self.events[0].cell_id if self.events else None

    @property
    def end_cell(self) -> Optional[str]:
        return self.events[-1].cell_id if self.events else None

    @property
    def avg_rsrp(self) -> float:
        if not self.events: return 0.0
        return round(sum(e.rsrp for e in self.events) / len(self.events), 2)

    @property
    def avg_ta(self) -> float:
        if not self.events: return 0.0
        return round(sum(e.ta for e in self.events) / len(self.events), 2)

    @property
    def avg_distance_km(self) -> float:
        if not self.events: return 0.0
        return round(sum(e.distance_km for e in self.events) / len(self.events), 3)

    @property
    def max_distance_km(self) -> float:
        return max((e.distance_km for e in self.events), default=0.0)

    @property
    def min_distance_km(self) -> float:
        return min((e.distance_km for e in self.events), default=0.0)

    @property
    def total_path_km(self) -> float:
        if len(self.events) < 2:
            return 0.0
        total = 0.0
        for i in range(1, len(self.events)):
            p, c = self.events[i-1], self.events[i]
            if p.ue_lat and p.ue_lon and c.ue_lat and c.ue_lon:
                total += haversine_distance(p.ue_lat, p.ue_lon, c.ue_lat, c.ue_lon)
        return round(total / 1000.0, 3)

    @property
    def movement_trend(self) -> str:
        return detect_movement_trend([e.ta for e in self.events]).value

    @property
    def trajectory_points(self) -> List[Tuple[float, float]]:
        return [(e.ue_lat, e.ue_lon) for e in self.events
                if e.ue_lat is not None and e.ue_lon is not None]

    @property
    def duration_sec(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            'subscriber_hash': self.subscriber_hash,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_sec': self.duration_sec,
            'start_cell': self.start_cell,
            'end_cell': self.end_cell,
            'events_count': len(self.events),
            'avg_rsrp': self.avg_rsrp,
            'avg_ta': self.avg_ta,
            'avg_distance_km': self.avg_distance_km,
            'max_distance_km': self.max_distance_km,
            'min_distance_km': self.min_distance_km,
            'total_path_km': self.total_path_km,
            'movement_trend': self.movement_trend,
            'trajectory_points': len(self.trajectory_points),
        }


@dataclass
class SiteRecord:
    cell_id: str
    latitude: float
    longitude: float
    azimuth: float
    mechanical_tilt: float = 0.0
    electrical_tilt: float = 0.0
    height_m: float = 30.0
    band: str = "1800"
    technology: str = "LTE"
    site_name: str = ""
    region: str = ""

    def __post_init__(self):
        if not 0 <= self.azimuth <= 360:
            raise ValueError(f"Invalid azimuth: {self.azimuth}")
        if self.height_m <= 0:
            raise ValueError(f"Invalid height: {self.height_m}")

    @property
    def total_tilt(self) -> float:
        return self.mechanical_tilt + self.electrical_tilt


# ============================================================================
# Core Components
# ============================================================================
class SubscriberAnonymizer:
    def __init__(self, salt: Optional[str] = None):
        if salt is None:
            salt = os.environ.get('ANONYMIZER_SALT', uuid.uuid4().hex)
        self._salt = salt.encode() if isinstance(salt, str) else salt
        self._cache: Dict[str, str] = {}

    def hash(self, imsi: str) -> str:
        if imsi not in self._cache:
            d = hmac.new(self._salt, imsi.encode(), hashlib.sha256)
            self._cache[imsi] = d.hexdigest()[:16]
        return self._cache[imsi]


class SiteDatabase:
    def __init__(self):
        self._sites: Dict[str, SiteRecord] = {}
        self._pci_map: Dict[int, List[str]] = defaultdict(list)

    def add(self, site: SiteRecord) -> None:
        self._sites[site.cell_id] = site
        try:
            pci = abs(hash(site.cell_id)) % 504
            self._pci_map[pci].append(site.cell_id)
        except Exception:
            pass

    def get(self, cell_id: str) -> Optional[SiteRecord]:
        return self._sites.get(cell_id)

    def resolve_pci(self, pci: int) -> Optional[str]:
        lst = self._pci_map.get(pci, [])
        return lst[0] if lst else None

    def load_csv(self, path: str) -> int:
        if not _DEPS['pandas']:
            raise ImportError("pandas required")
        df = pd.read_csv(path)
        count = 0
        for _, row in df.iterrows():
            self.add(SiteRecord(
                cell_id=str(row['cell_id']),
                latitude=float(row['lat']),
                longitude=float(row['lon']),
                azimuth=float(row.get('azimuth', 0)),
                mechanical_tilt=float(row.get('mech_tilt', 0)),
                electrical_tilt=float(row.get('elec_tilt', 0)),
                height_m=float(row.get('height_m', 30)),
                band=str(row.get('band', '1800')),
                technology=str(row.get('tech', 'LTE')),
                site_name=str(row.get('site_name', '')),
                region=str(row.get('region', '')),
            ))
            count += 1
        return count

    def __len__(self) -> int:
        return len(self._sites)


class RawLogParser:
    def __init__(self, anonymizer: SubscriberAnonymizer):
        self.anonymizer = anonymizer
        self.errors: List[Dict] = []

    def _parse_timestamp(self, ts: Any) -> Optional[datetime]:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except ValueError:
                pass
        return None

    def parse_ran(self, raw: Dict[str, Any]) -> Optional[NetworkEvent]:
        try:
            imsi = str(raw.get('imsi', ''))
            if not imsi: return None
            ts = self._parse_timestamp(raw.get('timestamp'))
            if ts is None: return None
            cell_id = str(raw.get('cell_id', ''))
            if not cell_id: return None
            ta = int(raw.get('ta', 0))
            rsrp = float(raw.get('rsrp', -140))
            if not 0 <= ta <= 3846: return None
            if not -156 <= rsrp <= -40: return None

            neighbors = []
            for n in raw.get('neighbors', []):
                try:
                    neighbors.append(NeighborCell(
                        pci=int(n['pci']),
                        cell_id=n.get('cell_id'),
                        rsrp=float(n.get('rsrp', -140)),
                        rsrq=float(n['rsrq']) if 'rsrq' in n else None,
                        delta_rsrp=float(n.get('delta_rsrp', 0)),
                        trigger=n.get('trigger', 'A3'),
                        ttt_ms=int(n.get('ttt', 0)),
                        forbidden=bool(n.get('forbidden', False)),
                    ))
                except (ValueError, KeyError):
                    continue

            return NetworkEvent(
                subscriber_hash=self.anonymizer.hash(imsi),
                cell_id=cell_id, timestamp=ts, ta=ta, rsrp=rsrp,
                neighbor_list=neighbors,
                event_type=raw.get('event_type', 'MEASUREMENT_REPORT'),
                source='RAN',
            )
        except Exception as e:
            self.errors.append({'raw': raw, 'error': str(e)})
            return None

    def parse_core(self, raw: Dict[str, Any]) -> Optional[NetworkEvent]:
        try:
            imsi = str(raw.get('imsi', ''))
            if not imsi: return None
            ts = self._parse_timestamp(raw.get('timestamp'))
            if ts is None: return None
            event = NetworkEvent(
                subscriber_hash=self.anonymizer.hash(imsi),
                cell_id=str(raw.get('cell_id', 'UNKNOWN')),
                timestamp=ts,
                ta=int(raw.get('ta', 0)),
                rsrp=float(raw.get('rsrp', -140)),
                event_type=raw.get('event_type', 'S1AP'),
                source='CORE',
            )
            if 'cause' in raw:
                event.anomaly = str(raw['cause'])
            return event
        except Exception as e:
            self.errors.append({'raw': raw, 'error': str(e)})
            return None

    def parse_batch(self, raw_events: List[Dict], source: str = 'RAN') -> List[NetworkEvent]:
        parser = self.parse_ran if source == 'RAN' else self.parse_core
        return [evt for raw in raw_events if (evt := parser(raw)) is not None]


class EventEnricher:
    def __init__(self, site_db: SiteDatabase):
        self.site_db = site_db
        self.unmapped: Set[str] = set()

    def enrich(self, event: NetworkEvent) -> NetworkEvent:
        site = self.site_db.get(event.cell_id)
        if site is None:
            self.unmapped.add(event.cell_id)
            event.anomaly = 'UNMAPPED_CELL'
            return event
        event.site_lat = site.latitude
        event.site_lon = site.longitude
        ue_lat, ue_lon = estimate_ue_position(
            ta=event.ta, site_lat=site.latitude, site_lon=site.longitude,
            azimuth=site.azimuth, tilt=site.total_tilt, height_m=site.height_m,
        )
        event.ue_lat = ue_lat
        event.ue_lon = ue_lon
        gd = ground_distance_km(event.ta, site.height_m)
        event.distance_category = classify_distance_km(gd)
        event.is_edge = (event.rsrp < -115 and event.ta > 30)
        for n in event.neighbor_list:
            if n.cell_id is None:
                resolved = self.site_db.resolve_pci(n.pci)
                if resolved:
                    n.cell_id = resolved
        return event

    def enrich_batch(self, events: List[NetworkEvent]) -> List[NetworkEvent]:
        return [self.enrich(e) for e in events]


class SessionBuilder:
    def __init__(self, timeout_min: int = 15):
        self.timeout_sec = timeout_min * 60

    def build(self, events: List[NetworkEvent]) -> List[SubscriberSession]:
        groups: Dict[str, List[NetworkEvent]] = defaultdict(list)
        for e in events:
            groups[e.subscriber_hash].append(e)
        sessions = []
        for sub_hash, sub_events in groups.items():
            sub_events.sort(key=lambda x: x.timestamp)
            chunk = [sub_events[0]]
            for i in range(1, len(sub_events)):
                gap = (sub_events[i].timestamp - sub_events[i-1].timestamp).total_seconds()
                if gap > self.timeout_sec:
                    sessions.append(SubscriberSession(sub_hash, chunk))
                    chunk = [sub_events[i]]
                else:
                    chunk.append(sub_events[i])
            if chunk:
                sessions.append(SubscriberSession(sub_hash, chunk))
        return sessions


class DropAnalyzer:
    @staticmethod
    def analyze(session: SubscriberSession) -> Dict[str, Any]:
        if len(session.events) < 2:
            return {'drop_detected': False, 'drop_cause': DropCause.NORMAL_END.value}

        last = session.events[-1]
        prev = session.events[-2]
        window = session.events[-5:]
        rsrp_vals = [e.rsrp for e in window]
        ta_vals = [e.ta for e in window]

        result = {
            'drop_detected': False,
            'drop_cause': DropCause.UNKNOWN.value,
            'drop_point': None,
            'target_neighbors': [],
            'final_rsrp': last.rsrp,
            'final_ta': last.ta,
            'final_distance_km': last.distance_km,
            'avg_rsrp': session.avg_rsrp,
            'avg_ta': session.avg_ta,
            'avg_distance_km': session.avg_distance_km,
            'signal_trend': 'STABLE',
            'distance_trend': session.movement_trend,
        }

        if len(rsrp_vals) >= 2:
            if rsrp_vals[-1] < -120 and ta_vals[-1] > ta_vals[0]:
                result['signal_trend'] = 'DETERIORATING'
            elif rsrp_vals[-1] > -85 and max(ta_vals) - min(ta_vals) <= 2:
                result['signal_trend'] = 'STRONG_SUDDEN'

        # Scenario A: Coverage hole
        if last.rsrp < -120 and last.ta > prev.ta:
            result['drop_detected'] = True
            result['drop_cause'] = DropCause.COVERAGE_HOLE.value
            if last.ue_lat and last.ue_lon:
                result['drop_point'] = {'lat': last.ue_lat, 'lon': last.ue_lon}

        # Scenario B: Sudden drop on good signal
        elif prev.rsrp > -85 and last.rsrp < -130:
            result['drop_detected'] = True
            strong_nbr = [n for n in prev.neighbor_list if n.rsrp > -105]
            result['target_neighbors'] = [n.cell_id for n in strong_nbr if n.cell_id]
            result['drop_cause'] = DropCause.HO_FAILURE.value if strong_nbr else DropCause.SUDDEN_UE_LOSS.value

        # Scenario C: Cell edge, no neighbors
        elif last.rsrp < -115 and not last.neighbor_list:
            result['drop_detected'] = True
            result['drop_cause'] = DropCause.ISOLATED_CELL_EDGE.value
            if last.ue_lat and last.ue_lon:
                result['drop_point'] = {'lat': last.ue_lat, 'lon': last.ue_lon}

        # Scenario D: Core network error
        if last.anomaly and 'NETWORK' in last.anomaly.upper():
            result['drop_detected'] = True
            result['drop_cause'] = DropCause.CORE_FAILURE.value

        return result


# ============================================================================
# Exporters
# ============================================================================
class GeoJSONExporter:
    @staticmethod
    def export(sessions: List[SubscriberSession], filepath: str) -> int:
        features = []
        for s in sessions:
            pts = s.trajectory_points
            if len(pts) < 2:
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in pts]},
                "properties": s.summary()
            })
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {"total_tracks": len(features), "generated": datetime.now(timezone.utc).isoformat()}
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        return len(features)


class CSVExporter:
    @staticmethod
    def export_sessions(sessions: List[SubscriberSession], filepath: str) -> int:
        if not _DEPS['pandas']:
            return 0
        pd.DataFrame([s.summary() for s in sessions]).to_csv(filepath, index=False)
        return len(sessions)

    @staticmethod
    def export_drops(drops: List[Dict], filepath: str) -> int:
        if not _DEPS['pandas']:
            return 0
        pd.DataFrame(drops).to_csv(filepath, index=False)
        return len(drops)


class ParquetExporter:
    @staticmethod
    def export_sessions(sessions: List[SubscriberSession], filepath: str) -> int:
        if not _DEPS['pyarrow']:
            return 0
        rows = [s.summary() for s in sessions]
        if not rows:
            return 0
        pq.write_table(pa.Table.from_pylist(rows), filepath, compression='snappy')
        return len(rows)


class ClickHouseExporter:
    """Экспорт витрины в ClickHouse."""

    DDL = """
    CREATE TABLE IF NOT EXISTS {database}.{table} (
        date Date,
        subscriber_hash FixedString(16),
        session_start DateTime64(3, 'UTC'),
        session_end DateTime64(3, 'UTC'),
        start_cell String,
        end_cell String,
        target_neighbors Array(String),
        avg_rsrp Float32,
        final_rsrp Float32,
        avg_ta Float32,
        final_ta UInt16,
        avg_distance_km Float32,
        final_distance_km Float32,
        total_path_km Float32,
        drop_cause LowCardinality(String),
        signal_trend LowCardinality(String),
        distance_trend LowCardinality(String),
        drop_lat Float64,
        drop_lon Float64,
        trajectory_points UInt16
    ) ENGINE = MergeTree()
    PARTITION BY toYYYYMM(date)
    ORDER BY (drop_cause, date, subscriber_hash)
    SETTINGS index_granularity = 8192
    """

    def __init__(self, host: str = 'localhost', port: int = 9000,
                 database: str = 'telecom', table: str = 'rf_dropped_sessions'):
        self.host = host
        self.port = port
        self.database = database
        self.table = table
        self._client = None

    def connect(self) -> bool:
        if not _DEPS['clickhouse']:
            print("ERROR: clickhouse-driver not installed. Run: pip install clickhouse-driver")
            return False
        try:
            self._client = CHClient(host=self.host, port=self.port)
            self._client.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            self._client = CHClient(host=self.host, port=self.port, database=self.database)
            self._client.execute(self.DDL.format(database=self.database, table=self.table))
            print(f"Connected to ClickHouse, table {self.database}.{self.table} ready")
            return True
        except Exception as e:
            print(f"ClickHouse connection failed: {e}")
            return False

    def insert_drops(self, drops: List[Dict], sessions_map: Dict[str, SubscriberSession]) -> int:
        if not self._client:
            return 0
        rows = []
        for d in drops:
            if not d.get('drop_detected'):
                continue
            sub_hash = d.get('subscriber_hash', '')
            session = sessions_map.get(sub_hash)
            if session is None:
                continue

            end_dt = session.end_time or datetime.now(timezone.utc)
            rows.append((
                end_dt.date(),
                sub_hash,
                session.start_time,
                end_dt,
                session.start_cell or '',
                session.end_cell or '',
                d.get('target_neighbors', []),
                d.get('avg_rsrp', 0.0),
                d.get('final_rsrp', 0.0),
                d.get('avg_ta', 0.0),
                int(d.get('final_ta', 0)),
                d.get('avg_distance_km', 0.0),
                d.get('final_distance_km', 0.0),
                session.total_path_km,
                d.get('drop_cause', 'UNKNOWN'),
                d.get('signal_trend', 'STABLE'),
                d.get('distance_trend', 'UNKNOWN'),
                d['drop_point']['lat'] if d.get('drop_point') else 0.0,
                d['drop_point']['lon'] if d.get('drop_point') else 0.0,
                len(session.trajectory_points),
            ))

        if rows:
            self._client.execute(
                f"INSERT INTO {self.database}.{self.table} VALUES",
                rows
            )
        return len(rows)


class HTMLMapExporter:
    """Интерактивная HTML-карта треков (folium)."""

    @staticmethod
    def export(sessions: List[SubscriberSession], filepath: str) -> bool:
        if not _DEPS['folium']:
            print("folium not installed. Run: pip install folium")
            return False

        if not sessions:
            print("No sessions to export")
            return False

        # Центр карты — первая точка первого трека
        center = None
        for s in sessions:
            pts = s.trajectory_points
            if pts:
                center = pts[0]
                break
        if center is None:
            center = (55.751244, 37.618423)  # Moscow default

        m = folium.Map(location=center, zoom_start=14, tiles='OpenStreetMap')

        colors = ['red', 'blue', 'green', 'orange', 'purple', 'darkred', 'darkblue']
        color_idx = 0

        for session in sessions:
            pts = session.trajectory_points
            if len(pts) < 2:
                continue

            color = colors[color_idx % len(colors)]
            color_idx += 1

            # Линия трека
            folium.PolyLine(
                pts,
                color=color,
                weight=3,
                opacity=0.7,
                popup=f"Sub: {session.subscriber_hash[:8]}<br>"
                      f"RSRP avg: {session.avg_rsrp} dBm<br>"
                      f"Dist avg: {session.avg_distance_km} km<br>"
                      f"Path: {session.total_path_km} km"
            ).add_to(m)

            # Точки старта и конца
            folium.CircleMarker(
                pts[0], radius=6, color='green', fill=True,
                popup=f"START: {session.start_cell}"
            ).add_to(m)
            folium.CircleMarker(
                pts[-1], radius=6, color='red', fill=True,
                popup=f"END: {session.end_cell}"
            ).add_to(m)

        m.save(filepath)
        print(f"HTML map saved to {filepath}")
        return True


# ============================================================================
# Main Pipeline
# ============================================================================
class TelecomPipeline:
    """Основной оркестратор."""

    def __init__(self, salt: Optional[str] = None, session_timeout_min: int = 15):
        self.anonymizer = SubscriberAnonymizer(salt)
        self.site_db = SiteDatabase()
        self.parser = RawLogParser(self.anonymizer)
        self.enricher = EventEnricher(self.site_db)
        self.session_builder = SessionBuilder(session_timeout_min)
        self.drop_analyzer = DropAnalyzer()
        self.stats: Dict[str, Any] = {}

    def load_sites_csv(self, path: str) -> int:
        return self.site_db.load_csv(path)

    def add_sites(self, sites: List[Dict]) -> int:
        count = 0
        for s in sites:
            self.site_db.add(SiteRecord(**s))
            count += 1
        return count

    def process(self, raw_events: List[Dict], source: str = 'RAN') -> Tuple[List[SubscriberSession], List[Dict]]:
        # Parse
        events = self.parser.parse_batch(raw_events, source)
        # Enrich
        enriched = self.enricher.enrich_batch(events)
        # Build sessions
        sessions = self.session_builder.build(enriched)
        # Analyze drops
        drops = []
        sessions_map = {}
        for s in sessions:
            analysis = self.drop_analyzer.analyze(s)
            analysis.update({
                'subscriber_hash': s.subscriber_hash,
                'session_start': s.start_time.isoformat() if s.start_time else None,
                'session_end': s.end_time.isoformat() if s.end_time else None,
                'start_cell': s.start_cell,
                'end_cell': s.end_cell,
                'events_count': len(s.events),
            })
            drops.append(analysis)
            sessions_map[s.subscriber_hash] = s

        self.stats = {
            'raw_events': len(raw_events),
            'parsed_events': len(events),
            'enriched_events': len(enriched),
            'sessions': len(sessions),
            'drops_detected': sum(1 for d in drops if d.get('drop_detected')),
            'unmapped_cells': list(self.enricher.unmapped),
            'parse_errors': len(self.parser.errors),
        }
        return sessions, drops


# ============================================================================
# Demo Data Generator
# ============================================================================
def generate_demo_sites() -> List[Dict]:
    """Генерация демо-станций (район Москвы)."""
    return [
        {'cell_id': '250-01-001-1A', 'latitude': 55.751244, 'longitude': 37.618423,
         'azimuth': 0, 'mechanical_tilt': 2, 'electrical_tilt': 4, 'height_m': 30,
         'band': '1800', 'technology': 'LTE', 'site_name': 'Red Square'},
        {'cell_id': '250-01-001-2A', 'latitude': 55.751244, 'longitude': 37.618423,
         'azimuth': 120, 'mechanical_tilt': 2, 'electrical_tilt': 4, 'height_m': 30,
         'band': '1800', 'technology': 'LTE', 'site_name': 'Red Square'},
        {'cell_id': '250-01-001-3A', 'latitude': 55.751244, 'longitude': 37.618423,
         'azimuth': 240, 'mechanical_tilt': 2, 'electrical_tilt': 4, 'height_m': 30,
         'band': '1800', 'technology': 'LTE', 'site_name': 'Red Square'},
        {'cell_id': '250-01-002-1A', 'latitude': 55.755000, 'longitude': 37.622000,
         'azimuth': 60, 'mechanical_tilt': 3, 'electrical_tilt': 2, 'height_m': 25,
         'band': '1800', 'technology': 'LTE', 'site_name': 'North Tower'},
        {'cell_id': '250-01-002-2A', 'latitude': 55.755000, 'longitude': 37.622000,
         'azimuth': 180, 'mechanical_tilt': 3, 'electrical_tilt': 2, 'height_m': 25,
         'band': '1800', 'technology': 'LTE', 'site_name': 'North Tower'},
        {'cell_id': '250-01-003-1A', 'latitude': 55.748000, 'longitude': 37.615000,
         'azimuth': 90, 'mechanical_tilt': 0, 'electrical_tilt': 6, 'height_m': 20,
         'band': '800', 'technology': 'LTE', 'site_name': 'South Bridge'},
    ]


def generate_demo_events() -> List[Dict]:
    """Генерация демо-событий (3 сценария)."""
    base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Subscriber 1: нормальное движение с хендовером
    sub1 = []
    imsi1 = "250011234567890"
    for i, (cell, ta, rsrp, dt, nbrs) in enumerate([
        ('250-01-001-1A', 2, -75, 0, [{'pci': 2, 'rsrp': -95}]),
        ('250-01-001-1A', 8, -95, 30, [{'pci': 2, 'rsrp': -90}]),
        ('250-01-001-1A', 15, -108, 60, [{'pci': 2, 'rsrp': -85}]),
        ('250-01-002-1A', 3, -82, 65, []),
        ('250-01-002-1A', 5, -88, 120, [{'pci': 1, 'rsrp': -105}]),
    ]):
        sub1.append({
            'imsi': imsi1, 'cell_id': cell,
            'timestamp': (base + timedelta(seconds=dt)).isoformat(),
            'ta': ta, 'rsrp': rsrp, 'neighbors': nbrs,
            'event_type': 'HO_COMPLETE' if i == 3 else 'MEASUREMENT_REPORT',
        })

    # Subscriber 2: уход в мертвую зону
    sub2 = []
    imsi2 = "250019876543210"
    for i, (ta, rsrp, dt) in enumerate([
        (5, -85, 0), (12, -100, 20), (20, -112, 40), (28, -122, 55), (30, -128, 60),
    ]):
        sub2.append({
            'imsi': imsi2, 'cell_id': '250-01-002-2A',
            'timestamp': (base + timedelta(seconds=dt)).isoformat(),
            'ta': ta, 'rsrp': rsrp,
            'neighbors': [{'pci': 3, 'rsrp': rsrp + 4}],
            'event_type': 'RLF_INDICATION' if i == 4 else 'MEASUREMENT_REPORT',
        })

    # Subscriber 3: внезапное выключение
    sub3 = []
    imsi3 = "250015556667777"
    for ta, rsrp, dt, etype in [
        (3, -78, 0, 'MEASUREMENT_REPORT'),
        (3, -80, 10, 'MEASUREMENT_REPORT'),
        (3, -140, 15, 'UE_CONTEXT_RELEASE'),
    ]:
        sub3.append({
            'imsi': imsi3, 'cell_id': '250-01-003-1A',
            'timestamp': (base + timedelta(seconds=dt)).isoformat(),
            'ta': ta, 'rsrp': rsrp, 'neighbors': [],
            'event_type': etype,
        })

    return sub1 + sub2 + sub3


# ============================================================================
# Main
# ============================================================================
def main():
    print("=" * 60)
    print("  TELECOM RAW LOG PROCESSOR v2.0")
    print("=" * 60)

    # 1. Init pipeline
    pipeline = TelecomPipeline(salt="demo-salt-2024")

    # 2. Load sites
    print("\n[1] Loading site database...")
    n = pipeline.add_sites(generate_demo_sites())
    print(f"    Loaded {n} sectors")

    # 3. Generate & process events
    print("\n[2] Processing raw events...")
    raw = generate_demo_events()
    sessions, drops = pipeline.process(raw)

    # 4. Print stats
    s = pipeline.stats
    print(f"\n{'=' * 60}")
    print("  PIPELINE STATISTICS")
    print(f"{'=' * 60}")
    print(f"  Raw events:        {s['raw_events']}")
    print(f"  Parsed events:     {s['parsed_events']}")
    print(f"  Enriched events:   {s['enriched_events']}")
    print(f"  Sessions:          {s['sessions']}")
    print(f"  Drops detected:    {s['drops_detected']}")
    if s['unmapped_cells']:
        print(f"  Unmapped cells:    {s['unmapped_cells']}")
    if s['parse_errors']:
        print(f"  Parse errors:      {s['parse_errors']}")

    # 5. Print drop details
    print(f"\n{'=' * 60}")
    print("  DROP ANALYSIS")
    print(f"{'=' * 60}")
    for i, d in enumerate(drops, 1):
        if d.get('drop_detected'):
            print(f"\n  --- Drop #{i} ---")
            print(f"  Subscriber:  {d['subscriber_hash']}")
            print(f"  Time:        {d['session_end']}")
            print(f"  Cell:        {d['start_cell']} → {d['end_cell']}")
            print(f"  Cause:       {d['drop_cause']}")
            print(f"  Signal:      {d['signal_trend']}, final RSRP={d['final_rsrp']} dBm")
            print(f"  Distance:    final={d['final_distance_km']} km, trend={d.get('distance_trend', '?')}")
            if d.get('target_neighbors'):
                print(f"  Neighbors:   {d['target_neighbors']}")
            if d.get('drop_point'):
                print(f"  Location:    ({d['drop_point']['lat']:.6f}, {d['drop_point']['lon']:.6f})")

    # 6. Export
    print(f"\n{'=' * 60}")
    print("  EXPORT")
    print(f"{'=' * 60}")

    out = Path('output')
    out.mkdir(exist_ok=True)

    # GeoJSON
    n_geo = GeoJSONExporter.export(sessions, str(out / 'trajectories.geojson'))
    print(f"  GeoJSON: {n_geo} tracks → {out / 'trajectories.geojson'}")

    # CSV
    n_csv = CSVExporter.export_sessions(sessions, str(out / 'sessions.csv'))
    print(f"  CSV sessions: {n_csv} rows → {out / 'sessions.csv'}")

    # Drops CSV
    n_drop = CSVExporter.export_drops(drops, str(out / 'drops.csv'))
    print(f"  CSV drops: {n_drop} rows → {out / 'drops.csv'}")

    # Parquet
    n_pq = ParquetExporter.export_sessions(sessions, str(out / 'sessions.parquet'))
    print(f"  Parquet: {n_pq} rows → {out / 'sessions.parquet'}")

    # HTML Map
    HTMLMapExporter.export(sessions, str(out / 'map.html'))

    print(f"\n{'=' * 60}")
    print("  DONE. Output files in:", out.resolve())
    print(f"{'=' * 60}")

    return pipeline, sessions, drops


if __name__ == "__main__":
    main()