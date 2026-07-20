from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord
from app.services.analysis_service import (
    get_evidence_records,
    normalize_phone_number,
)


def _empty_relation(first_seen: datetime | None) -> dict[str, Any]:
    return {
        "total_records": 0,
        "total_calls": 0,
        "total_sms": 0,
        "total_duration_seconds": 0,
        "first_contact": first_seen,
        "last_contact": first_seen,
        "a_to_b_records": 0,
        "b_to_a_records": 0,
    }


def _empty_number_totals() -> dict[str, Any]:
    return {
        "total_records": 0,
        "outgoing_records": 0,
        "incoming_records": 0,
        "call_records": 0,
        "sms_records": 0,
        "total_duration_seconds": 0,
        "first_activity": None,
        "last_activity": None,
    }


def _pair_key(number_a: str, number_b: str) -> tuple[str, str]:
    return tuple(sorted((number_a, number_b)))


def _event_kind(record: CDRRecord) -> str:
    event_type = str(record.event_type or "").strip().lower()

    if event_type == "sms":
        return "sms"

    if event_type == "call":
        return "call"

    connection_type = str(
        getattr(record, "connection_type", "") or ""
    ).strip().lower()

    call_type = str(
        getattr(record, "call_type", "") or ""
    ).strip().lower()

    if "sms" in connection_type or "sms" in call_type:
        return "sms"

    return "call"


def _update_time_range(
    item: dict[str, Any],
    timestamp: datetime | None,
    first_key: str,
    last_key: str,
) -> None:
    if timestamp is None:
        return

    first_value = item[first_key]
    last_value = item[last_key]

    if first_value is None or timestamp < first_value:
        item[first_key] = timestamp

    if last_value is None or timestamp > last_value:
        item[last_key] = timestamp


def _connected_component_count(
    adjacency: dict[str, set[str]],
    nodes: set[str],
) -> int:
    visited: set[str] = set()
    component_count = 0

    for start in nodes:
        if start in visited:
            continue

        component_count += 1
        stack = [start]
        visited.add(start)

        while stack:
            current = stack.pop()

            for neighbour in adjacency.get(current, set()):
                if neighbour in visited:
                    continue

                visited.add(neighbour)
                stack.append(neighbour)

    return component_count


def _articulation_points(
    adjacency: dict[str, set[str]],
    nodes: set[str],
) -> set[str]:
    """Returns bridge-like articulation numbers in an undirected graph."""

    discovery: dict[str, int] = {}
    low: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    points: set[str] = set()
    counter = 0

    def visit(number: str) -> None:
        nonlocal counter

        discovery[number] = counter
        low[number] = counter
        counter += 1
        child_count = 0

        for neighbour in adjacency.get(number, set()):
            if neighbour not in discovery:
                parent[neighbour] = number
                child_count += 1
                visit(neighbour)
                low[number] = min(low[number], low[neighbour])

                if parent.get(number) is None and child_count > 1:
                    points.add(number)

                if (
                    parent.get(number) is not None
                    and low[neighbour] >= discovery[number]
                ):
                    points.add(number)

            elif neighbour != parent.get(number):
                low[number] = min(low[number], discovery[neighbour])

    for number in nodes:
        if number in discovery:
            continue

        parent[number] = None
        visit(number)

    return points


def build_contact_network(
    database: Session,
    case_id: int,
    evidence_id: int,
    selected_number: str,
) -> dict[str, Any]:
    """
    Builds one complete communication graph from every valid caller/receiver
    relationship in the selected evidence file.

    The selected number is used only for highlighting and opening its details.
    It does not limit graph traversal and no Level 1, Level 2 or Level 3 rule is
    applied. Every returned edge is backed by one or more CDR rows.
    """

    cleaned_selected_number = normalize_phone_number(selected_number)

    if not cleaned_selected_number:
        raise ValueError("Selected phone number is required.")

    records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    relations: dict[tuple[str, str], dict[str, Any]] = {}
    adjacency: dict[str, set[str]] = defaultdict(set)
    number_totals: dict[str, dict[str, Any]] = defaultdict(
        _empty_number_totals
    )
    graph_numbers: set[str] = set()
    valid_record_count = 0

    for record in records:
        caller = normalize_phone_number(record.caller_number)
        receiver = normalize_phone_number(record.receiver_number)

        if not caller or not receiver or caller == receiver:
            continue

        valid_record_count += 1
        graph_numbers.add(caller)
        graph_numbers.add(receiver)

        event_kind = _event_kind(record)
        duration = max(0, int(record.duration_seconds or 0))
        timestamp = record.start_datetime

        caller_totals = number_totals[caller]
        receiver_totals = number_totals[receiver]

        for totals in (caller_totals, receiver_totals):
            totals["total_records"] += 1
            totals["total_duration_seconds"] += duration

            if event_kind == "sms":
                totals["sms_records"] += 1
            else:
                totals["call_records"] += 1

            _update_time_range(
                totals,
                timestamp,
                "first_activity",
                "last_activity",
            )

        caller_totals["outgoing_records"] += 1
        receiver_totals["incoming_records"] += 1

        pair = _pair_key(caller, receiver)
        number_a, number_b = pair

        if pair not in relations:
            relations[pair] = _empty_relation(timestamp)

        relation = relations[pair]
        relation["total_records"] += 1
        relation["total_duration_seconds"] += duration

        if event_kind == "sms":
            relation["total_sms"] += 1
        else:
            relation["total_calls"] += 1

        if caller == number_a and receiver == number_b:
            relation["a_to_b_records"] += 1
        else:
            relation["b_to_a_records"] += 1

        _update_time_range(
            relation,
            timestamp,
            "first_contact",
            "last_contact",
        )

        adjacency[caller].add(receiver)
        adjacency[receiver].add(caller)

    articulation_numbers = _articulation_points(
        adjacency=adjacency,
        nodes=graph_numbers,
    )

    degrees = sorted(
        len(adjacency.get(number, set()))
        for number in graph_numbers
        if adjacency.get(number)
    )

    if degrees:
        percentile_index = min(
            len(degrees) - 1,
            int((len(degrees) - 1) * 0.85),
        )
        hub_degree_threshold = max(4, degrees[percentile_index])
    else:
        hub_degree_threshold = 4

    graph_edges: list[dict[str, Any]] = []
    weighted_degree: dict[str, int] = defaultdict(int)

    for (number_a, number_b), relation in relations.items():
        weighted_degree[number_a] += relation["total_records"]
        weighted_degree[number_b] += relation["total_records"]

        graph_edges.append(
            {
                "source": number_a,
                "target": number_b,
                "total_records": relation["total_records"],
                "total_calls": relation["total_calls"],
                "total_sms": relation["total_sms"],
                "total_duration_seconds": relation[
                    "total_duration_seconds"
                ],
                "source_to_target_records": relation["a_to_b_records"],
                "target_to_source_records": relation["b_to_a_records"],
                "first_contact": relation["first_contact"],
                "last_contact": relation["last_contact"],
            }
        )

    graph_nodes: list[dict[str, Any]] = []

    for number in graph_numbers:
        totals = number_totals[number]
        contact_count = len(adjacency.get(number, set()))

        graph_nodes.append(
            {
                "phone_number": number,
                "is_selected": number == cleaned_selected_number,
                "total_records": totals["total_records"],
                "outgoing_records": totals["outgoing_records"],
                "incoming_records": totals["incoming_records"],
                "call_records": totals["call_records"],
                "sms_records": totals["sms_records"],
                "total_duration_seconds": totals[
                    "total_duration_seconds"
                ],
                "contact_count": contact_count,
                "weighted_degree": weighted_degree[number],
                "first_activity": totals["first_activity"],
                "last_activity": totals["last_activity"],
                "is_hub": (
                    contact_count >= hub_degree_threshold
                    and contact_count >= 3
                ),
                "is_bridge": number in articulation_numbers,
            }
        )

    graph_nodes.sort(
        key=lambda node: (
            0 if node["is_selected"] else 1,
            -node["weighted_degree"],
            -node["contact_count"],
            node["phone_number"],
        )
    )

    graph_edges.sort(
        key=lambda edge: (
            -edge["total_records"],
            edge["source"],
            edge["target"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "selected_number": cleaned_selected_number,
        "selected_number_found": (
            cleaned_selected_number in graph_numbers
        ),
        "node_count": len(graph_nodes),
        "edge_count": len(graph_edges),
        "total_records_used": valid_record_count,
        "connected_component_count": _connected_component_count(
            adjacency=adjacency,
            nodes=graph_numbers,
        ),
        "nodes": graph_nodes,
        "edges": graph_edges,
    }