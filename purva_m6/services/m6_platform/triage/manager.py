import asyncio

class TriageEvents:
    def __init__(self):
        self.subscribers = set()

    async def subscribe(self):
        q = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q):
        self.subscribers.discard(q)

    async def publish(self, event):
        for q in list(self.subscribers):
            await q.put(event)

events = TriageEvents()
