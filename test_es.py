import asyncio

from elasticsearch import AsyncElasticsearch


async def main():
    es = AsyncElasticsearch("http://localhost:9200")

    try:
        print("Ping:", await es.ping())
        print("Info:", await es.info())
    except Exception as e:
        print(type(e).__name__)
        print(e)
    finally:
        await es.close()


asyncio.run(main())