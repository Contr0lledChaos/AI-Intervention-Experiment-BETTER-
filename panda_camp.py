import pygame
import sys
import random
import csv
from datetime import datetime
from pathlib import Path

from ai_teammate import AITeammate

try:
    from PIL import Image, ImageSequence
except ImportError:
    Image = None
    ImageSequence = None


# INITIALIZATION & SETUP

pygame.init()

WIDTH, HEIGHT = 1000, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Familiar Encampment: Panda Express")

FONT_SMALL = pygame.font.SysFont("Arial", 14)
FONT_MED = pygame.font.SysFont("Arial", 18)
FONT_INSTRUCTION_TITLE = pygame.font.SysFont("Arial", 18, bold=True)
FONT_INSTRUCTION = pygame.font.SysFont("Arial", 21, bold=True)
FONT_PANEL_TITLE = pygame.font.SysFont("Arial", 20, bold=True)
FONT_PANEL_BODY = pygame.font.SysFont("Arial", 16)
FONT_LARGE = pygame.font.SysFont("Arial", 24)
FONT_MORALE = pygame.font.SysFont("Arial", 30, bold=True)
FONT_XL = pygame.font.SysFont("Arial", 34, bold=True)
FONT_MONO = pygame.font.SysFont("Consolas", 14)

BASE_DIR = Path(__file__).resolve().parent

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200)
GREEN = (50, 205, 50)
RED = (220, 20, 60)
DARK_RED = (139, 0, 0)
GOLD = (255, 215, 0)

# Storm palette with compressed contrast, but still readable.
STORM_PANEL = (61, 65, 66)
STORM_PANEL_HOVER = (68, 72, 72)
STORM_BORDER = (105, 108, 106)
STORM_TITLE = (181, 181, 171)
STORM_TEXT = (151, 153, 146)
STORM_HUD = (174, 175, 165)
STORM_SHADOW = (63, 65, 63)
STORM_OVERLAY = (56, 59, 60)
STORM_TRACK = (87, 89, 87)
STORM_TARGET = (116, 129, 113)
STORM_WARNING = (147, 113, 108)

def draw_storm_visual_load():
    """Add dim haze, edge darkening and faint moving interference in STORM."""
    if state.phase != "STORM":
        return

    # Semi-transparent gray-green haze compresses the background contrast.
    haze = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pulse = int(5 * ((pygame.time.get_ticks() // 180) % 3))
    haze.fill((39 + pulse, 43 + pulse, 42 + pulse, 78))
    screen.blit(haze, (0, 0))

    # Darkened edges force more visual search without obscuring controls.
    vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(vignette, (18, 20, 20, 70), vignette.get_rect(), width=34)
    screen.blit(vignette, (0, 0))

    # Sparse, low-opacity scan lines create visual interference.
    interference = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    offset = (pygame.time.get_ticks() // 55) % 12
    for y in range(offset, HEIGHT, 12):
        pygame.draw.line(interference, (145, 148, 143, 13), (0, y), (WIDTH, y))
    screen.blit(interference, (0, 0))

# Load backgrounds and assets safely
def asset_path(*names):
    """Return the first existing asset beside this script."""
    for name in names:
        candidate = BASE_DIR / name
        if candidate.exists():
            return candidate
    return None

def make_dead_face(size=(45, 45)):
    """Reliable fallback dead-face icon; avoids missing emoji glyphs."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    pygame.draw.circle(surf, (225, 205, 80), (w // 2, h // 2), min(w, h) // 2 - 2)
    pygame.draw.circle(surf, BLACK, (w // 2, h // 2), min(w, h) // 2 - 2, 2)
    pygame.draw.line(surf, BLACK, (10, 12), (18, 20), 3)
    pygame.draw.line(surf, BLACK, (18, 12), (10, 20), 3)
    pygame.draw.line(surf, BLACK, (27, 12), (35, 20), 3)
    pygame.draw.line(surf, BLACK, (35, 12), (27, 20), 3)
    pygame.draw.arc(surf, BLACK, pygame.Rect(12, 25, 21, 12), 0.15, 3.0, 3)
    return surf

def load_scaled_image(names, size, alpha=True, fallback=None):
    path = asset_path(*names)
    if path is not None:
        try:
            image = pygame.image.load(str(path))
            image = image.convert_alpha() if alpha else image.convert()
            return pygame.transform.smoothscale(image, size)
        except pygame.error as exc:
            print(f"Could not load {path.name}: {exc}")
    return fallback() if fallback else pygame.Surface(size, pygame.SRCALPHA)

def load_gif_frames(names, size):
    """Load and fully composite every GIF frame with Pillow."""
    path = asset_path(*names)
    if path is None:
        print("Crying animation asset not found beside the Python file.")
        return [], []

    if path.suffix.lower() == ".gif":
        if Image is None or ImageSequence is None:
            print("Animated GIF support requires Pillow. Install it with: pip install pillow")
            fallback_frame = load_scaled_image((path.name,), size, alpha=True)
            return [fallback_frame], [100]

        try:
            frames, durations = [], []
            with Image.open(path) as gif:
                # GIFs
                for frame_number in range(getattr(gif, "n_frames", 1)):
                    gif.seek(frame_number)
                    duration = int(gif.info.get("duration", 100) or 100)
                    rgba = gif.convert("RGBA")
                    rgba = rgba.resize(size, Image.Resampling.LANCZOS)
                    surface = pygame.image.frombuffer(
                        rgba.tobytes(), rgba.size, "RGBA"
                    ).convert_alpha().copy()
                    frames.append(surface)
                    durations.append(max(40, duration))

            print(f"Loaded animated GIF: {path.name} ({len(frames)} frames)")
            return frames, durations
        except Exception as exc:
            print(f"Could not animate {path.name}: {exc}")

    fallback_frame = load_scaled_image((path.name,), size, alpha=True)
    print(f"Loaded static crying image: {path.name}")
    return [fallback_frame], [100]

background = load_scaled_image(
    ("kitchen.jpg", "kitvhen.jpg", "kitchen.png"),
    (WIDTH, HEIGHT),
    alpha=False,
    fallback=lambda: pygame.Surface((WIDTH, HEIGHT))
)
if background.get_at((0, 0))[:3] == (0, 0, 0) and asset_path("kitchen.jpg", "kitvhen.jpg", "kitchen.png") is None:
    background.fill((40, 70, 60))

img_dead = load_scaled_image(
    ("image_7a6a3b.png", "dead_face.png", "dead-face.png"),
    (45, 45),
    alpha=True,
    fallback=make_dead_face
)

# Prefer a real animated GIF, but retain compatibility with the old JPG name.
crying_frames, crying_durations = load_gif_frames(
    ("stick-figure-crying.gif", "crying.gif", "stick-figure-crying.jpg", "stick-figure-crying.png"),
    (250, 350)
)
if not crying_frames:
    fallback = pygame.Surface((250, 350), pygame.SRCALPHA)
    fallback.fill((100, 0, 0, 230))
    crying_frames, crying_durations = [fallback], [100]
crying_frame_index = 0
crying_frame_elapsed = 0
crying_last_tick = pygame.time.get_ticks()

# GAME STATE
class GameState:
    def __init__(self):
        self.phase_list = ["TUTORIAL", "TRAINING", "STORM", "GAME_OVER"]
        self.phase_index = 0
        self.phase = self.phase_list[self.phase_index]
        self.sub_phase = "MAIN"  
        
        self.time_left = 120  
        self.money = 50
        self.food_crates = 5
        self.med_crates = 3
        self.patients = 2
        self.joy = 75.0
        self.power_issues = 1
        
        self.instruction_text = ""
        self.alert_bg_flash = False 
        self.dead_count = 0  

        # Tutorial discovery state. The first click on each panel explains it;
        # a later click performs the normal action.
        self.tutorial_panels_seen = set()
        self.tutorial_panel_count = 5
        self.panic_timer = 0  # Forces the crying popup to stay visible for a set time
        
        # Med mini-game variables
        self.mg_time_left = 30
        self.mg_slider_pos = 200
        self.mg_slider_direction = 6
        self.mg_target_pos = random.randint(220, 580)
        self.mg_target_width = 40
        self.mg_is_glitched = False  
        
        # Power mini-game variables
        self.pg_time_left = 30
        self.pg_circles = []  
        self.pg_selected_indices = []
        
        # Money mini-game variables
        self.mny_time_left = 15
        self.mny_ingredients = [] 
        self.mny_score = 0
        # Kitchen ingredients have different cash values. The tier controls
        # the panel color so players can quickly prioritize valuable items.
        self.ingredient_values = {
            "Rice": 3,       # Low value
            "Veggies": 5,    # Low value
            "Milk": 6,       # Medium value
            "Eggs": 7,       # Medium value
            "Sugar": 8,      # High value
            "Flour": 10,     # High value
        }
        self.ingredient_pool = list(self.ingredient_values.keys())
        
        # A dedicated seeded generator keeps camp fluctuations uniform and
        # independent from the mini-game randomness. A fresh seed is used for
        # each session, while all draws from that seed remain reproducible.
        self.fluctuation_seed = random.SystemRandom().randrange(1, 2**31)
        self.fluctuation_rng = random.Random(self.fluctuation_seed)
        self.fluctuation_tick = 0
        self.next_fluctuation = {
            "budget": 2,
            "food": 4,
            "meds": 5,
            "patients": 4,
            "power": 5,
        }

        # Session analytics and end-screen state
        self.session_started_ms = pygame.time.get_ticks()
        self.activity_log = []
        self.log_scroll = 0
        self.log_saved_path = None
        self.game_over_logged = False
        self.stats = {
            "clicks": 0,
            "food_purchased": 0,
            "meds_purchased": 0,
            "medical_attempts": 0,
            "medical_successes": 0,
            "medical_failures": 0,
            "power_attempts": 0,
            "power_pairs_correct": 0,
            "power_pairs_wrong": 0,
            "power_repairs": 0,
            "kitchen_shifts": 0,
            "ingredients_collected": 0,
            "cash_earned": 0,
            "deaths": 0,
            "time_penalties": 0,
        }
        self.phase_start_ms = pygame.time.get_ticks()
        self.phase_durations = {"TUTORIAL": 0, "TRAINING": 0, "STORM": 0}

        self.update_phase_setup()
        self.log_event("SESSION", "Game session started")


    def elapsed_seconds(self):
        return max(0, (pygame.time.get_ticks() - self.session_started_ms) // 1000)

    def log_event(self, category, description):
        self.activity_log.append({
            "elapsed": self.elapsed_seconds(),
            "phase": self.phase,
            "category": category,
            "description": description,
            "money": self.money,
            "food": self.food_crates,
            "meds": self.med_crates,
            "patients": self.patients,
            "outages": self.power_issues,
            "morale": round(self.joy, 1),
        })

    def save_activity_log(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = BASE_DIR / f"player_activity_{timestamp}.csv"
        fieldnames = ["elapsed", "phase", "category", "description", "money", "food", "meds", "patients", "outages", "morale"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.activity_log)
        self.log_saved_path = str(path)
        return path

    def restart(self):
        self.__init__()

    def update_phase_setup(self):
        previous_phase = getattr(self, "phase", None)
        now_ms = pygame.time.get_ticks()
        if previous_phase in self.phase_durations:
            self.phase_durations[previous_phase] += max(0, (now_ms - self.phase_start_ms) // 1000)
        self.phase_start_ms = now_ms
        # Clamp the index defensively so the game always reaches GAME_OVER
        # instead of attempting to read beyond the phase list.
        self.phase_index = max(0, min(self.phase_index, len(self.phase_list) - 1))
        self.phase = self.phase_list[self.phase_index]
        self.alert_bg_flash = False
        if previous_phase and previous_phase != self.phase and hasattr(self, "activity_log"):
            self.log_event("PHASE", f"Entered {self.phase}")
        if self.phase == "TUTORIAL":
            self.time_left = 120
            self.instruction_text = (
                "TUTORIAL: You lead a survival camp inside Panda Express. "
                "Click each panel once to learn what it does. After a panel is explained, "
                "click it again to use it. Keep resources stocked and morale above 0%."
            )
        elif self.phase == "TRAINING":
            self.time_left = 240
            self.fluctuation_tick = 0
            self.next_fluctuation = {"budget": 1, "food": 2, "meds": 2, "patients": 2, "power": 3}
            self.instruction_text = "PLAYING MODULE: Your members are also on camp and living daily life, so quantities will naturally fluctuate."
        elif self.phase == "STORM":
            self.time_left = 300
            self.fluctuation_tick = 0
            self.next_fluctuation = {"budget": 1, "food": 2, "meds": 3, "patients": 2, "power": 2}
            self.instruction_text = "Half of the grid is damaged and not working. Your camp members are scared and can’t see! They’re injuring themselves in the dark and stress eating."
            self.food_crates = max(1, self.food_crates // 2)
            self.patients += 4
            self.power_issues = 4
            if ai_teammate.enabled:
                self.log_event("AI_BASELINE", ai_teammate.training_summary())
        elif self.phase == "GAME_OVER":
            self.time_left = 0
            self.sub_phase = "MAIN"
            if self.joy < 50:
                self.instruction_text = "MUTINY! Morale fell too low and the people have formed the new country of Beaverly Hillstownia. You have been exiled :)"
            else:
                self.instruction_text = "You have been a great leader who has helped the camp through storms and hardship. For your bravery, you are sacrificed to the Beaver gods so that they can enjoy your presence."
            if not self.game_over_logged:
                self.game_over_logged = True
                self.log_event("SESSION", f"Game ended with morale {self.joy:.1f}%")
                try:
                    self.save_activity_log()
                except OSError as exc:
                    print(f"Could not save activity log: {exc}")

    def show_tutorial_panel(self, panel_key):
        """Explain a panel on its first tutorial click; return True if explained."""
        if self.phase != "TUTORIAL" or panel_key in self.tutorial_panels_seen:
            return False

        explanations = {
            "money": (
                "KITCHEN PREP: Catch falling ingredients to earn money. Values differ: "
                "Rice $3, Veggies $5, Milk $6, Eggs $7, Sugar $8, and Flour $10. "
                "Green items are low value, blue items are medium value, and gold items are "
                "high value—prioritize Sugar and Flour! The shift advances camp time by 30 seconds. "
                "Click this panel again to try it."
            ),
            "food": (
                "FOOD PANEL: This shows your food-crate supply. Food helps protect morale, "
                "and very low food becomes dangerous. Each crate costs $5. Earn money in "
                "Kitchen Prep, then click this panel again to buy one crate."
            ),
            "meds": (
                "BUY MEDS: This shows your medical-supply stock. Treatments need a reliable "
                "supply reserve, and low medicine hurts camp morale. Each medical crate costs $10. "
                "Click this panel again when you have enough money."
            ),
            "heal": (
                "SAFETY / TREAT SICK: This shows how many camp members need treatment. "
                "Clicking it starts the surgery timing game. Align the moving white bar with "
                "the green target and press SPACE. Treatment advances time by 30 seconds. "
                "Click again to practice."
            ),
            "power": (
                "POWER PANEL: This shows active grid outages. Too many outages lower morale. "
                "The repair game asks you to match identical colored nodes; completing all pairs "
                "repairs one outage and advances time by 30 seconds. Click again to practice."
            ),
        }
        self.tutorial_panels_seen.add(panel_key)
        progress = len(self.tutorial_panels_seen)
        suffix = f"  Tutorial panels explored: {progress}/{self.tutorial_panel_count}."
        if progress == self.tutorial_panel_count:
            suffix += " Great—you now know every control. Practice them before time runs out!"
        self.instruction_text = explanations[panel_key] + suffix
        self.log_event("TUTORIAL", f"Explored {panel_key} panel")
        return True

    def trigger_death_panic(self, message):
        """Activates the full-screen visual panic mode when a patient dies."""
        self.dead_count += 1
        self.stats["deaths"] += 1
        self.joy = max(0.0, self.joy - 20.0)
        self.instruction_text = message
        self.alert_bg_flash = True
        self.panic_timer = 90  # 3 continuous seconds of panic
        self.log_event("MEDICAL", "Patient died; morale penalty applied")

    def apply_time_penalty(self):
        self.stats["time_penalties"] += 1
        self.log_event("TIME", "30-second time penalty applied")
        self.time_left -= 30
        if self.time_left <= 0:
            self.phase_index = min(self.phase_index + 1, len(self.phase_list) - 1)
            self.update_phase_setup()

    def start_medical_minigame(self):
        self.sub_phase = "MED_MINIGAME"
        self.stats["medical_attempts"] += 1
        self.log_event("ACTION", "Started medical treatment")
        ai_teammate.begin_attempt("medical", self.phase)
        self.mg_time_left = 30
        self.mg_slider_pos = 200
        self.mg_slider_direction = 7 if self.phase == "STORM" else 6
        self.alert_bg_flash = False
        
        if self.phase == "STORM" and random.random() < 0.15:
            self.mg_is_glitched = True
            self.instruction_text = "SURGERY FAILED: DEFIBRILLATOR CIRCUIT GLITCH ENCOUNTERED!"
        else:
            self.mg_is_glitched = False
            self.instruction_text = "SURGERY: Align the moving white bar over the green target and hit SPACEBAR!"
        
        if self.phase == "STORM":
            self.mg_target_width = 15
        else:
            self.mg_target_width = 40
            
        self.mg_target_pos = random.randint(220, 600 - self.mg_target_width)

    def start_power_minigame(self):
        self.sub_phase = "POWER_MINIGAME"
        self.stats["power_attempts"] += 1
        self.log_event("ACTION", "Started power repair")
        ai_teammate.begin_attempt("power", self.phase)
        self.pg_time_left = 30
        self.pg_circles = []
        self.pg_selected_indices = []
        self.alert_bg_flash = False
        
        if self.phase == "STORM":
            positions = []
            for x in [240, 360, 480, 600]:
                for y in [240, 315, 390]:
                    positions.append((x, y))
            random.shuffle(positions)
            
            pool = []
            red_shades = [
                (255, 0, 0), (200, 20, 20), (150, 0, 0),     
                (255, 80, 80), (255, 120, 120), (110, 10, 10)    
            ]
            for shade in red_shades:
                pool.extend([shade, shade])
        else:
            positions = [(280, 270), (400, 270), (520, 270), (280, 390), (400, 390), (520, 390)]
            random.shuffle(positions)
            color_pair1, color_pair2, color_pair3 = RED, GREEN, (0, 100, 255)
            pool = [color_pair1, color_pair1, color_pair2, color_pair2, color_pair3, color_pair3]
            
        for i in range(len(positions)):
            self.pg_circles.append({'pos': positions[i], 'color': pool[i], 'active': True})
            
        self.instruction_text = "POWER REPAIR: Link identical node colors to complete the circuit block."

    def start_money_minigame(self):
        self.sub_phase = "MONEY_MINIGAME"
        self.stats["kitchen_shifts"] += 1
        self.log_event("ACTION", "Started kitchen shift")
        ai_teammate.begin_attempt("kitchen", self.phase)
        self.mny_time_left = 15
        self.mny_score = 0
        self.mny_ingredients = []
        self.alert_bg_flash = False
        self.instruction_text = (
            "KITCHEN PREP: Click ingredients before they hit the floor! "
            "LOW/GREEN: Rice $3, Veggies $5 | MEDIUM/BLUE: Milk $6, Eggs $7 | "
            "HIGH/GOLD: Sugar $8, Flour $10. Prioritize the gold ingredients!"
        )

    def _schedule_next_fluctuation(self, name, minimum, maximum):
        """Schedule the next event using an inclusive uniform interval."""
        self.next_fluctuation[name] = (
            self.fluctuation_tick
            + self.fluctuation_rng.randint(minimum, maximum)
        )

    def _morale_condition_pressure(self):
        """Return combined morale pressure from all important camp conditions."""
        pressure = 0.0

        # Food availability
        if self.food_crates <= 0:
            pressure -= 0.85
        elif self.food_crates == 1:
            pressure -= 0.55
        elif self.food_crates == 2:
            pressure -= 0.30
        elif self.food_crates >= 5:
            pressure += 0.20

        # Medical supplies
        if self.med_crates <= 0:
            pressure -= 0.75
        elif self.med_crates == 1:
            pressure -= 0.48
        elif self.med_crates == 2:
            pressure -= 0.25
        elif self.med_crates >= 4:
            pressure += 0.15

        # Patients and power outages
        pressure += 0.18 if self.patients == 0 else -min(0.80, self.patients * 0.11)
        pressure += 0.18 if self.power_issues == 0 else -min(0.85, self.power_issues * 0.14)

        # Budget health
        if self.money <= 0:
            pressure -= 0.55
        elif self.money < 10:
            pressure -= 0.35
        elif self.money < 25:
            pressure -= 0.16
        elif self.money >= 60:
            pressure += 0.20
        elif self.money >= 40:
            pressure += 0.10

        # Deaths permanently make morale harder to maintain.
        pressure -= min(0.45, self.dead_count * 0.09)
        return pressure

    def handle_training_fluctuations(self):
        """Small, frequent, uniformly random changes during TRAINING only."""
        self.fluctuation_tick += 1
        rng = self.fluctuation_rng

        # Morale always changes and is strongly tied to the whole camp state.
        pressure = self._morale_condition_pressure()
        morale_delta = rng.uniform(-0.95, 0.95) + (pressure * 0.95)
        morale_delta = max(-2.6, min(2.2, morale_delta))
        if abs(morale_delta) < 0.18:
            morale_delta = 0.18 if rng.random() < 0.5 else -0.18
        self.joy = max(0.0, min(100.0, self.joy + morale_delta))

        # Each resource uses a uniformly selected interval, so changes are
        # continuous without every value jumping on exactly the same second.
        if self.fluctuation_tick >= self.next_fluctuation["budget"]:
            delta = rng.choice((-2, -1, 1, 2))
            self.money = max(0, min(999, self.money + delta))
            self._schedule_next_fluctuation("budget", 1, 3)

        if self.fluctuation_tick >= self.next_fluctuation["food"]:
            delta = rng.choice((-1, 1))
            if self.food_crates <= 0:
                delta = 1
            self.food_crates = max(0, min(9, self.food_crates + delta))
            self._schedule_next_fluctuation("food", 1, 3)

        if self.fluctuation_tick >= self.next_fluctuation["meds"]:
            delta = rng.choice((-1, 1))
            if self.med_crates <= 0:
                delta = 1
            self.med_crates = max(0, min(8, self.med_crates + delta))
            self._schedule_next_fluctuation("meds", 1, 3)

        if self.fluctuation_tick >= self.next_fluctuation["patients"]:
            delta = rng.choice((-1, 1))
            if self.patients <= 0:
                delta = 1
            self.patients = max(0, min(12, self.patients + delta))
            self._schedule_next_fluctuation("patients", 1, 3)

        if self.fluctuation_tick >= self.next_fluctuation["power"]:
            delta = rng.choice((-1, 1))
            if self.power_issues <= 0:
                delta = 1
            self.power_issues = max(0, min(6, self.power_issues + delta))
            self._schedule_next_fluctuation("power", 1, 3)

    def handle_storm_fluctuations(self):
        """During STORM, random environmental changes can only make things worse."""
        self.fluctuation_tick += 1
        rng = self.fluctuation_rng

        # Morale drops every second. Good supplies can slow the decline, but
        # environmental randomness can never raise morale during the storm.
        pressure = self._morale_condition_pressure()
        condition_burden = max(0.0, -pressure)
        morale_loss = rng.uniform(0.55, 1.15) + condition_burden * 0.80
        self.joy = max(0.0, self.joy - min(3.0, morale_loss))

        if self.fluctuation_tick >= self.next_fluctuation["budget"]:
            self.money = max(0, self.money - rng.randint(1, 2))
            self._schedule_next_fluctuation("budget", 1, 2)

        if self.fluctuation_tick >= self.next_fluctuation["food"]:
            if self.food_crates > 0:
                self.food_crates -= 1
            self._schedule_next_fluctuation("food", 2, 4)

        if self.fluctuation_tick >= self.next_fluctuation["meds"]:
            if self.med_crates > 0:
                self.med_crates -= 1
            self._schedule_next_fluctuation("meds", 2, 4)

        if self.fluctuation_tick >= self.next_fluctuation["patients"]:
            self.patients = min(12, self.patients + 1)
            self._schedule_next_fluctuation("patients", 1, 3)

        if self.fluctuation_tick >= self.next_fluctuation["power"]:
            self.power_issues = min(6, self.power_issues + 1)
            self._schedule_next_fluctuation("power", 1, 3)

    def tick_timer(self):
        if self.phase == "GAME_OVER":
            return
            
        if self.sub_phase == "MAIN" and self.joy <= 0:
            self.phase_index = 3
            self.update_phase_setup()
            
        if self.sub_phase == "MED_MINIGAME":
            self.mg_time_left -= 1
            if self.mg_time_left <= 0: 
                if random.random() < 0.40:
                    state.patients = max(0, state.patients - 1)
                    state.stats["medical_failures"] += 1
                    state.trigger_death_panic("SURGERY FAILURE: Time expired. Equipment failed and the patient died! Morale plummeted (-20.0%)")
                else:
                    state.joy = max(0.0, state.joy - 6.0)
                    state.stats["medical_failures"] += 1
                    state.instruction_text = "MISSED! Time expired. Suture slipped and infection flared up."
                    state.log_event("MEDICAL", "Treatment timed out")
                ai_teammate.end_attempt("medical")
                self.sub_phase = "MAIN"
                self.apply_time_penalty()
        elif self.sub_phase == "POWER_MINIGAME":
            self.pg_time_left -= 1
            if self.pg_time_left <= 0:
                self.log_event("POWER", "Power repair timed out")
                ai_teammate.end_attempt("power")
                self.sub_phase = "MAIN"
                self.apply_time_penalty()
        elif self.sub_phase == "MONEY_MINIGAME":
            self.mny_time_left -= 1
            if self.mny_time_left <= 0:
                self.money += self.mny_score
                self.stats["cash_earned"] += self.mny_score
                self.log_event("KITCHEN", f"Kitchen shift ended; earned ${self.mny_score}")
                self.instruction_text = f"Shift over! You prepared rations and earned +${self.mny_score}."
                ai_teammate.end_attempt("kitchen")
                self.sub_phase = "MAIN"
                self.apply_time_penalty()
        else:
            self.time_left -= 1
            if self.phase == "TRAINING":
                self.handle_training_fluctuations()
            elif self.phase == "STORM":
                self.handle_storm_fluctuations()
            # TUTORIAL intentionally has no automatic fluctuations.
                
            if self.time_left <= 0:
                self.phase_index = min(self.phase_index + 1, len(self.phase_list) - 1)
                self.update_phase_setup()

    def update_animations(self):
        # Handle the panic animation frames down counter
        if self.panic_timer > 0:
            self.panic_timer -= 1
            if self.panic_timer <= 0:
                self.alert_bg_flash = False

        if self.sub_phase == "MED_MINIGAME":
            if self.mg_is_glitched:
                self.mg_slider_pos = 600
            else:
                self.mg_slider_pos += self.mg_slider_direction
                if self.mg_slider_pos >= 600 or self.mg_slider_pos <= 200:
                    self.mg_slider_direction *= -1
                    
        elif self.sub_phase == "MONEY_MINIGAME":
            if random.random() < 0.05 and len(self.mny_ingredients) < 4:
                spawn_x = random.randint(200, 550)
                speed = random.randint(5, 9) if self.phase == "STORM" else random.randint(2, 5)
                ingredient_name = random.choice(self.ingredient_pool)
                self.mny_ingredients.append({
                    'rect': pygame.Rect(spawn_x, 180, 100, 38),
                    'speed': speed,
                    'name': ingredient_name,
                    'value': self.ingredient_values[ingredient_name]
                })
            for item in self.mny_ingredients[:]:
                item['rect'].y += item['speed']
                if item['rect'].y > 460:  
                    self.mny_ingredients.remove(item)

state = GameState()
ai_teammate = AITeammate()

# RENDERING MODULES
def draw_panel_button(screen, rect, title, lines, mouse_pos, line_colors=None, warning=False):
    hover = rect.collidepoint(mouse_pos)
    if warning:
        color = (175, 35, 45) if hover else (135, 20, 30)
        border_color = (255, 170, 170)
        title_color = WHITE
        body_color = WHITE
        border_width = 3
    elif state.phase == "STORM":
        color = STORM_PANEL_HOVER if hover else STORM_PANEL
        border_color = STORM_BORDER
        title_color = STORM_TITLE
        body_color = STORM_TEXT
        border_width = 1
    else:
        color = (60, 80, 90) if hover else (40, 50, 55)
        border_color = LIGHT_GRAY
        title_color = WHITE
        body_color = LIGHT_GRAY
        border_width = 2

    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, border_color, rect, width=border_width, border_radius=10)

    title_surf = FONT_PANEL_TITLE.render(title, True, title_color)
    screen.blit(title_surf, (rect.x + 14, rect.y + 10))
    for i, line in enumerate(lines):
        text_color = body_color
        if line_colors and i < len(line_colors) and line_colors[i] is not None:
            text_color = line_colors[i]
        line_surf = FONT_PANEL_BODY.render(line, True, text_color)
        screen.blit(line_surf, (rect.x + 14, rect.y + 42 + (i * 21)))
    return hover

def draw_text_wrapped(screen, text, font, color, rect):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] < rect.width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)
    
    y_offset = rect.y
    for line in lines:
        text_surface = font.render(line.strip(), True, color)
        screen.blit(text_surface, (rect.x, y_offset))
        y_offset += font.get_linesize()

def draw_instruction_panel():
    """Draw the instruction banner last so it stays visible above every overlay."""
    instruction_rect = pygame.Rect(38, 8, 924, 102)

    # The STORM module always uses an urgent angry-red banner with white text.
    if state.phase == "STORM":
        banner_color = (155, 0, 15)
        banner_border = (255, 220, 220)
        title_color = WHITE
        body_color = WHITE
    elif state.alert_bg_flash:
        banner_color = (125, 0, 0)
        banner_border = WHITE
        title_color = WHITE
        body_color = WHITE
    else:
        banner_color = (12, 24, 38)
        banner_border = (255, 215, 0)
        title_color = GOLD
        body_color = WHITE

    # Strong shadow, thick border, and bold type keep instructions bold and easier to seee.
    shadow_rect = instruction_rect.move(4, 4)
    pygame.draw.rect(screen, (0, 0, 0), shadow_rect, border_radius=9)
    pygame.draw.rect(screen, banner_color, instruction_rect, border_radius=9)
    pygame.draw.rect(screen, banner_border, instruction_rect, width=4, border_radius=9)

    title = FONT_INSTRUCTION_TITLE.render("INSTRUCTIONS", True, title_color)
    screen.blit(title, (instruction_rect.x + 16, instruction_rect.y + 9))

    text_bounds = pygame.Rect(
        instruction_rect.x + 16,
        instruction_rect.y + 34,
        instruction_rect.width - 32,
        instruction_rect.height - 40,
    )
    draw_text_wrapped(screen, state.instruction_text, FONT_INSTRUCTION, body_color, text_bounds)


def draw_medical_overlay():
    mg_rect = pygame.Rect(150, 150, 700, 350)
    panel_color = STORM_OVERLAY if state.phase == "STORM" else (30, 30, 40)
    border_color = STORM_BORDER if state.phase == "STORM" else WHITE
    title_color = STORM_TITLE if state.phase == "STORM" else WHITE
    pygame.draw.rect(screen, panel_color, mg_rect, border_radius=12)
    pygame.draw.rect(screen, border_color, mg_rect, width=2 if state.phase == "STORM" else 3, border_radius=12)
    
    title = FONT_LARGE.render(f"SURGERY THEATER - TIME: {state.mg_time_left}s", True, title_color)
    screen.blit(title, (180, 180))
    track_color = STORM_TRACK if state.phase == "STORM" else (70, 70, 70)
    target_color = STORM_TARGET if state.phase == "STORM" else GREEN
    pygame.draw.rect(screen, track_color, pygame.Rect(200, 280, 400, 40))
    pygame.draw.rect(screen, target_color, pygame.Rect(state.mg_target_pos, 280, state.mg_target_width, 40))
    
    color = STORM_WARNING if state.mg_is_glitched and state.phase == "STORM" else (RED if state.mg_is_glitched else (STORM_TITLE if state.phase == "STORM" else WHITE))
    pygame.draw.rect(screen, color, pygame.Rect(state.mg_slider_pos, 270, 8, 60))
    ai_teammate.draw_medical_suggestion(screen, state)
    
    if state.mg_is_glitched:
        warning_color = STORM_WARNING if state.phase == "STORM" else RED
        warning_msg = FONT_MED.render("SYSTEM FAILURE: HARDWARE FROZEN. Press SPACEBAR to pull plug.", True, warning_color)
        screen.blit(warning_msg, (200, 370))

def draw_power_overlay(mouse_pos):
    pg_rect = pygame.Rect(150, 150, 700, 350)
    panel_color = STORM_OVERLAY if state.phase == "STORM" else (25, 35, 45)
    border_color = STORM_BORDER if state.phase == "STORM" else WHITE
    title_color = STORM_TITLE if state.phase == "STORM" else WHITE
    pygame.draw.rect(screen, panel_color, pg_rect, border_radius=12)
    pygame.draw.rect(screen, border_color, pg_rect, width=2 if state.phase == "STORM" else 3, border_radius=12)
    
    title = FONT_LARGE.render(f"POWER PANEL NODE - TIME: {state.pg_time_left}s", True, title_color)
    screen.blit(title, (180, 170))
    
    hovered_idx = -1
    radius = 24 if state.phase == "STORM" else 35
    
    for idx, circ in enumerate(state.pg_circles):
        if not circ['active']: continue
        x, y = circ['pos']
        dist = ((mouse_pos[0] - x)**2 + (mouse_pos[1] - y)**2)**0.5
        is_selected = idx in state.pg_selected_indices
        if dist <= radius:
            hovered_idx = idx
            pygame.draw.circle(screen, circ['color'], (x, y), radius + 4)
        else:
            pygame.draw.circle(screen, circ['color'], (x, y), radius)
        if is_selected:
            selection_color = STORM_TITLE if state.phase == "STORM" else WHITE
            pygame.draw.circle(screen, selection_color, (x, y), radius + 4, width=3 if state.phase == "STORM" else 4)
        else:
            outline_color = STORM_BORDER if state.phase == "STORM" else LIGHT_GRAY
            pygame.draw.circle(screen, outline_color, (x, y), radius, width=1 if state.phase == "STORM" else 2)
    ai_teammate.draw_power_suggestion(screen, state, radius)
    return hovered_idx

def draw_money_overlay(mouse_pos):
    box_rect = pygame.Rect(150, 150, 700, 350)
    panel_color = STORM_OVERLAY if state.phase == "STORM" else (45, 40, 30)
    border_color = STORM_BORDER if state.phase == "STORM" else GOLD
    title_color = STORM_TITLE if state.phase == "STORM" else WHITE
    pygame.draw.rect(screen, panel_color, box_rect, border_radius=12)
    pygame.draw.rect(screen, border_color, box_rect, width=2 if state.phase == "STORM" else 3, border_radius=12)
    
    title = FONT_LARGE.render(f"KITCHEN PREP - TIME: {state.mny_time_left}s | Cash Earned: ${state.mny_score}", True, title_color)
    screen.blit(title, (170, 170))
    pygame.draw.rect(screen, (70, 60, 50), pygame.Rect(180, 210, 640, 260), width=1)
    
    hovered_item = None
    ai_priority_ids = ai_teammate.kitchen_priority_ids(state.mny_ingredients)
    for item in state.mny_ingredients:
        is_hover = item['rect'].collidepoint(mouse_pos)
        value = item['value']

        # Outside the storm, value tiers are strongly color coded:
        # green = low, blue = medium, gold = high.
        if value <= 5:
            base_color = (78, 170, 95)
            hover_color = (105, 205, 120)
            tier = "LOW"
        elif value <= 7:
            base_color = (75, 135, 205)
            hover_color = (105, 165, 235)
            tier = "MED"
        else:
            base_color = (230, 177, 55)
            hover_color = (255, 210, 75)
            tier = "HIGH"

        if state.phase == "STORM":
            # The storm deliberately removes the bright value colors. Every
            # ingredient becomes low-contrast gray, making visual searching
            # harder while its name, tier, and dollar value remain readable.
            base_color = (91, 94, 93)
            hover_color = (108, 111, 109)
            label_color = (177, 180, 174)
            item_border = (121, 124, 121)
            if id(item) in ai_priority_ids:
                base_color = (218, 165, 35)
                hover_color = (255, 210, 65)
                label_color = BLACK
                item_border = (255, 245, 120)
        else:
            label_color = WHITE if value <= 7 else BLACK
            item_border = WHITE

        color = hover_color if is_hover else base_color
        pygame.draw.rect(screen, color, item['rect'], border_radius=6)
        pygame.draw.rect(
            screen,
            item_border,
            item['rect'],
            width=2 if is_hover else 1,
            border_radius=6
        )

        label = f"{item['name']}  ${value}"
        lbl = FONT_SMALL.render(label, True, label_color)
        screen.blit(lbl, lbl.get_rect(center=item['rect'].center))

        if is_hover:
            hovered_item = item

    return hovered_item

def draw_end_screen(mouse_pos):
    screen.fill((24, 28, 30))
    pygame.draw.rect(screen, (39, 45, 47), pygame.Rect(25, 20, 950, 610), border_radius=12)
    pygame.draw.rect(screen, (132, 140, 139), pygame.Rect(25, 20, 950, 610), width=2, border_radius=12)

    outcome = "MUTINY" if state.joy < 50 else "VICTORY"
    title = FONT_XL.render(f"SESSION COMPLETE — {outcome}", True, (220, 222, 215))
    screen.blit(title, (50, 38))

    ending_message = state.instruction_text
    ending_rect = pygame.Rect(55, 88, 890, 62)
    draw_text_wrapped(screen, ending_message, FONT_MED, (202, 205, 198), ending_rect)

    summary_lines = [
        f"Final morale: {state.joy:.1f}%",
        f"Final budget: ${state.money}",
        f"Deaths: {state.dead_count}",
        f"Patients remaining: {state.patients}",
        f"Power outages remaining: {state.power_issues}",
        f"Total recorded events: {len(state.activity_log)}",
    ]
    for i, line in enumerate(summary_lines):
        screen.blit(FONT_SMALL.render(line, True, (188, 193, 188)), (55 + (i % 3) * 285, 154 + (i // 3) * 22))

    stat_rect = pygame.Rect(45, 205, 300, 320)
    log_rect = pygame.Rect(365, 205, 590, 320)
    pygame.draw.rect(screen, (31, 36, 38), stat_rect, border_radius=8)
    pygame.draw.rect(screen, (31, 36, 38), log_rect, border_radius=8)
    pygame.draw.rect(screen, (93, 101, 101), stat_rect, width=1, border_radius=8)
    pygame.draw.rect(screen, (93, 101, 101), log_rect, width=1, border_radius=8)

    screen.blit(FONT_PANEL_TITLE.render("PLAYER PERFORMANCE", True, (202, 205, 198)), (60, 220))
    stats_to_show = [
        ("Total clicks", state.stats["clicks"]),
        ("Food crates bought", state.stats["food_purchased"]),
        ("Medical supplies bought", state.stats["meds_purchased"]),
        ("Treatments attempted", state.stats["medical_attempts"]),
        ("Treatments successful", state.stats["medical_successes"]),
        ("Treatment failures", state.stats["medical_failures"]),
        ("Power repairs started", state.stats["power_attempts"]),
        ("Correct node pairs", state.stats["power_pairs_correct"]),
        ("Wrong node pairs", state.stats["power_pairs_wrong"]),
        ("Outages repaired", state.stats["power_repairs"]),
        ("Kitchen shifts", state.stats["kitchen_shifts"]),
        ("Ingredients collected", state.stats["ingredients_collected"]),
        ("Cash earned", f'${state.stats["cash_earned"]}'),
        ("Time penalties", state.stats["time_penalties"]),
    ]
    for i, (label, value) in enumerate(stats_to_show):
        y = 248 + i * 19
        screen.blit(FONT_SMALL.render(label, True, (158, 165, 161)), (60, y))
        value_surf = FONT_SMALL.render(str(value), True, (210, 212, 205))
        screen.blit(value_surf, (325 - value_surf.get_width(), y))

    screen.blit(FONT_PANEL_TITLE.render("ACTIVITY LOG", True, (202, 205, 198)), (380, 220))
    visible_rows = 15
    max_scroll = max(0, len(state.activity_log) - visible_rows)
    state.log_scroll = max(0, min(state.log_scroll, max_scroll))
    start = max(0, len(state.activity_log) - visible_rows - state.log_scroll)
    entries = state.activity_log[start:start + visible_rows]
    for i, entry in enumerate(entries):
        minutes, seconds = divmod(entry["elapsed"], 60)
        line = f'{minutes:02d}:{seconds:02d} [{entry["phase"][:5]}] {entry["category"]}: {entry["description"]}'
        if len(line) > 74:
            line = line[:71] + "..."
        screen.blit(FONT_MONO.render(line, True, (165, 171, 167)), (380, 248 + i * 18))

    hint = "Mouse wheel: scroll activity log"
    screen.blit(FONT_SMALL.render(hint, True, (128, 135, 133)), (380, 500))

    restart_rect = pygame.Rect(400, 550, 160, 48)
    save_rect = pygame.Rect(580, 550, 160, 48)
    quit_rect = pygame.Rect(760, 550, 160, 48)
    for rect, label in [(restart_rect, "RESTART"), (save_rect, "SAVE CSV"), (quit_rect, "QUIT")]:
        hovered = rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (76, 84, 84) if hovered else (60, 67, 68), rect, border_radius=7)
        pygame.draw.rect(screen, (147, 153, 150), rect, width=1, border_radius=7)
        label_surf = FONT_PANEL_TITLE.render(label, True, (218, 220, 214))
        screen.blit(label_surf, label_surf.get_rect(center=rect.center))

    status = f"CSV: {state.log_saved_path}" if state.log_saved_path else "CSV will also save automatically at game end."
    if len(status) > 100:
        status = status[:97] + "..."
    screen.blit(FONT_SMALL.render(status, True, (137, 145, 141)), (50, 607))
    return restart_rect, save_rect, quit_rect


# MAIN RUN LOOP

clock = pygame.time.Clock()
TIMER_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(TIMER_EVENT, 1000)

running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    clicked = False
    space_pressed = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == TIMER_EVENT:
            state.tick_timer()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked = True
                state.stats["clicks"] += 1
            elif state.phase == "GAME_OVER" and event.button == 4:
                state.log_scroll += 3
            elif state.phase == "GAME_OVER" and event.button == 5:
                state.log_scroll -= 3
        elif event.type == pygame.KEYDOWN:
            if (event.key == pygame.K_a and
                    (event.mod & pygame.KMOD_CTRL) and
                    (event.mod & pygame.KMOD_SHIFT)):
                ai_teammate.toggle(state)
            elif event.key == pygame.K_SPACE: 
                space_pressed = True
            elif event.key == pygame.K_1:
                state.phase_index = 0
                state.update_phase_setup()
            elif event.key == pygame.K_2:
                state.phase_index = 1
                state.update_phase_setup()
            elif event.key == pygame.K_3:
                state.phase_index = 2
                state.update_phase_setup()
                
    current_tick = pygame.time.get_ticks()
    dt = current_tick - crying_last_tick
    crying_last_tick = current_tick
    state.update_animations()
    ai_teammate.update(state)

    if state.phase == "GAME_OVER":
        restart_rect, save_rect, quit_rect = draw_end_screen(mouse_pos)
        if clicked:
            if restart_rect.collidepoint(mouse_pos):
                state.restart()
            elif save_rect.collidepoint(mouse_pos):
                try:
                    saved = state.save_activity_log()
                    state.log_event("SESSION", f"Activity CSV saved as {saved.name}")
                except OSError as exc:
                    state.log_event("ERROR", f"Could not save CSV: {exc}")
            elif quit_rect.collidepoint(mouse_pos):
                running = False
        pygame.display.flip()
        clock.tick(30)
        continue

    screen.blit(background, (0, 0))
    draw_storm_visual_load()
    
    # Draw tracking dead faces starting at y=160 so they NEVER overlap text
    for d in range(state.dead_count):
        row = d // 3
        col = d % 3
        screen.blit(img_dead, (20 + col * 50, 160 + row * 50))
        
    # Main HUD elements
    minutes, seconds = max(0, state.time_left) // 60, max(0, state.time_left) % 60
    hud_color = STORM_HUD if state.phase == "STORM" else WHITE
    shadow_color = STORM_SHADOW if state.phase == "STORM" else BLACK

    left_hud = f"Budget: ${state.money}  |  Phase: {state.phase}"
    time_hud = f"Time: {minutes:02d}:{seconds:02d}"
    left_text = FONT_LARGE.render(left_hud, True, hud_color)
    left_shadow = FONT_LARGE.render(left_hud, True, shadow_color)
    time_text = FONT_LARGE.render(time_hud, True, hud_color)
    time_shadow = FONT_LARGE.render(time_hud, True, shadow_color)
    screen.blit(left_shadow, (52, 117))
    screen.blit(left_text, (50, 115))
    screen.blit(time_shadow, (487, 117))
    screen.blit(time_text, (485, 115))

    # Large, eye-catching morale badge placed beside the timer.
    morale_rect = pygame.Rect(455, 145, 220, 58)
    morale_bg = (125, 28, 38) if state.joy < 40 else ((130, 92, 20) if state.joy < 65 else (34, 105, 65))
    pygame.draw.rect(screen, morale_bg, morale_rect, border_radius=12)
    pygame.draw.rect(screen, WHITE if state.phase != "STORM" else STORM_BORDER, morale_rect, width=2, border_radius=12)
    morale_text = FONT_MORALE.render(f"MORALE {state.joy:.1f}%", True, WHITE)
    screen.blit(morale_text, morale_text.get_rect(center=morale_rect.center))

    # Larger Sidebar Panels
    panel_x = 690
    panel_w = 290
    panel_h = 86
    panel_gap = 10
    panel_y = 145

    money_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    money_hover = draw_panel_button(screen, money_rect, "Kitchen Prep", ["Work shift for extra cash funds"], mouse_pos)

    food_rect = pygame.Rect(panel_x, panel_y + (panel_h + panel_gap), panel_w, panel_h)
    food_warning = RED if state.food_crates <= 2 else None
    food_hover = draw_panel_button(
        screen, food_rect, "Food Panel",
        [f"Crates: {state.food_crates}", "Buy Crate (-$5)"], mouse_pos,
        [WHITE if food_warning else None, None],
        warning=state.food_crates <= 2
    )

    buy_med_rect = pygame.Rect(panel_x, panel_y + 2 * (panel_h + panel_gap), panel_w, panel_h)
    med_warning = RED if state.med_crates <= 2 else None
    buy_med_hover = draw_panel_button(
        screen, buy_med_rect, "Buy Meds",
        [f"In Stock: {state.med_crates}", "Buy (-$10)"], mouse_pos,
        [WHITE if med_warning else None, None],
        warning=state.med_crates <= 2
    )

    heal_rect = pygame.Rect(panel_x, panel_y + 3 * (panel_h + panel_gap), panel_w, panel_h)
    heal_hover = draw_panel_button(
        screen, heal_rect, "Safety / Treat Sick",
        [f"Patients: {state.patients}", "Cost: Free (Takes -30s)"], mouse_pos,
        [WHITE if state.patients >= 3 else None, None],
        warning=state.patients >= 3
    )

    power_rect = pygame.Rect(panel_x, panel_y + 4 * (panel_h + panel_gap), panel_w, panel_h)
    power_warning = RED if state.power_issues >= 3 else None
    power_hover = draw_panel_button(
        screen, power_rect, "Power Panel",
        [f"Outages: {state.power_issues}/6", "Fix Grid Outages"], mouse_pos,
        [WHITE if power_warning else None, None],
        warning=state.power_issues >= 3
    )

    # Sub-Phase Router
    if state.sub_phase == "MED_MINIGAME":
        draw_medical_overlay()
        if space_pressed:
            ai_teammate.record_action("medical", state.phase)
            if state.mg_is_glitched:
                state.stats["medical_failures"] += 1
                state.patients = max(0, state.patients - 1)
                state.trigger_death_panic("SURGERY FAILURE: The defibrillator grid short-circuited. Patient died! Morale fell hard (-20.0%)")
            else:
                if state.mg_target_pos <= state.mg_slider_pos <= (state.mg_target_pos + state.mg_target_width):
                    state.patients = max(0, state.patients - 1)
                    state.joy = min(100.0, state.joy + 8.0)
                    state.stats["medical_successes"] += 1
                    state.log_event("MEDICAL", "Patient stabilized successfully")
                    state.instruction_text = "SUCCESS! Patient stabilized. (Time advanced 30s)"
                else:
                    if random.random() < 0.40:
                        state.patients = max(0, state.patients - 1)
                        state.stats["medical_failures"] += 1
                        state.trigger_death_panic("SURGERY FAILURE: Suture slipped drastically and the patient died! Morale plummeted (-20.0%)")
                    else:
                        state.joy = max(0.0, state.joy - 6.0)
                        state.stats["medical_failures"] += 1
                        state.log_event("MEDICAL", "Treatment missed; patient survived")
                        state.instruction_text = "MISSED! Suture slipped, causing an unexpected minor hemorrhage."
            ai_teammate.end_attempt("medical")
            state.sub_phase = "MAIN"
            state.apply_time_penalty()
            
    elif state.sub_phase == "POWER_MINIGAME":
        hovered_circ_idx = draw_power_overlay(mouse_pos)
        if clicked and hovered_circ_idx != -1:
            ai_teammate.record_action("power", state.phase)
            if hovered_circ_idx not in state.pg_selected_indices:
                state.pg_selected_indices.append(hovered_circ_idx)
            if len(state.pg_selected_indices) == 2:
                idx1, idx2 = state.pg_selected_indices
                if state.pg_circles[idx1]['color'] == state.pg_circles[idx2]['color']:
                    state.stats["power_pairs_correct"] += 1
                    state.log_event("POWER", "Matched a correct node pair")
                    state.pg_circles[idx1]['active'] = False
                    state.pg_circles[idx2]['active'] = False
                else:
                    state.stats["power_pairs_wrong"] += 1
                    state.log_event("POWER", "Selected an incorrect node pair")
                    state.joy = max(0.0, state.joy - 3.0)
                state.pg_selected_indices = []
            if all(not c['active'] for c in state.pg_circles):
                state.power_issues = max(0, state.power_issues - 1)
                state.stats["power_repairs"] += 1
                state.log_event("POWER", "Completed a power-grid repair")
                state.joy = min(100.0, state.joy + 5.0)
                ai_teammate.end_attempt("power")
                state.sub_phase = "MAIN"
                state.apply_time_penalty()
                
    elif state.sub_phase == "MONEY_MINIGAME":
        hovered_item = draw_money_overlay(mouse_pos)
        if clicked and hovered_item:
            ai_teammate.record_action("kitchen", state.phase)
            ingredient_value = hovered_item['value']
            state.mny_score += ingredient_value
            state.stats["ingredients_collected"] += 1
            state.log_event(
                "KITCHEN",
                f"Collected {hovered_item['name']} worth ${ingredient_value}"
            )
            if ai_teammate.is_assisting("kitchen"):
                state.instruction_text = (
                    f"COLLECTED {hovered_item['name'].upper()}! +${ingredient_value}. "
                    "AI SUGGESTION remains active: glowing gold foods are high-value "
                    "or efficient nearby choices. You still choose and click them yourself."
                )
            else:
                state.instruction_text = (
                    f"COLLECTED {hovered_item['name'].upper()}! +${ingredient_value}. "
                    "Values: Rice $3, Veggies $5, Milk $6, Eggs $7, Sugar $8, Flour $10. "
                    "Gold ingredients are worth the most!"
                )
            state.mny_ingredients.remove(hovered_item)
            
    else:
        if clicked and state.phase != "GAME_OVER":
            if money_hover:
                if not state.show_tutorial_panel("money"):
                    state.start_money_minigame()
            elif food_hover:
                if not state.show_tutorial_panel("food"):
                    if state.money >= 5:
                        state.money -= 5
                        state.food_crates += 1
                        state.stats["food_purchased"] += 1
                        state.log_event("PURCHASE", "Bought one food crate for $5")
                    else:
                        state.instruction_text = "NOT ENOUGH MONEY: A food crate costs $5. Use Kitchen Prep to earn more cash."
            elif buy_med_hover:
                if not state.show_tutorial_panel("meds"):
                    if state.money >= 10:
                        state.money -= 10
                        state.med_crates += 1
                        state.stats["meds_purchased"] += 1
                        state.log_event("PURCHASE", "Bought one medical crate for $10")
                    else:
                        state.instruction_text = "NOT ENOUGH MONEY: Medical supplies cost $10. Use Kitchen Prep to earn more cash."
            elif heal_hover:
                if not state.show_tutorial_panel("heal"):
                    if state.patients > 0:
                        state.start_medical_minigame()
                    else:
                        state.instruction_text = "NO PATIENTS: Everyone is currently healthy. Check this panel again when someone becomes sick."
            elif power_hover:
                if not state.show_tutorial_panel("power"):
                    if state.power_issues > 0:
                        state.start_power_minigame()
                    else:
                        state.instruction_text = "GRID STABLE: There are no power outages to repair right now."

    # Render the crying popup overlay on top of EVERYTHING during active panic frames
    if state.alert_bg_flash:
        crying_frame_elapsed += dt
        while crying_frame_elapsed >= crying_durations[crying_frame_index]:
            crying_frame_elapsed -= crying_durations[crying_frame_index]
            crying_frame_index = (crying_frame_index + 1) % len(crying_frames)

        # Keep the panic GIF visible without covering the morale badge or timer.
        panic_popup_rect = crying_frames[crying_frame_index].get_rect()
        panic_popup_rect.topleft = (170, 220)
        screen.blit(crying_frames[crying_frame_index], panic_popup_rect)
    else:
        crying_frame_index = 0
        crying_frame_elapsed = 0

    # Draw this last so mini-games, storm effects, and panic graphics never hide it.
    draw_instruction_panel()

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
