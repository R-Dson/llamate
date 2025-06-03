"""Text utility functions for Llamate"""

def clean_text(text: str) -> str:
    """Clean and normalize text input"""
    return " ".join(text.split())