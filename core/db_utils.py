from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path

from django.utils import timezone

from .models import ProductionEntry


def _normalize_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_int(value):
    text = _normalize_text(value)
    if not text:
        return None
    return int(text)


def _build_source_hash(payload: dict) -> str:
    ordered_keys = [
        "schema_version",
        "timestamp",
        "cliente",
        "display",
        "numero_display",
        "maquinario",
        "processo",
        "data_producao",
        "operadores",
        "numero_operadores",
        "hora_inicio",
        "hora_fim",
        "quantidade",
        "pecas_mortas",
        "quantidade_total",
    ]
    normalized_values = []
    for key in ordered_keys:
        value = payload.get(key, "")
        if key == "timestamp" and isinstance(value, datetime):
            normalized_values.append(value.replace(tzinfo=None).isoformat(timespec="microseconds"))
        else:
            normalized_values.append(_normalize_text(value))
    raw = "||".join(normalized_values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_entry_source_hash(payload: dict) -> str:
    return _build_source_hash(payload)


def _parse_timestamp(value: str) -> datetime:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    parsed = datetime.fromisoformat(normalized)
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def build_entry_payload_from_csv_row(row: dict, *, import_key: str | None = None) -> dict:
    payload = {
        "import_key": import_key,
        "schema_version": _normalize_text(row.get("ID")),
        "timestamp": _parse_timestamp(row.get("Timestamp", "")),
        "cliente": _normalize_text(row.get("Cliente")),
        "display": _normalize_text(row.get("Display")),
        "numero_display": _normalize_text(row.get("Numero Display")),
        "maquinario": _normalize_text(row.get("Maquinário") or row.get("MaquinÃ¡rio")),
        "processo": _normalize_text(row.get("Processo")),
        "data_producao": _normalize_text(row.get("Data")),
        "operadores": _normalize_text(row.get("Operadores")),
        "numero_operadores": _normalize_int(row.get("Numero Operadores")),
        "hora_inicio": _normalize_text(row.get("Hora Início") or row.get("Hora InÃ­cio")),
        "hora_fim": _normalize_text(row.get("Hora Fim")),
        "quantidade": _normalize_int(row.get("Quantidade")) or 0,
        "pecas_mortas": _normalize_int(row.get("Peças Mortas") or row.get("PeÃ§as Mortas")) or 0,
        "quantidade_total": _normalize_int(row.get("Quantidade Total")) or 0,
    }
    payload["source_hash"] = _build_source_hash(payload)
    return payload


def build_entry_payload_from_streamlit(payload: dict, *, schema_version: str, timestamp: datetime) -> dict:
    entry_payload = {
        "schema_version": schema_version,
        "timestamp": timestamp,
        "cliente": _normalize_text(payload.get("cliente")),
        "display": _normalize_text(payload.get("acabado")),
        "numero_display": _normalize_text(payload.get("numero_display")),
        "maquinario": _normalize_text(payload.get("ferramental")),
        "processo": _normalize_text(payload.get("processo")),
        "data_producao": _normalize_text(payload.get("data_producao")),
        "operadores": _normalize_text(payload.get("operadores")),
        "numero_operadores": _normalize_int(payload.get("numero_operadores")),
        "hora_inicio": _normalize_text(payload.get("hora_iniciada")),
        "hora_fim": _normalize_text(payload.get("hora_finalizada")),
        "quantidade": _normalize_int(payload.get("quantidade_produzida")) or 0,
        "pecas_mortas": _normalize_int(payload.get("pecas_mortas")) or 0,
        "quantidade_total": _normalize_int(payload.get("quantidade_total")) or 0,
    }
    entry_payload["source_hash"] = _build_source_hash(entry_payload)
    return entry_payload


def save_streamlit_entry(payload: dict, *, schema_version: str) -> ProductionEntry:
    timestamp = timezone.now()
    entry_payload = build_entry_payload_from_streamlit(
        payload,
        schema_version=schema_version,
        timestamp=timestamp,
    )
    return ProductionEntry.objects.create(**entry_payload)


def update_production_entry(entry: ProductionEntry, payload: dict) -> ProductionEntry:
    fields = [
        "schema_version",
        "timestamp",
        "cliente",
        "display",
        "numero_display",
        "maquinario",
        "processo",
        "data_producao",
        "operadores",
        "numero_operadores",
        "hora_inicio",
        "hora_fim",
        "quantidade",
        "pecas_mortas",
        "quantidade_total",
    ]
    for field in fields:
        setattr(entry, field, payload.get(field))
    entry.source_hash = compute_entry_source_hash(payload)
    entry.save(update_fields=fields + ["source_hash"])
    return entry


def import_csv_to_database(csv_path: Path) -> tuple[int, int]:
    created = 0
    skipped = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_number, row in enumerate(reader, start=2):
            if not any(_normalize_text(value) for value in row.values()):
                skipped += 1
                continue
            import_key = f"{csv_path.resolve()}::{row_number}"
            payload = build_entry_payload_from_csv_row(row, import_key=import_key)
            _, was_created = ProductionEntry.objects.get_or_create(
                import_key=import_key,
                defaults=payload,
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    return created, skipped
