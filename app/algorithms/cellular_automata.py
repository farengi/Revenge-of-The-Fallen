import random
from app.algorithms.bfs import bfs_pathfind

def decide_next_move(element, grid, topology):
    """
    Decide the next move based on cellular automata rules with improved deadlock fallback:
      1. Update history and track stuck_count
      2. BFS fallback if an agent has been stuck for several steps
      3. Direct path movement when aligned
      4. Gradient following (closer to target)
      5. Random movement for fallback

    This hybrid approach uses local rules most of the time, but
    falls back to global pathfinding to break persistent loops.
    """


    # 0) No movement if no target or already there
    if not element.has_target() or element.at_target():
        return None

    # 1) Update history and stuck_count
    # Ensure element has history attributes
    if hasattr(element, 'update_history'):
        element.update_history()
    # Determine progress
    try:
        progress = element.is_making_progress()
    except AttributeError:
        progress = True
    # Track stuck_count on the element
    count = getattr(element, 'stuck_count', 0)
    if not progress:
        count += 1
    else:
        count = 0
    element.stuck_count = count

    # 2) BFS fallback when stuck too long
    if element.stuck_count >= 3:
        tx, ty = element.target_x, element.target_y
        # Temporarily remove element for pathfinding
        grid.remove_element(element)
        result = bfs_pathfind(grid, element.x, element.y, tx, ty, topology)
        grid.add_element(element)
        if result:
            path, _ = result
            if path and len(path) > 1:
                # Reset stuck counter and take first step on path
                element.stuck_count = 0
                return path[1]
        # If BFS fails, proceed to local rules

    # 3) Gather valid empty neighbors
    neighbors = grid.get_neighbors(element.x, element.y, topology)
    valid = [(x, y) for x, y in neighbors if grid.is_empty(x, y)]
    if not valid:
        return None

    # 4) Direct path along major axis
    tx, ty = element.target_x, element.target_y
    dx, dy = tx - element.x, ty - element.y
    if abs(dx) > abs(dy):
        candidate = (element.x + (1 if dx > 0 else -1), element.y)
    else:
        candidate = (element.x, element.y + (1 if dy > 0 else -1))
    if candidate in valid:
        return candidate

    # 5) Gradient following: minimize Manhattan distance
    gradient = sorted(valid, key=lambda p: abs(p[0]-tx) + abs(p[1]-ty))
    move_grad = gradient[0]
    if random.random() < 0.9:
        return move_grad

    # 6) Random fallback
    return random.choice(valid)
