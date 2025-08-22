from typing import Generator, assert_never
import toml
from os.path import expanduser
import os
import time
import glob
import statx
import json

from dataclasses import dataclass
from typing import List, Union


@dataclass
class VarChange:
    var_type: str
    tick: int
    ts: str
    id: int
    old_value: int
    new_value: int


@dataclass
class InventoryChange:
    tick: int
    ts: str
    old_inventory: List[int]
    old_quantities: List[int]
    new_inventory: List[int]
    new_quantities: List[int]


@dataclass
class AbsolutePosition:
    x: int
    y: int
    plane: int

    @staticmethod
    def from_obj(o: dict[str, int]) -> "AbsolutePosition":
        return AbsolutePosition(
            o["x"],
            o["y"],
            o["plane"],
        )


@dataclass
class Dialogue:
    event_type: str  # started or ended
    tick: int
    ts: str
    actor_name: str
    actor_id: int
    last_interacted_name: str
    last_interacted_id: int
    last_interacted_position: AbsolutePosition | None
    player_position: AbsolutePosition
    text: str
    dialogue_options: list[str]
    dialogue_option_chosen: int


@dataclass
class AnimationPlayerChanged:
    tick: int
    ts: str

    animation: int
    pose_animation: int
    old_animation: int
    old_pose_animation: int
    player_position: AbsolutePosition
    interaction_id: int
    interaction_menu_option: str
    interaction_menu_target: str
    interaction_position: AbsolutePosition | None


def parse_log_line(
    line: str,
) -> Union[VarChange, Dialogue, InventoryChange, AnimationPlayerChanged, dict]:
    parsed_line = json.loads(line)
    line_type = parsed_line["type"]

    if line_type in ("VARPLAYER_CHANGED", "VARBIT_CHANGED"):
        data = parsed_line["data"]
        return VarChange(
            var_type="varbit" if line_type == "VARBIT_CHANGED" else "varp",
            tick=parsed_line["tick"],
            ts=parsed_line["ts"],
            id=data["id"],
            old_value=data["oldValue"],
            new_value=data["newValue"],
        )

    if line_type in ("DIALOGUE_STARTED", "DIALOGUE_ENDED"):
        data = parsed_line["data"]
        last_interacted_position = None
        if "lastInteractedPosition" in data:
            last_interacted_position = AbsolutePosition.from_obj(
                data["lastInteractedPosition"]
            )
        return Dialogue(
            event_type="started" if line_type == "DIALOGUE_STARTED" else "ended",
            tick=parsed_line["tick"],
            ts=parsed_line["ts"],
            actor_name=data["actorName"],
            actor_id=data.get("actorID", -1),
            last_interacted_name=data.get("lastInteractedName", ""),
            last_interacted_id=data.get("lastInteractedID", -1),
            last_interacted_position=last_interacted_position,
            player_position=AbsolutePosition.from_obj(data["playerPosition"]),
            text=data["dialogueText"],
            dialogue_options=data.get("dialogueOptions", []),
            dialogue_option_chosen=data.get("dialogueOptionChosen", -1),
        )

    if line_type == "INVENTORY_CHANGED":
        data = parsed_line["data"]
        return InventoryChange(
            tick=parsed_line["tick"],
            ts=parsed_line["ts"],
            old_inventory=data["oldInventory"],
            old_quantities=data["oldQuantities"],
            new_inventory=data["newInventory"],
            new_quantities=data["newQuantities"],
        )

    if line_type == "ANIMATION_PLAYER_CHANGED":
        data = parsed_line["data"]

        interaction_position = None
        if "interactionPosition" in data:
            interaction_position = AbsolutePosition.from_obj(
                data["interactionPosition"]
            )

        return AnimationPlayerChanged(
            tick=parsed_line["tick"],
            ts=parsed_line["ts"],
            animation=data["animation"],
            pose_animation=data["poseAnimation"],
            old_animation=data["oldAnimation"],
            old_pose_animation=data["oldPoseAnimation"],
            player_position=AbsolutePosition.from_obj(data["playerPosition"]),
            interaction_id=data["interactionId"],
            interaction_menu_option=data.get("interactionMenuOption", ""),
            interaction_menu_target=data.get("interactionMenuTarget", ""),
            interaction_position=interaction_position,
        )

    return {
        "tick": parsed_line["tick"],
        "ts": parsed_line["ts"],
        "type": line_type,
        "raw": parsed_line,
    }


def load_varbit_lookups() -> dict[str, str]:
    with open("data/gameval_varbits.json", "r") as fh:
        return json.load(fh)


def load_varp_lookups() -> dict[str, str]:
    with open("data/gameval_varps.json", "r") as fh:
        return json.load(fh)


def find_newest_file(log_dir: str) -> str:
    pattern = os.path.join(log_dir, "*-logs.txt")
    files = glob.glob(pattern)

    if not files:
        raise RuntimeError(
            f"No Action Logger files found in {log_dir} (pattern: {pattern})"
        )

    newest_file = max(files, key=lambda x: statx.statx(x).btime)
    return newest_file


def tail(file_path: str) -> Generator[str, None, None]:
    with open(file_path) as fh:
        # fh.seek(0, 2)
        while True:
            line = fh.readline()
            if line:
                yield line.rstrip("\n")
            else:
                time.sleep(0.1)


def main() -> None:
    config = toml.load("config.toml")
    tail_config = config.get("tail", {})

    action_logger_log_dir = expanduser(
        config.get("action_logger_log_dir", "~/.runelite/action-logger")
    )

    newest_log_file = find_newest_file(action_logger_log_dir)
    print(f"Reading from {newest_log_file}")

    show_inventory_changes = tail_config.get("show_inventory_changes", True)
    if not show_inventory_changes:
        print(" + Hiding inventory changes")

    show_dialogue_events = tail_config.get("show_dialogue_events", True)
    if not show_dialogue_events:
        print(" + Hiding dialogue events")

    show_animation_changes = tail_config.get("show_animation_changes", True)
    if not show_animation_changes:
        print(" + Hiding animation changes")

    filtered_varbits: set[int] = set(tail_config.get("filtered_varbits", []))
    filtered_varps: set[int] = set(tail_config.get("filtered_varps", []))

    varbit_lookups = load_varbit_lookups()
    varp_lookups = load_varp_lookups()

    for raw_line in tail(newest_log_file):
        d = parse_log_line(raw_line)
        match d:
            case VarChange():
                str_id = str(d.id)
                if d.var_type == "varbit":
                    if d.id in filtered_varbits:
                        continue
                    name = varbit_lookups.get(str_id, "_unnamed_")
                elif d.var_type == "varp":
                    if d.id in filtered_varps:
                        continue
                    name = varp_lookups.get(str_id, "_unnamed_")
                else:
                    raise ValueError(f"unknown var type: {d.var_type}")

                print(
                    f"[{d.ts} {d.tick}] {d.var_type} {name} ({d.id}) {d.old_value} -> {d.new_value}"
                )

            case Dialogue():
                if not show_dialogue_events:
                    continue
                print(f"[{d.ts} {d.tick}] dialogue {d.event_type}: {d}")

            case InventoryChange():
                if not show_inventory_changes:
                    continue
                print(f"[{d.ts} {d.tick}] inventory change: {d}")

            case AnimationPlayerChanged():
                if not show_animation_changes:
                    continue
                # TODO: make prettier
                print(f"[{d.ts} {d.tick}] animation change: {d}")

            case dict():
                print(f"unhandled event: {d}")

            case _:
                assert_never(d)


if __name__ == "__main__":
    main()
