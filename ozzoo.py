"""
OzZoo Simulation Game (Advanced GUI)



Features:
- Tkinter GUI (main dashboard + controls)
- Core OOP: Animal hierarchy (ABC), Enclosure, Zoo, Visitor, Food, Medicine, Manager, GameEngine
- >=10 classes, encapsulation, inheritance, polymorphism
- Abstract Base Class (Animal) and an ICleanable-like ABC
- Design Patterns: Factory (AnimalFactory) and Observer (HealthObserver)
- Singleton-like FinanceManager
- Custom exceptions (InsufficientFundsError, HabitatCapacityExceededError, IncompatibleSpeciesError)
- Game loop (day ticks), random events, breeding, resource management
- Logging (console) and in-game messages
- Extensible and commented for assignment/documentation
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from abc import ABC, abstractmethod
import random
import threading
import queue
import time
from typing import List, Dict, Optional, Any

# -----------------------
# Custom Exceptions
# -----------------------


class OzZooError(Exception):
    """Base class for OzZoo custom exceptions."""
    pass


class InsufficientFundsError(OzZooError):
    pass


class HabitatCapacityExceededError(OzZooError):
    pass


class IncompatibleSpeciesError(OzZooError):
    pass

# -----------------------
# Observer (Health Warning)
# -----------------------


class HealthObserver:
    """
    Simple observer that subscribes to animals and notifies manager/UI on critical health.
    """

    def __init__(self):
        self.subscriptions = []

    def subscribe(self, animal):
        if animal not in self.subscriptions:
            self.subscriptions.append(animal)
            animal._observers.append(self)

    def unsubscribe(self, animal):
        if animal in self.subscriptions:
            self.subscriptions.remove(animal)
            if self in animal._observers:
                animal._observers.remove(self)

    def notify(self, animal, message):
        # For now simply print; UI will read the Animal's status too
        print(f"[ALERT] {animal.name}: {message}")

# -----------------------
# ICleanable-like ABC
# -----------------------


class ICleanable(ABC):
    @abstractmethod
    def clean(self):
        pass

# -----------------------
# Abstract Animal (ABC)
# -----------------------


class Animal(ABC):
    """
    Abstract base class for all animals.
    """
    _id_counter = 1

    def __init__(self, species: str, name: Optional[str] = None, age: int = 0, health: float = 100.0, hunger: float = 0.0, happiness: float = 100.0):
        self.id = Animal._id_counter
        Animal._id_counter += 1
        self.species = species
        self.name = name or f"{species}-{self.id}"
        self.age = age
        self._health = health  # protected attribute
        self._hunger = hunger
        self._happiness = happiness
        self._observers: List[HealthObserver] = []
        self.sex = random.choice(['M', 'F'])
        self.pregnant = False
        self.days_pregnant = 0
        self.social_needs = 50.0  # 0-100
        self._max_age = 20  # default; subclasses may override

    # Encapsulation with property getters/setters and name mangling for private-like
    @property
    def health(self):
        return max(0.0, min(100.0, self._health))

    @health.setter
    def health(self, value):
        old = self._health
        self._health = max(0.0, min(100.0, value))
        if self._health < 30 and old >= 30:
            # notify observers
            for obs in self._observers:
                obs.notify(self, f"Health critical ({self._health:.1f})")
        if self._health == 0:
            for obs in self._observers:
                obs.notify(self, "This animal has died.")

    @property
    def hunger(self):
        return max(0.0, min(100.0, self._hunger))

    @hunger.setter
    def hunger(self, value):
        self._hunger = max(0.0, min(100.0, value))

    @property
    def happiness(self):
        return max(0.0, min(100.0, self._happiness))

    @happiness.setter
    def happiness(self, value):
        self._happiness = max(0.0, min(100.0, value))

    def daily_update(self):
        """
        Called every day (game tick). Modify hunger, health, etc.
        """
        self.age += 1/365  # age in years roughly per day tick
        # hunger increases
        self.hunger += random.uniform(5, 15)
        # happiness drops if hungry
        if self.hunger > 50:
            self.happiness -= (self.hunger - 50) * 0.1
        # health decline if very hungry
        if self.hunger > 80:
            self.health -= (self.hunger - 80) * 0.5
        else:
            # small health regen if well fed and happy
            if self.hunger < 30 and self.happiness > 60:
                self.health += 0.5
        # social needs effect
        if self.social_needs < 30:
            self.happiness -= 1
        # pregnancy progression
        if self.pregnant:
            self.days_pregnant += 1
            if self.days_pregnant >= self.get_gestation_period_days():
                self.pregnant = False
                self.days_pregnant = 0
                return self.give_birth()
        return None

    def feed(self, food):
        """
        Feed the animal. Different animals react differently -> polymorphism.
        """
        # base behavior
        if food.food_type not in self.accepted_food_types():
            # partly refused -> less benefit
            self.hunger -= 5
            self.happiness -= 5
            return f"{self.name} refused some of the food."
        # accepted
        hunger_reduction = food.nutrition_value
        self.hunger -= hunger_reduction
        self.happiness += min(10, hunger_reduction * 0.3)
        self.health += min(5, hunger_reduction * 0.1)
        return f"{self.name} ate {food.food_type} (-{hunger_reduction:.1f} hunger)."

    def is_alive(self):
        return self.health > 0

    @abstractmethod
    def make_sound(self):
        pass

    @abstractmethod
    def accepted_food_types(self) -> List[str]:
        pass

    @abstractmethod
    def get_gestation_period_days(self) -> int:
        """Return gestation period in days (integer)."""
        pass

    def attempt_breed_with(self, partner):
        """
        Attempt to breed with another animal. Checks species, sexes, health, and enclosure suitability.
        """
        if self.species != partner.species:
            raise IncompatibleSpeciesError("Different species cannot breed.")
        if self.sex == partner.sex:
            return False  # same sex won't produce offspring
        # health and happiness prerequisites
        if self.health < 60 or partner.health < 60:
            return False
        if self.happiness < 50 or partner.happiness < 50:
            return False
        # if one is already pregnant, skip
        if self.pregnant or partner.pregnant:
            return False
        # chance influenced by happiness
        chance = (self.happiness + partner.happiness)/200
        if random.random() < chance:
            # make female pregnant
            female = self if self.sex == 'F' else partner
            female.pregnant = True
            female.days_pregnant = 0
            return True
        return False

    def give_birth(self):
        """
        Returns a new Animal instance or None. Subclasses may override.
        """
        # default single offspring
        factory = AnimalFactory()
        baby = factory.create(self.species, age=0)
        baby.happiness = 80.0
        baby.health = 80.0
        return baby

# -----------------------
# Concrete Animal classes (inheritance depth >= 2)
# Animal -> Mammal -> Marsupial -> Koala/Kangaroo
# -----------------------


class Mammal(Animal):
    def __init__(self, species, name=None, age=0, **kwargs):
        super().__init__(species, name=name, age=age, **kwargs)
        self.is_warm_blooded = True
        self._max_age = 25

    def accepted_food_types(self):
        return ['herbivore_food', 'general_food']

    def make_sound(self):
        return f"{self.name} the {self.species} makes a mammalian sound."

    def get_gestation_period_days(self):
        return 60


class Marsupial(Mammal):
    def __init__(self, species, name=None, age=0, **kwargs):
        super().__init__(species, name=name, age=age, **kwargs)
        self._max_age = 18

    def get_gestation_period_days(self):
        return 35  # shorter for simplicity


class Koala(Marsupial):
    def __init__(self, name=None, age=0, **kwargs):
        super().__init__('Koala', name=name, age=age, **kwargs)

    def make_sound(self):
        return "munch munch (koala sound)"

    def accepted_food_types(self):
        return ['eucalyptus']

    def get_gestation_period_days(self):
        return 34


class Kangaroo(Marsupial):
    def __init__(self, name=None, age=0, **kwargs):
        super().__init__('Kangaroo', name=name, age=age, **kwargs)

    def make_sound(self):
        return "chortle (kangaroo sound)"

    def accepted_food_types(self):
        return ['herbivore_food', 'general_food']

    def get_gestation_period_days(self):
        return 30

# Birds


class Bird(Animal):
    def __init__(self, species, name=None, age=0, can_fly=True, **kwargs):
        super().__init__(species, name=name, age=age, **kwargs)
        self.can_fly = can_fly
        self._max_age = 15

    def accepted_food_types(self):
        return ['seeds', 'meaty_food', 'general_food']

    def make_sound(self):
        return f"{self.name} chirps."

    def get_gestation_period_days(self):
        return 20


class WedgeTailedEagle(Bird):
    def __init__(self, name=None, age=0, **kwargs):
        super().__init__('Wedge-tailed Eagle', name=name, age=age, can_fly=True, **kwargs)

    def make_sound(self):
        return "screech (eagle)"

    def accepted_food_types(self):
        return ['meaty_food']

# -----------------------
# Food & Medicine
# -----------------------


class Food:
    """
    Food items consumed by animals.
    """

    def __init__(self, food_type: str, nutrition_value: float, cost: float):
        self.food_type = food_type
        self.nutrition_value = nutrition_value
        self.cost = cost


class Medicine:
    """
    Medicine for animal health improvements.
    """

    def __init__(self, name: str, healing_value: float, cost: float):
        self.name = name
        self.healing_value = healing_value
        self.cost = cost

# -----------------------
# Enclosure & Habitat
# -----------------------


class Enclosure(ICleanable):
    """
    Enclosure contains animals and provides habitat-specific influences.
    """

    def __init__(self, name: str, capacity: int, habitat_type: str, cleanliness: float = 100.0, upgrade_level=1):
        self.name = name
        self.capacity = capacity
        self.habitat_type = habitat_type  # e.g., 'forest', 'grassland', 'aviary'
        self.cleanliness = cleanliness
        self.animals: List[Animal] = []
        self.upgrade_level = upgrade_level

    def add_animal(self, animal: Animal):
        if len(self.animals) >= self.capacity:
            raise HabitatCapacityExceededError("Enclosure is full.")
        # species-habitat compatibility check (simple)
        if self.habitat_type == 'aviary' and isinstance(animal, Mammal):
            raise IncompatibleSpeciesError("Mammals can't live in the aviary.")
        self.animals.append(animal)

    def remove_animal(self, animal: Animal):
        if animal in self.animals:
            self.animals.remove(animal)

    def daily_maintenance(self):
        # cleanliness drops with number of animals
        self.cleanliness -= len(self.animals) * 0.5
        if self.cleanliness < 30:
            # animals unhappy and health declines slowly
            for a in self.animals:
                a.happiness -= 1
                a.health -= 0.3

    def clean(self):
        self.cleanliness = 100.0

    def upgrade(self):
        self.upgrade_level += 1
        self.capacity += 2
        # improved happiness
        for a in self.animals:
            a.happiness += 5

# -----------------------
# Visitor
# -----------------------


class Visitor:
    def __init__(self, budget: float):
        self.budget = budget
        self.satisfaction = 70.0  # 0-100

    def visit_enclosure(self, enclosure: Enclosure):
        # satisfaction depends on animal activity, cleanliness
        avg_happiness = 50.0
        if enclosure.animals:
            avg_happiness = sum(
                a.happiness for a in enclosure.animals)/len(enclosure.animals)
        self.satisfaction += (avg_happiness - 50)/20 + \
            (enclosure.cleanliness - 50)/50
        # spending influenced by satisfaction
        spend = max(0, min(self.budget, random.uniform(
            5, 25) * (self.satisfaction/100)))
        self.budget -= spend
        return spend

# -----------------------
# Singletons & Managers
# -----------------------


class FinanceManager:
    """
    Finance manager implemented as a simple singleton-like class (module-level instance used by Zoo).
    """

    def __init__(self, starting_balance: float = 1000.0):
        self.balance = starting_balance
        self.income_history = []
        self.expense_history = []

    def add_income(self, amount: float, reason: str = ""):
        self.balance += amount
        self.income_history.append((amount, reason))

    def add_expense(self, amount: float, reason: str = ""):
        if amount > self.balance:
            raise InsufficientFundsError("Not enough money.")
        self.balance -= amount
        self.expense_history.append((amount, reason))

# -----------------------
# Factory Pattern for Animals
# -----------------------


class AnimalFactory:
    """
    Factory to create animals by species name.
    """

    def create(self, species: str, name: Optional[str] = None, age: int = 0, **kwargs) -> Animal:
        species = species.lower()
        if 'koala' in species:
            return Koala(name=name, age=age, **kwargs)
        elif 'kangaroo' in species:
            return Kangaroo(name=name, age=age, **kwargs)
        elif 'eagle' in species or 'wedge' in species:
            return WedgeTailedEagle(name=name, age=age, **kwargs)
        else:
            # default choose mammal
            return Mammal(species.title(), name=name, age=age, **kwargs)

# -----------------------
# Zoo & GameEngine
# -----------------------


class Zoo:
    """
    Main zoo class representing the whole zoo.
    """

    def __init__(self, name="OzZoo"):
        self.name = name
        self.enclosures: List[Enclosure] = []
        self.food_inventory: Dict[str, int] = {}  # food_type -> quantity
        self.medicine_inventory: Dict[str, int] = {}
        self.finance_manager = FinanceManager(starting_balance=2000.0)
        self.observer = HealthObserver()
        self.daily_ticket_price = 25.0
        self.day = 1
        self.event_log: List[str] = []
        # starter enclosures
        self.create_default_setup()

    def create_default_setup(self):
        self.enclosures.append(
            Enclosure("Forest Enclosure", capacity=4, habitat_type='forest'))
        self.enclosures.append(
            Enclosure("Grassland Enclosure", capacity=5, habitat_type='grassland'))
        self.enclosures.append(
            Enclosure("Aviary", capacity=6, habitat_type='aviary'))
        # starter animals
        factory = AnimalFactory()
        k1 = factory.create("Koala", name="Kiki", age=2)
        k2 = factory.create("Koala", name="Koko", age=3)
        kang = factory.create("Kangaroo", name="Joey", age=4)
        eagle = factory.create("Wedge-tailed Eagle", name="Aerie", age=5)
        # place animals (simple placement)
        self.enclosures[0].add_animal(k1)
        self.enclosures[0].add_animal(k2)
        self.enclosures[1].add_animal(kang)
        self.enclosures[2].add_animal(eagle)
        # subscribe observers
        self.observer.subscribe(k1)
        self.observer.subscribe(k2)
        self.observer.subscribe(kang)
        self.observer.subscribe(eagle)
        # initial food
        self.food_inventory = {'eucalyptus': 20, 'herbivore_food': 30,
                               'seeds': 20, 'meaty_food': 10, 'general_food': 25}
        # medicine
        self.medicine_inventory = {'basic_med': 5}

    def buy_food(self, food_type: str, quantity: int, price_per_unit: float):
        cost = price_per_unit * quantity
        try:
            self.finance_manager.add_expense(
                cost, f"Bought {quantity} of {food_type}")
        except InsufficientFundsError as e:
            raise
        self.food_inventory[food_type] = self.food_inventory.get(
            food_type, 0) + quantity
        self.log_event(f"Purchased {quantity}x {food_type} for ${cost:.2f}")

    def buy_animal(self, species: str, enclosure: Enclosure, price: float):
        if price > self.finance_manager.balance:
            raise InsufficientFundsError("Cannot afford animal.")
        factory = AnimalFactory()
        animal = factory.create(species)
        enclosure.add_animal(animal)
        self.observer.subscribe(animal)
        self.finance_manager.add_expense(
            price, f"Bought animal {animal.name} ({species})")
        self.log_event(f"Bought {animal.name} the {species} for ${price:.2f}")

    def daily_operations(self):
        """
        Called each day: visitors, resource consumption, animal updates, events.
        """
        revenue = 0.0
        # visitors
        visitor_count = random.randint(5, 20)
        for _ in range(visitor_count):
            v = Visitor(budget=random.uniform(10, 200))
            # pick an enclosure
            enc = random.choice(self.enclosures)
            revenue += v.visit_enclosure(enc)
        # ticket income
        ticket_income = visitor_count * self.daily_ticket_price
        revenue += ticket_income
        self.finance_manager.add_income(revenue, "Daily visitors & sales")
        self.log_event(
            f"Day {self.day}: {visitor_count} visitors -> ${revenue:.2f} revenue")
        # animals daily update
        new_babies = []
        for enc in self.enclosures:
            enc.daily_maintenance()
            # feed from inventory automatically (auto-feeding small amount if food available)
            for a in list(enc.animals):
                # auto-feed strategy: try accepted foods first
                fed = False
                for ft in a.accepted_food_types():
                    if self.food_inventory.get(ft, 0) > 0:
                        # consume one unit
                        self.food_inventory[ft] -= 1
                        food = Food(ft, nutrition_value=20, cost=0)
                        a.feed(food)
                        fed = True
                        break
                if not fed:
                    # animal gets hungrier (hunger increment done in daily_update)
                    a.hunger += 5
                baby = a.daily_update()
                if baby:
                    try:
                        enc.add_animal(baby)
                        self.observer.subscribe(baby)
                        new_babies.append(baby)
                        self.log_event(
                            f"New birth! A {baby.species} named {baby.name} was born in {enc.name}.")
                    except HabitatCapacityExceededError:
                        # baby can't be placed -> die sadly
                        self.log_event(
                            "A newborn couldn't be placed and sadly didn't survive.")
                # if animal died due to health -> remove
                if not a.is_alive():
                    enc.remove_animal(a)
                    self.log_event(
                        f"{a.name} ({a.species}) died due to poor health.")
        # random events
        self.handle_random_events()
        self.day += 1

    def handle_random_events(self):
        # some events with probabilities
        r = random.random()
        if r < 0.06:
            # heatwave: cleanliness drops, animals lose happiness
            for enc in self.enclosures:
                enc.cleanliness -= 15
                for a in enc.animals:
                    a.happiness -= 10
            self.finance_manager.add_expense(200, "Heatwave emergency cooling")
            self.log_event(
                "Heatwave: animals are stressed; cooling expenses paid.")
        elif r < 0.12:
            # donation if zoo doing well
            if self.finance_manager.balance > 1000:
                donation = random.uniform(100, 500)
                self.finance_manager.add_income(donation, "Donation")
                self.log_event(f"A generous donor gave ${donation:.2f}!")
        elif r < 0.18:
            # escape attempt (one animal gets stressed)
            enc = random.choice(self.enclosures)
            if enc.animals:
                a = random.choice(enc.animals)
                a.happiness -= 20
                self.log_event(
                    f"{a.name} had an escape scare and is stressed.")
                # small cost to repair
                try:
                    self.finance_manager.add_expense(
                        50, "Escape incident repairs")
                except InsufficientFundsError:
                    pass

    def log_event(self, text: str):
        print(f"[Day {self.day}] {text}")
        self.event_log.append(f"Day {self.day}: {text}")

# -----------------------
# GUI Application (Tkinter)
# -----------------------


class OzZooApp(tk.Tk):
    def __init__(self, zoo: Zoo):
        super().__init__()
        self.title("OzZoo Simulation")
        self.geometry("1100x700")
        self.zoo = zoo
        self.running = False
        self.tick_interval_ms = 2500  # 2.5 seconds per day for autoplay
        # Thread-safe queue for UI messages
        self.msg_queue = queue.Queue()
        # Build UI
        self.create_widgets()
        # schedule UI update loop
        self.after(500, self.process_queue)

    def create_widgets(self):
        # Top frame: finance + day + controls
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        # Finance label
        self.balance_var = tk.StringVar()
        self.update_balance_var()
        ttk.Label(top, textvariable=self.balance_var, font=(
            "Helvetica", 14)).pack(side=tk.LEFT, padx=8)

        # Day label
        self.day_var = tk.StringVar(value=f"Day: {self.zoo.day}")
        ttk.Label(top, textvariable=self.day_var, font=(
            "Helvetica", 14)).pack(side=tk.LEFT, padx=12)

        # Buttons
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.RIGHT)
        self.start_btn = ttk.Button(
            btn_frame, text="Start Auto", command=self.start_auto)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.pause_btn = ttk.Button(
            btn_frame, text="Pause", command=self.pause_auto, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Advance Day",
                   command=self.advance_day).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Buy Food",
                   command=self.buy_food_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Buy Animal",
                   command=self.buy_animal_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Clean Enclosure",
                   command=self.clean_enclosure_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Upgrade Enclosure",
                   command=self.upgrade_enclosure_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Generate Reports (optional)",
                   command=self.generate_reports).pack(side=tk.LEFT, padx=4)

        # Middle frame: enclosures list and details
        middle = ttk.Frame(self)
        middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Enclosure Listbox
        left_panel = ttk.Frame(middle)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        ttk.Label(left_panel, text="Enclosures:", font=(
            "Helvetica", 12, 'bold')).pack(anchor='w')
        self.enc_listbox = tk.Listbox(left_panel, width=30)
        self.enc_listbox.pack(fill=tk.Y, expand=True)
        self.enc_listbox.bind("<<ListboxSelect>>",
                              lambda e: self.update_enclosure_details())

        # Center: details
        center_panel = ttk.Frame(middle)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(center_panel, text="Enclosure Details:",
                  font=("Helvetica", 12, 'bold')).pack(anchor='w')
        self.enc_details_text = tk.Text(center_panel, height=20, wrap=tk.WORD)
        self.enc_details_text.pack(fill=tk.BOTH, expand=True)
        # Right: resources + event log
        right_panel = ttk.Frame(middle)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=6, pady=6)
        ttk.Label(right_panel, text="Resources:", font=(
            "Helvetica", 12, 'bold')).pack(anchor='w')
        self.res_text = tk.Text(right_panel, height=10, width=30)
        self.res_text.pack()
        ttk.Label(right_panel, text="Event Log:", font=(
            "Helvetica", 12, 'bold')).pack(anchor='w', pady=(6, 0))
        self.event_text = tk.Text(right_panel, height=12, width=30)
        self.event_text.pack()

        # Bottom: animal actions & status
        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=6)
        ttk.Label(bottom, text="Selected Animal Actions:",
                  font=("Helvetica", 12, 'bold')).pack(anchor='w')
        act_frame = ttk.Frame(bottom)
        act_frame.pack(fill=tk.X)
        ttk.Button(act_frame, text="Feed Selected",
                   command=self.feed_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(act_frame, text="Give Medicine",
                   command=self.give_medicine_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(act_frame, text="Attempt Breed Pair",
                   command=self.attempt_breed_pair).pack(side=tk.LEFT, padx=4)
        ttk.Button(act_frame, text="View Animal Info",
                   command=self.view_animal_info).pack(side=tk.LEFT, padx=4)

        # populate enclosure list and initial details
        self.refresh_enclosure_list()
        self.update_resource_text()
        self.update_event_text()

    # -----------------------
    # UI helpers
    # -----------------------
    def update_balance_var(self):
        bal = self.zoo.finance_manager.balance
        self.balance_var.set(f"Balance: ${bal:.2f}")

    def refresh_enclosure_list(self):
        self.enc_listbox.delete(0, tk.END)
        for i, enc in enumerate(self.zoo.enclosures):
            self.enc_listbox.insert(
                tk.END, f"{i+1}. {enc.name} ({len(enc.animals)}/{enc.capacity})")

    def update_enclosure_details(self):
        sel = self.enc_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        enc = self.zoo.enclosures[idx]
        self.enc_details_text.delete('1.0', tk.END)
        info = f"Name: {enc.name}\nHabitat: {enc.habitat_type}\nCapacity: {enc.capacity}\nCleanliness: {enc.cleanliness:.1f}\nUpgrade level: {enc.upgrade_level}\n\nAnimals:\n"
        for a in enc.animals:
            info += f"- {a.name} ({a.species}) Age:{a.age:.1f} Sex:{a.sex} Health:{a.health:.1f} Hunger:{a.hunger:.1f} Happiness:{a.happiness:.1f}\n"
        self.enc_details_text.insert(tk.END, info)

    def update_resource_text(self):
        self.res_text.delete('1.0', tk.END)
        inv = "Food Inventory:\n"
        for k, v in self.zoo.food_inventory.items():
            inv += f"- {k}: {v}\n"
        inv += "\nMedicine Inventory:\n"
        for k, v in self.zoo.medicine_inventory.items():
            inv += f"- {k}: {v}\n"
        inv += f"\nTicket Price: ${self.zoo.daily_ticket_price:.2f}\n"
        self.res_text.insert(tk.END, inv)

    def update_event_text(self):
        self.event_text.delete('1.0', tk.END)
        # show last 30 events
        for e in self.zoo.event_log[-30:]:
            self.event_text.insert(tk.END, e + "\n")

    def process_queue(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get_nowait()
            # simply append to event log area
            self.zoo.event_log.append(msg)
        self.update_balance_var()
        self.day_var.set(f"Day: {self.zoo.day}")
        self.refresh_enclosure_list()
        self.update_resource_text()
        self.update_event_text()
        self.after(500, self.process_queue)

    # -----------------------
    # Actions
    # -----------------------
    def start_auto(self):
        if self.running:
            return
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.auto_tick()

    def pause_auto(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)

    def auto_tick(self):
        if not self.running:
            return
        # perform a day tick
        self.advance_day()
        # schedule next
        self.after(self.tick_interval_ms, self.auto_tick)

    def advance_day(self):
        try:
            self.zoo.daily_operations()
            # push a summary message to queue
            last = self.zoo.event_log[-1] if self.zoo.event_log else ""
            self.msg_queue.put(f"Day advanced: {last}")
        except Exception as e:
            messagebox.showerror("Error during day processing", str(e))

    def buy_food_dialog(self):
        choices = list(self.zoo.food_inventory.keys())
        # allow buying common types
        choices = ['eucalyptus', 'herbivore_food',
                   'seeds', 'meaty_food', 'general_food']
        ft = simpledialog.askstring(
            "Buy Food", f"Food type ({', '.join(choices)}):")
        if not ft:
            return
        try:
            qty = simpledialog.askinteger(
                "Qty", "Quantity to buy:", minvalue=1, maxvalue=500)
            if not qty:
                return
            price = {'eucalyptus': 3, 'herbivore_food': 2, 'seeds': 1.5,
                     'meaty_food': 4, 'general_food': 2.5}.get(ft, 2)
            self.zoo.buy_food(ft, qty, price)
            messagebox.showinfo(
                "Success", f"Bought {qty}x {ft} for ${qty*price:.2f}")
        except InsufficientFundsError:
            messagebox.showerror("Funds", "Not enough funds to buy that food.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buy_animal_dialog(self):
        species = simpledialog.askstring(
            "Buy Animal", "Species (e.g., Koala, Kangaroo, Wedge-tailed Eagle):")
        if not species:
            return
        # choose enclosure
        enc_index = simpledialog.askinteger(
            "Enclosure", f"Place in enclosure number (1-{len(self.zoo.enclosures)}):", minvalue=1, maxvalue=len(self.zoo.enclosures))
        if not enc_index:
            return
        price = {'koala': 400, 'kangaroo': 350, 'wedge-tailed eagle': 500}
        cost = price.get(species.lower(), 300)
        try:
            self.zoo.buy_animal(
                species, self.zoo.enclosures[enc_index-1], cost)
            messagebox.showinfo(
                "Bought", f"Bought a {species} for ${cost:.2f}")
        except InsufficientFundsError:
            messagebox.showerror("Funds", "Insufficient funds.")
        except IncompatibleSpeciesError as e:
            messagebox.showerror("Incompatibility", str(e))
        except HabitatCapacityExceededError:
            messagebox.showerror("Capacity", "That enclosure is full.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clean_enclosure_dialog(self):
        idx = simpledialog.askinteger(
            "Clean", f"Enclosure number to clean (1-{len(self.zoo.enclosures)}):", minvalue=1, maxvalue=len(self.zoo.enclosures))
        if not idx:
            return
        enc = self.zoo.enclosures[idx-1]
        cost = 20 * (1 + len(enc.animals)/2)
        try:
            self.zoo.finance_manager.add_expense(cost, "Cleaning enclosure")
            enc.clean()
            messagebox.showinfo(
                "Cleaned", f"Cleaned {enc.name} for ${cost:.2f}")
        except InsufficientFundsError:
            messagebox.showerror("Funds", "Not enough money to clean.")
        self.update_resource_text()

    def upgrade_enclosure_dialog(self):
        idx = simpledialog.askinteger(
            "Upgrade", f"Enclosure number to upgrade (1-{len(self.zoo.enclosures)}):", minvalue=1, maxvalue=len(self.zoo.enclosures))
        if not idx:
            return
        enc = self.zoo.enclosures[idx-1]
        cost = 200 * enc.upgrade_level
        try:
            self.zoo.finance_manager.add_expense(cost, "Enclosure upgrade")
            enc.upgrade()
            messagebox.showinfo(
                "Upgraded", f"Upgraded {enc.name} to level {enc.upgrade_level} for ${cost:.2f}")
        except InsufficientFundsError:
            messagebox.showerror("Funds", "Not enough funds to upgrade.")

    def get_selected_animal(self) -> Optional[Animal]:
        sel = self.enc_listbox.curselection()
        if not sel:
            messagebox.showwarning("Selection", "Select an enclosure first.")
            return None
        enc = self.zoo.enclosures[sel[0]]
        # if multiple animals, ask to choose by index
        if not enc.animals:
            messagebox.showwarning(
                "No Animals", "That enclosure has no animals.")
            return None
        if len(enc.animals) == 1:
            return enc.animals[0]
        # ask which
        names = [f"{i+1}. {a.name} ({a.species})" for i,
                 a in enumerate(enc.animals)]
        choice = simpledialog.askinteger(
            "Choose Animal", "Choose number:\n" + "\n".join(names), minvalue=1, maxvalue=len(enc.animals))
        if not choice:
            return None
        return enc.animals[choice-1]

    def feed_selected(self):
        a = self.get_selected_animal()
        if not a:
            return
        # choose food type from inventory
        choices = [k for k, v in self.zoo.food_inventory.items() if v > 0]
        if not choices:
            messagebox.showwarning(
                "No Food", "No food in inventory. Buy some first.")
            return
        ft = simpledialog.askstring(
            "Feed", f"Food type ({', '.join(choices)}):")
        if not ft or ft not in self.zoo.food_inventory or self.zoo.food_inventory[ft] <= 0:
            messagebox.showwarning(
                "Invalid", "Invalid food choice or none left.")
            return
        # consume
        self.zoo.food_inventory[ft] -= 1
        food = Food(ft, nutrition_value=25, cost=0)
        r = a.feed(food)
        messagebox.showinfo("Fed", r)
        self.update_resource_text()
        self.update_enclosure_details()

    def give_medicine_selected(self):
        a = self.get_selected_animal()
        if not a:
            return
        if not self.zoo.medicine_inventory or sum(self.zoo.medicine_inventory.values()) == 0:
            messagebox.showwarning("No Medicine", "No medicine available.")
            return
        med_name = next(
            (k for k, v in self.zoo.medicine_inventory.items() if v > 0), None)
        if not med_name:
            messagebox.showwarning("No Medicine", "No medicine available.")
            return
        # consume one
        self.zoo.medicine_inventory[med_name] -= 1
        a.health += 15
        messagebox.showinfo(
            "Medicine", f"Gave medicine to {a.name}. Health now {a.health:.1f}")
        self.update_resource_text()
        self.update_enclosure_details()

    def attempt_breed_pair(self):
        # pick enclosure
        sel = self.enc_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select an enclosure first.")
            return
        enc = self.zoo.enclosures[sel[0]]
        if len(enc.animals) < 2:
            messagebox.showwarning(
                "Need pair", "Need at least two animals in enclosure.")
            return
        # choose two
        names = [
            f"{i+1}. {a.name} ({a.species}, {a.sex})" for i, a in enumerate(enc.animals)]
        p1 = simpledialog.askinteger(
            "Breed - Parent 1", "Choose parent 1:\n" + "\n".join(names), minvalue=1, maxvalue=len(enc.animals))
        if not p1:
            return
        p2 = simpledialog.askinteger(
            "Breed - Parent 2", "Choose parent 2:\n" + "\n".join(names), minvalue=1, maxvalue=len(enc.animals))
        if not p2 or p1 == p2:
            messagebox.showwarning("Invalid", "Invalid pair.")
            return
        a1 = enc.animals[p1-1]
        a2 = enc.animals[p2-1]
        try:
            success = a1.attempt_breed_with(a2)
            if success:
                messagebox.showinfo(
                    "Breeding", "Breeding occurred! Female is now pregnant.")
            else:
                messagebox.showinfo("Breeding", "Breeding attempt failed.")
        except IncompatibleSpeciesError as e:
            messagebox.showerror("Incompatible", str(e))
        self.update_enclosure_details()

    def view_animal_info(self):
        a = self.get_selected_animal()
        if not a:
            return
        info = f"Name: {a.name}\nSpecies: {a.species}\nSex: {a.sex}\nAge: {a.age:.2f}\nHealth: {a.health:.1f}\nHunger: {a.hunger:.1f}\nHappiness: {a.happiness:.1f}\nPregnant: {a.pregnant}\n"
        messagebox.showinfo("Animal Info", info)

    # -----------------------
    # Reports (optional PDF generation)
    # -----------------------
    def generate_reports(self):
        """
        Generate a simple text-based report and attempt PDF if reportlab is installed.
        """
        try:
            import reportlab
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            # create a PDF summary
            filename = "ozzoo_report_summary.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            text = c.beginText(40, 750)
            text.setFont("Helvetica", 12)
            text.textLine(f"OzZoo Report - Day {self.zoo.day}")
            text.textLine("")
            text.textLine(f"Balance: ${self.zoo.finance_manager.balance:.2f}")
            text.textLine("")
            text.textLine("Enclosures Summary:")
            for enc in self.zoo.enclosures:
                text.textLine(
                    f"- {enc.name}: {len(enc.animals)}/{enc.capacity} animals, Cleanliness {enc.cleanliness:.1f}")
            text.textLine("")
            text.textLine("Recent Events:")
            for e in self.zoo.event_log[-10:]:
                text.textLine(f"- {e}")
            c.drawText(text)
            c.showPage()
            c.save()
            messagebox.showinfo("Report", f"Generated PDF report: {filename}")
        except Exception as e:
            # fallback to text file
            filename = "ozzoo_report_summary.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"OzZoo Report - Day {self.zoo.day}\n")
                f.write(
                    f"Balance: ${self.zoo.finance_manager.balance:.2f}\n\n")
                f.write("Enclosures Summary:\n")
                for enc in self.zoo.enclosures:
                    f.write(
                        f"- {enc.name}: {len(enc.animals)}/{enc.capacity} animals, Cleanliness {enc.cleanliness:.1f}\n")
                f.write("\nRecent Events:\n")
                for e in self.zoo.event_log[-10:]:
                    f.write(f"- {e}\n")
            messagebox.showinfo("Report", f"Generated text report: {filename}")

# -----------------------
# Main Entry
# -----------------------


def main():
    zoo = Zoo()
    app = OzZooApp(zoo)
    app.mainloop()


if __name__ == "__main__":
    main()
