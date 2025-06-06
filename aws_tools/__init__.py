__version__ = "0.1.0"


if __name__ == "__main__":
    """
    Generate the non-async modules
    """
    import os
    import pathlib
    import importlib
    import aws_tools
    from aws_tools._async_tools import _generate_sync_module

    package_path = pathlib.Path(aws_tools.__file__).parent

    for name in os.listdir(package_path / "asynchrone"):
        if not name.endswith(".py") or name.startswith("_"):
            continue
        name = name[:-3]
        module = importlib.import_module(f"{aws_tools.__name__}.asynchrone.{name}")
        output_filename = package_path / "synchrone" / (name+".py")
        with open(output_filename, "w") as f:
            f.write(_generate_sync_module(module))
