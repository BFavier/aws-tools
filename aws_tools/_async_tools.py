import sys
import pathlib
import inspect
import asyncio
from typing import Awaitable, TypeVar, Callable, Any


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


def _generate_sync_wrapper_code(async_func: Callable[[Any, Any], Awaitable[T]]) -> str:
    """
    returns a string representation of a synchrone function wrapper around an synchrone function
    """
    assert inspect.iscoroutinefunction(async_func)
    sig = inspect.signature(async_func)
    doc = "    " + "\n    ".join(inspect.getdoc(async_func).split("\n"))
    return_type = sig.return_annotation
    params = list(sig.parameters.values())
    param_str = ", ".join(str(p) for p in params)
    args_str = ", ".join(f"{p.name}={p.name}" for p in params)
    func_name = async_func.__name__.removesuffix("_async")
    async_name = async_func.__name__
    return_type_str = f" -> {getattr(return_type, '__name__', repr(return_type))}" if return_type != inspect.Signature.empty else ""
    docstring = f'    """\n{doc}\n    """' if doc else ""
    return f"def {func_name}({param_str}){return_type_str}:\n{docstring}\n    return _run_async({async_name}({args_str}))"


def _generate_sync_module(module_name: str) -> str:
    """
    generate a sync module alongside
    """
    module = sys.modules[module_name]
    original_path = pathlib.Path(module.__file__)
    assert "_async" in original_path.stem
    path = original_path.with_stem(original_path.stem.replace("_async", ""))
    module_path = f"aws_tools.{original_path.stem}"
    with open(path, "w") as f:
        f.write(f"\"\"\"\nThis module was automatically generated from {module_path}\n\"\"\"\n")
        f.write(f"from {__name__} import _run_async\n")
        f.write(f"from {module_path} import {', '.join(name for name, obj in vars(module).items() if not name.startswith("_"))}\n")
        for name, obj in inspect.getmembers(module, inspect.iscoroutinefunction):
            if not name.startswith("_"):
                f.write(f"\n\n{_generate_sync_wrapper_code(obj)}\n\n")
