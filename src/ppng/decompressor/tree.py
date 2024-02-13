from typing import Self
from toolz import pipe

class Node:
    def __init__(self, symbol: int | None, left: Self = None, right: Self = None) -> None:
        self.symbol = symbol
        self.left = left
        self.right = right

    def __str__(self) -> str:
        return f"symbol: {self.symbol}, left: {self.left}, right: {self.right}"

    def is_leaf(self) -> bool:
        return (self.left is None) and (self.right is None)

class HuffmanTree:
    def __init__(self) -> None:
        self.root = Node(None)

    def insert(self, symbol: int | None, huffman_code: int, huffman_code_length: int) -> None:
        current_node = self.root
        for bit in bin(huffman_code)[2:].zfill(huffman_code_length):
            if bit == '0':
                if current_node.left is None:
                    # Create a intermediate (maybe leaf) node
                    current_node.left = Node(None)
                current_node = current_node.left
            else:
                if current_node.right is None:
                    # Create a intermediate (maybe leaf) node
                    current_node.right = Node(None)
                current_node = current_node.right
        # Set the symbol to the leaf node
        current_node.symbol = symbol

    def search(self, huffman_code: int, huffman_code_length: int) -> int | None:
        current_node = self.root
        for bit in bin(huffman_code)[2:].zfill(huffman_code_length):
            if bit == '0':
                if current_node.left is None:
                    return None
                current_node = current_node.left
            else:
                if current_node.right is None:
                    return None
                current_node = current_node.right
        return current_node.symbol

    def print(self) -> None:
        def print_tree(node: Node, start_depth: int) -> None:
            if node is not None:
                print_tree(node.right, start_depth + 1)
                print(f'{" " * 4 * start_depth} -> [{node.symbol}]')
                print_tree(node.left, start_depth + 1)
        print_tree(self.root, 0)

    def get_symbol_code_table(self) -> dict[int, str]:
        symbol_code_table = {}
        def get_symbol_code(node: Node, code: str) -> None:
            if node is not None:
                if node.is_leaf():
                    symbol_code_table[node.symbol] = code
                else:
                    get_symbol_code(node.left, code + '0')
                    get_symbol_code(node.right, code + '1')
        get_symbol_code(self.root, '')
        return symbol_code_table

    # Make canonical huffman tree from decoded values and lengths of their codes
    @staticmethod
    def create_canonical_huffman_tree(code_length_code_table: dict[int, int]) -> Self:
        # Sort by the length of the code and then by the value
        table: list[tuple[int, int]] = pipe(
            code_length_code_table.items(),
            lambda arg: sorted(arg, key=lambda x: (x[1], x[0])),
            lambda arg: filter(lambda x: x[1] != 0, arg),
            list,
        )

        huffman_tree = HuffmanTree()
        current_code = 0
        current_code_length = 0
        for symbol, length in table:
            if length > current_code_length:
                # Each time the code length increases, a zero is appended to the end of the code.
                current_code <<= length - current_code_length
                current_code_length = length
            huffman_tree.insert(symbol, current_code, current_code_length)
            # Each time a new code is inserted, current code is incremented.
            current_code += 1
        return huffman_tree
