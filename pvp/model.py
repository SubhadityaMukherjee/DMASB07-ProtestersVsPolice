from random import choices

from mesa import Model
from mesa.datacollection import DataCollector
from mesa.space import Grid
from mesa.time import RandomActivation

from .agents.block import Block
from .agents.citizen import Citizen
from .agents.cop import Cop
from .strategies import *

try:
    from playsound import playsound
except:
    pass


class ProtestersVsPolice(Model):
    """
    Model 1 from "Modeling civil violence: An agent-based computational
    approach," by Joshua Epstein.
    http://www.pnas.org/content/99/suppl_3/7243.full
    Attributes:
        height: grid height
        width: grid width
        citizen_density: approximate % of cells occupied by citizens.
        cop_density: approximate % of calles occupied by cops.
        citizen_vision: number of cells in each direction (N, S, E and W) that
            citizen can inspect
        cop_vision: number of cells in each direction (N, S, E and W) that cop
            can inspect
        legitimacy:  (L) citizens' perception of regime legitimacy, equal
            across all citizens
        max_jail_term: (J_max)
        active_threshold: if (grievance - (risk_aversion * arrest_probability))
            > threshold, citizen rebels
        arrest_prob_constant: set to ensure agents make plausible arrest
            probability estimates
        movement: binary, whether agents try to move at step end
        max_iters: model may not have a natural stopping point, so we set a
            max.

    """

    def __init__(
        self,
        height=40,
        width=40,
        grid_density=0.7,
        ratio=0.074,
        environment="Random distribution",
        barricade=4,
        citizen_vision=7,
        cop_vision=7,
        legitimacy=0.8,
        max_jail_term=1000,
        jail_capacity=50,
        active_threshold=0.1,
        strategy="random",
        arrest_prob_constant=2.3,
        aggression=0.7,  # TODO
        direction_bias="none",
        movement=True,
        max_iters=1000,
        funmode=False,
    ):
        super().__init__()

        self.height = height
        self.width = width
        self.grid_density = grid_density
        self.ratio = ratio
        self.funmode = funmode
        self.citizen_vision = citizen_vision
        self.cop_vision = cop_vision
        self.legitimacy = legitimacy
        self.max_jail_term = max_jail_term
        self.jail_capacity = jail_capacity
        self.active_threshold = active_threshold
        self.arrest_prob_constant = arrest_prob_constant
        self.movement = movement
        self.jailed_agents = []
        self.arrested_agents = []
        self.jailed = 0
        self.test = 0
        self.strategy = strategy
        self.max_iters = max_iters
        self.iteration = 0
        self.aggression = self.random.random()
        self.direction_bias = direction_bias
        self.schedule = RandomActivation(self)
        self.grid = (
            Grid(height, width, torus=False)
            if self.strategy == "circle"
            else Grid(height, width, torus=True)
        )
        self.environment = environment

        self.numTotalSpaces = self.height * self.width
        self.numFreeSpaces = (self.height * self.width) * self.grid_density - barricade
        self.numCitizens = self.numFreeSpaces * self.ratio
        self.numCops = self.numFreeSpaces - self.numCitizens
        self.barricade = barricade
        self.citizen, self.cop, self.block = None, None, None

        model_reporters = {
            "Quiescent": lambda m: self.count_type_citizens(m, "Quiescent"),
            "Active": lambda m: self.count_type_citizens(m, "Active"),
            "Jailed": lambda m: self.count_jailed(m),
        }
        agent_reporters = {
            "x": lambda a: a.pos[0],
            "y": lambda a: a.pos[1],
            "breed": lambda a: a.breed,
            "jail_sentence": lambda a: getattr(a, "jail_sentence", None),
            "condition": lambda a: getattr(a, "condition", None),
            "arrest_probability": lambda a: getattr(a, "arrest_probability", None),
        }
        self.datacollector = DataCollector(
            model_reporters=model_reporters, agent_reporters=agent_reporters
        )
        self.spawner()

        self.running = True
        self.datacollector.collect(self)

    def spawner(self):
        self.unique_id = 0
        if self.environment == "Random distribution":
            random_strategy(self)
        elif self.environment == "Block in the middle":
            middle_block(self)
        elif self.environment == "Wall of cops":
            side_strategy(self, "left", "cop")
        elif self.environment == "Street":
            streets(self)
        elif self.environment == "Circle":
            circle(self)

    def step(self):
        """
        Advance the model by one step and collect data.
        """
        self.schedule.step()
        print(len(self.arrested_agents))
        for i in self.arrested_agents:
            if len(self.jailed_agents) < self.jail_capacity:  # TODO: change
                self.jailed_agents.append(i)
                try:
                    self.grid._remove_agent(i.pos, i)
                    self.schedule.remove(i)
                    self.test += 1
                    self.arrested_agents.remove(i)
                except KeyError:
                    pass
        self.datacollector.collect(self)

        self.iteration += 1
        if self.iteration % 3 == 0 and self.funmode == True:
            try:
                playsound("pewpew.mp3")
            except:
                pass

        if self.iteration > self.max_iters:
            self.running = False
        print(self.jailed)
        print(self.test)
        print(len(self.arrested_agents))
        print(len(self.jailed_agents))

    @staticmethod
    def count_type_citizens(model, condition, exclude_jailed=True):
        """
        Helper method to count agents by Quiescent/Active.
        """
        count = 0
        for agent in model.schedule.agents:
            if agent.breed == "cop":
                continue
            if exclude_jailed and agent.jail_sentence:
                continue
            if agent.condition == condition:
                count += 1
        return count

    @staticmethod
    def count_jailed(model):
        """
        Helper method to count jailed agents.
        """
        count = 0
        for agent in model.schedule.agents:
            if agent.breed == "citizen" and agent.jail_sentence:
                count += 1
        return count
