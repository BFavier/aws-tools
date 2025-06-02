import sys
import pathlib
import inspect
import asyncio
import threading
from typing import Awaitable, TypeVar, Callable, Any, AsyncIterator, Iterator


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


def _async_iter_to_sync(async_iter: AsyncIterator[T]) -> Iterator[T]:
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
    param_str = ", ".join(str(p) for p in params)
    args_str = ", ".join(f"{p.name}={p.name}" for p in params)
    func_name = async_func.__name__.removesuffix("_async")
    async_name = async_func.__name__
    return_type_str = f" -> {getattr(return_type, '__name__', repr(return_type))}" if return_type != inspect.Signature.empty else ""
    code = f"return _run_async({async_name}({args_str}))" if inspect.iscoroutinefunction(async_func) else f"return _async_iter_to_sync({async_name}({args_str}))"
    return f"def {func_name}({param_str}){return_type_str}:\n{doc}    {code}"


def _generate_sync_module(module_name: str) -> str:
    """
    generate a sync module alongside
    """
    module = sys.modules[module_name]
    original_path = pathlib.Path(module.__file__)
    assert "_async" in original_path.stem
    path = original_path.with_stem(original_path.stem.replace("_async", ""))
    module_path = f"{module.__package__}.{original_path.stem}"
    with open(path, "w") as f:
        f.write(f"\"\"\"\nThis module was automatically generated from {module_path}\n\"\"\"\n")
        f.write(f"from {__name__} import _run_async, _async_iter_to_sync\n")
        f.write(f"from {module_path} import {', '.join(name for name, obj in vars(module).items() if not name.startswith("_"))}\n")
        for filter in (inspect.isasyncgenfunction, inspect.iscoroutinefunction):
            for name, obj in inspect.getmembers(module, filter):
                if not name.startswith("_"):
                    f.write(f"\n\n{_generate_sync_wrapper_code(obj)}\n\n")
