OzZoo Simulation Game

OzZoo is a Python-based zoo management simulation that demonstrates advanced object-oriented programming and Tkinter GUI development. The game allows players to manage animals, enclosures, finances, visitors, and random events, including feeding, health monitoring, breeding, and daily operations.

**Features**

- Interactive GUI: Control the zoo, view enclosures, and manage animals

- Animal simulation: Health, hunger, happiness, aging, and breeding system

- Enclosure management: Capacity, habitat type, cleanliness, and upgrades

- Finance tracking: Income, expenses, food, and animal purchases

- Random events: Heatwaves, donations, and animal escape incidents

**Design patterns**:

- Factory: For animal creation

- Observer: Health monitoring

- Singleton-like: Finance manager

- Custom exceptions: For insufficient funds, capacity limits, and species incompatibility

- Report generation: Text or PDF reports summarizing zoo status and events

**Class & Design Overview**

- Animal Hierarchy (ABC): Animal → Mammal → Marsupial → Koala/Kangaroo; Bird → WedgeTailedEagle

- Enclosure: Manages animals, habitat effects, and cleanliness

- Zoo: Main simulation manager, handles daily operations, visitors, finances, and events

- Visitor: Simulates visitor interactions, satisfaction, and spending

- FinanceManager: Tracks zoo income and expenses

- AnimalFactory: Creates animals by species

- HealthObserver: Observer pattern for health alerts

- OzZooApp: Tkinter GUI for interactive management

**Requirements**

- Python 3.8+

- Tkinter (included with Python)


**Running the Game**

- Clone the repository:
git clone https://github.com/your-username/OzZoo.git
cd OzZoo


**Run the application**:

- python ozzoo.py

**Use the GUI to**:

- Start or pause automatic daily operations

- Advance the day manually

- Feed animals, give medicine, attempt breeding

- Buy food or animals

- Clean and upgrade enclosures

- Generate reports

**Notes**

- Designed for easy extension: new species, foods, events, or enclosures can be added.

**Demonstrates key OOP concepts, design patterns, and GUI integration.**

**License**

--- This project is released under the MIT License
.

