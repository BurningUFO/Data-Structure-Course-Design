"""
成员 C：第十周哈夫曼压缩基础版

当前实现提供：
1. 字符频率统计
2. 哈夫曼树与编码表构建
3. 文本压缩与解压
4. 压缩前后体积估算，便于第十周演示

当前限制：
- 目前为内存级结构，未落地为磁盘二进制容器
- `estimated_package_size_bytes` 包含频率表的 JSON 估算大小
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Any


@dataclass(order=True)
class HuffmanNode:
    frequency: int
    order: int
    symbol: str | None = field(compare=False, default=None)
    left: "HuffmanNode | None" = field(compare=False, default=None)
    right: "HuffmanNode | None" = field(compare=False, default=None)


def build_frequency_table(text: str) -> dict[str, int]:
    if not text:
        return {}
    counter = Counter(text)
    return dict(sorted(counter.items(), key=lambda item: (item[1], item[0])))


def build_huffman_tree(frequency_table: dict[str, int]) -> HuffmanNode | None:
    if not frequency_table:
        return None

    heap: list[HuffmanNode] = []
    order = 0
    for symbol, frequency in frequency_table.items():
        heappush(heap, HuffmanNode(frequency=frequency, order=order, symbol=symbol))
        order += 1

    while len(heap) > 1:
        left = heappop(heap)
        right = heappop(heap)
        parent = HuffmanNode(
            frequency=left.frequency + right.frequency,
            order=order,
            left=left,
            right=right,
        )
        order += 1
        heappush(heap, parent)

    return heap[0]


def build_code_table(tree: HuffmanNode | None) -> dict[str, str]:
    if tree is None:
        return {}

    code_table: dict[str, str] = {}

    def traverse(node: HuffmanNode, prefix: str) -> None:
        if node.symbol is not None:
            code_table[node.symbol] = prefix or "0"
            return
        if node.left is not None:
            traverse(node.left, prefix + "0")
        if node.right is not None:
            traverse(node.right, prefix + "1")

    traverse(tree, "")
    return code_table


def encode_text(text: str, code_table: dict[str, str]) -> str:
    if not text:
        return ""
    return "".join(code_table[char] for char in text)


def pack_bits(bitstring: str) -> tuple[bytes, int]:
    if not bitstring:
        return b"", 0

    padding_bits = (8 - len(bitstring) % 8) % 8
    padded_bitstring = bitstring + ("0" * padding_bits)
    packed_bytes = bytes(
        int(padded_bitstring[index : index + 8], 2)
        for index in range(0, len(padded_bitstring), 8)
    )
    return packed_bytes, padding_bits


def unpack_bits(packed_bytes: bytes, padding_bits: int) -> str:
    if not packed_bytes:
        return ""

    bitstring = "".join(f"{byte:08b}" for byte in packed_bytes)
    if padding_bits:
        return bitstring[:-padding_bits]
    return bitstring


def estimate_frequency_table_size(frequency_table: dict[str, int]) -> int:
    serialized = json.dumps(frequency_table, ensure_ascii=False, sort_keys=True)
    return len(serialized.encode("utf-8"))


def compress_text(text: str) -> dict[str, Any]:
    frequency_table = build_frequency_table(text)
    tree = build_huffman_tree(frequency_table)
    code_table = build_code_table(tree)
    encoded_bits = encode_text(text, code_table)
    packed_bytes, padding_bits = pack_bits(encoded_bits)

    original_size_bytes = len(text.encode("utf-8"))
    bitstream_size_bytes = len(packed_bytes)
    frequency_table_size_estimate_bytes = estimate_frequency_table_size(frequency_table)
    estimated_package_size_bytes = bitstream_size_bytes + frequency_table_size_estimate_bytes

    return {
        "frequency_table": frequency_table,
        "code_table": code_table,
        "encoded_bits": encoded_bits,
        "packed_bytes": packed_bytes,
        "padding_bits": padding_bits,
        "bit_length": len(encoded_bits),
        "character_count": len(text),
        "unique_character_count": len(frequency_table),
        "original_size_bytes": original_size_bytes,
        "bitstream_size_bytes": bitstream_size_bytes,
        "frequency_table_size_estimate_bytes": frequency_table_size_estimate_bytes,
        "estimated_package_size_bytes": estimated_package_size_bytes,
        "estimated_compression_ratio": round(
            (estimated_package_size_bytes / original_size_bytes) if original_size_bytes else 0.0,
            4,
        ),
        "storage_format": "packed_bytes + frequency_table_json_estimate",
    }


def decompress_text(payload: dict[str, Any]) -> str:
    packed_bytes = payload.get("packed_bytes", b"")
    if not isinstance(packed_bytes, bytes):
        packed_bytes = bytes(packed_bytes)

    padding_bits = int(payload.get("padding_bits", 0))
    encoded_bits = payload.get("encoded_bits")
    if not isinstance(encoded_bits, str) or not encoded_bits:
        encoded_bits = unpack_bits(packed_bytes, padding_bits)

    code_table = payload.get("code_table", {})
    if not isinstance(code_table, dict) or not code_table:
        return ""

    reverse_code_table = {str(code): str(symbol) for symbol, code in code_table.items()}
    current = ""
    decoded_characters: list[str] = []

    for bit in encoded_bits:
        current += bit
        symbol = reverse_code_table.get(current)
        if symbol is None:
            continue
        decoded_characters.append(symbol)
        current = ""

    return "".join(decoded_characters)


__all__ = [
    "HuffmanNode",
    "build_frequency_table",
    "build_huffman_tree",
    "build_code_table",
    "encode_text",
    "pack_bits",
    "unpack_bits",
    "compress_text",
    "decompress_text",
]
