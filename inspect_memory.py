import asyncio
import inspect
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )
from data.memory import initialize_store, shutdown_store
from data.memory_manager import memory_manager
from pprint import pprint


async def main():
    await initialize_store()

    m = memory_manager.manager

    print("Config schema:")
    pprint(m.config_schema().model_json_schema())
    print(type(m))
    print("default namespace:", m.namespace)
    print("get_namespace:", m.get_namespace)
    print(inspect.signature(m.get_namespace))

    if hasattr(m, "search"):
        print("search:", inspect.signature(m.search))

    if hasattr(m, "ainvoke"):
        print("ainvoke:", inspect.signature(m.ainvoke))

    if hasattr(m, "invoke"):
        print("invoke:", inspect.signature(m.invoke))

    print("Methods:")
    print([x for x in dir(m) if not x.startswith("_")])

    await shutdown_store()


asyncio.run(main())