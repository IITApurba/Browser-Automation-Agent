try:
    from browser_use import Agent as BrowserUseAgent
except ImportError:
    BrowserUseAgent = None


class BrowserUseAdapter:
    async def run_subtask(self, task_description: str, llm) -> dict:
        if BrowserUseAgent is None:
            raise RuntimeError(
                "browser-use is not installed; install with `pip install -e .[browseruse]` to use BrowserUseAdapter"
            )

        agent = BrowserUseAgent(task=task_description, llm=llm)
        result = await agent.run()
        return {"result": result}
