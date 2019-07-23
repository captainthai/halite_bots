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
            if dist is not 0:
                value = value / dist
                # value = value - (5 * dist)

            map_values[p] = value
            
    # sort map_values and return the best n positions
    sorted_d = sorted(map_values.items(), key=lambda x: x[1], reverse=True)
    
    targets = []
    for i in range(n):
        targets.append(sorted_d[i][0])

    return targets
    
# Gatherer class - Use a FSM to gather and return resources
class gatherer:
    class state:
        GATHER = 0
        RETURN = 1
        SEEK = 2
        
    def __init__(self, id):
        self.id = id
        self.state = gatherer.state.GATHER
        self.seek_p = None
    
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
                self.state = gatherer.state.GATHER
                cmd = self.gather(ship, game)
            elif game.game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:
                move_dir = game.game_map.naive_navigate(ship, self.seek_p)
                cmd = ship.move(move_dir)
            else:
                cmd = ship.stay_still()
        
    def gather(self, ship, game):
        if ship.is_full:
            self.state = gatherer.state.RETURN
            cmd = self.store(ship, game)
        else:
            # gather
            if game.game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:
                d = random.choice([Direction.North, Direction.South, Direction.East, Direction.West])
                p = ship.position
                p = p.directional_offset(d)
                if game.game_map[p].is_occupied:
                    cmd = ship.stay_still()
                else:
                    cmd = ship.move(d)
                    game.game_map[p].mark_unsafe(ship)                
            else:
                cmd = ship.stay_still()
                
        return cmd
        
    def store(self, ship, game):
        if ship.position == game.me.shipyard.position:
            self.state = gatherer.state.GATHER
            cmd = self.gather(ship, game)
        else:
            # go home
            if game.game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
                move_dir = game.game_map.naive_navigate(ship, game.me.shipyard.position)
                cmd = ship.move(move_dir)
            else:
                cmd = ship.stay_still()
                
        return cmd

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.

targets = get_targets(game, 15)
logging.info(targets)
target_idx = 0

# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("Gatherer")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

#initialized list of gatherers
gatherers = []
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

    # if necessary, process the map
    #if 
    
    # look for ships to add
    for s in me.get_ships():
        if s.id not in [x.id for x in gatherers]:
            gatherers.append(gatherer(s.id))
            gatherers[-1].seek_p = targets[target_idx]
            target_idx += 1
    logging.info([x.id for x in gatherers])
     
    for g in gatherers:
        if me.has_ship(g.id):
            s = me.get_ship(g.id)
            command_queue.append(g.update(s, game))
        else:
            gatherers.remove(g)
            
            
    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 150 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and len(me.get_ships()) < 15:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    logging.info(command_queue)
    game.end_turn(command_queue)

