"""Validators and duplicate-label scanner for the encoding model.

Copyright (c) 2026-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from encoding_assistant.model import Block, Ndz, Section, Encoding


def is_numeric(text: str) -> bool:
    if not text.strip():
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


def is_optional_numeric(text: str) -> bool:
    return not text.strip() or is_numeric(text)


def zap_pair_valid(zap_origin: str, zap_sft_fac: str) -> bool:
    both_empty = not zap_origin.strip() and not zap_sft_fac.strip()
    both_numeric = is_numeric(zap_origin) and is_numeric(zap_sft_fac)
    return both_empty or both_numeric


def section_odd_no_switch(section: Section) -> bool:
    """True if the section has an odd node count >= 3 and no real switch.

    Derailers (Switch with empty lr_pk) do not count. 1-node terminals are
    excluded because the cross/turnout rule does not apply to stubs.
    """
    n = len(section.nodes)
    if n < 3 or n % 2 == 0:
        return False
    return not any(
        sw.lr_pk.strip()
        for node in section.nodes
        for sw in node.switches
    )


def duplicate_labels(encoding: Encoding) -> list:
    counts = {}

    def bump(label: str, category: str):
        if not label:
            return
        key = (category, label)
        counts[key] = counts.get(key, 0) + 1

    element_labels = []
    signal_labels = []
    switch_labels = []

    for element in encoding.elements:
        if isinstance(element, (Block, Ndz)):
            element_labels.append(element.label)
            if element.signal is not None:
                _collect_signal_for_dup_scan(element.signal,
                                             element.label,
                                             signal_labels)
        elif isinstance(element, Section):
            element_labels.append(element.label)
            for node in element.nodes:
                if node.signal is not None:
                    _collect_signal_for_dup_scan(node.signal,
                                                 element.label,
                                                 signal_labels)
                for switch in node.switches:
                    switch_labels.append(switch.label)

    for lbl in element_labels:
        bump(lbl, 'element')
    for lbl in signal_labels:
        bump(lbl, 'signal')
    for lbl in switch_labels:
        bump(lbl, 'switch')

    duplicates = []
    for (category, label), count in counts.items():
        if count > 1:
            duplicates.append((category, label, count))
    duplicates.sort()
    return duplicates


def _collect_signal_for_dup_scan(signal, parent_label: str, bucket: list):
    label = signal.label.strip()
    if label == 'M':
        bucket.append(f'M_{parent_label}')
    else:
        bucket.append(label)
