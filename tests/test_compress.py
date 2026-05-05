import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.compress.huffman import (
    build_code_table,
    build_frequency_table,
    build_huffman_tree,
    compress_text,
    decompress_text,
)
from src.diary.diary_service import load_diary_records


def test_build_frequency_table():
    frequency_table = build_frequency_table("aaabbc")

    assert frequency_table["a"] == 3
    assert frequency_table["b"] == 2
    assert frequency_table["c"] == 1
    print("test_build_frequency_table passed.")


def test_build_code_table():
    frequency_table = build_frequency_table("aaabbc")
    tree = build_huffman_tree(frequency_table)
    code_table = build_code_table(tree)

    assert set(code_table) == {"a", "b", "c"}
    assert all(code for code in code_table.values())
    print("test_build_code_table passed.")


def test_compress_and_decompress_sample_text():
    text = "北大图书馆的自习座位很抢手，建议早点到馆。"
    payload = compress_text(text)
    restored = decompress_text(payload)

    assert restored == text
    assert payload["bit_length"] > 0
    assert payload["original_size_bytes"] > 0
    assert payload["bitstream_size_bytes"] > 0
    print("test_compress_and_decompress_sample_text passed.")


def test_compress_diary_content_roundtrip():
    records = load_diary_records()
    text = records[2]["content"]
    payload = compress_text(text)
    restored = decompress_text(payload)

    assert restored == text
    assert payload["unique_character_count"] > 1
    assert payload["estimated_package_size_bytes"] >= payload["bitstream_size_bytes"]
    print("test_compress_diary_content_roundtrip passed.")


def test_single_character_roundtrip():
    text = "哈哈哈哈哈哈"
    payload = compress_text(text)
    restored = decompress_text(payload)

    assert restored == text
    assert len(payload["code_table"]) == 1
    print("test_single_character_roundtrip passed.")


def run_all_tests():
    print("Running compression module tests...")
    test_build_frequency_table()
    test_build_code_table()
    test_compress_and_decompress_sample_text()
    test_compress_diary_content_roundtrip()
    test_single_character_roundtrip()
    print("All compression tests passed.")


if __name__ == "__main__":
    run_all_tests()
