"""Text utility functions for llamate"""

def clean_text(text: str) -> str:
    """Clean and normalize text input"""
    return " ".join(text.split())