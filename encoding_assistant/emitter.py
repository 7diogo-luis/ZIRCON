"""Emit .zlt, .zlg and .zad file contents from an Encoding model.

Copyright (c) 2026-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from encoding_assistant.model import (Block, Ndz, Section, Signal, Encoding)


def emit_zlt(encoding: Encoding) -> str:
    lines = []

    for element in encoding.elements:
        if isinstance(element, Block):
            lines.append(f'BLK {element.label}')
            if element.signal is not None:
                lines.append('\t' + _signal_zlt_line(element.signal))

        elif isinstance(element, Ndz):
            lines.append(f'NDZ {element.label}')
            if element.signal is not None:
                lines.append('\t' + _signal_zlt_line(element.signal))

        elif isinstance(element, Section):
            line = f'SEC {element.label}'
            if element.tjd:
                line += ' TJD'
            if element.ndz_flag:
                line += ' NDZ'
            lines.append(line)
            sorted_nodes = sorted(element.nodes, key=lambda n: n.index)
            for node in sorted_nodes:
                lines.append('\t' + _node_zlt_line(node))
                if node.signal is not None:
                    lines.append('\t\t' + _signal_zlt_line(node.signal))
                for switch in node.switches:
                    lines.append(f'\t\tSWI {switch.label}')

    return '\n'.join(lines) + '\n'


def _signal_zlt_line(signal: Signal) -> str:
    keyword = 'SWP' if signal.pedal else 'SIG'
    line = f'{keyword} {signal.label}'
    if signal.rw_only:
        line += ' *'
    return line


def _node_zlt_line(node) -> str:
    has_con = bool(node.con_ele.strip())
    if has_con and node.tjs_weak:
        return f'NDE {node.index} {node.con_ele} -'
    if has_con and not node.tjs_weak:
        return f'NDE {node.index} {node.con_ele}'
    if not has_con and node.tjs_weak:
        return f'NDE {node.index} -'
    return f'NDE {node.index}'


def emit_zlg(encoding: Encoding) -> str:
    lines = ['SECS']

    for element in encoding.elements:
        if isinstance(element, Section):
            sorted_nodes = sorted(element.nodes, key=lambda n: n.index)
            pks = ' '.join(node.pk for node in sorted_nodes)
            lines.append(f'\t{element.label} {pks}')

    lines.append('SWIS')
    seen_switch_labels = set()
    for element in encoding.elements:
        if not isinstance(element, Section):
            continue
        sorted_nodes = sorted(element.nodes, key=lambda n: n.index)
        for node in sorted_nodes:
            for switch in node.switches:
                if switch.label in seen_switch_labels:
                    continue
                seen_switch_labels.add(switch.label)
                line = f'\t{switch.label} {switch.point_pk}'
                if switch.lr_pk.strip():
                    line += f' {switch.lr_pk}'
                lines.append(line)

    lines.append('SIGS')
    seen_signal_labels = set()
    for element in encoding.elements:
        if isinstance(element, (Block, Ndz)) and element.signal is not None:
            expanded = _expanded_signal_label(element.signal, element.label)
            if expanded not in seen_signal_labels:
                seen_signal_labels.add(expanded)
                lines.append('\t' + _signal_zlg_line(element.signal,
                                                     element.label))
        elif isinstance(element, Section):
            sorted_nodes = sorted(element.nodes, key=lambda n: n.index)
            for node in sorted_nodes:
                if node.signal is None:
                    continue
                expanded = _expanded_signal_label(node.signal, element.label)
                if expanded in seen_signal_labels:
                    continue
                seen_signal_labels.add(expanded)
                lines.append('\t' + _signal_zlg_line(node.signal,
                                                     element.label))

    return '\n'.join(lines) + '\n'


def _expanded_signal_label(signal: Signal, parent_label: str) -> str:
    return (f'M_{parent_label}' if signal.label.strip() == 'M'
            else signal.label)


def _signal_zlg_line(signal: Signal, parent_label: str) -> str:
    label = _expanded_signal_label(signal, parent_label)
    line = f'{label} {signal.pole_pk}'
    if signal.zap_origin_pk.strip() and signal.zap_sft_fac.strip():
        line += f' {signal.zap_origin_pk} {signal.zap_sft_fac}'
    return line


def emit_zad(encoding: Encoding) -> str:
    keys = ('station_name', 'station_lbl', 'interlocking_name',
            'encoding_author', 'date')
    return '\n'.join(f'{k} {encoding.metadata[k]}' for k in keys) + '\n'
