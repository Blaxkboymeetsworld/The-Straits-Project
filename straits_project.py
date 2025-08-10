import sys, os
# Force UTF-8 output where supported
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# On Windows, also set console code page to UTF-8 (best effort)
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

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
        return statuses[self.relationship_level]

class GameState:
    def __init__(self):
        self.faction = None
        self.ship = None
        self.first_mate = CrewMember("Omar", "First Mate", 2)

    def set_faction(self, choice):
        if choice == "1":
            self.faction = "Portuguese Conquistador"
            self.ship = "Caravel"
        elif choice == "2":
            self.faction = "Arab Muslim Dāʿī"
            self.ship = "Dhow"

    def intro_event(self):
        print("\n--- The Straits Project ---")
        print("You awake weary in the wee hours of the morning...")
        print("You hear a knock at the door and call them to come in.")
        print("You see your first mate, Omar, in the early morning glow.")
        print('"Sir, finally we have arrived at our destination. Give the word and we should be able to dock within the hour. What are your orders?"\n')
        print("1. 'Bring us in, Omar.'")
        print("2. 'Let's have a chat first.'")
        choice = input("> ")

        if choice == "1":
            print("\nYou begin a separate text sequence with the harbormaster immediately.")
            print(f"Relationship with Omar remains at {self.first_mate.relationship_level}/5.")
        elif choice == "2":
            print("\nYou and Omar have a genuine heart-to-heart...")
            print("He confides that being far from his family has been tough due to his new child.")
            self.first_mate.relationship_level = min(4, self.first_mate.relationship_level + 2)
            print(f"Relationship with Omar improved to {self.first_mate.relationship_level}/5.")
        else:
            print("\nInvalid input. No action taken.")

        print("\n" + self.first_mate.relationship_status())

def run_game():
    game = GameState()
    print("Choose your faction:")
    print("1. Portuguese Conquistador")
    print("2. Arab Muslim Dāʿī")
    faction_choice = input("> ")
    game.set_faction(faction_choice)
    print(f"\nYou have chosen: {game.faction}")
    print(f"You are traveling on an old {game.ship}.\n")
    game.intro_event()

run_game()
