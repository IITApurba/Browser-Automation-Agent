import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"


class ReportGenerator:
    def __init__(self, template_dir: str | Path = TEMPLATE_DIR) -> None:
        self._env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)

    def generate(self, run, steps, extracted_data) -> str:
        template = self._env.get_template("report.md.jinja")
        plan = getattr(run, "plan", None) or {}
        task_goal = plan.get("task_goal") or getattr(run, "task_goal", "") or ""
        status = getattr(run, "status", "unknown")
        status = getattr(status, "value", status)
        return template.render(
            task_goal=task_goal,
            status=status,
            steps=steps,
            extracted_data=extracted_data,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def save(self, run_id, markdown: str, out_dir: str = "reports") -> str:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{run_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(markdown)
        return path
