import random
import json
from pathlib import Path
from typing import Dict, List
import datetime

# ANSI color codes for terminal formatting
COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "BOLD": "\033[1m",
    "RESET": "\033[0m",
}

SAVE_FILE = "tv_show_progress.json"


class ShowSelector:
    """Manage TV show selection process with state persistence"""

    def __init__(self, shows: List[str]):
        self.original_order = shows.copy()
        self.remaining_shows = shows.copy()
        self.watched_shows: List[Dict] = []
        self.total_shows = len(shows)
        self.history: List[Dict] = []

        if Path(SAVE_FILE).exists():
            self.load_progress(shows)
        else:
            self.total_shows = len(self.original_order)

    def add_show(self, show_name: str) -> bool:
        """Add a new show to the system if not already exists (case-insensitive)"""
        show_name = show_name.strip()
        if not show_name:
            return False

        # Case-insensitive check
        if any(show_name.lower() == s.lower() for s in self.original_order):
            return False

        self.original_order.append(show_name)
        self.remaining_shows.append(show_name)
        self.total_shows = len(self.original_order)
        self.save_progress()
        return True

    def select_show(self) -> Dict[str, str]:
        """Randomly select and move a show from remaining to watched"""
        if not self.remaining_shows:
            return None

        selected = random.choice(self.remaining_shows)
        selection = {
            "show": selected,
            "timestamp": datetime.datetime.now().isoformat(),
            "action": "watched",
        }

        self.watched_shows.append(selection)
        self.remaining_shows.remove(selected)
        self.history.append(selection)
        self.save_progress()

        return selection

    def undo_last(self) -> Dict[str, str]:
        """Undo the last selection while maintaining original order"""
        if not self.history:
            return None

        last_selection = self.history.pop()
        show_to_restore = last_selection["show"]

        try:
            original_index = self.original_order.index(show_to_restore)
        except ValueError:
            original_index = len(self.original_order)

        insert_index = 0
        for idx, show in enumerate(self.remaining_shows):
            if self.original_order.index(show) > original_index:
                insert_index = idx
                break
        else:
            insert_index = len(self.remaining_shows)

        self.remaining_shows.insert(insert_index, show_to_restore)
        self.watched_shows.remove(last_selection)
        self.save_progress()

        return last_selection

    def get_progress(self) -> Dict:
        """Get current viewing progress statistics"""
        return {
            "watched": len(self.watched_shows),
            "remaining": len(self.remaining_shows),
            "total": self.total_shows,
            "percentage": round((len(self.watched_shows) / self.total_shows) * 100, 1)
            if self.total_shows
            else 0.0,
        }

    def save_progress(self):
        """Save current state to file"""
        with open(SAVE_FILE, "w") as f:
            json.dump(
                {
                    "original_order": self.original_order,
                    "remaining": self.remaining_shows,
                    "watched": self.watched_shows,
                    "history": self.history,
                },
                f,
                indent=2,
            )

    def load_progress(self, initial_shows: List[str]):
        """Load progress from file with advanced corruption handling"""
        backup_file = Path(SAVE_FILE).with_suffix(".bak")
        data = None

        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)

            # Validate required keys
            required_keys = ["original_order", "remaining", "watched", "history"]
            if not all(key in data for key in required_keys):
                raise KeyError("Missing required keys in save file")

            # Validate data types
            if not (
                isinstance(data["original_order"], list)
                and isinstance(data["remaining"], list)
                and isinstance(data["watched"], list)
                and isinstance(data["history"], list)
            ):
                raise ValueError("Invalid data types in save file")

            self.original_order = data["original_order"]
            self.remaining_shows = data["remaining"]
            self.watched_shows = data["watched"]
            self.history = data["history"]
            self.total_shows = len(self.original_order)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"{COLORS['RED']}⚠️ Corrupted save file: {str(e)}{COLORS['RESET']}")

            # Create backup of corrupted file
            if Path(SAVE_FILE).exists():
                print(
                    f"{COLORS['YELLOW']}Creating backup at {backup_file}{COLORS['RESET']}"
                )
                Path(SAVE_FILE).rename(backup_file)

            # Try to load from backup
            try:
                if backup_file.exists():
                    with open(backup_file, "r") as f:
                        backup_data = json.load(f)

                    if not all(key in backup_data for key in required_keys):
                        raise KeyError("Backup file missing keys")

                    self.original_order = backup_data["original_order"]
                    self.remaining_shows = backup_data["remaining"]
                    self.watched_shows = backup_data["watched"]
                    self.history = backup_data["history"]
                    self.total_shows = len(self.original_order)
                    print(
                        f"{COLORS['GREEN']}✔️ Successfully loaded from backup{COLORS['RESET']}"
                    )
                    return
            except Exception as backup_error:
                print(
                    f"{COLORS['RED']}⚠️ Backup load failed: {str(backup_error)}{COLORS['RESET']}"
                )

            # Attempt data recovery from corrupted data
            try:
                remaining = data.get("remaining", []) if data else []
                watched = data.get("watched", []) if data else []
                history = data.get("history", []) if data else []

                # Reconstruct original_order from remaining + watched shows
                watched_shows = [s["show"] for s in watched]
                all_shows = remaining + watched_shows
                seen = set()
                recovered_order = []
                for show in all_shows + initial_shows:
                    if show.lower() not in seen:
                        seen.add(show.lower())
                        recovered_order.append(show)

                self.original_order = recovered_order
                self.remaining_shows = remaining
                self.watched_shows = watched
                self.history = history
                self.total_shows = len(self.original_order)

                print(
                    f"{COLORS['GREEN']}✔️ Recovered {self.total_shows} shows from corrupted data{COLORS['RESET']}"
                )

                # Validate remaining shows exist in original_order
                self.remaining_shows = [
                    s for s in self.remaining_shows if s in self.original_order
                ]
                # Validate watched shows exist in original_order
                self.watched_shows = [
                    s for s in self.watched_shows if s["show"] in self.original_order
                ]

            except Exception as recovery_error:
                print(
                    f"{COLORS['RED']}⚠️ Data recovery failed: {str(recovery_error)}{COLORS['RESET']}"
                )
                print(
                    f"{COLORS['YELLOW']}⚠️ Resetting to initial show list{COLORS['RESET']}"
                )
                self.original_order = initial_shows.copy()
                self.remaining_shows = initial_shows.copy()
                self.watched_shows = []
                self.history = []
                self.total_shows = len(initial_shows)

            self.save_progress()


def display_progress_bar(percentage: float):
    """Display a visual progress bar with precise calculation"""
    filled = int(round(percentage / (100 / 30)))
    bar = f"{COLORS['GREEN']}{'█' * filled}{COLORS['RESET']}{'-' * (30 - filled)}"
    print(f"\nProgress: {bar} {percentage}%")


def show_menu() -> str:
    """Display interactive menu and get user choice"""
    print(f"\n{COLORS['BOLD']}{COLORS['MAGENTA']}Main Menu{COLORS['RESET']}")
    print(f"{COLORS['CYAN']}1. Pick random show")
    print("2. Undo last selection")
    print("3. View watched list")
    print("4. View remaining shows")
    print("5. Add new TV show")
    print(f"6. Exit{COLORS['RESET']}")
    return input(
        f"{COLORS['YELLOW']}⟳ Enter your choice (1-6): {COLORS['RESET']}"
    ).strip()


def print_header(text: str):
    """Print section headers with formatting"""
    print(f"\n{COLORS['BOLD']}{COLORS['MAGENTA']}▶ {text}{COLORS['RESET']}")


def main():
    initial_shows = [
        "The Sopranos",
        "Breaking Bad",
        "Oz",
        "Better Call Saul",
        "The Wire",
        "Game of Thrones",
        "House of Cards",
        "Boardwalk Empire",
        "Justified",
        "Dexter",
        "The Leftovers",
        "Homeland",
        "Rome",
        "Mad Men",
        "Sons of Anarchy",
        "Lost",
        "Hannibal",
        "Six Feet Under",
        "The Office",
        "MINDHUNTER",
        "Louie",
        "Deadwood",
        "Twin Peaks",
        "Person of Interest",
        "House",
        "True Detective",
        "Seinfeld",
        "Mr. Robot",
        "Silicon Valley",
        "Severance",
        "Fringe",
        "Curb Your Enthusiasm",
        "Succession",
        "The Americans",
        "Treme",
        "Fargo",
        "BoJack Horseman",
        "Narcos",
        "Atlanta",
        "Mr Inbetween",
        "The Crown",
        "Black Mirror",
        "Dark",
        "The Newsroom",
        "It's Always Sunny in Philadelphia",
        "Prison Break",
        "The White Lotus",
        "Fleabag",
        "Rick and Morty",
        "House of the Dragon",
    ]

    selector = ShowSelector(initial_shows)

    print(
        f"\n{COLORS['BOLD']}{COLORS['MAGENTA']}"
        "░▒▓███████▓▒░ TV Show Selection Assistant ░▒▓███████▓▒░"
        f"{COLORS['RESET']}"
    )

    try:
        while True:
            choice = show_menu()
            progress = selector.get_progress()

            if choice == "1":
                selection = selector.select_show()
                if not selection:
                    print(f"\n{COLORS['GREEN']}🎉 All shows watched!{COLORS['RESET']}")
                    continue

                print_header("New Selection")
                print(f"{COLORS['CYAN']}📺 Show: {selection['show']}")
                print(
                    f"⏰ Selected at: {selection['timestamp'][:16].replace('T', ' ')}"
                )
                display_progress_bar(progress["percentage"])

            elif choice == "2":
                undone = selector.undo_last()
                if undone:
                    print_header("Undo Successful")
                    print(
                        f"{COLORS['YELLOW']}↩️ Undid: {undone['show']}{COLORS['RESET']}"
                    )
                    display_progress_bar(selector.get_progress()["percentage"])
                else:
                    print(f"{COLORS['RED']}⚠️ Nothing to undo!{COLORS['RESET']}")

            elif choice == "3":
                print_header("Watched Shows")
                if not selector.watched_shows:
                    print(f"{COLORS['YELLOW']}No shows watched yet.{COLORS['RESET']}")
                else:
                    for idx, show in enumerate(selector.watched_shows, 1):
                        print(f"{idx}. {show['show']} ({show['timestamp'][:10]})")

            elif choice == "4":
                print_header("Remaining Shows")
                if not selector.remaining_shows:
                    print(f"{COLORS['GREEN']}All shows watched! 🎉{COLORS['RESET']}")
                else:
                    for idx, show in enumerate(selector.remaining_shows, 1):
                        print(f"{idx}. {show}")

            elif choice == "5":
                print_header("Add New TV Show")
                new_show = input(
                    f"{COLORS['YELLOW']}Enter show name: {COLORS['RESET']}"
                ).strip()
                if selector.add_show(new_show):
                    print(f"{COLORS['GREEN']}✅ Added '{new_show}' to collection!")
                else:
                    print(f"{COLORS['RED']}⚠️ Show already exists or invalid name.")
                print(
                    f"{COLORS['CYAN']}Total shows now: {selector.total_shows}{COLORS['RESET']}"
                )

            elif choice == "6":
                print(
                    f"\n{COLORS['YELLOW']}📊 Final Stats: {progress['watched']} watched, "
                    f"{progress['remaining']} remaining{COLORS['RESET']}"
                )
                break

            else:
                print(f"{COLORS['RED']}⚠️ Invalid choice!{COLORS['RESET']}")

    except KeyboardInterrupt:
        print(
            f"\n{COLORS['RED']}🚨 Session interrupted. Progress saved.{COLORS['RESET']}"
        )


if __name__ == "__main__":
    main()
