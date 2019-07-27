#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt.positionals import Position

import logging

import FUBot.strategy as STRAT

# =============================================================================
class director:
    def __init__(self, game):
        # select strategy based on map
        self.select_strategy(game)
        positions = [x for x in Position(0,0).get_surrounding_cardinals()]
        logging.info("Positions around (0,0)")
        logging.info(positions)
        
    def update(self, game):
        command_queue = []
        
        if self.strategy:
            command_queue = self.strategy.update(game)
            
        return command_queue
        
    def select_strategy(self, game):
        n_players = len([x for x in game.players])
        logging.info("NUMBER OF PLAYERS: {}".format(n_players))
        if n_players == 2:
            self.strategy = STRAT.camp_enemy_base(game)
        else:
            self.strategy = STRAT.gather_passive(game)
