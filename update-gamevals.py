from os import path
from typing import Any
import toml
from os.path import expanduser
import jast
import json
from itertools import batched


# Print the names of all classes
class NameVisitor(jast.JNodeVisitor):
    def default_result(self):
        return []

    def visit_Field(self, node: jast.JAST) -> Any:
        # NOTE: we're not checking if it's an int, we'd need to check node.modifiers for that
        if len(node.declarators) == 1:
            d = node.declarators[0]
            return [d.id.id, d.init.value]
        return []

    def aggregate_result(self, aggregate: Any, result: Any) -> Any:
        return aggregate + result


def update_varbits(gameval_dir: str, output_filename: str) -> None:
    output_path = path.join("data", output_filename)
    print(f"Writing Varbit gamevals to {output_path}")

    data: dict[str, str] = {}

    with open(path.join(gameval_dir, "VarbitID.java")) as fh:
        tree = jast.parse(fh.read())
        visitor = NameVisitor()
        enum_map = visitor.visit(tree)
        for enum_name, enum_value in batched(enum_map, n=2):
            data[enum_value] = enum_name

    with open(output_path, "w+") as fh:
        fh.write(json.dumps(data, indent=4))


def update_varps(gameval_dir: str, output_filename: str) -> None:
    output_path = path.join("data", output_filename)
    print(f"Writing Varp gamevals to {output_path}")

    data: dict[str, str] = {}

    with open(path.join(gameval_dir, "VarPlayerID.java")) as fh:
        tree = jast.parse(fh.read())
        visitor = NameVisitor()
        enum_map = visitor.visit(tree)
        for enum_name, enum_value in batched(enum_map, n=2):
            data[enum_value] = enum_name

        with open(output_path, "w+") as fh:
            fh.write(json.dumps(data, indent=4))


def main() -> None:
    config = toml.load("config.toml")

    runelite_dir = expanduser(config.get("runelite_dir", "~/git/runelite"))

    gameval_dir = path.join(
        runelite_dir,
        "runelite-api",
        "src",
        "main",
        "java",
        "net",
        "runelite",
        "api",
        "gameval",
    )

    update_varbits(gameval_dir, "gameval_varbits.json")
    update_varps(gameval_dir, "gameval_varps.json")


if __name__ == "__main__":
    main()
