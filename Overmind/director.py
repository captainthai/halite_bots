#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.positionals import Position

import logging

import Overmind.strategy as STRAT

# =============================================================================
class director:
    def __init__(self, game):
        # select strategy based on map
        self.strategy = STRAT.gather_passive(game)
        
    def update(self, game):
        command_queue = []

        if self.strategy:
            command_queue = self.strategy.update(game)
            
        return command_queue
