from typing import Self

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
