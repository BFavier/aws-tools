import pathlib
import inspect
import asyncio
import threading
from types import ModuleType
from typing import Awaitable, TypeVar, Callable, Any, AsyncIterable, Iterable


T = TypeVar("T")


def _run_async(coro: Awaitable[T]) -> T:
    """
    Run coroutine safely even if already inside an event loop
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    else:
        return asyncio.run(coro)


def _async_iter_to_sync(async_iter: AsyncIterable[T]) -> Iterable[T]:
    """
    Converts an async iterator into a sync iterator
    """
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    queue = asyncio.Queue(maxsize=1)
    sentinel = object()  # put in the queue when an error is raised
    exception_holder = []

    async def produce():
        try:
            async for item in async_iter:
                await queue.put(item)
        except Exception as e:
            exception_holder.append(e)
        finally:
            await queue.put(sentinel)

    asyncio.run_coroutine_threadsafe(produce(), loop)

    def iterator():
        try:
            while True:
                future = asyncio.run_coroutine_threadsafe(queue.get(), loop)
                item = future.result()
                if item is sentinel:
                    if exception_holder:
                        raise exception_holder[0]
                    break
                yield item
        finally:
            loop.call_soon_threadsafe(loop.stop)
            thread.join()
            loop.close()

    return iterator()


async def _sync_iter_to_async(sync_iter: Iterable[T]) -> AsyncIterable[T]:
    """
    Converts a synchrone iterable into an sync one
    """
    for obj in sync_iter:
        yield obj
        await asyncio.sleep(0)


def _generate_sync_wrapper_code(async_func: Callable[[Any, Any], Awaitable[T]]) -> str:
    """
    returns a string representation of a synchrone function wrapper around an synchrone function
    """
    assert inspect.iscoroutinefunction(async_func) or inspect.isasyncgenfunction(async_func)
    sig = inspect.signature(async_func)
    doc = inspect.getdoc(async_func)
    if doc is not None:
        doc = '    """\n    ' + "\n    ".join(doc.split("\n")) + '\n    """\n'
    else:
        doc = ""
    return_type = sig.return_annotation
    params = list(sig.parameters.values())
    param_str = ", ".join(str(p).replace("AsyncIterable", "Iterable") for p in params)
    args_str = ", ".join(f"{p.name}={p.name}" for p in params)
    func_name = async_func.__name__.removesuffix("_async")
    async_name = async_func.__name__
    return_type_str = f" -> {getattr(return_type, '__name__', repr(return_type))}".replace("AsyncIterable", "Iterable") if return_type != inspect.Signature.empty else ""
    code = ""
    for p in params:
        if "AsyncIterable" in str(p):
            code += f"{p.name} = _sync_iter_to_async({p.name})\n    "
    code = f"{code}return _run_async({async_name}({args_str}))" if inspect.iscoroutinefunction(async_func) else f"return _async_iter_to_sync({async_name}({args_str}))"
    return f"def {func_name}({param_str}){return_type_str}:\n{doc}    {code}"


def _generate_sync_module(module: ModuleType) -> str:
    """
    generate a sync module alongside
    """
    code = ""
    code += f"\"\"\"\nThis module was automatically generated from {module.__name__}\n\"\"\"\n"
    code += f"from {__name__} import _run_async, _async_iter_to_sync, _sync_iter_to_async\n"
    code += f"from {module.__name__} import {', '.join(name for name, obj in vars(module).items() if not name.startswith("_"))}\n"
    for filter in (inspect.isasyncgenfunction, inspect.iscoroutinefunction):
        for name, obj in inspect.getmembers(module, filter):
            if not name.startswith("_"):
                code += f"\n\n{_generate_sync_wrapper_code(obj)}\n"
    return code
