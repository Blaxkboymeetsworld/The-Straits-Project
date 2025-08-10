import sys, os

# --- UTF-8 / Windows console setup ---
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

# --- small utilities ---
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def prompt(allowed=None):
    """Read a trimmed line; optionally restrict to allowed set."""
    s = input("> ").strip()
    if allowed is None:
        return s
    while s not in allowed:
        print(f"Please choose {', '.join(allowed)}.")
        s = input("> ").strip()
    return s

# --- data model ---
class CrewMember:
    def __init__(self, name, role, relationship_level):
        self.name = name
        self.role = role
        self.relationship_level = relationship_level  # 0-4 scale

    def relationship_status(self):
        statuses = {
            0: "Desertion: Will abandon you the first chance they get.",
            1: "Mutinous/Insubordinate: Unreliable for even the most basic tasks.",
            2: "Outward contempt: This relationship is fraught, and there will be pushbacks.",
            3: "Loyal: This character is trustworthy and has faith in your judgement.",
            4: "Unwavering: This character trusts you implicitly."
        }
        return statuses.get(self.relationship_level, "Unknown")

NAME_PORT = "Portuguese Conquistador"
NAME_ARAB = "Arab Muslim Dāʿī"
# Placeholder for future path:
NAME_CHIN = "Chinese Trader"

class GameState:
    def __init__(self):
        self.faction = None
        self.ship = None
        self.first_mate = CrewMember("Omar", "First Mate", 2)  # starts 2/5

    def set_faction(self, choice):
        if choice == "1":
            self.faction = NAME_PORT
            self.ship = "Caravel"
        elif choice == "2":
            self.faction = NAME_ARAB
            self.ship = "Dhow"
        elif choice == "3":
            self.faction = NAME_CHIN
            self.ship = "Junk"

# --- game flow ---
def title_screen():
    clear()
    print("========================================")
    print("           THE STRAITS PROJECT          ")
    print("========================================")
    print("A text-based RPG set in 16th-century SEA")
    print()
    print("1) Start")
    print("2) Quit")
    choice = prompt({"1", "2"})
    return choice

def choose_faction(game: GameState):
    clear()
    print("Choose your faction:")
    print("1. Portuguese Conquistador")
    print("2. Arab Muslim Dāʿī")
    # print("3. Chinese Trader")  # enable soon
    choice = prompt({"1", "2"})  # add "3" later
    game.set_faction(choice)
    clear()
    print(f"You have chosen: {game.faction}")
    print(f"You are traveling on an old {game.ship}.")
    input("\n(Press Enter to continue...)")

def intro_event(game: GameState):
    clear()
    print("\n--- The Straits Project ---")
    print("You awake weary in the wee hours of the morning.")
    print("Your quarters are still dark and filled with the stench of a man who has seen better days.")
    print("You hear a knock at the door and call them to come in.")
    print("The door cracks open and you see your first mate, Omar, in the early morning glow.")
    print("You have been at odds with him for the better part of the month over choices made leading up to this point.")
    print('"Sir, finally we have arrived at our destination. Give the word and we should be able to dock within the hour. What are your orders?"\n')
    print("1) 'Bring us in, Omar.' Put on boots, say a prayer, and begin the day.")
    print("2) 'Let’s have a chat first.' Talk about the troubling first leg of the trip.")
    choice = prompt({"1", "2"})

    if choice == "1":
        clear()
        print("You begin a separate text sequence with the harbormaster immediately.")
        print(f"Relationship with Omar remains at {game.first_mate.relationship_level}/5.")
    else:
        clear()
        print("You and Omar have a genuine heart-to-heart.")
        print("He confides that being far from his family has been tough due to his new child.")
        print("He finds solace in your willingness to engage him in conversation.")
        game.first_mate.relationship_level = min(4, game.first_mate.relationship_level + 2)
        print(f"Relationship with Omar improved to {game.first_mate.relationship_level}/5.")

    print("\n" + game.first_mate.relationship_status())
    input("\n(Press Enter to continue...)")

def main():
    while True:
        choice = title_screen()
        if choice == "2":
            clear()
            print("Farewell, Captain.")
            return
        # Start selected
        game = GameState()
        choose_faction(game)
        intro_event(game)
        # After intro, loop back to title for now
        clear()
        print("End of prototype segment.")
        print("1) Return to Title")
        print("2) Quit")
        post = prompt({"1", "2"})
        if post == "2":
            clear()
            print("Farewell, Captain.")
            return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nFarewell, Captain. Until next voyage.")


