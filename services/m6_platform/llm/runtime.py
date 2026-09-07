import httpx
from ..settings import settings

class LLMRuntime:
    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{settings.llm_base_url}/health")
                return response.is_success
        except Exception:
            return False

    async def generate(self, prompt, schema, grammar=None):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.llm_base_url}/generate",
                json={"prompt": prompt, "schema": schema, "grammar": grammar},
            )
            response.raise_for_status()
            return response.json()
