# Python 3.6

import hlt

from hlt import constants
from hlt.positionals import Direction

import logging

from Overmind.tools import *
from Overmind.roles import *

# =============================================================================
class strategy:
    def update():
        logging.error("FAILED TO IMPLEMENT UPDATE METHOD IN STRATEGY SUBCLASS")
        return []
        
# =============================================================================
class camp_enemy_base(strategy):
    def __init__(self, game):
        self.gs = []
        self.fus = []
        self.stop_spawning = False
        
        # set targets to surround other players base
        for p in game.players:
            if p is not game.me.id:
                player = game.players[p]
                break
        
        self.targets = player.shipyard.position.get_surrounding_cardinals()
        logging.info(self.targets)
        
    def update(self, game):
        # You extract player metadata and the updated map metadata here for convenience.
        me = game.me
        game_map = game.game_map
        
        # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
        #   end of the turn.
        command_queue = []
        
        # remove sunk ships
        for g in self.gs:
            if not me.has_ship(g.id):
                self.gs.remove(g)
        for f in self.fus:
            if not me.has_ship(f.id):
                self.fus.remove(f)
                
        # get ships with no roles
        roleless = []
        for s in me.get_ships():
            all_ships = self.gs + self.fus
            if s.id not in [x.id for x in all_ships]:
                roleless.append(s)
        
        # assign new roles
        logging.info("Roleless: {}".format(roleless))
        while roleless:
            s = roleless[0]
            if len(self.gs) > 6 and len(self.fus) < 4:
                self.fus.append(blocker(s.id))
            else:
                self.gs.append(gatherer(s.id))
            roleless.remove(s)
        
        # look for ships to add
        # for s in me.get_ships():
            # if s.id not in [x.id for x in self.gs]:
                # self.gs.append(gatherer(s.id))

        # update gatherers
        seekless = [x for x in self.gs if x.seek_pos is None]
        if seekless:
            t = get_targets(game, len(seekless))
            tidx = 0
            for seekship in seekless:
                seekship.seek_pos = t[tidx]
                tidx += 1
        
        for g in self.gs:
            g_ship = me.get_ship(g.id)
            command_queue.append(g.update(g_ship, game))


        # update fu-ers
        for f in self.fus:
            if not f.target and self.targets:
                logging.info("Acquiring target")
                for t in self.targets:
                    if t not in [x.target for x in self.fus if x.target is not None]:
                        f.target = t
                        logging.info("new target assigned: {}".format(t))
                        break
            fu_ship = me.get_ship(f.id)
            command_queue.append(f.update(fu_ship, game))

        # If the game is in the first 200 turns and you have enough halite, spawn a ship.
        # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
        if game.turn_number <= 150 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and len(me.get_ships()) < 15 and not self.stop_spawning:
            if (get_total_halite(game) > 50000):
                command_queue.append(me.shipyard.spawn())
            else:
                self.stop_spawning = True

        return command_queue

# =============================================================================
class camp_enemy_base_4p(strategy):
    def __init__(self, game):
        self.gs = []
        self.fus = []
        self.stop_spawning = False
        
        # set targets to camp on all other bases
        self.targets = []
        for p in game.players:
            if p is not game.me.id:
                self.targets.append(game.players[p].shipyard.position)
                
        logging.info(self.targets)
        
    def update(self, game):
        # You extract player metadata and the updated map metadata here for convenience.
        me = game.me
        game_map = game.game_map
        
        # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
        #   end of the turn.
        command_queue = []
        
        # remove sunk ships
        for g in self.gs:
            if not me.has_ship(g.id):
                self.gs.remove(g)
        for f in self.fus:
            if not me.has_ship(f.id):
                self.fus.remove(f)
                
        # get ships with no roles
        roleless = []
        for s in me.get_ships():
            all_ships = self.gs + self.fus
            if s.id not in [x.id for x in all_ships]:
                roleless.append(s)
        
        # assign new roles
        logging.info("Roleless: {}".format(roleless))
        while roleless:
            s = roleless[0]
            if len(self.gs) > 6 and len(self.fus) < len(self.targets):
                self.fus.append(blocker(s.id))
            else:
                self.gs.append(gatherer(s.id))
            roleless.remove(s)
        
        # look for ships to add
        # for s in me.get_ships():
            # if s.id not in [x.id for x in self.gs]:
                # self.gs.append(gatherer(s.id))

        # update gatherers
        seekless = [x for x in self.gs if x.seek_pos is None]
        if seekless:
            t = get_targets(game, len(seekless))
            tidx = 0
            for seekship in seekless:
                seekship.seek_pos = t[tidx]
                tidx += 1
        
        for g in self.gs:
            g_ship = me.get_ship(g.id)
            command_queue.append(g.update(g_ship, game))


        # update fu-ers
        for f in self.fus:
            if not f.target and self.targets:
                logging.info("Acquiring target")
                for t in self.targets:
                    if t not in [x.target for x in self.fus if x.target is not None]:
                        f.target = t
                        logging.info("new target assigned: {}".format(t))
                        break
            fu_ship = me.get_ship(f.id)
            command_queue.append(f.update(fu_ship, game))

        # If the game is in the first 200 turns and you have enough halite, spawn a ship.
        # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
        if game.turn_number <= 150 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and len(me.get_ships()) < 15 and not self.stop_spawning:
            if (get_total_halite(game) > 50000):
                command_queue.append(me.shipyard.spawn())
            else:
                self.stop_spawning = True

        return command_queue

# =============================================================================
class gather_passive(strategy):
    def __init__(self):
        self.gs = []
        self.ds = []
        self.stop_spawning = False
        
    def update(self, game):
        # You extract player metadata and the updated map metadata here for convenience.
        me = game.me
        game_map = game.game_map
        
        # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
        #   end of the turn.
        command_queue = []

        # look for ships to add
        for s in me.get_ships():
            if s.id not in [x.id for x in self.gs] and s.id not in [y.id for y in self.ds]:
                self.gs.append(gatherer(s.id))
        # logging.info("ADDED SHIPS")
        
        # look for ships to remove
        for g in self.gs:
            if not me.has_ship(g.id):
                self.gs.remove(g)
                
        for d in self.ds:
            if not me.has_ship(d.id):
                self.ds.remove(d)
            elif d.idle:
                # if we have idle destroyers, convert them to gatherers
                idle_id = d.id
                self.ds.remove(d)
                self.gs.append(gatherer(idle_id))
        # logging.info("REMOVING SHIPS")
                
        # give seekers new targets/paths
        seekless = [x for x in self.gs if x.seek_pos is None]
        if seekless:
            assign_targets(game, seekless)
            for seekship in seekless:
                seekship.seek_path = get_path(game, me.get_ship(seekship.id).position, seekship.seek_pos)
        # logging.info("UPDATED SEEK LOCATIONS SHIPS")
        
        # look for enemy ships that are too close to our shipyard and destroy them
        my_ship_ids = [s.id for s in me.get_ships()]
        logging.info("My ship ids: {}".format(my_ship_ids))
        for i in range(-2, 3):
            for j in range(-2, 3):
                map_pos = me.shipyard.position.directional_offset((i,j))
                if game_map[map_pos].is_occupied:
                    enemy_id = game_map[map_pos].ship.id
                    if enemy_id not in my_ship_ids and enemy_id not in [x.target_id for x in self.ds]:
                        # find the closest available ship and make it a destroyer
                        ship_ids = [g.id for g in self.gs if g.state == gatherer.state.SEEK]
                        ship_list = [s for s in me.get_ships() if s.id in ship_ids]
                        s_id = get_closest_ship(game, map_pos, ship_list)
                        
                        if s_id:
                            logging.info("Closest ship id: {} to target {} at ({}, {})".format(s_id, enemy_id, i, j))
                            for g in self.gs:
                                if g.id == s_id:
                                    self.gs.remove(g)
                                    break
                            self.ds.append(destroyer(s_id, enemy_id))
                        else:
                            logging.info("Have to use a gathering/returning ship to defend :(")
                            ship_ids = [g.id for g in self.gs]
                            ship_list = [s for s in me.get_ships() if s.id in ship_ids]
                            s_id = get_closest_ship(game, map_pos, ship_list)
                            if s_id:
                                for g in self.gs:
                                    if g.id == s_id:
                                        self.gs.remove(g)
                                        break
                                self.ds.append(destroyer(s_id, enemy_id))
                            else:
                                logging.info("we're done for")
                        
                        
        logging.info("Gatherers: {}".format([x.id for x in self.gs]))
        logging.info("Destroyers: {}".format([x.id for x in self.ds]))
        # update ships
        for g in self.gs:
            if me.has_ship(g.id):
                g_ship = me.get_ship(g.id)
                command_queue.append(g.update(g_ship, game))
            else:
                logging.info("Warning: missing ship in gatherers")
            
        for d in self.ds:
            if me.has_ship(d.id):
                d_ship = me.get_ship(d.id)
                command_queue.append(d.update(d_ship, game))
            else:
                logging.info("Warning: missing ship in destroyers")
        # logging.info("UPDATED SHIPS")
                
        # If the game is in the first 200 turns and you have enough halite, spawn a ship.
        # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
        if game.turn_number <= 150 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and len(me.get_ships()) < 15 and not self.stop_spawning:
            if (get_total_halite(game) > 50000):
                command_queue.append(me.shipyard.spawn())
            else:
                self.stop_spawning = True

        return command_queue
