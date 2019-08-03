# Python 3.6

import hlt

from hlt import constants
from hlt.positionals import Direction

from Overmind.ga_param import Params as GAP

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
def calc_max_ships(game):
    max_ships = int((GAP.MAX_SHIPS_X / game.game_map.width) + (GAP.MAX_SHIPS_Y / get_total_halite(game)))
    return max_ships
    
# =============================================================================
# get targets - find the places with the most concentrated halite on the map
# =============================================================================
def get_targets(game, n):
    p_dist = list(range(-GAP.TARGET_SIZE, GAP.TARGET_SIZE+1))
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
            
            d_value = 1 + ((dist / max_dist) * (GAP.DSCALE - 1))
            
            value = value / d_value

            map_values[p] = value
            
    # sort map_values and return the best n positions
    sorted_d = sorted(map_values.items(), key=lambda x: x[1], reverse=True)
    
    targets = []
    for i in range(n):
        targets.append(sorted_d[i][0])

    return targets

# =============================================================================
def assign_targets(game, gs):
    p_dist = list(range(-2, 3))
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
                    
            map_values[p] = value
            
    # now scale the values for each ship we want to assign
    max_dist = math.sqrt((game.game_map.width*game.game_map.width/4) + (game.game_map.height*game.game_map.height/4))
    
    for g in gs:
        if game.me.has_ship(g.id):
            temp_map_vals = {}
            for pos, val in map_values.items():
                dist = game.game_map.calculate_distance(game.me.get_ship(g.id).position, pos)
                d_value = 1 + ((dist / max_dist) * (GAP.DSCALE - 1))
                temp_map_vals[pos] = val / d_value
            
            # now sort and assign
            sorted_d = sorted(temp_map_vals.items(), key=lambda x: x[1], reverse=True)
            g.seek_pos = sorted_d[0][0]
            map_values.pop(g.seek_pos, None)
        
# =============================================================================
def get_dist(game, p1, p2):
    w = game.game_map.width
    h = game.game_map.height
    
    dx = int(math.fabs(p1.x - p2.x))
    if dx > w - dx:
        dx = w - dx
    
    dy = int(math.fabs(p1.y - p2.y))
    if dy > h - dy:
        dy = h - dy
        
    return math.sqrt((dx * dx) + (dy * dy))
    
# =============================================================================
# A* pathfinding
# =============================================================================
def get_path(game, p1, p2, unsafe=False):
    
    class Node:
        def __init__(self, pos):
            self.previous = None
            self.h = None
            self.cost = 0
            self.p = pos
            
    if p1 == p2:
        return None
    
    if not unsafe and game.game_map[p2].is_occupied:
        return None
        
    start_node = Node(p1)
    evaluated_nodes = []
    leaf_nodes = []
    
    head_node = start_node
    while True:
        # get new leaf nodes
        new_leaf_positions = head_node.p.get_surrounding_cardinals()
        new_leaf_positions = [x for x in new_leaf_positions if x not in [n.p for n in evaluated_nodes]]
        if unsafe:
            for n in new_leaf_positions:
                if n == p2:
                    new_leaf_positions = [p2]
        else:
            new_leaf_positions = [x for x in new_leaf_positions if not game.game_map[x].is_occupied]
        
        # new_leaf_positions = [x for x in head_node.p.get_surrounding_cardinals() if not game.game_map[x].is_occupied and x not in evaluated_nodes]
        
        # evaluate leaf nodes
        for pos in new_leaf_positions:
            nn = Node(pos)
            nn.previous = head_node
            nn.cost = head_node.cost + 1
            
            if pos == p2:
                # found a path, generate a list of positions and return items
                logging.info("Path found!")
                path = [pos]
                p_node = nn.previous
                while True:
                    if p_node.previous is None:
                        return path[::-1]
                        
                    path.append(p_node.p)
                    p_node = p_node.previous
            else:
                nn.h = get_dist(game, nn.p, p2)
                leaf_nodes.append(nn)
                evaluated_nodes.append(nn)
        
        # update head node
        if not leaf_nodes:
            # no new nodes, return failure
            return None
        else:
            leaf_nodes.sort(key=lambda node: node.cost + node.h)
            head_node = leaf_nodes.pop(0)

# =============================================================================            
def get_closest_ship(game, pos, ship_list):
    s_id = None
    
    dist = 1000
    for shp in ship_list:
        temp_dist = get_dist(game, pos, shp.position)
        if temp_dist < dist:
            dist = temp_dist
            s_id = shp.id
    
    return s_id
    
# =============================================================================            
def get_ship_from_id(game, id):
    s = None
    for p_id in game.players:
        if game.players[p_id].has_ship(id):
            s = game.players[p_id].get_ship(id)
            break
            
    return s
    