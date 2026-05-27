"""In-memory model for an in-progress ZIRCON station encoding.

Copyright (c) 2026-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class Signal:
    label: str = ''
    pedal: bool = False
    rw_only: bool = False
    pole_pk: str = ''
    zap_origin_pk: str = ''
    zap_sft_fac: str = ''


@dataclass
class Switch:
    label: str = ''
    point_pk: str = ''
    lr_pk: str = ''


@dataclass
class Node:
    index: str = 'A'
    con_ele: str = ''
    pk: str = ''
    tjs_weak: bool = False
    signal: Optional[Signal] = None
    switches: list = field(default_factory=list)


@dataclass
class Block:
    label: str = ''
    signal: Optional[Signal] = None


@dataclass
class Ndz:
    label: str = ''
    signal: Optional[Signal] = None


@dataclass
class Section:
    label: str = ''
    tjd: bool = False
    ndz_flag: bool = False
    nodes: list = field(default_factory=list)


Element = Union[Block, Ndz, Section]


@dataclass
class Encoding:
    metadata: dict = field(default_factory=lambda: {
        'station_name': '',
        'station_lbl': '',
        'interlocking_name': '',
        'encoding_author': '',
        'date': '',
    })
    elements: list = field(default_factory=list)


def next_free_node_index(section: Section) -> str:
    used = {node.index for node in section.nodes}
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if letter not in used:
            return letter
    return 'A'


def parent_label_of_signal(encoding: Encoding, signal: Signal) -> Optional[str]:
    for element in encoding.elements:
        if isinstance(element, (Block, Ndz)) and element.signal is signal:
            return element.label
        if isinstance(element, Section):
            for node in element.nodes:
                if node.signal is signal:
                    return element.label
    return None
