#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging
import math

# =============================================================================
def get_total_halite(game):
    halite = 0
    for x in range(game.game_map.width):
        for y in range(game.game_map.height):
            p = hlt.Position(x, y)
            halite += game.game_map[p].halite_amount
            
    return halite

# =============================================================================
# get targets - find the places with the most concentrated halite on the map
# =============================================================================
def get_targets(game, n):
    p_dist = [-1, 0, 1]
    map_values = {}
    
    for x in range(game.game_map.width):
        for y in range(game.game_map.height):
            p = hlt.Position(x, y)
            value = 0
            
            # for this position get the surrounding cells and add up the halite values
            for dx in p_dist:
                for dy in p_dist:
                    temp_p = hlt.Position(x+dx, y+dy)
                    p_n = game.game_map.normalize(temp_p)
                    value += game.game_map[p_n].halite_amount
            
            dist = game.game_map.calculate_distance(game.me.shipyard.position, p)
            max_dist = math.sqrt((game.game_map.width*game.game_map.width/4) + (game.game_map.height*game.game_map.height/4))
            
            d_max = 3
            d_value = 1 + ((dist / max_dist) * (d_max - 1))
            
            value = value / d_value

            map_values[p] = value
            
    # sort map_values and return the best n positions
    sorted_d = sorted(map_values.items(), key=lambda x: x[1], reverse=True)
    
    targets = []
    for i in range(n):
        targets.append(sorted_d[i][0])

    return targets

# =============================================================================
# Gatherer class - Use a FSM to gather and return resources
# =============================================================================
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

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.

# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("Gatherer")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

#initialized list of gatherers
gatherers = []
stop_spawning = False
while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map
    
    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
   
    # look for ships to add
    for s in me.get_ships():
        if s.id not in [x.id for x in gatherers]:
            gatherers.append(gatherer(s.id))

    # look for ships to remove
    for g in gatherers:
        if not me.has_ship(g.id):
            gatherers.remove(g)
            
    # update all ships
    seekless = [x for x in gatherers if x.seek_p is None]
    if seekless:
        t = get_targets(game, len(seekless))
        tidx = 0
        for seekship in seekless:
            seekship.seek_p = t[tidx]
            tidx += 1
    
    for g in gatherers:
        g_ship = me.get_ship(g.id)
        command_queue.append(g.update(g_ship, game))
            
    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 150 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and len(me.get_ships()) < 15 and not stop_spawning:
        if (get_total_halite(game) > 50000):
            command_queue.append(me.shipyard.spawn())
        else:
            stop_spawning = True

    # Send your moves back to the game environment, ending this turn.
    logging.info(command_queue)
    game.end_turn(command_queue)

