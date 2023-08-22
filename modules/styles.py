# We need this so Python doesn't complain about the unknown StableDiffusionProcessing-typehint at runtime
from __future__ import annotations
import csv
import os
import os.path
import tempfile
import shutil
import typing
from installer import log


if typing.TYPE_CHECKING:
    # Only import this when code is being type-checked, it doesn't have any effect at runtime
    from .processing import StableDiffusionProcessing


class PromptStyle(typing.NamedTuple):
    name: str
    prompt: str
    negative_prompt: str


def merge_prompts(style_prompt: str, prompt: str) -> str:
    if "{prompt}" in style_prompt:
        res = style_prompt.replace("{prompt}", prompt)
    else:
        original_prompt = prompt.strip()
        style_prompt = style_prompt.strip()
        parts = filter(None, (original_prompt, style_prompt))
        if original_prompt.endswith(","):
            res = " ".join(parts)
        else:
            res = ", ".join(parts)
    return res


def apply_styles_to_prompt(prompt, styles):
    for style in styles:
        prompt = merge_prompts(style, prompt)
    return prompt


class StyleDatabase:
    def __init__(self, path: str):
        self.no_style = PromptStyle("None", "", "")
        self.styles = {}
        self.path = path
        self.reload()

    def reload(self):
        self.styles.clear()
        if not os.path.exists(self.path):
            self.save_styles(self.path)
        with open(self.path, "r", encoding="utf-8-sig", newline='') as file:
            reader = csv.DictReader(file, skipinitialspace=True)
            for row in reader:
                try:
                    prompt = row["prompt"] if "prompt" in row else row["text"]
                    negative_prompt = row.get("negative_prompt", "")
                    self.styles[row["name"]] = PromptStyle(row["name"], prompt, negative_prompt)
                except Exception:
                    log.error(f'Styles error: {self.path} {row}')
            log.debug(f'Loaded styles: {self.path} {len(self.styles.keys())}')

    def get_style_prompts(self, styles):
        return [self.styles.get(x, self.no_style).prompt for x in styles]

    def get_negative_style_prompts(self, styles):
        return [self.styles.get(x, self.no_style).negative_prompt for x in styles]

    def apply_styles_to_prompt(self, prompt, styles):
        return apply_styles_to_prompt(prompt, [self.styles.get(x, self.no_style).prompt for x in styles])

    def apply_negative_styles_to_prompt(self, prompt, styles):
        return apply_styles_to_prompt(prompt, [self.styles.get(x, self.no_style).negative_prompt for x in styles])

    def save_styles(self, path: str) -> None:
        basedir = os.path.dirname(path)
        if basedir is not None and len(basedir) > 0:
            os.makedirs(basedir, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(".csv")
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline='') as file:
            writer = csv.DictWriter(file, fieldnames=PromptStyle._fields)
            writer.writeheader()
            writer.writerows(style._asdict() for k, style in self.styles.items())
            log.debug(f'Saved styles: {path} {len(self.styles.keys())}')
        shutil.move(temp_path, path)
