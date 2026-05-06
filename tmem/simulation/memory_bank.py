"""Synthetic LoCoMo-style memory bank (~30 notes, 10 sessions).

Per A-MEM (Xu et al., Sec. 3.1), keywords, tags, and contextual sentences would
normally come from an LLM; here they are **authored in data** so the pipeline
runs without API keys while preserving the same *fields* as the paper.

Links use cosine similarity above a threshold on note embeddings (A-MEM
Sec. 3.2 uses an LLM over top‑k cosine neighbors; this is a deterministic
approximation of that step).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

import numpy as np

from tmem.config import TMemConfig
from tmem.memory_note import MemoryNote
from tmem.retrieval import cosine_similarities


def _dt(day_offset: int, hour: int = 10) -> datetime:
    """Anchored synthetic timeline: base Jan 5, 2025 + day_offset."""
    base = datetime(2025, 1, 5, hour, 0, 0)
    from datetime import timedelta

    return base + timedelta(days=day_offset)


# Session day offsets (spread over ~4 months)
_SESSION_DAYS = [0, 15, 32, 50, 67, 85, 92, 98, 108, 125]


def _session_ts(session_idx: int) -> datetime:
    """session_idx in 1..10"""
    return _dt(_SESSION_DAYS[session_idx - 1])


def raw_note_specs() -> List[dict]:
    """Structured content for 30 memories (3 per session × 10 sessions)."""
    s = _session_ts
    return [
        # Session 1
        {
            "id": "s01_n1",
            "session": 1,
            "timestamp": s(1),
            "content": "Bob told Alice he loved dinner at Trattoria Roma on Mulberry Street and recommended the osso buco.",
            "keywords": ["Bob", "restaurant", "Trattoria Roma", "Mulberry", "recommendation"],
            "tags": ["food", "social", "session1"],
            "context": "Bob shares a one-off Italian restaurant recommendation with Alice.",
            "access_count": 0,
        },
        {
            "id": "s01_n2",
            "session": 1,
            "timestamp": s(1),
            "content": "Alice said she currently lives in a walk-up in Brooklyn and spends weekends at NYC museums while mostly working remotely.",
            "keywords": ["Alice", "Brooklyn", "NYC", "currently", "apartment", "museums"],
            "tags": ["housing", "location", "session1"],
            "context": "Alice describes currently living in New York City (later contradicted by Seattle move).",
            "access_count": 2,
        },
        {
            "id": "s01_n3",
            "session": 1,
            "timestamp": s(1),
            "content": "Light small talk about rainy January weather and commuting on the subway.",
            "keywords": ["weather", "subway", "January"],
            "tags": ["chitchat", "session1"],
            "context": "Casual weather and transit conversation.",
            "access_count": 1,
        },
        # Session 2 — Google job
        {
            "id": "s02_n1",
            "session": 2,
            "timestamp": s(2),
            "content": "Alice said she is currently a software engineer at Google on the Search ranking team and works from the Mountain View office most days.",
            "keywords": ["Alice", "Google", "currently", "software engineer", "Search", "work"],
            "tags": ["career", "employment", "session2"],
            "context": "Alice is described as currently working at Google (superseded by later career change).",
            "access_count": 1,
        },
        {
            "id": "s02_n2",
            "session": 2,
            "timestamp": s(2),
            "content": "Alice and Bob discussed onboarding paperwork and badge pickup at the Google campus.",
            "keywords": ["onboarding", "Google", "badge"],
            "tags": ["career", "logistics", "session2"],
            "context": "Logistics around starting at Google.",
            "access_count": 0,
        },
        {
            "id": "s02_n3",
            "session": 2,
            "timestamp": s(2),
            "content": "Alice complained about long Caltrain commutes from the city to Mountain View.",
            "keywords": ["Caltrain", "commute", "Mountain View"],
            "tags": ["transit", "session2"],
            "context": "Commute details while at Google.",
            "access_count": 0,
        },
        # Session 3 — photography begins
        {
            "id": "s03_n1",
            "session": 3,
            "timestamp": s(3),
            "content": "Alice bought a Sony A7IV mirrorless camera and a 35mm prime lens to start a serious weekend photography hobby.",
            "keywords": ["Sony", "A7IV", "camera", "photography", "35mm"],
            "tags": ["hobby", "gear", "session3"],
            "context": "Alice acquires a Sony A7IV for photography.",
            "access_count": 25,
        },
        {
            "id": "s03_n2",
            "session": 3,
            "timestamp": s(3),
            "content": "Weekend hike at Rancho San Antonio; Alice brought the new camera but forgot extra batteries.",
            "keywords": ["hike", "Rancho San Antonio", "batteries"],
            "tags": ["outdoors", "session3"],
            "context": "Outdoor hike with new camera gear.",
            "access_count": 3,
        },
        {
            "id": "s03_n3",
            "session": 3,
            "timestamp": s(3),
            "content": "Discussion of RAW vs JPEG for editing landscapes in Lightroom.",
            "keywords": ["RAW", "JPEG", "Lightroom", "editing"],
            "tags": ["photography", "software", "session3"],
            "context": "Photo editing workflow preferences.",
            "access_count": 8,
        },
        # Session 4 — old phone
        {
            "id": "s04_n1",
            "session": 4,
            "timestamp": s(4),
            "content": "Alice shared her cell number 555-0100 so Bob could add her to a group chat about trivia night.",
            "keywords": ["phone", "555-0100", "trivia", "group chat"],
            "tags": ["contact", "session4"],
            "context": "Older phone number for Alice (later superseded).",
            "access_count": 1,
        },
        {
            "id": "s04_n2",
            "session": 4,
            "timestamp": s(4),
            "content": "Alice attended a NeurIPS meetup in the city and chatted about retrieval-augmented generation trends.",
            "keywords": ["NeurIPS", "RAG", "meetup"],
            "tags": ["ML", "session4"],
            "context": "Academic social event.",
            "access_count": 0,
        },
        {
            "id": "s04_n3",
            "session": 4,
            "timestamp": s(4),
            "content": "Bob recommended a novel about lunar colonies; Alice added it to her reading list.",
            "keywords": ["novel", "reading", "lunar"],
            "tags": ["books", "session4"],
            "context": "Book recommendation.",
            "access_count": 0,
        },
        # Session 5 — photography continues
        {
            "id": "s05_n1",
            "session": 5,
            "timestamp": s(5),
            "content": "Alice visited SFMOMA alone with her camera and spent two hours photographing geometric shadows in the lobby.",
            "keywords": ["SFMOMA", "photography", "museum", "shadows"],
            "tags": ["hobby", "art", "session5"],
            "context": "Alice practices photography at SFMOMA.",
            "access_count": 28,
        },
        {
            "id": "s05_n2",
            "session": 5,
            "timestamp": s(5),
            "content": "Bob asked Alice for tips on buying a used film camera on eBay.",
            "keywords": ["film camera", "eBay", "used gear"],
            "tags": ["photography", "shopping", "session5"],
            "context": "Photography gear shopping advice.",
            "access_count": 4,
        },
        {
            "id": "s05_n3",
            "session": 5,
            "timestamp": s(5),
            "content": "They planned a Saturday coffee at Blue Bottle near the waterfront.",
            "keywords": ["coffee", "Blue Bottle", "weekend"],
            "tags": ["social", "session5"],
            "context": "Casual meetup planning.",
            "access_count": 1,
        },
        # Session 6 — Japan planning
        {
            "id": "s06_n1",
            "session": 6,
            "timestamp": s(6),
            "content": "Alice and Bob agreed to plan a two-week spring trip to Japan focusing on Tokyo food alleys and Kyoto temples.",
            "keywords": ["Japan", "Tokyo", "Kyoto", "trip", "Bob", "Alice"],
            "tags": ["travel", "planning", "session6"],
            "context": "Alice and Bob plan a Japan trip together.",
            "access_count": 6,
        },
        {
            "id": "s06_n2",
            "session": 6,
            "timestamp": s(6),
            "content": "They compared flight prices on Google Flights and discussed flying into Haneda.",
            "keywords": ["flights", "Haneda", "Google Flights"],
            "tags": ["travel", "logistics", "session6"],
            "context": "Flight planning for Japan.",
            "access_count": 2,
        },
        {
            "id": "s06_n3",
            "session": 6,
            "timestamp": s(6),
            "content": "Bob said he wants to try okonomiyaki in Osaka if time permits.",
            "keywords": ["Osaka", "okonomiyaki", "food"],
            "tags": ["travel", "food", "session6"],
            "context": "Food preferences for Japan itinerary.",
            "access_count": 1,
        },
        # Session 7 — Japan follow-up
        {
            "id": "s07_n1",
            "session": 7,
            "timestamp": s(7),
            "content": "Alice booked a ryokan in Gion and a JR Pass; Bob confirmed he will share the Kyoto leg of the itinerary spreadsheet.",
            "keywords": ["ryokan", "Gion", "JR Pass", "Kyoto", "Japan"],
            "tags": ["travel", "lodging", "session7"],
            "context": "Concrete bookings for the Japan trip with Bob.",
            "access_count": 7,
        },
        {
            "id": "s07_n2",
            "session": 7,
            "timestamp": s(7),
            "content": "They debated pocket WiFi vs eSIM for data roaming in Japan.",
            "keywords": ["pocket WiFi", "eSIM", "roaming", "Japan"],
            "tags": ["travel", "tech", "session7"],
            "context": "Connectivity planning for Japan travel.",
            "access_count": 1,
        },
        {
            "id": "s07_n3",
            "session": 7,
            "timestamp": s(7),
            "content": "Bob mentioned his sister loved the teamLab exhibit in Tokyo and might join for a day.",
            "keywords": ["teamLab", "Tokyo", "exhibit"],
            "tags": ["travel", "art", "session7"],
            "context": "Optional Tokyo activities for Japan trip.",
            "access_count": 2,
        },
        # Session 8 — Meta switch
        {
            "id": "s08_n1",
            "session": 8,
            "timestamp": s(8),
            "content": "Alice told Bob she resigned from Google; she is currently a senior engineer at Meta on Ads ranking infrastructure in Menlo Park.",
            "keywords": ["Alice", "Meta", "Google", "currently", "engineer", "Ads", "work"],
            "tags": ["career", "employment", "session8"],
            "context": "Alice leaves Google and currently works at Meta.",
            "access_count": 5,
        },
        {
            "id": "s08_n2",
            "session": 8,
            "timestamp": s(8),
            "content": "Alice described Meta onboarding swag and a confusing internal wiki search tool.",
            "keywords": ["Meta", "onboarding", "wiki"],
            "tags": ["work", "session8"],
            "context": "Meta workplace details.",
            "access_count": 1,
        },
        {
            "id": "s08_n3",
            "session": 8,
            "timestamp": s(8),
            "content": "Bob joked that Alice collects big-tech lanyards like Pokémon badges.",
            "keywords": ["lanyards", "humor", "big tech"],
            "tags": ["social", "session8"],
            "context": "Playful comment about job changes.",
            "access_count": 0,
        },
        # Session 9 — Seattle move
        {
            "id": "s09_n1",
            "session": 9,
            "timestamp": s(9),
            "content": "Alice moved from NYC; she currently rents on Capitol Hill in Seattle near Meta's Seattle office and hikes on weekends.",
            "keywords": ["Seattle", "Capitol Hill", "NYC", "currently", "Meta", "moved", "hiking"],
            "tags": ["relocation", "housing", "session9"],
            "context": "Alice now lives in Seattle after leaving New York.",
            "access_count": 6,
        },
        {
            "id": "s09_n2",
            "session": 9,
            "timestamp": s(9),
            "content": "Alice photographed fog over Elliott Bay at sunrise with her usual Sony kit.",
            "keywords": ["Elliott Bay", "photography", "Sony", "Seattle", "sunrise"],
            "tags": ["hobby", "session9"],
            "context": "Photography practice in Seattle after relocation.",
            "access_count": 30,
        },
        {
            "id": "s09_n3",
            "session": 9,
            "timestamp": s(9),
            "content": "Alice filed a USPS change-of-address from Brooklyn to Seattle.",
            "keywords": ["USPS", "change of address", "Brooklyn", "Seattle"],
            "tags": ["logistics", "session9"],
            "context": "Official address change supporting Seattle move.",
            "access_count": 2,
        },
        # Session 10 — new phone + hobby reinforcement
        {
            "id": "s10_n1",
            "session": 10,
            "timestamp": s(10),
            "content": "Alice gave Bob her updated cell number 555-0199 after switching carriers for better Seattle coverage.",
            "keywords": ["phone", "555-0199", "carrier", "Seattle"],
            "tags": ["contact", "session10"],
            "context": "Current phone number for Alice.",
            "access_count": 3,
        },
        {
            "id": "s10_n2",
            "session": 10,
            "timestamp": s(10),
            "content": "Since relocating to Seattle, Alice picked up street photography walks through Capitol Hill every Sunday with the same Sony A7IV setup.",
            "keywords": ["Seattle", "street photography", "Capitol Hill", "Sunday", "Sony", "A7IV"],
            "tags": ["hobby", "post-move", "session10"],
            "context": "Photography hobby continued and emphasized after Seattle move.",
            "access_count": 22,
        },
        {
            "id": "s10_n3",
            "session": 10,
            "timestamp": s(10),
            "content": "Alice said Meta's Seattle office has good espresso and fewer meetings than her old Google schedule.",
            "keywords": ["Meta", "Seattle office", "espresso", "Google"],
            "tags": ["work", "session10"],
            "context": "Comparison of Meta Seattle vs past Google experience.",
            "access_count": 2,
        },
    ]


def specs_to_notes(specs: List[dict]) -> List[MemoryNote]:
    notes: List[MemoryNote] = []
    for sp in specs:
        notes.append(
            MemoryNote(
                id=sp["id"],
                content=sp["content"],
                timestamp=sp["timestamp"],
                keywords=list(sp["keywords"]),
                tags=list(sp["tags"]),
                context=sp["context"],
                links=[],
                access_count=int(sp.get("access_count", 0)),
                last_accessed=sp["timestamp"],
            )
        )
    return notes


def add_cosine_links(notes: List[MemoryNote], cfg: TMemConfig) -> None:
    """Bidirectional links when cosine similarity between embeddings exceeds threshold."""
    if len(notes) < 2:
        return
    embs = np.stack([n.embedding for n in notes], axis=0)
    # pairwise cosine
    norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-12
    nmat = embs / norms
    sim = nmat @ nmat.T
    ids = [n.id for n in notes]
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            if sim[i, j] > cfg.auto_link_cosine_threshold:
                if ids[j] not in notes[i].links:
                    notes[i].links.append(ids[j])
                if ids[i] not in notes[j].links:
                    notes[j].links.append(ids[i])


def encode_notes(model, notes: List[MemoryNote]) -> None:
    """Set ``embedding`` from f_enc(concat(c_i, K_i, G_i, X_i)) per A-MEM paper."""
    texts = [n.embedding_input_text() for n in notes]
    vecs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    for n, row in zip(notes, vecs):
        n.embedding = np.asarray(row, dtype=np.float32)


def build_memory_bank(
    model,
    cfg: TMemConfig,
) -> Tuple[List[MemoryNote], datetime]:
    """Return notes with embeddings, links, and simulated ``t_current``."""
    specs = raw_note_specs()
    notes = specs_to_notes(specs)
    encode_notes(model, notes)
    add_cosine_links(notes, cfg)
    # "Now" is after the last session so every note has nonnegative age.
    t_current = datetime(2025, 6, 10, 12, 0, 0)
    return notes, t_current
