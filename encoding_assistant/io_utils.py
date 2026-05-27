"""File-system utilities for writing .zlt/.zlg/.zad triplets.

Copyright (c) 2026-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

import os
from dataclasses import dataclass

from encoding_assistant.emitter import emit_zlt, emit_zlg, emit_zad
from encoding_assistant.model import Encoding


INPUT_DIR = os.path.join('stations', 'input')
EXTENSIONS = ('.zlt', '.zlg', '.zad')


@dataclass
class SaveResult:
    written_paths: list
    cancelled: bool = False


def target_paths(station_lbl: str, suffix: str = '') -> list:
    return [os.path.join(INPUT_DIR, f'{station_lbl}{suffix}{ext}')
            for ext in EXTENSIONS]


def any_target_exists(station_lbl: str) -> bool:
    return any(os.path.exists(p) for p in target_paths(station_lbl))


def next_free_suffix(station_lbl: str) -> str:
    n = 1
    while True:
        suffix = f'_{n}'
        if not any(os.path.exists(p)
                   for p in target_paths(station_lbl, suffix)):
            return suffix
        n += 1


def write_triplet(encoding: Encoding, suffix: str = '') -> list:
    label = encoding.metadata['station_lbl']
    paths = target_paths(label, suffix)
    contents = (emit_zlt(encoding), emit_zlg(encoding), emit_zad(encoding))

    os.makedirs(INPUT_DIR, exist_ok=True)

    for path, content in zip(paths, contents):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    return paths
