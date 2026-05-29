import yaml
_prompts: dict = {}


def load_prompts(yaml_path: str) -> None:
    global _prompts
    with open(yaml_path, "r", encoding="utf-8") as f:
        _prompts = yaml.safe_load(f)


def get_system_prompt(theme: str, tone: str) -> str:
    themes = _prompts.get("themes", {})
    template = themes.get(theme, themes.get("other", {})).get("system", "")
    return template.format(tone=tone)


def get_clarification_prompt(tone: str) -> str:
    template = _prompts.get("clarification", {}).get("system", "")
    return template.format(tone=tone)