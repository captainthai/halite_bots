# Python 3.6

import hlt

from hlt import constants
from hlt.positionals import Direction

import logging
import random

from FUBot.tools import get_path

# =============================================================================
# blocker class - just navigate to a locatation and stay there
# =============================================================================
class blocker:
    def __init__(self, id):
        self.id = id
        self.target = None
        self.path = None

    def update(self, ship, game):
        if self.target:
            logging.info("current ship {} path: {}".format(self.id, self.path))
            if self.path:
                # See if the last move was successful
                if ship.position == self.path[0]:
                    self.path.pop(0)
                    
                if self.path:
                    move_dir = game.game_map.naive_navigate(ship, self.path[0])
                    if move_dir == (0, 0):
                        # something is blocking the path, get a new one
                        self.path = None
                        cmd = ship.stay_still()
                    else:
                        cmd = ship.move(move_dir)
                else:
                    cmd = ship.stay_still()
                
            else:
                # acquire a new path
                logging.info("Getting Path for Ship: {} from {} to {}".format(self.id, ship.position, self.target))
                self.path = get_path(game, ship.position, self.target)
                if self.path:
                    logging.info(self.path)
                cmd = ship.stay_still()
                
        else:
            cmd = ship.stay_still()

        return cmd
        
class gatherer:
    class state:
        GATHER = 0
        RETURN = 1
        SEEK = 2
        
    def __init__(self, id):
        self.id = id
        self.state = gatherer.state.SEEK
        self.seek_p = None
        self.right_of_way = False
        self.delay = False
    
    def update(self, ship, game):
        if self.state == gatherer.state.GATHER:
            cmd = self.gather(ship, game)
        elif self.state == gatherer.state.RETURN:
            cmd = self.store(ship, game)
        elif self.state == gatherer.state.SEEK:
            cmd = self.seek(ship, game)
        else:
            # invalid state
            self.state = gatherer.state.GATHER
            cmd = ship.stay_still()
            
        return cmd
        
    def seek(self, ship, game):
        if self.seek_p is None:
            self.state = gatherer.state.GATHER
            cmd = self.gather(ship, game)
        else:
            if ship.is_full:
                self.state = gatherer.state.RETURN
                cmd = self.store(ship, game)
            elif ship.position == self.seek_p:
                self.seek_p = None
                self.state = gatherer.state.GATHER
                cmd = self.gather(ship, game)
            elif self.delay:
                cmd = ship.stay_still()
                self.delay = False
            elif self._is_efficient_to_seek(ship, game):
                move_dir = game.game_map.naive_navigate(ship, self.seek_p)
                moves = []
                if self.right_of_way:
                    for pos in ship.position.get_surrounding_cardinals():
                        if not game.game_map[pos].is_occupied:
                            self.right_of_way = False
                            self.delay = True
                            moves.append(game.game_map.naive_navigate(ship, pos))
                    
                    if moves:
                        move_dir = random.choice(moves)
                    else:
                        move_dir = (0,0)
                        
                elif move_dir == (0,0):
                    self.right_of_way = True
                    
                cmd = ship.move(move_dir)
            else:
                cmd = ship.stay_still()
        
        return cmd
        
    def gather(self, ship, game):
        if ship.is_full:
            self.state = gatherer.state.RETURN
            cmd = self.store(ship, game)
        else:
            # gather - Move toward the cell with most halite
            value = 0
            next_pos = None
            
            for p in ship.position.get_surrounding_cardinals():
                if not game.game_map[p].is_occupied:
                    v = game.game_map[p].halite_amount
                    if v > value:
                        value = v
                        next_pos = p
                        
            if next_pos is None or not self._is_efficient_to_gather(ship, game, next_pos):
                cmd = ship.stay_still()
            else:
                move_dir = game.game_map.naive_navigate(ship, next_pos)
                cmd = ship.move(move_dir)
                game.game_map[next_pos].mark_unsafe(ship)
                
        return cmd
        
    def store(self, ship, game):
        if ship.position == game.me.shipyard.position:
            self.state = gatherer.state.SEEK
            cmd = self.seek(ship, game)
        else:
            # go home
            if game.game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
                move_dir = game.game_map.naive_navigate(ship, game.me.shipyard.position)
                cmd = ship.move(move_dir)
            else:
                cmd = ship.stay_still()
                
        return cmd
        
    def _is_efficient_to_seek(self, ship, game):
        seek = False
        
        cost_to_move = game.game_map[ship.position].halite_amount * 0.1
        value_if_stay = game.game_map[ship.position].halite_amount * 0.25
        
        if cost_to_move <= ship.halite_amount:
            seek = True
        
        if value_if_stay > (ship.halite_amount / 2):
            seek = False
        
        return seek
        
    def _is_efficient_to_gather(self, ship, game, next_pos):
        move = False
        cost_to_move = game.game_map[ship.position].halite_amount * 0.1
        value_in_next_location = game.game_map[next_pos].halite_amount * 0.25
        value_in_current_location = game.game_map[ship.position].halite_amount * 0.25
        
        logging.info("Cost to move: {}".format(cost_to_move))
        logging.info("Value in next: {}".format(value_in_next_location))
        if cost_to_move <= ship.halite_amount and (value_in_next_location > (value_in_current_location + 3 * cost_to_move)):
            move = True
        
        logging.info("MOVE? : {}".format(move))
        return move
        