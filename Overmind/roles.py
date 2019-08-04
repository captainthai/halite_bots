# Python 3.6

import hlt

from hlt import constants
from hlt.positionals import Direction

import logging
import random

from Overmind.tools import *

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

# =============================================================================
class destroyer:
    def __init__(self, id, target_id):
        self.id = id
        self.target_id = target_id
        self.idle = False
        self.path = None
        
    def update(self, ship, game):
        # make sure target ship still exists
        t_ship = get_ship_from_id(game, self.target_id)
        if t_ship:
            # make sure we have a path
            if not self.path or t_ship.position not in self.path:
                self.path = get_path(game, ship.position, t_ship.position, unsafe=True)
            
            logging.info("destroyer path: {}".format(self.path))
            if self.path:
                unsafe_moves = game.game_map.get_unsafe_moves(ship.position, self.path[0])
                if len(self.path) == 1:
                    if unsafe_moves:
                        move_dir = unsafe_moves[0]
                    else:
                        move_dir = (0,0)
                else:
                    move_dir = game.game_map.naive_navigate(ship, self.path[0]) 

                logging.info("move dir: {}, unsafe_moves: {}".format(move_dir, unsafe_moves))
                if move_dir == (0, 0):
                    # something is blocking the path, we need a new one
                    self.path = None
                    cmd = ship.stay_still()
                else:
                    cmd = ship.move(move_dir)
            else:
                cmd = ship.stay_still()
            
        else:
            logging.info("destroyer going idle: {}".format(ship.id))
            self.idle = True
            cmd = ship.stay_still()
            
        return cmd

# =============================================================================
class gatherer:
    class state:
        GATHER = 0
        RETURN = 1
        SEEK = 2
        COLLAPSE = 3
        
    def __init__(self, id):
        self.id = id
        self.state = gatherer.state.SEEK
        self.seek_pos = None
        self.seek_path = None
        self.idle_count = 0
    
    def update(self, ship, game):
        # if we are getting close to the end of the game, make sure
        # to return resources before the time is up
        if game.turn_number >= constants.MAX_TURNS - game.game_map.calculate_distance(ship.position, game.me.shipyard.position) - (4 + ((game.game_map.width - 32)/2)):
            self.state = gatherer.state.COLLAPSE
        
        if self.state == gatherer.state.GATHER:
            cmd = self.gather(ship, game)
        elif self.state == gatherer.state.RETURN:
            cmd = self.store(ship, game)
        elif self.state == gatherer.state.SEEK:
            cmd = self.seek(ship, game)
        elif self.state == gatherer.state.COLLAPSE:
            cmd = self.collapse(ship, game)
        else:
            # invalid state
            self.state = gatherer.state.GATHER
            cmd = ship.stay_still()
            
        return cmd
        
    def seek(self, ship, game):
        if self.seek_pos is None:
            self.state = gatherer.state.GATHER
            cmd = self.gather(ship, game)
        else:
            if ship.is_full:
                self.state = gatherer.state.RETURN
                cmd = self.store(ship, game)
            elif ship.position == self.seek_pos:
                self.seek_pos = None
                self.seek_path = None
                self.state = gatherer.state.GATHER
                cmd = self.gather(ship, game)
            elif self._is_efficient_to_seek(ship, game):
                if self.seek_path:
                    # See if the last move was successful
                    if ship.position == self.seek_path[0]:
                        self.seek_path.pop(0)
                    
                    # move to the next position
                    cmd = self._seek_move(ship, game)
                else:
                    # acquire a new path
                    logging.info("Getting Path for Ship: {} from {} to {}".format(self.id, ship.position, self.seek_pos))
                    self.seek_path = get_path(game, ship.position, self.seek_pos)
                    if self.seek_path:
                        logging.info(self.seek_path)
                    
                    # move to the next position
                    cmd = self._seek_move(ship, game)
            else:
                cmd = ship.stay_still()
        
        return cmd
        
    def _seek_move(self, ship, game):
        if self.seek_path:
            move_dir = game.game_map.naive_navigate(ship, self.seek_path[0])
            if move_dir == (0, 0):
                # something is blocking the path, get a new one
                self.seek_pos = None
                self.seek_path = None
                cmd = self._random_move(game, ship)
                logging.info("seeker {} moving randomly {}".format(ship.id, cmd))
            else:
                cmd = ship.move(move_dir)
        else:
            cmd = self._random_move(game, ship)
            
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
                        
            if next_pos:
                if self._is_efficient_to_gather(ship, game, next_pos):
                    move_dir = game.game_map.naive_navigate(ship, next_pos)
                    cmd = ship.move(move_dir)
                    game.game_map[next_pos].mark_unsafe(ship)
                else:
                    cmd = ship.stay_still()
            else:
                cmd = self._random_move()
                
        return cmd
        
    def store(self, ship, game):
        if ship.position == game.me.shipyard.position:
            self.state = gatherer.state.SEEK
            cmd = self.seek(ship, game)
        else:
            # go home
            if game.game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
                move_dir = game.game_map.naive_navigate(ship, game.me.shipyard.position)
                if move_dir == (0,0):
                    self.idle_count += 1
                    if self.idle_count == 3:
                        cmd = self._random_move(game, ship)
                    else:
                        cmd = ship.stay_still()
                else:
                    cmd = ship.move(move_dir)
                    self.idle_count = 0
            else:
                cmd = ship.stay_still()
                
        return cmd
        
    def collapse(self, ship, game):
        if ship.position == game.me.shipyard.position:
            cmd = ship.stay_still()
        else:
            move_dir = game.game_map.naive_navigate(ship, game.me.shipyard.position)
            
            if move_dir == (0,0):
                if game.game_map.calculate_distance(ship.position, game.me.shipyard.position) == 1:
                    unsafe_moves = game.game_map.get_unsafe_moves(ship.position, game.me.shipyard.position)
                    cmd = ship.move(unsafe_moves[0])
                else:
                    cmd = ship.stay_still()
            else:
                cmd = ship.move(move_dir)
                
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
        
    def _random_move(self, game, ship):
        moves = ship.position.get_surrounding_cardinals()
        moves = [p for p in moves if not game.game_map[p].is_occupied]
        if moves:
            move_pos = random.choice(moves)
            move_dir = game.game_map.naive_navigate(ship, move_pos)
            cmd = ship.move(move_dir)
            game.game_map[move_pos].mark_unsafe(ship)
        else:
            cmd = ship.stay_still()
        return cmd
        