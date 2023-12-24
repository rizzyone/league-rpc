from typing import Any, Optional

import requests
import urllib3

from league_rpc_linux.colors import Colors
from league_rpc_linux.polling import wait_until_exists
from league_rpc_linux.username import get_summoner_name

from league_rpc_linux.const import (
    CURRENT_PATCH,
    BASE_CHAMPION_URL,
    BASE_SKIN_URL,
    GAME_MODE_CONVERT_MAP,
    CHAMPION_NAME_CONVERT_MAP,
    ALL_GAME_DATA_URL,
)

urllib3.disable_warnings()


def gather_ingame_information() -> tuple[str, str, int, str, int, int]:
    """
    Get the current playing champion name.
    """
    all_game_data_url = ALL_GAME_DATA_URL
    your_summoner_name = get_summoner_name()

    champion_name: str | None = None
    skin_id: int | None = None
    skin_name: str | None = None
    game_mode: str | None = None  # Set if the game mode was never found.. Maybe you are playing something new?
    level: int | None = None
    gold: int | None = None

    if response := wait_until_exists(
        url=all_game_data_url,
        custom_message="Did not find game data.. Will try again in 5 seconds",
    ):
        parsed_data = response.json()
        game_mode = GAME_MODE_CONVERT_MAP.get(
            parsed_data["gameData"]["gameMode"],
            parsed_data["gameData"]["gameMode"],
        )

        if game_mode == "TFT":
            # If the currentGame is TFT.. gather the relevant information
            level = gather_tft_data(parsed_data=parsed_data)
        else:
            # If the gamemode is LEAGUE gather the relevant information.
            champion_name, skin_id, skin_name = gather_league_data(
                parsed_data=parsed_data, summoners_name=your_summoner_name
            )
            if game_mode == "Arena":
                level, gold = gather_arena_data(parsed_data=parsed_data)
            print("-" * 50)
            if champion_name:
                print(
                    f"{Colors.yellow}Champion name found {Colors.green}({champion_name}),{Colors.yellow} continuing..{Colors.reset}"
                )
            if skin_name:
                print(
                    f"{Colors.yellow}Skin detected: {Colors.green}{skin_name},{Colors.yellow} continuing..{Colors.reset}"
                )
            if game_mode:
                print(
                    f"{Colors.yellow}Game mode detected: {Colors.green}{game_mode},{Colors.yellow} continuing..{Colors.reset}"
                )
            print("-" * 50)

    # Returns default values if information was not found.
    return (
        (champion_name or ""),
        (skin_name or ""),
        (skin_id or 0),
        (game_mode or ""),
        (level or 0),
        (gold or 0),
    )


def gather_league_data(
    parsed_data: dict[str, Any],
    summoners_name: str,
) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """
    If the gamemode is LEAGUE, gather the relevant information and return it to RPC.
    """
    champion_name: Optional[str] = None
    skin_id: Optional[int] = None
    skin_name: Optional[str] = None

    for player in parsed_data["allPlayers"]:
        if player["summonerName"] == summoners_name:
            champion_name = CHAMPION_NAME_CONVERT_MAP.get(
                player["championName"],
                player["championName"],
            )
            skin_id = player["skinID"]
            skin_name = player.get("skinName")
            break
        continue
    return champion_name, skin_id, skin_name


def gather_tft_data(parsed_data: dict[str, Any]) -> int:
    """
    If the gamemode is TFT, it will gather information and return it to RPC
    """
    level = int(parsed_data["activePlayer"]["level"])
    return level


def gather_arena_data(parsed_data: dict[str, Any]) -> tuple[int, int]:
    """
    If the gamemode is Arena, it will gather information and return it to RPC
    """
    level = int(parsed_data["activePlayer"]["level"])
    gold = int(parsed_data["activePlayer"]["currentGold"])
    return level, gold


def check_url(url: str) -> bool:
    """
    Just a simple url checker. expecting an OK.
    """
    try:
        return requests.get(url=url, verify=False, timeout=15).status_code == 200
    except requests.RequestException:
        return False


def get_skin_asset(
    champion_name: str,
    skin_id: int,
    fallback_asset: str,
) -> str:
    """
    Returns either a default champion art
    or the selected skin for that specific champion.
    """
    if skin_id != 0:
        url = f"{BASE_SKIN_URL}{champion_name}_{skin_id}.jpg"
    else:
        url = f"{BASE_CHAMPION_URL}{champion_name}.png"

    if not check_url(url):
        print(
            f"""{Colors.red}Failed to request the champion/skin image
    {Colors.orange}Reasons for this could be the following:
{Colors.blue}(1) Maybe a false positive.. A new attempt will be made to find the skin art. But if it keeps failing, then something is wrong.
    If the skin art is after further attempts found, then you can simply ignore this message..
(2) Your version of this application is outdated
(3) The maintainer of this application has not updated to the latest patch..
    If league's latest patch isn't {CURRENT_PATCH}, then contact ({Colors.orange}@haze.dev{Colors.blue} on Discord).{Colors.reset}"""
        )
        return fallback_asset

    return url
