import re
import unicodedata

class Normalizer:
    @staticmethod
    def clean_text(text:str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize('NFKC', text)
        text = Normalizer.dehyphenate(text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    @staticmethod
    def dehyphenate(text: str) -> str:
        return re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)